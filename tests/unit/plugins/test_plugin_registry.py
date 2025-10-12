"""RED TESTS FOR S2-301: Plugin registry duplicate guard.

These tests verify that the plugin registry:
1. Prevents duplicate plugin registration by ID
2. Surfaces actionable error messages on duplicate attempts
3. Allows successful registration of unique plugins
"""
import pytest

from app.core.exceptions import PluginError
from app.plugins.registry import PluginRegistry
from tests.plugins.stubs import make_stub_plugin


@pytest.mark.unit
def test_registry_allows_unique_plugin_registration():
    """Test that registry successfully registers plugins with unique IDs."""
    registry = PluginRegistry()
    plugin = make_stub_plugin()
    
    registry.register(plugin)
    
    assert registry.get(plugin.plugin_id) is plugin
    assert len(registry.all()) == 1


@pytest.mark.unit
def test_registry_prevents_duplicate_plugin_registration():
    """Test that registry raises PluginError when registering duplicate plugin ID."""
    registry = PluginRegistry()
    plugin1 = make_stub_plugin()
    plugin2 = make_stub_plugin()
    
    registry.register(plugin1)
    
    with pytest.raises(PluginError) as exc_info:
        registry.register(plugin2)
    
    error_message = str(exc_info.value)
    assert plugin1.plugin_id in error_message
    assert "already registered" in error_message.lower()


@pytest.mark.unit
def test_registry_provides_actionable_duplicate_error_context():
    """Test that duplicate registration error includes plugin metadata for debugging."""
    registry = PluginRegistry()
    plugin1 = make_stub_plugin()
    plugin2 = make_stub_plugin()
    
    registry.register(plugin1)
    
    with pytest.raises(PluginError) as exc_info:
        registry.register(plugin2)
    
    error_message = str(exc_info.value)
    # Should include plugin ID and clear action to take
    assert plugin1.plugin_id in error_message
    assert plugin1.name in error_message
    assert plugin1.version in error_message


@pytest.mark.unit
def test_registry_get_returns_none_for_unknown_plugin():
    """Test that get() returns None for plugins that aren't registered."""
    registry = PluginRegistry()
    
    result = registry.get("unknown.plugin.id")
    
    assert result is None


@pytest.mark.unit
def test_registry_all_returns_registered_plugins():
    """Test that all() returns list of all registered plugins."""
    registry = PluginRegistry()
    plugin = make_stub_plugin()
    
    assert registry.all() == []
    
    registry.register(plugin)
    
    assert registry.all() == [plugin]
