package app.imaa.android.core

import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.sin

data class FaceObservation(
    val yaw: Float,
    val pitch: Float,
    val roll: Float,
    val expressions: Map<String, Float>? = null,
    val eyes: EyeFeatures? = null,
)

/** Port of desktop/imaa/core/head.py: head pose relative to the user's own neutral pose. */
class HeadRecognizer {
    var sensitivity = 1f
    var holdScale = 1f
    var livePose: String? = null
        private set
    var delta = Triple(0f, 0f, 0f)
        private set
    var lastEventAt = -10f
        private set

    private val turnDeg = 20f
    private val tiltDeg = 15f
    private val lookUpDeg = 12f
    private val lookDownDeg = 12f
    private val holdMs = 450
    private val repeatMs = 380
    private val nodDeg = 9f
    private val shakeDeg = 9f
    private val exprThreshold = 0.5f
    private val exprHold = mapOf("mouth_open" to 350, "smile" to 450, "brows_up" to 400)
    private val calibrationFrames = 12

    private val samples = mutableListOf<Triple<Float, Float, Float>>()
    var baseline: Triple<Float, Float, Float>? = null
        private set
    private var holdLabel: String? = null
    private var holdSince = 0f
    private var fired: String? = null
    private var lastRepeat = 0f
    private val pitchHist = ArrayDeque<Triple<Float, Float, Float>>()
    private val yawHist = ArrayDeque<Triple<Float, Float, Float>>()
    private var blockUntil = 0f
    private val exprSince = mutableMapOf<String, Float?>()
    private val exprFired = mutableSetOf<String>()

    fun recalibrate() {
        samples.clear(); baseline = null; holdLabel = null; fired = null
        pitchHist.clear(); yawHist.clear(); blockUntil = 0f; exprSince.clear(); exprFired.clear()
    }

    fun update(obs: FaceObservation?, t: Float): List<GestureEvent> {
        if (obs == null) {
            holdLabel = null; fired = null; livePose = null; pitchHist.clear(); yawHist.clear()
            return emptyList()
        }
        val base = baseline
        if (base == null) {
            samples += Triple(obs.yaw, obs.pitch, obs.roll)
            if (samples.size >= calibrationFrames) {
                baseline = Triple(
                    samples.map { it.first }.sorted()[samples.size / 2],
                    samples.map { it.second }.sorted()[samples.size / 2],
                    samples.map { it.third }.sorted()[samples.size / 2],
                )
            }
            return emptyList()
        }
        val dy = obs.yaw - base.first
        val dp = obs.pitch - base.second
        val dr = obs.roll - base.third
        delta = Triple(dy, dp, dr)
        if (abs(dy) < 5 && abs(dp) < 5 && abs(dr) < 5) {
            val a = 0.01f
            baseline = Triple(base.first * (1 - a) + obs.yaw * a, base.second * (1 - a) + obs.pitch * a, base.third * (1 - a) + obs.roll * a)
        }
        val events = mutableListOf<GestureEvent>()
        events += dynamic(dy, dp, t)
        events += holds(dy, dp, dr, t)
        obs.expressions?.let { events += expressions(it, t) }
        if (events.isNotEmpty()) lastEventAt = t
        return events
    }

    private fun dynamic(dy: Float, dp: Float, t: Float): List<GestureEvent> {
        pitchHist.addLast(Triple(t, dp, dy))
        yawHist.addLast(Triple(t, dy, dp))
        while (pitchHist.isNotEmpty() && t - pitchHist.first().first > 1.0f) pitchHist.removeFirst()
        while (yawHist.isNotEmpty() && t - yawHist.first().first > 1.4f) yawHist.removeFirst()
        if (t < blockUntil) return emptyList()

        val nod = nodDeg / sensitivity
        val below = pitchHist.filter { it.second < -nod }
        if (below.isNotEmpty() && dp > -nod / 3) {
            val span = below.last().first - below.first().first
            if (span < 0.5f && pitchHist.first().second > -nod / 2 && pitchHist.maxOf { abs(it.third) } < 12f) return fire("nod", t)
        }
        val shake = shakeDeg / sensitivity
        val signs = mutableListOf<Int>()
        for ((_, y, p) in yawHist) {
            if (abs(p) > 14f) { signs.clear(); break }
            val s = if (y > shake) 1 else if (y < -shake) -1 else 0
            if (s != 0 && (signs.isEmpty() || signs.last() != s)) signs += s
        }
        if (signs.size >= 3) return fire("shake", t)
        return emptyList()
    }

