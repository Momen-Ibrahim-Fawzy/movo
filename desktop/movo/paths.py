"""File-system locations. Nothing here touches the camera; only settings and screenshots are written."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "Movo"
LEGACY_DIR_NAMES = ("Imaa",)  # the app's previous name; settings are moved over on first start


def resource_dir() -> Path:
    """Folder that contains the ``movo`` package resources, also when frozen by PyInstaller."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / "movo"
    return Path(__file__).resolve().parent


def asset(*parts: str) -> Path:
    return resource_dir().joinpath("assets", *parts)


def config_dir() -> Path:
    override = os.environ.get("MOVO_CONFIG_DIR")
    if override:
        path = Path(override)
    else:
        path = _platform_dir(APP_DIR_NAME)
        if not path.exists():
            _migrate_legacy(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _platform_dir(name: str) -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / name
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / name
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / name.lower()


def _migrate_legacy(target: Path) -> None:
    """Copy settings from the app's previous name so nothing is lost after the rename."""
    import shutil

    for legacy in LEGACY_DIR_NAMES:
        old = _platform_dir(legacy) / "settings.json"
        if old.is_file():
            try:
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(old, target / "settings.json")
            except OSError:
                pass
            return


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
