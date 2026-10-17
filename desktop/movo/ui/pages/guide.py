"""In-app "How to use" guide: numbered steps, the gesture cheat sheet and tips."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from movo.core.catalog import DEFAULT_BINDINGS, EYE_GESTURES, HAND_GESTURES, HEAD_GESTURES
from movo.i18n import tr
from movo.ui import theme
from movo.ui.pages import Page
from movo.ui.widgets import Card, label, page_header

STEPS = (
    ("guide.s1", "guide.s1_d", "home"),
    ("guide.s2", "guide.s2_d", None),
    ("guide.s3", "guide.s3_d", "home"),
    ("guide.s4", "guide.s4_d", None),
    ("guide.s5", "guide.s5_d", "hand"),
    ("guide.s6", "guide.s6_d", "head"),
    ("guide.s9", "guide.s9_d", "eyes"),
    ("guide.s7", "guide.s7_d", "profiles"),
    ("guide.s8", "guide.s8_d", "settings"),
)


class StepBadge(QLabel):
    def __init__(self, n: int):
        super().__init__(str(n))
        p = theme.current()
        self.setFixedSize(32, 32)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"background:{p.accent_soft}; color:{p.accent}; border-radius:16px; font-weight:700;")


class GuidePage(Page):
    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self.body.addWidget(page_header(tr("guide.title"), tr("guide.subtitle")))

        steps = Card()
        for i, (title, desc, target) in enumerate(STEPS, start=1):
            row = QHBoxLayout()
            row.setSpacing(14)
            row.addWidget(StepBadge(i), 0, Qt.AlignTop)
            text = QVBoxLayout()
            text.setSpacing(2)
            text.addWidget(label(tr(title), "SectionTitle"))
            text.addWidget(label(tr(desc), "Muted", wrap=True))
            row.addLayout(text, 1)
            if target:
                go = QPushButton(tr("guide.open"))
                go.setObjectName("Ghost")
                go.clicked.connect(lambda _=False, k=target: self.ctx.go(k))
                row.addWidget(go, 0, Qt.AlignTop)
            steps.lay.addLayout(row)
        self.body.addWidget(steps)

        for title, gestures in (
            ("guide.hand_sheet", HAND_GESTURES),
            ("guide.head_sheet", HEAD_GESTURES),
            ("guide.eye_sheet", EYE_GESTURES),
        ):
            sheet = Card()
            sheet.lay.addWidget(label(tr(title), "SectionTitle"))
            grid = QGridLayout()
            grid.setHorizontalSpacing(18)
            grid.setVerticalSpacing(10)
            for r, g in enumerate(gestures):
                emoji = label(g.emoji)
                emoji.setStyleSheet("font-size: 18pt;")
                grid.addWidget(emoji, r, 0)
                name = QVBoxLayout()
                name.setSpacing(0)
                name.addWidget(label(tr(f"g.{g.id}")))
                name.addWidget(label(tr(f"g.{g.id}.how"), "Small", wrap=True))
                grid.addLayout(name, r, 1)
                action = DEFAULT_BINDINGS.get(g.id, "none")
                grid.addWidget(label("→  " + tr(f"a.{action}"), "Muted"), r, 2)
            grid.setColumnStretch(1, 1)
            sheet.lay.addLayout(grid)
            self.body.addWidget(sheet)

        tips = Card()
        tips.lay.addWidget(label(tr("about.tips"), "SectionTitle"))
        for i in range(1, 7):
            tips.lay.addWidget(label(f"•  {tr(f'about.tip{i}')}", wrap=True))
        self.body.addWidget(tips)
        self.body.addStretch(1)
