# Eye gestures — research and plan

Goal: let people control Imaa with their eyes alone — **with or without glasses** — for when hands and head
movement are unavailable or inconvenient (accessibility, eating, holding something, lying down).

## 1. What we learned

| Topic | Finding | Consequence for Imaa |
|-------|---------|----------------------|
| Signals available on desktop/Android | MediaPipe Face Landmarker returns 478 landmarks **including 10 iris points** and 52 ARKit-style blendshapes, among them `eyeBlinkLeft/Right`, `eyeLookUp/Down/In/Out*`, `eyeSquint*` (values 0–1) | Already loaded in *Accurate* head mode — eye gestures cost **no extra model** and ~0 extra CPU |
| Classic blink metric | *Eye Aspect Ratio* (EAR, Soukupová & Čech 2016): eyelid opening ÷ eye width; widely used with MediaPipe landmarks | Use EAR as a second, geometric signal next to the learned blendshape |
| Known failure modes | Noise, poor landmarks and fast head motion create false blinks; the usual fix is temporal smoothing / multi-frame features | Median filter + hysteresis + minimum durations; ignore eye gestures while the head moves |
| Glasses | No published benchmark of MediaPipe blink/iris accuracy with glasses; practitioners report that **glare** and back-light degrade iris landmarks; lenses also **magnify/shrink** the eye (changes absolute EAR) | Never use fixed thresholds: **per-user calibration** (open/closed/centre) plus a *glasses* option that leans on the learned blendshape and smooths more |
| Natural blinking | People blink ~15–20×/min, each 100–400 ms | Never map a *single normal blink*. Use double blink, long blink, winks, eyes-closed and held glances |
| Looking down / smiling | Looking down lowers the upper lid; smiling squints both eyes | Suppress closure when `eyeLookDown` is high; suppress winks while smiling |
| Webcam gaze *pointing* | Needs screen calibration and is still imprecise on webcams | Not in v1 — we use **coarse glances** (left/right/up/down) instead; gaze pointer is on the roadmap |
| iOS | Vision gives eye contours and pupils (no blink scores); ARKit gives blink blendshapes on TrueDepth devices | v1 iOS uses EAR + pupil position; ARKit is a later upgrade |

