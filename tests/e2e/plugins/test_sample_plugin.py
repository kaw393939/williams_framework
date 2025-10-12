"""RED TESTS FOR S2-305: Sample plugin acceptance flow.

These tests verify that:
1. Sample plugin is packaged and documented
2. End-to-end test ensures hook modifies content
3. CLI telemetry records plugin events
"""
from unittest.mock import patch

import pytest

from app.pipeline.etl import ContentPipeline
from app.plugins.registry import PluginRegistry
from app.plugins.samples import EnrichmentPlugin


@pytest.mark.e2e
async def test_sample_plugin_modifies_content_end_to_end():
    """Test that sample enrichment plugin modifies content through full pipeline."""
    registry = PluginRegistry()
    plugin = EnrichmentPlugin()
    registry.register(plugin)

    pipeline = ContentPipeline(plugin_registry=registry)
    await pipeline.initialize()

    # Verify plugin was initialized
    assert plugin._initialized is True
    assert len(plugin.history) == 1
    assert plugin.history[0][0] == "on_load"

    # Process content through before_store hook
    original_content = {
        "url": "https://example.com/test",
        "title": "Test Content",
        "tags": ["test"],
    }

    modified_content = await pipeline.before_store(original_content)

    # Verify content was enriched
    assert "enriched" in modified_content["tags"]
    assert "sample-plugin" in modified_content["tags"]
    assert modified_content["enrichment_applied"] is True
    assert modified_content["enriched_by"] == "sample.enrichment"

    # Verify original tags are preserved
    assert "test" in modified_content["tags"]


@pytest.mark.integration
async def test_sample_plugin_telemetry_records_events():
    """Test that CLI telemetry records plugin events."""
    registry = PluginRegistry()
    plugin = EnrichmentPlugin()
    registry.register(plugin)

    with patch("app.core.telemetry.log_event") as log_event:
        pipeline = ContentPipeline(plugin_registry=registry)
        await pipeline.initialize()

        # Verify on_load telemetry
        assert log_event.called
        on_load_calls = [
            call for call in log_event.call_args_list
            if call.args[0].get("event_type") == "plugin.on_load"
        ]
        assert len(on_load_calls) == 1
        assert on_load_calls[0].args[0]["plugin_id"] == "sample.enrichment"

        # Process content
        content = {"url": "https://example.com", "tags": []}
        await pipeline.before_store(content)

        # Verify before_store telemetry
        before_store_calls = [
            call for call in log_event.call_args_list
            if call.args[0].get("event_type") == "plugin.before_store"
        ]
        assert len(before_store_calls) == 1
        assert before_store_calls[0].args[0]["plugin_id"] == "sample.enrichment"


@pytest.mark.unit
def test_sample_plugin_has_required_metadata():
    """Test that sample plugin has all required metadata fields."""
    plugin = EnrichmentPlugin()

    assert hasattr(plugin, "plugin_id")
    assert hasattr(plugin, "name")
    assert hasattr(plugin, "version")
    assert plugin.plugin_id == "sample.enrichment"
    assert plugin.name == "Content Enrichment Plugin"
    assert plugin.version == "1.0.0"


@pytest.mark.unit
async def test_sample_plugin_on_load_returns_structured_response():
    """Test that on_load hook returns properly structured response."""
    plugin = EnrichmentPlugin()

    context = {"pipeline": "test"}
    result = await plugin.on_load(context)

    assert "plugin_id" in result
    assert "event" in result
    assert "payload" in result
    assert result["plugin_id"] == "sample.enrichment"
    assert result["event"] == "on_load"
    assert result["payload"]["status"] == "initialized"


@pytest.mark.unit
async def test_sample_plugin_before_store_enriches_tags():
    """Test that before_store hook adds enrichment tags."""
    plugin = EnrichmentPlugin()

    content = {"url": "https://example.com", "tags": ["original"]}
    result = await plugin.before_store(content)

    payload = result["payload"]
    assert "enriched" in payload["tags"]
    assert "sample-plugin" in payload["tags"]
    assert "original" in payload["tags"]  # Original tags preserved
    assert payload["enrichment_applied"] is True
    assert payload["enriched_by"] == "sample.enrichment"


@pytest.mark.e2e
async def test_sample_plugin_works_with_multiple_plugins():
    """Test that sample plugin works alongside other plugins in registry."""
    from tests.plugins.stubs import make_stub_plugin

    registry = PluginRegistry()

    # Register multiple plugins
    enrichment = EnrichmentPlugin()
    stub = make_stub_plugin()

    registry.register(enrichment)
    registry.register(stub)

    pipeline = ContentPipeline(plugin_registry=registry)
    await pipeline.initialize()

    # Both plugins should initialize
    assert enrichment._initialized
    assert len(stub.history) == 1

    # Process content through both plugins
    content = {"url": "https://example.com", "tags": []}
    result = await pipeline.before_store(content)

    # Both plugins should have modified content
    assert "enriched" in result["tags"]  # From enrichment plugin
    assert "stubbed" in result["tags"]   # From stub plugin
