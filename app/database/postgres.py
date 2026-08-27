"""
PostgreSQL connection and initialization for Security Copilot
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database.models import Base

logger = logging.getLogger(__name__)

# Async engine for FastAPI (supports asyncpg for Postgres and aiosqlite for SQLite).
db_url = settings.postgres_url_full
if "sqlite" in db_url:
    async_url = db_url if "sqlite+aiosqlite" in db_url else db_url.replace("sqlite://", "sqlite+aiosqlite://")
else:
    async_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

async_engine = create_async_engine(
    async_url,
    echo=settings.debug,
    future=True,
    pool_pre_ping=True,
)

def get_async_engine():
    """Return current active async engine."""
    return async_engine

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Sync engine for migrations and admin tasks
sync_engine = create_engine(
    settings.postgres_url_full,
    echo=settings.debug,
    pool_pre_ping=True,
)

# Sync session factory
SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for async sessions outside of request handlers.

    Commits on success, rolls back on error.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_sync_session():
    """Get sync database session"""
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        logger.error(f"Database session error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


async def init_postgres() -> None:
    """Initialize database with automatic SQLite fallback if PostgreSQL is unreachable."""
    global async_engine, AsyncSessionLocal
    try:
        logger.info("Initializing PostgreSQL database...")
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("PostgreSQL database initialized successfully")
    except Exception as e:
        logger.warning(f"PostgreSQL connection failed ({e}). Falling back to local SQLite database.")
        async_engine = create_async_engine("sqlite+aiosqlite:///./seccopilot.db", echo=settings.debug, future=True)
        AsyncSessionLocal.configure(bind=async_engine)
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("SQLite database fallback initialized successfully")


async def close_postgres() -> None:
    """Close PostgreSQL connections"""
    try:
        await async_engine.dispose()
        logger.info("PostgreSQL connections closed")
    except Exception as e:
        logger.error(f"Error closing PostgreSQL: {e}")


async def check_postgres_health() -> bool:
    """Check PostgreSQL health"""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}")
        return False
