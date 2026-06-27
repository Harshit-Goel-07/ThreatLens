"""Integration tests for authentication API endpoints."""

import pytest
from httpx import AsyncClient
from app.main import app
from app.database.models import User
from app.database.postgres import async_session_maker
from app.core.security import hash_password


@pytest.mark.asyncio
async def test_login_success():
    """Test successful login with valid credentials."""
    async with async_session_maker() as session:
        # Create a test user
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=hash_password("testpass123"),
            is_active=True,
            is_admin=False,
        )
        session.add(user)
        await session.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpass123"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            json={"username": "nonexistent", "password": "wrongpass"},
        )
        
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_current_user_unauthenticated():
    """Test accessing current user endpoint without authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/auth/current")
        
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_current_user_authenticated():
    """Test accessing current user endpoint with valid token."""
    async with async_session_maker() as session:
        # Create a test user
        user = User(
            username="testuser2",
            email="test2@example.com",
            hashed_password=hash_password("testpass123"),
            is_active=True,
            is_admin=False,
        )
        session.add(user)
        await session.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login to get token
        login_response = await client.post(
            "/api/auth/login",
            json={"username": "testuser2", "password": "testpass123"},
        )
        token = login_response.json()["access_token"]
        
        # Access current user endpoint
        response = await client.get(
            "/api/auth/current",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser2"
        assert data["email"] == "test2@example.com"


@pytest.mark.asyncio
async def test_api_key_authentication():
    """Test authentication using API key."""
    async with async_session_maker() as session:
        # Create a test user with API key
        user = User(
            username="apikeyuser",
            email="apikey@example.com",
            hashed_password=hash_password("testpass123"),
            api_key="test-api-key-12345",
            is_active=True,
            is_admin=False,
        )
        session.add(user)
        await session.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/auth/current",
            headers={"X-API-Key": "test-api-key-12345"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "apikeyuser"
