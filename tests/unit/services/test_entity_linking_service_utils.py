"""Unit tests for EntityLinkingService utility methods."""
import pytest

from app.services.entity_linking_service import EntityLinkingService


class TestEntityLinkingServiceUtilities:
    """Test utility methods in EntityLinkingService."""

    @pytest.fixture
    def service(self):
        """Create service instance for testing utilities."""
        # Use None for neo_repo since we're only testing utility methods
        from unittest.mock import Mock
        mock_repo = Mock()
        return EntityLinkingService(neo_repo=mock_repo)

    def test_normalize_text_lowercase(self, service):
        """Test text normalization converts to lowercase."""
        assert service._normalize_text("HELLO WORLD") == "hello world"
        assert service._normalize_text("Test") == "test"

    def test_normalize_text_removes_extra_whitespace(self, service):
        """Test text normalization removes extra whitespace."""
        assert service._normalize_text("hello  world") == "hello world"
        assert service._normalize_text("  test  ") == "test"
        assert service._normalize_text("a\tb\nc") == "a b c"

    def test_string_similarity_exact_match(self, service):
        """Test string similarity returns 1.0 for exact matches."""
        assert service._string_similarity("test", "test") == 1.0
        assert service._string_similarity("OpenAI", "OpenAI") == 1.0

    def test_string_similarity_empty_strings(self, service):
        """Test string similarity returns 0.0 for empty strings."""
        assert service._string_similarity("", "test") == 0.0
        assert service._string_similarity("test", "") == 0.0
        assert service._string_similarity("", "") == 0.0

    def test_string_similarity_substring_match(self, service):
        """Test string similarity detects substring matches."""
        # "openai" is substring of "openai inc"
        similarity = service._string_similarity("openai", "openai inc")
        assert similarity > 0.5  # Should have high similarity

    def test_string_similarity_different_strings(self, service):
        """Test string similarity for completely different strings."""
        similarity = service._string_similarity("cat", "dog")
        assert 0.0 <= similarity < 1.0  # Should be between 0 and 1, not equal

    def test_calculate_confidence_exact_match(self, service):
        """Test confidence calculation for exact matches."""
        confidence = service._calculate_confidence("OpenAI", "OpenAI")
        assert confidence >= 0.9  # Exact match should have high confidence

    def test_calculate_confidence_different_case(self, service):
        """Test confidence calculation is case-insensitive."""
        confidence1 = service._calculate_confidence("openai", "OpenAI")
        confidence2 = service._calculate_confidence("OPENAI", "openai")
        assert confidence1 >= 0.8  # Should be high due to normalization
        assert confidence2 >= 0.8

    def test_calculate_confidence_similar_text(self, service):
        """Test confidence calculation for similar text."""
        confidence = service._calculate_confidence("OpenAI Inc", "OpenAI")
        assert 0.5 <= confidence <= 1.0  # Should be moderately high

    def test_calculate_confidence_different_text(self, service):
        """Test confidence calculation for different text."""
        confidence = service._calculate_confidence("Microsoft", "Google")
        assert 0.0 <= confidence < 1.0  # Should be lower than exact match
