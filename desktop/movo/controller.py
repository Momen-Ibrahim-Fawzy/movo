"""Application controller: owns the engine, the action executor and the local services, and exposes Qt signals
for the UI. Engine/executor callbacks arrive on background threads and are forwarded through queued signals."""

from __future__ import annotations

import logging
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QCursor, QGuiApplication

from movo.actions import ActionExecutor, ActionResult
from movo.config import Settings
from movo.core.dispatcher import Dispatcher
from movo.core.engine import Engine, EngineCallbacks
from movo.core.events import GestureEvent
from movo.paths import default_screenshot_dir
from movo.services import active_window, autostart
from movo.services.browser_bridge import BrowserBridge
from movo.services.remote_server import RemoteServer
from movo.services.system_hooks import GlobalHotkey

log = logging.getLogger(__name__)


class Controller(QObject):
    state_changed = Signal(str)  # stopped | starting | running | paused | error:<key>
    stats_changed = Signal(object)
    preview_frame = Signal(object)
    action_done = Signal(object)
    gesture_seen = Signal(object, str)
    profile_changed = Signal(str)  # effective profile id
    integrations_changed = Signal()

    _sig_state = Signal(str)
    _sig_screenshot = Signal()
    _sig_pause = Signal()
    _sig_pointer_button = Signal(str)
    _sig_active_app = Signal(str)
    _sig_start = Signal()

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.executor = ActionExecutor(on_result=self.action_done.emit)
        self.dispatcher = Dispatcher(settings, self.executor, on_gesture=lambda e, a: self.gesture_seen.emit(e, a))
        self.engine = Engine(
            settings,
            self.dispatcher,
            EngineCallbacks(
                state=self._sig_state.emit,
                preview=self.preview_frame.emit,
                stats=self.stats_changed.emit,
                pointer_move=self._pointer_move,
                pointer_button=self._sig_pointer_button.emit,
            ),
        )
        self._state = "stopped"
        self.effective_profile = settings.get("active_profile")
        self.active_app: Optional[str] = None
        self.bridge: Optional[BrowserBridge] = None
        self.remote: Optional[RemoteServer] = None
        self.hotkey: Optional[GlobalHotkey] = None
        self._screen_geo = (0, 0, 1920, 1080)
        self._scale = 1.0

        self._sig_state.connect(self._on_engine_state, Qt.QueuedConnection)
        self._sig_screenshot.connect(self._take_screenshot, Qt.QueuedConnection)
        self._sig_pause.connect(self.toggle_pause, Qt.QueuedConnection)
        self._sig_pointer_button.connect(self._pointer_button, Qt.QueuedConnection)
        self._sig_active_app.connect(self._on_active_app, Qt.QueuedConnection)
        self._sig_start.connect(self.start, Qt.QueuedConnection)

        self.executor.hooks["screenshot"] = self._hook_screenshot
        self.executor.hooks["pause_control"] = self._hook_pause
        self.executor.hooks["skip_ad_bridge"] = lambda: self.bridge.request_skip() if self.bridge else None

        settings.on_change(self._on_setting)
        self._update_screen()
        self._watch_stop = threading.Event()
        threading.Thread(target=self._watch_active_app, name="movo-active-app", daemon=True).start()

    # ------------------------------------------------------------------ lifecycle
    def start_services(self) -> None:
        if self.settings.get("browser_bridge.enabled", True):
            self._start_bridge()
        if self.settings.get("remote.enabled", False):
            self._start_remote()
        self._start_hotkey()
        if self.settings.get("launch_at_login"):
            autostart.set_enabled(True)  # refresh the path after updates

    def shutdown(self) -> None:
        self._watch_stop.set()
        self.engine.stop()
        self.executor.close()
        if self.bridge:
            self.bridge.stop()
        if self.remote:
            self.remote.stop()
        if self.hotkey:
            self.hotkey.stop()

    # ------------------------------------------------------------------ state
    @property
    def state(self) -> str:
        return self._state

    @property
    def running(self) -> bool:
        return self._state in ("running", "paused", "starting")

    @property
    def paused(self) -> bool:
        return self.dispatcher.paused

    def _set_state(self, state: str) -> None:
        self._state = state
        self.state_changed.emit(state)

    @Slot(str)
    def _on_engine_state(self, state: str) -> None:
        if state == "running" and self.dispatcher.paused:
            state = "paused"
        if state == "stopped" or state.startswith("error:"):
            self.dispatcher.paused = False
        self._set_state(state)

    def start(self) -> None:
        if self.engine.alive:
            return
        self._update_screen()
        self._set_state("starting")
        self.engine.start()

    def stop(self) -> None:
        self.engine.stop(wait=False)
        if self._state == "starting":
            self._set_state("stopped")

    def toggle(self) -> None:
        self.stop() if self.running else self.start()

    def set_paused(self, paused: bool) -> None:
        self.dispatcher.paused = paused
        if self._state in ("running", "paused"):
            self._set_state("paused" if paused else "running")

    @Slot()
    def toggle_pause(self) -> None:
        if not self.running:
            self.start()
            return
        self.set_paused(not self.dispatcher.paused)

    def set_practice(self, on: bool) -> None:
        self.dispatcher.practice = on

    def set_preview_enabled(self, on: bool) -> None:
        self.engine.preview_enabled = on

    def restart_engine(self) -> None:
        if not self.running:
            return

        def again():
            # Joining guarantees the old engine's "stopped" signal is queued before the new start.
            self.engine.join(3)
            self._sig_start.emit()

        self.engine.stop(wait=False)
        threading.Thread(target=again, daemon=True).start()

    # ------------------------------------------------------------------ settings reactions
    def _on_setting(self, key: str) -> None:
        if key in ("camera", "camera.index", "camera.width", "camera.height"):
            QTimer.singleShot(0, self.restart_engine)
        elif key == "head.mode":
            self.engine.face_mode_changed()
        elif key in ("browser_bridge.enabled", "browser_bridge.port"):
            QTimer.singleShot(0, self._restart_bridge)
        elif key in ("remote.enabled", "remote.port", "remote.code"):
            QTimer.singleShot(0, self._restart_remote)
        elif key == "hotkey_pause":
            QTimer.singleShot(0, self._start_hotkey)
        elif key == "launch_at_login":
            autostart.set_enabled(bool(self.settings.get("launch_at_login")))
        elif key in ("active_profile", "auto_profiles", "*") or key.startswith("profiles"):
            QTimer.singleShot(0, lambda: self._on_active_app(self.active_app or ""))

    # ------------------------------------------------------------------ profiles
    def _watch_active_app(self) -> None:
        last = None
        while not self._watch_stop.wait(1.2):
            if not self.settings.get("auto_profiles", True):
                continue
            app = active_window.active_app()
            if app and app != last and not app.startswith("movo"):
                last = app
                self._sig_active_app.emit(app)

    @Slot(str)
    def _on_active_app(self, app: str) -> None:
        self.active_app = app or self.active_app
        manual = self.settings.get("active_profile")
        profile = manual
        if self.settings.get("auto_profiles", True):
            profile = active_window.match_profile(self.active_app, self.settings.get("profiles", {})) or manual
        self.dispatcher.profile = profile
        if profile != self.effective_profile:
            self.effective_profile = profile
            self.profile_changed.emit(profile)

    # ------------------------------------------------------------------ hooks (worker thread)
    def _hook_screenshot(self) -> None:
        self._sig_screenshot.emit()
        return None

    def _hook_pause(self) -> ActionResult:
        will_pause = not self.dispatcher.paused
        self._sig_pause.emit()
        return ActionResult("pause_control", True, "paused" if will_pause else "resumed")

    @Slot()
    def _take_screenshot(self) -> None:
        folder = Path(self.settings.get("screenshots.folder") or default_screenshot_dir())
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            folder = default_screenshot_dir()
            folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"Movo {datetime.now():%Y-%m-%d %H-%M-%S}.png"
        ok = False
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        pix = screen.grabWindow(0) if screen else None
        if pix is not None and not pix.isNull() and not _looks_blank(pix):
            ok = pix.save(str(path), "PNG")
            if ok and self.settings.get("screenshots.copy_to_clipboard", True):
                QGuiApplication.clipboard().setPixmap(pix)
        if not ok:
            ok = _os_screenshot(path)
        self.action_done.emit(
            ActionResult("screenshot", ok, "screenshot_saved" if ok else "screenshot_failed", {"path": str(path)})
        )

    # ------------------------------------------------------------------ pointer
    def _update_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen:
            g = screen.geometry()
            self._scale = screen.devicePixelRatio() if sys.platform == "win32" else 1.0
            self._screen_geo = (g.x(), g.y(), g.width(), g.height())

    def _pointer_move(self, x: float, y: float, relative: bool) -> None:
        from movo.actions import keys

        if self.dispatcher.paused or self.dispatcher.practice:
            return
        if relative:
            keys.move_by(x * self._scale, y * self._scale)
        else:
            gx, gy, gw, gh = self._screen_geo
            keys.move_to(int((gx + x * gw) * self._scale), int((gy + y * gh) * self._scale))

    @Slot(str)
    def _pointer_button(self, button: str) -> None:
        from movo.actions import keys

        if self.dispatcher.paused or self.dispatcher.practice:
            if button != "up":
                return
        if button in ("left", "right"):
            keys.click(button)
        elif button == "down":
            keys.mouse_down()
        elif button == "up":
            keys.mouse_up()

    # ------------------------------------------------------------------ services
    def _start_bridge(self) -> None:
        self.bridge = BrowserBridge(int(self.settings.get("browser_bridge.port", 47812)), on_change=self._integration_changed)
        if not self.bridge.start():
            self.bridge = None
        self.integrations_changed.emit()

    @Slot()
    def _restart_bridge(self) -> None:
        if self.bridge:
            self.bridge.stop()
            self.bridge = None
        if self.settings.get("browser_bridge.enabled", True):
            self._start_bridge()
        self.integrations_changed.emit()

    def _start_remote(self) -> None:
        self.remote = RemoteServer(
            int(self.settings.get("remote.port", 47813)),
            str(self.settings.get("remote.code")),
            on_event=self.dispatcher.handle,
            on_action=self.dispatcher.handle_action,
            on_change=self._integration_changed,
        )
        if not self.remote.start():
            self.remote = None
        self.integrations_changed.emit()

    @Slot()
    def _restart_remote(self) -> None:
        if self.remote:
            self.remote.stop()
            self.remote = None
        if self.settings.get("remote.enabled", False):
            self._start_remote()
        self.integrations_changed.emit()

    def _integration_changed(self, *_):
        self.integrations_changed.emit()

    @Slot()
    def _start_hotkey(self) -> None:
        if self.hotkey:
            self.hotkey.stop()
        combo = self.settings.get("hotkey_pause", "")
        self.hotkey = None
        if combo:
            hk = GlobalHotkey(combo, self._sig_pause.emit)
            if hk.start():
                self.hotkey = hk

    def handle_remote_event(self, ev: GestureEvent) -> None:
        self.dispatcher.handle(ev)


def _looks_blank(pix) -> bool:
    """Wayland and missing macOS permission give black images."""
    img = pix.toImage().scaled(16, 16)
    return all(img.pixelColor(x, y).value() < 3 for x in range(16) for y in range(16))


def _os_screenshot(path: Path) -> bool:
    import shutil
    import subprocess

    candidates = []
    if sys.platform == "darwin":
        candidates.append(["screencapture", "-x", str(path)])
    elif sys.platform.startswith("linux"):
        candidates += [["gnome-screenshot", "-f", str(path)], ["spectacle", "-b", "-n", "-o", str(path)], ["grim", str(path)]]
    for cmd in candidates:
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, timeout=10, check=True)
                return path.exists()
            except (OSError, subprocess.SubprocessError):
                continue
    return False
