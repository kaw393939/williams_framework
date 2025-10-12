"""Test suite for ExportService.

Tests the library export functionality with markdown generation,
filtering, and ZIP archive creation.
"""

from datetime import UTC, datetime
from io import BytesIO
from zipfile import ZipFile

import pytest

from app.core.models import ContentSource, LibraryFile
from app.services.export_service import ExportService


@pytest.fixture
def sample_items():
    """Create sample library items for testing."""
    return [
        LibraryFile(
            title="Python Best Practices",
            url="https://example.com/python",
            file_path="library/tier-a/python-best-practices.md",
            tags=["python", "programming"],
            tier="tier-a",
            source_type=ContentSource.WEB,
            quality_score=9.5,
            created_at=datetime(2024, 1, 15, tzinfo=UTC),
        ),
        LibraryFile(
            title="JavaScript Fundamentals",
            url="https://example.com/js",
            file_path="library/tier-b/javascript-fundamentals.md",
            tags=["javascript", "programming"],
            tier="tier-b",
            source_type=ContentSource.WEB,
            quality_score=8.2,
            created_at=datetime(2024, 2, 20, tzinfo=UTC),
        ),
        LibraryFile(
            title="Database Design",
            url="https://example.com/db",
            file_path="library/tier-a/database-design.md",
            tags=["database", "design"],
            tier="tier-a",
            source_type=ContentSource.WEB,
            quality_score=9.1,
            created_at=datetime(2024, 3, 10, tzinfo=UTC),
        ),
    ]


def test_export_service_has_qa_id():
    """Test that ExportService has a QA ID for test automation."""
    service = ExportService()
    assert service.qa_id == "export-service"


def test_export_to_markdown_single_item(sample_items):
    """Test converting a single item to markdown format."""
    service = ExportService()
    item = sample_items[0]

    markdown = service.export_to_markdown(item)

    assert "# Python Best Practices" in markdown
    assert "**URL**: https://example.com/python" in markdown
    assert "**Tags**: python, programming" in markdown
    assert "**Tier**: tier-a" in markdown
    assert "**Quality Score**: 9.5" in markdown
    assert "**Created**: 2024-01-15" in markdown
    assert "**Source Type**: web" in markdown
    assert "library/tier-a/python-best-practices.md" in markdown


def test_export_to_markdown_includes_all_fields(sample_items):
    """Test that markdown export includes all relevant fields."""
    service = ExportService()
    item = sample_items[1]

    markdown = service.export_to_markdown(item)

    # Check for all required sections
    assert "# JavaScript Fundamentals" in markdown
    assert "**URL**:" in markdown
    assert "**Tags**:" in markdown
    assert "**Tier**:" in markdown
    assert "**Quality Score**:" in markdown
    assert "**Created**:" in markdown
    assert "**Source Type**:" in markdown
    assert "**File Path**:" in markdown


def test_export_filtered_items_by_tier(sample_items):
    """Test exporting only items from specific tier."""
    service = ExportService()

    tier_a_items = service.filter_for_export(
        sample_items,
        tier_filter="tier-a"
    )

    assert len(tier_a_items) == 2
    assert all(item.tier == "tier-a" for item in tier_a_items)


def test_export_filtered_items_by_tags(sample_items):
    """Test exporting only items with specific tags."""
    service = ExportService()

    programming_items = service.filter_for_export(
        sample_items,
        tag_filter=["programming"]
    )

    assert len(programming_items) == 2
    assert all("programming" in item.tags for item in programming_items)


def test_export_filtered_items_combined(sample_items):
    """Test combining tier and tag filters."""
    service = ExportService()

    filtered = service.filter_for_export(
        sample_items,
        tier_filter="tier-a",
        tag_filter=["programming"]
    )

    assert len(filtered) == 1
    assert filtered[0].title == "Python Best Practices"


def test_create_zip_archive(sample_items):
    """Test creating ZIP archive with multiple markdown files."""
    service = ExportService()

    zip_bytes = service.create_zip_archive(sample_items)

    # Verify it's a valid ZIP file
    zip_file = ZipFile(BytesIO(zip_bytes), 'r')

    # Check that all items are included
    file_names = zip_file.namelist()
    assert len(file_names) == 3
    assert "python-best-practices.md" in file_names
    assert "javascript-fundamentals.md" in file_names
    assert "database-design.md" in file_names

    # Verify content of one file
    content = zip_file.read("python-best-practices.md").decode('utf-8')
    assert "# Python Best Practices" in content


def test_create_zip_with_organization(sample_items):
    """Test ZIP archive organizes files by tier."""
    service = ExportService()

    zip_bytes = service.create_zip_archive(
        sample_items,
        organize_by_tier=True
    )

    zip_file = ZipFile(BytesIO(zip_bytes), 'r')
    file_names = zip_file.namelist()

    # Check tier-based organization
    assert any("tier-a/" in name for name in file_names)
    assert any("tier-b/" in name for name in file_names)


def test_sanitize_filename():
    """Test filename sanitization for safe file creation."""
    service = ExportService()

    # Test various problematic characters
    assert service.sanitize_filename("Test / File") == "test-file"
    assert service.sanitize_filename("File: Name?") == "file-name"
    assert service.sanitize_filename("A * B | C") == "a-b-c"
    assert service.sanitize_filename("Multiple   Spaces") == "multiple-spaces"


def test_export_empty_list():
    """Test exporting empty list returns empty ZIP."""
    service = ExportService()

    zip_bytes = service.create_zip_archive([])
    zip_file = ZipFile(BytesIO(zip_bytes), 'r')

    assert len(zip_file.namelist()) == 0
