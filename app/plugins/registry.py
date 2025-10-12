"""Plugin registry for managing plugin lifecycle and preventing duplicates."""
from __future__ import annotations

from typing import Any, Optional

from app.core.exceptions import PluginError


class PluginRegistry:
    """Central registry for plugin management with duplicate detection."""

    def __init__(self) -> None:
        self._plugins: dict[str, Any] = {}

    def register(self, plugin: Any) -> None:
        """Register a plugin.

        Args:
            plugin: Plugin instance to register.

        Raises:
            PluginError: If a plugin with the same ID is already registered.
        """
        plugin_id = plugin.plugin_id
        
        if plugin_id in self._plugins:
            existing = self._plugins[plugin_id]
            raise PluginError(
                f"Plugin '{plugin_id}' is already registered. "
                f"Existing plugin: {existing.name} v{existing.version}. "
                f"Cannot register duplicate plugin ID. "
                f"Please use a unique plugin_id or unregister the existing plugin first."
            )
        
        self._plugins[plugin_id] = plugin

    def get(self, plugin_id: str) -> Optional[Any]:
        """Get a registered plugin by ID.

        Args:
            plugin_id: Plugin identifier.

        Returns:
            Plugin instance if found, None otherwise.
        """
        return self._plugins.get(plugin_id)

    def all(self) -> list[Any]:
        """Get all registered plugins.

        Returns:
            List of all registered plugin instances.
        """
        return list(self._plugins.values())
