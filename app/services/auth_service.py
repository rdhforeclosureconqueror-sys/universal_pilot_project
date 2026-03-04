from __future__ import annotations

import logging
import os
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.users import User, UserRole
from auth.auth_handler import create_access_token, hash_password, verify_password

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    # =====================================================
    # USER REGISTRATION
    # =====================================================

    def register_user(self, email: str, password: str, role: UserRole = UserRole.user) -> User:
        email = email.strip().lower()

        existing = self.db.query(User).filter(User.email == email).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        user = User(
            id=uuid4(),
            email=email,
            hashed_password=hash_password(password),
            role=role,
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    # =====================================================
    # ADMIN CREATION
    # =====================================================

    def create_admin(self, email: str, password: str, admin_secret: str | None = None) -> User:
        email = email.strip().lower()

        existing_admin = self.db.query(User).filter(User.role == UserRole.admin).first()
        required_secret = os.getenv("ADMIN_CREATION_SECRET", "").strip()

        if existing_admin and required_secret and admin_secret != required_secret:
            raise HTTPException(
                status_code=403,
                detail="Admin already exists; valid admin secret required",
            )

        existing = self.db.query(User).filter(User.email == email).first()

        if existing:
            if existing.role != UserRole.admin:
                existing.role = UserRole.admin

            existing.hashed_password = hash_password(password)

            self.db.commit()
            self.db.refresh(existing)

            return existing

        return self.register_user(email=email, password=password, role=UserRole.admin)

    # =====================================================
    # LOGIN
    # =====================================================

    def login(self, username: str, password: str) -> dict:
        email = username.strip().lower()

        user = self.db.query(User).filter(User.email == email).first()

        if not user:
            logger.info("auth.login.user_missing", extra={"email": email})
            raise HTTPException(status_code=401, detail="Incorrect email or password")

        logger.info(
            "auth.login.attempt",
            extra={"user_id": str(user.id), "email": user.email},
        )

        if not verify_password(password, user.hashed_password):
            logger.warning(
                "auth.login.password_failed",
                extra={"user_id": str(user.id), "email": user.email},
            )
            raise HTTPException(status_code=401, detail="Incorrect email or password")

        token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "role": user.role.value if user.role else UserRole.user.value,
            }
        )

        return {"access_token": token, "token_type": "bearer"}


# =====================================================
# ADMIN BOOTSTRAP
# =====================================================

def ensure_admin_user(db: Session) -> bool:
    """
    Ensures an admin exists using environment variables.

    Behavior:
    - If admin does not exist → create one
    - If admin exists but email matches → update password if needed
    - If admin exists with different email → leave untouched
    """

    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "").strip()

    if not email or not password:
        logger.warning("auth.bootstrap_admin.missing_env")
        return False

    existing = db.query(User).filter(User.email == email).first()

    if existing:
        if existing.role != UserRole.admin:
            existing.role = UserRole.admin

        # Ensure password stays in sync with env
        if not verify_password(password, existing.hashed_password):
            existing.hashed_password = hash_password(password)
            db.commit()
            logger.info("auth.bootstrap_admin.password_updated", extra={"email": email})

        return True

    # Create admin if missing
    AuthService(db).create_admin(
        email=email,
        password=password,
        admin_secret=os.getenv("ADMIN_CREATION_SECRET"),
    )

    logger.info("auth.bootstrap_admin.created", extra={"email": email})

    return True
