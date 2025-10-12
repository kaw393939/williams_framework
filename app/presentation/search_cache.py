"""Search caching with Redis for embedding storage and telemetry.

This module provides caching for search query embeddings to avoid
recomputing expensive embedding operations. Cache hits and misses
are tracked via telemetry for observability.
"""
import hashlib
import json
from typing import Any

from app.core.telemetry import TelemetryService


class SearchCache:
    """Cache for search query embeddings with Redis storage.

    This component provides:
    - Deterministic cache keys from query text
    - Serialization/deserialization of embeddings
    - TTL-based expiration
    - Telemetry integration for cache metrics

    Example:
        >>> cache = SearchCache(redis_client=redis, embedder=embedder)
        >>> embedding = await cache.get_or_compute("python programming")
    """

    def __init__(
        self,
        redis_client: Any | None = None,
        embedder: Any | None = None,
        telemetry: TelemetryService | None = None,
        ttl_seconds: int = 3600
    ):
        """Initialize search cache.

        Args:
            redis_client: Redis client for storage (optional for testing)
            embedder: Embedding generator (optional for testing)
            telemetry: Telemetry service for tracking metrics
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.redis_client = redis_client
        self.embedder = embedder
        self.telemetry = telemetry
        self.ttl_seconds = ttl_seconds

    def get_cache_key(self, query: str) -> str:
        """Generate deterministic cache key from query text.

        Uses SHA-256 hash of query text to create consistent keys.

        Args:
            query: Search query text

        Returns:
            Cache key string with "search:" prefix
        """
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        return f"search:{query_hash}"

    async def get(self, query: str) -> list[float] | None:
        """Get cached embedding for query.

        Args:
            query: Search query text

        Returns:
            Cached embedding list or None if not found
        """
        if self.redis_client is None:
            return None

        cache_key = self.get_cache_key(query)
        cached_value = await self.redis_client.get(cache_key)

        if cached_value is None:
            return None

        return json.loads(cached_value)

    async def set(self, query: str, embedding: list[float]) -> None:
        """Store embedding in cache with TTL.

        Args:
            query: Search query text
            embedding: Embedding vector to cache
        """
        if self.redis_client is None:
            return

        cache_key = self.get_cache_key(query)
        serialized = json.dumps(embedding)
        await self.redis_client.set(cache_key, serialized, ex=self.ttl_seconds)

    async def get_or_compute(self, query: str) -> list[float]:
        """Get cached embedding or compute and cache it.

        This method implements the cache-aside pattern:
        1. Try to get from cache
        2. On cache hit: return cached value and track telemetry
        3. On cache miss: compute embedding, store in cache, track telemetry

        Args:
            query: Search query text

        Returns:
            Embedding vector (from cache or newly computed)
        """
        # Try cache first
        cached_embedding = await self.get(query)

        if cached_embedding is not None:
            # Cache hit
            if self.telemetry:
                self.telemetry.track_cache_hit("search_embedding", {"query": query})
            return cached_embedding

        # Cache miss - compute embedding
        if self.embedder is None:
            raise ValueError("Embedder required for cache miss computation")

        embedding = self.embedder.embed(query)

        # Store in cache
        await self.set(query, embedding)

        # Track telemetry
        if self.telemetry:
            self.telemetry.track_cache_miss("search_embedding", {"query": query})

        return embedding
