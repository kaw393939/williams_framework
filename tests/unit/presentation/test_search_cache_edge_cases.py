"""Edge case tests for SearchCache to achieve 100% coverage.

Tests for:
1. SearchCache with no redis_client (defensive None checks)
2. SearchCache with no embedder (error path)
3. Edge cases not covered by mock-based tests
"""
import pytest


@pytest.mark.asyncio
async def test_search_cache_get_returns_none_when_no_redis_client():
    """Test that get() returns None when redis_client is not configured."""
    from app.presentation.search_cache import SearchCache

    cache = SearchCache(redis_client=None)
    result = await cache.get("test query")

    assert result is None, "Should return None when redis_client is None"


@pytest.mark.asyncio
async def test_search_cache_set_no_op_when_no_redis_client():
    """Test that set() is a no-op when redis_client is not configured."""
    from app.presentation.search_cache import SearchCache

    cache = SearchCache(redis_client=None)
    # Should not raise an error, just be a no-op
    await cache.set("test query", [0.1, 0.2, 0.3])


@pytest.mark.asyncio
async def test_search_cache_get_or_compute_raises_when_no_embedder():
    """Test that get_or_compute raises ValueError on cache miss with no embedder."""
    from unittest.mock import AsyncMock

    from app.presentation.search_cache import SearchCache

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # Force cache miss

    cache = SearchCache(redis_client=mock_redis, embedder=None)

    with pytest.raises(ValueError, match="Embedder required"):
        await cache.get_or_compute("test query")
