"""Render the brand SVG into the PNG/ICO/ICNS files used by the app and the installers.

Usage: python scripts/make_icons.py
"""

from __future__ import annotations

import io
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parents[2]
SVG = ROOT / "branding" / "logo.svg"
APP_ICONS = ROOT / "desktop" / "imaa" / "assets" / "icons"
PKG = ROOT / "desktop" / "packaging"
BRAND = ROOT / "branding"


def render(size: int, svg: Path = SVG, grayscale: bool = False) -> QImage:
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(str(svg)).render(p, QRectF(0, 0, size, size))
    p.end()
    if grayscale:
        gray = img.convertToFormat(QImage.Format_Grayscale8).convertToFormat(QImage.Format_ARGB32)
        for y in range(size):
            for x in range(size):
                a = img.pixelColor(x, y).alpha()
                c = gray.pixelColor(x, y)
                c.setAlpha(a)
                gray.setPixelColor(x, y, c)
        img = gray
    return img


def png_bytes(img: QImage) -> bytes:
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


def main() -> int:
    QGuiApplication(sys.argv[:1])
    APP_ICONS.mkdir(parents=True, exist_ok=True)
    PKG.mkdir(parents=True, exist_ok=True)
    shutil.copy(SVG, APP_ICONS / "logo.svg")
    for size in (16, 32, 64, 128, 256, 512, 1024):
        render(size).save(str(BRAND / f"logo-{size}.png"))
    render(256).save(str(APP_ICONS / "logo-256.png"))
    render(64, grayscale=True).save(str(APP_ICONS / "tray-off.png"))
    render(64).save(str(APP_ICONS / "tray-on.png"))
    render(512).save(str(PKG / "imaa.png"))

    from PIL import Image  # Pillow writes multi-size ICO and ICNS files

    big = Image.open(io.BytesIO(png_bytes(render(1024))))
    big.save(PKG / "imaa.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    big.save(PKG / "imaa.icns")
    print("icons written to", APP_ICONS, "and", PKG)
    return 0


if __name__ == "__main__":
    sys.exit(main())
