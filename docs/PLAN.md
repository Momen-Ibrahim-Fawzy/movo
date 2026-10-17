# Imaa — Product & Implementation Plan

> **Imaa** (Arabic: **إيماءة**, "a gesture / a nod") lets people control their computer and phone
> with hand and head gestures, using only the camera they already have.
> Everything is processed live, on the device. No video is recorded, stored, or sent anywhere.

This document is the single source of truth for scope, decisions, and delivery order.
Research notes that informed it are in [RESEARCH.md](RESEARCH.md); the technical design is in
[ARCHITECTURE.md](ARCHITECTURE.md); the visual system is in [DESIGN.md](DESIGN.md).

---

## 1. Goals

| # | Goal | How we measure it |
|---|------|-------------------|
| G1 | Control common tasks hands-free: volume, media, slides, scrolling, zoom, tabs, screenshot, microphone, ad skipping | Every action reachable from a default gesture |
| G2 | Head gestures as a first-class input, so people who cannot use their hands are included | Every action can be bound to a head gesture |
| G3 | Privacy by construction | Frames live only in memory; no network code touches frames; no telemetry |
| G4 | Runs on modest hardware | < 15 % of one CPU core on a 2018 dual-core laptop in *Eco* mode; idle mode when nobody is in view |
| G5 | Friendly for everyone | Arabic + English (full RTL), light/dark/system themes, onboarding, live practice mode |
| G6 | Everywhere | Windows, macOS, Linux desktop; Android phone/tablet/ChromeOS; iOS/iPadOS |

## 2. Non-goals (v1)

- Sign-language translation (different problem, different models).
- Cloud features, accounts, or sync. Settings stay on the device; export/import is a file.
- Controlling *other apps* on iOS — Apple does not allow it (see §6.3). iOS gets an in-app
  gesture viewer and a "remote camera" mode for the desktop instead.

## 3. Feature scope

### 3.1 Actions (all platforms where the OS allows)

| Category | Actions |
|----------|---------|
| Audio & media | Volume up/down, mute, play/pause (Space), media play/pause key, next/previous track |
| Navigation | Next / previous (→ / ←), Page Down / Page Up, Up / Down, Enter, Escape, browser back/forward |
| Presentation | Next / previous slide, black screen, start/stop slideshow, full screen |
| Scroll & zoom | Scroll up/down (speed follows how far you move), zoom in / out / reset |
| Tabs & windows | Next / previous tab, new tab, close tab, switch app, show desktop |
| Capture | Screenshot (saved to *Pictures/Imaa*, optional copy to clipboard) |
| Microphone | Toggle microphone mute (system-wide), or a meeting app's own shortcut via profiles |
| Ads | Skip ad — clicks a visible "Skip" button (browser helper, Windows UI Automation, Android Accessibility) |
| Mouse | Air mouse (index finger moves the cursor, pinch clicks), head pointer (head moves the cursor) |
| Control | Pause / resume Imaa itself, custom keyboard shortcut (any key combination) |

### 3.2 Hand gestures (defaults — every one is re-bindable)

| Gesture | Default action | Why this mapping |
|---------|----------------|------------------|
| 👍 Thumb up (hold) | Volume up, repeats | Universal "more" |
| 👎 Thumb down (hold) | Volume down, repeats | Universal "less" |
| 👉 Point right | Next (→) — also next slide | Direction = direction |
| 👈 Point left | Previous (←) | Direction = direction |
| 🤏 Pinch (quick tap) | Play / pause (Space) | "Click" in the air |
| ☝️ Index up, move up / down | Scroll up / down | Works like a joystick: further = faster |
| 🤏 Pinch & hold, move up / down | Zoom in / out | "Grab and pull" (as on modern headsets) |
| ✋ Open hand swipe right / left | Next / previous tab | Like turning a page |
| ✌️ Victory | Screenshot | The "photo" pose |
| 🤙 Call sign | Toggle microphone | The "phone call" pose |
| ✊ Fist | Skip ad | "Punch the ad" |
| 🤘 Rock sign (hold longer) | Pause / resume Imaa | Deliberate, rarely made by accident |
| 🖖 Three fingers | *(free)* | Available for custom bindings |

