"""
Rate limiting via slowapi.

The limiter keys on the authenticated API key (if present) or the client IP,
so a single noisy client cannot exhaust the budget for everyone. When REDIS_URL
is reachable slowapi uses it as a shared backend (correct across multiple
workers); otherwise it falls back to in-memory limiting.
"""

from __future__ import annotations

import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import settings

logger = logging.getLogger(__name__)


def _rate_limit_key(request: Request) -> str:
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"key:{api_key[:16]}"
    return f"ip:{get_remote_address(request)}"


def _storage_uri() -> str:
    if settings.redis_url and (
        settings.redis_url.startswith("redis://")
        or settings.redis_url.startswith("rediss://")
    ):
        try:
            import redis

            client = redis.from_url(settings.redis_url, socket_timeout=0.5)
            client.ping()
            return settings.redis_url
        except Exception as e:
            logger.info("Redis storage unreachable for rate limiter (%s), using memory://", e)
    return "memory://"


limiter = Limiter(
    key_func=_rate_limit_key,
    default_limits=[settings.rate_limit],
    storage_uri=_storage_uri(),
    headers_enabled=True,
)
