"""RED TESTS FOR S2-304: Feature flag gating.

These tests verify that:
1. Settings toggle controls plugin discovery
2. Disabling plugins skips registry bootstrap safely
3. Configuration is properly documented
"""
from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.pipeline.etl import ContentPipeline
from app.plugins.registry import PluginRegistry
from tests.plugins.stubs import make_stub_plugin


@pytest.mark.integration
async def test_pipeline_skips_plugins_when_disabled():
    """Test that pipeline doesn't execute plugin hooks when plugins are disabled."""
    # Create registry with plugin
    registry = PluginRegistry()
    stub = make_stub_plugin()
    registry.register(stub)

    # Mock settings to disable plugins
    with patch("app.core.config.get_settings") as mock_settings:
        mock_settings.return_value = Settings(enable_plugins=False)

        pipeline = ContentPipeline(plugin_registry=registry)
        await pipeline.initialize()

        # Verify plugins were NOT executed
        assert len(stub.history) == 0


@pytest.mark.integration
async def test_pipeline_executes_plugins_when_enabled():
    """Test that pipeline executes plugin hooks when plugins are enabled."""
    registry = PluginRegistry()
    stub = make_stub_plugin()
    registry.register(stub)

    # Mock settings to enable plugins
    with patch("app.core.config.get_settings") as mock_settings:
        mock_settings.return_value = Settings(enable_plugins=True)

        pipeline = ContentPipeline(plugin_registry=registry)
        await pipeline.initialize()

        # Verify plugins were executed
        assert len(stub.history) == 1
        assert stub.history[0][0] == "on_load"


@pytest.mark.unit
def test_settings_has_enable_plugins_flag():
    """Test that Settings model includes enable_plugins configuration."""
    settings = Settings()

    assert hasattr(settings, "enable_plugins")
    assert isinstance(settings.enable_plugins, bool)


@pytest.mark.unit
def test_settings_enable_plugins_defaults_to_true():
    """Test that enable_plugins defaults to True for backward compatibility."""
    settings = Settings()

    assert settings.enable_plugins is True


@pytest.mark.integration
async def test_before_store_skips_plugins_when_disabled():
    """Test that before_store hook is skipped when plugins are disabled."""
    registry = PluginRegistry()
    stub = make_stub_plugin()
    registry.register(stub)

    with patch("app.core.config.get_settings") as mock_settings:
        mock_settings.return_value = Settings(enable_plugins=False)

        pipeline = ContentPipeline(plugin_registry=registry)

        mock_content = {"url": "https://example.com", "tags": []}
        result = await pipeline.before_store(mock_content)

        # Verify plugin was NOT called
        assert len(stub.history) == 0

        # Content should be unchanged
        assert result == mock_content
