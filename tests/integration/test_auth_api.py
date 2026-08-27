"""Integration tests for authentication API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.database.models import User
from app.database.postgres import session_scope
from app.main import app


@pytest.mark.asyncio
async def test_login_success():
    """Test successful login with valid credentials."""
    async with session_scope() as session:
        user = User(
            email="test@example.com",
            full_name="Test User",
            hashed_password=hash_password("testpass123"),
            is_active=True,
            role="analyst",
        )
        session.add(user)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpass123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrongpass"},
        )

        assert response.status_code == 401


@pytest.mark.asyncio
async def test_current_user_unauthenticated():
    """Test accessing current user endpoint without authentication."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401


@pytest.mark.asyncio
async def test_current_user_authenticated():
    """Test accessing current user endpoint with valid token."""
    async with session_scope() as session:
        user = User(
            email="test2@example.com",
            full_name="Test User 2",
            hashed_password=hash_password("testpass123"),
            is_active=True,
            role="analyst",
        )
        session.add(user)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test2@example.com", "password": "testpass123"},
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "subject" in data
        assert data["role"] == "analyst"


@pytest.mark.asyncio
async def test_api_key_authentication():
    """Test authentication using service API key."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/auth/me",
            headers={"X-API-Key": "test-api-key-12345"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["auth_method"] == "api_key"
