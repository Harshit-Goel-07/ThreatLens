"""
Configuration management for Security Copilot.

Settings are loaded from environment variables (and an optional ``.env`` file)
using ``pydantic-settings`` v2. Secrets never have insecure defaults: in a
non-debug ("production") environment the application refuses to start unless the
required secrets are provided.
"""

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# A clearly-marked placeholder used by .env.example. If it ever reaches a
# production runtime we fail fast instead of running with a known secret.
_INSECURE_PLACEHOLDERS = {
    "",
    "change-me",
    "your-secret-key-here",
    "secure_password",
    "sk-...",
}


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Runtime environment ------------------------------------------------
    environment: Literal["development", "staging", "production"] = Field(
        default="production", alias="ENVIRONMENT"
    )
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=True, alias="LOG_JSON")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    # --- LLM provider selection --------------------------------------------
    llm_provider: Literal["openai", "ollama"] = Field(
        default="openai", alias="LLM_PROVIDER"
    )
    use_openai_embeddings: bool = Field(default=False, alias="USE_OPENAI_EMBEDDINGS")

    # --- OpenAI -------------------------------------------------------------
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL"
    )

    # --- Ollama (local models) ---------------------------------------------
    ollama_host: str = Field(default="http://localhost:11434", alias="OLLAMA_HOST")
    ollama_model: str = Field(default="llama3", alias="OLLAMA_MODEL")

    # --- Vector database (Qdrant) ------------------------------------------
    qdrant_host: str = Field(default="localhost", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")
    qdrant_api_key: Optional[str] = Field(default=None, alias="QDRANT_API_KEY")
    qdrant_https: bool = Field(default=False, alias="QDRANT_HTTPS")

    # --- PostgreSQL ---------------------------------------------------------
    postgres_url: Optional[str] = Field(default=None, alias="POSTGRES_URL")
    postgres_user: str = Field(default="seccopilot", alias="POSTGRES_USER")
    postgres_password: str = Field(default="", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="seccopilot", alias="POSTGRES_DB")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    # --- Redis (caching / rate-limit backend) ------------------------------
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    cache_ttl_seconds: int = Field(default=3600, alias="CACHE_TTL_SECONDS")

    # --- Authentication -----------------------------------------------------
    jwt_secret_key: str = Field(default="", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=30, alias="JWT_EXPIRE_MINUTES")
    # Comma-separated list of accepted service API keys (X-API-Key header).
    api_keys: str = Field(default="", alias="API_KEYS")
    # Bootstrap admin user created on first startup (optional).
    admin_email: Optional[str] = Field(default=None, alias="ADMIN_EMAIL")
    admin_password: Optional[str] = Field(default=None, alias="ADMIN_PASSWORD")

    # --- CORS / security ----------------------------------------------------
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        alias="CORS_ORIGINS",
    )
    rate_limit: str = Field(default="60/minute", alias="RATE_LIMIT")
    max_request_bytes: int = Field(default=1_048_576, alias="MAX_REQUEST_BYTES")

    # --- Ingestion ----------------------------------------------------------
    mitre_data_url: str = Field(
        default="https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json",
        alias="MITRE_DATA_URL",
    )
    nvd_api_base_url: str = Field(
        default="https://services.nvd.nist.gov/rest/json/cves/2.0",
        alias="NVD_API_BASE_URL",
    )
    nvd_api_key: Optional[str] = Field(default=None, alias="NVD_API_KEY")
    ingestion_batch_size: int = Field(default=100, alias="INGESTION_BATCH_SIZE")

    # --- Retrieval ----------------------------------------------------------
    default_top_k: int = Field(default=10, alias="DEFAULT_TOP_K")
    rerank_top_k: int = Field(default=5, alias="RERANK_TOP_K")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")
    reranker_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2", alias="RERANKER_MODEL"
    )
    chunk_size: int = Field(default=500, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, alias="CHUNK_OVERLAP")
    max_query_length: int = Field(default=5000, alias="MAX_QUERY_LENGTH")

    # --- Validators ---------------------------------------------------------
    @field_validator("log_level")
    @classmethod
    def _normalise_log_level(cls, value: str) -> str:
        value = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if value not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(allowed)}")
        return value

    @model_validator(mode="after")
    def _enforce_production_secrets(self) -> "Settings":
        """Fail fast on insecure secrets in non-development environments."""
        if self.environment != "development" and not self.debug:
            problems: list[str] = []

            if self.jwt_secret_key in _INSECURE_PLACEHOLDERS or len(self.jwt_secret_key) < 32:
                problems.append(
                    "JWT_SECRET_KEY must be set to a strong value of >=32 chars"
                )
            if self.postgres_password in _INSECURE_PLACEHOLDERS:
                problems.append("POSTGRES_PASSWORD must be set to a non-default value")
            if self.llm_provider == "openai" and (
                not self.openai_api_key or self.openai_api_key in _INSECURE_PLACEHOLDERS
            ):
                problems.append("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

            if problems:
                raise ValueError(
                    "Insecure/missing configuration for a non-development "
                    "environment:\n  - " + "\n  - ".join(problems)
                )
        return self

    # --- Derived helpers ----------------------------------------------------
    @property
    def qdrant_url(self) -> str:
        scheme = "https" if self.qdrant_https else "http"
        return f"{scheme}://{self.qdrant_host}:{self.qdrant_port}"

    @property
    def postgres_url_full(self) -> str:
        if self.postgres_url and "@" in self.postgres_url:
            return self.postgres_url
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}

    @property
    def expose_docs(self) -> bool:
        """Only expose interactive API docs outside production."""
        return self.environment != "production" or self.debug


@lru_cache
def get_settings() -> "Settings":
    """Cached settings accessor (so the .env file is parsed only once)."""
    return Settings()


# Global settings instance (kept for backwards-compatibility with existing imports).
settings = get_settings()
