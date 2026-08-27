"""Unit tests for security utilities."""

import pytest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


def test_hash_password():
    """Test password hashing."""
    password = "secure_password_123"
    hashed = hash_password(password)

    assert hashed != password
    assert isinstance(hashed, str)
    assert len(hashed) > 50


def test_verify_password_correct():
    """Test password verification with correct password."""
    password = "secure_password_123"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_incorrect():
    """Test password verification with incorrect password."""
    password = "secure_password_123"
    wrong_password = "wrong_password"
    hashed = hash_password(password)

    assert verify_password(wrong_password, hashed) is False


def test_create_access_token():
    """Test JWT access token creation."""
    token = create_access_token("test_user", extra_claims={"role": "user"})

    assert isinstance(token, str)
    assert len(token) > 50


def test_decode_access_token_valid():
    """Test JWT access token decoding with valid token."""
    token = create_access_token("test_user", extra_claims={"role": "user"})

    decoded = decode_access_token(token)

    assert decoded["sub"] == "test_user"
    assert decoded["role"] == "user"


def test_decode_access_token_invalid():
    """Test JWT access token decoding with invalid token."""
    invalid_token = "invalid.token.string"

    with pytest.raises(Exception):
        decode_access_token(invalid_token)


def test_token_expiration():
    """Test that tokens have an expiration claim."""
    token = create_access_token("test_user", expires_minutes=60)

    decoded = decode_access_token(token)

    assert "exp" in decoded
