"""Keyboard and mouse injection through pynput (Windows, macOS, Linux/X11)."""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import Iterable
from typing import Union

from pynput import keyboard, mouse

log = logging.getLogger(__name__)
IS_MAC = sys.platform == "darwin"
Key = keyboard.Key
KeyLike = Union[Key, keyboard.KeyCode, str]

_kb = keyboard.Controller()
_mouse = mouse.Controller()

MOD = Key.cmd if IS_MAC else Key.ctrl

_NAMED = {
    "ctrl": Key.ctrl,
    "control": Key.ctrl,
    "shift": Key.shift,
    "alt": Key.alt,
    "option": Key.alt,
    "cmd": Key.cmd,
    "command": Key.cmd,
    "win": Key.cmd,
    "super": Key.cmd,
    "meta": Key.cmd,
    "mod": MOD,
    "enter": Key.enter,
    "return": Key.enter,
    "esc": Key.esc,
    "escape": Key.esc,
    "tab": Key.tab,
    "space": Key.space,
    "backspace": Key.backspace,
    "delete": Key.delete,
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "home": Key.home,
    "end": Key.end,
    "pageup": Key.page_up,
    "pagedown": Key.page_down,
    "plus": "=",
    "minus": "-",
}
for _i in range(1, 21):
    _k = getattr(Key, f"f{_i}", None)
    if _k is not None:
        _NAMED[f"f{_i}"] = _k


def press(*combo: KeyLike) -> None:
    """Press a key combination, e.g. ``press(MOD, "=")``."""
    held = []
    try:
        for k in combo[:-1]:
            _kb.press(k)
            held.append(k)
        _kb.press(combo[-1])
        _kb.release(combo[-1])
    finally:
        for k in reversed(held):
            _kb.release(k)


def parse_shortcut(text: str) -> list[KeyLike]:
    """``"ctrl+shift+m"`` → ``[Key.ctrl, Key.shift, "m"]``. Raises ValueError for unknown names."""
    keys: list[KeyLike] = []
    for part in [p.strip().lower() for p in text.replace(" ", "").split("+") if p.strip()]:
        if part in _NAMED:
            keys.append(_NAMED[part])
        elif len(part) == 1:
            keys.append(part)
        else:
            raise ValueError(part)
    if not keys:
        raise ValueError("empty")
    return keys


def press_shortcut(text: str) -> None:
    press(*parse_shortcut(text))


def scroll(steps: float) -> None:
    """Positive = up. Fractional steps are accumulated so slow scrolling still moves."""
    global _scroll_acc
    _scroll_acc += steps
    whole = int(_scroll_acc)
    if whole:
        _scroll_acc -= whole
        _mouse.scroll(0, whole)


_scroll_acc = 0.0


def click(button: str = "left") -> None:
    _mouse.click(mouse.Button.left if button == "left" else mouse.Button.right)


def mouse_down() -> None:
    _mouse.press(mouse.Button.left)


def mouse_up() -> None:
    _mouse.release(mouse.Button.left)


def move_to(x: int, y: int) -> None:
    _mouse.position = (x, y)


def move_by(dx: float, dy: float) -> None:
    _mouse.move(int(round(dx)), int(round(dy)))


def mouse_position() -> tuple[int, int]:
    x, y = _mouse.position
    return int(x), int(y)


def tap_sequence(keys: Iterable[KeyLike], delay: float = 0.02) -> None:
    for k in keys:
        press(k)
        time.sleep(delay)
