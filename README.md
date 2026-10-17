<p align="center">
  <img src="branding/logo-128.png" width="96" alt="Imaa logo" />
</p>

<h1 align="center">Imaa · إيماءة</h1>

<p align="center">
  <b>Control your computer and phone with a wave of your hand or a nod of your head — privately.</b><br/>
  Everything happens on your device. No video is recorded, saved or sent anywhere.
</p>

<p align="center">
  <a href="README.ar.md">العربية</a> ·
  <a href="docs/USER_GUIDE.md">User guide</a> ·
  <a href="docs/PLAN.md">Plan</a> ·
  <a href="docs/ARCHITECTURE.md">Architecture</a> ·
  <a href="docs/PRIVACY.md">Privacy</a>
</p>

<p align="center">
  <img src="docs/screenshots/en-light-home.png" width="49%" alt="Home, light theme" />
  <img src="docs/screenshots/ar-dark-home.png" width="49%" alt="Home in Arabic, dark theme" />
</p>

---

## What it does

| Category | What you can do hands-free |
|----------|----------------------------|
| 🔊 Sound & media | Volume up / down, mute, play / pause, next / previous track |
| 📽️ Presentations | Next / previous slide, black screen, start the slideshow |
| 📜 Reading | Scroll up / down (speed follows your hand), zoom in / out |
| 📑 Browsing | Next / previous tab, back / forward, new / close tab |
| 📸 Screenshot | Saved to *Pictures/Imaa* and copied to the clipboard |
| 🎙️ Calls | Microphone on / off for the whole system |
| ⏩ Ads | Skip ads by pressing the visible *Skip* button for you |
| 🖱️ Mouse | Air mouse (index finger) or head pointer (head + open mouth to click) |
| ⌨️ Anything else | Bind any gesture to any keyboard shortcut |

### Default gestures

| Hand | Action | Head | Action |
|------|--------|------|--------|
| 👍 Thumb up (hold) | Volume up | 🙂 Nod | Play / pause |
| 👎 Thumb down (hold) | Volume down | 🙅 Shake | Skip ad |
| 👉 Point right | Next | ↗️ Tilt right | Next |
| 👈 Point left | Previous | ↖️ Tilt left | Previous |
| 🤏 Pinch | Play / pause | ⬆️ Look up (hold) | Scroll up |
| ☝️ Index up + move | Scroll | ⬇️ Look down (hold) | Scroll down |
| 🤏 Pinch, hold & pull | Zoom in / out | ➡️ Turn right | Next tab |
| ✋ Swipe right / left | Next / previous tab | ⬅️ Turn left | Previous tab |
| ✌️ Victory | Screenshot | 😮 Open mouth \* | Microphone on / off |
| 🤙 Call sign | Microphone on / off | 😁 Smile \* | Screenshot |
| ✊ Fist | Skip ad | | |
| 🤘 Rock sign (hold) | Pause / resume Imaa | | |

\* *Accurate* head mode. Every gesture can be re-assigned, switched off, or set per **profile**
(General, Presentation, Media, Browser, Meeting — Imaa switches automatically for the app in front).

### Built for everyone

- **Start, stop and pause inside the app** — big power button, tray menu, or **Ctrl + Alt + G** anywhere.
- **English and Arabic** with a full right-to-left layout, **light, dark or system** theme — switch instantly.
- **Practice mode** shows which gesture Imaa sees without doing anything.
- **Head gestures and head pointer** for people who can't use their hands.
- **Phone as a remote camera** — the phone app recognises gestures and sends only the gesture name to the computer over your Wi-Fi.
- **Light on resources** — about 10–20 ms of CPU per frame; rests at 5 fps when nobody is in view; Eco mode for older laptops.

## Platforms

| Platform | Package | Notes |
|----------|---------|-------|
| Windows 10 / 11 | Installer (`Imaa-Setup-x.y.z.exe`) or portable zip | No admin rights needed |
| macOS 12+ (Apple Silicon and Intel) | `Imaa-macOS-<arch>.dmg` | Allow *Camera* and *Accessibility* when asked |
| Linux (X11; Wayland with limits) | AppImage or tar.gz | Volume/mic via PulseAudio or PipeWire |
| Android 8+ (phones, tablets, ChromeOS) | APK | Full device control via an Accessibility Service |
| iOS / iPadOS 16+ | Xcode project | Gesture viewer for PDFs and photos, and remote camera for the desktop |
| Chrome, Edge, Brave, Firefox | Browser helper | Optional, for reliable ad skipping |

Downloads appear under **Releases** once a version is tagged. See the [user guide](docs/USER_GUIDE.md) for step-by-step setup.

## Privacy

Imaa only looks at the camera while it is running. Each picture is analysed in memory and replaced by the next one —
there is no code that writes camera pictures to disk or to the network. No accounts, analytics or ads.
The browser helper only listens on `127.0.0.1`; the phone remote is off until you turn it on and pair with a code.
Details: [docs/PRIVACY.md](docs/PRIVACY.md).

## Repository layout

```
desktop/            Windows · macOS · Linux app (Python, Qt, MediaPipe)
  imaa/core/        camera, trackers, hand & head recognisers, engine, dispatcher
  imaa/actions/     keyboard, mouse, volume, microphone, ad skipping
  imaa/services/    browser bridge, phone remote, auto-profiles, autostart, hotkey
  imaa/ui/          theme, pages, HUD, tray, onboarding
  imaa/i18n/        English and Arabic strings
  tests/            unit tests (synthetic hands and faces), service tests
  packaging/        PyInstaller spec, Windows installer, Linux desktop entry, icons
mobile/android/     Android app (Kotlin, Jetpack Compose, CameraX, MediaPipe)
mobile/ios/         iOS / iPadOS app (Swift, SwiftUI, Vision)
browser-extension/  Imaa Helper for Chromium browsers and Firefox
branding/           logo sources and exports
docs/               plan, research, architecture, design, privacy, guides
```

## Build from source

**Desktop** (Python 3.10–3.12):

```bash
cd desktop
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python scripts/download_models.py                   # one-time, ~12 MB of on-device models
python -m imaa                                      # run
pytest                                              # tests
pyinstaller packaging/imaa.spec --noconfirm         # package for this OS
```

**Android**: open `mobile/android` in Android Studio (or run `gradle assembleDebug`). The build downloads the models.
**iOS**: `cd mobile/ios && xcodegen && open Imaa.xcodeproj`.

Continuous integration builds every platform; tagging `vX.Y.Z` publishes a release.

## Licence

© 2026 Momen Ibrahim Fawzy. All rights reserved — see [LICENSE](LICENSE).
Open-source components are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
