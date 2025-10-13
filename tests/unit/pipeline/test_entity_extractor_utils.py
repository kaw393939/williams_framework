"""Unit tests for EntityExtractor utility methods."""
import pytest
from unittest.mock import Mock

from app.pipeline.transformers.entity_extractor import EntityExtractor


class TestEntityExtractorUtilities:
    """Test utility methods in EntityExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance for testing utilities."""
        mock_repo = Mock()
        return EntityExtractor(neo_repo=mock_repo)

    def test_generate_title_from_url(self, extractor):
        """Test generating title from URL."""
        title = extractor._generate_title("https://example.com/path/to/page")
        assert "example.com" in title
        assert "Content from" in title

    def test_generate_title_from_url_with_subdomain(self, extractor):
        """Test generating title with subdomain."""
        title = extractor._generate_title("https://blog.example.com/article")
        assert "blog.example.com" in title

    def test_generate_title_no_scheme(self, extractor):
        """Test generating title with no scheme."""
        title = extractor._generate_title("example.com")
        assert "example.com" in title or "Unknown" in title

    def test_generate_summary_short_text(self, extractor):
        """Test summary generation for short text."""
        text = "This is a short text."
        summary = extractor._generate_summary(text)
        assert summary == text

    def test_generate_summary_long_text_with_period(self, extractor):
        """Test summary generation for long text with sentence boundary."""
        text = "This is the first sentence. " * 30  # Make it long
        summary = extractor._generate_summary(text)
        assert len(summary) <= 401  # Max length + period
        assert summary.endswith('.')

    def test_generate_summary_long_text_no_period(self, extractor):
        """Test summary generation for long text without sentence boundary."""
        text = "A" * 500  # No periods
        summary = extractor._generate_summary(text)
        assert len(summary) <= 403  # Max length + "..."
        assert summary.endswith('...')

    def test_generate_summary_period_near_end(self, extractor):
        """Test summary when period is near the end."""
        text = ("Word " * 60) + ". More text after."  # Period around position 360
        summary = extractor._generate_summary(text)
        assert summary.endswith('.')
