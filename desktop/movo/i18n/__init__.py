"""Tiny translation layer: JSON string tables, live language switching, RTL awareness."""

from __future__ import annotations

import json
from pathlib import Path

LANGUAGES = {"en": "English", "ar": "العربية"}
RTL_LANGUAGES = {"ar"}

_dir = Path(__file__).resolve().parent
_tables: dict[str, dict[str, str]] = {}
_lang = "en"


def _table(lang: str) -> dict[str, str]:
    if lang not in _tables:
        try:
            _tables[lang] = json.loads((_dir / f"{lang}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _tables[lang] = {}
    return _tables[lang]


def system_language() -> str:
    try:
        from PySide6.QtCore import QLocale

        if QLocale.system().language() == QLocale.Arabic:
            return "ar"
    except Exception:
        pass
    return "en"


def set_language(setting: str) -> str:
    """Accepts ``system`` | ``en`` | ``ar``; returns the effective language."""
    global _lang
    _lang = system_language() if setting == "system" else (setting if setting in LANGUAGES else "en")
    return _lang


def language() -> str:
    return _lang


def is_rtl() -> bool:
    return _lang in RTL_LANGUAGES


def tr(key: str, **kwargs) -> str:
    text = _table(_lang).get(key) or _table("en").get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def has(key: str) -> bool:
    return key in _table(_lang) or key in _table("en")


def keys(lang: str) -> set[str]:
    return set(_table(lang))
