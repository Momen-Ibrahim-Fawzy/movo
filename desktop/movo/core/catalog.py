"""Static catalog of gestures and actions.

Kept free of Qt and MediaPipe imports so it can be shared by the engine, the UI and the tests.
Labels are translation keys (see ``movo/i18n``).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GestureInfo:
    id: str
    source: str  # "hand" | "head"
    emoji: str
    hold_ms: int = 0  # default hold time for static poses (0 = event gesture)
    accurate_only: bool = False  # head gestures that need the Face Landmarker


HAND_GESTURES: tuple[GestureInfo, ...] = (
    GestureInfo("thumb_up", "hand", "👍", 300),
    GestureInfo("thumb_down", "hand", "👎", 300),
    GestureInfo("point_right", "hand", "👉", 300),
    GestureInfo("point_left", "hand", "👈", 300),
    GestureInfo("pinch", "hand", "🤏"),
    GestureInfo("index_up_move_up", "hand", "☝️"),
    GestureInfo("index_up_move_down", "hand", "☝️"),
    GestureInfo("pinch_drag_up", "hand", "🤏"),
    GestureInfo("pinch_drag_down", "hand", "🤏"),
    GestureInfo("swipe_right", "hand", "✋"),
    GestureInfo("swipe_left", "hand", "✋"),
    GestureInfo("victory", "hand", "✌️", 550),
    GestureInfo("call", "hand", "🤙", 600),
    GestureInfo("fist", "hand", "✊", 600),
    GestureInfo("rock", "hand", "🤘", 1200),
    GestureInfo("three", "hand", "🖖", 550),
)

HEAD_GESTURES: tuple[GestureInfo, ...] = (
    GestureInfo("nod", "head", "🙂"),
    GestureInfo("shake", "head", "🙅"),
    GestureInfo("tilt_right", "head", "↗️", 450),
    GestureInfo("tilt_left", "head", "↖️", 450),
    GestureInfo("look_up", "head", "⬆️", 450),
    GestureInfo("look_down", "head", "⬇️", 450),
    GestureInfo("turn_right", "head", "➡️", 450),
    GestureInfo("turn_left", "head", "⬅️", 450),
    GestureInfo("mouth_open", "head", "😮", 350, accurate_only=True),
    GestureInfo("smile", "head", "😁", 450, accurate_only=True),
    GestureInfo("brows_up", "head", "🤨", 400, accurate_only=True),
)

EYE_GESTURES: tuple[GestureInfo, ...] = (
    GestureInfo("wink_left", "eye", "😉", 350, accurate_only=True),
    GestureInfo("wink_right", "eye", "😉", 350, accurate_only=True),
    GestureInfo("blink_double", "eye", "👁️", accurate_only=True),
    GestureInfo("blink_long", "eye", "😌", 600, accurate_only=True),
    GestureInfo("eyes_closed", "eye", "😴", 2000, accurate_only=True),
    GestureInfo("eye_look_up", "eye", "🔼", 600, accurate_only=True),
    GestureInfo("eye_look_down", "eye", "🔽", 600, accurate_only=True),
    GestureInfo("eye_look_left", "eye", "◀️", 600, accurate_only=True),
    GestureInfo("eye_look_right", "eye", "▶️", 600, accurate_only=True),
)

ALL_GESTURES: dict[str, GestureInfo] = {g.id: g for g in HAND_GESTURES + HEAD_GESTURES + EYE_GESTURES}


@dataclass(frozen=True)
class ActionInfo:
    id: str
    category: str
    emoji: str
    repeatable: bool = False  # may fire repeatedly while a gesture is held


ACTIONS: tuple[ActionInfo, ...] = (
    ActionInfo("none", "control", "∅"),
    # audio & media
    ActionInfo("volume_up", "media", "🔊", True),
    ActionInfo("volume_down", "media", "🔉", True),
    ActionInfo("volume_mute", "media", "🔇"),
    ActionInfo("play_pause", "media", "⏯️"),
    ActionInfo("media_play_pause", "media", "⏯️"),
    ActionInfo("media_next", "media", "⏭️"),
    ActionInfo("media_prev", "media", "⏮️"),
    # navigation
    ActionInfo("next", "navigation", "➡️", True),
    ActionInfo("previous", "navigation", "⬅️", True),
    ActionInfo("key_up", "navigation", "⬆️", True),
    ActionInfo("key_down", "navigation", "⬇️", True),
    ActionInfo("page_down", "navigation", "⏬", True),
    ActionInfo("page_up", "navigation", "⏫", True),
    ActionInfo("enter", "navigation", "↩️"),
    ActionInfo("escape", "navigation", "⎋"),
    ActionInfo("browser_back", "navigation", "◀️"),
    ActionInfo("browser_forward", "navigation", "▶️"),
    # presentation
    ActionInfo("slide_next", "presentation", "📽️", True),
    ActionInfo("slide_prev", "presentation", "📽️", True),
    ActionInfo("slide_black", "presentation", "⬛"),
    ActionInfo("slideshow_start", "presentation", "🎬"),
    ActionInfo("fullscreen", "presentation", "⛶"),
    # scroll & zoom
    ActionInfo("scroll_up", "view", "🔼", True),
    ActionInfo("scroll_down", "view", "🔽", True),
    ActionInfo("zoom_in", "view", "🔍", True),
    ActionInfo("zoom_out", "view", "🔎", True),
    ActionInfo("zoom_reset", "view", "💯"),
    # tabs & windows
    ActionInfo("next_tab", "tabs", "📑", True),
    ActionInfo("prev_tab", "tabs", "📑", True),
    ActionInfo("new_tab", "tabs", "➕"),
    ActionInfo("close_tab", "tabs", "✖️"),
    ActionInfo("switch_app", "tabs", "🔀"),
    ActionInfo("show_desktop", "tabs", "🖥️"),
    # capture, mic, ads
    ActionInfo("screenshot", "tools", "📸"),
    ActionInfo("mic_toggle", "tools", "🎙️"),
    ActionInfo("skip_ad", "tools", "⏩"),
    # mouse
    ActionInfo("left_click", "mouse", "🖱️"),
    ActionInfo("right_click", "mouse", "🖱️"),
    # control
    ActionInfo("pause_control", "control", "⏸️"),
    ActionInfo("custom_shortcut", "control", "⌨️", True),
)

ACTIONS_BY_ID: dict[str, ActionInfo] = {a.id: a for a in ACTIONS}
ACTION_CATEGORIES = ("media", "navigation", "presentation", "view", "tabs", "tools", "mouse", "control")


DEFAULT_BINDINGS: dict[str, str] = {
    # hand
    "thumb_up": "volume_up",
    "thumb_down": "volume_down",
    "point_right": "next",
    "point_left": "previous",
    "pinch": "play_pause",
    "index_up_move_up": "scroll_up",
    "index_up_move_down": "scroll_down",
    "pinch_drag_up": "zoom_in",
    "pinch_drag_down": "zoom_out",
    "swipe_right": "next_tab",
    "swipe_left": "prev_tab",
    "victory": "screenshot",
    "call": "mic_toggle",
    "fist": "skip_ad",
    "rock": "pause_control",
    "three": "none",
    # head
    "nod": "play_pause",
    "shake": "skip_ad",
    "tilt_right": "next",
    "tilt_left": "previous",
    "look_up": "scroll_up",
    "look_down": "scroll_down",
    "turn_right": "next_tab",
    "turn_left": "prev_tab",
    "mouth_open": "mic_toggle",
    "smile": "screenshot",
    "brows_up": "none",
    # eyes
    "wink_left": "previous",
    "wink_right": "next",
    "blink_double": "play_pause",
    "blink_long": "skip_ad",
    "eyes_closed": "pause_control",
    "eye_look_up": "scroll_up",
    "eye_look_down": "scroll_down",
    "eye_look_left": "none",
    "eye_look_right": "none",
}

# Profile presets: overrides on top of DEFAULT_BINDINGS, plus apps that activate them automatically.
PROFILE_PRESETS: dict[str, dict] = {
    "general": {"overrides": {}, "apps": []},
    "presentation": {
        "overrides": {
            "point_right": "slide_next",
            "point_left": "slide_prev",
            "tilt_right": "slide_next",
            "tilt_left": "slide_prev",
            "wink_right": "slide_next",
            "wink_left": "slide_prev",
            "pinch": "slide_black",
            "victory": "slideshow_start",
        },
        "apps": ["powerpnt", "keynote", "impress", "soffice", "libreoffice", "acrord32", "acrobat", "sumatrapdf"],
    },
    "media": {
        "overrides": {
            "pinch": "media_play_pause",
            "nod": "media_play_pause",
            "swipe_right": "media_next",
            "swipe_left": "media_prev",
            "victory": "fullscreen",
        },
        "apps": ["vlc", "spotify", "music", "tv", "mpv", "potplayer", "wmplayer", "iina", "movies & tv"],
    },
    "browser": {
        "overrides": {"point_right": "browser_forward", "point_left": "browser_back"},
        "apps": [],
    },
    "meeting": {
        "overrides": {"call": "mic_toggle", "mouth_open": "mic_toggle", "victory": "screenshot"},
        "apps": ["zoom", "teams", "ms-teams", "webex", "slack", "discord", "skype"],
    },
}
