import logging
import os
from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    hashed = pwd_context.hash(password)
    if not _is_valid_bcrypt_hash(hashed):
        raise ValueError("Generated password hash is malformed")
    return hashed


def _is_valid_bcrypt_hash(hashed_password: str) -> bool:
    if not isinstance(hashed_password, str):
        return False
    if len(hashed_password) != 60:
        return False
    return hashed_password.startswith("$2a$") or hashed_password.startswith("$2b$") or hashed_password.startswith("$2y$")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not _is_valid_bcrypt_hash(hashed_password):
        logger.warning("auth.verify_password.invalid_hash_format")
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        logger.exception("auth.verify_password.exception")
        return False


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
