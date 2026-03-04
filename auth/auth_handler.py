import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# =====================================================
# JWT CONFIG
# =====================================================

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# =====================================================
# PASSWORD HASHING
# =====================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str) -> str:
    """
    Generate a bcrypt hash for a password.
    """
    if not password:
        raise ValueError("Password cannot be empty")

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored hash.
    """

    if not hashed_password:
        logger.warning("auth.verify_password.missing_hash")
        return False

    try:
        return pwd_context.verify(plain_password, hashed_password)

    except ValueError:
        # Happens when hash format is invalid
        logger.warning("auth.verify_password.invalid_hash_format")
        return False

    except Exception:
        logger.exception("auth.verify_password.exception")
        return False


# =====================================================
# TOKEN CREATION
# =====================================================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    """

    to_encode = data.copy()

    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# =====================================================
# TOKEN DECODING
# =====================================================

def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.
    """

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        return payload

    except JWTError:
        return None
