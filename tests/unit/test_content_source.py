"""Unit tests for ContentSource enum.

Following TDD RED-GREEN-REFACTOR cycle.
This test should FAIL initially since ContentSource doesn't exist yet.
"""
import pytest
from app.core.types import ContentSource


class TestContentSource:
    """Test suite for ContentSource enum."""

    def test_content_source_valid_values(self):
        """Test that ContentSource has all required source types."""
        # Arrange & Act
        sources = list(ContentSource)
        
        # Assert
        assert ContentSource.WEB in sources
        assert ContentSource.YOUTUBE in sources
        assert ContentSource.PDF in sources
        assert ContentSource.TEXT in sources
        assert len(sources) == 4

    def test_content_source_string_values(self):
        """Test that ContentSource enum values are strings."""
        # Arrange & Act & Assert
        assert ContentSource.WEB.value == "web"
        assert ContentSource.YOUTUBE.value == "youtube"
        assert ContentSource.PDF.value == "pdf"
        assert ContentSource.TEXT.value == "text"

    def test_content_source_from_string(self):
        """Test creating ContentSource from string value."""
        # Arrange
        source_str = "web"
        
        # Act
        source = ContentSource(source_str)
        
        # Assert
        assert source == ContentSource.WEB

    def test_content_source_invalid_value(self):
        """Test that invalid source type raises ValueError."""
        # Arrange
        invalid_source = "invalid_source"
        
        # Act & Assert
        with pytest.raises(ValueError):
            ContentSource(invalid_source)

    def test_content_source_comparison(self):
        """Test ContentSource enum equality."""
        # Arrange
        source1 = ContentSource.WEB
        source2 = ContentSource.WEB
        source3 = ContentSource.YOUTUBE
        
        # Act & Assert
        assert source1 == source2
        assert source1 != source3

    def test_content_source_in_collection(self):
        """Test ContentSource can be used in collections."""
        # Arrange
        sources = {ContentSource.WEB, ContentSource.PDF}
        
        # Act & Assert
        assert ContentSource.WEB in sources
        assert ContentSource.YOUTUBE not in sources
        assert len(sources) == 2
