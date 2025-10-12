"""Library statistics component for Streamlit dashboard.

This module provides components for displaying library statistics including
tier distribution, quality scores, and tag frequency analysis.
"""
from typing import List, Dict, Any, Tuple
from collections import Counter

from app.core.models import LibraryFile


class LibraryStatsComponent:
    """Component for calculating and displaying library statistics.
    
    This component provides:
    - Tier distribution analysis
    - Average quality score calculation
    - Total item count tracking
    - Tag frequency analysis
    - Chart data formatting for Streamlit
    
    Example:
        >>> component = LibraryStatsComponent()
        >>> stats = component.calculate_stats(library_items)
        >>> print(stats["average_quality_score"])
    """
    
    def __init__(self):
        """Initialize library stats component."""
        self.total_count_qa_id = "stats-total-count"
        self.avg_score_qa_id = "stats-avg-score"
        self.tier_chart_qa_id = "stats-tier-chart"
        self.tag_chart_qa_id = "stats-tag-chart"
    
    def calculate_stats(self, items: List[LibraryFile]) -> Dict[str, Any]:
        """Calculate statistics for library items.
        
        Args:
            items: List of LibraryFile objects
        
        Returns:
            Dictionary containing:
            - total_count: Total number of items
            - average_quality_score: Average quality score across all items
            - tier_distribution: Count of items in each tier
            - tag_frequency: Count of each tag across all items
        """
        if not items:
            return {
                "total_count": 0,
                "average_quality_score": 0.0,
                "tier_distribution": {"tier-a": 0, "tier-b": 0, "tier-c": 0},
                "tag_frequency": {}
            }
        
        # Calculate tier distribution
        tier_counts = Counter(item.tier for item in items)
        tier_distribution = {
            "tier-a": tier_counts.get("tier-a", 0),
            "tier-b": tier_counts.get("tier-b", 0),
            "tier-c": tier_counts.get("tier-c", 0),
        }
        
        # Calculate average quality score
        total_quality = sum(item.quality_score for item in items)
        average_quality_score = total_quality / len(items)
        
        # Calculate tag frequency
        all_tags = []
        for item in items:
            all_tags.extend(item.tags)
        tag_frequency = dict(Counter(all_tags))
        
        return {
            "total_count": len(items),
            "average_quality_score": average_quality_score,
            "tier_distribution": tier_distribution,
            "tag_frequency": tag_frequency
        }
    
    def get_top_tags(
        self,
        items: List[LibraryFile],
        top_n: int = 10
    ) -> List[Tuple[str, int]]:
        """Get the top N most frequent tags.
        
        Args:
            items: List of LibraryFile objects
            top_n: Number of top tags to return
        
        Returns:
            List of tuples (tag_name, count) sorted by count descending
        """
        all_tags = []
        for item in items:
            all_tags.extend(item.tags)
        
        tag_counter = Counter(all_tags)
        return tag_counter.most_common(top_n)
    
    def format_tier_chart_data(self, items: List[LibraryFile]) -> Dict[str, List]:
        """Format tier distribution data for Streamlit bar chart.
        
        Args:
            items: List of LibraryFile objects
        
        Returns:
            Dictionary with "tier" and "count" keys for chart rendering
        """
        stats = self.calculate_stats(items)
        tier_dist = stats["tier_distribution"]
        
        return {
            "tier": ["tier-a", "tier-b", "tier-c"],
            "count": [
                tier_dist["tier-a"],
                tier_dist["tier-b"],
                tier_dist["tier-c"]
            ]
        }
    
    def format_tag_chart_data(
        self,
        items: List[LibraryFile],
        top_n: int = 10
    ) -> Dict[str, List]:
        """Format tag frequency data for Streamlit bar chart.
        
        Args:
            items: List of LibraryFile objects
            top_n: Number of top tags to include
        
        Returns:
            Dictionary with "tag" and "count" keys for chart rendering
        """
        top_tags = self.get_top_tags(items, top_n)
        
        return {
            "tag": [tag for tag, count in top_tags],
            "count": [count for tag, count in top_tags]
        }
