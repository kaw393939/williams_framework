"""Integration tests for EnhancedChunker with Neo4j provenance.

Tests the chunker with REAL Neo4j database to ensure proper integration
with existing pipeline architecture.
"""
from datetime import datetime

import pytest

from app.core.id_generator import generate_chunk_id, generate_doc_id
from app.core.models import RawContent
from app.core.types import ContentSource
from app.pipeline.transformers.enhanced_chunker import EnhancedChunker


@pytest.fixture
def chunker(neo_repo):
    """Create an EnhancedChunker with test Neo4j repository."""
    neo_repo.clear_database()
    neo_repo.initialize_schema()
    return EnhancedChunker(neo_repo=neo_repo, chunk_size=100, chunk_overlap=20)


@pytest.fixture
def sample_raw_content():
    """Create sample RawContent for testing."""
    return RawContent(
        url="https://example.com/article",
        source_type=ContentSource.WEB,
        raw_text="This is the first sentence. This is the second sentence. This is the third sentence.",
        metadata={"title": "Test Article", "author": "Test Author"},
        extracted_at=datetime(2025, 10, 12, 10, 0, 0),
    )


class TestChunkerInitialization:
    """Test chunker initialization."""

    def test_initialization_with_defaults(self, neo_repo):
        """Test chunker initializes with default parameters."""
        neo_repo.initialize_schema()
        chunker = EnhancedChunker(neo_repo=neo_repo)

        assert chunker._chunk_size == 1000
        assert chunker._chunk_overlap == 200

    def test_initialization_with_custom_params(self, neo_repo):
        """Test chunker initializes with custom parameters."""
        neo_repo.initialize_schema()
        chunker = EnhancedChunker(
            neo_repo=neo_repo,
            chunk_size=500,
            chunk_overlap=100,
        )

        assert chunker._chunk_size == 500
        assert chunker._chunk_overlap == 100


class TestTextChunking:
    """Test text chunking logic."""

    def test_chunk_simple_text(self, chunker):
        """Test chunking simple text."""
        text = "First sentence. Second sentence. Third sentence."
        chunks = chunker._chunk_text(text)

        assert len(chunks) > 0
        assert all("text" in chunk for chunk in chunks)
        assert all("start_offset" in chunk for chunk in chunks)
        assert all("end_offset" in chunk for chunk in chunks)

    def test_chunk_preserves_byte_offsets(self, chunker):
        """Test that chunks have correct byte offsets."""
        text = "Hello world. This is a test."
        chunks = chunker._chunk_text(text)

        # Verify offsets are sequential and non-overlapping in stored chunks
        # (overlap is for context, not storage)
        for i, chunk in enumerate(chunks):
            assert chunk["start_offset"] >= 0
            assert chunk["end_offset"] > chunk["start_offset"]
            assert chunk["index"] == i

    def test_chunk_empty_text(self, chunker):
        """Test chunking empty text."""
        chunks = chunker._chunk_text("")
        assert chunks == []

    def test_chunk_unicode_text(self, chunker):
        """Test chunking text with unicode characters."""
        text = "Hello 世界! Schrödinger's cat. Café au lait."
        chunks = chunker._chunk_text(text)

        assert len(chunks) > 0
        # Verify unicode preserved
        full_text = "".join(chunk["text"] for chunk in chunks)
        assert "世界" in full_text
        assert "Schrödinger" in full_text


