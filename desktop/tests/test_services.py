import asyncio
import json

import pytest

from imaa.actions.keys import parse_shortcut
from imaa.actions.skip_ad import matches
from imaa.core.events import GestureEvent
from imaa.services.browser_bridge import BrowserBridge
from imaa.services.remote_server import RemoteServer, proof

websockets = pytest.importorskip("websockets")
from websockets.asyncio.client import connect  # noqa: E402


@pytest.mark.parametrize(
    "text", ["Skip", "Skip Ad", "Skip ads ›", "تخطي", "تخطي الإعلانات", "Passer l'annonce", "Omitir anuncio"]
)
def test_skip_matches(text):
    assert matches(text)


@pytest.mark.parametrize("text", ["", "Skip to content", "Subscribe", "Skipping stones", "Next video"])
def test_skip_rejects(text):
    assert not matches(text)


def test_parse_shortcut():
    from imaa.actions.keys import Key

    assert parse_shortcut("ctrl+shift+m") == [Key.ctrl, Key.shift, "m"]
    assert parse_shortcut("F5") == [Key.f5]
    with pytest.raises(ValueError):
        parse_shortcut("ctrl+banana")


def test_remote_pairing_and_events(unused_port):
    events, actions = [], []
    server = RemoteServer(unused_port, "123456", events.append, actions.append)
    assert server.start()

    async def client(code):
        async with connect(f"ws://127.0.0.1:{unused_port}") as ws:
            challenge = json.loads(await ws.recv())
            await ws.send(json.dumps({"type": "auth", "device": "Test phone", "proof": proof(code, challenge["nonce"])}))
            reply = await ws.recv()
            if json.loads(reply)["type"] != "welcome":
                return False
            await ws.send(json.dumps({"type": "gesture", "gesture": "thumb_up", "phase": "start"}))
            await ws.send(json.dumps({"type": "gesture", "gesture": "evil"}))
            await ws.send(json.dumps({"type": "action", "action": "next"}))
            await asyncio.sleep(0.2)
            return True

    try:
        assert asyncio.run(client("123456"))
        with pytest.raises(Exception):
            asyncio.run(client("000000"))
    finally:
        server.stop()
    assert events == [GestureEvent("thumb_up", "start", 1.0, "remote")]
    assert actions == ["next"]


def test_bridge_rejects_web_pages(unused_port):
    bridge = BrowserBridge(unused_port)
    assert bridge.start()

    async def try_origin(origin):
        async with connect(f"ws://127.0.0.1:{unused_port}", origin=origin) as ws:
            await ws.send(json.dumps({"type": "ping"}))
            return json.loads(await ws.recv())["type"]

    try:
        with pytest.raises(Exception):
            asyncio.run(try_origin("https://evil.example"))
        assert asyncio.run(try_origin("chrome-extension://abcdef")) == "pong"
        assert bridge.request_skip(timeout=0.2) is None  # client already gone
    finally:
        bridge.stop()


@pytest.fixture
def unused_port():
    import socket

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port
