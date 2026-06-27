"""Integration tests for query API endpoints."""

import pytest
from httpx import AsyncClient
from app.main import app
from app.database.models import User
from app.database.postgres import async_session_maker
from app.core.security import hash_password


@pytest.mark.asyncio
async def test_query_unauthenticated():
    """Test query endpoint without authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/query",
            json={"query": "test query", "sources": ["mitre"]},
        )
        
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_query_authenticated():
    """Test query endpoint with valid authentication."""
    async with async_session_maker() as session:
        # Create a test user
        user = User(
            username="queryuser",
            email="query@example.com",
            hashed_password=hash_password("testpass123"),
            api_key="query-api-key",
            is_active=True,
            is_admin=False,
        )
        session.add(user)
        await session.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/query",
            json={"query": "test query", "sources": ["mitre"]},
            headers={"X-API-Key": "query-api-key"},
        )
        
        # May fail due to missing vector store, but should not be 401
        assert response.status_code != 401


@pytest.mark.asyncio
async def test_query_invalid_input():
    """Test query endpoint with invalid input."""
    async with async_session_maker() as session:
        # Create a test user
        user = User(
            username="validationuser",
            email="validation@example.com",
            hashed_password=hash_password("testpass123"),
            api_key="validation-api-key",
            is_active=True,
            is_admin=False,
        )
        session.add(user)
        await session.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test with empty query
        response = await client.post(
            "/api/query",
            json={"query": "", "sources": ["mitre"]},
            headers={"X-API-Key": "validation-api-key"},
        )
        
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_query_stream_unauthenticated():
    """Test query stream endpoint without authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/query/stream",
            json={"query": "test query", "sources": ["mitre"]},
        )
        
        assert response.status_code == 401
