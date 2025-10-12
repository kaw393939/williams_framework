"""Unit tests for RawContent Pydantic model.

Following TDD RED-GREEN-REFACTOR cycle.
This test should FAIL initially since RawContent doesn't exist yet.
"""
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.core.models import RawContent
from app.core.types import ContentSource


class TestRawContent:
    """Test suite for RawContent Pydantic model."""

    def test_raw_content_valid_web(self):
        """Test creating valid RawContent for web source."""
        # Arrange
        data = {
            "url": "https://example.com/article",
            "source_type": ContentSource.WEB,
            "raw_text": "This is the extracted web content",
            "metadata": {"title": "Example Article", "author": "John Doe"},
            "extracted_at": datetime(2025, 10, 9, 12, 0, 0)
        }

        # Act
        content = RawContent(**data)

        # Assert
        assert str(content.url) == "https://example.com/article"
        assert content.source_type == ContentSource.WEB
        assert content.raw_text == "This is the extracted web content"
        assert content.metadata["title"] == "Example Article"
        assert content.extracted_at == datetime(2025, 10, 9, 12, 0, 0)

    def test_raw_content_valid_youtube(self):
        """Test creating valid RawContent for YouTube source."""
        # Arrange
        data = {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "source_type": ContentSource.YOUTUBE,
            "raw_text": "Video transcript here",
            "metadata": {
                "title": "Great Video",
                "channel": "Example Channel",
                "duration": 180
            },
            "extracted_at": datetime.now()
        }

        # Act
        content = RawContent(**data)

        # Assert
        assert content.source_type == ContentSource.YOUTUBE
        assert "youtube.com" in str(content.url)
        assert content.metadata["duration"] == 180

    def test_raw_content_url_validation(self):
        """Test that URL must be valid."""
        # Invalid URL
        with pytest.raises(ValidationError) as exc_info:
            RawContent(
                url="not-a-valid-url",
                source_type=ContentSource.WEB,
                raw_text="content",
                metadata={},
                extracted_at=datetime.now()
            )
        assert "url" in str(exc_info.value).lower()

    def test_raw_content_text_required(self):
        """Test that raw_text is required and cannot be empty."""
        # Missing raw_text
        with pytest.raises(ValidationError) as exc_info:
            RawContent(
                url="https://example.com",
                source_type=ContentSource.WEB,
                metadata={},
                extracted_at=datetime.now()
            )
        assert "raw_text" in str(exc_info.value).lower()

        # Empty raw_text
        with pytest.raises(ValidationError) as exc_info:
            RawContent(
                url="https://example.com",
                source_type=ContentSource.WEB,
                raw_text="",
                metadata={},
                extracted_at=datetime.now()
            )
        assert "raw_text" in str(exc_info.value).lower()

    def test_raw_content_metadata_optional(self):
        """Test that metadata can be empty dict."""
        # Arrange & Act
        content = RawContent(
            url="https://example.com",
            source_type=ContentSource.TEXT,
            raw_text="Simple text content",
            metadata={},
            extracted_at=datetime.now()
        )

        # Assert
        assert content.metadata == {}

    def test_raw_content_extracted_at_defaults_to_now(self):
        """Test that extracted_at defaults to current time if not provided."""
        # Arrange
        before = datetime.now()

        # Act
        content = RawContent(
            url="https://example.com",
            source_type=ContentSource.WEB,
            raw_text="content",
            metadata={}
        )

        after = datetime.now()

        # Assert
        assert before <= content.extracted_at <= after

    def test_raw_content_pdf_source(self):
        """Test creating RawContent for PDF source."""
        # Arrange & Act
        content = RawContent(
            url="https://example.com/document.pdf",
            source_type=ContentSource.PDF,
            raw_text="Extracted PDF text content",
            metadata={
                "pages": 10,
                "file_size": 1024000,
                "author": "Jane Smith"
            },
            extracted_at=datetime.now()
        )

        # Assert
        assert content.source_type == ContentSource.PDF
        assert content.metadata["pages"] == 10
        assert ".pdf" in str(content.url)

    def test_raw_content_json_serialization(self):
        """Test that RawContent can be serialized to JSON."""
        # Arrange
        content = RawContent(
            url="https://example.com",
            source_type=ContentSource.WEB,
            raw_text="Test content",
            metadata={"key": "value"},
            extracted_at=datetime(2025, 10, 9, 12, 0, 0)
        )

        # Act
        json_data = content.model_dump()

        # Assert
        assert "url" in json_data
        assert json_data["source_type"] == "web"
        assert json_data["raw_text"] == "Test content"
        assert json_data["metadata"]["key"] == "value"

    def test_raw_content_from_json(self):
        """Test creating RawContent from JSON data."""
        # Arrange
        json_data = {
            "url": "https://test.com",
            "source_type": "youtube",
            "raw_text": "Video content",
            "metadata": {"views": 1000},
            "extracted_at": "2025-10-09T12:00:00"
        }

        # Act
        content = RawContent(**json_data)

        # Assert
        assert content.source_type == ContentSource.YOUTUBE
        assert content.metadata["views"] == 1000

    def test_raw_content_large_text(self):
        """Test RawContent can handle large text content."""
        # Arrange
        large_text = "A" * 1000000  # 1MB of text

        # Act
        content = RawContent(
            url="https://example.com/long",
            source_type=ContentSource.WEB,
            raw_text=large_text,
            metadata={},
            extracted_at=datetime.now()
        )

        # Assert
        assert len(content.raw_text) == 1000000

    def test_raw_content_special_characters_in_text(self):
        """Test RawContent handles special characters and unicode."""
        # Arrange
        special_text = "Hello 世界 🌍 Test €$¥ \n\t Special chars!"

        # Act
        content = RawContent(
            url="https://example.com",
            source_type=ContentSource.WEB,
            raw_text=special_text,
            metadata={},
            extracted_at=datetime.now()
        )

        # Assert
        assert content.raw_text == special_text
        assert "世界" in content.raw_text
        assert "🌍" in content.raw_text
