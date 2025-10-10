"""Unit tests for LibraryFile Pydantic model.

Following TDD RED-GREEN-REFACTOR cycle.
"""
from datetime import datetime
from pathlib import Path
import pytest
from pydantic import ValidationError
from app.core.models import LibraryFile
from app.core.types import ContentSource


class TestLibraryFile:
    """Test suite for LibraryFile Pydantic model."""

    def test_library_file_valid_tier_a(self):
        """Test creating valid LibraryFile in tier-a."""
        # Arrange
        data = {
            "file_path": Path("/library/tier-a/document.md"),
            "url": "https://example.com/article",
            "source_type": ContentSource.WEB,
            "tier": "tier-a",
            "quality_score": 9.5,
            "title": "Excellent Article",
            "tags": ["ai", "ml"],
            "created_at": datetime(2025, 10, 9, 12, 0, 0)
        }
        
        # Act
        file = LibraryFile(**data)
        
        # Assert
        assert file.file_path == Path("/library/tier-a/document.md")
        assert file.tier == "tier-a"
        assert file.quality_score == 9.5
        assert "ai" in file.tags

    def test_library_file_tier_validation(self):
        """Test that tier must be tier-a, tier-b, tier-c, or tier-d."""
        # Valid tiers
        for tier in ["tier-a", "tier-b", "tier-c", "tier-d"]:
            file = LibraryFile(
                file_path=Path(f"/library/{tier}/file.md"),
                url="https://example.com",
                source_type=ContentSource.WEB,
                tier=tier,
                quality_score=8.0,
                title="Test",
                tags=[]
            )
            assert file.tier == tier
        
        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            LibraryFile(
                file_path=Path("/library/invalid/file.md"),
                url="https://example.com",
                source_type=ContentSource.WEB,
                tier="tier-z",
                quality_score=8.0,
                title="Test",
                tags=[]
            )
        assert "tier" in str(exc_info.value).lower()

    def test_library_file_quality_score_bounds(self):
        """Test that quality_score must be between 0 and 10."""
        # Test lower bound violation
        with pytest.raises(ValidationError) as exc_info:
            LibraryFile(
                file_path=Path("/library/tier-d/file.md"),
                url="https://example.com",
                source_type=ContentSource.WEB,
                tier="tier-d",
                quality_score=-1.0,
                title="Test",
                tags=[]
            )
        assert "quality_score" in str(exc_info.value).lower()
        
        # Test upper bound violation
        with pytest.raises(ValidationError) as exc_info:
            LibraryFile(
                file_path=Path("/library/tier-a/file.md"),
                url="https://example.com",
                source_type=ContentSource.WEB,
                tier="tier-a",
                quality_score=11.0,
                title="Test",
                tags=[]
            )
        assert "quality_score" in str(exc_info.value).lower()
        
        # Valid boundaries
        file_min = LibraryFile(
            file_path=Path("/library/tier-d/file.md"),
            url="https://example.com",
            source_type=ContentSource.WEB,
            tier="tier-d",
            quality_score=0.0,
            title="Minimum",
            tags=[]
        )
        assert file_min.quality_score == 0.0
        
        file_max = LibraryFile(
            file_path=Path("/library/tier-a/file.md"),
            url="https://example.com",
            source_type=ContentSource.WEB,
            tier="tier-a",
            quality_score=10.0,
            title="Maximum",
            tags=[]
        )
        assert file_max.quality_score == 10.0

    def test_library_file_created_at_defaults(self):
        """Test that created_at defaults to current time."""
        before = datetime.now()
        
        file = LibraryFile(
            file_path=Path("/library/tier-b/file.md"),
            url="https://example.com",
            source_type=ContentSource.YOUTUBE,
            tier="tier-b",
            quality_score=7.5,
            title="Video",
            tags=[]
        )
        
        after = datetime.now()
        assert before <= file.created_at <= after

    def test_library_file_different_source_types(self):
        """Test LibraryFile with different source types."""
        for source_type in [ContentSource.WEB, ContentSource.YOUTUBE, ContentSource.PDF, ContentSource.TEXT]:
            file = LibraryFile(
                file_path=Path(f"/library/tier-b/{source_type.value}.md"),
                url="https://example.com",
                source_type=source_type,
                tier="tier-b",
                quality_score=7.0,
                title=f"{source_type.value} content",
                tags=[]
            )
            assert file.source_type == source_type

    def test_library_file_tags_optional(self):
        """Test that tags can be empty."""
        file = LibraryFile(
            file_path=Path("/library/tier-c/file.md"),
            url="https://example.com",
            source_type=ContentSource.TEXT,
            tier="tier-c",
            quality_score=5.5,
            title="Simple",
            tags=[]
        )
        assert file.tags == []

    def test_library_file_with_multiple_tags(self):
        """Test LibraryFile with multiple tags."""
        file = LibraryFile(
            file_path=Path("/library/tier-a/research.md"),
            url="https://example.com/research",
            source_type=ContentSource.PDF,
            tier="tier-a",
            quality_score=9.0,
            title="Research Paper",
            tags=["research", "ai", "deep-learning", "neural-networks", "transformers"]
        )
        assert len(file.tags) == 5
        assert "transformers" in file.tags

    def test_library_file_path_object(self):
        """Test that file_path is a Path object."""
        file = LibraryFile(
            file_path=Path("/library/tier-a/doc.md"),
            url="https://example.com",
            source_type=ContentSource.WEB,
            tier="tier-a",
            quality_score=8.5,
            title="Document",
            tags=[]
        )
        assert isinstance(file.file_path, Path)
        assert file.file_path.name == "doc.md"

    def test_library_file_json_serialization(self):
        """Test that LibraryFile can be serialized."""
        file = LibraryFile(
            file_path=Path("/library/tier-b/test.md"),
            url="https://example.com",
            source_type=ContentSource.WEB,
            tier="tier-b",
            quality_score=7.5,
            title="Test",
            tags=["tag1", "tag2"],
            created_at=datetime(2025, 10, 9, 12, 0, 0)
        )
        
        json_data = file.model_dump()
        assert json_data["tier"] == "tier-b"
        assert json_data["quality_score"] == 7.5
        assert json_data["source_type"] == "web"

    def test_library_file_tier_quality_consistency(self):
        """Test various tier-quality combinations."""
        # High quality in tier-a
        file_a = LibraryFile(
            file_path=Path("/library/tier-a/excellent.md"),
            url="https://example.com",
            source_type=ContentSource.WEB,
            tier="tier-a",
            quality_score=9.2,
            title="Excellent",
            tags=[]
        )
        assert file_a.tier == "tier-a"
        assert file_a.quality_score >= 9.0
        
        # Medium quality in tier-c
        file_c = LibraryFile(
            file_path=Path("/library/tier-c/medium.md"),
            url="https://example.com",
            source_type=ContentSource.WEB,
            tier="tier-c",
            quality_score=6.0,
            title="Medium",
            tags=[]
        )
        assert file_c.tier == "tier-c"
        assert 5.0 <= file_c.quality_score < 7.0
