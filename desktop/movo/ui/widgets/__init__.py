"""Reusable, theme-aware widgets."""

from __future__ import annotations

from collections.abc import Callable
from typing import Optional

import numpy as np
from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
)
from PySide6.QtGui import QBrush, QColor, QConicalGradient, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from movo.i18n import is_rtl, tr
from movo.ui import theme


# ---------------------------------------------------------------------------- basics
def label(text: str, name: str = "", wrap: bool = False) -> QLabel:
    w = QLabel(text)
    if name:
        w.setObjectName(name)
    w.setWordWrap(wrap)
    return w


class Card(QFrame):
    def __init__(self, parent: Optional[QWidget] = None, padding: int = 20, spacing: int = 12, shadow: bool = True):
        super().__init__(parent)
        self.setObjectName("Card")
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(padding, padding, padding, padding)
        self.lay.setSpacing(spacing)
        if shadow:
            eff = QGraphicsDropShadowEffect(self)
            eff.setBlurRadius(24)
            eff.setOffset(0, 4)
            c = QColor(theme.current().shadow)
            c.setAlpha(18 if theme.current().name == "light" else 60)
            eff.setColor(c)
            self.setGraphicsEffect(eff)

    def set_active(self, active: bool) -> None:
        if self.property("active") == active:
            return
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)


def page_header(title: str, subtitle: str = "") -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 4)
    lay.setSpacing(2)
    lay.addWidget(label(title, "PageTitle"))
    if subtitle:
        lay.addWidget(label(subtitle, "PageSubtitle", wrap=True))
    return w


def hline() -> QFrame:
    f = QFrame()
    f.setFixedHeight(1)
    f.setStyleSheet(f"background: {theme.current().border};")
    return f


