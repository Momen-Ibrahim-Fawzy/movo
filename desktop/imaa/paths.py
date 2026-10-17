"""File-system locations. Nothing here touches the camera; only settings and screenshots are written."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "Imaa"


def resource_dir() -> Path:
    """Folder that contains the ``imaa`` package resources, also when frozen by PyInstaller."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / "imaa"
    return Path(__file__).resolve().parent


def asset(*parts: str) -> Path:
    return resource_dir().joinpath("assets", *parts)


def config_dir() -> Path:
    override = os.environ.get("IMAA_CONFIG_DIR")
    if override:
        path = Path(override)
    elif sys.platform == "win32":
        path = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP_DIR_NAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    else:
        path = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_DIR_NAME.lower()
    path.mkdir(parents=True, exist_ok=True)
    return path


def pictures_dir() -> Path:
    if sys.platform.startswith("linux"):
        try:
            import subprocess

            out = subprocess.run(["xdg-user-dir", "PICTURES"], capture_output=True, text=True, timeout=2)
            if out.returncode == 0 and out.stdout.strip():
                return Path(out.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            pass
    return Path.home() / "Pictures"


def default_screenshot_dir() -> Path:
    return pictures_dir() / APP_DIR_NAME
