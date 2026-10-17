"""Executes actions on a background worker so slow ones never stall the camera loop."""

from __future__ import annotations

import logging
import queue
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Optional

from imaa.core.catalog import ACTIONS_BY_ID

log = logging.getLogger(__name__)
IS_MAC = sys.platform == "darwin"


@dataclass
class ActionResult:
    action: str
    ok: bool = True
    message: str = ""  # translation key for the HUD; empty = use the action label
    args: dict = field(default_factory=dict)
    gesture: str = ""
    source: str = "hand"


@dataclass
class ActionRequest:
    action: str
    magnitude: float = 1.0
    shortcut: str = ""
    gesture: str = ""
    source: str = "hand"


class ActionExecutor:
    """Runs actions in order on one worker thread.

    ``hooks`` lets the application provide UI-bound actions:
    ``screenshot() -> ActionResult``, ``pause_control() -> ActionResult``,
    ``skip_ad_bridge() -> Optional[bool]`` (None = helper not connected).
    """

    def __init__(self, on_result: Optional[Callable[[ActionResult], None]] = None):
        self.on_result = on_result
        self.hooks: dict[str, Callable] = {}
        self.scroll_speed = 1.0
        self._q: queue.Queue[Optional[ActionRequest]] = queue.Queue(maxsize=64)
        self._thread = threading.Thread(target=self._loop, name="imaa-actions", daemon=True)
        self._thread.start()

    def submit(self, req: ActionRequest) -> None:
        try:
            self._q.put_nowait(req)
        except queue.Full:
            log.warning("action queue full, dropping %s", req.action)

    def close(self) -> None:
        self._q.put(None)

    def _loop(self) -> None:
        while True:
            req = self._q.get()
            if req is None:
                return
            try:
                result = self.run(req)
            except Exception as exc:  # keep the worker alive whatever happens
                log.exception("action %s failed", req.action)
                result = ActionResult(req.action, False, "action_failed", {"error": str(exc)})
            if result is not None:
                result.gesture = req.gesture
                result.source = req.source
                if self.on_result:
                    self.on_result(result)

    # ------------------------------------------------------------------ actions
    def run(self, req: ActionRequest) -> Optional[ActionResult]:
        from imaa.actions import keys, system

        a = req.action
        if a == "none" or a not in ACTIONS_BY_ID:
            return None
        K, MOD = keys.Key, keys.MOD
        simple = {
            "play_pause": (K.space,),
            "media_play_pause": (K.media_play_pause,),
            "media_next": (K.media_next,),
            "media_prev": (K.media_previous,),
            "next": (K.right,),
            "previous": (K.left,),
            "key_up": (K.up,),
            "key_down": (K.down,),
            "page_down": (K.page_down,),
            "page_up": (K.page_up,),
            "enter": (K.enter,),
            "escape": (K.esc,),
            "browser_back": (K.cmd, "[") if IS_MAC else (K.alt, K.left),
            "browser_forward": (K.cmd, "]") if IS_MAC else (K.alt, K.right),
            "slide_next": (K.page_down,),
            "slide_prev": (K.page_up,),
            "slide_black": ("b",),
            "slideshow_start": (K.cmd, K.shift, K.enter) if IS_MAC else (K.f5,),
            "fullscreen": (K.ctrl, K.cmd, "f") if IS_MAC else (K.f11,),
            "zoom_in": (MOD, "="),
            "zoom_out": (MOD, "-"),
            "zoom_reset": (MOD, "0"),
            "next_tab": (K.ctrl, K.tab),
            "prev_tab": (K.ctrl, K.shift, K.tab),
            "new_tab": (MOD, "t"),
            "close_tab": (MOD, "w"),
            "switch_app": (K.cmd, K.tab) if IS_MAC else (K.alt, K.tab),
            "show_desktop": (K.cmd, K.f3) if IS_MAC else (K.cmd, "d"),
        }
        if a in simple:
            keys.press(*simple[a])
            return ActionResult(a)
        if a in ("volume_up", "volume_down", "volume_mute"):
            system.volume({"volume_up": 1, "volume_down": -1, "volume_mute": 0}[a])
            return ActionResult(a)
        if a in ("scroll_up", "scroll_down"):
            steps = 1.6 * req.magnitude * self.scroll_speed
            keys.scroll(steps if a == "scroll_up" else -steps)
            return ActionResult(a)
        if a in ("left_click", "right_click"):
            keys.click("left" if a == "left_click" else "right")
            return ActionResult(a)
        if a == "mic_toggle":
            muted = system.toggle_microphone()
            if muted is None:
                return ActionResult(a, False, "mic_unsupported")
            return ActionResult(a, True, "mic_muted" if muted else "mic_unmuted")
        if a == "skip_ad":
            return self._skip_ad()
        if a == "custom_shortcut":
            if not req.shortcut:
                return ActionResult(a, False, "shortcut_missing")
            keys.press_shortcut(req.shortcut)
            return ActionResult(a, True, "shortcut_sent", {"keys": req.shortcut})
        hook = self.hooks.get(a)
        if hook:
            return hook()
        return ActionResult(a, False, "action_failed")

    def _skip_ad(self) -> ActionResult:
        from imaa.actions.skip_ad import skip_native

        bridge = self.hooks.get("skip_ad_bridge")
        clicked = bridge() if bridge else None
        if clicked:
            return ActionResult("skip_ad", True, "skip_ad_done")
        if skip_native():
            return ActionResult("skip_ad", True, "skip_ad_done")
        if clicked is None:
            return ActionResult("skip_ad", False, "skip_ad_no_helper")
        return ActionResult("skip_ad", False, "skip_ad_none")
