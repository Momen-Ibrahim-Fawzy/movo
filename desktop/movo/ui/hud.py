"""Click-through on-screen feedback bubble ("🔊 Volume up")."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QFont, QFontMetrics, QGuiApplication, QPainter
from PySide6.QtWidgets import QWidget

from movo.i18n import is_rtl
from movo.ui import theme


class Hud(QWidget):
    def __init__(self, settings):
        super().__init__(
            None,
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowTransparentForInput
            | Qt.WindowDoesNotAcceptFocus
            | Qt.NoDropShadowWindowHint,
        )
        self.settings = settings
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._emoji = ""
        self._text = ""
        self._ok = True
        self._timer = QTimer(self, singleShot=True)
        self._timer.timeout.connect(self._fade)
        self._anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self._done)

    def show_message(self, emoji: str, text: str, ok: bool = True, ms: int = 1300) -> None:
        if not self.settings.get("hud.enabled", True):
            return
        self._emoji, self._text, self._ok = emoji, text, ok
        f = QFont(self.font())
        f.setPointSizeF(13)
        f.setWeight(QFont.DemiBold)
        self.setFont(f)
        fm = QFontMetrics(f)
        w = fm.horizontalAdvance(f"{emoji}   {text}") + 56
        h = fm.height() + 28
        self.resize(max(160, w), h)
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        g = screen.availableGeometry()
        x = g.x() + (g.width() - self.width()) // 2
        y = g.y() + (g.height() - self.height() - 72 if self.settings.get("hud.position", "bottom") == "bottom" else 48)
        self.move(x, y)
        self._anim.stop()
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()
        self.update()
        self._timer.start(ms)

    def _fade(self) -> None:
        self._anim.setDuration(350)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def _done(self) -> None:
        if self.windowOpacity() <= 0.01:
            self.hide()

    def paintEvent(self, _):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        bg = QColor(18, 20, 28, 225)
        qp.setPen(Qt.NoPen)
        qp.setBrush(bg)
        qp.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        accent = QColor(theme.DARK.accent if self._ok else theme.DARK.danger)
        qp.setBrush(accent)
        dot = QRectF(r.right() - 22 if is_rtl() else r.left() + 14, r.center().y() - 4, 8, 8)
        qp.drawEllipse(dot)
        qp.setPen(QColor("#FFFFFF"))
        text = f"{self._text}   {self._emoji}" if is_rtl() else f"{self._emoji}   {self._text}"
        qp.drawText(r.adjusted(24, 0, -24, 0), Qt.AlignCenter, text)
