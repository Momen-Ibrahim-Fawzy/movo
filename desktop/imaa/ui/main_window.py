from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from imaa.i18n import is_rtl, set_language, tr
from imaa.paths import asset
from imaa.services.system_hooks import is_wayland, mac_accessibility_trusted, open_mac_privacy
from imaa.ui import theme
from imaa.ui.pages.about import AboutPage
from imaa.ui.pages.gestures import HandPage, HeadPage
from imaa.ui.pages.guide import GuidePage
from imaa.ui.pages.home import HomePage
from imaa.ui.pages.profiles import ProfilesPage
from imaa.ui.pages.settings import SettingsPage
from imaa.ui.widgets import LogoMark, StatusDot, label

NAV = (
    ("home", "home", HomePage),
    ("hand", "hand", HandPage),
    ("head", "face", HeadPage),
    ("profiles", "layers", ProfilesPage),
    ("guide", "book", GuidePage),
    ("settings", "settings", SettingsPage),
    ("about", "info", AboutPage),
)


def apply_appearance(app: QApplication, settings) -> None:
    set_language(settings.get("language", "system"))
    theme.set_current(theme.resolve(settings.get("theme", "system")))
    app.setLayoutDirection(Qt.RightToLeft if is_rtl() else Qt.LeftToRight)
    app.setFont(theme.app_font(is_rtl()))
    app.setStyleSheet(theme.stylesheet(theme.current()))


