from __future__ import annotations

from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget


class Page(QScrollArea):
    """Scrollable page with consistent margins. Subclasses fill ``self.body``."""

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.settings = ctx.settings
        self.controller = ctx.controller
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        inner.setObjectName("Root")
        self.body = QVBoxLayout(inner)
        self.body.setContentsMargins(32, 28, 32, 32)
        self.body.setSpacing(18)
        self.setWidget(inner)

    def on_shown(self) -> None:
        """Called when the page becomes visible."""

    def on_hidden(self) -> None:
        """Called when another page is selected."""
