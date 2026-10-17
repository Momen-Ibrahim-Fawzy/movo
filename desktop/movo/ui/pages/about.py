from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout

from movo import __version__
from movo.i18n import tr
from movo.ui.pages import Page
from movo.ui.widgets import Card, LogoMark, label, page_header


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

        guide = QPushButton(tr("home.how_to"))
        guide.setObjectName("Primary")
        guide.clicked.connect(lambda: self.ctx.go("guide"))
        hero.lay.addWidget(guide, 0, Qt.AlignLeft)

        dev = Card()
        dev.lay.addWidget(label(tr("about.developer"), "SectionTitle"))
        dev.lay.addWidget(label(tr("about.dev_name")))
        dev.lay.addWidget(label(tr("about.dev_role"), "Muted", wrap=True))
        contact = label(
            '<a href="mailto:momenibrahimfawzy982000@gmail.com">momenibrahimfawzy982000@gmail.com</a><br>'
            '<span dir="ltr">+966 55 706 8834 · +20 10 9638 8123</span><br>'
            '<a href="https://www.linkedin.com/in/momen-ibrahim-fawzy-0b067a1b8/">LinkedIn</a> · <a href="https://github.com/Momen-Ibrahim-Fawzy">GitHub</a> · <a href="https://orcid.org/0009-0001-7287-0705">ORCID</a> · <a href="https://scholar.google.com/citations?user=PV3WxD4AAAAJ&hl=en">Google Scholar</a>',
            wrap=True,
        )
        contact.setTextFormat(Qt.RichText)
        contact.setTextInteractionFlags(Qt.TextBrowserInteraction)
        contact.setOpenExternalLinks(True)
        dev.lay.addWidget(contact)
        self.body.addWidget(dev)

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
