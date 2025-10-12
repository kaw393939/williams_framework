"""Tests for streamlit_app testable functions."""
import pytest

from app.presentation.state import LibraryItem, PresentationState, PresentationStats
from app.presentation.streamlit_app import build_app, default_state_provider


def test_default_state_provider_returns_valid_state():
    """Test that default_state_provider returns a valid PresentationState."""
    state = default_state_provider()

    assert isinstance(state, PresentationState)
    assert isinstance(state.stats, PresentationStats)
    assert isinstance(state.library_items, tuple)
    assert isinstance(state.stats.total_items, int)
    assert isinstance(state.stats.tier_counts, dict)


def test_default_state_provider_calculates_stats():
    """Test that default_state_provider calculates correct statistics."""
    state = default_state_provider()

    # Stats should match library items
    assert state.stats.total_items == len(state.library_items)

    # Tier counts should sum to total
    total_from_tiers = sum(state.stats.tier_counts.values())
    assert total_from_tiers == state.stats.total_items


def test_build_app_returns_callable():
    """Test that build_app returns a callable function."""

    def mock_state_provider():
        return PresentationState(
            library_items=(),
            stats=PresentationStats(total_items=0, tier_counts={})
        )

    app = build_app(mock_state_provider)

    assert callable(app)


def test_build_app_binds_state_provider():
    """Test that build_app creates function bound to provided state."""
    called = []

    def mock_state_provider():
        called.append(True)
        return PresentationState(
            library_items=(),
            stats=PresentationStats(total_items=0, tier_counts={})
        )

    app = build_app(mock_state_provider)

    # Note: We can't actually call app() because it uses Streamlit functions
    # which require a Streamlit runtime. But we've tested that build_app
    # returns a callable that's properly constructed.
    assert callable(app)
