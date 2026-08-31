"""
Database connection and initialization for ThreatLens.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.database.models import Base

logger = logging.getLogger(__name__)


def _build_async_url(url: str) -> str:
    """Convert a database URL to its async driver variant."""
    if "sqlite" in url:
        return url if "aiosqlite" in url else url.replace("sqlite://", "sqlite+aiosqlite://")
    return url.replace("postgresql://", "postgresql+asyncpg://")


_engine_kwargs = dict(echo=settings.debug, future=True)
# pool_pre_ping is unsupported for SQLite's NullPool
if "sqlite" not in settings.postgres_url_full:
    _engine_kwargs["pool_pre_ping"] = True

async_engine = create_async_engine(_build_async_url(settings.postgres_url_full), **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def get_async_engine():
    """Return current active async engine."""
    return async_engine


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for async sessions outside of request handlers."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_postgres() -> None:
    """Initialize database — creates tables. Falls back to SQLite if PostgreSQL fails."""
    global async_engine, AsyncSessionLocal
    try:
        logger.info("Initializing database...")
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        db_type = "SQLite" if "sqlite" in str(async_engine.url) else "PostgreSQL"
        logger.info("%s database initialized successfully", db_type)
    except Exception as e:
        logger.warning("Database init failed (%s). Falling back to local SQLite.", e)
        async_engine = create_async_engine("sqlite+aiosqlite:///./threatlens.db", echo=settings.debug, future=True)
        AsyncSessionLocal.configure(bind=async_engine)
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("SQLite fallback database initialized successfully")


async def close_postgres() -> None:
    """Dispose database engine connections."""
    try:
        await async_engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error("Error closing database: %s", e)


async def check_postgres_health() -> bool:
    """Check database health."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
