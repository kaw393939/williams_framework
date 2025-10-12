"""Sample enrichment plugin that adds metadata tags to content.

This plugin demonstrates the plugin lifecycle and serves as a
reference implementation for custom plugin development.
"""
from __future__ import annotations

from typing import Any


class EnrichmentPlugin:
    """Sample plugin that enriches content with additional metadata tags."""

    plugin_id = "sample.enrichment"
    name = "Content Enrichment Plugin"
    version = "1.0.0"

    def __init__(self) -> None:
        self.history: list[tuple[str, dict[str, Any]]] = []
        self._initialized = False

    async def on_load(self, context: dict[str, Any]) -> dict[str, Any]:
        """Hook called when plugin is loaded by the pipeline.

        Args:
            context: Initialization context from the pipeline.

        Returns:
            Dict with plugin_id, event type, and payload.
        """
        self._initialized = True
        self.history.append(("on_load", dict(context)))

        return {
            "plugin_id": self.plugin_id,
            "event": "on_load",
            "payload": {
                **context,
                "status": "initialized",
                "plugin_name": self.name,
            },
        }

    async def before_store(self, content: dict[str, Any]) -> dict[str, Any]:
        """Hook called before content is stored.

        This hook adds enrichment tags to the content.

        Args:
            content: Content dictionary to enrich.

        Returns:
            Dict with plugin_id, event type, and enriched payload.
        """
        self.history.append(("before_store", dict(content)))

        # Enrich content with additional metadata
        enriched = dict(content)
        tags = list(enriched.get("tags", []))
        
        # Add enrichment tags
        tags.extend(["enriched", "sample-plugin"])
        
        # Add metadata
        enriched["tags"] = tags
        enriched["enrichment_applied"] = True
        enriched["enriched_by"] = self.plugin_id

        return {
            "plugin_id": self.plugin_id,
            "event": "before_store",
            "payload": enriched,
        }
