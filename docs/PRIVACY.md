# Privacy

**Short version: Imaa looks at your camera only while it is running, only on your device, and never keeps
or sends a picture.**

## What happens to camera pictures

1. The camera delivers a frame into a single in-memory slot that is overwritten by the next frame.
2. The frame is analysed by on-device models (MediaPipe on desktop/Android, Apple Vision on iOS) into a few
   dozen numbers (finger joint positions, head angles, expression scores).
3. Those numbers are turned into a gesture name like `thumb_up`; the picture is discarded.
4. While the Imaa window is visible and *Show camera* is on, a downscaled copy is drawn in the preview. It is
   never written to disk.

There is no code path that writes a camera frame to a file, a network socket, the clipboard or a log.

## Network

| Connection | Default | Direction | Content |
|------------|---------|-----------|---------|
| Browser helper bridge | On | `127.0.0.1` only — not reachable from other devices; web pages are rejected by origin check | Commands such as "skip ad" and the answer "clicked: yes/no" |
| Phone remote | **Off** | Local network, pairing code required (HMAC challenge), rate-limited, brute-force lock-out | Gesture names only, e.g. `{"gesture": "thumb_up"}` |
| Internet | Never at run time | — | Models are bundled with the app |

## What is stored

- Your settings (language, theme, gesture bindings, profiles) in a JSON file in your user profile:
  - Windows `%APPDATA%\Imaa\settings.json`
  - macOS `~/Library/Application Support/Imaa/settings.json`
  - Linux `~/.config/imaa/settings.json`
- A small rotating log (`imaa.log`, ≤ 1 MB) with technical messages — no images, no keystrokes, no window titles.
- Screenshots you ask for (✌️), saved to *Pictures/Imaa*.

## Permissions and why

| Permission | Platform | Why |
|------------|----------|-----|
| Camera | all | See gestures |
| Accessibility | macOS | Send keys and mouse events to other apps |
| Screen Recording | macOS | Screenshots |
| Accessibility service | Android | Perform taps/swipes/global actions you request; find a visible "Skip ad" button when you make the skip gesture |
| Foreground service (camera), notifications | Android | Keep working when another app is in front; show a persistent notice with Pause/Stop |
| Local network | iOS/Android | Optional phone-remote mode only |

## No tracking

No accounts, analytics, crash reporters, advertising SDKs or third-party trackers.