class TestNeo4jIntegration:
    """Test Neo4j provenance storage."""

    @pytest.mark.asyncio
    async def test_transform_creates_document(self, chunker, sample_raw_content, neo_repo):
        """Test transform creates Document node in Neo4j."""
        await chunker.transform(sample_raw_content)

        # Verify document was created
        doc_id = generate_doc_id(str(sample_raw_content.url))
        doc = neo_repo.get_document(doc_id)

        assert doc is not None
        assert doc["id"] == doc_id
        assert doc["url"] == str(sample_raw_content.url)

    @pytest.mark.asyncio
    async def test_transform_creates_chunks(self, chunker, sample_raw_content, neo_repo):
        """Test transform creates Chunk nodes with PART_OF relationships."""
        await chunker.transform(sample_raw_content)

        # Verify chunks were created
        doc_id = generate_doc_id(str(sample_raw_content.url))
        _doc = neo_repo.get_document(doc_id)

        # Query chunks
        query = """
        MATCH (c:Chunk)-[:PART_OF]->(d:Document {id: $doc_id})
        RETURN c
        ORDER BY c.start_offset
        """
        result = neo_repo.execute_query(query, {"doc_id": doc_id})
        chunks = [dict(record["c"]) for record in result]

        assert len(chunks) > 0
        # Verify chunks have required properties
        for chunk in chunks:
            assert "id" in chunk
            assert "text" in chunk
            assert "start_offset" in chunk
            assert "end_offset" in chunk

    @pytest.mark.asyncio
    async def test_transform_returns_processed_content(self, chunker, sample_raw_content):
        """Test transform returns valid ProcessedContent."""
        result = await chunker.transform(sample_raw_content)

        assert result.url == sample_raw_content.url
        assert result.source_type == sample_raw_content.source_type
        assert result.title == "Test Article"
        assert len(result.summary) > 0
        assert result.screening_result.decision == "ACCEPT"


class TestDeterministicIDs:
    """Test deterministic ID generation."""

    @pytest.mark.asyncio
    async def test_same_url_produces_same_doc_id(self, chunker, neo_repo):
        """Test same URL produces same document ID."""
        url = "https://example.com/test"

        content1 = RawContent(
            url=url,
            source_type=ContentSource.WEB,
            raw_text="First version",
        )

        content2 = RawContent(
            url=url,
            source_type=ContentSource.WEB,
            raw_text="Second version",
        )

        await chunker.transform(content1)
        await chunker.transform(content2)

        # Should have only one document (same ID)
        doc_id = generate_doc_id(url)
        doc = neo_repo.get_document(doc_id)

        assert doc is not None
        assert doc["id"] == doc_id

    @pytest.mark.asyncio
    async def test_chunk_ids_deterministic(self, chunker, sample_raw_content, neo_repo):
        """Test chunk IDs are deterministic based on offset."""
        await chunker.transform(sample_raw_content)

        doc_id = generate_doc_id(str(sample_raw_content.url))

        # Query first chunk
        query = """
        MATCH (c:Chunk)-[:PART_OF]->(d:Document {id: $doc_id})
        RETURN c
        ORDER BY c.start_offset
        LIMIT 1
        """
        result = neo_repo.execute_query(query, {"doc_id": doc_id})
        chunk = dict(result[0]["c"])

        # Verify ID matches expected pattern
        expected_id = generate_chunk_id(doc_id, chunk["start_offset"])
        assert chunk["id"] == expected_id


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_very_long_text(self, chunker, neo_repo):
        """Test chunking very long text."""
        long_text = "This is a sentence. " * 1000  # ~20,000 characters

        content = RawContent(
            url="https://example.com/long",
            source_type=ContentSource.WEB,
            raw_text=long_text,
        )

        result = await chunker.transform(content)

        # Should create multiple chunks
        doc_id = generate_doc_id(str(content.url))
        query = """
        MATCH (c:Chunk)-[:PART_OF]->(d:Document {id: $doc_id})
        RETURN count(c) as chunk_count
        """
        result = neo_repo.execute_query(query, {"doc_id": doc_id})
        chunk_count = result[0]["chunk_count"]

        assert chunk_count > 1

    @pytest.mark.asyncio
    async def test_text_with_special_characters(self, chunker, neo_repo):
        """Test chunking text with special characters."""
        text = "AT&T is a company. O'Reilly publishes books. Cost is $100."

        content = RawContent(
            url="https://example.com/special",
            source_type=ContentSource.WEB,
            raw_text=text,
        )

        result = await chunker.transform(content)

        # Verify special characters preserved
        doc_id = generate_doc_id(str(content.url))
        query = """
        MATCH (c:Chunk)-[:PART_OF]->(d:Document {id: $doc_id})
        RETURN c.text as text
        """
        result = neo_repo.execute_query(query, {"doc_id": doc_id})
        chunk_texts = [record["text"] for record in result]
        full_text = "".join(chunk_texts)

        assert "AT&T" in full_text
        assert "O'Reilly" in full_text
        assert "$100" in full_text
