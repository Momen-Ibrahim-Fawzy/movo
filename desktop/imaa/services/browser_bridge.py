"""Local bridge to the Imaa browser helper extension.

Listens on 127.0.0.1 only and accepts WebSocket connections whose Origin is a browser extension.
Web pages therefore cannot connect. The bridge only *sends* commands (e.g. "skip_ad") and receives the
result; no page content or browsing data is ever transferred.
"""

from __future__ import annotations

import asyncio
import http
import itertools
import json
import logging
from collections.abc import Callable
from typing import Optional

from websockets.asyncio.server import Server, ServerConnection, serve

from imaa.services import aio

log = logging.getLogger(__name__)
ALLOWED_ORIGIN_PREFIXES = ("chrome-extension://", "moz-extension://", "safari-web-extension://", "extension://")


class BrowserBridge:
    def __init__(self, port: int = 47812, on_change: Optional[Callable[[int], None]] = None):
        self.port = port
        self.on_change = on_change
        self._server: Optional[Server] = None
        self._clients: set[ServerConnection] = set()
        self._pending: dict[int, asyncio.Future] = {}
        self._ids = itertools.count(1)
        self.error: Optional[str] = None

    @property
    def connected(self) -> int:
        return len(self._clients)

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> bool:
        try:
            aio.run(self._start(), timeout=5)
            return True
        except Exception as exc:
            self.error = str(exc)
            log.warning("browser bridge could not start: %s", exc)
            return False

    def stop(self) -> None:
        if self._server is not None:
            try:
                aio.run(self._stop(), timeout=5)
            except Exception:
                log.exception("browser bridge stop failed")

    async def _start(self) -> None:
        self._server = await serve(self._handler, "127.0.0.1", self.port, process_request=self._check_origin, ping_interval=20)

    async def _stop(self) -> None:
        assert self._server is not None
        self._server.close()
        await self._server.wait_closed()
        self._server = None
        self._clients.clear()
        self._changed()

    @staticmethod
    def _check_origin(connection, request):
        origin = request.headers.get("Origin", "")
        if not origin.startswith(ALLOWED_ORIGIN_PREFIXES):
            return connection.respond(http.HTTPStatus.FORBIDDEN, "Forbidden\n")
        return None

    async def _handler(self, ws: ServerConnection) -> None:
        self._clients.add(ws)
        self._changed()
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(msg, dict):
                    continue
                if msg.get("type") == "result":
                    fut = self._pending.get(msg.get("id"))
                    if fut and not fut.done():
                        fut.set_result(bool(msg.get("clicked")))
                elif msg.get("type") == "ping":
                    await ws.send(json.dumps({"type": "pong"}))
        except Exception:
            pass
        finally:
            self._clients.discard(ws)
            self._changed()

    def _changed(self) -> None:
        if self.on_change:
            self.on_change(len(self._clients))

    # ------------------------------------------------------------------ commands
    def request_skip(self, timeout: float = 1.2) -> Optional[bool]:
        """Ask every connected browser to click a visible skip button.

        Returns True if one did, False if none found one, None when no helper is connected.
        """
        if not self._clients:
            return None
        try:
            return aio.run(self._broadcast("skip_ad", timeout), timeout=timeout + 1)
        except Exception:
            return False

    async def _broadcast(self, command: str, timeout: float) -> bool:
        futures = []
        for ws in list(self._clients):
            rid = next(self._ids)
            fut = asyncio.get_running_loop().create_future()
            self._pending[rid] = fut
            futures.append((rid, fut))
            try:
                await ws.send(json.dumps({"type": command, "id": rid}))
            except Exception:
                fut.set_result(False)
        try:
            done, _ = await asyncio.wait([f for _, f in futures], timeout=timeout)
            return any(f.result() for f in done if not f.cancelled())
        finally:
            for rid, _ in futures:
                self._pending.pop(rid, None)
