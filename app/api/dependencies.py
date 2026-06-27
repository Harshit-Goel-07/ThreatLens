"""
Authentication & authorization dependencies.

Two complementary mechanisms are supported (the user chose "both"):

1. **Service API keys** via the ``X-API-Key`` header — ideal for
   service-to-service / automation callers.
2. **JWT bearer tokens** via the ``Authorization: Bearer <token>`` header —
   ideal for interactive users authenticated through ``/api/v1/auth/login``.

A request is authorized if *either* mechanism succeeds.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import constant_time_compare, decode_access_token
from app.database.models import User
from app.database.postgres import get_async_session

# auto_error=False so we can combine both schemes and emit a single 401.
_api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


@dataclass
class Principal:
    """The authenticated caller."""

    subject: str
    role: str
    auth_method: str  # "api_key" | "jwt"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def _match_api_key(api_key: Optional[str]) -> bool:
    if not api_key:
        return False
    return any(constant_time_compare(api_key, known) for known in settings.api_key_set)


async def get_current_principal(
    api_key: Optional[str] = Depends(_api_key_scheme),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_async_session),
) -> Principal:
    """Resolve the caller from an API key or a JWT, or raise 401."""
    # 1) Service API key.
    if _match_api_key(api_key):
        return Principal(subject="service", role="admin", auth_method="api_key")

    # 2) JWT bearer token.
    if credentials and credentials.scheme.lower() == "bearer":
        try:
            payload = decode_access_token(credentials.credentials)
        except jwt.PyJWTError:
            raise _UNAUTHORIZED

        user_id = payload.get("sub")
        if not user_id:
            raise _UNAUTHORIZED

        user = await db.get(User, int(user_id)) if user_id.isdigit() else None
        if user is None or not user.is_active:
            raise _UNAUTHORIZED

        return Principal(subject=str(user.id), role=user.role, auth_method="jwt")

    raise _UNAUTHORIZED


async def require_admin(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    """Authorize only admin principals (used for ingestion/management routes)."""
    if not principal.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return principal


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()
