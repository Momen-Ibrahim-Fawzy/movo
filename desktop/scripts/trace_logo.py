"""Trace the Movo mark from the brand artwork into clean SVGs (branding/logo.svg and branding/mark.svg).

- the head is fitted as a perfect circle,
- the two signal waves are rebuilt as true circular arcs with round caps,
- the motion stroke is traced, evenly resampled and smoothed,
then the whole mark is centred on a solid-blue rounded square.

Usage: python scripts/trace_logo.py <artwork.png>
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BLUE = "#1A73E8"
SIZE = 512
RADIUS = 118  # corner radius of the app-icon square
MARK_WIDTH = 0.70  # share of the square the mark spans


def smooth_path(points: np.ndarray) -> str:
    """Closed Catmull-Rom spline through the points, written as cubic Béziers."""
    p = points.astype(float)
    n = len(p)
    d = f"M{p[0][0]:.1f},{p[0][1]:.1f}"
    for i in range(n):
        p0, p1, p2, p3 = p[i - 1], p[i], p[(i + 1) % n], p[(i + 2) % n]
        c1 = p1 + (p2 - p0) / 6
        c2 = p2 - (p3 - p1) / 6
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d + " Z"


def resample_smooth(pts: np.ndarray, n: int, window: int) -> np.ndarray:
    """Evenly resample a closed outline and smooth it with a circular moving average."""
    pts = pts.astype(float)
    closed = np.vstack([pts, pts[:1]])
    seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, cum[-1], n, endpoint=False)
    res = np.column_stack([np.interp(t, cum, closed[:, 0]), np.interp(t, cum, closed[:, 1])])
    kernel = np.ones(window) / window
    pad = window // 2
    cols = []
    for dim in (0, 1):
        v = np.concatenate([res[-pad:, dim], res[:, dim], res[:pad, dim]])
        cols.append(np.convolve(v, kernel, mode="valid"))
    return np.column_stack(cols)


def fit_arc(contour: np.ndarray):
    """Least-squares circle through a stroke outline → (cx, cy, radius, width, start_deg, end_deg)."""
    pts = contour.reshape(-1, 2).astype(float)
    a = np.column_stack([2 * pts[:, 0], 2 * pts[:, 1], np.ones(len(pts))])
    b = (pts**2).sum(1)
    cx, cy, _ = np.linalg.lstsq(a, b, rcond=None)[0]
    d = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)
    r_in, r_out = np.percentile(d, 5), np.percentile(d, 95)
    width = (r_out - r_in) * 0.85  # percentiles include the anti-aliased edge; match the artwork weight
    radius = (r_in + r_out) / 2
    ang = np.degrees(np.arctan2(pts[:, 1] - cy, pts[:, 0] - cx))  # arcs open to the left → angles near 0°
    cap = np.degrees(width / 2 / radius)
    return cx, cy, radius, width, ang.min() + cap, ang.max() - cap


def build_svg(parts: list[str], strokes: list[str], background: bool) -> str:
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}" width="{SIZE}" height="{SIZE}">']
    if background:
        lines.append(f'  <rect x="0" y="0" width="{SIZE}" height="{SIZE}" rx="{RADIUS}" fill="{BLUE}"/>')
    lines.append('  <g fill="#FFFFFF">')
    lines += [f"    {p}" for p in parts]
    lines.append("  </g>")
    lines.append('  <g fill="none" stroke="#FFFFFF" stroke-linecap="round">')
    lines += [f"    {s}" for s in strokes]
    lines.append("  </g>")
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def main() -> int:
    src = cv2.imread(sys.argv[1])
    hsv = cv2.cvtColor(src, cv2.COLOR_BGR2HSV)
    blue = cv2.inRange(hsv, (95, 120, 120), (125, 255, 255))
    ys, xs = np.where(blue[: int(src.shape[0] * 0.66)] > 0)
    square = src[ys.min() : ys.max(), xs.min() : xs.max()]
    white = cv2.inRange(cv2.cvtColor(square, cv2.COLOR_BGR2HSV), (0, 0, 200), (180, 70, 255))
    h, w = white.shape
    inner = np.zeros_like(white)
    cv2.rectangle(inner, (int(w * 0.06), int(h * 0.06)), (int(w * 0.94), int(h * 0.94)), 255, -1)
    white = cv2.morphologyEx(cv2.bitwise_and(white, inner), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contours = sorted([c for c in contours if cv2.contourArea(c) > 500], key=cv2.contourArea, reverse=True)
    biggest = cv2.contourArea(contours[0])

    shapes = []
    for c in contours:
        area = cv2.contourArea(c)
        (_cx, _cy), r = cv2.minEnclosingCircle(c)
        if area / (np.pi * r * r) > 0.8:
            m = cv2.moments(c)
            shapes.append(("circle", (m["m10"] / m["m00"], m["m01"] / m["m00"], np.sqrt(area / np.pi))))
        elif area < 0.5 * biggest:
            shapes.append(("arc", fit_arc(c)))
        else:
            shapes.append(("path", resample_smooth(c.reshape(-1, 2), 140, 9)))
    print("shapes:", [k for k, _ in shapes])

    allpts = np.vstack([c.reshape(-1, 2) for c in contours])
    (mx0, my0), (mx1, my1) = allpts.min(0), allpts.max(0)
    scale = SIZE * MARK_WIDTH / (mx1 - mx0)
    ox = SIZE / 2 - (mx0 + mx1) / 2 * scale
    oy = SIZE / 2 - (my0 + my1) / 2 * scale

    def tx(pt) -> np.ndarray:
        return np.array([pt[0] * scale + ox, pt[1] * scale + oy])

    parts, strokes = [], []
    for kind, val in shapes:
        if kind == "circle":
            cx, cy, r = val
            c = tx((cx, cy))
            parts.append(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="{r * scale:.1f}"/>')
        elif kind == "arc":
            cx, cy, r, width, a0, a1 = val
            c, rr = tx((cx, cy)), r * scale
            p0 = c + rr * np.array([np.cos(np.radians(a0)), np.sin(np.radians(a0))])
            p1 = c + rr * np.array([np.cos(np.radians(a1)), np.sin(np.radians(a1))])
            strokes.append(
                f'<path d="M{p0[0]:.1f},{p0[1]:.1f} A{rr:.1f},{rr:.1f} 0 0 1 {p1[0]:.1f},{p1[1]:.1f}" '
                f'stroke-width="{width * scale:.1f}"/>'
            )
        else:
            parts.append(f'<path d="{smooth_path(np.array([tx(p) for p in val]))}"/>')

    (ROOT / "branding" / "logo.svg").write_text(build_svg(parts, strokes, True), encoding="utf-8")
    (ROOT / "branding" / "mark.svg").write_text(build_svg(parts, strokes, False), encoding="utf-8")
    print("wrote branding/logo.svg and branding/mark.svg")
    return 0


if __name__ == "__main__":
    sys.exit(main())