Safety rules borrowed from the reference behaviour and extended:
static poses must be **held** briefly (default 0.35 s, longer for rare actions);
diagonal pointing is ignored; poses are ignored while the hand is moving fast;
each gesture has a cooldown; non-repeating gestures need the hand to change pose before firing again.

### 3.3 Head gestures

Two engines, selectable in Settings:

| Mode | Model | Cost | Gestures |
|------|-------|------|----------|
| **Light** | BlazeFace short-range (230 KB, ~3 ms) | Very low | Turn, tilt, look up/down, nod, shake |
| **Accurate** | Face Landmarker + blendshapes (3.7 MB, ~4 ms) | Low | All of Light, plus mouth open, smile, eyebrows raised, head pointer |

| Head gesture | Default action |
|--------------|----------------|
| Nod (quick down-up) | Play / pause |
| Shake (quick left-right) | Skip ad |
| Tilt head right / left (hold) | Next / previous |
| Look up / down (hold) | Scroll up / down, repeats |
| Turn head right / left (hold) | Next / previous tab |
| Open mouth (Accurate) | Toggle microphone |
| Smile (Accurate) | Screenshot |
| Raise eyebrows (Accurate) | *(free)* |

Head pose is measured *relative to the person's own neutral pose*, captured automatically in the first
second and re-captured with one click ("Recalibrate"), so posture, camera height and glasses don't matter.

### 3.4 App features

- **Start / Stop / Pause inside the app** — one big button on Home, the tray/menu-bar icon, and a global
  shortcut (default **Ctrl + Alt + G**). Closing the window keeps Imaa in the tray (configurable); *Quit* is explicit.
- **Live preview** with skeleton overlay (optional — turning it off saves CPU). Preview is never produced when
  the window is hidden.
- **On-screen feedback (HUD)** — small, click-through bubble that shows the action just performed
  (e.g. "🔊 Volume up"). Position and on/off configurable.
- **Practice mode** — gesture cards light up when Imaa sees that gesture, so people learn without triggering actions.
- **Profiles** — General, Presentation, Media, Browser, Meeting. Each has its own bindings and an optional list of apps;
  Imaa switches automatically when that app is in front (e.g. PowerPoint → Presentation).
- **Settings** — language (System / English / العربية), theme (System / Light / Dark), camera, resolution, mirror,
  power mode (Eco / Balanced / Performance), hand & head sensitivity, hold times, HUD, sounds, start with the system,
  start minimised, start detecting on launch, global shortcut, screenshot folder, import/export, reset.
- **Onboarding** — 3 short steps: language & theme → privacy & camera → gesture tour.
- **Integrations (all local, all opt-in)**
  - *Browser helper* (Chrome/Edge/Brave/Firefox extension) for reliable ad skipping; talks only to `127.0.0.1`.
  - *Phone as remote camera* — the phone recognises gestures and sends only the gesture name to the
    desktop over the local network after pairing with a 6-digit code. Useful when the desktop has no webcam
    or for presenting from across a room.

### 3.5 Mobile

- **Android (phones, tablets, ChromeOS)** — full system control through an Accessibility Service: volume, media,
  back/home/recents, scroll, zoom (two-finger pinch), swipe next/previous, screenshot, microphone mute, ad skipping
  (finds and taps "Skip"), status bubble with Stop. Camera runs in a foreground service with the system privacy indicator.
- **iOS / iPadOS** — Apple Vision framework (built in, no model download, Neural Engine). In-app gesture viewer for
  PDFs and photos (next/previous, scroll, zoom), practice mode, and remote-camera mode for the desktop.

## 4. Key decisions

