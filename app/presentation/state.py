"""Typed presentation state shared between the Streamlit app and tests."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class LibraryItem:
    """A simplified view of processed content for presentation."""

    title: str
    summary: str
    tier: str
    tags: Sequence[str]


@dataclass(frozen=True)
class PresentationStats:
    """High level metrics surfaced in the presentation layer."""

    total_items: int
    tier_counts: Mapping[str, int]


@dataclass(frozen=True)
class PresentationState:
    """Aggregate state consumed by the Streamlit UI."""

    library_items: Sequence[LibraryItem]
    stats: PresentationStats
