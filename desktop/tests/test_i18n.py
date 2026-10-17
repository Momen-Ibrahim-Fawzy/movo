import re
from pathlib import Path

from movo import i18n
from movo.core.catalog import ACTIONS, ALL_GESTURES, PROFILE_PRESETS

PKG = Path(__file__).resolve().parents[1] / "movo"
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def test_arabic_has_every_english_key():
    assert i18n.keys("en") - i18n.keys("ar") == set()
    assert i18n.keys("ar") - i18n.keys("en") == set()


def test_placeholders_match():
    en, ar = i18n._table("en"), i18n._table("ar")
    for key, text in en.items():
        assert set(PLACEHOLDER.findall(text)) == set(PLACEHOLDER.findall(ar[key])), key


def test_catalog_is_translated():
    en = i18n.keys("en")
    for gid in ALL_GESTURES:
        assert f"g.{gid}" in en and f"g.{gid}.how" in en
    for a in ACTIONS:
        assert f"a.{a.id}" in en
    for pid in PROFILE_PRESETS:
        assert f"profile.{pid}" in en and f"profile.{pid}.d" in en


def test_literal_keys_used_in_code_exist():
    en = i18n.keys("en")
    used = set()
    for path in PKG.rglob("*.py"):
        used |= set(re.findall(r"""tr\(\s*["']([a-z_]+\.[a-z0-9_.]+)["']""", path.read_text(encoding="utf-8")))
    missing = sorted(k for k in used if k not in en)
    assert missing == []


def test_dynamic_state_and_error_keys():
    en = i18n.keys("en")
    for s in ("stopped", "starting", "running", "paused"):
        assert f"state.{s}" in en and f"state.{s}_d" in en
    for e in ("camera_unavailable", "camera_lost", "engine_failed"):
        assert f"error.{e}" in en


def test_rtl_switch():
    assert i18n.set_language("ar") == "ar" and i18n.is_rtl()
    assert i18n.tr("nav.home") == "الرئيسية"
    assert i18n.set_language("en") == "en" and not i18n.is_rtl()
    assert i18n.tr("missing.key") == "missing.key"
