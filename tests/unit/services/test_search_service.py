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