| Decision | Choice | Alternatives considered | Reason |
|----------|--------|------------------------|--------|
| Desktop stack | Python 3.10+ · PySide6 (Qt 6) · MediaPipe Tasks · OpenCV capture · pynput | Electron + MediaPipe JS; Tauri; Flutter desktop | One codebase for 3 OSes, native tray/RTL/HiDPI, mature key injection, small CPU footprint (no browser engine) |
| Gesture logic | Own geometric classifier on 21 landmarks + state machines | MediaPipe Gesture Recognizer (7 fixed gestures) | Needs 13+ gestures, pinch-drag, swipes, joystick scroll; pure Python → unit-testable and portable to Kotlin/Swift |
| Head pose | Keypoint geometry relative to a personal baseline | Solving PnP, transformation matrices | Same maths for both engines, robust, cheap, no camera calibration |
| Android | Kotlin · Jetpack Compose · CameraX · MediaPipe Tasks · AccessibilityService | Flutter, React Native | System control needs native services anyway |
| iOS | Swift · SwiftUI · Vision · AVFoundation · PDFKit | MediaPipe iOS | Vision is built in, faster on Neural Engine, smaller app |
| i18n | JSON string tables + `tr()` (desktop), Android string resources, iOS String Catalog | Qt Linguist | No build-time tools; live language switching; easy for translators |
| Packaging | PyInstaller (one-folder) per OS in GitHub Actions; Inno Setup on Windows; DMG on macOS; AppImage + tar.gz on Linux | Nuitka, Briefcase | Proven with MediaPipe + Qt |

## 5. Performance budget

- Capture 640×480 (configurable), a reader thread keeps only the newest frame (no lag build-up).
- MediaPipe in VIDEO mode → the hand tracker re-uses the previous hand box and skips palm detection.
- **Adaptive frame rate**: Eco 12 fps · Balanced 20 fps · Performance 30 fps; drops to 5 fps after 3 s with nobody in view;
  back to full speed on the first detection.
- Hand + head enabled together → models alternate frames instead of both running every frame.
- Preview frames are only drawn when the window is visible (≤ 15 fps, downscaled).
- Models are bundled (12 MB total) — the app never downloads anything at run time.

## 6. Privacy & platform constraints

1. Frames are numpy arrays in RAM, overwritten every frame. There is no code path that writes a frame to disk or socket.
2. Network listeners are off by default except the browser helper, which binds to `127.0.0.1` only and rejects any origin
   that is not a browser extension. The phone remote listens on the LAN only when the user turns it on, and requires pairing.
3. iOS: apps cannot inject input into other apps or the system; that is why iOS ships the viewer + remote mode.
4. Android: Google Play only lets apps declare `isAccessibilityTool` when helping people with disabilities is the primary
   purpose. Imaa's in-app disclosure explains exactly what the service does before the user turns it on (required by Play policy).
5. macOS: needs *Camera* and *Accessibility* permission (the app detects missing permission and opens the right settings page).
   Screenshots need *Screen Recording*.
6. Linux: key injection works on X11; on Wayland Imaa uses `ydotool`/`pactl` fallbacks where available and says so in Settings.

## 7. Business model (see [BUSINESS.md](BUSINESS.md))

Free core with a one-time "Pro" upgrade (profiles, head pointer, phone remote, custom shortcuts), discounted/free licences
for people with disabilities and schools, and B2B site licences for clinics, labs, kitchens and lecture halls
(touch-free = hygiene). No ads, no data sale — privacy is the product.

## 8. Delivery plan

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 0 | Research, naming, brand, this plan | ✅ |
| 1 | Repository skeleton, docs, licences, CI | ✅ |
| 2 | Desktop core: camera, trackers, hand classifier, head classifier, dispatcher, actions | ✅ |
| 3 | Desktop UI: theme system, Home, Gestures, Head, Profiles, Settings, About, tray, HUD, onboarding, EN/AR | ✅ |
| 4 | Integrations: browser helper extension, phone remote server, auto-profiles, autostart | ✅ |
| 5 | Unit tests (classifiers, dispatcher, config, translations) + UI smoke tests | ✅ |
| 6 | Packaging workflows: Windows, macOS, Linux | ✅ |
| 7 | Android app | ✅ |
| 8 | iOS app | ✅ |
| 9 | User guides EN/AR, privacy policy, release | ✅ |

## 9. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| False triggers | Hold time, cooldown, motion guard, pause gesture, per-gesture enable switch, practice mode |
| Poor lighting | Status chip warns "Low light"; tips in onboarding |
| macOS/Wayland input restrictions | Clear in-app banners with one-click fixes |
| Ad sites change their markup | Text-based button matching (EN/AR) rather than fixed selectors only |
| Accessibility policy review (Play) | Prominent disclosure screen; accessibility-first positioning |
