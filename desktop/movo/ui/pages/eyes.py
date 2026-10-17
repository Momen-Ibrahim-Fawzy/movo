"""Eye gestures page: settings, live eye meter and the calibration wizard."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QProgressBar, QPushButton, QVBoxLayout, QWidget

from movo.i18n import is_rtl, tr
from movo.ui import theme
from movo.ui.pages.gestures import GesturesPage
from movo.ui.widgets import Card, SettingRow, label, slider, toggle_row


class EyeMeter(QWidget):
    """Two openness bars (left / right eye) and a gaze dot — lets people with glasses see that tracking works."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.setMinimumWidth(560)
        self.setLayoutDirection(Qt.LeftToRight)  # the eyes are drawn as the camera (mirror) sees them
        self.open = (1.0, 1.0)
        self.gaze = (0.0, 0.0)
        self.seen = False

    def set_values(self, open_lr, gaze, seen: bool) -> None:
        self.open, self.gaze, self.seen = open_lr, gaze, seen
        self.update()

    def paintEvent(self, _):
        p = theme.current()
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)
        h = self.height()
        # eyes: draw as two almond outlines that close with the measured openness
        for i, cx in enumerate((60, 150)):
            o = max(0.05, min(1.0, self.open[i])) if self.seen else 0.05
            rect = QRectF(cx - 36, h / 2 - 22 * o, 72, 44 * o)
            qp.setPen(QPen(QColor(p.accent if self.seen else p.border), 2))
            qp.setBrush(QColor(p.accent_soft))
            qp.drawEllipse(rect)
            if self.seen and o > 0.3:
                gx = max(-1.5, min(1.5, self.gaze[0])) * 14
                gy = max(-1.5, min(1.5, self.gaze[1])) * -8 * o
                qp.setPen(Qt.NoPen)
                qp.setBrush(QColor(p.accent))
                qp.drawEllipse(QPointF(cx + gx, h / 2 + gy), 9 * o, 9 * o)
            qp.setPen(QColor(p.text_muted))
            qp.drawText(QRectF(cx - 40, h - 22, 80, 20), Qt.AlignCenter, tr("eyes.left") if i == 0 else tr("eyes.right"))
        # gaze pad
        pad = QRectF(230, 14, 92, 92)
        qp.setPen(QPen(QColor(p.border), 1.5))
        qp.setBrush(Qt.NoBrush)
        qp.drawRoundedRect(pad, 12, 12)
        qp.drawLine(QPointF(pad.center().x(), pad.top() + 8), QPointF(pad.center().x(), pad.bottom() - 8))
        qp.drawLine(QPointF(pad.left() + 8, pad.center().y()), QPointF(pad.right() - 8, pad.center().y()))
        inner = pad.adjusted(14, 14, -14, -14)
        qp.setPen(QPen(QColor(p.text_muted), 1, Qt.DashLine))
        qp.drawRect(inner)  # the dashed square = glance thresholds
        if self.seen:
            x = pad.center().x() + max(-1.6, min(1.6, self.gaze[0])) * inner.width() / 2
            y = pad.center().y() - max(-1.6, min(1.6, self.gaze[1])) * inner.height() / 2
            qp.setPen(Qt.NoPen)
            qp.setBrush(QColor(p.accent))
            qp.drawEllipse(QPointF(x, y), 6, 6)
        if not self.seen:
            qp.setPen(QColor(p.text_muted))
            align = Qt.AlignRight if is_rtl() else Qt.AlignLeft
            qp.drawText(
                QRectF(340, 0, max(0, self.width() - 340), h), align | Qt.AlignVCenter | Qt.TextWordWrap, tr("eyes.not_seen")
            )


