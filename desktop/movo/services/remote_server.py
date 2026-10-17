"""Phone-as-remote receiver (opt-in).

The phone recognises gestures itself and sends only small JSON messages such as
``{"type": "gesture", "gesture": "thumb_up", "phase": "start"}``. No images are ever sent.

Pairing: the server sends a random nonce; the phone answers with HMAC-SHA256(code, nonce). Failed attempts
are rate-limited per address. See docs/REMOTE_PROTOCOL.md.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import socket
import time
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Optional

from websockets.asyncio.server import Server, ServerConnection, serve

from movo import __version__
from movo.core.catalog import ACTIONS_BY_ID, ALL_GESTURES
from movo.core.events import GestureEvent
from movo.services import aio

log = logging.getLogger(__name__)
PROTOCOL_VERSION = 1
MAX_MSGS_PER_SECOND = 30
MAX_FAILURES = 5
BAN_SECONDS = 60


def proof(code: str, nonce: str) -> str:
    return hmac.new(code.encode(), nonce.encode(), hashlib.sha256).hexdigest()


def local_addresses() -> list[str]:
    addrs: list[str] = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))  # no packet is sent; this only picks the LAN interface
        addrs.append(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in addrs and not ip.startswith("127."):
                addrs.append(ip)
    except OSError:
        pass
    return addrs or ["127.0.0.1"]


class RemoteServer:
    def __init__(
        self,
        port: int,
        code: str,
        on_event: Callable[[GestureEvent], None],
        on_action: Callable[[str], None],
        on_change: Optional[Callable[[list[str]], None]] = None,
    ):
        self.port = port
        self.code = code
        self.on_event = on_event
        self.on_action = on_action
        self.on_change = on_change
        self._server: Optional[Server] = None
        self._devices: dict[ServerConnection, str] = {}
        self._failures: dict[str, deque] = defaultdict(deque)
        self.error: Optional[str] = None

    @property
    def devices(self) -> list[str]:
        return list(self._devices.values())

    def pairing_uri(self) -> str:
        return f"movo://pair?host={local_addresses()[0]}&port={self.port}&code={self.code}"

    def start(self) -> bool:
        try:
            aio.run(self._start(), timeout=5)
            return True
        except Exception as exc:
            self.error = str(exc)
            log.warning("remote server could not start: %s", exc)
            return False

    def stop(self) -> None:
        if self._server is not None:
            try:
                aio.run(self._stop(), timeout=5)
            except Exception:
                log.exception("remote server stop failed")

    async def _start(self) -> None:
        self._server = await serve(self._handler, "0.0.0.0", self.port, ping_interval=20, max_size=4096)

    async def _stop(self) -> None:
        assert self._server is not None
        self._server.close()
        await self._server.wait_closed()
        self._server = None
        self._devices.clear()
        self._changed()

    def _banned(self, addr: str) -> bool:
        q = self._failures[addr]
        now = time.monotonic()
        while q and now - q[0] > BAN_SECONDS:
            q.popleft()
        return len(q) >= MAX_FAILURES

    async def _handler(self, ws: ServerConnection) -> None:
        addr = ws.remote_address[0] if ws.remote_address else "?"
        if self._banned(addr):
            await ws.close(4003, "too many attempts")
            return
        nonce = secrets.token_hex(16)
        await ws.send(json.dumps({"type": "challenge", "nonce": nonce, "server": "Movo", "version": PROTOCOL_VERSION}))
        try:
            raw = await ws.recv()
            msg = json.loads(raw)
        except Exception:
            return
        if (
            not isinstance(msg, dict)
            or msg.get("type") != "auth"
            or not hmac.compare_digest(str(msg.get("proof", "")), proof(self.code, nonce))
        ):
            self._failures[addr].append(time.monotonic())
            await ws.close(4001, "pairing failed")
            return
        device = str(msg.get("device", "Phone"))[:40]
        self._devices[ws] = device
        self._changed()
        await ws.send(json.dumps({"type": "welcome", "app_version": __version__}))
        window: deque = deque()
        try:
            async for raw in ws:
                now = time.monotonic()
                window.append(now)
                while window and now - window[0] > 1.0:
                    window.popleft()
                if len(window) > MAX_MSGS_PER_SECOND:
                    continue
                self._dispatch(raw)
        except Exception:
            pass
        finally:
            self._devices.pop(ws, None)
            self._changed()

    def _dispatch(self, raw) -> None:
        try:
            msg = json.loads(raw)
        except ValueError:
            return
        if not isinstance(msg, dict):
            return
        if msg.get("type") == "gesture" and msg.get("gesture") in ALL_GESTURES:
            phase = "repeat" if msg.get("phase") == "repeat" else "start"
            try:
                mag = max(0.0, min(1.0, float(msg.get("magnitude", 1.0))))
            except (TypeError, ValueError):
                mag = 1.0
            self.on_event(GestureEvent(msg["gesture"], phase, mag, "remote"))
        elif msg.get("type") == "action" and msg.get("action") in ACTIONS_BY_ID:
            self.on_action(msg["action"])

    def _changed(self) -> None:
        if self.on_change:
            self.on_change(self.devices)
