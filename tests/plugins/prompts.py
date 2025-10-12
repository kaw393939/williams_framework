"""Prompt snapshot utilities for plugin/prompt testing."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

__all__ = ["PromptSnapshot", "load_prompt_snapshot"]


@dataclass(frozen=True)
class PromptSnapshot:
    """In-memory representation of a prompt snapshot."""

    name: str
    content: str
    checksum: str
    path: Path


_CACHE: dict[str, PromptSnapshot] = {}


def load_prompt_snapshot(name: str) -> PromptSnapshot:
    """Load a prompt snapshot by name and memoize the result."""

    if name in _CACHE:
        return _CACHE[name]

    prompt_path = _resolve_prompt_path(name)
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt snapshot '{name}' not found at {prompt_path}")

    content = prompt_path.read_text(encoding="utf-8")
    checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()

    snapshot = PromptSnapshot(name=name, content=content, checksum=checksum, path=prompt_path)
    _CACHE[name] = snapshot
    return snapshot


def _resolve_prompt_path(name: str) -> Path:
    base_dir = Path(__file__).resolve().parent.parent / "fixtures" / "prompts"
    return base_dir / f"{name}.prompt"
