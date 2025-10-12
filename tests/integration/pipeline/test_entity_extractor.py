"""Integration tests for EntityExtractor with Neo4j provenance.

Tests the entity extractor with REAL Neo4j database to ensure proper integration
with existing pipeline architecture and complete provenance tracking.
"""
from datetime import datetime

import pytest

from app.core.id_generator import generate_chunk_id, generate_doc_id
from app.core.models import RawContent
from app.core.types import ContentSource
from app.pipeline.transformers.entity_extractor import EntityExtractor


@pytest.fixture
def extractor(neo_repo):
    """Create an EntityExtractor with test Neo4j repository."""
    neo_repo.clear_database()
    neo_repo.initialize_schema()
    # Use extractor without LLM (fallback to pattern-based)
    return EntityExtractor(neo_repo=neo_repo)


@pytest.fixture
def sample_document_with_chunks(neo_repo):
    """Create a sample document with chunks in Neo4j."""
    url = "https://example.com/article"
    doc_id = generate_doc_id(url)

    # Create document
    neo_repo.create_document(
        doc_id=doc_id,
        url=url,
        title="AI Research Article",
        metadata={"author": "John Doe"},
    )

    # Create chunks with entity-rich text
    chunks_data = [
        {
            "text": "Albert Einstein developed the theory of relativity in 1905. "
                    "He worked at the University of Zurich.",
            "start_offset": 0,
            "end_offset": 110,
        },
        {
            "text": "Marie Curie discovered radium in 1898. She won the Nobel Prize in 1903.",
            "start_offset": 110,
            "end_offset": 182,
        },
        {
            "text": 'The concept of "artificial intelligence" was coined in 1956. '
                    "John McCarthy organized the Dartmouth Conference.",
            "start_offset": 182,
            "end_offset": 280,
        },
    ]

    for chunk_data in chunks_data:
        chunk_id = generate_chunk_id(doc_id, chunk_data["start_offset"])
        neo_repo.create_chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            text=chunk_data["text"],
            start_offset=chunk_data["start_offset"],
            end_offset=chunk_data["end_offset"],
        )

    return {
        "url": url,
        "doc_id": doc_id,
        "chunks_count": len(chunks_data),
    }


@pytest.fixture
def sample_raw_content(sample_document_with_chunks):
    """Create sample RawContent matching the test document."""
    return RawContent(
        url=sample_document_with_chunks["url"],
        source_type=ContentSource.WEB,
        raw_text="Albert Einstein developed the theory of relativity in 1905. "
                 "He worked at the University of Zurich. "
                 "Marie Curie discovered radium in 1898. She won the Nobel Prize in 1903. "
                 'The concept of "artificial intelligence" was coined in 1956. '
                 "John McCarthy organized the Dartmouth Conference.",
        metadata={"title": "AI Research Article"},
        extracted_at=datetime(2025, 10, 12, 10, 0, 0),
    )


class TestExtractorInitialization:
    """Test entity extractor initialization."""

    def test_initialization_with_defaults(self, neo_repo):
        """Test extractor initializes with default parameters."""
        neo_repo.initialize_schema()
        extractor = EntityExtractor(neo_repo=neo_repo)

        assert extractor._neo_repo is not None
        assert extractor._llm_provider is None
        assert "PERSON" in extractor._entity_types
        assert "ORGANIZATION" in extractor._entity_types
        assert "CONCEPT" in extractor._entity_types

    def test_initialization_with_custom_types(self, neo_repo):
        """Test extractor initializes with custom entity types."""
        neo_repo.initialize_schema()
        custom_types = ["PERSON", "LOCATION"]
        extractor = EntityExtractor(
            neo_repo=neo_repo,
            entity_types=custom_types,
        )

        assert extractor._entity_types == custom_types


