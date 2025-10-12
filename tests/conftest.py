from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from tests.util.virtual_clock import VirtualClock, patch_asyncio_sleep


@pytest.fixture
def virtual_clock(monkeypatch: pytest.MonkeyPatch, event_loop: asyncio.AbstractEventLoop) -> VirtualClock:
    """Provide a deterministic virtual clock patched into asyncio.sleep."""

    clock = VirtualClock(loop=event_loop)
    monkeypatch.setattr(asyncio, "sleep", patch_asyncio_sleep(clock))
    return clock


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Automatically apply pytest markers based on folder structure."""

    marker_by_folder = {
        "unit": "unit",
        "integration": "integration",
        "e2e": "e2e",
        "ui": "ui",
        "presentation": "ui",
    }

    for item in items:
        path = Path(str(item.fspath))
        try:
            tests_index = path.parts.index("tests")
        except ValueError:
            continue

        if tests_index + 1 >= len(path.parts):
            continue

        folder = path.parts[tests_index + 1]
        marker_name = marker_by_folder.get(folder)
        if marker_name:
            item.add_marker(marker_name)

        if folder == "e2e":
            item.add_marker("slow")
