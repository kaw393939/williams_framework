"""Tests for EntityExtractor with LLM provider to cover LLM-based extraction paths."""
import pytest

from app.core.id_generator import generate_chunk_id, generate_doc_id
from app.core.models import RawContent
from app.core.types import ContentSource
from app.pipeline.transformers.entity_extractor import EntityExtractor


class MockLLMProvider:
    """Mock LLM provider that returns controlled entity extraction responses."""

    def __init__(self, response: str | None = None, should_raise: bool = False):
        """Initialize mock with controlled response.

        Args:
            response: JSON response to return
            should_raise: Whether to raise an exception
        """
        self.response = response or """[
            {"text": "Albert Einstein", "type": "PERSON", "offset": 0},
            {"text": "University of Zurich", "type": "ORGANIZATION", "offset": 60}
        ]"""
        self.should_raise = should_raise
        self.generate_calls = []

    async def generate(self, prompt: str, **kwargs):
        """Mock generate method."""
        self.generate_calls.append({"prompt": prompt, "kwargs": kwargs})
        if self.should_raise:
            raise ValueError("LLM error")
        return self.response


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    return MockLLMProvider()


@pytest.fixture
def extractor_with_llm(neo_repo, mock_llm_provider):
    """Create an EntityExtractor with mock LLM."""
    neo_repo.clear_database()
    neo_repo.initialize_schema()
    return EntityExtractor(neo_repo=neo_repo, llm_provider=mock_llm_provider)


@pytest.fixture
def sample_doc_with_chunk(neo_repo):
    """Create a sample document with one chunk."""
    url = "https://example.com/article"
    doc_id = generate_doc_id(url)

    neo_repo.create_document(
        doc_id=doc_id,
        url=url,
        title="AI Article",
        metadata={},
    )

    chunk_text = "Albert Einstein developed relativity. He worked at the University of Zurich."
    chunk_id = generate_chunk_id(doc_id, 0)
    neo_repo.create_chunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        text=chunk_text,
        start_offset=0,
        end_offset=len(chunk_text),
    )

    return {
        "url": url,
        "doc_id": doc_id,
        "chunk_id": chunk_id,
        "text": chunk_text,
    }


class TestLLMBasedExtraction:
    """Test entity extraction with LLM provider."""

    @pytest.mark.asyncio
    async def test_uses_llm_when_available(
        self, extractor_with_llm, sample_doc_with_chunk, mock_llm_provider
    ):
        """Test that extractor uses LLM when provider is available."""
        raw_content = RawContent(
            url=sample_doc_with_chunk["url"],
            source_type=ContentSource.WEB,
            raw_text=sample_doc_with_chunk["text"],
            metadata={},
        )

        result = await extractor_with_llm.transform(raw_content)

        # Verify LLM was called
        assert len(mock_llm_provider.generate_calls) > 0
        # Verify entities were extracted
        assert "Albert Einstein" in result.tags or "University of Zurich" in result.tags

    @pytest.mark.asyncio
    async def test_llm_error_falls_back_to_pattern_based(
        self, neo_repo, sample_doc_with_chunk
    ):
        """Test that LLM errors fall back to pattern-based extraction."""
        mock_llm = MockLLMProvider(should_raise=True)
        extractor = EntityExtractor(neo_repo=neo_repo, llm_provider=mock_llm)

        raw_content = RawContent(
            url=sample_doc_with_chunk["url"],
            source_type=ContentSource.WEB,
            raw_text=sample_doc_with_chunk["text"],
            metadata={},
        )

        # Should not raise, should fall back to pattern-based
        result = await extractor.transform(raw_content)

        # Should still have some tags (from fallback)
        assert len(result.tags) > 0

    @pytest.mark.asyncio
    async def test_parse_llm_entities_with_valid_json(
        self, extractor_with_llm, sample_doc_with_chunk
    ):
        """Test parsing of valid LLM JSON response."""
        response = """[
            {"text": "Albert Einstein", "type": "PERSON", "offset": 0},
            {"text": "University", "type": "ORG", "offset": 60}
        ]"""

        entities = extractor_with_llm._parse_llm_entities(
            response, sample_doc_with_chunk["text"]
        )

        assert len(entities) >= 1
        assert any(e["text"] == "Albert Einstein" for e in entities)

    @pytest.mark.asyncio
    async def test_parse_llm_entities_with_invalid_json(
        self, extractor_with_llm, sample_doc_with_chunk
    ):
        """Test parsing of invalid LLM JSON response."""
        response = "This is not JSON"

        entities = extractor_with_llm._parse_llm_entities(
            response, sample_doc_with_chunk["text"]
        )

        assert entities == []

    @pytest.mark.asyncio
    async def test_parse_llm_entities_validates_text_exists(
        self, extractor_with_llm, sample_doc_with_chunk
    ):
        """Test that parser validates entities exist in chunk text."""
        response = """[
            {"text": "Nonexistent Entity", "type": "PERSON", "offset": 0}
        ]"""

        entities = extractor_with_llm._parse_llm_entities(
            response, sample_doc_with_chunk["text"]
        )

        # Should be empty since entity doesn't exist in text
        assert len(entities) == 0

    @pytest.mark.asyncio
    async def test_parse_llm_entities_case_insensitive(
        self, extractor_with_llm
    ):
        """Test that parser handles case-insensitive offset finding."""
        # Test with entity that exists in text, but offset is wrong (needs recalculation)
        chunk_text = "Albert Einstein developed the theory of relativity."
        response = """[
            {"text": "Albert Einstein", "type": "PERSON", "offset": 999}
        ]"""

        entities = extractor_with_llm._parse_llm_entities(response, chunk_text)

        # Should find entity and recalculate correct offset
        assert len(entities) == 1
        assert entities[0]["text"] == "Albert Einstein"
        assert entities[0]["offset"] == 0  # Corrected offset

    @pytest.mark.asyncio
    async def test_build_entity_extraction_prompt(self, extractor_with_llm):
        """Test that entity extraction prompt is properly formatted."""
        text = "Sample text for extraction"

        prompt = extractor_with_llm._build_entity_extraction_prompt(text)

        assert "Sample text for extraction" in prompt
        assert "JSON" in prompt
        assert "PERSON" in prompt or "ORGANIZATION" in prompt
