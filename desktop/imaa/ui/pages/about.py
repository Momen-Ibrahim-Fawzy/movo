from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout

from imaa import __version__
from imaa.core.catalog import DEFAULT_BINDINGS, HAND_GESTURES, HEAD_GESTURES
from imaa.i18n import tr
from imaa.ui.pages import Page
from imaa.ui.widgets import Card, LogoMark, label, page_header


class AboutPage(Page):
    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self.body.addWidget(page_header(tr("about.title"), ""))

        hero = Card()
        row = QHBoxLayout()
        row.addWidget(LogoMark(88))
        text = QVBoxLayout()
        name = label(tr("app.name"), "PageTitle")
        text.addWidget(name)
        text.addWidget(label(tr("app.tagline"), "Muted", wrap=True))
        text.addWidget(label(tr("about.version", version=__version__), "Small"))
        row.addLayout(text, 1)
        hero.lay.addLayout(row)
        hero.lay.addWidget(label(tr("about.meaning"), wrap=True))
        self.body.addWidget(hero)

        sheet = Card()
        sheet.lay.addWidget(label(tr("about.cheatsheet"), "SectionTitle"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(6)
        gestures = [g for g in HAND_GESTURES + HEAD_GESTURES if DEFAULT_BINDINGS.get(g.id, "none") != "none"]
        half = (len(gestures) + 1) // 2
        for i, g in enumerate(gestures):
            col = (i // half) * 2
            r = i % half
            grid.addWidget(label(f"{g.emoji}  {tr(f'g.{g.id}')}"), r, col)
            grid.addWidget(label(tr(f"a.{DEFAULT_BINDINGS[g.id]}"), "Muted"), r, col + 1)
        sheet.lay.addLayout(grid)
        self.body.addWidget(sheet)

        tips = Card()
        tips.lay.addWidget(label(tr("about.tips"), "SectionTitle"))
        for i in range(1, 7):
            tips.lay.addWidget(label(f"•  {tr(f'about.tip{i}')}", wrap=True))
        self.body.addWidget(tips)

        privacy = Card()
        privacy.lay.addWidget(label(tr("settings.privacy"), "SectionTitle"))
        privacy.lay.addWidget(label(tr("settings.privacy_text"), wrap=True))
        self.body.addWidget(privacy)

        credits = Card()
        credits.lay.addWidget(label(tr("about.credits"), "SectionTitle"))
        c = label(tr("about.credits_text"), "Muted", wrap=True)
        c.setTextInteractionFlags(Qt.TextBrowserInteraction)
        c.setOpenExternalLinks(True)
        credits.lay.addWidget(c)
        credits.lay.addWidget(label(tr("about.copyright"), "Small"))
        self.body.addWidget(credits)
        self.body.addStretch(1)
