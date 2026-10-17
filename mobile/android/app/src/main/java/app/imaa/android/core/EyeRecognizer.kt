package app.imaa.android.core

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

/** Eye features in the user's left/right (see desktop/imaa/core/eyes.py). */
data class EyeFeatures(
    val earLeft: Float,
    val earRight: Float,
    val blinkLeft: Float? = null,
    val blinkRight: Float? = null,
    val gazeX: Float = 0f,
    val gazeY: Float = 0f,
    val lookUp: Float = 0f,
    val lookDown: Float = 0f,
    val smile: Float = 0f,
)

data class EyeCalibration(
    val openEarL: Float, val openEarR: Float, val closedEarL: Float, val closedEarR: Float,
    val openBs: Float?, val closedBs: Float?, val gazeX: Float, val gazeY: Float,
) {
    fun encode(): String = listOf(openEarL, openEarR, closedEarL, closedEarR, openBs ?: -1f, closedBs ?: -1f, gazeX, gazeY).joinToString(",")

    companion object {
        fun decode(s: String): EyeCalibration? {
            val v = s.split(",").mapNotNull { it.toFloatOrNull() }
            if (v.size != 8) return null
            return EyeCalibration(v[0], v[1], v[2], v[3], v[4].takeIf { it >= 0 }, v[5].takeIf { it >= 0 }, v[6], v[7])
        }
    }
}

/** Port of desktop/imaa/core/eyes.py — winks, double/long blinks, eyes closed and held glances, glasses-aware. */
class EyeRecognizer {
    var sensitivity = 1f
    var holdScale = 1f
    var glasses = false
        set(v) { if (v != field) { field = v; configureFilters() } }
    var calibration: EyeCalibration? = null
        set(v) { field = v; v?.let { gazeCenter = floatArrayOf(it.gazeX, it.gazeY); gazeSamples = 999 } }
    var livePose: String? = null
        private set
    var openness = floatArrayOf(1f, 1f)
        private set

    private class Median(n: Int) {
        private val q = ArrayDeque<Float>()
        private val size = n
        operator fun invoke(v: Float): Float {
            q.addLast(v); if (q.size > size) q.removeFirst()
            val s = q.sorted(); return s[s.size / 2]
        }
    }

    private var f = filters()
    private fun filters() = (0 until 8).map { Median(if (glasses) 5 else 3) }
    private fun configureFilters() { f = filters() }

    private val closed = booleanArrayOf(false, false)
    private var bothSince: Float? = null
    private var closedFired = false
    private var lastShort: Float? = null
    private var winkSide: Int? = null
    private var winkSince = 0f
    private var winkFired = false
    private var glance: String? = null
    private var glanceSince = 0f
    private var glanceFired = false
    private var glanceLast = 0f
    private val earHist = ArrayDeque<FloatArray>()
    private var gazeCenter = floatArrayOf(0f, 0f)
    private var gazeSamples = 0
    private var capture: String? = null
    private val captured = mutableMapOf<String, MutableList<FloatArray>>()
    private var muteFor = 0f
    private var muteUntil = -1f

    fun reset() {
        closed[0] = false; closed[1] = false; bothSince = null; closedFired = false; lastShort = null
        winkSide = null; winkFired = false; glance = null; glanceFired = false; livePose = null
    }

    fun beginCapture(kind: String) { captured[kind] = mutableListOf(); capture = kind }
    fun endCapture() { capture = null; muteFor = 1.5f }

    fun finishCalibration(): EyeCalibration? {
        val op = captured["open"].orEmpty(); val cl = captured["closed"].orEmpty()
        captured.clear()
        if (op.size < 5 || cl.size < 5) return null
        fun med(rows: List<FloatArray>, i: Int): Float? = rows.map { it[i] }.filter { it >= 0 }.sorted().let { if (it.isEmpty()) null else it[it.size / 2] }
        val c = EyeCalibration(med(op, 0)!!, med(op, 1)!!, med(cl, 0)!!, med(cl, 1)!!, med(op, 2), med(cl, 2), med(op, 3) ?: 0f, med(op, 4) ?: 0f)
        if (min(c.openEarL - c.closedEarL, c.openEarR - c.closedEarR) < 0.03f) return null
        calibration = c
        return c
    }

