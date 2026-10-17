"""Eye gestures: winks, double/long blinks, eyes closed, and held glances.

Works with or without glasses by (1) fusing a learned signal (MediaPipe blink blendshapes) with a geometric one
(eye aspect ratio), (2) measuring everything relative to the person's own calibrated levels, and (3) smoothing
enough that a single glare frame can never trigger anything. See docs/EYE_GESTURES.md.

All left/right values are from the **user's** point of view.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from statistics import median
from typing import Optional

from imaa.core.events import GestureEvent


@dataclass
class EyeFeatures:
    ear_left: float
    ear_right: float
    blink_left: Optional[float] = None  # learned closure score 0..1 (None when unavailable, e.g. iOS Vision)
    blink_right: Optional[float] = None
    gaze_x: float = 0.0  # iris offset from the eye centre, + = towards the user's right (≈ ±0.15 at the extremes)
    gaze_y: float = 0.0  # + = up
    look_up: float = 0.0  # learned look scores 0..1
    look_down: float = 0.0
    smile: float = 0.0


@dataclass
class EyeSettings:
    sensitivity: float = 1.0  # > 1 = easier to trigger
    hold_scale: float = 1.0
    glasses: bool = False
    close_on: float = 0.6
    close_off: float = 0.35
    wink_hold_s: float = 0.35
    short_blink: tuple = (0.06, 0.45)
    long_blink: tuple = (0.6, 1.5)
    closed_hold_s: float = 2.0
    double_gap_s: float = 0.8
    glance_hold_s: float = 0.6
    glance_repeat_s: float = 0.4
    glance_x: float = 0.10  # iris offset that counts as a deliberate horizontal glance
    glance_y: float = 0.08
    head_limit_deg: float = 20.0
    head_still_deg: float = 8.0  # glances need a still head (the eyes counter-rotate when the head turns)
    calibration: dict = field(default_factory=dict)


class _Median:
    def __init__(self, n: int):
        self.q: deque = deque(maxlen=n)

    def __call__(self, v: float) -> float:
        self.q.append(v)
        return median(self.q)


class EyeRecognizer:
    def __init__(self, settings: Optional[EyeSettings] = None):
        self.s = settings or EyeSettings()
        self.live_pose: Optional[str] = None
        self.openness = (1.0, 1.0)  # for the live meter (1 = open, 0 = closed)
        self.gaze = (0.0, 0.0)
        self._capture: Optional[str] = None
        self._captured: dict[str, list] = {}
        self._mute_for = 0.0
        self._mute_until = -1.0
        self._configure_filters()
        self.reset()

    # ------------------------------------------------------------------ setup
    def _configure_filters(self) -> None:
        n = 5 if self.s.glasses else 3
        self._f = {k: _Median(n) for k in ("ear_l", "ear_r", "bl", "br", "gx", "gy", "lu", "ld")}
        self._glasses = self.s.glasses

    def reset(self) -> None:
        self._closed = [False, False]
        self._both_since: Optional[float] = None
        self._closed_fired = False
        self._last_short: Optional[float] = None
        self._wink_side: Optional[int] = None
        self._wink_since = 0.0
        self._wink_fired = False
        self._glance: Optional[str] = None
        self._glance_since = 0.0
        self._glance_fired = False
        self._glance_last = 0.0
        self._ear_hist: deque = deque(maxlen=400)  # ~20 s at 20 fps, for auto-calibration
        self._gaze_center = [0.0, 0.0]
        self._gaze_samples = 0
        self.live_pose = None

    @property
    def calibrated(self) -> bool:
        return bool(self.s.calibration)

    def load_calibration(self, data: dict) -> None:
        self.s.calibration = dict(data or {})
        if self.s.calibration:
            self._gaze_center = [self.s.calibration.get("gaze_x", 0.0), self.s.calibration.get("gaze_y", 0.0)]
            self._gaze_samples = 999

    # ------------------------------------------------------------------ calibration capture
    def begin_capture(self, kind: str) -> None:
        """kind = "open" (eyes open, looking at the screen centre) or "closed"."""
        self._captured[kind] = []
        self._capture = kind

    def end_capture(self) -> None:
        self._capture = None
        self._mute_for = 1.5  # the user is opening their eyes again — don't read that as a blink

    def finish_calibration(self) -> Optional[dict]:
        """Turn captured samples into personal levels. Returns None if the eyes were not seen clearly."""
        op, cl = self._captured.get("open", []), self._captured.get("closed", [])
        self._captured = {}
        if len(op) < 5 or len(cl) < 5:
            return None

        def med(rows, i):
            vals = [r[i] for r in rows if r[i] is not None]
            return median(vals) if vals else None

        data = {
            "open_ear_l": med(op, 0),
            "open_ear_r": med(op, 1),
            "closed_ear_l": med(cl, 0),
            "closed_ear_r": med(cl, 1),
            "open_bs": med(op, 2),
            "closed_bs": med(cl, 2),
            "gaze_x": med(op, 3),
            "gaze_y": med(op, 4),
        }
        if min(data["open_ear_l"] - data["closed_ear_l"], data["open_ear_r"] - data["closed_ear_r"]) < 0.03:
            return None
        self.load_calibration(data)
        return data

    # ------------------------------------------------------------------ main
    def update(
        self,
        feat: Optional[EyeFeatures],
        t: float,
        head_delta: tuple[float, float, float] = (0.0, 0.0, 0.0),
        head_busy: bool = False,
    ) -> list[GestureEvent]:
        if self._glasses != self.s.glasses:
            self._configure_filters()
        if feat is None:
            self.reset()
            return []
        f = self._f
        ear = (f["ear_l"](feat.ear_left), f["ear_r"](feat.ear_right))
        bs = (
            f["bl"](feat.blink_left) if feat.blink_left is not None else None,
            f["br"](feat.blink_right) if feat.blink_right is not None else None,
        )
        gx, gy = f["gx"](feat.gaze_x), f["gy"](feat.gaze_y)
        look_up, look_down = f["lu"](feat.look_up), f["ld"](feat.look_down)

        if self._mute_for:
            self._mute_until = t + self._mute_for
            self._mute_for = 0.0
        if self._capture is not None:
            bs_mean = None if bs[0] is None or bs[1] is None else (bs[0] + bs[1]) / 2
            self._captured[self._capture].append((ear[0], ear[1], bs_mean, gx, gy))
            self._both_since = None  # never trigger gestures while the user is following calibration steps
            self._wink_side = None
            self._glance = None
            return []

        dy, dp, _dr = head_delta
        frontal = abs(dy) < self.s.head_limit_deg and abs(dp) < self.s.head_limit_deg
        if frontal:
            self._ear_hist.append(ear)
        closure = [self._closure(i, ear[i], bs[i], look_down) for i in (0, 1)]
        self.openness = (1 - closure[0], 1 - closure[1])

        if not frontal or head_busy or t < self._mute_until:
            self._both_since = None
            self._wink_side = None
            self._glance = None
            self.live_pose = None
            return []

        k = self.s.sensitivity
        on, off = min(0.85, self.s.close_on / k), self.s.close_off
        for i in (0, 1):
            if not self._closed[i] and closure[i] >= on:
                self._closed[i] = True
            elif self._closed[i] and closure[i] <= off:
                self._closed[i] = False

        events: list[GestureEvent] = []
        events += self._blinks(t)
        events += self._winks(t, closure, feat.smile)
        both_open = not self._closed[0] and not self._closed[1]
        if both_open:
            self._update_gaze_center(gx, gy, dy, dp)
        events += self._glances(t, gx, gy, look_up, look_down, both_open, dy, dp)
        return events

    # ------------------------------------------------------------------ signals
    def _open_level(self, i: int) -> float:
        cal = self.s.calibration
        if cal:
            return cal["open_ear_l" if i == 0 else "open_ear_r"]
        if len(self._ear_hist) >= 15:
            vals = sorted(e[i] for e in self._ear_hist)
            return vals[int(len(vals) * 0.9) - 1]
        return max(e[i] for e in self._ear_hist) if self._ear_hist else 0.3

    def _closure(self, i: int, ear: float, bs: Optional[float], look_down: float) -> float:
        open_ear = max(self._open_level(i), 1e-3)
        cal = self.s.calibration
        closed_ear = cal.get("closed_ear_l" if i == 0 else "closed_ear_r") if cal else None
        span = (open_ear - closed_ear) if closed_ear is not None else 0.6 * open_ear
        geo = max(0.0, min(1.0, (open_ear - ear) / max(span, 1e-3)))
        if bs is None:
            c = geo
        else:
            if cal and cal.get("open_bs") is not None and cal.get("closed_bs") is not None:
                lo, hi = cal["open_bs"], cal["closed_bs"]
                bs = max(0.0, min(1.0, (bs - lo) / max(hi - lo, 0.05)))
            w = 0.6 if self.s.glasses else 0.5
            c = w * bs + (1 - w) * geo
            # When the lids are clearly shut and the learned score agrees at least partly, trust it
            # (the learned score can stay low behind thick frames or glare).
            if geo >= 0.9 and bs >= 0.3:
                c = max(c, 0.75)
        return max(0.0, min(1.0, c - 0.35 * look_down))

    # ------------------------------------------------------------------ blinks
    def _blinks(self, t: float) -> list[GestureEvent]:
        s = self.s
        both = self._closed[0] and self._closed[1]
        if both:
            if self._both_since is None:
                self._both_since = t
            elif not self._closed_fired and t - self._both_since >= s.closed_hold_s * s.hold_scale:
                self._closed_fired = True
                self._last_short = None
                self.live_pose = "eyes_closed"
                return [GestureEvent("eyes_closed", "start", 1.0, "eye")]
            return []
        if self._both_since is None:
            return []
        d = t - self._both_since
        self._both_since = None
        if self._closed_fired:
            self._closed_fired = False
            return []
        if s.long_blink[0] * s.hold_scale <= d <= s.long_blink[1] * max(1.0, s.hold_scale):
            self._last_short = None
            self.live_pose = "blink_long"
            return [GestureEvent("blink_long", "start", 1.0, "eye")]
        if s.short_blink[0] <= d <= s.short_blink[1]:
            if self._last_short is not None and t - self._last_short <= s.double_gap_s:
                self._last_short = None
                self.live_pose = "blink_double"
                return [GestureEvent("blink_double", "start", 1.0, "eye")]
            self._last_short = t
        return []

    def _winks(self, t: float, closure: list[float], smile: float) -> list[GestureEvent]:
        s = self.s
        side = None
        if self._closed[0] != self._closed[1]:
            i = 0 if self._closed[0] else 1
            if closure[1 - i] < 0.3 and smile < 0.5:
                side = i
        if side != self._wink_side:
            self._wink_side = side
            self._wink_since = t
            if side is None:
                self._wink_fired = False
            return []
        if side is None or self._wink_fired:
            return []
        if t - self._wink_since >= s.wink_hold_s * s.hold_scale:
            self._wink_fired = True
            name = "wink_left" if side == 0 else "wink_right"
            self.live_pose = name
            return [GestureEvent(name, "start", 1.0, "eye")]
        return []

    # ------------------------------------------------------------------ glances
    def _update_gaze_center(self, gx: float, gy: float, dy: float, dp: float) -> None:
        if self.calibrated or abs(dy) > 5 or abs(dp) > 5:
            return
        if self._gaze_samples < 15:
            n = self._gaze_samples + 1
            self._gaze_center = [
                self._gaze_center[0] + (gx - self._gaze_center[0]) / n,
                self._gaze_center[1] + (gy - self._gaze_center[1]) / n,
            ]
            self._gaze_samples = n
        elif abs(gx - self._gaze_center[0]) < self.s.glance_x / 2 and abs(gy - self._gaze_center[1]) < self.s.glance_y / 2:
            a = 0.01
            self._gaze_center = [self._gaze_center[0] * (1 - a) + gx * a, self._gaze_center[1] * (1 - a) + gy * a]

    def _glances(self, t, gx, gy, look_up, look_down, both_open, dy, dp) -> list[GestureEvent]:
        s, k = self.s, self.s.sensitivity
        hx = (gx - self._gaze_center[0]) / (s.glance_x / k)
        vy_iris = (gy - self._gaze_center[1]) / (s.glance_y / k)
        vy_learned = (look_up - look_down) / (0.5 / k)
        vy = (vy_iris + vy_learned) / 2 if (look_up or look_down) else vy_iris
        self.gaze = (hx, vy)
        label = None
        still = abs(dy) < s.head_still_deg and abs(dp) < s.head_still_deg
        if both_open and still and self._gaze_samples >= 15:
            cands = [(hx, "eye_look_right"), (-hx, "eye_look_left"), (vy, "eye_look_up"), (-vy, "eye_look_down")]
            best = max(cands)
            if best[0] >= 1.0:
                label = best[1]
        if label != self._glance:
            self._glance = label
            self._glance_since = t
            self._glance_fired = False
            if label is None and self.live_pose and self.live_pose.startswith("eye_look"):
                self.live_pose = None
            return []
        if label is None or t - self._glance_since < s.glance_hold_s * s.hold_scale:
            return []
        self.live_pose = label
        if not self._glance_fired:
            self._glance_fired = True
            self._glance_last = t
            return [GestureEvent(label, "start", 1.0, "eye")]
        if t - self._glance_last >= s.glance_repeat_s:
            self._glance_last = t
            return [GestureEvent(label, "repeat", 1.0, "eye")]
        return []
