"""RED TESTS FOR S3-402: Library tier filter UI.

These tests verify that:
1. Tier dropdown options match config thresholds
2. Selection filters library table snapshot
3. Component integrates with Streamlit state
"""
import pytest

from app.presentation.components.tier_filter import TierFilter, get_tier_options


@pytest.mark.unit
def test_get_tier_options_returns_all_tiers():
    """Test that tier options include all configured tiers."""
    options = get_tier_options()

    assert "All" in options
    assert "tier-a" in options
    assert "tier-b" in options
    assert "tier-c" in options


@pytest.mark.unit
def test_get_tier_options_includes_all_filter():
    """Test that 'All' option is available for showing all items."""
    options = get_tier_options()

    assert options[0] == "All", "All should be the first option"


@pytest.mark.integration
def test_tier_filter_component_has_qa_id():
    """Test that tier filter has QA ID for test automation."""
    tier_filter = TierFilter()

    assert hasattr(tier_filter, "qa_id")
    assert isinstance(tier_filter.qa_id, str)
    assert tier_filter.qa_id == "tier-filter"


@pytest.mark.unit
def test_filter_library_items_returns_all_when_all_selected():
    """Test that filtering with 'All' returns all items."""
    from datetime import datetime

    from app.core.models import LibraryFile
    from app.core.types import ContentSource

    items = [
        LibraryFile(
            url="https://example.com/1",
            source_type=ContentSource.WEB,
            file_path="/library/tier-a/test1.md",
            title="Test 1",
            summary="Summary 1",
            tags=["test"],
            tier="tier-a",
            quality_score=9.5,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        LibraryFile(
            url="https://example.com/2",
            source_type=ContentSource.WEB,
            file_path="/library/tier-b/test2.md",
            title="Test 2",
            summary="Summary 2",
            tags=["test"],
            tier="tier-b",
            quality_score=7.5,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]

    tier_filter = TierFilter()
    filtered = tier_filter.filter_items(items, selected_tier="All")

    assert len(filtered) == 2


@pytest.mark.unit
def test_filter_library_items_filters_by_tier_a():
    """Test that filtering by tier-a returns only tier-a items."""
    from datetime import datetime

    from app.core.models import LibraryFile
    from app.core.types import ContentSource

    items = [
        LibraryFile(
            url="https://example.com/1",
            source_type=ContentSource.WEB,
            file_path="/library/tier-a/test1.md",
            title="Test 1",
            summary="Summary 1",
            tags=["test"],
            tier="tier-a",
            quality_score=9.5,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        LibraryFile(
            url="https://example.com/2",
            source_type=ContentSource.WEB,
            file_path="/library/tier-b/test2.md",
            title="Test 2",
            summary="Summary 2",
            tags=["test"],
            tier="tier-b",
            quality_score=7.5,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]

    tier_filter = TierFilter()
    filtered = tier_filter.filter_items(items, selected_tier="tier-a")

    assert len(filtered) == 1
    assert filtered[0].tier == "tier-a"


@pytest.mark.unit
def test_filter_library_items_filters_by_tier_b():
    """Test that filtering by tier-b returns only tier-b items."""
    from datetime import datetime

    from app.core.models import LibraryFile
    from app.core.types import ContentSource

    items = [
        LibraryFile(
            url="https://example.com/1",
            source_type=ContentSource.WEB,
            file_path="/library/tier-a/test1.md",
            title="Test 1",
            summary="Summary 1",
            tags=["test"],
            tier="tier-a",
            quality_score=9.5,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        LibraryFile(
            url="https://example.com/2",
            source_type=ContentSource.WEB,
            file_path="/library/tier-b/test2.md",
            title="Test 2",
            summary="Summary 2",
            tags=["test"],
            tier="tier-b",
            quality_score=7.5,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]

    tier_filter = TierFilter()
    filtered = tier_filter.filter_items(items, selected_tier="tier-b")

    assert len(filtered) == 1
    assert filtered[0].tier == "tier-b"


@pytest.mark.unit
def test_filter_library_items_returns_empty_when_no_matches():
    """Test that filtering returns empty list when no items match."""
    from datetime import datetime

    from app.core.models import LibraryFile
    from app.core.types import ContentSource

    items = [
        LibraryFile(
            url="https://example.com/1",
            source_type=ContentSource.WEB,
            file_path="/library/tier-a/test1.md",
            title="Test 1",
            summary="Summary 1",
            tags=["test"],
            tier="tier-a",
            quality_score=9.5,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]

    tier_filter = TierFilter()
    filtered = tier_filter.filter_items(items, selected_tier="tier-c")

    assert len(filtered) == 0