Sources: [MediaPipe Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker) ·
[EAR blink detection preprint](https://preprints.org/manuscript/202410.0131/v1) ·
[MediaPipe vs Dlib EAR (IEICE FIT 2023)](https://www.ieice.org/publications/conference-FIT-DVDs/FIT2023/data/html/program/pdf/J-043.pdf) ·
[EAR failure modes](https://hcl.pyimagesearch.com/?p=5360) ·
[Unsupervised EAR blink detection](https://mints.utdallas.edu/?p=142) ·
[Glasses reflections and eye direction](https://forum.opencv.org/t/how-to-remove-reflections-when-wearing-glasses-in-order-to-detect-the-eye-directions-correctly/2987) ·
[Webcam eye-gesture controllers & glare](https://hackernoon.com/i-turned-my-eyes-into-a-game-controller-with-nothing-but-a-webcam) ·
[Iris landmarks for gaze (Roboflow)](https://blog.roboflow.com/build-eye-tracking-in-browser/) ·
[Landmark-based gaze limits (arXiv 2026)](https://arxiv.org/html/2603.24724v1) ·
[EyeGestures](https://www.toolmage.com/en/tool/eyegestures/) ·
[SensePilot](https://zerocon26.zeroproject.org/participations/644782)

## 2. Gesture vocabulary

| Gesture | How | Default action | Why this default |
|---------|-----|----------------|-----------------|
| 😉 **Wink left** | Close only your left eye ~0.35 s | Previous | Left = back |
| 😉 **Wink right** | Close only your right eye ~0.35 s | Next | Right = forward |
| 👁️ **Double blink** | Two quick deliberate blinks | Play / pause | Most people can do it, even if they can't wink |
| 😌 **Long blink** | Close both eyes 0.6–1.5 s, then open | Skip ad | Harmless if nothing to skip |
| 😴 **Eyes closed** | Keep both eyes closed 2 s | Pause / resume Imaa | Safety switch that needs no hands or head |
| 👀 **Look up / down** (hold) | Glance to the top/bottom of the screen | Scroll up / down, repeating | Reading hands-free |
| 👀 **Look left / right** (hold) | Glance far left/right | *(free)* | Off by default: people glance aside often |

"Left/right" is always the **user's** left/right, whatever the mirror setting.

## 3. Detection design

```
Face Landmarker (Accurate mode) ─► per-eye features ─► smoothing ─► calibration ─► state machines ─► events
   landmarks + iris + blendshapes      EAR, blink score,     median-3/5   personal open/closed   wink / blinks /
                                       iris x/y, look scores  per signal   levels & gaze centre   closed / glances
```

**Per-eye closure** `c ∈ [0,1]` fuses two independent signals:

- geometric: `c_geo = clamp((EAR_open − EAR) / (0.6 · EAR_open))` using the *personal* open-eye EAR,
- learned: `c_bs = eyeBlink` blendshape.
- `c = w·c_bs + (1−w)·c_geo` with `w = 0.5`, or **0.6 with glasses** (the learned model copes better with frames and glare than raw lid distances).
- If the lids are clearly shut (`c_geo ≥ 0.9`) and the learned score agrees at least partly (`≥ 0.3`), the eye counts as closed — in our test with an occluded eye the learned score only reached 0.41 while the geometry was unambiguous.
- Looking down lowers the lid: `c −= 0.35 · eyeLookDown`.

An eye is *closed* above 0.6 and *open* again below 0.35 (hysteresis). Each signal passes a median filter
(3 frames, **5 with glasses**) so a single glare frame can't produce a blink.

**Gaze** = iris centre position between the eye corners (horizontal) and between the lids (vertical), averaged
over both eyes and fused with the `eyeLookUp/Down` blendshapes, relative to the user's calibrated centre.

**Safety gates** — eye gestures are ignored when:
- the head is turned/tilted beyond 20° or the face is not found,
- a head gesture (nod/shake) just fired,
- the user is smiling (winks) or both eyes are half-closed (squinting).

**Calibration** (Eye gestures page → *Calibrate*, 6 seconds): eyes open looking at the screen centre (2 s),
eyes closed (2 s), then normal blinking (2 s). Stores the personal open/closed levels and gaze centre in the settings,
so glasses, eye shape and droopy lids are handled per person. Without calibration Imaa auto-learns the open level
from the last 20 s (90th percentile of openness).

**Frame rate** — blinks are short, so when eye gestures are on the face model runs **every frame** (hand model on
alternate frames). The face model is ~4 ms, so the cost stays low.

## 4. Implementation plan

| # | Work | Where |
|---|------|-------|
| 1 | Eye features from Face Landmarker (EAR, iris, blendshapes, screen-side → user-side mapping) | `desktop/imaa/core/trackers.py` |
| 2 | `EyeRecognizer` (smoothing, calibration, wink/double/long/closed/glance state machines, gates) | `desktop/imaa/core/eyes.py` |
| 3 | Catalog: 9 eye gestures + defaults; settings `eyes.*`; engine scheduling | `catalog.py`, `config.py`, `engine.py` |
| 4 | UI: **Eye gestures** page (enable, *I wear glasses*, sensitivity, calibration wizard, live eye meter, gesture cards); Home quick switch; guide step | `ui/pages/` |
| 5 | Tests with synthetic eyes: winks, double/long blink, closed, glances, natural blinks ignored, glare spikes ignored, look-down ≠ blink, smile/head gates | `tests/test_eyes.py` |
| 6 | Android port (Face Landmarker already in Accurate mode) + Eyes tab + glasses switch | `mobile/android` |
| 7 | iOS port with Vision eye contours + pupils (EAR-based) | `mobile/ios` |
| 8 | Docs: user guides EN/AR, README | `docs/`, `README*` |

## 5. Roadmap after v1

- Gaze pointer with 9-point screen calibration and dwell-click (needs good lighting; best with an external webcam).
- ARKit eye blendshapes on iPhones/iPads with TrueDepth.
- Morse-style blink typing for people who can only blink.
- Automatic glasses detection from the eye-region appearance to choose the glasses profile without asking.