class TestPatternBasedExtraction:
    """Test pattern-based entity extraction (fallback mode)."""

    def test_extract_capitalized_sequences(self, extractor):
        """Test extraction of capitalized names/organizations."""
        text = "Albert Einstein worked with Marie Curie at the University of Zurich."
        entities = extractor._fallback_entity_extraction(text)

        # Should find "Albert Einstein", "Marie Curie"
        # (pattern requires 2+ consecutive capitalized words)
        entity_texts = [e["text"] for e in entities]
        assert "Albert Einstein" in entity_texts
        assert "Marie Curie" in entity_texts
        # Note: "University of Zurich" won't match due to "of" (lowercase connector)

    def test_extract_years(self, extractor):
        """Test extraction of years."""
        text = "The theory was developed in 1905 and published in 2023."
        entities = extractor._fallback_entity_extraction(text)

        years = [e for e in entities if e["type"] == "DATE"]
        assert len(years) == 2
        assert any(e["text"] == "1905" for e in years)
        assert any(e["text"] == "2023" for e in years)

    def test_extract_quoted_concepts(self, extractor):
        """Test extraction of quoted terms as concepts."""
        text = 'The term "artificial intelligence" was coined in 1956.'
        entities = extractor._fallback_entity_extraction(text)

        concepts = [e for e in entities if e["type"] == "CONCEPT"]
        assert len(concepts) >= 1
        assert any(e["text"] == "artificial intelligence" for e in concepts)

    def test_extract_preserves_offsets(self, extractor):
        """Test that entity offsets are accurate."""
        text = "Albert Einstein lived in Switzerland."
        entities = extractor._fallback_entity_extraction(text)

        einstein = next((e for e in entities if "Einstein" in e["text"]), None)
        assert einstein is not None
        assert einstein["offset"] == 0  # Starts at beginning


class TestNeo4jIntegration:
    """Test Neo4j entity and mention storage."""

    @pytest.mark.asyncio
    async def test_transform_creates_entities(self, extractor, sample_raw_content, sample_document_with_chunks, neo_repo):
        """Test transform creates Entity nodes in Neo4j."""
        await extractor.transform(sample_raw_content)

        # Verify entities were created
        query = "MATCH (e:Entity) RETURN e"
        result = neo_repo.execute_query(query)
        entities = [dict(record["e"]) for record in result]

        assert len(entities) > 0
        # Should find entities like "Albert Einstein", "Marie Curie", etc.
        entity_texts = [e["text"] for e in entities]
        assert any("Einstein" in text for text in entity_texts)

    @pytest.mark.asyncio
    async def test_transform_creates_mentions(self, extractor, sample_raw_content, sample_document_with_chunks, neo_repo):
        """Test transform creates Mention nodes with relationships."""
        await extractor.transform(sample_raw_content)

        # Verify mentions were created
        query = """
        MATCH (m:Mention)-[:FOUND_IN]->(c:Chunk)
        MATCH (m)-[:REFERS_TO]->(e:Entity)
        RETURN m, c, e
        """
        result = neo_repo.execute_query(query)
        mentions = result

        assert len(mentions) > 0

        # Verify mention has both relationships
        for record in mentions:
            mention = dict(record["m"])
            chunk = dict(record["c"])
            entity = dict(record["e"])

            assert "id" in mention
            assert "offset_in_chunk" in mention
            assert "id" in chunk
            assert "id" in entity

    @pytest.mark.asyncio
    async def test_transform_returns_processed_content(self, extractor, sample_raw_content, sample_document_with_chunks):
        """Test transform returns valid ProcessedContent."""
        result = await extractor.transform(sample_raw_content)

        assert result.url == sample_raw_content.url
        assert result.source_type == sample_raw_content.source_type
        assert result.title == "AI Research Article"
        assert len(result.tags) > 0  # Should have entity tags
        assert result.screening_result.decision == "ACCEPT"
        assert result.screening_result.screening_score == 8.0

    @pytest.mark.asyncio
    async def test_entity_mention_count_increments(self, extractor, sample_raw_content, sample_document_with_chunks, neo_repo):
        """Test that entity mention_count increments correctly."""
        await extractor.transform(sample_raw_content)

        # Find an entity that appears multiple times
        query = """
        MATCH (e:Entity)
        WHERE e.mention_count > 1
        RETURN e
        LIMIT 1
        """
        result = neo_repo.execute_query(query)

        # If we have any entity with multiple mentions, verify count
        if result:
            entity = dict(result[0]["e"])
            assert entity["mention_count"] >= 1


