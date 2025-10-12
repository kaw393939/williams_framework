"""Export service for converting library items to markdown.

Provides functionality to export library items as markdown files,
with support for filtering and ZIP archive generation.
"""

import re
from io import BytesIO
from typing import Optional
from zipfile import ZipFile

from app.core.models import LibraryFile


class ExportService:
    """Service for exporting library items to various formats.

    Supports markdown export, filtering by tier and tags,
    and ZIP archive creation for bulk downloads.
    """

    def __init__(self):
        """Initialize the export service."""
        self.qa_id = "export-service"

    def export_to_markdown(self, item: LibraryFile) -> str:
        """Convert a library item to markdown format.

        Args:
            item: The library item to export

        Returns:
            Markdown-formatted string representation
        """
        lines = [
            f"# {item.title}",
            "",
            f"**URL**: {item.url}",
            f"**Tags**: {', '.join(item.tags)}",
            f"**Tier**: {item.tier}",
            f"**Quality Score**: {item.quality_score}",
            f"**Source Type**: {item.source_type.value}",
            f"**Created**: {item.created_at.strftime('%Y-%m-%d')}",
            f"**File Path**: {item.file_path}",
            "",
        ]

        return "\n".join(lines)

    def filter_for_export(
        self,
        items: list[LibraryFile],
        tier_filter: Optional[str] = None,
        tag_filter: Optional[list[str]] = None,
    ) -> list[LibraryFile]:
        """Filter library items for export.

        Args:
            items: List of library items to filter
            tier_filter: Optional tier to filter by (e.g., "tier-a")
            tag_filter: Optional list of tags to filter by (OR logic)

        Returns:
            Filtered list of library items
        """
        filtered = items

        # Apply tier filter
        if tier_filter:
            filtered = [item for item in filtered if item.tier == tier_filter]

        # Apply tag filter (OR logic - item must have at least one tag)
        if tag_filter:
            filtered = [
                item for item in filtered
                if any(tag in item.tags for tag in tag_filter)
            ]

        return filtered

    def sanitize_filename(self, title: str) -> str:
        """Sanitize a title to create a safe filename.

        Args:
            title: The title to sanitize

        Returns:
            Safe filename string (lowercase, hyphenated)
        """
        # Remove or replace problematic characters
        safe = re.sub(r'[/:*?"<>|]', '', title)
        # Replace spaces and multiple spaces with single hyphen
        safe = re.sub(r'\s+', '-', safe.strip())
        # Convert to lowercase
        safe = safe.lower()
        # Remove any remaining non-alphanumeric characters except hyphens
        safe = re.sub(r'[^a-z0-9-]', '', safe)
        # Remove multiple consecutive hyphens
        safe = re.sub(r'-+', '-', safe)

        return safe

    def create_zip_archive(
        self,
        items: list[LibraryFile],
        organize_by_tier: bool = False,
    ) -> bytes:
        """Create a ZIP archive containing markdown files.

        Args:
            items: List of library items to export
            organize_by_tier: If True, organize files into tier folders

        Returns:
            ZIP archive as bytes
        """
        buffer = BytesIO()

        with ZipFile(buffer, 'w') as zip_file:
            for item in items:
                # Generate markdown content
                markdown = self.export_to_markdown(item)

                # Create filename
                filename = f"{self.sanitize_filename(item.title)}.md"

                # Add tier folder if organizing
                if organize_by_tier:
                    filename = f"{item.tier}/{filename}"

                # Write to ZIP
                zip_file.writestr(filename, markdown)

        buffer.seek(0)
        return buffer.getvalue()
