"""Hand gesture recognition from the 21 MediaPipe hand landmarks.

Pure Python, no third-party imports: the same logic is ported to the Android app and is unit-tested
with synthetic hands.

Landmark indices: 0 wrist · thumb 1-4 · index 5-8 · middle 9-12 · ring 13-16 · pinky 17-20.
Input landmarks must already be mirrored (what the user sees) and expressed in height units
(x multiplied by the aspect ratio), y pointing down.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Optional

from imaa.core.events import GestureEvent
from imaa.core.geometry import angle_at, angle_diff, direction, dist, mean_point

WRIST = 0
THUMB = (1, 2, 3, 4)
FINGERS = ((5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20))

# Static poses that fire actions after being held. Other labels (open_palm, point_up) are "modes".
STATIC_POSES = ("thumb_up", "thumb_down", "point_right", "point_left", "victory", "call", "fist", "rock", "three")
DEFAULT_HOLD_MS = {
    "thumb_up": 300,
    "thumb_down": 300,
    "point_right": 300,
    "point_left": 300,
    "victory": 550,
    "call": 600,
    "fist": 600,
    "rock": 1200,
    "three": 550,
}


@dataclass
class HandFeatures:
    palm: float
    extended: tuple[bool, bool, bool, bool, bool]  # thumb, index, middle, ring, pinky
    thumb_dir: float
    index_dir: float
    pinch_ratio: float
    index_reach: float  # wrist→index tip / palm size (curled ≈ 0.9, pinch ≈ 1.4, pointing ≈ 1.9)
    center: tuple[float, float]
    index_tip: tuple[float, float]
    pinch_point: tuple[float, float]


def analyze(lm: Sequence[Sequence[float]]) -> HandFeatures:
    wrist = lm[WRIST]
    palm = max(dist(wrist, lm[9]), 1e-6)

    extended = [False] * 5
    for i, (mcp, pip, _dip, tip) in enumerate(FINGERS):
        far = dist(wrist, lm[tip]) > dist(wrist, lm[pip]) * 1.2
        straight = angle_at(lm[mcp], lm[pip], lm[tip]) > 130
        extended[i + 1] = far and straight

    t_mcp, t_ip, t_tip = lm[2], lm[3], lm[4]
    thumb_straight = angle_at(t_mcp, t_ip, t_tip) > 140
    thumb_away = dist(t_tip, lm[5]) > 0.6 * palm and dist(t_tip, lm[17]) > dist(t_mcp, lm[17]) * 1.05
    extended[0] = thumb_straight and thumb_away

    center = mean_point([lm[0], lm[5], lm[9], lm[13], lm[17]])
    return HandFeatures(
        palm=palm,
        extended=tuple(extended),  # type: ignore[arg-type]
        thumb_dir=direction(lm[2], lm[4]),
        index_dir=direction(lm[5], lm[8]),
        pinch_ratio=dist(lm[4], lm[8]) / palm,
        index_reach=dist(wrist, lm[8]) / palm,
        center=center,
        index_tip=(lm[8][0], lm[8][1]),
        pinch_point=mean_point([lm[4], lm[8]]),
    )


def classify(f: HandFeatures, axis_tolerance: float = 35.0) -> Optional[str]:
    """Return the static pose label, or None when the hand is in no clear pose."""
    thumb, index, middle, ring, pinky = f.extended
    four = (index, middle, ring, pinky)

    if four == (False, False, False, False):
        if thumb:
            if angle_diff(f.thumb_dir, 90) <= axis_tolerance + 5:
                return "thumb_up"
            if angle_diff(f.thumb_dir, -90) <= axis_tolerance + 5:
                return "thumb_down"
            return None
        return "fist"
    if four == (True, False, False, False):
        if angle_diff(f.index_dir, 0) <= axis_tolerance:
            return "point_right"
        if angle_diff(f.index_dir, 180) <= axis_tolerance:
            return "point_left"
        if angle_diff(f.index_dir, 90) <= axis_tolerance:
            return "point_up"
        return None
    if four == (True, True, False, False):
        return "victory"
    if four == (True, True, True, False):
        return "three"
    if four == (True, False, False, True):
        return "rock"
    if four == (False, False, False, True) and thumb:
        return "call"
    if four == (True, True, True, True):
        return "open_palm"
    return None


@dataclass
class HandSettings:
    hold_scale: float = 1.0  # multiplies every hold time (0.5 = twice as fast)
    repeat_ms: int = 280  # repeat interval for held poses
    cooldown_ms: int = 250  # minimum gap between two different "start" events
    swipe_enabled: bool = True
    swipe_distance: float = 0.30  # in frame-height units
    swipe_time: float = 0.45  # seconds
    motion_guard: float = 1.1  # palm speed (height units / s) above which static poses are ignored
    pinch_enter: float = 0.28
    pinch_exit: float = 0.42
    pinch_tap_ms: int = 450
    pinch_drag_delay_ms: int = 350
    pinch_drag_step: float = 0.07
    joystick_deadzone: float = 0.035
    joystick_range: float = 0.15
    joystick_interval_ms: int = 90
    hold_ms: dict = field(default_factory=lambda: dict(DEFAULT_HOLD_MS))


class HandRecognizer:
    """Turns a stream of landmark frames into :class:`GestureEvent` objects."""

    def __init__(self, settings: Optional[HandSettings] = None):
        self.s = settings or HandSettings()
        self.live_pose: Optional[str] = None  # stable pose, for the UI / practice mode
        self.reset()

    # ------------------------------------------------------------------ state
    def reset(self) -> None:
        self._raw: Optional[str] = None
        self._raw_count = 0
        self._stable: Optional[str] = None
        self._stable_since = 0.0
        self._fired: Optional[str] = None
        self._last_repeat = 0.0
        self._last_start = -10.0
        self._history: deque = deque()
        self._swipe_block_until = 0.0
        self._pinching = False
        self._pinch_start = 0.0
        self._pinch_origin = (0.0, 0.0)
        self._dragging = False
        self._drag_ref = 0.0
        self._drag_dir: Optional[str] = None
        self._joy_active = False
        self._joy_anchor = 0.0
        self._joy_last = 0.0
        self._joy_dir: Optional[str] = None
        self.live_pose = None

    # ------------------------------------------------------------------ main
    def update(self, lm: Optional[Sequence[Sequence[float]]], t: float) -> list[GestureEvent]:
        if lm is None:
            self.reset()
            return []
        f = analyze(lm)
        events: list[GestureEvent] = []

        label = classify(f)
        self._history.append((t, f.center[0], f.center[1], label == "open_palm"))
        while self._history and t - self._history[0][0] > max(self.s.swipe_time, 0.2):
            self._history.popleft()
        speed = self._speed(t)
        self._update_stable(label, t)

        if self.s.swipe_enabled:
            events += self._detect_swipe(t)

        pinch_events, pinch_active = self._update_pinch(f, t)
        events += pinch_events
        if pinch_active:
            self.live_pose = "pinch"
            self._joy_active = False
            return events

        events += self._update_joystick(f, t)
        if speed <= self.s.motion_guard:
            events += self._update_static(t)
        else:
            self._stable_since = t  # moving: restart the hold timer
        return events

    # ------------------------------------------------------------------ helpers
    def _speed(self, t: float) -> float:
        recent = [h for h in self._history if t - h[0] <= 0.15]
        if len(recent) < 2:
            return 0.0
        dt = recent[-1][0] - recent[0][0]
        if dt <= 0:
            return 0.0
        return dist(recent[0][1:3], recent[-1][1:3]) / dt

    def _update_stable(self, label: Optional[str], t: float) -> None:
        if label == self._raw:
            self._raw_count += 1
        else:
            self._raw = label
            self._raw_count = 1
        if self._raw_count >= 2 and label != self._stable:
            self._stable = label
            self._stable_since = t
            if label != self._fired:
                self._fired = None
        self.live_pose = self._stable

    def _start(self, gesture: str, t: float, magnitude: float = 1.0) -> Optional[GestureEvent]:
        if t - self._last_start < self.s.cooldown_ms / 1000:
            return None
        self._last_start = t
        return GestureEvent(gesture, "start", magnitude, "hand")

    def _detect_swipe(self, t: float) -> list[GestureEvent]:
        if t < self._swipe_block_until or len(self._history) < 3:
            return []
        h = list(self._history)
        open_ratio = sum(1 for x in h if x[3]) / len(h)
        if open_ratio < 0.6:
            return []
        dx = h[-1][1] - h[0][1]
        dy = h[-1][2] - h[0][2]
        if abs(dx) >= self.s.swipe_distance and abs(dy) < abs(dx) * 0.6:
            self._swipe_block_until = t + 0.8
            self._history.clear()
            self._stable_since = t
            ev = self._start("swipe_right" if dx > 0 else "swipe_left", t)
            return [ev] if ev else []
        return []

    def _update_pinch(self, f: HandFeatures, t: float) -> tuple[list[GestureEvent], bool]:
        s = self.s
        events: list[GestureEvent] = []
        can_pinch = f.index_reach > 1.15 and self._stable not in ("fist", "thumb_up", "thumb_down")
        if not self._pinching:
            if can_pinch and f.pinch_ratio < s.pinch_enter:
                self._pinching = True
                self._pinch_start = t
                self._pinch_origin = f.pinch_point
                self._dragging = False
                self._drag_dir = None
            return events, self._pinching

        if f.pinch_ratio > s.pinch_exit:
            moved = dist(f.pinch_point, self._pinch_origin)
            if not self._dragging and (t - self._pinch_start) * 1000 <= s.pinch_tap_ms and moved < 0.08:
                ev = self._start("pinch", t)
                if ev:
                    events.append(ev)
            self._pinching = False
            self._dragging = False
            return events, False

        if not self._dragging and (t - self._pinch_start) * 1000 >= s.pinch_drag_delay_ms:
            self._dragging = True
            self._drag_ref = f.pinch_point[1]
        if self._dragging:
            delta = self._drag_ref - f.pinch_point[1]  # up is positive
            while abs(delta) >= s.pinch_drag_step:
                d = "up" if delta > 0 else "down"
                phase = "repeat" if self._drag_dir == d else "start"
                self._drag_dir = d
                events.append(GestureEvent(f"pinch_drag_{d}", phase, 1.0, "hand"))
                self._drag_ref -= s.pinch_drag_step if delta > 0 else -s.pinch_drag_step
                delta = self._drag_ref - f.pinch_point[1]
        return events, True

    def _update_joystick(self, f: HandFeatures, t: float) -> list[GestureEvent]:
        s = self.s
        if self._stable != "point_up":
            self._joy_active = False
            self._joy_dir = None
            return []
        if not self._joy_active:
            if (t - self._stable_since) * 1000 >= 220 * s.hold_scale:
                self._joy_active = True
                self._joy_anchor = f.index_tip[1]
                self._joy_last = t
            return []
        offset = self._joy_anchor - f.index_tip[1]  # up is positive
        excess = abs(offset) - s.joystick_deadzone
        if excess <= 0 or (t - self._joy_last) * 1000 < s.joystick_interval_ms:
            if excess <= 0:
                self._joy_dir = None
            return []
        self._joy_last = t
        d = "up" if offset > 0 else "down"
        magnitude = 0.25 + 0.75 * min(1.0, excess / s.joystick_range)
        phase = "repeat" if self._joy_dir == d else "start"
        self._joy_dir = d
        return [GestureEvent(f"index_up_move_{d}", phase, magnitude, "hand")]

    def _update_static(self, t: float) -> list[GestureEvent]:
        label = self._stable
        if label not in STATIC_POSES:
            return []
        hold = self.s.hold_ms.get(label, 400) * self.s.hold_scale / 1000
        held = t - self._stable_since
        if held < hold:
            return []
        if self._fired != label:
            ev = self._start(label, t)
            if ev is None:
                return []
            self._fired = label
            self._last_repeat = t
            return [ev]
        if (t - self._last_repeat) * 1000 >= self.s.repeat_ms:
            self._last_repeat = t
            return [GestureEvent(label, "repeat", 1.0, "hand")]
        return []
