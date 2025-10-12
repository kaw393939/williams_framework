"""Factories for deterministic Streamlit presentation state."""
from __future__ import annotations

from collections.abc import Callable
from typing import Sequence

from app.presentation.state import LibraryItem, PresentationState, PresentationStats


_LIBRARY_FIXTURES: Sequence[LibraryItem] = (
    LibraryItem(
        title="AI Research Roadmap",
        summary="Quarterly objectives covering pipeline, plugins, and presentation tiers.",
        tier="tier-a",
        tags=("roadmap", "planning"),
    ),
    LibraryItem(
        title="Streamlit Harness Notes",
        summary="Explains how the testing harness boots the app without external services.",
        tier="tier-b",
        tags=("testing", "ui"),
    ),
)

_STATS_FIXTURE = PresentationStats(
    total_items=len(_LIBRARY_FIXTURES),
    tier_counts={"tier-a": 1, "tier-b": 1, "tier-c": 0},
)


def make_presentation_state() -> PresentationState:
    """Return a deterministic presentation state for Streamlit tests."""

    return PresentationState(library_items=_LIBRARY_FIXTURES, stats=_STATS_FIXTURE)


def make_state_provider() -> Callable[[], PresentationState]:
    """Return a callable yielding the deterministic presentation state."""

    state = make_presentation_state()

    def _provider() -> PresentationState:
        return state

    return _provider
