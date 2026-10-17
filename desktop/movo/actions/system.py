"""System audio controls: output volume and microphone mute, per platform."""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from typing import Optional

log = logging.getLogger(__name__)


def _run(cmd: list[str]) -> Optional[str]:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


# ---------------------------------------------------------------------------- volume
def volume(step: int) -> None:
    """Change output volume. step > 0 louder, < 0 quieter, 0 toggles mute."""
    if sys.platform.startswith("linux") and shutil.which("pactl"):
        if step == 0:
            _run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"])
        else:
            _run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{'+' if step > 0 else '-'}5%"])
        return
    from movo.actions.keys import Key, press

    press(Key.media_volume_mute if step == 0 else Key.media_volume_up if step > 0 else Key.media_volume_down)


# ---------------------------------------------------------------------------- microphone
def toggle_microphone() -> Optional[bool]:
    """Toggle the default microphone. Returns the new *muted* state, or None if unsupported."""
    try:
        if sys.platform == "win32":
            return _toggle_mic_windows()
        if sys.platform == "darwin":
            return _toggle_mic_mac()
        return _toggle_mic_linux()
    except Exception:
        log.exception("microphone toggle failed")
        return None


def _toggle_mic_windows() -> Optional[bool]:
    from ctypes import POINTER, cast

    import comtypes
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    comtypes.CoInitialize()
    try:
        device = AudioUtilities.GetMicrophone()
        if device is None:
            return None
        iface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        endpoint = cast(iface, POINTER(IAudioEndpointVolume))
        muted = not bool(endpoint.GetMute())
        endpoint.SetMute(int(muted), None)
        return muted
    finally:
        comtypes.CoUninitialize()


_mac_saved_input_volume = 75


def _toggle_mic_mac() -> Optional[bool]:
    global _mac_saved_input_volume
    current = _run(["osascript", "-e", "input volume of (get volume settings)"])
    if current is None:
        return None
    level = int(current or 0)
    if level > 0:
        _mac_saved_input_volume = level
        _run(["osascript", "-e", "set volume input volume 0"])
        return True
    _run(["osascript", "-e", f"set volume input volume {_mac_saved_input_volume}"])
    return False


def _toggle_mic_linux() -> Optional[bool]:
    if shutil.which("pactl"):
        _run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "toggle"])
        state = _run(["pactl", "get-source-mute", "@DEFAULT_SOURCE@"])
        if state is not None:
            return state.lower().endswith("yes")
        return None
    if shutil.which("amixer"):
        out = _run(["amixer", "set", "Capture", "toggle"])
        if out is not None:
            return "[off]" in out
    return None
