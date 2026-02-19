"""Redis cache layer with decorator support."""

import functools
import json
import hashlib
from typing import Any, Callable, Optional

import redis.asyncio as redis
from config import settings
from utils.logger import logger


class CacheManager:
    """Async Redis cache manager."""

    def __init__(self):
        """Initialize cache manager."""
        self._redis: Optional[redis.Redis] = None
        self._enabled = True

    async def connect(self):
        """Connect to Redis."""
        try:
            self._redis = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            # Test connection
            await self._redis.ping()
            logger.info("Redis cache connected", host=settings.REDIS_HOST)
        except Exception as exc:
            logger.warning(
                "Redis unavailable, caching disabled",
                error=str(exc),
            )
            self._enabled = False
            self._redis = None

    async def disconnect(self):
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            logger.info("Redis cache disconnected")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self._enabled or not self._redis:
            return None

        try:
            value = await self._redis.get(key)
            if value:
                logger.debug("Cache hit", key=key)
                return json.loads(value)
            logger.debug("Cache miss", key=key)
            return None
        except Exception as exc:
            logger.error("Cache get failed", key=key, error=str(exc))
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 600,  # 10 minutes default
    ) -> bool:
        """Set value in cache with TTL."""
        if not self._enabled or not self._redis:
            return False

        try:
            serialized = json.dumps(value, default=str)
            await self._redis.setex(key, ttl, serialized)
            logger.debug("Cache set", key=key, ttl=ttl)
            return True
        except Exception as exc:
            logger.error("Cache set failed", key=key, error=str(exc))
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self._enabled or not self._redis:
            return False

        try:
            await self._redis.delete(key)
            logger.debug("Cache delete", key=key)
            return True
        except Exception as exc:
            logger.error("Cache delete failed", key=key, error=str(exc))
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        if not self._enabled or not self._redis:
            return 0

        try:
            keys = await self._redis.keys(pattern)
            if keys:
                deleted = await self._redis.delete(*keys)
                logger.info("Cache pattern deleted", pattern=pattern, count=deleted)
                return deleted
            return 0
        except Exception as exc:
            logger.error("Cache pattern delete failed", pattern=pattern, error=str(exc))
            return 0

    async def clear(self) -> bool:
        """Clear all cache."""
        if not self._enabled or not self._redis:
            return False

        try:
            await self._redis.flushdb()
            logger.warning("Cache cleared (all keys deleted)")
            return True
        except Exception as exc:
            logger.error("Cache clear failed", error=str(exc))
            return False


# Global cache instance
cache = CacheManager()


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate cache key from function arguments."""
    # Create unique key from args and kwargs
    key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
    key_hash = hashlib.md5(key_data.encode()).hexdigest()
    return f"{prefix}:{key_hash}"


def cached(
    ttl: int = 600,
    key_prefix: Optional[str] = None,
):
    """
    Cache decorator for async functions.
    
    Args:
        ttl: Time to live in seconds (default 600 = 10 min)
        key_prefix: Custom key prefix (default: function name)
    
    Example:
        @cached(ttl=300, key_prefix="products")
        async def get_products(category: str):
            return await db.query(...)
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            prefix = key_prefix or func.__name__
            cache_key = generate_cache_key(prefix, *args, **kwargs)

            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            await cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


async def invalidate_cache(pattern: str):
    """
    Invalidate cache by pattern.
    
    Example:
        await invalidate_cache("products:*")
    """
    return await cache.delete_pattern(pattern)
