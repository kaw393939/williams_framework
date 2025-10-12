"""Navigation structure helper for Streamlit UI.

Provides consistent navigation entries with icons and QA IDs for testing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class NavEntry:
    """Navigation entry with icon, label, and QA identifier."""

    icon: str
    label: str
    qa_id: str


# Navigation constants cached for performance
NAV_HOME: Final[NavEntry] = NavEntry(
    icon="🏠",
    label="Home",
    qa_id="nav-home",
)

NAV_LIBRARY: Final[NavEntry] = NavEntry(
    icon="📚",
    label="Library",
    qa_id="nav-library",
)

NAV_INGEST: Final[NavEntry] = NavEntry(
    icon="📥",
    label="Ingest",
    qa_id="nav-ingest",
)

NAV_SEARCH: Final[NavEntry] = NavEntry(
    icon="🔍",
    label="Search",
    qa_id="nav-search",
)

NAV_INSIGHTS: Final[NavEntry] = NavEntry(
    icon="💡",
    label="Insights",
    qa_id="nav-insights",
)


class NavigationBuilder:
    """Builder for navigation structure with consistent ordering."""

    def build(self) -> list[NavEntry]:
        """Build ordered navigation entries.

        Returns:
            List of navigation entries in display order.
        """
        return [
            NAV_HOME,
            NAV_LIBRARY,
            NAV_INGEST,
            NAV_SEARCH,
            NAV_INSIGHTS,
        ]
