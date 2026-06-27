"""
Security primitives: password hashing and JWT creation/verification.

Uses PyJWT (actively maintained) instead of python-jose, and passlib/bcrypt for
password hashing. All functions are pure and side-effect free so they are easy
to unit-test.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- Password hashing --------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored hash (constant time)."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        # Malformed hash – treat as a failed verification rather than crashing.
        return False


# --- JWT ---------------------------------------------------------------------
def create_access_token(
    subject: str,
    extra_claims: Optional[dict[str, Any]] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    """Create a signed JWT access token for ``subject`` (typically a user id)."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes or settings.jwt_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "jti": secrets.token_urlsafe(16),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises ``jwt.PyJWTError`` on failure."""
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "iat", "sub"]},
    )


def constant_time_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to avoid timing attacks."""
    return secrets.compare_digest(a, b)
