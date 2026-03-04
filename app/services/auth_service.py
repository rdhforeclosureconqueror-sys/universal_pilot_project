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

    def register_user(self, email: str, password: str, role: UserRole = UserRole.user) -> User:
        existing = self.db.query(User).filter(User.email == email).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        user = User(
            id=uuid4(),
            email=email.strip().lower(),
            hashed_password=hash_password(password),
            role=role,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_admin(self, email: str, password: str, admin_secret: str | None = None) -> User:
        existing_admin = self.db.query(User).filter(User.role == UserRole.admin).first()
        required_secret = os.getenv("ADMIN_CREATION_SECRET", "").strip()

        if existing_admin and required_secret and admin_secret != required_secret:
            raise HTTPException(status_code=403, detail="Admin already exists; valid admin secret required")

        existing = self.db.query(User).filter(User.email == email).first()
        if existing:
            if existing.role != UserRole.admin:
                existing.role = UserRole.admin
                existing.hashed_password = hash_password(password)
                self.db.commit()
                self.db.refresh(existing)
            return existing

        return self.register_user(email=email, password=password, role=UserRole.admin)

    def login(self, username: str, password: str) -> dict:
        user = self.db.query(User).filter(User.email == username.strip().lower()).first()
        if not user:
            logger.info("auth.login.user_missing", extra={"email": username})
            raise HTTPException(status_code=401, detail="Incorrect email or password")

        logger.info("auth.login.attempt", extra={"user_id": str(user.id), "email": user.email})
        if not verify_password(password, user.hashed_password):
            logger.warning("auth.login.password_failed", extra={"user_id": str(user.id), "email": user.email})
            raise HTTPException(status_code=401, detail="Incorrect email or password")

        token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "role": user.role.value if user.role else UserRole.user.value,
            }
        )
        return {"access_token": token, "token_type": "bearer"}


def ensure_admin_user(db: Session) -> bool:
    existing_admin = db.query(User).filter(User.role == UserRole.admin).first()
    if existing_admin:
        return False

    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "").strip()
    if not email or not password:
        logging.getLogger(__name__).warning("auth.bootstrap_admin.missing_env")
        return False

    AuthService(db).create_admin(email=email, password=password, admin_secret=os.getenv("ADMIN_CREATION_SECRET"))
    logging.getLogger(__name__).info("auth.bootstrap_admin.created", extra={"email": email})
    return True
