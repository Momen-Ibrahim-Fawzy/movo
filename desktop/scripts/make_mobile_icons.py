"""Generate the Android vector icons, the iOS app icon and the browser-helper icons from branding/.

Usage: python scripts/make_mobile_icons.py   (after scripts/make_icons.py)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MARK = ROOT / "branding" / "mark.svg"
RES = ROOT / "mobile" / "android" / "app" / "src" / "main" / "res" / "drawable"
IOS_ICON = ROOT / "mobile" / "ios" / "Movo" / "Resources" / "Assets.xcassets" / "AppIcon.appiconset" / "AppIcon-1024.png"
EXT_ICONS = ROOT / "browser-extension" / "icons"
BLUE = (26, 115, 232, 255)


def vector_paths(svg: str, color: str) -> str:
    out = []
    for cx, cy, r in re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)"/>', svg):
        cx, cy, r = float(cx), float(cy), float(r)
        d = f"M{cx - r:.1f},{cy:.1f} a{r:.1f},{r:.1f} 0 1,0 {2 * r:.1f},0 a{r:.1f},{r:.1f} 0 1,0 {-2 * r:.1f},0 Z"
        out.append(f'        <path android:fillColor="{color}" android:pathData="{d}" />')
    for d, w in re.findall(r'<path d="([^"]+)" stroke-width="([\d.]+)"/>', svg):
        out.append(
            f'        <path android:fillColor="#00000000" android:strokeColor="{color}" android:strokeWidth="{w}" '
            f'android:strokeLineCap="round" android:pathData="{d}" />'
        )
    for d in re.findall(r'<path d="([^"]+)"/>', svg):
        out.append(f'        <path android:fillColor="{color}" android:pathData="{d}" />')
    return "\n".join(out)


def vector(svg: str, size_dp: int, scale: float, color: str, tint: bool = False) -> str:
    tint_attr = '\n    android:tint="?attr/colorControlNormal"' if tint else ""
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- Generated from branding/mark.svg by desktop/scripts/make_mobile_icons.py -->
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="{size_dp}dp"
    android:height="{size_dp}dp"
    android:viewportWidth="512"
    android:viewportHeight="512"{tint_attr}>
    <group android:pivotX="256" android:pivotY="256" android:scaleX="{scale}" android:scaleY="{scale}">
{vector_paths(svg, color)}
    </group>
</vector>
"""


def main() -> int:
    svg = MARK.read_text(encoding="utf-8")
    # Adaptive icons only show the central 66/108 of the foreground: shrink the mark into that safe zone.
    (RES / "ic_launcher_foreground.xml").write_text(vector(svg, 108, 0.85, "#FFFFFF"), encoding="utf-8")
    (RES / "ic_stat_movo.xml").write_text(vector(svg, 24, 1.3, "#FFFFFF", tint=True), encoding="utf-8")
    old = RES / "ic_stat_imaa.xml"
    if old.exists():
        old.unlink()

    big = Image.open(ROOT / "branding" / "logo-1024.png").convert("RGBA")
    flat = Image.new("RGBA", big.size, BLUE)  # iOS icons must be opaque; iOS applies its own corner mask
    flat.alpha_composite(big)
    flat.convert("RGB").save(IOS_ICON)
    for s in (16, 32, 64, 128):
        Image.open(ROOT / "branding" / f"logo-{s}.png").save(EXT_ICONS / f"{s}.png")
    print("android vectors, iOS app icon and browser-helper icons written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
