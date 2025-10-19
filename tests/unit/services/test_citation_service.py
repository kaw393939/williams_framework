"""Unit tests for CitationService."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from app.services.citation_service import CitationService


@pytest.fixture
def mock_neo_repo():
    """Create mock Neo4j repository."""
    return Mock()


@pytest.fixture
def citation_service(mock_neo_repo):
    """Create CitationService instance."""
    return CitationService(mock_neo_repo)


def test_citation_service_initialization(mock_neo_repo):
    """Test CitationService initializes correctly."""
    service = CitationService(mock_neo_repo)
    assert service._neo_repo == mock_neo_repo
    assert isinstance(service._citation_cache, dict)
    assert len(service._citation_cache) == 0


def test_create_citation_success(citation_service, mock_neo_repo):
    """Test creating a citation with full metadata."""
    # Setup mock data
    mock_chunk = {
        "id": "chunk123",
        "doc_id": "doc456",
        "content": "Test content"
    }
    mock_doc = {
        "url": "https://example.com/doc",
        "title": "Test Document",
        "metadata": {"author": "Test Author", "published": "2025-01-01"}
    }
    
    mock_neo_repo.get_chunk.return_value = mock_chunk
    mock_neo_repo.get_document.return_value = mock_doc
    
    # Create citation
    citation = citation_service.create_citation(
        chunk_id="chunk123",
        quote_text="This is a test quote",
        citation_number=1
    )
    
    # Verify
    assert citation["citation_id"] == "[1]"
    assert citation["citation_number"] == 1
    assert citation["chunk_id"] == "chunk123"
    assert citation["doc_id"] == "doc456"
    assert citation["doc_url"] == "https://example.com/doc"
    assert citation["title"] == "Test Document"
    assert citation["quote_text"] == "This is a test quote"
    assert citation["metadata"]["author"] == "Test Author"
    assert "created_at" in citation
    
    # Verify cached
    assert "[1]" in citation_service._citation_cache
    assert citation_service._citation_cache["[1]"] == citation
    
    # Verify repo calls
    mock_neo_repo.get_chunk.assert_called_once_with("chunk123")
    mock_neo_repo.get_document.assert_called_once_with("doc456")


def test_create_citation_without_document(citation_service, mock_neo_repo):
    """Test creating citation when document info is missing."""
    mock_chunk = {"id": "chunk123", "doc_id": None}
    mock_neo_repo.get_chunk.return_value = mock_chunk
    
    citation = citation_service.create_citation(
        chunk_id="chunk123",
        quote_text="Quote text",
        citation_number=2
    )
    
    assert citation["citation_id"] == "[2]"
    assert citation["doc_url"] == ""
    assert citation["title"] == ""
    assert citation["metadata"] == {}


def test_create_citation_truncates_long_quotes(citation_service, mock_neo_repo):
    """Test that long quotes are truncated."""
    mock_chunk = {"id": "chunk123", "doc_id": "doc456"}
    mock_doc = {"url": "", "title": "", "metadata": {}}
    
    mock_neo_repo.get_chunk.return_value = mock_chunk
    mock_neo_repo.get_document.return_value = mock_doc
    
    long_quote = "A" * 300  # 300 character quote
    
    citation = citation_service.create_citation(
        chunk_id="chunk123",
        quote_text=long_quote,
        citation_number=3,
        max_quote_length=200
    )
    
    assert len(citation["quote_text"]) == 203  # 200 + "..."
    assert citation["quote_text"].endswith("...")


def test_create_citation_custom_max_length(citation_service, mock_neo_repo):
    """Test creating citation with custom max quote length."""
    mock_chunk = {"id": "chunk123", "doc_id": "doc456"}
    mock_doc = {"url": "", "title": "", "metadata": {}}
    
    mock_neo_repo.get_chunk.return_value = mock_chunk
    mock_neo_repo.get_document.return_value = mock_doc
    
    long_quote = "B" * 150
    
    citation = citation_service.create_citation(
        chunk_id="chunk123",
        quote_text=long_quote,
        citation_number=4,
        max_quote_length=50
    )
    
    assert len(citation["quote_text"]) == 53  # 50 + "..."
    assert citation["quote_text"] == ("B" * 50) + "..."


def test_resolve_citations_found_in_cache(citation_service):
    """Test resolving citations that exist in cache."""
    # Add citations to cache
    citation_service._citation_cache["[1]"] = {
        "citation_id": "[1]",
        "title": "Doc 1"
    }
    citation_service._citation_cache["[2]"] = {
        "citation_id": "[2]",
        "title": "Doc 2"
    }
    
    resolved = citation_service.resolve_citations(["[1]", "[2]"])
    
    assert len(resolved) == 2
    assert resolved["[1]"]["title"] == "Doc 1"
    assert resolved["[2]"]["title"] == "Doc 2"


def test_resolve_citations_not_in_cache(citation_service):
    """Test resolving citations that don't exist in cache."""
    resolved = citation_service.resolve_citations(["[99]"])
    
    assert len(resolved) == 1
    assert resolved["[99]"]["citation_id"] == "[99]"
    assert "error" in resolved["[99]"]
    assert resolved["[99]"]["error"] == "Citation not found in cache"


