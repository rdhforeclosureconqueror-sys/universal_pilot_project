from typing import List

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from auth.auth_handler import decode_access_token
from db.session import get_db
from models.users import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)

    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == payload["sub"]).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def require_role(allowed_roles: List[UserRole]):
    def role_checker(user: User = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions",
            )
        return user

    return role_checker
