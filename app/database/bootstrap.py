"""
Startup helpers for seeding initial database state.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.config import settings
from app.core.security import hash_password
from app.database.models import User
from app.database.postgres import session_scope

logger = logging.getLogger(__name__)


async def create_bootstrap_admin() -> None:
    """Create the bootstrap admin user from env vars, if configured and absent.

    Controlled by ADMIN_EMAIL / ADMIN_PASSWORD. Safe to call on every startup:
    it is a no-op when the user already exists or the vars are unset.
    """
    if not settings.admin_email or not settings.admin_password:
        return

    if len(settings.admin_password) < 12:
        logger.warning(
            "ADMIN_PASSWORD is shorter than 12 chars; skipping bootstrap admin creation"
        )
        return

    async with session_scope() as session:
        result = await session.execute(
            select(User).where(User.email == settings.admin_email.lower())
        )
        if result.scalar_one_or_none() is not None:
            return

        session.add(
            User(
                email=settings.admin_email.lower(),
                full_name="Bootstrap Admin",
                hashed_password=hash_password(settings.admin_password),
                role="admin",
                is_active=True,
            )
        )
        logger.info("Created bootstrap admin user: %s", settings.admin_email)
