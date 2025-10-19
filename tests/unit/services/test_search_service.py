"""RED TESTS FOR S4-501: Real-time vector search with Qdrant.

These tests verify that:
1. SearchService performs embedding-based semantic search
2. Results are ranked by relevance score (similarity)
3. Top-K filtering returns only the most relevant results
4. Integration with SearchCache for embedding reuse
5. Error handling for empty queries and no results
"""
from unittest.mock import AsyncMock, Mock

import pytest


@pytest.mark.unit
def test_search_service_has_search_method():
    """Test that SearchService exposes search method."""
    from app.services.search_service import SearchService

    service = SearchService()

    assert hasattr(service, "search")
    assert callable(service.search)


@pytest.mark.asyncio
async def test_search_service_returns_ranked_results():
    """Test that search returns results ranked by relevance score."""
    from app.services.search_service import SearchService

    mock_qdrant = AsyncMock()
    mock_qdrant.search.return_value = [
        {
            "id": "1",
            "score": 0.95,
            "payload": {
                "title": "Result 1",
                "summary": "Summary 1",
                "file_path": "/test1.md",
                "url": "https://example.com",
                "tier": "tier-a",
                "quality_score": 9.0,
                "tags": []
            }
        },
        {
            "id": "2",
            "score": 0.85,
            "payload": {
                "title": "Result 2",
                "summary": "Summary 2",
                "file_path": "/test2.md",
                "url": "https://example.com",
                "tier": "tier-b",
                "quality_score": 8.0,
                "tags": []
            }
        },
        {
            "id": "3",
            "score": 0.75,
            "payload": {
                "title": "Result 3",
                "summary": "Summary 3",
                "file_path": "/test3.md",
                "url": "https://example.com",
                "tier": "tier-b",
                "quality_score": 7.0,
                "tags": []
            }
        },
    ]

    mock_embedder = Mock()
    mock_embedder.embed.return_value = [0.1, 0.2, 0.3]

    service = SearchService(qdrant_client=mock_qdrant, embedder=mock_embedder)
    results = await service.search("test query", top_k=3)

    assert len(results) == 3
    assert results[0].relevance_score >= results[1].relevance_score
    assert results[1].relevance_score >= results[2].relevance_score


@pytest.mark.asyncio
async def test_search_service_respects_top_k_limit():
    """Test that search returns only top-K results."""
    from app.services.search_service import SearchService

    # Create a function that respects the limit parameter
    all_results = [
        {
            "id": str(i),
            "score": 1.0 - (i * 0.1),
            "payload": {
                "title": f"Result {i}",
                "summary": f"Summary {i}",
                "file_path": f"/test{i}.md",
                "url": "https://example.com",
                "tier": "tier-a",
                "quality_score": 9.0,
                "tags": []
            }
        }
        for i in range(10)
    ]

    mock_qdrant = AsyncMock()
    # Make the mock respect the limit parameter
    mock_qdrant.search.side_effect = lambda query_vector, limit: all_results[:limit]

    mock_embedder = Mock()
    mock_embedder.embed.return_value = [0.1, 0.2, 0.3]

    service = SearchService(qdrant_client=mock_qdrant, embedder=mock_embedder)
    results = await service.search("test query", top_k=5)

    assert len(results) == 5


@pytest.mark.asyncio
async def test_search_service_uses_cache_for_embeddings():
    """Test that search uses SearchCache to avoid recomputing embeddings."""
    from app.services.search_service import SearchService

    mock_cache = AsyncMock()
    mock_cache.get_or_compute.return_value = [0.1, 0.2, 0.3]

    mock_qdrant = AsyncMock()
    mock_qdrant.search.return_value = []

    service = SearchService(qdrant_client=mock_qdrant, search_cache=mock_cache)
    await service.search("test query", top_k=5)

    mock_cache.get_or_compute.assert_called_once_with("test query")


@pytest.mark.asyncio
async def test_search_service_returns_empty_for_no_results():
    """Test that search returns empty list when no results found."""
    from app.services.search_service import SearchService

    mock_qdrant = AsyncMock()
    mock_qdrant.search.return_value = []

    mock_embedder = Mock()
    mock_embedder.embed.return_value = [0.1, 0.2, 0.3]

    service = SearchService(qdrant_client=mock_qdrant, embedder=mock_embedder)
    results = await service.search("nonexistent query", top_k=5)

    assert results == []


@pytest.mark.asyncio
async def test_search_service_validates_empty_query():
    """Test that search handles empty query string."""
    from app.services.search_service import SearchService

    service = SearchService()
    results = await service.search("", top_k=5)

    assert results == []


