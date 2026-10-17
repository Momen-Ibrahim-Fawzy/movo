package app.imaa.android.control

import android.accessibilityservice.AccessibilityService
import android.content.Context
import android.media.AudioManager
import android.os.Build
import android.os.SystemClock
import android.view.KeyEvent
import android.widget.Toast
import app.imaa.android.ImaaApp
import app.imaa.android.R
import app.imaa.android.core.Catalog
import app.imaa.android.core.ImaaState

/** Executes Android actions. Runs on the main thread. */
object ActionRunner {
    fun run(context: Context, action: String, magnitude: Float = 1f) {
        val audio = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        val svc = ControlService.instance
        val label = Catalog.actionsById[action]?.let { "${it.emoji}  ${context.getString(it.label)}" } ?: action
        var message: String? = label

        fun needs(block: (ControlService) -> Boolean) {
            if (svc == null) message = context.getString(R.string.hud_needs_accessibility) else if (!block(svc)) message = null
        }

        when (action) {
            "volume_up" -> audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_RAISE, AudioManager.FLAG_SHOW_UI)
            "volume_down" -> audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_LOWER, AudioManager.FLAG_SHOW_UI)
            "volume_mute" -> audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_TOGGLE_MUTE, AudioManager.FLAG_SHOW_UI)
            "media_play_pause" -> mediaKey(audio, KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE)
            "media_next" -> mediaKey(audio, KeyEvent.KEYCODE_MEDIA_NEXT)
            "media_prev" -> mediaKey(audio, KeyEvent.KEYCODE_MEDIA_PREVIOUS)
            "next" -> needs { it.swipe(0.8f, 0.5f, 0.2f, 0.5f) }
            "previous" -> needs { it.swipe(0.2f, 0.5f, 0.8f, 0.5f) }
            "scroll_up" -> {
                val d = 0.12f + 0.25f * magnitude
                needs { it.swipe(0.5f, 0.45f - d / 2, 0.5f, 0.45f + d / 2, 260) }
            }
            "scroll_down" -> {
                val d = 0.12f + 0.25f * magnitude
                needs { it.swipe(0.5f, 0.55f + d / 2, 0.5f, 0.55f - d / 2, 260) }
            }
            "zoom_in" -> needs { it.pinch(out = true) }
            "zoom_out" -> needs { it.pinch(out = false) }
            "back" -> needs { it.global(AccessibilityService.GLOBAL_ACTION_BACK) }
            "home" -> needs { it.global(AccessibilityService.GLOBAL_ACTION_HOME) }
            "recents" -> needs { it.global(AccessibilityService.GLOBAL_ACTION_RECENTS) }
            "notifications" -> needs { it.global(AccessibilityService.GLOBAL_ACTION_NOTIFICATIONS) }
            "quick_settings" -> needs { it.global(AccessibilityService.GLOBAL_ACTION_QUICK_SETTINGS) }
            "screenshot" -> if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                message = null // the system shows its own screenshot animation
                if (svc == null) message = context.getString(R.string.hud_needs_accessibility) else svc.global(AccessibilityService.GLOBAL_ACTION_TAKE_SCREENSHOT)
            } else message = context.getString(R.string.hud_unsupported)
            "lock_screen" -> if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                needs { it.global(AccessibilityService.GLOBAL_ACTION_LOCK_SCREEN) }
            } else message = context.getString(R.string.hud_unsupported)
            "tap" -> needs { it.tap() }
            "mic_toggle" -> {
                val muted = !audio.isMicrophoneMute
                audio.isMicrophoneMute = muted
                message = context.getString(if (muted) R.string.hud_mic_muted else R.string.hud_mic_on)
            }
            "skip_ad" -> {
                message = if (svc == null) {
                    context.getString(R.string.hud_needs_accessibility)
                } else {
                    context.getString(if (svc.skipAd()) R.string.hud_skip_done else R.string.hud_skip_none)
                }
            }
            else -> message = null
        }
        ImaaState.lastAction.value = label
        message?.let { hud(context, it) }
    }

    private fun mediaKey(audio: AudioManager, code: Int) {
        val now = SystemClock.uptimeMillis()
        audio.dispatchMediaKeyEvent(KeyEvent(now, now, KeyEvent.ACTION_DOWN, code, 0))
        audio.dispatchMediaKeyEvent(KeyEvent(now, now, KeyEvent.ACTION_UP, code, 0))
    }

    fun hud(context: Context, text: String) {
        if (!ImaaApp.prefs.hudEnabled) return
        val svc = ControlService.instance
        if (svc != null) svc.showHud(text) else Toast.makeText(context.applicationContext, text, Toast.LENGTH_SHORT).show()
    }
}
