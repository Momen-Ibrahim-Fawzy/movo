"""Start Movo when the user signs in (per-user, no admin rights needed)."""

from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path

NAME = "Movo"


def _command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--minimized"]
    return [sys.executable, "-m", "movo", "--minimized"]


LEGACY_NAMES = ("Imaa",)  # remove start-up entries left by the app's previous name


def set_enabled(enabled: bool) -> bool:
    _remove_legacy()
    try:
        if sys.platform == "win32":
            _windows(enabled)
        elif sys.platform == "darwin":
            _mac(enabled)
        else:
            _linux(enabled)
        return True
    except OSError:
        return False


def _windows(enabled: bool) -> None:
    import subprocess
    import winreg

    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
    try:
        if enabled:
            winreg.SetValueEx(key, NAME, 0, winreg.REG_SZ, subprocess.list2cmdline(_command()))
        else:
            try:
                winreg.DeleteValue(key, NAME)
            except FileNotFoundError:
                pass
    finally:
        winreg.CloseKey(key)


def _mac(enabled: bool) -> None:
    plist = Path.home() / "Library" / "LaunchAgents" / "app.movo.desktop.plist"
    if not enabled:
        plist.unlink(missing_ok=True)
        return
    args = "".join(f"<string>{a}</string>" for a in _command())
    plist.parent.mkdir(parents=True, exist_ok=True)
    plist.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict><key>Label</key><string>app.movo.desktop</string>'
        f"<key>ProgramArguments</key><array>{args}</array><key>RunAtLoad</key><true/></dict></plist>\n",
        encoding="utf-8",
    )


def _linux(enabled: bool) -> None:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "autostart"
    desktop = base / "movo.desktop"
    if not enabled:
        desktop.unlink(missing_ok=True)
        return
    base.mkdir(parents=True, exist_ok=True)
    exec_line = os.environ.get("APPIMAGE") and f"{shlex.quote(os.environ['APPIMAGE'])} --minimized" or shlex.join(_command())
    desktop.write_text(
        "[Desktop Entry]\nType=Application\nName=Movo\nComment=Gesture control\n"
        f"Exec={exec_line}\nIcon=movo\nX-GNOME-Autostart-enabled=true\n",
        encoding="utf-8",
    )


def _remove_legacy() -> None:
    for name in LEGACY_NAMES:
        try:
            if sys.platform == "win32":
                import winreg

                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE
                )
                try:
                    winreg.DeleteValue(key, name)
                except FileNotFoundError:
                    pass
                finally:
                    winreg.CloseKey(key)
            elif sys.platform == "darwin":
                (Path.home() / "Library" / "LaunchAgents" / f"app.{name.lower()}.desktop.plist").unlink(missing_ok=True)
            else:
                base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "autostart"
                (base / f"{name.lower()}.desktop").unlink(missing_ok=True)
        except OSError:
            pass
