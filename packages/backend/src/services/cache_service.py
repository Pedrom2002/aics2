"""Redis caching service for expensive queries."""

import json
import logging

import redis.asyncio as aioredis

from src.config import settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def cache_get(key: str) -> dict | list | None:
    """Get a cached value. Returns None on miss or error."""
    try:
        r = await _get_redis()
        data = await r.get(f"cache:{key}")
        if data:
            return json.loads(data)
    except Exception as e:
        logger.debug("Cache get error for %s: %s", key, e)
    return None


async def cache_set(key: str, value: dict | list, ttl: int | None = None) -> None:
    """Set a cached value with optional TTL in seconds."""
    try:
        r = await _get_redis()
        ttl = ttl or settings.REDIS_CACHE_TTL
        await r.set(f"cache:{key}", json.dumps(value, default=str), ex=ttl)
    except Exception as e:
        logger.debug("Cache set error for %s: %s", key, e)


async def cache_invalidate(pattern: str) -> None:
    """Invalidate all keys matching a pattern."""
    try:
        r = await _get_redis()
        keys = []
        async for key in r.scan_iter(f"cache:{pattern}"):
            keys.append(key)
        if keys:
            await r.delete(*keys)
            logger.debug("Invalidated %d cache keys matching %s", len(keys), pattern)
    except Exception as e:
        logger.debug("Cache invalidate error for %s: %s", pattern, e)
