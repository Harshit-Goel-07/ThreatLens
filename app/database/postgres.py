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

# Async engine for FastAPI (uses the asyncpg driver).
async_engine = create_async_engine(
    settings.postgres_url_full.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.debug,
    future=True,
    pool_pre_ping=True,
)

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
    """Initialize PostgreSQL database with all tables"""
    try:
        logger.info("Initializing PostgreSQL database...")
        
        # Create all tables
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("PostgreSQL database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL: {e}")
        raise


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
