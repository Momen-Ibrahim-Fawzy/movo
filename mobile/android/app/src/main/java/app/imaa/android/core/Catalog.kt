package app.imaa.android.core

import app.imaa.android.R

/** Gesture ids are shared with the desktop app (they travel over the remote protocol). */
data class GestureInfo(val id: String, val source: String, val emoji: String, val name: Int, val accurateOnly: Boolean = false)

data class ActionInfo(val id: String, val emoji: String, val label: Int, val repeatable: Boolean = false)

object Catalog {
    val handGestures = listOf(
        GestureInfo("thumb_up", "hand", "👍", R.string.g_thumb_up),
        GestureInfo("thumb_down", "hand", "👎", R.string.g_thumb_down),
        GestureInfo("point_right", "hand", "👉", R.string.g_point_right),
        GestureInfo("point_left", "hand", "👈", R.string.g_point_left),
        GestureInfo("pinch", "hand", "🤏", R.string.g_pinch),
        GestureInfo("index_up_move_up", "hand", "☝️", R.string.g_index_up_move_up),
        GestureInfo("index_up_move_down", "hand", "☝️", R.string.g_index_up_move_down),
        GestureInfo("pinch_drag_up", "hand", "🤏", R.string.g_pinch_drag_up),
        GestureInfo("pinch_drag_down", "hand", "🤏", R.string.g_pinch_drag_down),
        GestureInfo("swipe_right", "hand", "✋", R.string.g_swipe_right),
        GestureInfo("swipe_left", "hand", "✋", R.string.g_swipe_left),
        GestureInfo("victory", "hand", "✌️", R.string.g_victory),
        GestureInfo("call", "hand", "🤙", R.string.g_call),
        GestureInfo("fist", "hand", "✊", R.string.g_fist),
        GestureInfo("rock", "hand", "🤘", R.string.g_rock),
        GestureInfo("three", "hand", "🖖", R.string.g_three),
    )

    val headGestures = listOf(
        GestureInfo("nod", "head", "🙂", R.string.g_nod),
        GestureInfo("shake", "head", "🙅", R.string.g_shake),
        GestureInfo("tilt_right", "head", "↗️", R.string.g_tilt_right),
        GestureInfo("tilt_left", "head", "↖️", R.string.g_tilt_left),
        GestureInfo("look_up", "head", "⬆️", R.string.g_look_up),
        GestureInfo("look_down", "head", "⬇️", R.string.g_look_down),
        GestureInfo("turn_right", "head", "➡️", R.string.g_turn_right),
        GestureInfo("turn_left", "head", "⬅️", R.string.g_turn_left),
        GestureInfo("mouth_open", "head", "😮", R.string.g_mouth_open, accurateOnly = true),
        GestureInfo("smile", "head", "😁", R.string.g_smile, accurateOnly = true),
        GestureInfo("brows_up", "head", "🤨", R.string.g_brows_up, accurateOnly = true),
    )

    val gestures: Map<String, GestureInfo> = (handGestures + headGestures).associateBy { it.id }

    val actions = listOf(
        ActionInfo("none", "∅", R.string.a_none),
        ActionInfo("volume_up", "🔊", R.string.a_volume_up, true),
        ActionInfo("volume_down", "🔉", R.string.a_volume_down, true),
        ActionInfo("volume_mute", "🔇", R.string.a_volume_mute),
        ActionInfo("media_play_pause", "⏯️", R.string.a_media_play_pause),
        ActionInfo("media_next", "⏭️", R.string.a_media_next),
        ActionInfo("media_prev", "⏮️", R.string.a_media_prev),
        ActionInfo("next", "➡️", R.string.a_next, true),
        ActionInfo("previous", "⬅️", R.string.a_previous, true),
        ActionInfo("scroll_up", "🔼", R.string.a_scroll_up, true),
        ActionInfo("scroll_down", "🔽", R.string.a_scroll_down, true),
        ActionInfo("zoom_in", "🔍", R.string.a_zoom_in, true),
        ActionInfo("zoom_out", "🔎", R.string.a_zoom_out, true),
        ActionInfo("back", "◀️", R.string.a_back),
        ActionInfo("home", "🏠", R.string.a_home),
        ActionInfo("recents", "🗂️", R.string.a_recents),
        ActionInfo("notifications", "🔔", R.string.a_notifications),
        ActionInfo("quick_settings", "⚙️", R.string.a_quick_settings),
        ActionInfo("screenshot", "📸", R.string.a_screenshot),
        ActionInfo("mic_toggle", "🎙️", R.string.a_mic_toggle),
        ActionInfo("skip_ad", "⏩", R.string.a_skip_ad),
        ActionInfo("tap", "👆", R.string.a_tap),
        ActionInfo("lock_screen", "🔒", R.string.a_lock_screen),
        ActionInfo("pause_control", "⏸️", R.string.a_pause_control),
    )

    val actionsById: Map<String, ActionInfo> = actions.associateBy { it.id }

    val defaultBindings: Map<String, String> = mapOf(
        "thumb_up" to "volume_up",
        "thumb_down" to "volume_down",
        "point_right" to "next",
        "point_left" to "previous",
        "pinch" to "media_play_pause",
        "index_up_move_up" to "scroll_up",
        "index_up_move_down" to "scroll_down",
        "pinch_drag_up" to "zoom_in",
        "pinch_drag_down" to "zoom_out",
        "swipe_right" to "recents",
        "swipe_left" to "back",
        "victory" to "screenshot",
        "call" to "mic_toggle",
        "fist" to "skip_ad",
        "rock" to "pause_control",
        "three" to "notifications",
        "nod" to "media_play_pause",
        "shake" to "skip_ad",
        "tilt_right" to "next",
        "tilt_left" to "previous",
        "look_up" to "scroll_up",
        "look_down" to "scroll_down",
        "turn_right" to "recents",
        "turn_left" to "back",
        "mouth_open" to "tap",
        "smile" to "screenshot",
        "brows_up" to "home",
    )
}

data class GestureEvent(val gesture: String, val phase: String = "start", val magnitude: Float = 1f, val source: String = "hand")
