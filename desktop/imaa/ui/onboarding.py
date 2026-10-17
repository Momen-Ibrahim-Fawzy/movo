"""First-run welcome: language & theme → privacy & camera → gesture tour."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QDialog, QGridLayout, QHBoxLayout, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from imaa.core.catalog import ALL_GESTURES, DEFAULT_BINDINGS
from imaa.i18n import LANGUAGES, tr
from imaa.ui.widgets import Card, LogoMark, SettingRow, combo, label

TOUR = ("thumb_up", "point_right", "pinch", "index_up_move_up", "pinch_drag_up", "swipe_right", "victory", "call", "fist", "rock")


class Onboarding(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.settings = window.settings
        self.setWindowTitle(tr("app.name"))
        self.setModal(True)
        self.setMinimumSize(720, 560)
        self.start_now = True
        self._build(0)

    def _build(self, index: int) -> None:
        if self.layout() is not None:
            QWidget().setLayout(self.layout())  # drop the old layout
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 28, 28, 24)
        lay.setSpacing(16)
        self.stack = QStackedWidget()
        self.stack.addWidget(self._page_welcome())
        self.stack.addWidget(self._page_privacy())
        self.stack.addWidget(self._page_tour())
        lay.addWidget(self.stack, 1)

        nav = QHBoxLayout()
        self.step = label("", "Small")
        nav.addWidget(self.step)
        nav.addStretch(1)
        self.back = QPushButton(tr("onb.back"))
        self.back.clicked.connect(lambda: self._go(self.stack.currentIndex() - 1))
        self.next = QPushButton(tr("onb.next"))
        self.next.setObjectName("Primary")
        self.next.clicked.connect(self._next)
        nav.addWidget(self.back)
        nav.addWidget(self.next)
        lay.addLayout(nav)
        self._go(index)

    def _page_welcome(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(14)
        lay.addWidget(LogoMark(84), 0, Qt.AlignHCenter)
        t = label(tr("onb.welcome"), "PageTitle")
        t.setAlignment(Qt.AlignHCenter)
        lay.addWidget(t)
        sub = label(tr("onb.welcome_d"), "PageSubtitle", wrap=True)
        sub.setAlignment(Qt.AlignHCenter)
        lay.addWidget(sub)
        card = Card(shadow=False)
        card.lay.addWidget(
            SettingRow(
                tr("settings.language"),
                "",
                combo(
                    [("system", tr("settings.system"))] + list(LANGUAGES.items()),
                    self.settings.get("language"),
                    self._set_language,
                ),
            )
        )
        card.lay.addWidget(
            SettingRow(
                tr("settings.theme"),
                "",
                combo(
                    [("system", tr("settings.system")), ("light", tr("settings.light")), ("dark", tr("settings.dark"))],
                    self.settings.get("theme"),
                    self._set_theme,
                ),
            )
        )
        lay.addWidget(card)
        lay.addStretch(1)
        return w

    def _page_privacy(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)
        lay.addWidget(label("🔒", "Emoji"), 0, Qt.AlignHCenter)
        t = label(tr("onb.privacy"), "PageTitle")
        t.setAlignment(Qt.AlignHCenter)
        lay.addWidget(t)
        card = Card(shadow=False)
        for i in range(1, 5):
            card.lay.addWidget(label(f"✓  {tr(f'onb.privacy{i}')}", wrap=True))
        lay.addWidget(card)
        tips = Card(shadow=False)
        tips.lay.addWidget(label(tr("onb.camera_tips"), "SectionTitle"))
        tips.lay.addWidget(label(tr("onb.camera_tips_d"), "Muted", wrap=True))
        if sys.platform == "darwin":
            tips.lay.addWidget(label(tr("onb.mac"), wrap=True))
        lay.addWidget(tips)
        lay.addStretch(1)
        return w

    def _page_tour(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)
        lay.addWidget(label(tr("onb.tour"), "PageTitle"))
        lay.addWidget(label(tr("onb.tour_d"), "PageSubtitle", wrap=True))
        card = Card(shadow=False)
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(8)
        for i, gid in enumerate(TOUR):
            g = ALL_GESTURES[gid]
            r, c = i // 2, (i % 2) * 2
            grid.addWidget(label(f"{g.emoji}  {tr(f'g.{gid}')}"), r, c)
            grid.addWidget(label(tr(f"a.{DEFAULT_BINDINGS[gid]}"), "Muted"), r, c + 1)
        card.lay.addLayout(grid)
        lay.addWidget(card)
        lay.addWidget(label(tr("onb.tour_head"), "Muted", wrap=True))
        self.start_box = QCheckBox(tr("onb.start_now"))
        self.start_box.setChecked(True)
        lay.addWidget(self.start_box)
        lay.addStretch(1)
        return w

    def _go(self, i: int) -> None:
        i = max(0, min(2, i))
        self.stack.setCurrentIndex(i)
        self.back.setVisible(i > 0)
        self.next.setText(tr("onb.finish") if i == 2 else tr("onb.next"))
        self.step.setText(tr("onb.step", n=i + 1, total=3))

    def _next(self) -> None:
        if self.stack.currentIndex() == 2:
            self.start_now = self.start_box.isChecked()
            self.settings.set("first_run_done", True)
            self.accept()
        else:
            self._go(self.stack.currentIndex() + 1)

    def _set_language(self, v: str) -> None:
        self.settings.set("language", v)
        self._restyle()

    def _set_theme(self, v: str) -> None:
        self.settings.set("theme", v)
        self._restyle()

    def _restyle(self) -> None:
        self.window.rebuild()
        self.setWindowTitle(tr("app.name"))
        self._build(0)
