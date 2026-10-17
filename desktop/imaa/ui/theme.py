"""Design tokens, light/dark palettes and the application style sheet.

See docs/DESIGN.md for the rationale. Every colour used by custom-painted widgets comes from ``current()``.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str
    sidebar: str
    surface: str
    surface_alt: str
    border: str
    text: str
    text_muted: str
    accent: str
    accent_hover: str
    accent_soft: str
    accent_text: str
    teal: str
    success: str
    warning: str
    danger: str
    shadow: str


LIGHT = Palette(
    name="light",
    bg="#F8F9FA",
    sidebar="#FFFFFF",
    surface="#FFFFFF",
    surface_alt="#F1F3F4",
    border="#E0E3E7",
    text="#1F1F1F",
    text_muted="#5F6368",
    accent="#1A73E8",
    accent_hover="#1765CC",
    accent_soft="#E8F0FE",
    accent_text="#FFFFFF",
    teal="#1A73E8",
    success="#1E8E3E",
    warning="#E37400",
    danger="#D93025",
    shadow="#3C4043",
)

DARK = Palette(
    name="dark",
    bg="#1F1F1F",
    sidebar="#202124",
    surface="#28292C",
    surface_alt="#303134",
    border="#3C4043",
    text="#E8EAED",
    text_muted="#9AA0A6",
    accent="#8AB4F8",
    accent_hover="#AECBFA",
    accent_soft="#283B57",
    accent_text="#202124",
    teal="#8AB4F8",
    success="#81C995",
    warning="#FDD663",
    danger="#F28B82",
    shadow="#000000",
)

BRAND_BLUE = "#1A73E8"  # logo and brand colour

_current: Palette = LIGHT


def current() -> Palette:
    return _current


def set_current(p: Palette) -> None:
    global _current
    _current = p


def resolve(theme_setting: str) -> Palette:
    if theme_setting == "dark":
        return DARK
    if theme_setting == "light":
        return LIGHT
    try:
        from PySide6.QtGui import QGuiApplication

        scheme = QGuiApplication.styleHints().colorScheme()
        return DARK if scheme == Qt.ColorScheme.Dark else LIGHT
    except Exception:
        return LIGHT


def app_font(rtl: bool = False) -> QFont:
    f = QFont()
    if sys.platform == "win32":
        fams = ["Segoe UI Variable Text", "Segoe UI", "Tahoma"]
    elif sys.platform == "darwin":
        fams = [".AppleSystemUIFont", "SF Pro Text", "Helvetica Neue", "Geeza Pro"]
    else:
        fams = ["Inter", "Noto Sans", "Noto Sans Arabic", "Cantarell", "DejaVu Sans"]
    if rtl and sys.platform != "darwin":
        fams = ["Segoe UI", "Noto Sans Arabic", "Noto Naskh Arabic", "Tahoma"] + fams
    f.setFamilies(fams)
    f.setPointSizeF(10.0 if sys.platform != "darwin" else 13.0)
    f.setHintingPreference(QFont.PreferNoHinting)
    return f


def rgba(hex_color: str, alpha: float) -> str:
    c = QColor(hex_color)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {int(alpha * 255)})"


def stylesheet(p: Palette) -> str:
    return f"""
* {{ outline: none; }}
QWidget {{ color: {p.text}; background: transparent; }}
QMainWindow, QDialog, #Root {{ background: {p.bg}; }}
QToolTip {{ background: {p.surface}; color: {p.text}; border: 1px solid {p.border}; padding: 6px 8px; border-radius: 6px; }}

