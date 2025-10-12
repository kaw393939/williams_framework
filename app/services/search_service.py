"""Search service for semantic search using Qdrant vector similarity.

This module provides real-time semantic search capabilities using
embedding-based retrieval, ranked results, and top-K filtering.
"""
import logging
from typing import Optional

from app.core.models import SearchResult

logger = logging.getLogger(__name__)


class SearchService:
    """Service for semantic search of library content.

    This service provides:
    - Embedding-based semantic search using Qdrant
    - Ranked results by relevance score (cosine similarity)
    - Top-K filtering for most relevant results
    - Integration with SearchCache for embedding reuse
    - Minimum score filtering

    Example:
        >>> search_service = SearchService(qdrant_repository=repo, embedder=embedder)
        >>> results = await search_service.search("machine learning", top_k=5)
    """

    def __init__(
        self,
        qdrant_client: Optional[any] = None,
        qdrant_repository: Optional[any] = None,
        embedder: Optional[any] = None,
        search_cache: Optional[any] = None
    ):
        """Initialize search service.

        Args:
            qdrant_client: Direct Qdrant client (for testing)
            qdrant_repository: QdrantRepository instance
            embedder: Embedding service for query vectorization
            search_cache: SearchCache for embedding reuse
        """
        self.qdrant_client = qdrant_client
        self.qdrant_repository = qdrant_repository
        self.embedder = embedder
        self.search_cache = search_cache

    async def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0
    ) -> list[SearchResult]:
        """Perform semantic search on library content.

        Args:
            query: Search query text
            top_k: Maximum number of results to return
            min_score: Minimum relevance score (0.0-1.0)

        Returns:
            List of SearchResult objects ranked by relevance score
        """
        # Validate query
        if not query or not query.strip():
            logger.warning("Empty query provided to search")
            return []

        # Get query embedding (using cache if available)
        if self.search_cache:
            query_embedding = await self.search_cache.get_or_compute(query)
        elif self.embedder:
            query_embedding = self.embedder.embed(query)
        else:
            logger.error("No embedder or cache available for search")
            return []

        # Perform vector search
        if self.qdrant_client:
            raw_results = await self.qdrant_client.search(
                query_vector=query_embedding,
                limit=top_k
            )
        elif self.qdrant_repository:
            raw_results = await self.qdrant_repository.search_by_vector(
                query_vector=query_embedding,
                top_k=top_k
            )
        else:
            logger.error("No Qdrant client or repository available for search")
            return []

        # Convert raw results to SearchResult models
        search_results = []
        for raw_result in raw_results:
            # Extract score and payload
            if isinstance(raw_result, dict):
                score = raw_result.get("score", 0.0)
                payload = raw_result.get("payload", {})
            else:
                score = getattr(raw_result, "score", 0.0)
                payload = getattr(raw_result, "payload", {})

            # Apply minimum score filter
            if score < min_score:
                continue

            # Create SearchResult
            try:
                result = SearchResult(
                    file_path=payload.get("file_path", ""),
                    url=payload.get("url", ""),
                    title=payload.get("title", ""),
                    summary=payload.get("summary", ""),
                    tags=payload.get("tags", []),
                    tier=payload.get("tier", ""),
                    quality_score=payload.get("quality_score", 0.0),
                    relevance_score=score,
                    matched_content=payload.get("matched_content")
                )
                search_results.append(result)
            except Exception as e:
                logger.error(f"Failed to create SearchResult: {e}")
                continue

        # Results are already sorted by score from Qdrant (descending)
        return search_results
