# Phone remote protocol (v1)

The phone app recognises gestures itself and sends only their names to the desktop app. The desktop applies its
own bindings and profiles.

## Transport

- WebSocket, `ws://<computer-ip>:<port>` (default port **47813**), local network only.
- Off by default on the desktop (Settings → Integrations → *Use my phone as a remote camera*).
- Pairing link (shown as a QR code on the desktop): `imaa://pair?host=192.168.1.20&port=47813&code=123456`.
  Scanning it with the phone's camera opens the Imaa app and fills in the details.

## Handshake

```
server → {"type": "challenge", "nonce": "<32 hex chars>", "server": "Imaa", "version": 1}
client → {"type": "auth", "device": "Pixel 8", "proof": hex(HMAC-SHA256(key = pairing code, msg = nonce))}
server → {"type": "welcome", "app_version": "1.0.0"}        # or close 4001 "pairing failed"
```

The pairing code itself never travels over the network. Five failed attempts from one address within 60 s
lock that address out for 60 s (close code 4003).

## Messages after pairing

```json
{"type": "gesture", "gesture": "thumb_up", "phase": "start", "magnitude": 1.0}
{"type": "gesture", "gesture": "index_up_move_down", "phase": "repeat", "magnitude": 0.6}
{"type": "action", "action": "next"}
```

- `gesture` must be one of the ids in `desktop/imaa/core/catalog.py`; unknown ids are ignored.
- `phase` is `start` or `repeat`; `magnitude` is clamped to 0–1.
- `action` (optional, for on-screen remote buttons) must be a known action id; `custom_shortcut` is refused.
- More than 30 messages per second are dropped. Messages are limited to 4 KB.

## Security notes

- The channel is not encrypted (local network, no secrets are exchanged after pairing, and only gesture names travel).
  A future version may add TLS with a certificate fingerprint embedded in the QR code.
- Regenerate the pairing code at any time from the desktop settings; connected phones must pair again.
