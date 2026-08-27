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
    """Create the bootstrap admin user from env vars, if configured and absent."""
    if not settings.admin_email or not settings.admin_password:
        return

    async with session_scope() as session:
        # Check primary email
        email_str = settings.admin_email.lower()
        result = await session.execute(
            select(User).where(User.email == email_str)
        )
        if result.scalar_one_or_none() is not None:
            return

        session.add(
            User(
                email=email_str,
                full_name="Administrator",
                hashed_password=hash_password(settings.admin_password),
                role="admin",
                is_active=True,
            )
        )
        logger.info("Created bootstrap admin user: %s", email_str)