class MainWindow(QMainWindow):
    def __init__(self, settings, controller):
        super().__init__()
        self.settings = settings
        self.controller = controller
        self.quitting = False
        self._current = "home"
        self.setWindowIcon(QIcon(str(asset("icons", "logo-256.png"))))
        self.resize(1120, 760)
        self.setMinimumSize(920, 620)
        self._rebuild_timer = QTimer(self, singleShot=True, interval=0)
        self._rebuild_timer.timeout.connect(self.rebuild)
        self.build()
        controller.state_changed.connect(self._on_state)
        self._on_state(controller.state)

    # ------------------------------------------------------------------ building
    def build(self) -> None:
        pal = theme.current()
        self.setWindowTitle(f"{tr('app.name')} — {tr('app.tagline_short')}")
        root = QWidget()
        root.setObjectName("Root")
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # sidebar
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(232)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(16, 20, 16, 16)
        sl.setSpacing(4)
        brand = QHBoxLayout()
        brand.setSpacing(10)
        brand.addWidget(LogoMark(38))
        bt = QVBoxLayout()
        bt.setSpacing(0)
        bt.addWidget(label(tr("app.name"), "Brand"))
        bt.addWidget(label(tr("app.tagline_short"), "BrandSub"))
        brand.addLayout(bt, 1)
        sl.addLayout(brand)
        sl.addSpacing(18)

        self.stack = QStackedWidget()
        self.pages = {}
        self.nav_buttons = {}
        group = QButtonGroup(self)
        group.setExclusive(True)
        for key, icon_name, cls in NAV:
            btn = QPushButton("  " + tr(f"nav.{key}").replace("&", "&&"))
            btn.setObjectName("NavItem")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setIcon(theme.icon(icon_name, pal.text_muted, 20))
            btn.setIconSize(QSize(20, 20))
            btn.clicked.connect(lambda _=False, k=key: self.go(k))
            group.addButton(btn)
            sl.addWidget(btn)
            self.nav_buttons[key] = (btn, icon_name)
            page = cls(self)
            self.pages[key] = page
            self.stack.addWidget(page)
        sl.addStretch(1)

        # mini status + quick switches at the bottom of the sidebar
        status = QHBoxLayout()
        self.side_dot = StatusDot(pal.text_muted, 8)
        self.side_status = label("", "Muted")
        status.addWidget(self.side_dot)
        status.addWidget(self.side_status, 1)
        sl.addLayout(status)
        quick = QHBoxLayout()
        theme_btn = QPushButton()
        theme_btn.setObjectName("Ghost")
        theme_btn.setIcon(theme.icon("moon" if pal.name == "light" else "sun", pal.text_muted, 18))
        theme_btn.setToolTip(tr("settings.theme"))
        theme_btn.clicked.connect(self._toggle_theme)
        lang_btn = QPushButton("ع" if not is_rtl() else "EN")
        lang_btn.setObjectName("Ghost")
        lang_btn.setToolTip(tr("settings.language"))
        lang_btn.clicked.connect(self._toggle_language)
        quick.addWidget(theme_btn)
        quick.addWidget(lang_btn)
        quick.addStretch(1)
        sl.addLayout(quick)

        divider = QFrame()
        divider.setObjectName("SidebarDivider")
        outer.addWidget(side)
        outer.addWidget(divider)

        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        banner = self._permission_banner()
        if banner:
            content.addWidget(banner)
        content.addWidget(self.stack, 1)
        outer.addLayout(content, 1)
        self.setCentralWidget(root)
        self.go(self._current)

    def _permission_banner(self):
        msg = None
        if mac_accessibility_trusted() is False:
            msg = tr("banner.mac_accessibility")
        elif is_wayland():
            msg = tr("banner.wayland")
        if not msg:
            return None
        w = QWidget()
        w.setObjectName("WarnBanner")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.addWidget(label(msg, wrap=True), 1)
        if mac_accessibility_trusted() is False:
            b = QPushButton(tr("banner.open_settings"))
            b.clicked.connect(open_mac_privacy)
            lay.addWidget(b)
        holder = QWidget()
        hl = QVBoxLayout(holder)
        hl.setContentsMargins(24, 16, 24, 0)
        hl.addWidget(w)
        return holder

    def rebuild_soon(self) -> None:
        self._rebuild_timer.start()

    def rebuild(self) -> None:
        apply_appearance(QApplication.instance(), self.settings)
        old = self.centralWidget()
        self.build()
        if old is not None:
            old.deleteLater()
        self._on_state(self.controller.state)
        tray = getattr(self, "tray", None)
        if tray:
            tray.retranslate()

    # ------------------------------------------------------------------ navigation
    def go(self, key: str) -> None:
        pal = theme.current()
        prev = self.pages.get(self._current)
        if prev is not None and prev is not self.pages.get(key):
            prev.on_hidden()
        self._current = key
        for k, (btn, icon_name) in self.nav_buttons.items():
            btn.setChecked(k == key)
            btn.setIcon(theme.icon(icon_name, pal.accent if k == key else pal.text_muted, 20))
        page = self.pages[key]
        self.stack.setCurrentWidget(page)
        if self.isVisible():
            page.on_shown()

    def _toggle_theme(self) -> None:
        self.settings.set("theme", "light" if theme.current().name == "dark" else "dark")
        self.rebuild_soon()

    def _toggle_language(self) -> None:
        self.settings.set("language", "en" if is_rtl() else "ar")
        self.rebuild_soon()

    def _on_state(self, state: str) -> None:
        pal = theme.current()
        key = "error" if state.startswith("error:") else state
        self.side_status.setText(tr(f"state.{key}"))
        color = {"running": pal.success, "paused": pal.warning, "starting": pal.accent, "error": pal.danger}.get(
            key, pal.text_muted
        )
        self.side_dot.set_color(color)

    # ------------------------------------------------------------------ window events
    def showEvent(self, e) -> None:
        super().showEvent(e)
        self.pages[self._current].on_shown()

    def hideEvent(self, e) -> None:
        super().hideEvent(e)
        self.controller.set_preview_enabled(False)

    def changeEvent(self, e) -> None:
        super().changeEvent(e)
        if e.type() == e.Type.WindowStateChange and self.isMinimized():
            self.controller.set_preview_enabled(False)
        elif e.type() == e.Type.WindowStateChange and self.isVisible():
            self.pages[self._current].on_shown()

    def closeEvent(self, e: QCloseEvent) -> None:
        tray = getattr(self, "tray", None)
        if not self.quitting and self.settings.get("close_to_tray", True) and tray is not None and tray.available:
            e.ignore()
            self.hide()
            tray.notify_hidden()
            return
        e.accept()
        QApplication.instance().quit()

    def show_and_raise(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()
