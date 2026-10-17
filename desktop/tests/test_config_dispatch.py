import json

import pytest

from imaa.actions import ActionRequest
from imaa.config import Settings
from imaa.core.dispatcher import Dispatcher
from imaa.core.events import GestureEvent
from imaa.services.active_window import match_profile


class FakeExecutor:
    def __init__(self):
        self.requests: list[ActionRequest] = []
        self.scroll_speed = 1.0

    def submit(self, req):
        self.requests.append(req)


@pytest.fixture
def settings(tmp_path):
    return Settings(tmp_path / "settings.json")


def test_defaults_and_persistence(settings, tmp_path):
    assert settings.binding("thumb_up") == "volume_up"
    assert len(settings.get("remote.code")) == 6
    settings.set("power_mode", "eco")
    again = Settings(tmp_path / "settings.json")
    assert again.get("power_mode") == "eco"


def test_corrupt_file_falls_back_to_defaults(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text("{not json", encoding="utf-8")
    assert Settings(p).get("theme") == "system"


def test_unknown_bindings_are_dropped(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"profiles": {"general": {"bindings": {"thumb_up": "rm_rf", "nope": "next"}}}}), encoding="utf-8")
    s = Settings(p)
    assert s.binding("thumb_up") == "volume_up"


def test_profile_overrides(settings):
    assert settings.binding("point_right", "presentation") == "slide_next"
    settings.set_binding("presentation", "fist", "zoom_reset")
    assert settings.binding("fist", "presentation") == "zoom_reset"
    assert settings.binding("fist", "general") == "skip_ad"


def test_add_and_delete_profile(settings):
    pid = settings.add_profile("Gaming", "media")
    assert settings.binding("pinch", pid) == "media_play_pause"
    settings.set("active_profile", pid)
    settings.delete_profile(pid)
    assert settings.get("active_profile") == "general"
    settings.delete_profile("general")
    assert "general" in settings.get("profiles")


def test_dispatch_basic_and_repeat(settings):
    ex = FakeExecutor()
    d = Dispatcher(settings, ex)
    d.handle(GestureEvent("thumb_up", "start"))
    d.handle(GestureEvent("thumb_up", "repeat"))
    d.handle(GestureEvent("victory", "start"))
    d.handle(GestureEvent("victory", "repeat"))  # screenshot is not repeatable
    assert [r.action for r in ex.requests] == ["volume_up", "volume_up", "screenshot"]


def test_dispatch_pause_practice_and_disabled(settings):
    ex = FakeExecutor()
    seen = []
    d = Dispatcher(settings, ex, on_gesture=lambda e, a: seen.append((e.gesture, a)))
    d.paused = True
    d.handle(GestureEvent("thumb_up"))
    d.handle(GestureEvent("rock"))  # pause gesture still works while paused
    d.paused = False
    d.practice = True
    d.handle(GestureEvent("fist"))
    d.practice = False
    settings.set_gesture_enabled("call", False)
    d.handle(GestureEvent("call"))
    assert [r.action for r in ex.requests] == ["pause_control"]
    assert ("fist", "skip_ad") in seen


def test_dispatch_effective_profile_and_shortcut(settings):
    ex = FakeExecutor()
    d = Dispatcher(settings, ex)
    settings.set_binding("general", "three", "custom_shortcut", "ctrl+shift+m")
    d.handle(GestureEvent("three"))
    d.profile = "presentation"
    d.handle(GestureEvent("point_right"))
    assert ex.requests[0].shortcut == "ctrl+shift+m"
    assert ex.requests[1].action == "slide_next"


def test_remote_direct_actions_are_validated(settings):
    ex = FakeExecutor()
    d = Dispatcher(settings, ex)
    assert d.handle_action("next") == "next"
    assert d.handle_action("custom_shortcut") is None
    assert d.handle_action("format_disk") is None


def test_match_profile(settings):
    profiles = settings.get("profiles")
    assert match_profile("powerpnt", profiles) == "presentation"
    assert match_profile("zoom.us", profiles) == "meeting"
    assert match_profile("notepad", profiles) is None
    assert match_profile(None, profiles) is None


def test_import_export_reset(settings, tmp_path):
    settings.set("theme", "dark")
    out = tmp_path / "export.json"
    settings.export_to(out)
    settings.reset()
    assert settings.get("theme") == "system"
    settings.import_from(out)
    assert settings.get("theme") == "dark"
