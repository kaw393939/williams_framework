"""Unit tests for TierFilter component."""
import pytest

from app.core.models import LibraryFile
from app.presentation.components.tier_filter import TierFilter, get_tier_options
from pathlib import Path


def test_get_tier_options():
    """Test that tier options include All and all tiers."""
    options = get_tier_options()
    assert options == ["All", "tier-a", "tier-b", "tier-c"]


class TestTierFilter:
    """Tests for TierFilter component."""

    @pytest.fixture
    def tier_filter(self):
        """Create TierFilter instance."""
        return TierFilter()

    @pytest.fixture
    def sample_files(self):
        """Create sample library files with different tiers."""
        return [
            LibraryFile(
                file_path=Path("tier-a/file1.json"),
                url="https://example.com/1",
                source_type="web",
                tier="tier-a",
                quality_score=0.95,
                title="Tier A File",
                summary="High quality",
                key_points=["point1"],
                tags=["tag1"],
                created_at="2024-01-01"
            ),
            LibraryFile(
                file_path=Path("tier-b/file2.json"),
                url="https://example.com/2",
                source_type="web",
                tier="tier-b",
                quality_score=0.75,
                title="Tier B File",
                summary="Medium quality",
                key_points=["point2"],
                tags=["tag2"],
                created_at="2024-01-02"
            ),
            LibraryFile(
                file_path=Path("tier-c/file3.json"),
                url="https://example.com/3",
                source_type="web",
                tier="tier-c",
                quality_score=0.55,
                title="Tier C File",
                summary="Lower quality",
                key_points=["point3"],
                tags=["tag3"],
                created_at="2024-01-03"
            ),
        ]

    def test_tier_filter_has_qa_id(self, tier_filter):
        """Test that tier filter has correct QA ID."""
        assert tier_filter.qa_id == "tier-filter"

    def test_filter_all_returns_all_items(self, tier_filter, sample_files):
        """Test that filtering by 'All' returns all items."""
        result = tier_filter.filter_items(sample_files, "All")
        assert len(result) == 3
        assert result == sample_files

    def test_filter_tier_a(self, tier_filter, sample_files):
        """Test filtering for tier-a only."""
        result = tier_filter.filter_items(sample_files, "tier-a")
        assert len(result) == 1
        assert result[0].tier == "tier-a"

    def test_filter_tier_b(self, tier_filter, sample_files):
        """Test filtering for tier-b only."""
        result = tier_filter.filter_items(sample_files, "tier-b")
        assert len(result) == 1
        assert result[0].tier == "tier-b"

    def test_filter_tier_c(self, tier_filter, sample_files):
        """Test filtering for tier-c only."""
        result = tier_filter.filter_items(sample_files, "tier-c")
        assert len(result) == 1
        assert result[0].tier == "tier-c"

    def test_filter_nonexistent_tier(self, tier_filter, sample_files):
        """Test filtering for non-existent tier returns empty list."""
        result = tier_filter.filter_items(sample_files, "tier-d")
        assert len(result) == 0
