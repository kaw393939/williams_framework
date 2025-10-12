"""RED TESTS FOR S4-502: Library statistics dashboard.

These tests verify that:
1. LibraryStatsComponent calculates tier distribution
2. Component computes average quality score
3. Component tracks total item count
4. Component analyzes tag frequency
5. Integration with Streamlit chart rendering
"""

import pytest


@pytest.mark.unit
def test_stats_component_calculates_tier_distribution():
    """Test that component calculates distribution of items across tiers."""
    from datetime import datetime

    from app.core.models import LibraryFile
    from app.core.types import ContentSource
    from app.presentation.components.library_stats import LibraryStatsComponent

    items = [
        LibraryFile(
            url="https://example.com/1",
            source_type=ContentSource.WEB,
            file_path="/tier-a/test1.md",
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
            file_path="/tier-a/test2.md",
            title="Test 2",
            summary="Summary 2",
            tags=["test"],
            tier="tier-a",
            quality_score=9.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        LibraryFile(
            url="https://example.com/3",
            source_type=ContentSource.WEB,
            file_path="/tier-b/test3.md",
            title="Test 3",
            summary="Summary 3",
            tags=["test"],
            tier="tier-b",
            quality_score=7.5,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]

    component = LibraryStatsComponent()
    stats = component.calculate_stats(items)

    assert stats["tier_distribution"]["tier-a"] == 2
    assert stats["tier_distribution"]["tier-b"] == 1
    assert stats["tier_distribution"]["tier-c"] == 0


@pytest.mark.unit
def test_stats_component_calculates_average_quality_score():
    """Test that component calculates average quality score."""
    from datetime import datetime

    from app.core.models import LibraryFile
    from app.core.types import ContentSource
    from app.presentation.components.library_stats import LibraryStatsComponent

    items = [
        LibraryFile(
            url="https://example.com/1",
            source_type=ContentSource.WEB,
            file_path="/test1.md",
            title="Test 1",
            summary="Summary",
            tags=[],
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
            tags=[],
            tier="tier-b",
            quality_score=7.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]

    component = LibraryStatsComponent()
    stats = component.calculate_stats(items)

    assert stats["average_quality_score"] == 8.0


@pytest.mark.unit
def test_stats_component_tracks_total_count():
    """Test that component tracks total item count."""
    from datetime import datetime

    from app.core.models import LibraryFile
    from app.core.types import ContentSource
    from app.presentation.components.library_stats import LibraryStatsComponent

    items = [
        LibraryFile(
            url=f"https://example.com/{i}",
            source_type=ContentSource.WEB,
            file_path=f"/test{i}.md",
            title=f"Test {i}",
            summary="Summary",
            tags=[],
            tier="tier-a",
            quality_score=9.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        for i in range(5)
    ]

    component = LibraryStatsComponent()
    stats = component.calculate_stats(items)

    assert stats["total_count"] == 5


@pytest.mark.unit
def test_stats_component_analyzes_tag_frequency():
    """Test that component analyzes tag frequency."""
    from datetime import datetime

    from app.core.models import LibraryFile
    from app.core.types import ContentSource
    from app.presentation.components.library_stats import LibraryStatsComponent

    items = [
        LibraryFile(
            url="https://example.com/1",
            source_type=ContentSource.WEB,
            file_path="/test1.md",
            title="Test 1",
            summary="Summary",
            tags=["python", "machine-learning"],
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
            tags=["machine-learning"],
            tier="tier-a",
            quality_score=9.5,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]

    component = LibraryStatsComponent()
    stats = component.calculate_stats(items)

    assert stats["tag_frequency"]["python"] == 2
    assert stats["tag_frequency"]["machine-learning"] == 2
    assert stats["tag_frequency"]["web"] == 1


@pytest.mark.unit
def test_stats_component_handles_empty_library():
    """Test that component handles empty library gracefully."""
    from app.presentation.components.library_stats import LibraryStatsComponent

    component = LibraryStatsComponent()
    stats = component.calculate_stats([])

    assert stats["total_count"] == 0
    assert stats["average_quality_score"] == 0.0
    assert stats["tier_distribution"] == {"tier-a": 0, "tier-b": 0, "tier-c": 0}
    assert stats["tag_frequency"] == {}


@pytest.mark.unit
def test_stats_component_returns_top_tags():
    """Test that component returns top N most frequent tags."""
    from datetime import datetime

    from app.core.models import LibraryFile
    from app.core.types import ContentSource
    from app.presentation.components.library_stats import LibraryStatsComponent

    items = [
        LibraryFile(
            url=f"https://example.com/{i}",
            source_type=ContentSource.WEB,
            file_path=f"/test{i}.md",
            title=f"Test {i}",
            summary="Summary",
            tags=["python"] * 3 + ["java"] * 2 + ["rust"],
            tier="tier-a",
            quality_score=9.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        for i in range(1)
    ]

    component = LibraryStatsComponent()
    top_tags = component.get_top_tags(items, top_n=2)

    assert len(top_tags) == 2
    assert top_tags[0][0] == "python"
    assert top_tags[0][1] == 3
    assert top_tags[1][0] == "java"
    assert top_tags[1][1] == 2


@pytest.mark.unit
def test_stats_component_has_qa_ids():
    """Test that stats component has QA IDs for testing."""
    from app.presentation.components.library_stats import LibraryStatsComponent

    component = LibraryStatsComponent()

    assert hasattr(component, "total_count_qa_id")
    assert hasattr(component, "avg_score_qa_id")
    assert hasattr(component, "tier_chart_qa_id")
    assert hasattr(component, "tag_chart_qa_id")


@pytest.mark.integration
def test_stats_component_formats_tier_chart_data():
    """Test that component formats data for Streamlit tier distribution chart."""
    from datetime import datetime

    from app.core.models import LibraryFile
    from app.core.types import ContentSource
    from app.presentation.components.library_stats import LibraryStatsComponent

    items = [
        LibraryFile(
            url=f"https://example.com/{i}",
            source_type=ContentSource.WEB,
            file_path=f"/tier-a/test{i}.md",
            title=f"Test {i}",
            summary="Summary",
            tags=[],
            tier="tier-a",
            quality_score=9.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        for i in range(3)
    ]

    component = LibraryStatsComponent()
    chart_data = component.format_tier_chart_data(items)

    assert "tier" in chart_data
    assert "count" in chart_data
    assert len(chart_data["tier"]) == 3  # tier-a, tier-b, tier-c
    assert chart_data["count"][0] == 3  # tier-a count


@pytest.mark.integration
def test_stats_component_formats_tag_chart_data():
    """Test that component formats data for tag frequency chart."""
    from datetime import datetime

    from app.core.models import LibraryFile
    from app.core.types import ContentSource
    from app.presentation.components.library_stats import LibraryStatsComponent

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
    ]

    component = LibraryStatsComponent()
    chart_data = component.format_tag_chart_data(items, top_n=5)

    assert "tag" in chart_data
    assert "count" in chart_data
    assert "python" in chart_data["tag"]
    assert "web" in chart_data["tag"]