    fun update(feat: EyeFeatures?, t: Float, headYaw: Float = 0f, headPitch: Float = 0f, headBusy: Boolean = false): List<GestureEvent> {
        if (feat == null) { reset(); return emptyList() }
        val ear = floatArrayOf(f[0](feat.earLeft), f[1](feat.earRight))
        val bs = arrayOf(feat.blinkLeft?.let { f[2](it) }, feat.blinkRight?.let { f[3](it) })
        val gx = f[4](feat.gazeX); val gy = f[5](feat.gazeY)
        val lookUp = f[6](feat.lookUp); val lookDown = f[7](feat.lookDown)
        if (muteFor > 0f) { muteUntil = t + muteFor; muteFor = 0f }
        capture?.let { kind ->
            val bsMean = if (bs[0] != null && bs[1] != null) (bs[0]!! + bs[1]!!) / 2 else -1f
            captured[kind]?.add(floatArrayOf(ear[0], ear[1], bsMean, gx, gy))
            bothSince = null; winkSide = null; glance = null
            return emptyList()
        }
        val frontal = abs(headYaw) < 20f && abs(headPitch) < 20f
        if (frontal) { earHist.addLast(ear); if (earHist.size > 400) earHist.removeFirst() }
        val closure = floatArrayOf(closure(0, ear[0], bs[0], lookDown), closure(1, ear[1], bs[1], lookDown))
        openness = floatArrayOf(1 - closure[0], 1 - closure[1])
        if (!frontal || headBusy || t < muteUntil) { bothSince = null; winkSide = null; glance = null; livePose = null; return emptyList() }

        val on = min(0.85f, 0.6f / sensitivity)
        for (i in 0..1) {
            if (!closed[i] && closure[i] >= on) closed[i] = true
            else if (closed[i] && closure[i] <= 0.35f) closed[i] = false
        }
        val events = mutableListOf<GestureEvent>()
        events += blinks(t)
        events += winks(t, closure, feat.smile)
        val bothOpen = !closed[0] && !closed[1]
        if (bothOpen) updateGazeCenter(gx, gy, headYaw, headPitch)
        events += glances(t, gx, gy, lookUp, lookDown, bothOpen, headYaw, headPitch)
        return events
    }

    private fun openLevel(i: Int): Float {
        calibration?.let { return if (i == 0) it.openEarL else it.openEarR }
        if (earHist.size >= 15) { val v = earHist.map { it[i] }.sorted(); return v[(v.size * 0.9f).toInt() - 1] }
        return earHist.maxOfOrNull { it[i] } ?: 0.3f
    }

    private fun closure(i: Int, ear: Float, bsIn: Float?, lookDown: Float): Float {
        val open = max(openLevel(i), 1e-3f)
        val cal = calibration
        val closedEar = cal?.let { if (i == 0) it.closedEarL else it.closedEarR }
        val span = if (closedEar != null) open - closedEar else 0.6f * open
        val geo = ((open - ear) / max(span, 1e-3f)).coerceIn(0f, 1f)
        var c = geo
        if (bsIn != null) {
            var bs = bsIn
            if (cal?.openBs != null && cal.closedBs != null) bs = ((bs - cal.openBs) / max(cal.closedBs - cal.openBs, 0.05f)).coerceIn(0f, 1f)
            val w = if (glasses) 0.6f else 0.5f
            c = w * bs + (1 - w) * geo
            if (geo >= 0.9f && bs >= 0.3f) c = max(c, 0.75f)
        }
        return (c - 0.35f * lookDown).coerceIn(0f, 1f)
    }

