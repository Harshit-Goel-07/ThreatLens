"""Integration tests for query API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_query_unauthenticated():
    """Test query endpoint without authentication."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/query",
            json={"query": "test query", "source_types": ["mitre"]},
        )

        assert response.status_code == 401


@pytest.mark.asyncio
async def test_query_authenticated():
    """Test query endpoint with valid authentication."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/query",
            json={"query": "test query", "source_types": ["mitre"]},
            headers={"X-API-Key": "test-api-key-12345"},
        )

        # Should be processed and return a status (200 OK or handled model response)
        assert response.status_code in (200, 400, 422, 500)
        assert response.status_code != 401


@pytest.mark.asyncio
async def test_query_invalid_input():
    """Test query endpoint with invalid input."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Test with empty query
        response = await client.post(
            "/api/v1/query",
            json={"query": "", "source_types": ["mitre"]},
            headers={"X-API-Key": "test-api-key-12345"},
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_query_stream_unauthenticated():
    """Test query stream endpoint without authentication."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/query/stream",
            json={"query": "test query", "source_types": ["mitre"]},
        )

        assert response.status_code == 401
