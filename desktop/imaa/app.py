"""Application bootstrap."""

from __future__ import annotations

import argparse
import getpass
import logging
import logging.handlers
import sys

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from imaa import __app_name__, __version__
from imaa.config import Settings
from imaa.core.catalog import ACTIONS_BY_ID, ALL_GESTURES
from imaa.i18n import tr
from imaa.paths import asset, config_dir


def _setup_logging(debug: bool) -> None:
    handler = logging.handlers.RotatingFileHandler(config_dir() / "imaa.log", maxBytes=512_000, backupCount=1, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.addHandler(handler)
    if debug:
        root.addHandler(logging.StreamHandler())
    root.setLevel(logging.DEBUG if debug else logging.INFO)


def _single_instance(name: str) -> QLocalServer | None:
    """Returns a server if this is the first instance; otherwise wakes the running one and returns None."""
    sock = QLocalSocket()
    sock.connectToServer(name)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        return None
    QLocalServer.removeServer(name)
    server = QLocalServer()
    server.listen(name)
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="imaa", description="Gesture control for your computer.")
    parser.add_argument("--minimized", action="store_true", help="start hidden in the tray")
    parser.add_argument("--start", action="store_true", help="start detection immediately")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--version", action="version", version=f"{__app_name__} {__version__}")
    args, qt_args = parser.parse_known_args(argv if argv is not None else sys.argv[1:])

    _setup_logging(args.debug)
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication([sys.argv[0]] + qt_args)
    app.setApplicationName(__app_name__)
    app.setApplicationDisplayName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(__app_name__)
    app.setDesktopFileName("imaa")
    app.setWindowIcon(QIcon(str(asset("icons", "logo-256.png"))))
    app.setQuitOnLastWindowClosed(False)

    server = _single_instance(f"imaa-{getpass.getuser()}")
    if server is None:
        return 0

    from imaa.controller import Controller
    from imaa.ui.hud import Hud
    from imaa.ui.main_window import MainWindow, apply_appearance
    from imaa.ui.tray import Tray

    settings = Settings()
    apply_appearance(app, settings)
    controller = Controller(settings)
    window = MainWindow(settings, controller)
    tray = Tray(window, controller)
    window.tray = tray
    hud = Hud(settings)

    sound = None
    try:
        from PySide6.QtMultimedia import QSoundEffect

        sound = QSoundEffect()
        sound.setSource(QUrl.fromLocalFile(str(asset("sounds", "tick.wav"))))
        sound.setVolume(0.35)
    except Exception:
        sound = None

    def on_action(result) -> None:
        info = ACTIONS_BY_ID.get(result.action)
        if info is None:
            return
        text = tr(f"hud.{result.message}", **result.args) if result.message else tr(f"a.{result.action}")
        hud.show_message(info.emoji, text, result.ok)
        if sound is not None and settings.get("sounds"):
            sound.play()

    def on_gesture(ev, action) -> None:
        if controller.dispatcher.practice:
            g = ALL_GESTURES.get(ev.gesture)
            hud.show_message(g.emoji if g else "✋", tr("hud.practice", gesture=tr(f"g.{ev.gesture}"), action=tr(f"a.{action}")))

    def on_state(state: str) -> None:
        if state == "paused":
            hud.show_message("⏸️", tr("hud.paused"))
        elif state.startswith("error:"):
            hud.show_message("⚠️", tr(f"error.{state.split(':', 1)[1]}"), ok=False, ms=3000)
            if not window.isVisible():
                window.show_and_raise()

    controller.action_done.connect(on_action)
    controller.gesture_seen.connect(on_gesture)
    controller.state_changed.connect(on_state)

    def wake() -> None:
        conn = server.nextPendingConnection()
        if conn is not None:
            conn.readyRead.connect(lambda: (conn.readAll(), window.show_and_raise()))

    server.newConnection.connect(wake)

    def scheme_changed(*_):
        if settings.get("theme", "system") == "system":
            window.rebuild_soon()

    try:
        app.styleHints().colorSchemeChanged.connect(scheme_changed)
    except AttributeError:
        pass

    controller.start_services()
    minimized = args.minimized or bool(settings.get("start_minimized"))
    if not minimized or not tray.available:
        window.show()

    def after_show() -> None:
        start = args.start or bool(settings.get("start_detection_on_launch"))
        if not settings.get("first_run_done"):
            from imaa.ui.onboarding import Onboarding

            window.show_and_raise()
            dlg = Onboarding(window)
            dlg.exec()
            settings.set("first_run_done", True)
            start = start or dlg.start_now
        if start:
            controller.start()

    QTimer.singleShot(150, after_show)
    app.aboutToQuit.connect(controller.shutdown)
    return app.exec()