@pytest.mark.asyncio
async def test_search_result_contains_required_fields():
    """Test that SearchResult model has required fields."""
    from app.core.models import SearchResult

    result = SearchResult(
        file_path="/library/tier-a/test.md",
        url="https://example.com",
        title="Test Title",
        summary="Test summary",
        tags=["test"],
        tier="tier-a",
        quality_score=9.5,
        relevance_score=0.95
    )

    assert result.file_path == "/library/tier-a/test.md"
    assert result.title == "Test Title"
    assert result.relevance_score == 0.95
    assert result.tier == "tier-a"


@pytest.mark.integration
async def test_search_service_with_qdrant_repository():
    """Test search service integrates with QdrantRepository."""
    from app.services.search_service import SearchService

    mock_qdrant_repo = AsyncMock()
    mock_qdrant_repo.search_by_vector.return_value = [
        {
            "id": "1",
            "score": 0.9,
            "payload": {
                "title": "Test",
                "summary": "Summary",
                "file_path": "/test.md",
                "tier": "tier-a",
                "tags": ["test"],
                "url": "https://example.com",
                "quality_score": 9.0
            }
        }
    ]

    mock_embedder = Mock()
    mock_embedder.embed.return_value = [0.1] * 384

    service = SearchService(qdrant_repository=mock_qdrant_repo, embedder=mock_embedder)
    results = await service.search("test query", top_k=5)

    assert len(results) == 1
    assert results[0].relevance_score == 0.9


@pytest.mark.integration
async def test_search_service_filters_by_minimum_score():
    """Test that search can filter results by minimum relevance score."""
    from app.services.search_service import SearchService

    mock_qdrant = AsyncMock()
    mock_qdrant.search.return_value = [
        {
            "id": "1",
            "score": 0.95,
            "payload": {
                "title": "High relevance",
                "summary": "Summary",
                "file_path": "/test1.md",
                "url": "https://example.com",
                "tier": "tier-a",
                "quality_score": 9.0,
                "tags": []
            }
        },
        {
            "id": "2",
            "score": 0.50,
            "payload": {
                "title": "Low relevance",
                "summary": "Summary",
                "file_path": "/test2.md",
                "url": "https://example.com",
                "tier": "tier-b",
                "quality_score": 7.0,
                "tags": []
            }
        },
        {
            "id": "3",
            "score": 0.30,
            "payload": {
                "title": "Very low",
                "summary": "Summary",
                "file_path": "/test3.md",
                "url": "https://example.com",
                "tier": "tier-c",
                "quality_score": 5.0,
                "tags": []
            }
        },
    ]

    mock_embedder = Mock()
    mock_embedder.embed.return_value = [0.1, 0.2, 0.3]

    service = SearchService(qdrant_client=mock_qdrant, embedder=mock_embedder)
    results = await service.search("test query", top_k=10, min_score=0.6)

    assert len(results) == 1
    assert results[0].relevance_score >= 0.6


@pytest.mark.unit
def test_query_with_citations_basic():
    """Test basic RAG query with citations."""
    from app.services.search_service import SearchService
    
    mock_neo_repo = Mock()
    mock_citation_service = Mock()
    
    # Mock chunks
    mock_neo_repo.execute_query.return_value = [
        {"id": "chunk1", "text": "AI is a field of computer science", "url": "test.com"},
        {"id": "chunk2", "text": "Machine learning is a subset of AI", "url": "test.com"}
    ]
    
    # Mock citation creation
    mock_citation_service.create_citation.side_effect = [
        {"citation_id": "[1]", "citation_number": 1, "quote_text": "AI is a field of computer science"},
        {"citation_id": "[2]", "citation_number": 2, "quote_text": "Machine learning is a subset of AI"}
    ]
    
    service = SearchService(
        neo_repo=mock_neo_repo,
        citation_service=mock_citation_service
    )
    
    result = service.query_with_citations("What is AI?", max_citations=2)
    
    assert "answer" in result
    assert len(result["citations"]) == 2
    assert result["total_count"] == 2
    assert result["citations"][0]["citation_id"] == "[1]"


