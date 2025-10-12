"""Tier filter component for library UI.

This module provides a Streamlit component for filtering library items by tier.
Tier options are derived from the application config thresholds.
"""
from typing import List

from app.core.models import LibraryFile


def get_tier_options() -> List[str]:
    """Get available tier options for filtering.
    
    Returns ordered list starting with 'All', then all configured tiers.
    Tier options match the tier values in LibraryFile model.
    
    Returns:
        List of tier options: ["All", "tier-a", "tier-b", "tier-c"]
    """
    return ["All", "tier-a", "tier-b", "tier-c"]


class TierFilter:
    """Component for filtering library items by tier.
    
    This component provides:
    - Dropdown selection of tier options
    - Filtering logic for LibraryFile items
    - QA ID for test automation
    
    Example:
        >>> tier_filter = TierFilter()
        >>> filtered_items = tier_filter.filter_items(all_items, "tier-a")
    """
    
    def __init__(self):
        """Initialize tier filter component."""
        self.qa_id = "tier-filter"
    
    def filter_items(
        self,
        items: List[LibraryFile],
        selected_tier: str
    ) -> List[LibraryFile]:
        """Filter library items by selected tier.
        
        Args:
            items: List of LibraryFile objects to filter
            selected_tier: Tier to filter by ("All", "tier-a", "tier-b", "tier-c")
        
        Returns:
            Filtered list of LibraryFile objects. If selected_tier is "All",
            returns all items. Otherwise returns only items matching the tier.
        """
        if selected_tier == "All":
            return items
        
        return [item for item in items if item.tier == selected_tier]
