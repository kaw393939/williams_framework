"""RED TESTS FOR S2-303: Plugin lifecycle execution.

These tests verify that:
1. Plugin hooks (on_load, before_store) execute within pipeline
2. Hook output is recorded in telemetry
3. Lifecycle executes with deterministic stub plugin
"""
from unittest.mock import patch

import pytest

from app.pipeline.etl import ContentPipeline
from app.plugins.registry import PluginRegistry
from tests.plugins.stubs import make_stub_plugin


@pytest.mark.integration
async def test_pipeline_executes_on_load_hook_on_initialization():
    """Test that pipeline executes on_load hook during initialization."""
    registry = PluginRegistry()
    stub = make_stub_plugin()
    registry.register(stub)

    with patch("app.core.telemetry.log_event") as log_event:
        pipeline = ContentPipeline(plugin_registry=registry)
        await pipeline.initialize()

        # Verify on_load was called
        assert len(stub.history) == 1
        assert stub.history[0][0] == "on_load"

        # Verify telemetry was emitted
        assert log_event.called
        telemetry_calls = [call.args[0] for call in log_event.call_args_list]
        assert any(
            event.get("event_type") == "plugin.on_load"
            for event in telemetry_calls
        )


@pytest.mark.integration
async def test_pipeline_executes_before_store_hook_before_loading():
    """Test that pipeline executes before_store hook before loader stores content."""
    registry = PluginRegistry()
    stub = make_stub_plugin()
    registry.register(stub)

    with patch("app.core.telemetry.log_event") as log_event:
        pipeline = ContentPipeline(plugin_registry=registry)
        # Assuming pipeline has a process method that calls before_store
        # This will need to be adjusted based on actual pipeline API

        # Create mock content to process
        mock_content = {
            "url": "https://example.com/test",
            "title": "Test Content",
            "tags": ["test"],
        }

        await pipeline.before_store(mock_content)

        # Verify before_store was called
        assert any(event == "before_store" for event, _ in stub.history)

        # Verify telemetry was emitted
        assert log_event.called
        telemetry_calls = [call.args[0] for call in log_event.call_args_list]
        assert any(
            event.get("event_type") == "plugin.before_store"
            for event in telemetry_calls
        )


@pytest.mark.integration
async def test_pipeline_records_plugin_hook_output_in_telemetry():
    """Test that hook output is captured in telemetry with plugin metadata."""
    registry = PluginRegistry()
    stub = make_stub_plugin()
    registry.register(stub)

    with patch("app.core.telemetry.log_event") as log_event:
        pipeline = ContentPipeline(plugin_registry=registry)
        await pipeline.initialize()

        # Check that telemetry includes plugin ID and hook result
        telemetry_calls = log_event.call_args_list

        # Find the plugin telemetry event
        plugin_events = [
            call for call in telemetry_calls
            if "plugin" in str(call.args[0]).lower()
        ]

        assert len(plugin_events) > 0

        # Verify telemetry includes plugin metadata
        for call in plugin_events:
            # Should include plugin_id from stub
            assert "plugin_id" in str(call) or stub.plugin_id in str(call)


@pytest.mark.integration
async def test_plugin_lifecycle_hooks_execute_in_order():
    """Test that plugin hooks execute in the correct lifecycle order."""
    registry = PluginRegistry()
    stub = make_stub_plugin()
    registry.register(stub)

    pipeline = ContentPipeline(plugin_registry=registry)

    # Initialize pipeline (should trigger on_load)
    await pipeline.initialize()

    assert len(stub.history) >= 1
    assert stub.history[0][0] == "on_load"

    # Process content (should trigger before_store)
    mock_content = {"url": "https://example.com/test", "tags": []}
    await pipeline.before_store(mock_content)

    assert len(stub.history) >= 2
    assert stub.history[1][0] == "before_store"

    # Verify order: on_load comes before before_store
    events = [event for event, _ in stub.history]
    on_load_idx = events.index("on_load")
    before_store_idx = events.index("before_store")
    assert on_load_idx < before_store_idx
