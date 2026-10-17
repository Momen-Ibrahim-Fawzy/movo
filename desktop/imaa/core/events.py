from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GestureEvent:
    """A recognised gesture.

    ``phase`` is ``"start"`` the first time a gesture fires and ``"repeat"`` while it keeps going
    (held pose, continued drag, joystick scroll). ``magnitude`` scales analog actions such as scrolling.
    """

    gesture: str
    phase: str = "start"
    magnitude: float = 1.0
    source: str = "hand"  # "hand" | "head" | "remote"
