"""Head gesture recognition.

Both face engines (BlazeFace keypoints in *Light* mode, Face Landmarker in *Accurate* mode) are reduced to
the same observation: the two eye centres and the nose tip, plus optional expression scores.
Angles are measured relative to the person's own neutral pose, so camera height, posture and glasses
don't matter.

Coordinates: mirrored image, height units, y down. Positive yaw = turned to the user's right,
positive pitch = looking up, positive roll = head tilted to the user's right.
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from statistics import median
from typing import Optional

from imaa.core.events import GestureEvent


@dataclass
class FaceObservation:
    yaw: float
    pitch: float
    roll: float
    expressions: Optional[dict] = None  # mouth_open / smile / brows_up in 0..1 (Accurate mode only)


def pose_from_points(eye_a: Sequence[float], eye_b: Sequence[float], nose: Sequence[float]) -> tuple[float, float, float]:
    """Raw (yaw, pitch, roll) proxies in degrees from two eye centres and the nose tip."""
    left, right = (eye_a, eye_b) if eye_a[0] <= eye_b[0] else (eye_b, eye_a)
    ex, ey = right[0] - left[0], right[1] - left[1]
    eye_dist = max(math.hypot(ex, ey), 1e-6)
    # Image y points down, so a head tilted to the user's right (mirror: screen right) lowers the right eye.
    roll = math.degrees(math.atan2(ey, ex))
    mid = ((left[0] + right[0]) / 2, (left[1] + right[1]) / 2)
    # Express the nose offset in the face's own (de-rotated) frame.
    r = math.atan2(ey, ex)
    nx, ny = nose[0] - mid[0], nose[1] - mid[1]
    lx = (nx * math.cos(-r) - ny * math.sin(-r)) / eye_dist
    ly = (nx * math.sin(-r) + ny * math.cos(-r)) / eye_dist
    # The nose tip sits ~0.5 eye-distances in front of the eye plane and ~0.7 below it.
    yaw = math.degrees(math.atan2(lx, 0.5))
    pitch = -ly * 119.0  # linearised: d(ly)/d(pitch) ≈ 0.48 per radian
    return yaw, pitch, roll


@dataclass
class HeadSettings:
    sensitivity: float = 1.0  # > 1 = smaller movements are enough
    hold_scale: float = 1.0
    turn_deg: float = 20.0
    tilt_deg: float = 15.0
    look_up_deg: float = 12.0
    look_down_deg: float = 12.0
    hold_ms: int = 450
    repeat_ms: int = 380
    nod_deg: float = 9.0
    shake_deg: float = 9.0
    expression_threshold: float = 0.5
    expression_hold_ms: dict = field(default_factory=lambda: {"mouth_open": 350, "smile": 450, "brows_up": 400})
    calibration_frames: int = 12


class HeadRecognizer:
    def __init__(self, settings: Optional[HeadSettings] = None):
        self.s = settings or HeadSettings()
        self.live_pose: Optional[str] = None
        self.delta = (0.0, 0.0, 0.0)
        self.recalibrate()

    def recalibrate(self) -> None:
        self._samples: list[tuple[float, float, float]] = []
        self.baseline: Optional[tuple[float, float, float]] = None
        self._hold_label: Optional[str] = None
        self._hold_since = 0.0
        self._fired: Optional[str] = None
        self._last_repeat = 0.0
        self._pitch_hist: deque = deque()
        self._yaw_hist: deque = deque()
        self._event_block_until = 0.0
        self._expr_since: dict[str, Optional[float]] = {}
        self._expr_fired: set[str] = set()

    @property
    def calibrated(self) -> bool:
        return self.baseline is not None

    def update(self, obs: Optional[FaceObservation], t: float) -> list[GestureEvent]:
        if obs is None:
            self._hold_label = None
            self._fired = None
            self.live_pose = None
            self._pitch_hist.clear()
            self._yaw_hist.clear()
            return []
        raw = (obs.yaw, obs.pitch, obs.roll)
        if self.baseline is None:
            self._samples.append(raw)
            if len(self._samples) >= self.s.calibration_frames:
                self.baseline = tuple(median(v[i] for v in self._samples) for i in range(3))  # type: ignore[assignment]
            return []

        dy, dp, dr = (raw[i] - self.baseline[i] for i in range(3))
        self.delta = (dy, dp, dr)
        # Slowly follow posture drift while the head is near neutral.
        if abs(dy) < 5 and abs(dp) < 5 and abs(dr) < 5:
            a = 0.01
            self.baseline = tuple(self.baseline[i] * (1 - a) + raw[i] * a for i in range(3))  # type: ignore[assignment]

        events: list[GestureEvent] = []
        events += self._dynamic(dy, dp, t)
        events += self._holds(dy, dp, dr, t)
        if obs.expressions:
            events += self._expressions(obs.expressions, t)
        return events

    # ------------------------------------------------------------------ nod / shake
    def _dynamic(self, dy: float, dp: float, t: float) -> list[GestureEvent]:
        k = self.s.sensitivity
        self._pitch_hist.append((t, dp, dy))
        self._yaw_hist.append((t, dy, dp))
        while self._pitch_hist and t - self._pitch_hist[0][0] > 1.0:
            self._pitch_hist.popleft()
        while self._yaw_hist and t - self._yaw_hist[0][0] > 1.4:
            self._yaw_hist.popleft()
        if t < self._event_block_until:
            return []

        # Nod: pitch dips below -nod and comes back quickly, without much yaw.
        nod = self.s.nod_deg / k
        below = [h for h in self._pitch_hist if h[1] < -nod]
        if below and dp > -nod / 3:
            span = below[-1][0] - below[0][0]
            start = self._pitch_hist[0]
            if span < 0.5 and start[1] > -nod / 2 and max(abs(h[2]) for h in self._pitch_hist) < 12:
                return self._fire_event("nod", t)

        # Shake: three alternating yaw excursions within the window.
        shake = self.s.shake_deg / k
        signs: list[int] = []
        for _, y, p in self._yaw_hist:
            if abs(p) > 14:
                signs = []
                break
            s = 1 if y > shake else -1 if y < -shake else 0
            if s and (not signs or signs[-1] != s):
                signs.append(s)
        if len(signs) >= 3:
            return self._fire_event("shake", t)
        return []

    def _fire_event(self, name: str, t: float) -> list[GestureEvent]:
        self._event_block_until = t + 1.0
        self._pitch_hist.clear()
        self._yaw_hist.clear()
        self._hold_label = None
        self.live_pose = name
        return [GestureEvent(name, "start", 1.0, "head")]

    # ------------------------------------------------------------------ holds
    def _holds(self, dy: float, dp: float, dr: float, t: float) -> list[GestureEvent]:
        s, k = self.s, self.s.sensitivity
        candidates = []
        for label, value, thr in (
            ("turn_right", dy, s.turn_deg),
            ("turn_left", -dy, s.turn_deg),
            ("look_up", dp, s.look_up_deg),
            ("look_down", -dp, s.look_down_deg),
            ("tilt_right", dr, s.tilt_deg),
            ("tilt_left", -dr, s.tilt_deg),
        ):
            thr /= k
            if value > thr:
                candidates.append((value / thr, label))
        label = max(candidates)[1] if candidates else None

        if label != self._hold_label:
            self._hold_label = label
            self._hold_since = t
            if label is None:
                self._fired = None
        self.live_pose = label if label else (self.live_pose if t < self._event_block_until else None)
        if label is None or t < self._event_block_until:
            return []
        if (t - self._hold_since) * 1000 < s.hold_ms * s.hold_scale:
            return []
        if self._fired != label:
            self._fired = label
            self._last_repeat = t
            return [GestureEvent(label, "start", 1.0, "head")]
        if (t - self._last_repeat) * 1000 >= s.repeat_ms:
            self._last_repeat = t
            return [GestureEvent(label, "repeat", 1.0, "head")]
        return []

    # ------------------------------------------------------------------ expressions
    def _expressions(self, expr: dict, t: float) -> list[GestureEvent]:
        events = []
        on = self.s.expression_threshold / self.s.sensitivity
        off = on * 0.6
        for name, hold_ms in self.s.expression_hold_ms.items():
            v = expr.get(name, 0.0)
            since = self._expr_since.get(name)
            if v >= on:
                if since is None:
                    self._expr_since[name] = t
                elif name not in self._expr_fired and (t - since) * 1000 >= hold_ms * self.s.hold_scale:
                    self._expr_fired.add(name)
                    self.live_pose = name
                    events.append(GestureEvent(name, "start", 1.0, "head"))
            elif v < off:
                self._expr_since[name] = None
                self._expr_fired.discard(name)
        return events
