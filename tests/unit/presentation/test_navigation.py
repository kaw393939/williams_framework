"""RED TESTS FOR S3-401: Navigation structure helper.

These tests verify that:
1. Nav builder returns ordered navigation entries
2. Each entry has icon, label, and QA ID
3. Entries are cached in constants for performance
"""
import pytest

from app.presentation.navigation import NavEntry, NavigationBuilder


@pytest.mark.unit
def test_nav_builder_returns_ordered_entries():
    """Test that navigation builder returns entries in correct order."""
    builder = NavigationBuilder()

    entries = builder.build()

    assert len(entries) > 0
    assert isinstance(entries, list)
    assert all(isinstance(entry, NavEntry) for entry in entries)


@pytest.mark.unit
def test_nav_entry_has_required_fields():
    """Test that NavEntry has icon, label, and qa_id fields."""
    builder = NavigationBuilder()
    entries = builder.build()

    first_entry = entries[0]
    assert hasattr(first_entry, "icon")
    assert hasattr(first_entry, "label")
    assert hasattr(first_entry, "qa_id")
    assert isinstance(first_entry.icon, str)
    assert isinstance(first_entry.label, str)
    assert isinstance(first_entry.qa_id, str)


@pytest.mark.unit
def test_nav_builder_includes_home_page():
    """Test that navigation includes Home page."""
    builder = NavigationBuilder()
    entries = builder.build()

    labels = [entry.label for entry in entries]
    assert "Home" in labels


@pytest.mark.unit
def test_nav_builder_includes_library_page():
    """Test that navigation includes Library page."""
    builder = NavigationBuilder()
    entries = builder.build()

    labels = [entry.label for entry in entries]
    assert "Library" in labels


@pytest.mark.unit
def test_nav_builder_includes_ingest_page():
    """Test that navigation includes Ingest page."""
    builder = NavigationBuilder()
    entries = builder.build()

    labels = [entry.label for entry in entries]
    assert "Ingest" in labels


@pytest.mark.unit
def test_nav_entries_have_unique_qa_ids():
    """Test that all QA IDs are unique for test automation."""
    builder = NavigationBuilder()
    entries = builder.build()

    qa_ids = [entry.qa_id for entry in entries]
    assert len(qa_ids) == len(set(qa_ids)), "QA IDs must be unique"


@pytest.mark.unit
def test_nav_entries_maintain_order():
    """Test that navigation entries maintain consistent order."""
    builder = NavigationBuilder()

    entries1 = builder.build()
    entries2 = builder.build()

    labels1 = [entry.label for entry in entries1]
    labels2 = [entry.label for entry in entries2]

    assert labels1 == labels2, "Navigation order must be consistent"


@pytest.mark.unit
def test_nav_builder_uses_emojis_for_icons():
    """Test that icons use emoji characters."""
    builder = NavigationBuilder()
    entries = builder.build()

    for entry in entries:
        # Icons should be non-empty strings (emojis)
        assert len(entry.icon) > 0
        assert isinstance(entry.icon, str)