    private fun blinks(t: Float): List<GestureEvent> {
        val both = closed[0] && closed[1]
        if (both) {
            val since = bothSince
            if (since == null) bothSince = t
            else if (!closedFired && t - since >= 2f * holdScale) {
                closedFired = true; lastShort = null; livePose = "eyes_closed"
                return listOf(GestureEvent("eyes_closed", "start", 1f, "eye"))
            }
            return emptyList()
        }
        val since = bothSince ?: return emptyList()
        val d = t - since
        bothSince = null
        if (closedFired) { closedFired = false; return emptyList() }
        if (d >= 0.6f * holdScale && d <= 1.5f * max(1f, holdScale)) {
            lastShort = null; livePose = "blink_long"
            return listOf(GestureEvent("blink_long", "start", 1f, "eye"))
        }
        if (d in 0.06f..0.45f) {
            val last = lastShort
            if (last != null && t - last <= 0.8f) {
                lastShort = null; livePose = "blink_double"
                return listOf(GestureEvent("blink_double", "start", 1f, "eye"))
            }
            lastShort = t
        }
        return emptyList()
    }

    private fun winks(t: Float, closure: FloatArray, smile: Float): List<GestureEvent> {
        var side: Int? = null
        if (closed[0] != closed[1]) {
            val i = if (closed[0]) 0 else 1
            if (closure[1 - i] < 0.3f && smile < 0.5f) side = i
        }
        if (side != winkSide) {
            winkSide = side; winkSince = t
            if (side == null) winkFired = false
            return emptyList()
        }
        if (side == null || winkFired) return emptyList()
        if (t - winkSince >= 0.35f * holdScale) {
            winkFired = true
            val name = if (side == 0) "wink_left" else "wink_right"
            livePose = name
            return listOf(GestureEvent(name, "start", 1f, "eye"))
        }
        return emptyList()
    }

    private fun updateGazeCenter(gx: Float, gy: Float, yaw: Float, pitch: Float) {
        if (calibration != null || abs(yaw) > 5 || abs(pitch) > 5) return
        if (gazeSamples < 15) {
            val n = gazeSamples + 1
            gazeCenter = floatArrayOf(gazeCenter[0] + (gx - gazeCenter[0]) / n, gazeCenter[1] + (gy - gazeCenter[1]) / n)
            gazeSamples = n
        } else if (abs(gx - gazeCenter[0]) < 0.05f && abs(gy - gazeCenter[1]) < 0.04f) {
            gazeCenter = floatArrayOf(gazeCenter[0] * 0.99f + gx * 0.01f, gazeCenter[1] * 0.99f + gy * 0.01f)
        }
    }

    private fun glances(t: Float, gx: Float, gy: Float, up: Float, down: Float, bothOpen: Boolean, yaw: Float, pitch: Float): List<GestureEvent> {
        val k = sensitivity
        val hx = (gx - gazeCenter[0]) / (0.10f / k)
        val vIris = (gy - gazeCenter[1]) / (0.08f / k)
        val vy = if (up != 0f || down != 0f) (vIris + (up - down) / (0.5f / k)) / 2 else vIris
        var label: String? = null
        if (bothOpen && abs(yaw) < 8 && abs(pitch) < 8 && gazeSamples >= 15) {
            val best = listOf(hx to "eye_look_right", -hx to "eye_look_left", vy to "eye_look_up", -vy to "eye_look_down").maxBy { it.first }
            if (best.first >= 1f) label = best.second
        }
        if (label != glance) {
            glance = label; glanceSince = t; glanceFired = false
            return emptyList()
        }
        if (label == null || t - glanceSince < 0.6f * holdScale) return emptyList()
        livePose = label
        if (!glanceFired) { glanceFired = true; glanceLast = t; return listOf(GestureEvent(label, "start", 1f, "eye")) }
        if (t - glanceLast >= 0.4f) { glanceLast = t; return listOf(GestureEvent(label, "repeat", 1f, "eye")) }
        return emptyList()
    }
}

/** Shared between the camera service and the calibration dialog (same process). */
object Eyes {
    val recognizer = EyeRecognizer()
}