def test_resolve_citations_mixed(citation_service):
    """Test resolving mix of cached and uncached citations."""
    citation_service._citation_cache["[1]"] = {
        "citation_id": "[1]",
        "title": "Found"
    }
    
    resolved = citation_service.resolve_citations(["[1]", "[99]"])
    
    assert len(resolved) == 2
    assert resolved["[1]"]["title"] == "Found"
    assert "error" in resolved["[99]"]


def test_get_citations_default_sorting(citation_service):
    """Test getting citations with default sorting (by relevance)."""
    # Add citations with different relevance scores
    citation_service._citation_cache["[1]"] = {
        "citation_id": "[1]",
        "relevance_score": 0.9
    }
    citation_service._citation_cache["[2]"] = {
        "citation_id": "[2]",
        "relevance_score": 0.5
    }
    citation_service._citation_cache["[3]"] = {
        "citation_id": "[3]",
        "relevance_score": 0.7
    }
    
    citations = citation_service.get_citations()
    
    assert len(citations) == 3
    assert citations[0]["citation_id"] == "[1]"  # Highest score
    assert citations[1]["citation_id"] == "[3]"
    assert citations[2]["citation_id"] == "[2]"  # Lowest score


def test_get_citations_sort_by_date_desc(citation_service):
    """Test sorting citations by date descending."""
    citation_service._citation_cache["[1]"] = {
        "citation_id": "[1]",
        "metadata": {"published": "2025-01-01"}
    }
    citation_service._citation_cache["[2]"] = {
        "citation_id": "[2]",
        "metadata": {"published": "2025-03-01"}
    }
    citation_service._citation_cache["[3]"] = {
        "citation_id": "[3]",
        "metadata": {"published": "2025-02-01"}
    }
    
    citations = citation_service.get_citations(sort_by="date", sort_order="desc")
    
    assert citations[0]["citation_id"] == "[2]"  # Latest
    assert citations[1]["citation_id"] == "[3]"
    assert citations[2]["citation_id"] == "[1]"  # Earliest


def test_get_citations_sort_by_date_asc(citation_service):
    """Test sorting citations by date ascending."""
    citation_service._citation_cache["[1]"] = {
        "citation_id": "[1]",
        "metadata": {"published": "2025-01-01"}
    }
    citation_service._citation_cache["[2]"] = {
        "citation_id": "[2]",
        "metadata": {"published": "2025-03-01"}
    }
    
    citations = citation_service.get_citations(sort_by="date", sort_order="asc")
    
    assert citations[0]["citation_id"] == "[1]"  # Earliest
    assert citations[1]["citation_id"] == "[2]"


def test_get_citations_sort_by_title(citation_service):
    """Test sorting citations by title."""
    citation_service._citation_cache["[1]"] = {
        "citation_id": "[1]",
        "title": "Zebra"
    }
    citation_service._citation_cache["[2]"] = {
        "citation_id": "[2]",
        "title": "Apple"
    }
    citation_service._citation_cache["[3]"] = {
        "citation_id": "[3]",
        "title": "Mango"
    }
    
    citations = citation_service.get_citations(sort_by="title", sort_order="asc")
    
    assert citations[0]["title"] == "Apple"
    assert citations[1]["title"] == "Mango"
    assert citations[2]["title"] == "Zebra"


def test_get_citations_with_limit(citation_service):
    """Test limiting number of returned citations."""
    for i in range(10):
        citation_service._citation_cache[f"[{i}]"] = {
            "citation_id": f"[{i}]",
            "relevance_score": 0.5
        }
    
    citations = citation_service.get_citations(limit=5)
    
    assert len(citations) == 5


def test_get_citations_empty_cache(citation_service):
    """Test getting citations when cache is empty."""
    citations = citation_service.get_citations()
    
    assert len(citations) == 0
    assert isinstance(citations, list)


def test_multiple_citations_in_sequence(citation_service, mock_neo_repo):
    """Test creating multiple citations in sequence."""
    mock_chunk = {"id": "chunk123", "doc_id": "doc456"}
    mock_doc = {"url": "test.com", "title": "Test", "metadata": {}}
    
    mock_neo_repo.get_chunk.return_value = mock_chunk
    mock_neo_repo.get_document.return_value = mock_doc
    
    cit1 = citation_service.create_citation("chunk123", "Quote 1", 1)
    cit2 = citation_service.create_citation("chunk123", "Quote 2", 2)
    cit3 = citation_service.create_citation("chunk123", "Quote 3", 3)
    
    assert len(citation_service._citation_cache) == 3
    assert cit1["citation_number"] == 1
    assert cit2["citation_number"] == 2
    assert cit3["citation_number"] == 3


def test_get_citations_with_missing_relevance_score(citation_service):
    """Test sorting when some citations lack relevance scores."""
    citation_service._citation_cache["[1]"] = {
        "citation_id": "[1]",
        "relevance_score": 0.8
    }
    citation_service._citation_cache["[2]"] = {
        "citation_id": "[2]"
        # No relevance_score
    }
    
    # Should not crash, citations with missing scores get 0
    citations = citation_service.get_citations(sort_by="relevance")
    
    assert len(citations) == 2
    assert citations[0]["citation_id"] == "[1]"  # Has score
    assert citations[1]["citation_id"] == "[2]"  # No score (0)
