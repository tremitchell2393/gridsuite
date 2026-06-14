"""
Security utilities: password hashing and JWT token creation/verification.

Kept intentionally minimal. If/when GridSuite moves to a managed auth
provider (Clerk, Auth0, Supabase Auth — as recommended in the architecture
doc), this module is the seam that gets swapped out; nothing else in the
app should need to change since routes depend on `get_current_user`
in app/api/v1/deps.py, not on these functions directly.
"""
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """
    Create a signed JWT for the given subject (typically the user ID).
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.now(UTC) + expires_delta
    to_encode = {"sub": str(subject), "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT. Raises jose.JWTError if invalid/expired —
    callers (see api/v1/deps.py) catch this and translate to a 401.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
