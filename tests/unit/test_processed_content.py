"""Unit tests for ProcessedContent Pydantic model.

Following TDD RED-GREEN-REFACTOR cycle.
"""
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.core.models import ProcessedContent, ScreeningResult
from app.core.types import ContentSource


class TestProcessedContent:
    """Test suite for ProcessedContent Pydantic model."""

    def test_processed_content_valid(self):
        """Test creating valid ProcessedContent."""
        # Arrange
        screening = ScreeningResult(
            screening_score=8.5,
            decision="ACCEPT",
            reasoning="High quality",
            estimated_quality=8.7
        )

        data = {
            "url": "https://example.com/article",
            "source_type": ContentSource.WEB,
            "title": "Great Article",
            "summary": "This is a comprehensive summary of the article content.",
            "key_points": ["Point 1", "Point 2", "Point 3"],
            "tags": ["ai", "machine-learning", "technology"],
            "screening_result": screening,
            "processed_at": datetime(2025, 10, 9, 12, 0, 0)
        }

        # Act
        content = ProcessedContent(**data)

        # Assert
        assert str(content.url) == "https://example.com/article"
        assert content.source_type == ContentSource.WEB
        assert content.title == "Great Article"
        assert len(content.key_points) == 3
        assert "ai" in content.tags
        assert content.screening_result.decision == "ACCEPT"

    def test_processed_content_title_required(self):
        """Test that title is required and non-empty."""
        screening = ScreeningResult(
            screening_score=8.0,
            decision="ACCEPT",
            reasoning="Good",
            estimated_quality=8.0
        )

        # Missing title
        with pytest.raises(ValidationError) as exc_info:
            ProcessedContent(
                url="https://example.com",
                source_type=ContentSource.WEB,
                summary="Summary",
                key_points=["Point"],
                tags=[],
                screening_result=screening
            )
        assert "title" in str(exc_info.value).lower()

        # Empty title
        with pytest.raises(ValidationError) as exc_info:
            ProcessedContent(
                url="https://example.com",
                source_type=ContentSource.WEB,
                title="",
                summary="Summary",
                key_points=["Point"],
                tags=[],
                screening_result=screening
            )
        assert "title" in str(exc_info.value).lower()

    def test_processed_content_summary_required(self):
        """Test that summary is required and non-empty."""
        screening = ScreeningResult(
            screening_score=8.0,
            decision="ACCEPT",
            reasoning="Good",
            estimated_quality=8.0
        )

        with pytest.raises(ValidationError) as exc_info:
            ProcessedContent(
                url="https://example.com",
                source_type=ContentSource.WEB,
                title="Title",
                key_points=["Point"],
                tags=[],
                screening_result=screening
            )
        assert "summary" in str(exc_info.value).lower()

    def test_processed_content_key_points_can_be_empty(self):
        """Test that key_points can be an empty list."""
        screening = ScreeningResult(
            screening_score=5.0,
            decision="MAYBE",
            reasoning="Uncertain",
            estimated_quality=5.0
        )

        # Act
        content = ProcessedContent(
            url="https://example.com",
            source_type=ContentSource.TEXT,
            title="Simple",
            summary="Brief summary",
            key_points=[],
            tags=[],
            screening_result=screening
        )

        # Assert
        assert content.key_points == []

    def test_processed_content_tags_can_be_empty(self):
        """Test that tags can be an empty list."""
        screening = ScreeningResult(
            screening_score=7.0,
            decision="ACCEPT",
            reasoning="Good",
            estimated_quality=7.0
        )

        # Act
        content = ProcessedContent(
            url="https://example.com",
            source_type=ContentSource.PDF,
            title="Document",
            summary="PDF summary",
            key_points=["Point"],
            tags=[],
            screening_result=screening
        )

        # Assert
        assert content.tags == []

    def test_processed_content_processed_at_defaults(self):
        """Test that processed_at defaults to current time."""
        screening = ScreeningResult(
            screening_score=8.0,
            decision="ACCEPT",
            reasoning="Good",
            estimated_quality=8.0
        )

        before = datetime.now()

        content = ProcessedContent(
            url="https://example.com",
            source_type=ContentSource.WEB,
            title="Test",
            summary="Summary",
            key_points=[],
            tags=[],
            screening_result=screening
        )

        after = datetime.now()

        assert before <= content.processed_at <= after

    def test_processed_content_with_multiple_tags(self):
        """Test ProcessedContent with multiple tags."""
        screening = ScreeningResult(
            screening_score=9.0,
            decision="ACCEPT",
            reasoning="Excellent",
            estimated_quality=9.2
        )

        content = ProcessedContent(
            url="https://example.com",
            source_type=ContentSource.YOUTUBE,
            title="Video Title",
            summary="Video about AI and ML",
            key_points=["AI concepts", "ML applications", "Future trends"],
            tags=["artificial-intelligence", "machine-learning", "deep-learning", "neural-networks"],
            screening_result=screening
        )

        assert len(content.tags) == 4
        assert "neural-networks" in content.tags

    def test_processed_content_json_serialization(self):
        """Test that ProcessedContent can be serialized."""
        screening = ScreeningResult(
            screening_score=8.0,
            decision="ACCEPT",
            reasoning="Good",
            estimated_quality=8.0
        )

        content = ProcessedContent(
            url="https://example.com",
            source_type=ContentSource.WEB,
            title="Test",
            summary="Summary",
            key_points=["Point 1"],
            tags=["tag1"],
            screening_result=screening,
            processed_at=datetime(2025, 10, 9, 12, 0, 0)
        )

        json_data = content.model_dump()

        assert json_data["title"] == "Test"
        assert json_data["source_type"] == "web"
        assert json_data["screening_result"]["decision"] == "ACCEPT"

    def test_processed_content_rejected(self):
        """Test ProcessedContent with REJECT decision."""
        screening = ScreeningResult(
            screening_score=2.0,
            decision="REJECT",
            reasoning="Low quality content",
            estimated_quality=2.5
        )

        content = ProcessedContent(
            url="https://example.com/bad",
            source_type=ContentSource.WEB,
            title="Low Quality",
            summary="This content is not suitable",
            key_points=[],
            tags=[],
            screening_result=screening
        )

        assert content.screening_result.decision == "REJECT"
        assert content.screening_result.screening_score == 2.0
