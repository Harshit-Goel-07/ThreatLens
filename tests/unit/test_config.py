"""Unit tests for configuration management."""

import os
import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_defaults():
    """Test that Settings loads with default values where possible."""
    # Set minimal required environment variables
    os.environ["JWT_SECRET_KEY"] = "test" * 8  # 32 chars
    os.environ["POSTGRES_URL"] = "postgresql://user:pass@localhost:5432/test"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    
    settings = Settings()
    
    assert settings.jwt_secret_key == "test" * 8
    assert settings.postgres_url == "postgresql://user:pass@localhost:5432/test"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.app_name == "Security Copilot"
    assert settings.debug is False
    assert settings.environment == "production"


def test_settings_jwt_secret_too_short():
    """Test that JWT secret key must be at least 32 characters."""
    os.environ["JWT_SECRET_KEY"] = "short"
    os.environ["POSTGRES_URL"] = "postgresql://user:pass@localhost:5432/test"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    
    with pytest.raises(ValidationError):
        Settings()


def test_settings_openai_config():
    """Test OpenAI configuration settings."""
    os.environ["JWT_SECRET_KEY"] = "test" * 8
    os.environ["POSTGRES_URL"] = "postgresql://user:pass@localhost:5432/test"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["OPENAI_API_KEY"] = "sk-test-key"
    os.environ["OPENAI_MODEL"] = "gpt-4"
    
    settings = Settings()
    
    assert settings.openai_api_key == "sk-test-key"
    assert settings.openai_model == "gpt-4"
    assert settings.use_openai is True


def test_settings_ollama_config():
    """Test Ollama configuration settings."""
    os.environ["JWT_SECRET_KEY"] = "test" * 8
    os.environ["POSTGRES_URL"] = "postgresql://user:pass@localhost:5432/test"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
    os.environ["OLLAMA_MODEL"] = "llama2"
    
    settings = Settings()
    
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.ollama_model == "llama2"
    assert settings.use_openai is False


def test_settings_cors_origins():
    """Test CORS origins configuration."""
    os.environ["JWT_SECRET_KEY"] = "test" * 8
    os.environ["POSTGRES_URL"] = "postgresql://user:pass@localhost:5432/test"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["CORS_ORIGINS"] = "http://localhost:5173,http://localhost:3000"
    
    settings = Settings()
    
    assert settings.cors_origins == ["http://localhost:5173", "http://localhost:3000"]


def test_settings_qdrant_config():
    """Test Qdrant configuration settings."""
    os.environ["JWT_SECRET_KEY"] = "test" * 8
    os.environ["POSTGRES_URL"] = "postgresql://user:pass@localhost:5432/test"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["QDRANT_URL"] = "http://localhost:6333"
    
    settings = Settings()
    
    assert settings.qdrant_url == "http://localhost:6333"
    assert settings.qdrant_api_key is None
