"""Search service for semantic search using Qdrant vector similarity.

This module provides real-time semantic search capabilities using
embedding-based retrieval, ranked results, and top-K filtering.
"""
import logging
from typing import Any

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
        qdrant_client: Any | None = None,
        qdrant_repository: Any | None = None,
        embedder: Any | None = None,
        search_cache: Any | None = None,
        neo_repo: Any | None = None,
        citation_service: Any | None = None,
        llm_provider: Any | None = None
    ):
        """Initialize search service.

        Args:
            qdrant_client: Direct Qdrant client (for testing)
            qdrant_repository: QdrantRepository instance
            embedder: Embedding service for query vectorization
            search_cache: SearchCache for embedding reuse
            neo_repo: Neo4j repository for chunk retrieval
            citation_service: CitationService for citation management
            llm_provider: LLM provider for answer generation
        """
        self.qdrant_client = qdrant_client
        self.qdrant_repository = qdrant_repository
        self.embedder = embedder
        self.search_cache = search_cache
        self.neo_repo = neo_repo
        self.citation_service = citation_service
        self.llm_provider = llm_provider

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

    def query_with_citations(
        self,
        query: str,
        max_citations: int = 5,
        page: int = 1,
        page_size: int = 10,
        min_relevance: float = 0.0
    ) -> dict:
        """Perform RAG query with citations.
        
        Args:
            query: User query
            max_citations: Maximum number of citations to include
            page: Page number for pagination
            page_size: Results per page
            min_relevance: Minimum relevance score
            
        Returns:
            Dictionary with answer, citations, and pagination info
        """
        if not self.neo_repo or not self.citation_service:
            logger.error("Neo4j or CitationService not configured")
            return {
                "answer": "Service not properly configured",
                "citations": [],
                "total_count": 0
            }
        
        # Get relevant chunks from Neo4j
        # For now, use a simple query - in production, use vector search
        chunks = self._get_relevant_chunks(query, max_citations)
        
        # Create citations
        citations = []
        for i, chunk in enumerate(chunks[:max_citations], 1):
            citation = self.citation_service.create_citation(
                chunk_id=chunk["id"],
                quote_text=chunk["text"],
                citation_number=i
            )
            citation["relevance_score"] = chunk.get("relevance_score", 0.8)
            citations.append(citation)
        
        # Generate answer with LLM if available
        if self.llm_provider:
            # Build context from chunks
            context = "\n\n".join([
                f"[{i+1}] {chunk['text']}"
                for i, chunk in enumerate(chunks[:max_citations])
            ])
            
            prompt = f"""Answer the following question using the provided sources. 
Include citations like [1], [2], [3] in your answer.

Question: {query}

Sources:
{context}

Answer:"""
            
            answer = self.llm_provider.generate(prompt)
        else:
            answer = f"Found {len(citations)} relevant sources for: {query}"
        
        # Pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_citations = citations[start_idx:end_idx]
        
        return {
            "answer": answer,
            "citations": paginated_citations,
            "total_count": len(citations),
            "page": page,
            "page_size": page_size
        }
    
    def _get_relevant_chunks(self, query: str, limit: int = 10) -> list[dict]:
        """Get relevant chunks for a query.
        
        Args:
            query: Search query
            limit: Maximum chunks to return
            
        Returns:
            List of chunk dictionaries
        """
        if not self.neo_repo:
            return []
        
        # Simple query to get recent chunks - in production, use vector search
        cypher_query = """
        MATCH (c:Chunk)-[:PART_OF]->(d:Document)
        RETURN c.id as id, c.text as text, d.url as url
        ORDER BY c.created_at DESC
        LIMIT $limit
        """
        
        results = self.neo_repo.execute_query(cypher_query, {"limit": limit})
        return [dict(r) for r in results]
