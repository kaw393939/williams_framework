# Worker Test Harness Notes

## Virtual Clock Fixture (`virtual_clock`)
The `virtual_clock` fixture provides a deterministic substitute for `asyncio.sleep` so worker tests can fast-forward time without relying on wall-clock delays. The fixture is available globally via `tests/conftest.py` and yields a `VirtualClock` instance with the following helpers:

- `now()` – returns the current virtual time as a timezone-aware `datetime` in UTC.
- `advance(delta)` – moves the clock forward by either a `timedelta` or seconds.

### Example
```python
import asyncio
from datetime import timedelta

import pytest


@pytest.mark.asyncio
async def test_worker_retry_backoff(virtual_clock):
    attempts = []

    async def retrying_task():
        attempts.append(virtual_clock.now())
        await asyncio.sleep(5)
        attempts.append(virtual_clock.now())

    task = asyncio.create_task(retrying_task())

    await asyncio.sleep(0)  # registers the pending sleep
    virtual_clock.advance(timedelta(seconds=5))

    await task

    assert attempts[1] - attempts[0] == timedelta(seconds=5)
```

Use `advance()` to simulate time passage and unblock coroutines waiting on `asyncio.sleep`.
