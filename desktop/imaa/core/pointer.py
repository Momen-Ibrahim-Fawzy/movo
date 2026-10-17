"""Cursor control: air mouse (index finger) and head pointer (head as a joystick)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


class OneEuroFilter:
    """Low-latency smoothing for noisy positions (Casiez et al., 2012)."""

    def __init__(self, min_cutoff: float = 1.2, beta: float = 0.02, d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x: Optional[float] = None
        self._dx = 0.0
        self._t: Optional[float] = None

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x: float, t: float) -> float:
        if self._x is None or self._t is None or t <= self._t:
            self._x, self._t = x, t
            return x
        dt = t - self._t
        dx = (x - self._x) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        self._dx = a_d * dx + (1 - a_d) * self._dx
        cutoff = self.min_cutoff + self.beta * abs(self._dx)
        a = self._alpha(cutoff, dt)
        self._x = a * x + (1 - a) * self._x
        self._t = t
        return self._x

    def reset(self) -> None:
        self._x = None
        self._t = None


@dataclass
class PointerOutput:
    x: float  # 0..1 of the virtual desktop
    y: float
    click: Optional[str] = None  # "left" | "right"
    drag: Optional[str] = None  # "down" | "up"


class AirMouse:
    """Maps the index fingertip inside an *active box* of the camera view to the whole screen.

    Pinching thumb + index = left click (hold to drag); thumb + middle = right click.
    """

    def __init__(self, box_margin: float = 0.18, smoothing: float = 0.5):
        self.margin = box_margin
        self.fx = OneEuroFilter(min_cutoff=0.6 + (1 - smoothing) * 2.5, beta=0.04)
        self.fy = OneEuroFilter(min_cutoff=0.6 + (1 - smoothing) * 2.5, beta=0.04)
        self._pinch = False
        self._pinch_t = 0.0
        self._dragging = False
        self._rpinch = False

    def reset(self) -> None:
        self.fx.reset()
        self.fy.reset()
        self._pinch = self._dragging = self._rpinch = False

    def update(self, lm, aspect: float, t: float) -> PointerOutput:
        from imaa.core.geometry import dist

        palm = max(dist(lm[0], lm[9]), 1e-6)
        # Track the index knuckle: it stays still while pinching, so clicks don't move the cursor.
        px = lm[5][0] / aspect
        py = lm[5][1]
        m = self.margin
        x = min(1.0, max(0.0, (px - m) / (1 - 2 * m)))
        y = min(1.0, max(0.0, (py - m) / (1 - 2 * m)))
        out = PointerOutput(self.fx(x, t), self.fy(y, t))

        ratio = dist(lm[4], lm[8]) / palm
        if not self._pinch and ratio < 0.28:
            self._pinch, self._pinch_t = True, t
        elif self._pinch:
            if ratio > 0.42:
                if self._dragging:
                    out.drag = "up"
                else:
                    out.click = "left"
                self._pinch = self._dragging = False
            elif not self._dragging and t - self._pinch_t > 0.45:
                self._dragging = True
                out.drag = "down"

        r_ratio = dist(lm[4], lm[12]) / palm
        if not self._pinch and not self._rpinch and r_ratio < 0.28:
            self._rpinch = True
            out.click = "right"
        elif self._rpinch and r_ratio > 0.42:
            self._rpinch = False
        return out


class HeadPointer:
    """Relative cursor movement: the further the head turns from neutral, the faster the cursor moves."""

    def __init__(self, speed: float = 1.0, deadzone: float = 4.0):
        self.speed = speed
        self.deadzone = deadzone

    def velocity(self, d_yaw: float, d_pitch: float) -> tuple[float, float]:
        """Pixels per second for the current head offset (degrees)."""

        def axis(v: float) -> float:
            e = abs(v) - self.deadzone
            if e <= 0:
                return 0.0
            return math.copysign((e**1.35) * 22.0 * self.speed, v)

        return axis(d_yaw), -axis(d_pitch)
