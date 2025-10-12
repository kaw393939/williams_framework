"""RED TESTS FOR S3-403: Search caching and telemetry.

These tests verify that:
1. Search queries cache embeddings in Redis
2. Cache hits return cached results without re-computing embeddings
3. Cache misses compute embeddings and store them
4. Telemetry tracks cache hits and misses
"""
from unittest.mock import AsyncMock, Mock

import pytest


@pytest.mark.unit
def test_search_cache_key_uses_query_text():
    """Test that cache key is derived from query text."""
    from app.presentation.search_cache import SearchCache

    cache = SearchCache()
    key1 = cache.get_cache_key("python programming")
    key2 = cache.get_cache_key("python programming")
    key3 = cache.get_cache_key("java programming")

    assert key1 == key2, "Same query should generate same key"
    assert key1 != key3, "Different queries should generate different keys"


@pytest.mark.unit
def test_search_cache_key_is_deterministic():
    """Test that cache keys are deterministic for same query."""
    from app.presentation.search_cache import SearchCache

    cache = SearchCache()
    key = cache.get_cache_key("test query")

    assert isinstance(key, str)
    assert len(key) > 0
    assert key.startswith("search:")


@pytest.mark.asyncio
async def test_search_cache_get_returns_none_on_miss():
    """Test that cache get returns None when key not found."""
    from app.presentation.search_cache import SearchCache

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    cache = SearchCache(redis_client=mock_redis)
    result = await cache.get("test query")

    assert result is None
    mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_search_cache_get_deserializes_embedding():
    """Test that cache get deserializes embedding from Redis."""
    import json

    from app.presentation.search_cache import SearchCache

    mock_embedding = [0.1, 0.2, 0.3]
    mock_redis = AsyncMock()
    mock_redis.get.return_value = json.dumps(mock_embedding)

    cache = SearchCache(redis_client=mock_redis)
    result = await cache.get("test query")

    assert result == mock_embedding
    mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_search_cache_set_serializes_embedding():
    """Test that cache set serializes embedding to Redis."""
    import json

    from app.presentation.search_cache import SearchCache

    mock_embedding = [0.1, 0.2, 0.3]
    mock_redis = AsyncMock()

    cache = SearchCache(redis_client=mock_redis)
    await cache.set("test query", mock_embedding)

    mock_redis.set.assert_called_once()
    call_args = mock_redis.set.call_args
    assert call_args[0][0].startswith("search:")
    assert json.loads(call_args[0][1]) == mock_embedding


@pytest.mark.asyncio
async def test_search_cache_set_with_ttl():
    """Test that cache set uses TTL for expiration."""
    from app.presentation.search_cache import SearchCache

    mock_embedding = [0.1, 0.2, 0.3]
    mock_redis = AsyncMock()

    cache = SearchCache(redis_client=mock_redis, ttl_seconds=3600)
    await cache.set("test query", mock_embedding)

    call_args = mock_redis.set.call_args
    assert call_args[1]["ex"] == 3600


@pytest.mark.asyncio
async def test_search_with_cache_hit_returns_cached_embedding():
    """Test that search with cache hit returns cached embedding without computing."""
    import json

    from app.presentation.search_cache import SearchCache

    mock_embedding = [0.1, 0.2, 0.3]
    mock_redis = AsyncMock()
    mock_redis.get.return_value = json.dumps(mock_embedding)

    mock_embedder = Mock()
    mock_telemetry = Mock()

    cache = SearchCache(
        redis_client=mock_redis,
        embedder=mock_embedder,
        telemetry=mock_telemetry
    )

    result = await cache.get_or_compute("test query")

    assert result == mock_embedding
    mock_embedder.embed.assert_not_called()
    mock_telemetry.track_cache_hit.assert_called_once()


@pytest.mark.asyncio
async def test_search_with_cache_miss_computes_and_stores():
    """Test that search with cache miss computes embedding and stores it."""
    from app.presentation.search_cache import SearchCache

    mock_embedding = [0.1, 0.2, 0.3]
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    mock_embedder = Mock()
    mock_embedder.embed.return_value = mock_embedding

    mock_telemetry = Mock()

    cache = SearchCache(
        redis_client=mock_redis,
        embedder=mock_embedder,
        telemetry=mock_telemetry
    )

    result = await cache.get_or_compute("test query")

    assert result == mock_embedding
    mock_embedder.embed.assert_called_once_with("test query")
    mock_redis.set.assert_called_once()
    mock_telemetry.track_cache_miss.assert_called_once()


@pytest.mark.integration
async def test_search_cache_telemetry_tracks_cache_metrics():
    """Test that telemetry tracks cache hit/miss events."""
    from app.core.telemetry import TelemetryService
    from app.presentation.search_cache import SearchCache

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    mock_embedder = Mock()
    mock_embedder.embed.return_value = [0.1, 0.2, 0.3]

    telemetry = TelemetryService()

    cache = SearchCache(
        redis_client=mock_redis,
        embedder=mock_embedder,
        telemetry=telemetry
    )

    await cache.get_or_compute("test query")

    # Verify telemetry event was logged
    events = telemetry.get_events()
    assert len(events) > 0
    assert events[-1]["event_type"] == "cache_miss"
