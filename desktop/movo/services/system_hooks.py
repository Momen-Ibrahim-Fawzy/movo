"""Global shortcut and platform permission checks."""

from __future__ import annotations

import logging
import subprocess
import sys
from collections.abc import Callable
from typing import Optional

log = logging.getLogger(__name__)


class GlobalHotkey:
    """System-wide shortcut (pynput format, e.g. ``<ctrl>+<alt>+g``)."""

    def __init__(self, combo: str, callback: Callable[[], None]):
        self.combo = combo
        self.callback = callback
        self._listener = None

    def start(self) -> bool:
        from pynput import keyboard

        try:
            self._listener = keyboard.GlobalHotKeys({self.combo: self.callback})
            self._listener.daemon = True
            self._listener.start()
            return True
        except Exception as exc:
            log.warning("global hotkey %s unavailable: %s", self.combo, exc)
            self._listener = None
            return False

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None


def mac_accessibility_trusted() -> Optional[bool]:
    """True/False on macOS, None elsewhere."""
    if sys.platform != "darwin":
        return None
    try:
        import ctypes
        import ctypes.util

        lib = ctypes.cdll.LoadLibrary(ctypes.util.find_library("ApplicationServices"))
        lib.AXIsProcessTrusted.restype = ctypes.c_bool
        return bool(lib.AXIsProcessTrusted())
    except Exception:
        return None


def open_mac_privacy(pane: str = "Privacy_Accessibility") -> None:
    subprocess.Popen(["open", f"x-apple.systempreferences:com.apple.preference.security?{pane}"])


def is_wayland() -> bool:
    import os

    return sys.platform.startswith("linux") and (
        os.environ.get("XDG_SESSION_TYPE") == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))
    )
