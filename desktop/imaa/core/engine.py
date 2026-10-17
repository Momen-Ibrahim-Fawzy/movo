"""The vision loop: camera → trackers → recognisers → dispatcher.

Runs on its own thread and talks to the UI only through callbacks. Frames never leave this module except
as a downscaled preview image handed to the UI while the window is visible.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from imaa.config import Settings
from imaa.core.camera import Camera
from imaa.core.dispatcher import Dispatcher
from imaa.core.events import GestureEvent
from imaa.core.hand import HandRecognizer, HandSettings
from imaa.core.head import HeadRecognizer, HeadSettings
from imaa.core.pointer import AirMouse, HeadPointer

log = logging.getLogger(__name__)

POWER_FPS = {"eco": 12, "balanced": 20, "performance": 30}
IDLE_FPS = 5
IDLE_AFTER_S = 3.0
PREVIEW_MAX_FPS = 15
PREVIEW_WIDTH = 480

HAND_CONNECTIONS = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (13, 17),
    (17, 18),
    (18, 19),
    (19, 20),
    (0, 17),
)


@dataclass
class EngineStats:
    fps: float = 0.0
    process_ms: float = 0.0
    hand: bool = False
    face: bool = False
    idle: bool = False
    low_light: bool = False
    hand_pose: Optional[str] = None
    head_pose: Optional[str] = None
    calibrated: bool = False


@dataclass
class EngineCallbacks:
    state: Callable[[str], None] = lambda s: None  # "starting" | "running" | "stopped" | "error:<key>"
    preview: Callable[[np.ndarray], None] = lambda img: None  # RGB uint8
    stats: Callable[[EngineStats], None] = lambda s: None
    pointer_move: Callable[[float, float, bool], None] = lambda x, y, relative: None
    pointer_button: Callable[[str], None] = lambda b: None


class Engine:
    def __init__(self, settings: Settings, dispatcher: Dispatcher, callbacks: Optional[EngineCallbacks] = None):
        self.settings = settings
        self.dispatcher = dispatcher
        self.cb = callbacks or EngineCallbacks()
        self.preview_enabled = True
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._restart_face = threading.Event()
        self.hand = HandRecognizer(HandSettings())
        self.head = HeadRecognizer(HeadSettings())
        self.air_mouse = AirMouse()
        self.head_pointer = HeadPointer()
        self.running = False

    # ------------------------------------------------------------------ control
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="imaa-engine", daemon=True)
        self._thread.start()

    def stop(self, wait: bool = True) -> None:
        self._stop.set()
        if wait and self._thread and self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout=3)

    @property
    def alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def join(self, timeout: float) -> None:
        if self._thread is not None and threading.current_thread() is not self._thread:
            self._thread.join(timeout)

    def recalibrate_head(self) -> None:
        self.head.recalibrate()

    def face_mode_changed(self) -> None:
        self._restart_face.set()

    def _apply_settings(self) -> None:
        s = self.settings
        hs = self.hand.s
        hs.hold_scale = float(s.get("hand.hold_scale", 1.0))
        hs.swipe_enabled = bool(s.get("hand.swipe_enabled", True))
        h = self.head.s
        h.sensitivity = float(s.get("head.sensitivity", 1.0))
        h.hold_scale = float(s.get("head.hold_scale", 1.0))
        self.dispatcher.executor.scroll_speed = float(s.get("hand.scroll_speed", 1.0))
        self.head_pointer.speed = float(s.get("pointer.speed", 1.0))

    # ------------------------------------------------------------------ loop
    def _run(self) -> None:
        try:
            self._loop()
        except Exception:
            log.exception("engine failed to start")
            self.running = False
            self.cb.state("error:engine_failed")

    def _loop(self) -> None:
        from imaa.core.trackers import FaceTracker, HandTracker

        self.cb.state("starting")
        cam_cfg = self.settings.get("camera")
        camera = Camera(int(cam_cfg.get("index", 0)), int(cam_cfg.get("width", 640)), int(cam_cfg.get("height", 480)))
        if not camera.open():
            self.cb.state(f"error:{camera.error}")
            return
        hand_tracker: Optional[HandTracker] = None
        face_tracker: Optional[FaceTracker] = None
        self.running = True
        self.cb.state("running")
        self.hand.reset()
        self.head.recalibrate()
        self.air_mouse.reset()

        seq = 0
        frame_no = 0
        last_ts = {"hand": -1, "face": -1}
        last_seen = time.monotonic()
        last_preview = 0.0
        last_stats = 0.0
        fps_times: list[float] = []
        proc_avg = 0.0
        hand_lm = None
        face_obs = None
        dragging = False
        last_tick = time.monotonic()
        stats = EngineStats()

        try:
            while not self._stop.is_set():
                loop_start = time.monotonic()
                self._apply_settings()
                s = self.settings
                hand_on = bool(s.get("hand.enabled", True)) or bool(s.get("pointer.air_mouse"))
                head_on = bool(s.get("head.enabled", False)) or bool(s.get("pointer.head_pointer"))
                accurate = s.get("head.mode", "light") == "accurate" or bool(s.get("pointer.head_pointer"))

                seq, frame = camera.latest(seq)
                if frame is None:
                    if camera.error:
                        self.cb.state(f"error:{camera.error}")
                        break
                    continue

                t0 = time.perf_counter()
                if s.get("camera.mirror", True):
                    frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h_px, w_px = rgb.shape[:2]
                aspect = w_px / h_px

                # Lazily (re)create trackers so disabled features cost nothing.
                if hand_on and hand_tracker is None:
                    hand_tracker = HandTracker()
                if not hand_on and hand_tracker is not None:
                    hand_tracker.close()
                    hand_tracker = None
                    hand_lm = None
                    self.hand.reset()
                if self._restart_face.is_set() or (face_tracker is not None and face_tracker.accurate != accurate):
                    self._restart_face.clear()
                    if face_tracker is not None:
                        face_tracker.close()
                        face_tracker = None
                    self.head.recalibrate()
                if head_on and face_tracker is None:
                    face_tracker = FaceTracker(accurate=accurate)
                if not head_on and face_tracker is not None:
                    face_tracker.close()
                    face_tracker = None
                    face_obs = None
                    self.head.update(None, 0)

                now = time.monotonic()
                ts = int(now * 1000)
                run_hand = hand_tracker is not None and (face_tracker is None or frame_no % 2 == 0)
                run_face = face_tracker is not None and (hand_tracker is None or frame_no % 2 == 1)
                frame_no += 1
                events: list[GestureEvent] = []

                if run_hand:
                    ts_h = max(ts, last_ts["hand"] + 1)
                    last_ts["hand"] = ts_h
                    raw = hand_tracker.detect(rgb, ts_h)
                    hand_lm = [(x * aspect, y, z) for x, y, z in raw] if raw else None
                    if s.get("pointer.air_mouse"):
                        if hand_lm:
                            out = self.air_mouse.update(hand_lm, aspect, now)
                            self.cb.pointer_move(out.x, out.y, False)
                            if out.click:
                                self.cb.pointer_button(out.click)
                            if out.drag:
                                dragging = out.drag == "down"
                                self.cb.pointer_button("down" if dragging else "up")
                        else:
                            if dragging:
                                self.cb.pointer_button("up")
                                dragging = False
                            self.air_mouse.reset()
                        events += [e for e in self.hand.update(hand_lm, now) if e.gesture == "rock"]
                    elif s.get("hand.enabled", True):
                        events += self.hand.update(hand_lm, now)

                if run_face:
                    ts_f = max(ts, last_ts["face"] + 1)
                    last_ts["face"] = ts_f
                    face_obs = face_tracker.detect(rgb, ts_f, aspect)
                    head_events = self.head.update(face_obs, now)
                    if s.get("pointer.head_pointer"):
                        dt = min(0.2, now - last_tick)
                        if face_obs is not None and self.head.calibrated:
                            vx, vy = self.head_pointer.velocity(self.head.delta[0], self.head.delta[1])
                            if vx or vy:
                                self.cb.pointer_move(vx * dt, vy * dt, True)
                        for e in head_events:
                            if e.gesture == "mouth_open":
                                self.cb.pointer_button("left")
                            elif e.gesture == "brows_up":
                                self.cb.pointer_button("right")
                        head_events = [e for e in head_events if e.gesture in ("nod", "shake", "smile")]
                    if s.get("head.enabled", False) or s.get("pointer.head_pointer"):
                        events += head_events
                    last_tick = now

                for ev in events:
                    self.dispatcher.handle(ev)

                proc_ms = (time.perf_counter() - t0) * 1000
                proc_avg = proc_avg * 0.9 + proc_ms * 0.1 if proc_avg else proc_ms
                present = (hand_lm is not None and hand_tracker is not None) or (
                    face_obs is not None and face_tracker is not None
                )
                if present:
                    last_seen = now
                idle = now - last_seen > IDLE_AFTER_S

                # Preview (only while someone is looking at the window)
                if self.preview_enabled and now - last_preview >= 1 / PREVIEW_MAX_FPS:
                    last_preview = now
                    self.cb.preview(self._render_preview(rgb, hand_lm, aspect, face_tracker))

                fps_times.append(now)
                fps_times = [x for x in fps_times if now - x <= 1.0]
                if now - last_stats >= 0.5:
                    last_stats = now
                    stats.fps = float(len(fps_times))
                    stats.process_ms = proc_avg
                    stats.hand = hand_lm is not None
                    stats.face = face_obs is not None
                    stats.idle = idle
                    stats.low_light = float(frame[::16, ::16].mean()) < 45
                    stats.hand_pose = self.hand.live_pose if hand_lm is not None else None
                    stats.head_pose = self.head.live_pose if face_obs is not None else None
                    stats.calibrated = self.head.calibrated
                    self.cb.stats(stats)

                target = IDLE_FPS if idle else POWER_FPS.get(s.get("power_mode", "balanced"), 20)
                remaining = 1 / target - (time.monotonic() - loop_start)
                if remaining > 0:
                    self._stop.wait(remaining)
        except Exception:
            log.exception("engine crashed")
            self.cb.state("error:engine_failed")
        finally:
            if dragging:
                self.cb.pointer_button("up")
            camera.close()
            if hand_tracker is not None:
                hand_tracker.close()
            if face_tracker is not None:
                face_tracker.close()
            self.running = False
            self.hand.reset()
            if self._stop.is_set():  # otherwise an error state was already reported
                self.cb.state("stopped")

    # ------------------------------------------------------------------ preview
    def _render_preview(self, rgb: np.ndarray, hand_lm, aspect: float, face_tracker) -> np.ndarray:
        h, w = rgb.shape[:2]
        scale = PREVIEW_WIDTH / w
        img = cv2.resize(rgb, (PREVIEW_WIDTH, int(h * scale)), interpolation=cv2.INTER_AREA)
        if not self.settings.get("show_skeleton", True):
            return img
        ph, pw = img.shape[:2]
        if hand_lm:
            pts = [(int(x / aspect * pw), int(y * ph)) for x, y, _ in hand_lm]
            for a, b in HAND_CONNECTIONS:
                cv2.line(img, pts[a], pts[b], (255, 255, 255), 3, cv2.LINE_AA)
                cv2.line(img, pts[a], pts[b], (124, 92, 255), 1, cv2.LINE_AA)
            for i, p in enumerate(pts):
                cv2.circle(img, p, 4 if i in (4, 8, 12, 16, 20) else 3, (0, 201, 167), -1, cv2.LINE_AA)
        if face_tracker is not None and face_tracker.points:
            for x, y in face_tracker.points:
                cv2.circle(img, (int(x * pw), int(y * ph)), 3, (0, 201, 167), -1, cv2.LINE_AA)
        return img
