"""
Redis FAQ Cache — stores and retrieves analysis results by query hash.

Flow:
    1. Normalize query (lowercase, strip whitespace)
    2. SHA-256 hash → Redis key  "faq:<hash>"
    3. GET  → return cached JSON dict if exists
    4. SET  → store result JSON with configurable TTL

A cache miss returns None; caller runs the full workflow and then stores the result.
"""

import hashlib
import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


def _make_key(query: str) -> str:
    """Normalize query and return a stable Redis key."""
    normalized = query.strip().lower()
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    return f"faq:{digest}"


class RedisCache:
    def __init__(self) -> None:
        self._client: aioredis.Redis | None = None

    async def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            settings = get_settings()
            self._client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    async def get(self, query: str) -> dict[str, Any] | None:
        """Return cached result for the query, or None on cache miss."""
        settings = get_settings()
        if not settings.cache_enabled:
            return None
        try:
            client = await self._get_client()
            key = _make_key(query)
            raw = await client.get(key)
            if raw is None:
                return None
            logger.info("Cache HIT for key %s", key)
            return json.loads(raw)
        except Exception as exc:
            # Never let a cache error break the request
            logger.warning("Redis GET failed: %s", exc)
            return None

    async def set(self, query: str, result: dict[str, Any]) -> None:
        """Store result in Redis with TTL from settings."""
        settings = get_settings()
        if not settings.cache_enabled:
            return
        try:
            client = await self._get_client()
            key = _make_key(query)
            await client.setex(key, settings.cache_ttl_seconds, json.dumps(result))
            logger.info("Cache SET for key %s (TTL %ds)", key, settings.cache_ttl_seconds)
        except Exception as exc:
            logger.warning("Redis SET failed: %s", exc)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


# Module-level singleton — shared across requests
_cache = RedisCache()


async def get_cache() -> RedisCache:
    return _cache
