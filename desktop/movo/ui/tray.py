from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from movo.i18n import tr
from movo.paths import asset


class Tray:
    def __init__(self, window, controller):
        self.window = window
        self.controller = controller
        self.available = QSystemTrayIcon.isSystemTrayAvailable()
        self._hidden_notice_shown = False
        self.icon_on = QIcon(str(asset("icons", "tray-on.png")))
        self.icon_off = QIcon(str(asset("icons", "tray-off.png")))
        self.tray = QSystemTrayIcon(self.icon_off)
        self.menu = QMenu()
        self.a_toggle = QAction(self.menu)
        self.a_pause = QAction(self.menu)
        self.a_show = QAction(self.menu)
        self.a_quit = QAction(self.menu)
        self.a_toggle.triggered.connect(controller.toggle)
        self.a_pause.triggered.connect(controller.toggle_pause)
        self.a_show.triggered.connect(window.show_and_raise)
        self.a_quit.triggered.connect(self._quit)
        for a in (self.a_toggle, self.a_pause):
            self.menu.addAction(a)
        self.menu.addSeparator()
        self.menu.addAction(self.a_show)
        self.menu.addAction(self.a_quit)
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._activated)
        controller.state_changed.connect(self._state)
        self.retranslate()
        if self.available:
            self.tray.show()

    def retranslate(self) -> None:
        self.a_show.setText(tr("tray.show"))
        self.a_quit.setText(tr("tray.quit"))
        self._state(self.controller.state)

    def _state(self, state: str) -> None:
        running = state in ("running", "paused", "starting")
        self.a_toggle.setText(tr("tray.stop") if running else tr("tray.start"))
        self.a_pause.setText(tr("tray.resume") if state == "paused" else tr("tray.pause"))
        self.a_pause.setEnabled(running)
        self.tray.setIcon(self.icon_on if state in ("running", "starting") else self.icon_off)
        key = "error" if state.startswith("error:") else state
        self.tray.setToolTip(f"{tr('app.name')} — {tr(f'state.{key}')}")

    def _activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.window.isVisible() and not self.window.isMinimized():
                self.window.hide()
            else:
                self.window.show_and_raise()

    def notify_hidden(self) -> None:
        if not self._hidden_notice_shown and self.available:
            self._hidden_notice_shown = True
            self.tray.showMessage(tr("app.name"), tr("tray.hidden"), self.icon_on, 4000)

    def _quit(self) -> None:
        self.window.quitting = True
        QApplication.instance().quit()
