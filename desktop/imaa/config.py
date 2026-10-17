"""User settings, stored as JSON in the per-user config folder."""

from __future__ import annotations

import copy
import json
import random
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional

from imaa.core.catalog import ACTIONS_BY_ID, ALL_GESTURES, DEFAULT_BINDINGS, PROFILE_PRESETS
from imaa.paths import config_dir

SCHEMA_VERSION = 1


def _default_profiles() -> dict:
    return {
        pid: {"name": "", "bindings": dict(p["overrides"]), "apps": list(p["apps"]), "shortcuts": {}}
        for pid, p in PROFILE_PRESETS.items()
    }


DEFAULTS: dict[str, Any] = {
    "version": SCHEMA_VERSION,
    "language": "system",  # system | en | ar
    "theme": "system",  # system | light | dark
    "first_run_done": False,
    "start_detection_on_launch": False,
    "start_minimized": False,
    "launch_at_login": False,
    "close_to_tray": True,
    "camera": {"index": 0, "width": 640, "height": 480, "mirror": True},
    "power_mode": "balanced",  # eco | balanced | performance
    "show_preview": True,
    "show_skeleton": True,
    "hand": {"enabled": True, "hold_scale": 1.0, "scroll_speed": 1.0, "swipe_enabled": True},
    "head": {"enabled": False, "mode": "light", "sensitivity": 1.0, "hold_scale": 1.0},
    "pointer": {"air_mouse": False, "head_pointer": False, "speed": 1.0, "smoothing": 0.5},
    "disabled_gestures": [],
    "profiles": _default_profiles(),
    "active_profile": "general",
    "auto_profiles": True,
    "hud": {"enabled": True, "position": "bottom"},  # bottom | top
    "sounds": False,
    "hotkey_pause": "<ctrl>+<alt>+g",
    "screenshots": {"folder": "", "copy_to_clipboard": True},
    "browser_bridge": {"enabled": True, "port": 47812},
    "remote": {"enabled": False, "port": 47813, "code": ""},
}


def _merge(defaults: dict, data: dict) -> dict:
    out = copy.deepcopy(defaults)
    for key, value in data.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict) and key != "profiles":
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


class Settings:
    """Thread-safe settings store with change notifications."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or (config_dir() / "settings.json")
        self._lock = threading.RLock()
        self._listeners: list[Callable[[str], None]] = []
        self.data = self._load()

    # ------------------------------------------------------------------ persistence
    def _load(self) -> dict:
        data: dict = {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        merged = _merge(DEFAULTS, data if isinstance(data, dict) else {})
        self._sanitize(merged)
        return merged

    @staticmethod
    def _sanitize(d: dict) -> None:
        if not isinstance(d.get("profiles"), dict) or not d["profiles"]:
            d["profiles"] = _default_profiles()
        for pid, p in list(d["profiles"].items()):
            if not isinstance(p, dict):
                del d["profiles"][pid]
                continue
            p.setdefault("name", "")
            p.setdefault("apps", [])
            p.setdefault("shortcuts", {})
            p["bindings"] = {g: a for g, a in p.get("bindings", {}).items() if g in ALL_GESTURES and a in ACTIONS_BY_ID}
        if d.get("active_profile") not in d["profiles"]:
            d["active_profile"] = next(iter(d["profiles"]))
        if not d["remote"].get("code"):
            d["remote"]["code"] = f"{random.SystemRandom().randrange(0, 1_000_000):06d}"
        d["disabled_gestures"] = [g for g in d.get("disabled_gestures", []) if g in ALL_GESTURES]

    def save(self) -> None:
        with self._lock:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.path)

    # ------------------------------------------------------------------ access
    def get(self, dotted: str, default: Any = None) -> Any:
        with self._lock:
            node: Any = self.data
            for part in dotted.split("."):
                if not isinstance(node, dict) or part not in node:
                    return default
                node = node[part]
            return node

    def set(self, dotted: str, value: Any, save: bool = True) -> None:
        with self._lock:
            parts = dotted.split(".")
            node = self.data
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            if node.get(parts[-1]) == value:
                return
            node[parts[-1]] = value
            if save:
                self.save()
        self._notify(dotted)

    def on_change(self, callback: Callable[[str], None]) -> None:
        self._listeners.append(callback)

    def _notify(self, key: str) -> None:
        for cb in list(self._listeners):
            try:
                cb(key)
            except Exception:  # a broken listener must not break settings
                import logging

                logging.getLogger(__name__).exception("settings listener failed")

    def notify(self, key: str) -> None:
        self._notify(key)

    # ------------------------------------------------------------------ bindings
    def binding(self, gesture: str, profile: Optional[str] = None) -> str:
        pid = profile or self.get("active_profile")
        p = self.get("profiles", {}).get(pid, {})
        return p.get("bindings", {}).get(gesture, DEFAULT_BINDINGS.get(gesture, "none"))

    def shortcut(self, gesture: str, profile: Optional[str] = None) -> str:
        pid = profile or self.get("active_profile")
        return self.get("profiles", {}).get(pid, {}).get("shortcuts", {}).get(gesture, "")

    def set_binding(self, profile: str, gesture: str, action: str, shortcut: Optional[str] = None) -> None:
        with self._lock:
            p = self.data["profiles"][profile]
            if action == DEFAULT_BINDINGS.get(gesture) and profile == "general":
                p["bindings"].pop(gesture, None)
            else:
                p["bindings"][gesture] = action
            if shortcut is not None:
                p["shortcuts"][gesture] = shortcut
            self.save()
        self._notify(f"profiles.{profile}")

    def gesture_enabled(self, gesture: str) -> bool:
        return gesture not in self.get("disabled_gestures", [])

    def set_gesture_enabled(self, gesture: str, enabled: bool) -> None:
        current = set(self.get("disabled_gestures", []))
        current.discard(gesture) if enabled else current.add(gesture)
        self.set("disabled_gestures", sorted(current))

    # ------------------------------------------------------------------ profiles
    def add_profile(self, name: str, copy_from: Optional[str] = None) -> str:
        with self._lock:
            base = self.data["profiles"].get(copy_from or "general", {})
            pid = "custom_" + "".join(random.choice("abcdefghijkmnpqrstuvwxyz23456789") for _ in range(6))
            self.data["profiles"][pid] = {
                "name": name,
                "bindings": dict(base.get("bindings", {})),
                "apps": [],
                "shortcuts": dict(base.get("shortcuts", {})),
            }
            self.save()
        self._notify("profiles")
        return pid

    def delete_profile(self, pid: str) -> None:
        with self._lock:
            if pid == "general" or pid not in self.data["profiles"]:
                return
            del self.data["profiles"][pid]
            if self.data["active_profile"] == pid:
                self.data["active_profile"] = "general"
            self.save()
        self._notify("profiles")

    # ------------------------------------------------------------------ import / export / reset
    def export_to(self, path: Path) -> None:
        path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")

    def import_from(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("not a settings file")
        with self._lock:
            merged = _merge(DEFAULTS, data)
            self._sanitize(merged)
            merged["first_run_done"] = True
            self.data = merged
            self.save()
        self._notify("*")

    def reset(self) -> None:
        with self._lock:
            code = self.data["remote"]["code"]
            self.data = copy.deepcopy(DEFAULTS)
            self.data["profiles"] = _default_profiles()
            self.data["first_run_done"] = True
            self.data["remote"]["code"] = code
            self.save()
        self._notify("*")
