"""Unit tests for input guardrails."""

import pytest
from app.core.guardrails import validate_query_input, sanitize_error_message


def test_validate_query_input_normal():
    """Test validation of normal query input."""
    query = "What are the common MITRE ATT&CK techniques?"
    
    is_valid, error = validate_query_input(query)
    
    assert is_valid is True
    assert error is None


def test_validate_query_input_too_long():
    """Test validation of overly long query input."""
    query = "test " * 10000  # Very long query
    
    is_valid, error = validate_query_input(query)
    
    assert is_valid is False
    assert error is not None
    assert "too long" in error.lower()


def test_validate_query_input_empty():
    """Test validation of empty query input."""
    query = ""
    
    is_valid, error = validate_query_input(query)
    
    assert is_valid is False
    assert error is not None


def test_validate_query_input_whitespace_only():
    """Test validation of whitespace-only query input."""
    query = "   \n\t   "
    
    is_valid, error = validate_query_input(query)
    
    assert is_valid is False
    assert error is not None


def test_sanitize_error_message():
    """Test error message sanitization."""
    error_message = "Database connection failed: password=secret123"
    
    sanitized = sanitize_error_message(error_message)
    
    assert "secret123" not in sanitized
    assert "password=" not in sanitized.lower()


def test_sanitize_error_message_with_path():
    """Test error message sanitization with file paths."""
    error_message = "Error reading file at /home/user/config/secret.key"
    
    sanitized = sanitize_error_message(error_message)
    
    assert "/home/user/" not in sanitized or "secret.key" not in sanitized


def test_sanitize_error_message_safe():
    """Test that safe error messages are not modified."""
    error_message = "Invalid input provided"
    
    sanitized = sanitize_error_message(error_message)
    
    assert sanitized == error_message
