"""Name of the application in front, used for automatic profile switching. Only the process name is read."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Optional


def active_app() -> Optional[str]:
    try:
        if sys.platform == "win32":
            return _windows()
        if sys.platform == "darwin":
            return _mac()
        return _linux()
    except Exception:
        return None


def _windows() -> Optional[str]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    handle = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return os.path.splitext(os.path.basename(buf.value))[0].lower()
    finally:
        kernel32.CloseHandle(handle)
    return None


def _mac() -> Optional[str]:
    try:
        from AppKit import NSWorkspace  # type: ignore[import-not-found]

        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        return str(app.localizedName()).lower() if app else None
    except ImportError:
        pass
    out = subprocess.run(
        ["osascript", "-e", 'tell application "System Events" to get name of first process whose frontmost is true'],
        capture_output=True,
        text=True,
        timeout=2,
    )
    return out.stdout.strip().lower() or None


def _linux() -> Optional[str]:
    if not shutil.which("xprop"):
        return None
    out = subprocess.run(["xprop", "-root", "_NET_ACTIVE_WINDOW"], capture_output=True, text=True, timeout=1)
    wid = out.stdout.strip().split()[-1] if out.stdout.strip() else ""
    if not wid.startswith("0x") or wid == "0x0":
        return None
    out = subprocess.run(["xprop", "-id", wid, "_NET_WM_PID"], capture_output=True, text=True, timeout=1)
    try:
        pid = int(out.stdout.strip().split()[-1])
    except (ValueError, IndexError):
        return None
    try:
        with open(f"/proc/{pid}/comm", encoding="utf-8") as fh:
            return fh.read().strip().lower()
    except OSError:
        return None


def match_profile(app: Optional[str], profiles: dict) -> Optional[str]:
    """First profile whose app list contains a name that appears in ``app``."""
    if not app:
        return None
    app = app.lower()
    for pid, p in profiles.items():
        for name in p.get("apps", []):
            name = name.strip().lower()
            if name and (app == name or name in app):
                return pid
    return None