#Sidebar {{ background: {p.sidebar}; border: none; }}
#SidebarDivider {{ background: {p.border}; max-width: 1px; min-width: 1px; }}
#Brand {{ font-size: 17pt; font-weight: 700; }}
#BrandSub {{ color: {p.text_muted}; font-size: 8.5pt; }}
QPushButton#NavItem {{
    text-align: left; padding: 10px 14px; border-radius: 10px; border: none; background: transparent;
    color: {p.text_muted}; font-size: 10.5pt; font-weight: 500;
}}
QPushButton#NavItem:hover {{ background: {p.surface_alt}; color: {p.text}; }}
QPushButton#NavItem:checked {{ background: {p.accent_soft}; color: {p.accent}; font-weight: 600; }}

#PageTitle {{ font-size: 20pt; font-weight: 700; }}
#PageSubtitle {{ color: {p.text_muted}; font-size: 10.5pt; }}
#SectionTitle {{ font-size: 12pt; font-weight: 650; }}
#Muted {{ color: {p.text_muted}; }}
#Small {{ color: {p.text_muted}; font-size: 8.5pt; }}
#Emoji {{ font-size: 24pt; }}
#BigStatus {{ font-size: 15pt; font-weight: 650; }}

#Card {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: 16px; }}
#Card[active="true"] {{ border: 2px solid {p.accent}; }}
#Banner {{ background: {p.accent_soft}; border-radius: 12px; }}
#WarnBanner {{ background: {rgba(p.warning, 0.13)}; border: 1px solid {rgba(p.warning, 0.4)}; border-radius: 12px; }}

QPushButton {{
    background: {p.surface}; border: 1px solid {p.border}; border-radius: 10px;
    padding: 8px 16px; font-weight: 500;
}}
QPushButton:hover {{ border-color: {p.accent}; color: {p.accent}; }}
QPushButton:pressed {{ background: {p.accent_soft}; }}
QPushButton:disabled {{ color: {p.text_muted}; border-color: {p.border}; }}
QPushButton#Primary {{ background: {p.accent}; color: {p.accent_text}; border: none; font-weight: 600; }}
QPushButton#Primary:hover {{ background: {p.accent_hover}; color: {p.accent_text}; }}
QPushButton#Danger {{ color: {p.danger}; }}
QPushButton#Danger:hover {{ border-color: {p.danger}; }}
QPushButton#Ghost {{ background: transparent; border: none; color: {p.text_muted}; padding: 6px 10px; }}
QPushButton#Ghost:hover {{ color: {p.accent}; background: {p.surface_alt}; }}
QPushButton#Chip {{
    background: {p.surface_alt}; border: 1px solid transparent; border-radius: 14px; padding: 4px 12px;
    color: {p.text_muted}; font-size: 9pt;
}}
QPushButton#Chip:checked {{ background: {p.accent_soft}; color: {p.accent}; border-color: {p.accent}; }}

QComboBox, QLineEdit, QSpinBox {{
    background: {p.surface}; border: 1px solid {p.border}; border-radius: 9px; padding: 6px 10px;
    min-height: 20px; selection-background-color: {p.accent}; selection-color: {p.accent_text};
}}
QComboBox:hover, QLineEdit:hover, QSpinBox:hover {{ border-color: {p.accent}; }}
QComboBox:focus, QLineEdit:focus {{ border: 1px solid {p.accent}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: {p.surface}; border: 1px solid {p.border}; border-radius: 8px; padding: 4px;
    selection-background-color: {p.accent_soft}; selection-color: {p.text}; outline: none;
}}

QSlider::groove:horizontal {{ height: 6px; background: {p.border}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {p.accent}; border-radius: 3px; }}
QSlider::add-page:horizontal {{ background: {p.border}; border-radius: 3px; }}
QSlider::handle:horizontal {{
    background: {p.surface}; border: 2px solid {p.accent}; width: 14px; height: 14px; margin: -6px 0; border-radius: 9px;
}}

QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {p.border}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {p.text_muted}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ height: 0; background: none; }}

QListWidget {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: 12px; padding: 6px; }}
QListWidget::item {{ padding: 10px; border-radius: 8px; }}
QListWidget::item:selected {{ background: {p.accent_soft}; color: {p.text}; }}
QListWidget::item:hover {{ background: {p.surface_alt}; }}

