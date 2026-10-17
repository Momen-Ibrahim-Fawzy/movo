"""Routes recognised gestures to actions through the active profile."""

from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from imaa.actions import ActionExecutor, ActionRequest
from imaa.config import Settings
from imaa.core.catalog import ACTIONS_BY_ID
from imaa.core.events import GestureEvent


class Dispatcher:
    def __init__(
        self,
        settings: Settings,
        executor: ActionExecutor,
        on_gesture: Optional[Callable[[GestureEvent, str], None]] = None,
    ):
        self.settings = settings
        self.executor = executor
        self.on_gesture = on_gesture
        self.paused = False
        self.practice = False  # recognise and report, but don't act
        self.profile: Optional[str] = None  # None = the user's selected profile

    def action_for(self, gesture: str) -> str:
        return self.settings.binding(gesture, self.profile)

    def handle(self, ev: GestureEvent) -> Optional[str]:
        """Returns the action id that was submitted, if any."""
        if not self.settings.gesture_enabled(ev.gesture):
            return None
        action = self.action_for(ev.gesture)
        if self.on_gesture and ev.phase == "start":
            self.on_gesture(ev, action)
        if self.practice or action == "none":
            return None
        if self.paused and action != "pause_control":
            return None
        info = ACTIONS_BY_ID.get(action)
        if info is None or (ev.phase == "repeat" and not info.repeatable):
            return None
        shortcut = self.settings.shortcut(ev.gesture, self.profile) if action == "custom_shortcut" else ""
        self.executor.submit(ActionRequest(action, ev.magnitude, shortcut, ev.gesture, ev.source))
        return action

    def handle_action(self, action: str, source: str = "remote") -> Optional[str]:
        """Direct action request (phone remote buttons)."""
        if action not in ACTIONS_BY_ID or action in ("none", "custom_shortcut"):
            return None
        if self.paused and action != "pause_control":
            return None
        self.executor.submit(ActionRequest(action, 1.0, "", "", source))
        return action