class CalibrationDialog(QDialog):
    """Eyes open (2 s) → eyes closed (2 s, guided by sounds) → done."""

    STEPS = (("countdown", 3.0), ("open", 2.0), ("closed", 2.5), ("done", 0.0))

    def __init__(self, page: EyePage):
        super().__init__(page)
        self.page = page
        self.engine = page.controller.engine
        self.setWindowTitle(tr("eyes.calibrate"))
        self.setMinimumWidth(460)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)
        self.title = label("", "SectionTitle")
        self.text = label("", "Muted", wrap=True)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        self.bar.setStyleSheet(
            f"QProgressBar {{ background:{theme.current().surface_alt}; border:none; border-radius:4px; }}"
            f"QProgressBar::chunk {{ background:{theme.current().accent}; border-radius:4px; }}"
        )
        lay.addWidget(self.title)
        lay.addWidget(self.text)
        lay.addWidget(self.bar)
        row = QHBoxLayout()
        row.addStretch(1)
        self.button = QPushButton(tr("eyes.cal_start"))
        self.button.setObjectName("Primary")
        self.button.clicked.connect(self._start)
        row.addWidget(self.button)
        lay.addLayout(row)
        self._timer = QTimer(self, interval=50)
        self._timer.timeout.connect(self._tick)
        self._show_intro()

    def _show_intro(self):
        self.title.setText(tr("eyes.cal_title"))
        self.text.setText(tr("eyes.cal_intro"))
        self.bar.setValue(0)

    def _start(self):
        if not self.page.controller.running:
            self.page.controller.start()
        self.button.setEnabled(False)
        self.step = 0
        self.elapsed = 0.0
        self._enter()
        self._timer.start()

    def _enter(self):
        kind, _ = self.STEPS[self.step]
        if kind == "countdown":
            self.title.setText(tr("eyes.cal_ready"))
            self.text.setText(tr("eyes.cal_ready_d"))
        elif kind == "open":
            self.title.setText(tr("eyes.cal_open"))
            self.text.setText(tr("eyes.cal_open_d"))
            self.engine.eyes.begin_capture("open")
        elif kind == "closed":
            QApplication.beep()
            self.page.ctx.play_tick()
            self.title.setText(tr("eyes.cal_closed"))
            self.text.setText(tr("eyes.cal_closed_d"))
            self.engine.eyes.begin_capture("closed")
        else:
            self._finish()

    def _tick(self):
        kind, dur = self.STEPS[self.step]
        self.elapsed += 0.05
        self.bar.setValue(int(min(1.0, self.elapsed / dur) * 100) if dur else 100)
        if dur and kind == "countdown":
            self.title.setText(tr("eyes.cal_ready") + f"  {max(1, int(dur - self.elapsed + 0.99))}")
        if self.elapsed >= dur:
            self.step += 1
            self.elapsed = 0.0
            self._enter()

    def _finish(self):
        self._timer.stop()
        self.engine.eyes.end_capture()
        self.page.ctx.play_tick()
        data = self.engine.eyes.finish_calibration()
        if data:
            self.page.settings.set("eyes.calibration", data)
            self.title.setText(tr("eyes.cal_done"))
            self.text.setText(tr("eyes.cal_done_d"))
        else:
            self.title.setText(tr("eyes.cal_failed"))
            self.text.setText(tr("eyes.cal_failed_d"))
        self.button.setText(tr("eyes.cal_close"))
        self.button.setEnabled(True)
        self.button.clicked.disconnect()
        self.button.clicked.connect(self.accept)
        self.page.refresh_calibration()

    def reject(self):
        self._timer.stop()
        self.engine.eyes.end_capture()
        super().reject()


class EyePage(GesturesPage):
    source = "eye"

    def _settings_card(self) -> Card:
        s = self.settings
        card = Card()
        card.lay.addWidget(
            toggle_row(tr("eyes.enable"), tr("eyes.enable_d"), bool(s.get("eyes.enabled")), lambda v: s.set("eyes.enabled", v))
        )
        card.lay.addWidget(
            toggle_row(tr("eyes.glasses"), tr("eyes.glasses_d"), bool(s.get("eyes.glasses")), lambda v: s.set("eyes.glasses", v))
        )
        card.lay.addWidget(
            SettingRow(
                tr("head.sensitivity"),
                tr("eyes.sensitivity_d"),
                slider(float(s.get("eyes.sensitivity", 1.0)), 0.6, 1.6, lambda v: s.set("eyes.sensitivity", round(v, 2))),
            )
        )
        card.lay.addWidget(
            SettingRow(
                tr("hand.hold"),
                tr("eyes.hold_d"),
                slider(float(s.get("eyes.hold_scale", 1.0)), 0.6, 2.0, lambda v: s.set("eyes.hold_scale", round(v, 2))),
            )
        )
        cal_row = QHBoxLayout()
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(label(tr("eyes.calibrate")))
        self.cal_status = label("", "Small", wrap=True)
        text.addWidget(self.cal_status)
        cal_row.addLayout(text, 1)
        reset = QPushButton(tr("eyes.cal_reset"))
        reset.setObjectName("Ghost")
        reset.clicked.connect(lambda: (s.set("eyes.calibration", {}), self.refresh_calibration()))
        cal_row.addWidget(reset)
        go = QPushButton(theme.icon("eye", theme.current().accent_text, 16), tr("eyes.calibrate"))
        go.setObjectName("Primary")
        go.clicked.connect(lambda: CalibrationDialog(self).exec())
        cal_row.addWidget(go)
        card.lay.addLayout(cal_row)
        self.refresh_calibration()

        card.lay.addWidget(label(tr("eyes.meter"), "SectionTitle"))
        card.lay.addWidget(label(tr("eyes.meter_d"), "Small", wrap=True))
        self.meter = EyeMeter()
        card.lay.addWidget(self.meter)
        card.lay.addWidget(label("💡 " + tr("eyes.tips"), "Small", wrap=True))
        return card

    def refresh_calibration(self) -> None:
        done = bool(self.settings.get("eyes.calibration"))
        self.cal_status.setText(tr("eyes.cal_status_done") if done else tr("eyes.cal_status_auto"))

    def _stats(self, st) -> None:
        if not self.isVisible():
            return
        self.meter.set_values(st.eye_open, st.eye_gaze, st.eyes_seen)
        for gid, card in self.cards.items():
            card.set_active(gid == st.eye_pose)
