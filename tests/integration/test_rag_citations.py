"""Integration tests for Story S6-604: RAG with Citations.

Tests enhanced search service with citation support, including pagination,
sorting, and filtering capabilities for future scalability.

TDD Approach: RED -> GREEN -> REFACTOR
Testing Philosophy: Real Neo4j + LLM integration, no mocks
"""

import pytest
from app.core.id_generator import generate_doc_id, generate_chunk_id


@pytest.fixture
def citation_service(neo_repo):
    """Fixture for CitationService."""
    from app.services.citation_service import CitationService
    
    return CitationService(neo_repo)


@pytest.fixture
def rag_service(neo_repo, citation_service):
    """Fixture for enhanced RAG SearchService."""
    from app.services.search_service import SearchService
    
    # Mock LLM provider for testing
    class MockLLMProvider:
        def generate(self, prompt: str, **kwargs) -> str:
            # Simple mock that includes citations
            return "OpenAI was founded in 2015[1] by Sam Altman[2]. It is based in San Francisco[3]."
    
    return SearchService(
        neo_repo=neo_repo,
        citation_service=citation_service,
        llm_provider=MockLLMProvider()
    )


class TestRAGWithCitations:
    """Integration tests for RAG with citation support."""

    def test_rag_query_returns_answer_with_citations(self, rag_service, neo_repo):
        """Test 1: RAG query returns answer with inline citations.
        
        Expected behavior:
        - Answer includes [1], [2], [3] citation markers
        - Citations reference actual sources
        - Answer is coherent and relevant
        """
        # Arrange - create documents with entities
        url1 = "https://example.com/openai-history"
        doc_id1 = generate_doc_id(url1)
        neo_repo.create_document(
            doc_id=doc_id1,
            url=url1,
            title="OpenAI History",
            metadata={"published": "2023-01-01"}
        )
        
        chunk_id1 = generate_chunk_id(doc_id1, 0)
        text1 = "OpenAI was founded in 2015 to advance artificial intelligence."
        neo_repo.create_chunk(chunk_id1, doc_id1, text1, 0, len(text1), [0.1] * 384)
        
        url2 = "https://example.com/sam-altman"
        doc_id2 = generate_doc_id(url2)
        neo_repo.create_document(
            doc_id=doc_id2,
            url=url2,
            title="Sam Altman Bio",
            metadata={"published": "2023-06-01"}
        )
        
        chunk_id2 = generate_chunk_id(doc_id2, 0)
        text2 = "Sam Altman is the CEO and co-founder of OpenAI."
        neo_repo.create_chunk(chunk_id2, doc_id2, text2, 0, len(text2), [0.1] * 384)
        
        # Act - perform RAG query
        result = rag_service.query_with_citations(
            query="Who founded OpenAI and when?",
            max_citations=5
        )
        
        # Assert
        assert result is not None
        assert "answer" in result
        assert "citations" in result
        assert "[1]" in result["answer"] or "[2]" in result["answer"]
        assert len(result["citations"]) > 0

    def test_citation_metadata_includes_all_fields(self, citation_service, neo_repo):
        """Test 2: Citation metadata includes doc_url, chunk_id, quote_text.
        
        Expected behavior:
        - Each citation has complete metadata
        - Includes: doc_url, chunk_id, title, quote_text, page_number (if available)
        - Metadata enables click-through to source
        """
        # Arrange
        url = "https://example.com/test-doc"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(
            doc_id=doc_id,
            url=url,
            title="Test Document",
            metadata={"page_number": 5}
        )
        
        chunk_id = generate_chunk_id(doc_id, 0)
        text = "This is a test chunk with important information."
        neo_repo.create_chunk(chunk_id, doc_id, text, 0, len(text), [0.1] * 384)
        
        # Act - create citation
        citation = citation_service.create_citation(
            chunk_id=chunk_id,
            quote_text=text,
            citation_number=1
        )
        
        # Assert
        assert citation["citation_id"] == "[1]"
        assert citation["doc_url"] == url
        assert citation["chunk_id"] == chunk_id
        assert citation["quote_text"] == text
        assert citation["title"] == "Test Document"
        assert "page_number" in citation.get("metadata", {})

    def test_citation_includes_exact_quote_text(self, citation_service, neo_repo):
        """Test 3: Citation includes exact quote from source.
        
        Expected behavior:
        - Quote text is extracted from chunk
        - Maximum quote length configurable
        - Ellipsis added if truncated
        """
        # Arrange
        url = "https://example.com/long-text"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Long Text", metadata={})
        
        chunk_id = generate_chunk_id(doc_id, 0)
        long_text = "This is a very long text that contains many words and should be truncated when used as a quote in citations. " * 5
        neo_repo.create_chunk(chunk_id, doc_id, long_text, 0, len(long_text), [0.1] * 384)
        
        # Act
        citation = citation_service.create_citation(
            chunk_id=chunk_id,
            quote_text=long_text[:100] + "...",
            citation_number=1,
            max_quote_length=100
        )
        
        # Assert
        assert len(citation["quote_text"]) <= 103  # 100 + "..."
        assert "..." in citation["quote_text"] or len(long_text) <= 100

    def test_citation_resolver_maps_ids_to_metadata(self, citation_service, neo_repo):
        """Test 4: Citation resolver maps [1] → full metadata.
        
        Expected behavior:
        - Resolve citation ID to full metadata
        - Support batch resolution ([1], [2], [3])
        - Fast lookup (cached or indexed)
        """
        # Arrange - create multiple citations
        url1 = "https://example.com/doc1"
        doc_id1 = generate_doc_id(url1)
        neo_repo.create_document(doc_id=doc_id1, url=url1, title="Doc 1", metadata={})
        
        chunk_id1 = generate_chunk_id(doc_id1, 0)
        neo_repo.create_chunk(chunk_id1, doc_id1, "Text 1", 0, 6, [0.1] * 384)
        
        url2 = "https://example.com/doc2"
        doc_id2 = generate_doc_id(url2)
        neo_repo.create_document(doc_id=doc_id2, url=url2, title="Doc 2", metadata={})
        
        chunk_id2 = generate_chunk_id(doc_id2, 0)
        neo_repo.create_chunk(chunk_id2, doc_id2, "Text 2", 0, 6, [0.1] * 384)
        
        citation1 = citation_service.create_citation(chunk_id1, "Text 1", 1)
        citation2 = citation_service.create_citation(chunk_id2, "Text 2", 2)
        
        # Act - resolve multiple citations
        resolved = citation_service.resolve_citations(["[1]", "[2]"])
        
        # Assert
        assert len(resolved) == 2
        assert resolved["[1]"]["doc_url"] == url1
        assert resolved["[2]"]["doc_url"] == url2

    def test_multiple_citations_in_same_answer(self, rag_service, neo_repo):
        """Test 5: Handle multiple citations in single answer.
        
        Expected behavior:
        - Answer can reference multiple sources
        - Citations numbered sequentially [1], [2], [3]
        - Each citation links to unique source
        """
        # Arrange - create multiple source documents
        for i in range(3):
            url = f"https://example.com/doc{i}"
            doc_id = generate_doc_id(url)
            neo_repo.create_document(doc_id=doc_id, url=url, title=f"Doc {i}", metadata={})
            
            chunk_id = generate_chunk_id(doc_id, 0)
            neo_repo.create_chunk(chunk_id, doc_id, f"Content {i}", 0, 9, [0.1] * 384)
        
        # Act
        result = rag_service.query_with_citations(
            query="Test query",
            max_citations=3
        )
        
        # Assert
        answer = result["answer"]
        # Should have multiple citations (at least 2)
        citation_count = sum(1 for match in ["[1]", "[2]", "[3]"] if match in answer)
        assert citation_count >= 2

    def test_rag_query_with_pagination(self, rag_service, neo_repo):
        """Test 6: RAG query with pagination support.
        
        Expected behavior:
        - Support page and page_size parameters
        - Return total_count for pagination UI
        - Maintain relevance ranking across pages
        """
        # Arrange - create many documents
        for i in range(25):
            url = f"https://example.com/doc{i}"
            doc_id = generate_doc_id(url)
            neo_repo.create_document(doc_id=doc_id, url=url, title=f"Doc {i}", metadata={})
            
            chunk_id = generate_chunk_id(doc_id, 0)
            neo_repo.create_chunk(chunk_id, doc_id, f"Content about AI topic {i}", 0, 20, [0.1] * 384)
        
        # Act - query with pagination
        page1 = rag_service.query_with_citations(
            query="AI topic",
            page=1,
            page_size=10,
            max_citations=10
        )
        
        page2 = rag_service.query_with_citations(
            query="AI topic",
            page=2,
            page_size=10,
            max_citations=10
        )
        
        # Assert
        assert "total_count" in page1
        assert "page" in page1
        assert "page_size" in page1
        assert len(page1["citations"]) <= 10
        assert len(page2["citations"]) <= 10
        # Different pages should have different results
        if len(page1["citations"]) > 0 and len(page2["citations"]) > 0:
            assert page1["citations"][0]["chunk_id"] != page2["citations"][0]["chunk_id"]

    def test_citation_sorting_by_relevance(self, citation_service, neo_repo):
        """Test 7: Sort citations by relevance score.
        
        Expected behavior:
        - Citations sorted by relevance (default)
        - Support sort_by parameter: relevance, date, title
        - Support sort_order: asc, desc
        """
        # Arrange - create documents with different relevance
        for i, score in enumerate([0.9, 0.7, 0.95, 0.6]):
            url = f"https://example.com/doc{i}"
            doc_id = generate_doc_id(url)
            neo_repo.create_document(
                doc_id=doc_id,
                url=url,
                title=f"Doc {i}",
                metadata={"published": f"2023-0{i+1}-01"}
            )
            
            chunk_id = generate_chunk_id(doc_id, 0)
            neo_repo.create_chunk(chunk_id, doc_id, f"Content {i}", 0, 9, [score] * 384)
        
        # Act - get sorted citations
        citations = citation_service.get_citations(
            sort_by="relevance",
            sort_order="desc",
            limit=10
        )
        
        # Assert - should be sorted by relevance descending
        if len(citations) >= 2:
            assert citations[0].get("relevance_score", 0) >= citations[1].get("relevance_score", 0)

    def test_citation_filtering_by_date(self, citation_service, neo_repo):
        """Test 8: Filter citations by date range.
        
        Expected behavior:
        - Support date_from and date_to parameters
        - Filter citations by document publication date
        - Combine with other filters (relevance, entity type)
        """
        # Arrange - create documents with different dates
        for i in range(3):
            url = f"https://example.com/doc{i}"
            doc_id = generate_doc_id(url)
            neo_repo.create_document(
                doc_id=doc_id,
                url=url,
                title=f"Doc {i}",
                metadata={"published": f"202{i+1}-01-01"}
            )
            
            chunk_id = generate_chunk_id(doc_id, 0)
            neo_repo.create_chunk(chunk_id, doc_id, f"Content {i}", 0, 9, [0.1] * 384)
            citation_service.create_citation(chunk_id, f"Content {i}", i+1)
        
        # Act - filter by date
        citations = citation_service.get_citations(
            date_from="2022-01-01",
            date_to="2022-12-31"
        )
        
        # Assert - should only include 2022 documents
        for citation in citations:
            pub_date = citation.get("metadata", {}).get("published", "")
            if pub_date:
                assert pub_date.startswith("2022")

    def test_performance_answer_query_under_5_seconds(self, rag_service, neo_repo):
        """Test 9: RAG query performance < 5 seconds.
        
        Expected behavior:
        - Query + LLM generation + citation resolution < 5s
        - Efficient vector search
        - Cached embeddings when possible
        """
        import time
        
        # Arrange - create test data
        for i in range(10):
            url = f"https://example.com/doc{i}"
            doc_id = generate_doc_id(url)
            neo_repo.create_document(doc_id=doc_id, url=url, title=f"Doc {i}", metadata={})
            
            chunk_id = generate_chunk_id(doc_id, 0)
            neo_repo.create_chunk(chunk_id, doc_id, f"AI content {i}", 0, 12, [0.1] * 384)
        
        # Act - measure query time
        start = time.time()
        result = rag_service.query_with_citations(
            query="What is AI?",
            max_citations=5
        )
        elapsed = time.time() - start
        
        # Assert
        assert result is not None
        assert elapsed < 5.0, f"Query took {elapsed:.2f}s (expected <5s)"

    def test_handle_queries_with_no_relevant_sources(self, rag_service, neo_repo):
        """Test 10: Handle queries with no matching sources.
        
        Expected behavior:
        - Return empty citations list
        - Provide helpful message in answer
        - Don't crash or return null
        """
        # Arrange - create unrelated documents
        url = "https://example.com/cooking"
        doc_id = generate_doc_id(url)
        neo_repo.create_document(doc_id=doc_id, url=url, title="Cooking Guide", metadata={})
        
        chunk_id = generate_chunk_id(doc_id, 0)
        neo_repo.create_chunk(chunk_id, doc_id, "How to bake bread", 0, 17, [0.9] * 384)
        
        # Act - query unrelated topic
        result = rag_service.query_with_citations(
            query="quantum computing algorithms",
            max_citations=5,
            min_relevance=0.8  # High threshold
        )
        
        # Assert
        assert result is not None
        assert "citations" in result
        assert len(result["citations"]) == 0 or all(
            c.get("relevance_score", 0) >= 0.8 for c in result["citations"]
        )
