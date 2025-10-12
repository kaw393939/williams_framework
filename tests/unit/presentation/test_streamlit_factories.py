"""Unit tests for deterministic Streamlit factories and helpers."""

from app.presentation.app import build_app
from tests.factories.streamlit import make_presentation_state, make_state_provider


def test_make_presentation_state_is_repeatable():
    first = make_presentation_state()
    second = make_presentation_state()

    assert first is not second
    assert first == second
    assert len(first.library_items) == 2
    assert first.stats.total_items == 2


def test_make_state_provider_returns_cached_state():
    provider = make_state_provider()

    first = provider()
    second = provider()

    assert first is second
    assert first.library_items[0].title == "AI Research Roadmap"


def test_build_app_uses_state_provider(monkeypatch):
    provider = make_state_provider()
    calls = []

    def fake_run_app(state_provider):
        calls.append(state_provider)

    monkeypatch.setattr("app.presentation.app.run_app", fake_run_app)

    runner = build_app(provider)
    runner()

    assert calls == [provider]
