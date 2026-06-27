"""
Optional Redis-backed cache.

The cache is best-effort: if Redis is unavailable the application keeps working,
it simply skips caching. This keeps the service resilient and easy to run
without Redis during local development.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[redis.Redis] = None


async def get_redis() -> Optional[redis.Redis]:
    """Return a shared async Redis client, or ``None`` if unavailable."""
    global _client
    if _client is None:
        try:
            _client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
            )
            await _client.ping()
            logger.info("Connected to Redis cache")
        except Exception as exc:  # noqa: BLE001 - cache is optional
            logger.warning("Redis unavailable, caching disabled: %s", exc)
            _client = None
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        finally:
            _client = None


def make_cache_key(prefix: str, payload: dict[str, Any]) -> str:
    """Build a deterministic cache key from a JSON-serialisable payload."""
    blob = json.dumps(payload, sort_keys=True, default=str)
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return f"seccopilot:{prefix}:{digest}"


async def cache_get(key: str) -> Optional[Any]:
    client = await get_redis()
    if client is None:
        return None
    try:
        raw = await client.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cache get failed: %s", exc)
        return None


async def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    client = await get_redis()
    if client is None:
        return
    try:
        await client.set(
            key,
            json.dumps(value, default=str),
            ex=ttl or settings.cache_ttl_seconds,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cache set failed: %s", exc)