QCheckBox {{ spacing: 8px; }}
QMenu {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: 10px; padding: 6px; }}
QMenu::item {{ padding: 7px 18px; border-radius: 6px; }}
QMenu::item:selected {{ background: {p.accent_soft}; color: {p.text}; }}
QMenu::separator {{ height: 1px; background: {p.border}; margin: 4px 8px; }}
"""


# ---------------------------------------------------------------------------- icons
# Simple line icons drawn for Imaa (24×24, stroke = currentColor).
ICONS = {
    "home": '<path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10v9.5h13V10"/><path d="M10 19.5v-5h4v5"/>',
    "hand": '<path d="M8 13V5.5a1.5 1.5 0 0 1 3 0V12"/><path d="M11 11V4a1.5 1.5 0 0 1 3 0v7"/>'
    '<path d="M14 11V5.5a1.5 1.5 0 0 1 3 0V13"/><path d="M17 10.5a1.5 1.5 0 0 1 3 0V15a6 6 0 0 1-6 6h-1.5'
    'a6 6 0 0 1-4.6-2.2L4.5 15.6a1.6 1.6 0 0 1 2.4-2.1L8 14.6"/>',
    "face": '<circle cx="12" cy="12" r="8.5"/><path d="M9 10h.01M15 10h.01"/><path d="M8.5 14.5a4.5 4.5 0 0 0 7 0"/>',
    "layers": '<path d="M12 3 3 8l9 5 9-5-9-5z"/><path d="m3 13 9 5 9-5"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1'
    "a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1"
    "a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1"
    " 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0"
    "v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0"
    ' 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 16v-4.5M12 8h.01"/>',
    "book": '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z"/><path d="M4 20.5A2.5 2.5 0 0 0 6.5 23H20v-5"/><path d="M8.5 7.5h7M8.5 11h5"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.6 4.6l1.4 1.4M18 18l1.4 1.4M2.5 12h2'
    'M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4"/>',
    "moon": '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    "lock": '<rect x="5" y="10.5" width="14" height="10" rx="2.5"/><path d="M8.5 10.5V7.5a3.5 3.5 0 0 1 7 0v3"/>',
    "camera": '<path d="M3.5 8.5A2 2 0 0 1 5.5 6.5h2l1.5-2h6l1.5 2h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/>'
    '<circle cx="12" cy="13" r="3.5"/>',
    "pause": '<rect x="6.5" y="5" width="3.5" height="14" rx="1"/><rect x="14" y="5" width="3.5" height="14" rx="1"/>',
    "play": '<path d="M7 4.5v15l12-7.5z"/>',
    "refresh": '<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4.5V11h-6.5"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "trash": '<path d="M4 7h16M9.5 7V4.5h5V7M6.5 7l1 13h9l1-13"/>',
    "phone": '<rect x="7" y="2.5" width="10" height="19" rx="2.5"/><path d="M11 18.5h2"/>',
    "puzzle": '<path d="M9 4.5a2 2 0 0 1 4 0V6h4v4h1.5a2 2 0 0 1 0 4H17v4h-4v-1.5a2 2 0 0 0-4 0V18H5v-4h1.5a2 2 0 0 0 0-4H5V6h4z"/>',
}


def icon_pixmap(name: str, color: str, size: int = 20, dpr: float = 2.0) -> QPixmap:
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    px = int(size * dpr)
    img = QImage(px, px, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter, QRectF(0, 0, px, px))
    painter.end()
    pm = QPixmap.fromImage(img)
    pm.setDevicePixelRatio(dpr)
    return pm


def icon(name: str, color: str, size: int = 20) -> QIcon:
    return QIcon(icon_pixmap(name, color, size))


def mix(c1: str, c2: str, t: float) -> QColor:
    a, b = QColor(c1), QColor(c2)
    return QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
    )
