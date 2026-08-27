"""Pytest configuration and shared fixtures."""

import os
import pytest

# Set test environment variables before importing app modules
os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "false"
os.environ["JWT_SECRET_KEY"] = "test" * 8  # 32 chars
os.environ["POSTGRES_URL"] = "sqlite+aiosqlite:///./test_runner.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["QDRANT_HOST"] = "localhost"
os.environ["QDRANT_PORT"] = "6333"
os.environ["API_KEYS"] = "test-api-key-12345"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def initialize_test_db():
    """Ensure clean database state per test."""
    from app.database.models import Base
    from app.database.postgres import get_async_engine, init_postgres

    await init_postgres()
    engine = get_async_engine()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield
