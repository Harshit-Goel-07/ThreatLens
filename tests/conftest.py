"""Pytest configuration and shared fixtures."""

import os
import pytest
from typing import AsyncGenerator, Generator

# Set test environment variables before importing app modules
os.environ["JWT_SECRET_KEY"] = "test" * 8  # 32 chars
os.environ["POSTGRES_URL"] = "postgresql://test:test@localhost:5432/test_db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["QDRANT_URL"] = "http://localhost:6333"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DEBUG"] = "true"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    """Fixture for test database session."""
    from app.database.postgres import async_session_maker, init_db
    
    # Initialize test database
    await init_db()
    
    async with async_session_maker() as session:
        yield session
        
        # Cleanup
        await session.rollback()