    private fun fire(name: String, t: Float): List<GestureEvent> {
        blockUntil = t + 1f
        pitchHist.clear(); yawHist.clear(); holdLabel = null
        livePose = name
        return listOf(GestureEvent(name, "start", 1f, "head"))
    }

    private fun holds(dy: Float, dp: Float, dr: Float, t: Float): List<GestureEvent> {
        val candidates = listOf(
            Triple("turn_right", dy, turnDeg), Triple("turn_left", -dy, turnDeg),
            Triple("look_up", dp, lookUpDeg), Triple("look_down", -dp, lookDownDeg),
            Triple("tilt_right", dr, tiltDeg), Triple("tilt_left", -dr, tiltDeg),
        ).mapNotNull { (label, value, thr) -> val th = thr / sensitivity; if (value > th) (value / th) to label else null }
        val label = candidates.maxByOrNull { it.first }?.second
        if (label != holdLabel) {
            holdLabel = label
            holdSince = t
            if (label == null) fired = null
        }
        livePose = label ?: if (t < blockUntil) livePose else null
        if (label == null || t < blockUntil) return emptyList()
        if ((t - holdSince) * 1000 < holdMs * holdScale) return emptyList()
        if (fired != label) {
            fired = label; lastRepeat = t
            return listOf(GestureEvent(label, "start", 1f, "head"))
        }
        if ((t - lastRepeat) * 1000 >= repeatMs) {
            lastRepeat = t
            return listOf(GestureEvent(label, "repeat", 1f, "head"))
        }
        return emptyList()
    }

    private fun expressions(expr: Map<String, Float>, t: Float): List<GestureEvent> {
        val events = mutableListOf<GestureEvent>()
        val on = exprThreshold / sensitivity
        val off = on * 0.6f
        for ((name, hold) in exprHold) {
            val v = expr[name] ?: 0f
            val since = exprSince[name]
            if (v >= on) {
                if (since == null) exprSince[name] = t
                else if (name !in exprFired && (t - since) * 1000 >= hold * holdScale) {
                    exprFired += name
                    livePose = name
                    events += GestureEvent(name, "start", 1f, "head")
                }
            } else if (v < off) {
                exprSince[name] = null
                exprFired -= name
            }
        }
        return events
    }

    companion object {
        /** Raw (yaw, pitch, roll) proxies in degrees from two eye centres and the nose tip. */
        fun poseFromPoints(a: P, b: P, nose: P): Triple<Float, Float, Float> {
            val (left, right) = if (a.x <= b.x) a to b else b to a
            val ex = right.x - left.x
            val ey = right.y - left.y
            val eyeDist = maxOf(hypot(ex, ey), 1e-6f)
            val r = atan2(ey, ex)
            val roll = Math.toDegrees(r.toDouble()).toFloat()
            val mx = (left.x + right.x) / 2
            val my = (left.y + right.y) / 2
            val nx = nose.x - mx
            val ny = nose.y - my
            val lx = (nx * cos(-r) - ny * sin(-r)) / eyeDist
            val ly = (nx * sin(-r) + ny * cos(-r)) / eyeDist
            val yaw = Math.toDegrees(atan2(lx, 0.5f).toDouble()).toFloat()
            val pitch = -ly * 119f
            return Triple(yaw, pitch, roll)
        }
    }
}
