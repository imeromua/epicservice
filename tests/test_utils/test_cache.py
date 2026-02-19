"""Tests for Redis cache."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from utils.cache import CacheManager, cached, generate_cache_key, invalidate_cache


@pytest.fixture
async def mock_redis():
    """Mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.keys = AsyncMock(return_value=[])
    redis_mock.flushdb = AsyncMock(return_value=True)
    redis_mock.close = AsyncMock()
    return redis_mock


@pytest.fixture
async def cache_manager(mock_redis):
    """Cache manager with mocked Redis."""
    cache = CacheManager()
    cache._redis = mock_redis
    cache._enabled = True
    return cache


@pytest.mark.asyncio
async def test_cache_get_hit(cache_manager, mock_redis):
    """Test cache hit."""
    mock_redis.get.return_value = '{"result": "cached"}'
    
    value = await cache_manager.get("test_key")
    
    assert value == {"result": "cached"}
    mock_redis.get.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_cache_get_miss(cache_manager, mock_redis):
    """Test cache miss."""
    mock_redis.get.return_value = None
    
    value = await cache_manager.get("test_key")
    
    assert value is None
    mock_redis.get.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_cache_set(cache_manager, mock_redis):
    """Test cache set."""
    result = await cache_manager.set("test_key", {"data": "value"}, ttl=300)
    
    assert result is True
    mock_redis.setex.assert_called_once()
    args = mock_redis.setex.call_args[0]
    assert args[0] == "test_key"
    assert args[1] == 300


@pytest.mark.asyncio
async def test_cache_delete(cache_manager, mock_redis):
    """Test cache delete."""
    result = await cache_manager.delete("test_key")
    
    assert result is True
    mock_redis.delete.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_cache_delete_pattern(cache_manager, mock_redis):
    """Test cache delete by pattern."""
    mock_redis.keys.return_value = ["key1", "key2", "key3"]
    mock_redis.delete.return_value = 3
    
    count = await cache_manager.delete_pattern("test:*")
    
    assert count == 3
    mock_redis.keys.assert_called_once_with("test:*")
    mock_redis.delete.assert_called_once_with("key1", "key2", "key3")


@pytest.mark.asyncio
async def test_cache_disabled():
    """Test cache when disabled."""
    cache = CacheManager()
    cache._enabled = False
    
    # All operations should return None/False
    assert await cache.get("key") is None
    assert await cache.set("key", "value") is False
    assert await cache.delete("key") is False
    assert await cache.delete_pattern("*") == 0


def test_generate_cache_key():
    """Test cache key generation."""
    key1 = generate_cache_key("test", "arg1", "arg2", kwarg1="value1")
    key2 = generate_cache_key("test", "arg1", "arg2", kwarg1="value1")
    key3 = generate_cache_key("test", "arg1", "arg2", kwarg1="value2")
    
    # Same arguments = same key
    assert key1 == key2
    
    # Different arguments = different key
    assert key1 != key3
    
    # Key format
    assert key1.startswith("test:")


@pytest.mark.asyncio
async def test_cached_decorator():
    """Test @cached decorator."""
    call_count = 0
    
    @cached(ttl=60, key_prefix="test_func")
    async def expensive_function(arg):
        nonlocal call_count
        call_count += 1
        return {"result": arg}
    
    # Mock cache
    with patch("utils.cache.cache") as mock_cache:
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(return_value=True)
        
        # First call - cache miss
        result1 = await expensive_function("test")
        assert result1 == {"result": "test"}
        assert call_count == 1
        
        # Second call - cache hit
        mock_cache.get.return_value = {"result": "test"}
        result2 = await expensive_function("test")
        assert result2 == {"result": "test"}
        assert call_count == 1  # Not called again
