"""RED TESTS FOR S4-503: Tag-based navigation and filtering.

These tests verify that:
1. TagFilter component supports multi-select dropdown
2. AND logic filters items matching ALL selected tags
3. OR logic filters items matching ANY selected tag
4. Integration with tier filtering from S3-402
5. Empty tag selection returns all items
"""
import pytest
from unittest.mock import Mock


@pytest.mark.unit
def test_tag_filter_has_qa_id():
    """Test that tag filter has QA ID for test automation."""
    from app.presentation.components.tag_filter import TagFilter
    
    tag_filter = TagFilter()
    
    assert hasattr(tag_filter, "qa_id")
    assert tag_filter.qa_id == "tag-filter"


@pytest.mark.unit
def test_tag_filter_get_all_tags_from_items():
    """Test that component extracts all unique tags from library items."""
    from app.presentation.components.tag_filter import TagFilter
    from app.core.models import LibraryFile
    from app.core.types import ContentSource
    from datetime import datetime
    
    items = [
        LibraryFile(
            url="https://example.com/1",
            source_type=ContentSource.WEB,
            file_path="/test1.md",
            title="Test 1",
            summary="Summary",
            tags=["python", "web"],
            tier="tier-a",
            quality_score=9.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        LibraryFile(
            url="https://example.com/2",
            source_type=ContentSource.WEB,
            file_path="/test2.md",
            title="Test 2",
            summary="Summary",
            tags=["python", "data"],
            tier="tier-b",
            quality_score=7.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]
    
    tag_filter = TagFilter()
    all_tags = tag_filter.get_all_tags(items)
    
    assert set(all_tags) == {"python", "web", "data"}


@pytest.mark.unit
def test_tag_filter_with_and_logic():
    """Test that AND logic returns items matching ALL selected tags."""
    from app.presentation.components.tag_filter import TagFilter
    from app.core.models import LibraryFile
    from app.core.types import ContentSource
    from datetime import datetime
    
    items = [
        LibraryFile(
            url="https://example.com/1",
            source_type=ContentSource.WEB,
            file_path="/test1.md",
            title="Test 1",
            summary="Summary",
            tags=["python", "web", "tutorial"],
            tier="tier-a",
            quality_score=9.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        LibraryFile(
            url="https://example.com/2",
            source_type=ContentSource.WEB,
            file_path="/test2.md",
            title="Test 2",
            summary="Summary",
            tags=["python", "web"],
            tier="tier-b",
            quality_score=7.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        LibraryFile(
            url="https://example.com/3",
            source_type=ContentSource.WEB,
            file_path="/test3.md",
            title="Test 3",
            summary="Summary",
            tags=["python"],
            tier="tier-a",
            quality_score=8.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]
    
    tag_filter = TagFilter()
    filtered = tag_filter.filter_by_tags(
        items,
        selected_tags=["python", "web"],
        logic="AND"
    )
    
    # Only items 1 and 2 have BOTH python AND web
    assert len(filtered) == 2
    assert all("python" in item.tags and "web" in item.tags for item in filtered)


@pytest.mark.unit
def test_tag_filter_with_or_logic():
    """Test that OR logic returns items matching ANY selected tag."""
    from app.presentation.components.tag_filter import TagFilter
    from app.core.models import LibraryFile
    from app.core.types import ContentSource
    from datetime import datetime
    
    items = [
        LibraryFile(
            url="https://example.com/1",
            source_type=ContentSource.WEB,
            file_path="/test1.md",
            title="Test 1",
            summary="Summary",
            tags=["python"],
            tier="tier-a",
            quality_score=9.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        LibraryFile(
            url="https://example.com/2",
            source_type=ContentSource.WEB,
            file_path="/test2.md",
            title="Test 2",
            summary="Summary",
            tags=["java"],
            tier="tier-b",
            quality_score=7.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        LibraryFile(
            url="https://example.com/3",
            source_type=ContentSource.WEB,
            file_path="/test3.md",
            title="Test 3",
            summary="Summary",
            tags=["rust"],
            tier="tier-a",
            quality_score=8.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]
    
    tag_filter = TagFilter()
    filtered = tag_filter.filter_by_tags(
        items,
        selected_tags=["python", "java"],
        logic="OR"
    )
    
    # Items 1 and 2 have either python OR java
    assert len(filtered) == 2
    assert any("python" in item.tags or "java" in item.tags for item in filtered)


@pytest.mark.unit
def test_tag_filter_empty_selection_returns_all():
    """Test that empty tag selection returns all items."""
    from app.presentation.components.tag_filter import TagFilter
    from app.core.models import LibraryFile
    from app.core.types import ContentSource
    from datetime import datetime
    
    items = [
        LibraryFile(
            url=f"https://example.com/{i}",
            source_type=ContentSource.WEB,
            file_path=f"/test{i}.md",
            title=f"Test {i}",
            summary="Summary",
            tags=["tag"],
            tier="tier-a",
            quality_score=9.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        for i in range(3)
    ]
    
    tag_filter = TagFilter()
    filtered = tag_filter.filter_by_tags(items, selected_tags=[], logic="AND")
    
    assert len(filtered) == 3


@pytest.mark.integration
def test_combined_tier_and_tag_filtering():
    """Test that tier and tag filtering can be combined."""
    from app.presentation.components.tag_filter import TagFilter
    from app.presentation.components.tier_filter import TierFilter
    from app.core.models import LibraryFile
    from app.core.types import ContentSource
    from datetime import datetime
    
    items = [
        LibraryFile(
            url="https://example.com/1",
            source_type=ContentSource.WEB,
            file_path="/tier-a/test1.md",
            title="Test 1",
            summary="Summary",
            tags=["python", "web"],
            tier="tier-a",
            quality_score=9.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        LibraryFile(
            url="https://example.com/2",
            source_type=ContentSource.WEB,
            file_path="/tier-b/test2.md",
            title="Test 2",
            summary="Summary",
            tags=["python"],
            tier="tier-b",
            quality_score=7.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        LibraryFile(
            url="https://example.com/3",
            source_type=ContentSource.WEB,
            file_path="/tier-a/test3.md",
            title="Test 3",
            summary="Summary",
            tags=["java"],
            tier="tier-a",
            quality_score=8.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]
    
    # First filter by tier
    tier_filter = TierFilter()
    tier_filtered = tier_filter.filter_items(items, selected_tier="tier-a")
    
    # Then filter by tags
    tag_filter = TagFilter()
    final_filtered = tag_filter.filter_by_tags(
        tier_filtered,
        selected_tags=["python"],
        logic="OR"
    )
    
    # Should only have item 1 (tier-a AND python tag)
    assert len(final_filtered) == 1
    assert final_filtered[0].tier == "tier-a"
    assert "python" in final_filtered[0].tags


@pytest.mark.unit
def test_tag_filter_returns_empty_when_no_matches():
    """Test that filter returns empty list when no items match."""
    from app.presentation.components.tag_filter import TagFilter
    from app.core.models import LibraryFile
    from app.core.types import ContentSource
    from datetime import datetime
    
    items = [
        LibraryFile(
            url="https://example.com/1",
            source_type=ContentSource.WEB,
            file_path="/test1.md",
            title="Test 1",
            summary="Summary",
            tags=["python"],
            tier="tier-a",
            quality_score=9.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]
    
    tag_filter = TagFilter()
    filtered = tag_filter.filter_by_tags(
        items,
        selected_tags=["rust", "go"],
        logic="AND"
    )
    
    assert len(filtered) == 0


@pytest.mark.unit
def test_tag_filter_case_sensitive():
    """Test that tag filtering is case-sensitive."""
    from app.presentation.components.tag_filter import TagFilter
    from app.core.models import LibraryFile
    from app.core.types import ContentSource
    from datetime import datetime
    
    items = [
        LibraryFile(
            url="https://example.com/1",
            source_type=ContentSource.WEB,
            file_path="/test1.md",
            title="Test 1",
            summary="Summary",
            tags=["Python"],
            tier="tier-a",
            quality_score=9.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]
    
    tag_filter = TagFilter()
    filtered = tag_filter.filter_by_tags(
        items,
        selected_tags=["python"],  # lowercase
        logic="OR"
    )
    
    # Should not match "Python" (uppercase P)
    assert len(filtered) == 0
