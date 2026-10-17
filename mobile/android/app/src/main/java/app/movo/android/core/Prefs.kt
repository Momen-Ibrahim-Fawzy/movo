package app.movo.android.core

import android.content.Context
import android.content.SharedPreferences
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import org.json.JSONObject

/** Settings stored on the device only. ``version`` changes on every write so Compose can recompose. */
class Prefs(context: Context) {
    private val sp: SharedPreferences = context.getSharedPreferences("movo", Context.MODE_PRIVATE)
    private val _version = MutableStateFlow(0)
    val version: StateFlow<Int> = _version

    private fun changed() {
        _version.value = _version.value + 1
    }

    private fun str(key: String, def: String) = sp.getString(key, def) ?: def
    private fun putStr(key: String, v: String) { sp.edit().putString(key, v).apply(); changed() }
    private fun putBool(key: String, v: Boolean) { sp.edit().putBoolean(key, v).apply(); changed() }
    private fun putFloat(key: String, v: Float) { sp.edit().putFloat(key, v).apply(); changed() }

    var language: String get() = str("language", "system"); set(v) = putStr("language", v)
    var theme: String get() = str("theme", "system"); set(v) = putStr("theme", v)
    var handEnabled: Boolean get() = sp.getBoolean("hand_enabled", true); set(v) = putBool("hand_enabled", v)
    var headEnabled: Boolean get() = sp.getBoolean("head_enabled", false); set(v) = putBool("head_enabled", v)
    var headMode: String get() = str("head_mode", "light"); set(v) = putStr("head_mode", v)
    var holdScale: Float get() = sp.getFloat("hold_scale", 1f); set(v) = putFloat("hold_scale", v)
    var headSensitivity: Float get() = sp.getFloat("head_sensitivity", 1f); set(v) = putFloat("head_sensitivity", v)
    var powerMode: String get() = str("power_mode", "balanced"); set(v) = putStr("power_mode", v)
    var hudEnabled: Boolean get() = sp.getBoolean("hud_enabled", true); set(v) = putBool("hud_enabled", v)
    var practice: Boolean get() = sp.getBoolean("practice", false); set(v) = putBool("practice", v)
    var remoteEnabled: Boolean get() = sp.getBoolean("remote_enabled", false); set(v) = putBool("remote_enabled", v)
    var remoteHost: String get() = str("remote_host", ""); set(v) = putStr("remote_host", v)
    var remotePort: Int get() = sp.getInt("remote_port", 47813); set(v) { sp.edit().putInt("remote_port", v).apply(); changed() }
    var remoteCode: String get() = str("remote_code", ""); set(v) = putStr("remote_code", v)
    var eyesEnabled: Boolean get() = sp.getBoolean("eyes_enabled", false); set(v) = putBool("eyes_enabled", v)
    var eyesGlasses: Boolean get() = sp.getBoolean("eyes_glasses", false); set(v) = putBool("eyes_glasses", v)
    var eyesSensitivity: Float get() = sp.getFloat("eyes_sensitivity", 1f); set(v) = putFloat("eyes_sensitivity", v)
    var eyesCalibration: String get() = str("eyes_calibration", ""); set(v) = putStr("eyes_calibration", v)
    var disclosureAccepted: Boolean get() = sp.getBoolean("disclosure", false); set(v) = putBool("disclosure", v)

    fun targetFps(): Int = when (powerMode) { "eco" -> 10; "performance" -> 24; else -> 15 }

    private fun bindings(): JSONObject = runCatching { JSONObject(str("bindings", "{}")) }.getOrDefault(JSONObject())

    fun binding(gesture: String): String {
        val custom = bindings().optString(gesture, "")
        return if (custom.isNotEmpty() && custom in Catalog.actionsById) custom else Catalog.defaultBindings[gesture] ?: "none"
    }

    fun setBinding(gesture: String, action: String) {
        val b = bindings()
        if (action == Catalog.defaultBindings[gesture]) b.remove(gesture) else b.put(gesture, action)
        putStr("bindings", b.toString())
    }

    fun gestureEnabled(gesture: String): Boolean = gesture !in (sp.getStringSet("disabled", emptySet()) ?: emptySet())

    fun setGestureEnabled(gesture: String, enabled: Boolean) {
        val set = (sp.getStringSet("disabled", emptySet()) ?: emptySet()).toMutableSet()
        if (enabled) set -= gesture else set += gesture
        sp.edit().putStringSet("disabled", set).apply()
        changed()
    }
}
