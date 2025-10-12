"""Deterministic plugin stubs for unit and integration testing."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HookResult:
    """Structured result returned by stub plugin hooks."""

    plugin_id: str
    event: str
    payload: dict[str, Any]


class StubPlugin:
    """A deterministic plugin stub with predictable hook behaviour."""

    plugin_id = "tests.stub.plugin"
    name = "Deterministic Stub Plugin"
    version = "1.0.0"

    def __init__(self) -> None:
        self.history: list[tuple[str, dict[str, Any]]] = []

    async def on_load(self, context: dict[str, Any]) -> HookResult:
        context_copy = deepcopy(context)
        self.history.append(("on_load", context_copy))

        payload = dict(context_copy)
        payload.setdefault("status", "ok")
        return HookResult(plugin_id=self.plugin_id, event="on_load", payload=payload)

    async def before_store(self, content: dict[str, Any]) -> HookResult:
        original = deepcopy(content)
        self.history.append(("before_store", original))

        payload = deepcopy(content)
        tags = list(payload.get("tags", []))
        tags.append("stubbed")
        payload["tags"] = tags
        return HookResult(plugin_id=self.plugin_id, event="before_store", payload=payload)


def make_stub_plugin() -> StubPlugin:
    """Return a fresh stub plugin instance used in tests."""

    return StubPlugin()
