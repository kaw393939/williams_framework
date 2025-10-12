"""Deterministic virtual clock utilities for async worker tests."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass
class ScheduledSleeper:
    wake_at: datetime
    future: asyncio.Future[None]


@dataclass
class VirtualClock:
    """A controllable clock that coordinates with asyncio sleepers."""

    start_at: datetime = field(
        default_factory=lambda: datetime(2025, 1, 1, tzinfo=UTC)
    )
    loop: asyncio.AbstractEventLoop | None = None

    def __post_init__(self) -> None:
        self._loop = self.loop or asyncio.get_event_loop()
        self._now = self.start_at
        self._sleepers: list[ScheduledSleeper] = []

    def now(self) -> datetime:
        """Return the current virtual time."""

        return self._now

    def advance(self, delta: timedelta | float | int) -> datetime:
        """Advance the virtual clock forwards by the supplied delta."""

        step = self._coerce_delta(delta)
        if step.total_seconds() < 0:
            raise ValueError("VirtualClock cannot move backwards")

        self._now += step
        self._release_ready_sleepers()
        return self._now

    async def sleep(self, delay: timedelta | float | int) -> None:
        """Suspend execution until the clock advances past the delay."""

        wake_at = self._now + self._coerce_delta(delay)
        future: asyncio.Future[None] = self._loop.create_future()
        self._sleepers.append(ScheduledSleeper(wake_at=wake_at, future=future))
        self._sleepers.sort(key=lambda scheduled: scheduled.wake_at)
        self._release_ready_sleepers()
        await future

    def _coerce_delta(self, delta: timedelta | float | int) -> timedelta:
        if isinstance(delta, timedelta):
            return delta

        return timedelta(seconds=float(delta))

    def _release_ready_sleepers(self) -> None:
        pending: list[ScheduledSleeper] = []
        for scheduled in self._sleepers:
            if scheduled.wake_at <= self._now:
                if not scheduled.future.done():
                    self._loop.call_soon(scheduled.future.set_result, None)
            else:
                pending.append(scheduled)
        self._sleepers = pending


def patch_asyncio_sleep(clock: VirtualClock) -> Callable[..., Awaitable[Any]]:
    """Return a coroutine function compatible with asyncio.sleep."""

    async def virtual_sleep(delay: float | int = 0, result: Any = None) -> Any:
        await clock.sleep(delay)
        return result

    return virtual_sleep
