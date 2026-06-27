"""
Authentication routes: login (JWT issuance) and current-user introspection.

User provisioning is handled out-of-band (bootstrap admin via env vars, or by an
admin creating analysts) to keep the public surface minimal and safe.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import Principal, get_current_principal, get_user_by_email, require_admin
from app.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.database.models import User
from app.database.postgres import get_async_session

logger = logging.getLogger(__name__)
router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    full_name: str | None = Field(default=None, max_length=255)
    role: str = Field(default="analyst", pattern="^(analyst|admin)$")


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None
    role: str
    is_active: bool


@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_async_session)):
    """Authenticate a user and return a JWT access token."""
    user = await get_user_by_email(db, payload.email)
    # Always run a verification to keep timing roughly constant.
    placeholder = "$2b$12$" + "x" * 53
    if user is None or not verify_password(payload.password, user.hashed_password or placeholder):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token(subject=str(user.id), extra_claims={"role": user.role})
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.get("/auth/me", response_model=dict)
async def whoami(principal: Principal = Depends(get_current_principal)):
    """Return the identity of the current caller."""
    return {
        "subject": principal.subject,
        "role": principal.role,
        "auth_method": principal.auth_method,
    }


@router.post("/auth/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateRequest,
    _: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new user (admin only)."""
    existing = await get_user_by_email(db, payload.email)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("Created user %s with role %s", user.email, user.role)
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )
