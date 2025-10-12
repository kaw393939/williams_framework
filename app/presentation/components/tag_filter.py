"""Tag filter component for library UI.

This module provides tag-based filtering with AND/OR logic
for multi-tag selection, integrating with tier filtering.
"""
from typing import Literal

from app.core.models import LibraryFile


class TagFilter:
    """Component for filtering library items by tags.

    This component provides:
    - Multi-select tag filtering
    - AND logic (items must have ALL selected tags)
    - OR logic (items must have ANY selected tag)
    - Tag extraction from library items
    - Integration with tier filtering

    Example:
        >>> tag_filter = TagFilter()
        >>> filtered = tag_filter.filter_by_tags(items, ["python", "web"], logic="AND")
    """

    def __init__(self):
        """Initialize tag filter component."""
        self.qa_id = "tag-filter"

    def get_all_tags(self, items: list[LibraryFile]) -> list[str]:
        """Extract all unique tags from library items.

        Args:
            items: List of LibraryFile objects

        Returns:
            Sorted list of unique tags
        """
        all_tags: set[str] = set()
        for item in items:
            all_tags.update(item.tags)

        return sorted(all_tags)

    def filter_by_tags(
        self,
        items: list[LibraryFile],
        selected_tags: list[str],
        logic: Literal["AND", "OR"] = "OR"
    ) -> list[LibraryFile]:
        """Filter library items by selected tags.

        Args:
            items: List of LibraryFile objects to filter
            selected_tags: List of tags to filter by
            logic: "AND" (all tags must match) or "OR" (any tag must match)

        Returns:
            Filtered list of LibraryFile objects
        """
        # Empty selection returns all items
        if not selected_tags:
            return items

        filtered_items = []
        selected_tag_set = set(selected_tags)

        for item in items:
            item_tag_set = set(item.tags)

            if logic == "AND":
                # Item must have ALL selected tags
                if selected_tag_set.issubset(item_tag_set):
                    filtered_items.append(item)
            else:  # logic == "OR"
                # Item must have AT LEAST ONE selected tag
                if selected_tag_set.intersection(item_tag_set):
                    filtered_items.append(item)

        return filtered_items