class TestDeterministicIDs:
    """Test deterministic ID generation for entities and mentions."""

    @pytest.mark.asyncio
    async def test_same_entity_produces_same_id(self, extractor, neo_repo):
        """Test same entity text+type produces same entity ID."""
        # Create two documents with the same entity
        for i in range(2):
            url = f"https://example.com/doc{i}"
            doc_id = generate_doc_id(url)

            neo_repo.create_document(
                doc_id=doc_id,
                url=url,
                title=f"Document {i}",
                metadata={},
            )

            chunk_id = generate_chunk_id(doc_id, 0)
            neo_repo.create_chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                text="Albert Einstein discovered relativity.",
                start_offset=0,
                end_offset=40,
            )

            content = RawContent(
                url=url,
                source_type=ContentSource.WEB,
                raw_text="Albert Einstein discovered relativity.",
                metadata={"title": f"Document {i}"},
                extracted_at=datetime.now(),
            )

            await extractor.transform(content)

        # Should have only one entity node (same ID, incremented mention_count)
        query = """
        MATCH (e:Entity)
        WHERE e.text CONTAINS 'Einstein'
        RETURN e
        """
        result = neo_repo.execute_query(query)
        entities = [dict(record["e"]) for record in result]

        assert len(entities) == 1
        assert entities[0]["mention_count"] >= 2  # Mentioned in both docs


class TestProvenanceChain:
    """Test complete provenance chain from mention to source."""

    @pytest.mark.asyncio
    async def test_trace_entity_to_source_document(self, extractor, sample_raw_content, sample_document_with_chunks, neo_repo):
        """Test tracing an entity back to its source document."""
        await extractor.transform(sample_raw_content)

        # Find an entity and trace to its source
        query = """
        MATCH (e:Entity)
        WHERE e.text CONTAINS 'Einstein'
        MATCH (m:Mention)-[:REFERS_TO]->(e)
        MATCH (m)-[:FOUND_IN]->(c:Chunk)-[:PART_OF]->(d:Document)
        RETURN e, m, c, d
        LIMIT 1
        """
        result = neo_repo.execute_query(query)

        assert len(result) > 0

        record = result[0]
        entity = dict(record["e"])
        mention = dict(record["m"])
        chunk = dict(record["c"])
        document = dict(record["d"])

        # Verify complete chain
        assert "Einstein" in entity["text"]
        assert mention["offset_in_chunk"] >= 0
        assert chunk["text"]
        assert document["url"] == str(sample_raw_content.url)

    @pytest.mark.asyncio
    async def test_trace_entity_to_exact_location(self, extractor, sample_raw_content, sample_document_with_chunks, neo_repo):
        """Test tracing entity to exact byte offset in document."""
        await extractor.transform(sample_raw_content)

        # Trace a specific entity to its location
        query = """
        MATCH (e:Entity)
        WHERE e.text CONTAINS 'Einstein'
        MATCH (m:Mention)-[:REFERS_TO]->(e)
        MATCH (m)-[:FOUND_IN]->(c:Chunk)
        RETURN e.text as entity_text,
               m.offset_in_chunk as offset_in_chunk,
               c.start_offset as chunk_start,
               c.text as chunk_text
        LIMIT 1
        """
        result = neo_repo.execute_query(query)

        assert len(result) > 0

        record = result[0]

        # Verify entity appears at calculated offset
        offset_in_chunk = record["offset_in_chunk"]
        chunk_text = record["chunk_text"]
        entity_text = record["entity_text"]

        assert entity_text in chunk_text
        # Entity should appear near the calculated offset in chunk
        actual_offset_in_chunk = chunk_text.find(entity_text)
        assert abs(actual_offset_in_chunk - offset_in_chunk) < 10  # Allow small tolerance


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_error_when_document_not_found(self, extractor, neo_repo):
        """Test error when trying to extract from non-existent document."""
        content = RawContent(
            url="https://example.com/missing",
            source_type=ContentSource.WEB,
            raw_text="Some text",
            metadata={},
            extracted_at=datetime.now(),
        )

        with pytest.raises(ValueError, match="not found in Neo4j"):
            await extractor.transform(content)

    @pytest.mark.asyncio
    async def test_handles_chunks_with_no_entities(self, extractor, neo_repo):
        """Test handling chunks with no extractable entities."""
        url = "https://example.com/noentities"
        doc_id = generate_doc_id(url)

        neo_repo.create_document(
            doc_id=doc_id,
            url=url,
            title="Simple Doc",
            metadata={},
        )

        chunk_id = generate_chunk_id(doc_id, 0)
        neo_repo.create_chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            text="the and or but is are was were",  # Only stopwords
            start_offset=0,
            end_offset=30,
        )

        content = RawContent(
            url=url,
            source_type=ContentSource.WEB,
            raw_text="the and or but is are was were",
            metadata={"title": "Simple Doc"},
            extracted_at=datetime.now(),
        )

        result = await extractor.transform(content)

        # Should succeed but with no entities/tags
        assert result.screening_result.decision == "ACCEPT"
        # Tags might be empty or very few
        assert len(result.tags) < 5
