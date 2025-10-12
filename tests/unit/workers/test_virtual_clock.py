"""Tests for the async virtual clock fixture used by worker suites."""
from __future__ import annotations

from datetime import timedelta, timezone

import asyncio
import pytest


@pytest.mark.asyncio
async def test_virtual_clock_resumes_sleep_when_advanced(virtual_clock):
    """Sleepers should resume once the clock has advanced past the delay."""

    sleeper = asyncio.create_task(asyncio.sleep(5))

    # Allow the event loop to register the sleeper with the patched sleep implementation.
    await asyncio.sleep(0)

    assert not sleeper.done()

    virtual_clock.advance(timedelta(seconds=4))
    await asyncio.sleep(0)
    assert not sleeper.done()

    virtual_clock.advance(timedelta(seconds=1))
    await sleeper


def test_virtual_clock_now_is_timezone_aware(virtual_clock):
    """The clock should expose UTC-aware timestamps for deterministic comparisons."""

    now = virtual_clock.now()
    assert now.tzinfo is timezone.utc


def test_virtual_clock_advance_returns_updated_now(virtual_clock):
    """Advancing the clock should move forward the reported time by the given delta."""

    start = virtual_clock.now()
    virtual_clock.advance(timedelta(seconds=30))

    assert virtual_clock.now() == start + timedelta(seconds=30)
