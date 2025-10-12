"""Red tests for plugin stub utilities used in downstream stories."""
from __future__ import annotations

import pytest

from tests.plugins import stubs


def test_stub_plugin_has_deterministic_identity() -> None:
    plugin = stubs.make_stub_plugin()

    assert plugin.plugin_id == "tests.stub.plugin"
    assert plugin.name == "Deterministic Stub Plugin"
    assert plugin.version == "1.0.0"


@pytest.mark.asyncio
async def test_stub_plugin_hooks_return_predictable_payloads() -> None:
    plugin = stubs.make_stub_plugin()

    load_result = await plugin.on_load(context={"sequence": 1})
    assert load_result.plugin_id == "tests.stub.plugin"
    assert load_result.event == "on_load"
    assert load_result.payload == {"sequence": 1, "status": "ok"}

    content = {
        "title": "Example",
        "summary": "Content prior to plugin",
        "tags": ["pipeline"],
    }

    store_result = await plugin.before_store(content)
    assert store_result.plugin_id == "tests.stub.plugin"
    assert store_result.event == "before_store"
    assert store_result.payload["tags"] == ["pipeline", "stubbed"]
    assert content["tags"] == ["pipeline"]


@pytest.mark.asyncio
async def test_stub_plugin_records_call_history() -> None:
    plugin = stubs.make_stub_plugin()

    await plugin.on_load(context={"sequence": 2})
    await plugin.before_store({"title": "A", "summary": "B", "tags": []})

    assert plugin.history == [
        ("on_load", {"sequence": 2}),
        ("before_store", {"title": "A", "summary": "B", "tags": []}),
    ]