@pytest.mark.unit
def test_query_with_citations_pagination_mismatch():
    """Test that demonstrates the pagination bug with citation references.
    
    BUG: When paginating citations, the answer references ALL citations
    but only a subset is returned. This causes citation numbers to mismatch.
    """
    from app.services.search_service import SearchService
    
    mock_neo_repo = Mock()
    mock_citation_service = Mock()
    mock_llm_provider = Mock()
    
    # Mock 10 chunks
    mock_neo_repo.execute_query.return_value = [
        {"id": f"chunk{i}", "text": f"Content {i}", "url": "test.com"}
        for i in range(1, 11)
    ]
    
    # Mock citation creation - creates citations [1] through [10]
    mock_citation_service.create_citation.side_effect = [
        {
            "citation_id": f"[{i}]",
            "citation_number": i,
            "quote_text": f"Content {i}"
        }
        for i in range(1, 11)
    ]
    
    # LLM generates answer referencing citations [1], [2], [3]
    mock_llm_provider.generate.return_value = "According to [1], [2], and [3], AI is important."
    
    service = SearchService(
        neo_repo=mock_neo_repo,
        citation_service=mock_citation_service,
        llm_provider=mock_llm_provider
    )
    
    # Request page 2 with page_size=5 (should return citations 6-10)
    result = service.query_with_citations(
        "What is AI?",
        max_citations=10,
        page=2,
        page_size=5
    )
    
    # BUG DEMONSTRATION:
    # Answer mentions [1], [2], [3]
    assert "[1]" in result["answer"]
    assert "[2]" in result["answer"]
    assert "[3]" in result["answer"]
    
    # But paginated citations start at [6]!
    # This is the bug - citation numbers don't match
    assert len(result["citations"]) == 5
    assert result["citations"][0]["citation_number"] == 6  # Should be 6, not 1
    
    # User sees answer referencing [1], [2], [3]
    # But citations shown are [6], [7], [8], [9], [10]
    # Citations [1], [2], [3] are NOT in the result!


@pytest.mark.unit
def test_query_with_citations_with_llm():
    """Test RAG query generates answer with LLM."""
    from app.services.search_service import SearchService
    
    mock_neo_repo = Mock()
    mock_citation_service = Mock()
    mock_llm_provider = Mock()
    
    mock_neo_repo.execute_query.return_value = [
        {"id": "chunk1", "text": "ML is AI", "url": "test.com"}
    ]
    
    mock_citation_service.create_citation.return_value = {
        "citation_id": "[1]",
        "quote_text": "ML is AI"
    }
    
    mock_llm_provider.generate.return_value = "Machine learning is AI [1]."
    
    service = SearchService(
        neo_repo=mock_neo_repo,
        citation_service=mock_citation_service,
        llm_provider=mock_llm_provider
    )
    
    result = service.query_with_citations("What is ML?")
    
    # Should use LLM
    mock_llm_provider.generate.assert_called_once()
    assert result["answer"] == "Machine learning is AI [1]."
    assert "Question: What is ML?" in mock_llm_provider.generate.call_args[0][0]


@pytest.mark.unit
def test_query_with_citations_without_llm():
    """Test RAG query without LLM generates fallback answer."""
    from app.services.search_service import SearchService
    
    mock_neo_repo = Mock()
    mock_citation_service = Mock()
    
    mock_neo_repo.execute_query.return_value = [
        {"id": "chunk1", "text": "Test", "url": "test.com"}
    ]
    
    mock_citation_service.create_citation.return_value = {
        "citation_id": "[1]",
        "quote_text": "Test"
    }
    
    service = SearchService(
        neo_repo=mock_neo_repo,
        citation_service=mock_citation_service
        # No LLM provider
    )
    
    result = service.query_with_citations("test query")
    
    assert "Found" in result["answer"]
    assert "relevant sources" in result["answer"]


@pytest.mark.unit
def test_query_with_citations_no_services():
    """Test query_with_citations without required services."""
    from app.services.search_service import SearchService
    
    service = SearchService()  # No neo_repo or citation_service
    
    result = service.query_with_citations("test")
    
    assert "not properly configured" in result["answer"]
    assert result["citations"] == []
    assert result["total_count"] == 0


@pytest.mark.unit
def test_get_relevant_chunks():
    """Test _get_relevant_chunks queries Neo4j."""
    from app.services.search_service import SearchService
    
    mock_neo_repo = Mock()
    mock_neo_repo.execute_query.return_value = [
        {"id": "chunk1", "text": "Test content", "url": "example.com"}
    ]
    
    service = SearchService(neo_repo=mock_neo_repo)
    
    chunks = service._get_relevant_chunks("test query", limit=5)
    
    assert len(chunks) == 1
    assert chunks[0]["id"] == "chunk1"
    
    # Verify limit was passed
    call_args = mock_neo_repo.execute_query.call_args
    assert call_args[0][1]["limit"] == 5


@pytest.mark.unit
def test_get_relevant_chunks_no_neo_repo():
    """Test _get_relevant_chunks without Neo4j repo."""
    from app.services.search_service import SearchService
    
    service = SearchService()
    
    chunks = service._get_relevant_chunks("test")
    
    assert chunks == []
