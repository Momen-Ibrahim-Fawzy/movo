# Research notes

What we looked at before designing Imaa, and what we took from it. Collected October 2026.

## 1. The landscape

| Product | Platforms | Model | What it does well | Gap Imaa fills |
|---------|-----------|-------|-------------------|----------------|
| **Pawvis** | macOS 14+ | Free, open source | Hand-tracked cursor, finger-dip click, two-finger scroll, dwell click | macOS only; no head control; no presenter/media focus |
| **Wand** | macOS | Free | Shortcut-style gestures (launch apps, media, slides) | Single platform; no accessibility head mode |
| **Neural Lab AirTouch** | Windows, Android, Linux | Monthly subscription (individuals & companies) | 9 preset gestures, up to 15 custom | Paid subscription; no head gestures; no Arabic |
| **Virtual Touch Screen 2** | Windows (Steam, early access) | Paid | Touch-screen emulation | Unmaintained (no update in 13+ months) |
| **Google Project Gameface** | Windows, Android (open source) | Free | Head-driven cursor + facial gestures (raise eyebrows to click, open mouth…) mapped to mouse/keys; per-gesture thresholds | Mouse-centric; no hand gestures; no presentation/media profiles |
| **SensePilot** | Windows | Paid after 30-day trial | Webcam head tracking, facial gestures and speech | Paid; no hand gestures |
| **Smyle Mouse** | Windows | Paid | Head mouse with smile/dwell click | Paid; single purpose |
| **Apple Head/Eye tracking, Switch Control** | iOS, macOS | Built-in | System-level accessibility | Hard to discover; no gesture vocabulary for media/slides |

**Take-aways**

1. Nobody combines *hand* gestures for everyday convenience with *head* gestures for accessibility in one product.
2. Most tools are single-platform; the paid cross-platform option is subscription-based.
3. None ships a native Arabic interface or right-to-left layout.
4. Gameface proved that **MediaPipe Face Landmarker blendshapes** (52 expression scores) are good enough for facial "clicks" and that **per-gesture thresholds** matter — we adopted both.
5. Reviews of hand-gesture apps repeatedly mention *learning curve* and *lighting* — hence Imaa's practice mode, onboarding tour, low-light warning and adjustable hold times.

## 2. Technology choices

| Question | Finding | Decision |
|----------|---------|----------|
| On-device hand tracking | MediaPipe Hand Landmarker: 21 3-D landmarks, VIDEO mode reuses the previous hand box (tracking) and skips palm detection | Use it on desktop and Android; ~10–20 ms per frame on a laptop CPU in our tests |
| Cheap head pose | BlazeFace short-range: 6 keypoints, 230 KB, ~3 ms | "Light" head mode from eyes + nose geometry |
| Expressions | Face Landmarker + blendshapes (`jawOpen`, `mouthSmile*`, `browInnerUp`…), ~4 ms | "Accurate" head mode |
| iOS | Vision `VNDetectHumanHandPoseRequest` has the same 21 joints; `VNDetectFaceLandmarksRequest` gives eye/nose/lip landmarks; runs on the Neural Engine | Native Vision on iOS — no model download, smaller app |
| Webcam capture on Windows | OpenCV Media Foundation opened in ~2 s at 30 fps with hardware transforms disabled; DirectShow took 3.5–5 s at 10 fps; Qt Multimedia 1.75 s at 10 fps in the same light | OpenCV + MSMF (`OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS=0`), DirectShow fallback |
| Package size | OpenCV-contrib alone is 138 MB; headless OpenCV without the FFmpeg plugin, plus trimming Qt's software OpenGL/QML/PDF, brought the Windows build from 378 MB to 276 MB | Trim in the PyInstaller spec |
| Browser ad skip | Chrome 116+ keeps an extension service worker alive while a WebSocket exchanges messages within 30 s | Helper extension with 20 s keep-alive; desktop accepts only extension origins on 127.0.0.1 |

## 3. Platform rules that shape the product

- **Google Play — Accessibility API**: only apps whose *primary purpose* is helping people with disabilities may declare `isAccessibilityTool`; everyone else must show a prominent in-app disclosure and get affirmative consent before enabling the service. Imaa does both: it is positioned as an accessibility tool *and* shows the disclosure dialog (`disclosure_body`).
- **Android 14** requires the `FOREGROUND_SERVICE_CAMERA` permission and a camera-typed foreground service started while the app is visible.
- **iOS** does not allow apps to inject input into other apps. iOS therefore gets an in-app viewer plus a remote-camera mode for the desktop.
- **macOS** needs Accessibility permission for synthetic key events and Screen Recording for screenshots; both must be re-granted after replacing the app bundle.
- **Linux/Wayland** blocks synthetic input from regular clients; X11 works, Wayland needs `ydotool`. Volume and microphone go through PulseAudio/PipeWire (`pactl`).

## 4. Feature ideas collected (and where they landed)

| Idea | Source | Status |
|------|--------|--------|
| Practice mode with live highlight | Learning-curve complaints in reviews | ✅ v1 |
| Per-app profiles with auto-switching | Presenter and media use cases | ✅ v1 |
| Head pointer with mouth-open click | Gameface | ✅ v1 |
| Air mouse | Pawvis | ✅ v1 |
| Phone as remote camera (gesture names only) | Desktops without webcams, lecture halls | ✅ v1 |
| On-screen feedback bubble | General UX | ✅ v1 |
| Low-light warning, idle mode | Battery and reliability | ✅ v1 |
| Dwell click, custom recorded gestures (few-shot) | Pawvis, AirTouch | Roadmap |
| Two-hand zoom, laser pointer overlay for slides | Presenter feedback | Roadmap |
| Voice confirmations for blind/low-vision users | Accessibility | Roadmap |
| Smart-TV / Raspberry Pi kiosk build | "Touchless" kiosks, kitchens, clinics | Roadmap |

## Sources

- Pawvis — https://hunted.space/product/pawvis
- Wand — https://toolradar.com/tools/wand
- AirTouch (Engadget) — https://www.engadget.com/computing/accessories/neural-labs-airtouch-brings-gesture-control-to-windows-and-android-devices-with-just-a-webcam-180031750.html
- Virtual Touch Screen 2 — https://store.steampowered.com/app/2588630/Virtual_Touch_Screen_2/
- Project Gameface — https://developers.googleblog.com/en/project-gameface-makes-gaming-accessible-to-everyone/
- SensePilot (Zero Project 2026) — https://zerocon26.zeroproject.org/opportunities/UGFydGljaXBhdGlvbk9wcG9ydHVuaXR5OjIwMTQwMg==
- Smyle Mouse — https://askjan.org/vendors/Perceptive-Devices-LLC.cfm
- MediaPipe Hand Landmarker — https://ai.google.dev/mediapipe/solutions/vision/hand_landmarker
- Chrome extension WebSockets — https://developer.chrome.com/docs/extensions/mv3/tut_websockets
- Google Play Accessibility API policy — https://support.google.com/googleplay/android-developer/answer/10964491?hl=en
- Touchless UI in embedded products — https://www.cranksoftware.com/resources/blogs/why-touchless-gestures-should-matter-to-embedded-gui-development-teams
