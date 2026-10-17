"""Builds plausible 21-point hands for tests (height units, y down, mirrored view)."""

from __future__ import annotations

import math

MCPS = {1: (-0.045, -0.17), 2: (0.0, -0.18), 3: (0.04, -0.17), 4: (0.075, -0.15)}


def _finger(mcp, extended: bool):
    x, y = mcp
    if extended:
        return [(x, y), (x, y - 0.06), (x, y - 0.10), (x, y - 0.135)]
    return [(x, y), (x, y - 0.045), (x + 0.005, y - 0.015), (x + 0.005, y + 0.02)]


def _thumb(extended: bool):
    if extended:  # out to the side, away from the fingers
        return [(-0.03, -0.03), (-0.07, -0.07), (-0.11, -0.085), (-0.15, -0.10)]
    return [(-0.03, -0.03), (-0.06, -0.07), (-0.05, -0.11), (-0.01, -0.13)]  # tucked over the fingers


def hand(thumb=False, index=False, middle=False, ring=False, pinky=False, rotate=0.0, at=(0.65, 0.6), scale=1.0):
    """Upright hand (fingers up) rotated counter-clockwise by ``rotate`` degrees around the wrist."""
    pts = [(0.0, 0.0)] + _thumb(thumb)
    for i, ext in zip((1, 2, 3, 4), (index, middle, ring, pinky), strict=True):
        pts += _finger(MCPS[i], ext)
    return _place(pts, rotate, at, scale)


def pinch_hand(closed=True, at=(0.65, 0.6)):
    thumb_tip = (-0.112, -0.20) if closed else (-0.16, -0.12)
    pts = [(0.0, 0.0), (-0.03, -0.03), (-0.07, -0.07), (-0.10, -0.13), thumb_tip]
    pts += [(-0.045, -0.17), (-0.07, -0.21), (-0.09, -0.22), (-0.11, -0.21)]
    for i in (2, 3, 4):
        pts += _finger(MCPS[i], True)
    return _place(pts, 0.0, at, 1.0)


def _place(pts, rotate, at, scale):
    r = math.radians(rotate)
    out = []
    for x, y in pts:
        # y is down, so a counter-clockwise rotation on screen uses -r for the y component.
        rx = x * math.cos(r) + y * math.sin(r)
        ry = -x * math.sin(r) + y * math.cos(r)
        out.append((at[0] + rx * scale, at[1] + ry * scale, 0.0))
    return out


POSES = {
    "open_palm": dict(thumb=True, index=True, middle=True, ring=True, pinky=True),
    "fist": dict(),
    "victory": dict(index=True, middle=True),
    "three": dict(index=True, middle=True, ring=True),
    "rock": dict(index=True, pinky=True),
    "call": dict(thumb=True, pinky=True),
    "point_up": dict(index=True),
    # Thumb sticks out to the left (-x); rotating by -90° turns it upward.
    "thumb_up": dict(thumb=True, rotate=-90),
    "thumb_down": dict(thumb=True, rotate=90),
    # Index points up; rotating by -90° makes it point right, +90° left.
    "point_right": dict(index=True, rotate=-90),
    "point_left": dict(index=True, rotate=90),
}


def face_points(yaw=0.0, pitch=0.0, roll=0.0, at=(0.65, 0.5), eye=0.12):
    """Two eye centres and a nose tip for a head with the given pose (degrees)."""
    y_r, p_r, r_r = (math.radians(v) for v in (yaw, pitch, roll))
    # 3-D model in eye-distance units: eyes at x=±0.5, nose 0.7 below and 0.5 in front.
    model = [(-0.5, 0.0, 0.0), (0.5, 0.0, 0.0), (0.0, 0.7, 0.5)]
    out = []
    for x, y, z in model:
        # pitch (looking up lifts the nose: rotate about x)
        y, z = y * math.cos(p_r) - z * math.sin(p_r), y * math.sin(p_r) + z * math.cos(p_r)
        # yaw (turning right moves the nose to screen right in the mirror)
        x, z = x * math.cos(y_r) + z * math.sin(y_r), -x * math.sin(y_r) + z * math.cos(y_r)
        # roll (tilting right lowers the right eye; y is down)
        x, y = x * math.cos(r_r) - y * math.sin(r_r), x * math.sin(r_r) + y * math.cos(r_r)
        out.append((at[0] + x * eye, at[1] + y * eye))
    return out
