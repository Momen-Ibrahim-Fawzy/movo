"""A single background asyncio loop shared by the local network services."""

from __future__ import annotations

import asyncio
import threading
from typing import Optional

_loop: Optional[asyncio.AbstractEventLoop] = None
_lock = threading.Lock()


def loop() -> asyncio.AbstractEventLoop:
    global _loop
    with _lock:
        if _loop is None:
            _loop = asyncio.new_event_loop()
            threading.Thread(target=_loop.run_forever, name="movo-net", daemon=True).start()
        return _loop


def run(coro, timeout: Optional[float] = None):
    """Run a coroutine on the service loop from any thread and wait for the result."""
    return asyncio.run_coroutine_threadsafe(coro, loop()).result(timeout)


def spawn(coro):
    return asyncio.run_coroutine_threadsafe(coro, loop())