# ---------------------------------------------------------------------------- toggle switch
class Toggle(QAbstractButton):
    """iOS / Fluent style switch with a smooth knob animation. Mirrors itself in RTL layouts."""

    def __init__(self, checked: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(44, 24)
        self._pos = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def _animate(self, on: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def _get(self) -> float:
        return self._pos

    def _set(self, v: float) -> None:
        self._pos = v
        self.update()

    knob = Property(float, _get, _set)

    def sizeHint(self) -> QSize:
        return QSize(44, 24)

    def paintEvent(self, _):
        p = theme.current()
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        track = theme.mix(p.border, p.accent, self._pos)
        if not self.isEnabled():
            track.setAlpha(110)
        qp.setPen(Qt.NoPen)
        qp.setBrush(track)
        qp.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        pos = self._pos if not is_rtl() else 1 - self._pos
        d = r.height() - 6
        x = 3 + pos * (r.width() - d - 6)
        qp.setBrush(QColor("#FFFFFF"))
        qp.drawEllipse(QRectF(x + 0.5, 3.5, d, d))


class SettingRow(QWidget):
    """Title + description on one side, a control on the other."""

    def __init__(self, title: str, description: str, control: QWidget, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 6)
        lay.setSpacing(16)
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(label(title))
        if description:
            text.addWidget(label(description, "Small", wrap=True))
        lay.addLayout(text, 1)
        lay.addWidget(control, 0, Qt.AlignVCenter)


def toggle_row(title: str, description: str, checked: bool, on_change: Callable[[bool], None]) -> SettingRow:
    t = Toggle(checked)
    t.toggled.connect(on_change)
    row = SettingRow(title, description, t)
    row.toggle = t  # type: ignore[attr-defined]
    return row


def combo(items: list[tuple[str, str]], current: str, on_change: Callable[[str], None], width: int = 200) -> QComboBox:
    c = QComboBox()
    c.setMinimumWidth(width)
    for value, text in items:
        c.addItem(text, value)
    idx = c.findData(current)
    if idx >= 0:
        c.setCurrentIndex(idx)
    c.currentIndexChanged.connect(lambda _i: on_change(c.currentData()))
    return c


def slider(value: float, lo: float, hi: float, on_change: Callable[[float], None], width: int = 200) -> QSlider:
    s = QSlider(Qt.Horizontal)
    s.setRange(0, 100)
    s.setFixedWidth(width)
    s.setValue(int(round((value - lo) / (hi - lo) * 100)))
    s.valueChanged.connect(lambda v: on_change(lo + (hi - lo) * v / 100))
    return s


# ---------------------------------------------------------------------------- status dot
class StatusDot(QWidget):
    def __init__(self, color: str = "#999", size: int = 10, pulse: bool = False, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._size = size
        self.setFixedSize(size + 8, size + 8)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.set_pulse(pulse)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def set_pulse(self, on: bool) -> None:
        if on:
            self._timer.start(50)
        else:
            self._timer.stop()
            self._phase = 0.0
            self.update()

    def _tick(self):
        self._phase = (self._phase + 0.05) % 1.0
        self.update()

    def paintEvent(self, _):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        if self._timer.isActive():
            halo = QColor(self._color)
            halo.setAlphaF(0.35 * (1 - self._phase))
            qp.setPen(Qt.NoPen)
            qp.setBrush(halo)
            r = self._size / 2 + 4 * self._phase
            qp.drawEllipse(c, r, r)
        qp.setPen(Qt.NoPen)
        qp.setBrush(self._color)
        qp.drawEllipse(c, self._size / 2, self._size / 2)


# ---------------------------------------------------------------------------- power button
class PowerButton(QAbstractButton):
    """Large circular start/stop control with the brand gradient and a breathing ring while running."""

    def __init__(self, parent=None, diameter: int = 132):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(diameter + 28, diameter + 28)
        self._d = diameter
        self._phase = 0.0
        self._busy = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._hover = False
        self.toggled.connect(lambda on: self._timer.start(33) if on else self._stop_anim())

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        if busy:
            self._timer.start(33)
        elif not self.isChecked():
            self._stop_anim()
        self.update()

    def _stop_anim(self):
        if not self._busy:
            self._timer.stop()
        self._phase = 0.0
        self.update()

    def _tick(self):
        self._phase = (self._phase + 0.012) % 1.0
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, _):
        p = theme.current()
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        r = self._d / 2
        on = self.isChecked()

        if on and not self._busy:
            for k in (0.0, 0.5):
                ph = (self._phase + k) % 1.0
                ring = QColor(p.accent)
                ring.setAlphaF(0.45 * (1 - ph))
                qp.setPen(QPen(ring, 2))
                qp.setBrush(Qt.NoBrush)
                qp.drawEllipse(c, r + 2 + 10 * ph, r + 2 + 10 * ph)

        if on or self._hover:
            brush = QBrush(QColor(p.accent))
            if not on:
                qp.setOpacity(0.14)
        else:
            brush = QBrush(QColor(p.surface_alt))
        qp.setPen(Qt.NoPen)
        qp.setBrush(brush)
        qp.drawEllipse(c, r, r)
        qp.setOpacity(1.0)
        if not on:
            qp.setPen(QPen(QColor(p.border), 2))
            qp.setBrush(Qt.NoBrush)
            qp.drawEllipse(c, r, r)

        if self._busy:
            cg = QConicalGradient(c, -self._phase * 360 * 3)
            cg.setColorAt(0, QColor(p.accent))
            cg.setColorAt(0.5, QColor(0, 0, 0, 0))
            qp.setPen(QPen(QBrush(cg), 4, Qt.SolidLine, Qt.RoundCap))
            qp.drawEllipse(c, r - 2, r - 2)

        # power glyph
        fg = QColor(p.accent_text) if on else QColor(p.accent if self._hover else p.text_muted)
        pen = QPen(fg, 6, Qt.SolidLine, Qt.RoundCap)
        qp.setPen(pen)
        qp.setBrush(Qt.NoBrush)
        gr = r * 0.36
        rect = QRectF(c.x() - gr, c.y() - gr + 3, gr * 2, gr * 2)
        qp.drawArc(rect, int(120 * 16), int(300 * 16))
        qp.drawLine(QPointF(c.x(), c.y() - gr - 4), QPointF(c.x(), c.y() + 1))


# ---------------------------------------------------------------------------- preview
class PreviewView(QWidget):
    """Shows the live camera preview with rounded corners, or a friendly placeholder."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._img: Optional[QImage] = None
        self._buf: Optional[np.ndarray] = None
        self.placeholder = tr("home.preview_off")
        self.overlay_text = ""
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_frame(self, rgb: Optional[np.ndarray]) -> None:
        if rgb is None:
            self._img = None
            self._buf = None
        else:
            self._buf = np.ascontiguousarray(rgb)
            h, w = self._buf.shape[:2]
            self._img = QImage(self._buf.data, w, h, w * 3, QImage.Format_RGB888)
        self.update()

    def paintEvent(self, _):
        p = theme.current()
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        qp.setRenderHint(QPainter.SmoothPixmapTransform)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, 14, 14)
        qp.setClipPath(path)
        qp.fillPath(path, QColor(p.surface_alt))
        if self._img is not None:
            iw, ih = self._img.width(), self._img.height()
            scale = max(r.width() / iw, r.height() / ih)
            tw, th = iw * scale, ih * scale
            target = QRectF(r.center().x() - tw / 2, r.center().y() - th / 2, tw, th)
            qp.drawImage(target, self._img)
            if self.overlay_text:
                pill = QRectF(r.left() + 12, r.bottom() - 44, min(r.width() - 24, 60 + 8 * len(self.overlay_text)), 32)
                qp.setPen(Qt.NoPen)
                qp.setBrush(QColor(0, 0, 0, 140))
                qp.drawRoundedRect(pill, 16, 16)
                qp.setPen(QColor("#FFFFFF"))
                qp.drawText(pill, Qt.AlignCenter, self.overlay_text)
        else:
            qp.setPen(QColor(p.text_muted))
            f = qp.font()
            f.setPointSizeF(f.pointSizeF() * 1.05)
            qp.setFont(f)
            # camera glyph
            cx, cy = r.center().x(), r.center().y() - 18
            pen = QPen(QColor(p.text_muted), 2)
            qp.setPen(pen)
            qp.drawRoundedRect(QRectF(cx - 22, cy - 14, 44, 30), 6, 6)
            qp.drawEllipse(QPointF(cx, cy + 1), 8, 8)
            qp.drawText(QRectF(r.left() + 20, cy + 26, r.width() - 40, 60), Qt.AlignHCenter | Qt.TextWordWrap, self.placeholder)


# ---------------------------------------------------------------------------- logo
class LogoMark(QWidget):
    def __init__(self, size: int = 36, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        from PySide6.QtSvg import QSvgRenderer

        from movo.paths import asset

        self._r = QSvgRenderer(str(asset("icons", "logo.svg")))

    def paintEvent(self, _):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        self._r.render(qp, QRectF(0, 0, self.width(), self.height()))


def flash(widget: QWidget, ms: int = 700) -> None:
    """Briefly highlight a Card."""
    if isinstance(widget, Card):
        widget.set_active(True)
        QTimer.singleShot(ms, lambda: widget.set_active(False))


__all__ = [
    "Card",
    "Toggle",
    "SettingRow",
    "toggle_row",
    "combo",
    "slider",
    "label",
    "page_header",
    "hline",
    "StatusDot",
    "PowerButton",
    "PreviewView",
    "LogoMark",
    "flash",
]
