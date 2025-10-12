"""Red tests for prompt snapshot loader utilities."""
from __future__ import annotations

import hashlib

import pytest

from tests.plugins import prompts


EXPECTED_SUMMARIZE_PROMPT = (
    "You are the Williams Librarian summarizer.\n"
    "Summarize the provided research artifact into three tiers:\n"
    "- Tier A: executive digest\n"
    "- Tier B: practitioner insights\n"
    "- Tier C: raw notes\n"
)


def test_load_prompt_snapshot_returns_expected_content_and_checksum() -> None:
    snapshot = prompts.load_prompt_snapshot("summarize")

    assert snapshot.name == "summarize"
    assert snapshot.content == EXPECTED_SUMMARIZE_PROMPT
    assert snapshot.path.name == "summarize.prompt"
    assert snapshot.checksum == hashlib.sha256(EXPECTED_SUMMARIZE_PROMPT.encode("utf-8")).hexdigest()


def test_load_prompt_snapshot_missing_prompt_raises_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        prompts.load_prompt_snapshot("nonexistent")
