"""Small 2-D geometry helpers working on (x, y) tuples.

Coordinates are in *height units*: x is multiplied by the frame aspect ratio so that distances are
isotropic, and y grows downwards (image convention).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

Point = Sequence[float]


def dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def angle_at(a: Point, b: Point, c: Point) -> float:
    """Angle ABC in degrees (180 = straight line)."""
    v1 = (a[0] - b[0], a[1] - b[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    n1 = math.hypot(*v1)
    n2 = math.hypot(*v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return 180.0
    cos = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def direction(a: Point, b: Point) -> float:
    """Direction of the vector a→b in degrees, mathematical convention with y pointing *up*.

    0 = right, 90 = up, ±180 = left, -90 = down.
    """
    return math.degrees(math.atan2(-(b[1] - a[1]), b[0] - a[0]))


def angle_diff(a: float, b: float) -> float:
    """Smallest absolute difference between two angles in degrees."""
    d = (a - b + 180.0) % 360.0 - 180.0
    return abs(d)


def mean_point(points: Sequence[Point]) -> tuple[float, float]:
    n = len(points)
    return (sum(p[0] for p in points) / n, sum(p[1] for p in points) / n)
