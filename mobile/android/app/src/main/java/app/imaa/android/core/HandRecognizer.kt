package app.imaa.android.core

import app.imaa.android.core.Geo.angleAt
import app.imaa.android.core.Geo.angleDiff
import app.imaa.android.core.Geo.direction
import app.imaa.android.core.Geo.dist
import kotlin.math.abs
import kotlin.math.min

/**
 * Hand gestures from the 21 MediaPipe landmarks — a direct port of the desktop recogniser
 * (desktop/imaa/core/hand.py) so both apps behave the same. Landmarks must be mirrored and in height units.
 */
class HandRecognizer {
    var holdScale = 1f
    var swipeEnabled = true
    var livePose: String? = null
        private set

    private val repeatMs = 280
    private val cooldownMs = 250
    private val swipeDistance = 0.30f
    private val swipeTime = 0.45f
    private val motionGuard = 1.1f
    private val pinchEnter = 0.28f
    private val pinchExit = 0.42f
    private val pinchTapMs = 450
    private val pinchDragDelayMs = 350
    private val pinchDragStep = 0.07f
    private val joyDeadzone = 0.035f
    private val joyRange = 0.15f
    private val joyIntervalMs = 90
    private val holdMs = mapOf(
        "thumb_up" to 300, "thumb_down" to 300, "point_right" to 300, "point_left" to 300,
        "victory" to 550, "call" to 600, "fist" to 600, "rock" to 1200, "three" to 550,
    )

    data class Features(
        val palm: Float,
        val extended: BooleanArray,
        val thumbDir: Float,
        val indexDir: Float,
        val pinchRatio: Float,
        val indexReach: Float,
        val center: P,
        val indexTip: P,
        val pinchPoint: P,
    )

    private data class Sample(val t: Float, val x: Float, val y: Float, val open: Boolean)

    private var raw: String? = null
    private var rawCount = 0
    private var stable: String? = null
    private var stableSince = 0f
    private var fired: String? = null
    private var lastRepeat = 0f
    private var lastStart = -10f
    private val history = ArrayDeque<Sample>()
    private var swipeBlockUntil = 0f
    private var pinching = false
    private var pinchStart = 0f
    private var pinchOrigin = P(0f, 0f)
    private var dragging = false
    private var dragRef = 0f
    private var dragDir: String? = null
    private var joyActive = false
    private var joyAnchor = 0f
    private var joyLast = 0f
    private var joyDir: String? = null

    fun reset() {
        raw = null; rawCount = 0; stable = null; stableSince = 0f; fired = null
        lastRepeat = 0f; lastStart = -10f; history.clear(); swipeBlockUntil = 0f
        pinching = false; dragging = false; dragDir = null
        joyActive = false; joyDir = null; livePose = null
    }

    fun update(lm: List<P>?, t: Float): List<GestureEvent> {
        if (lm == null) {
            reset()
            return emptyList()
        }
        val f = analyze(lm)
        val events = mutableListOf<GestureEvent>()
        val label = classify(f)
        history.addLast(Sample(t, f.center.x, f.center.y, label == "open_palm"))
        while (history.isNotEmpty() && t - history.first().t > maxOf(swipeTime, 0.2f)) history.removeFirst()
        val speed = speed(t)
        updateStable(label, t)

        if (swipeEnabled) detectSwipe(t)?.let { events += it }
        val (pinchEvents, pinchActive) = updatePinch(f, t)
        events += pinchEvents
        if (pinchActive) {
            livePose = "pinch"
            joyActive = false
            return events
        }
        events += updateJoystick(f, t)
        if (speed <= motionGuard) events += updateStatic(t) else stableSince = t
        return events
    }

    private fun speed(t: Float): Float {
        val recent = history.filter { t - it.t <= 0.15f }
        if (recent.size < 2) return 0f
        val dt = recent.last().t - recent.first().t
        if (dt <= 0f) return 0f
        return dist(P(recent.first().x, recent.first().y), P(recent.last().x, recent.last().y)) / dt
    }

    private fun updateStable(label: String?, t: Float) {
        if (label == raw) rawCount++ else { raw = label; rawCount = 1 }
        if (rawCount >= 2 && label != stable) {
            stable = label
            stableSince = t
            if (label != fired) fired = null
        }
        livePose = stable
    }

    private fun start(gesture: String, t: Float, magnitude: Float = 1f): GestureEvent? {
        if (t - lastStart < cooldownMs / 1000f) return null
        lastStart = t
        return GestureEvent(gesture, "start", magnitude, "hand")
    }

    private fun detectSwipe(t: Float): GestureEvent? {
        if (t < swipeBlockUntil || history.size < 3) return null
        val openRatio = history.count { it.open }.toFloat() / history.size
        if (openRatio < 0.6f) return null
        val dx = history.last().x - history.first().x
        val dy = history.last().y - history.first().y
        if (abs(dx) >= swipeDistance && abs(dy) < abs(dx) * 0.6f) {
            swipeBlockUntil = t + 0.8f
            history.clear()
            stableSince = t
            return start(if (dx > 0) "swipe_right" else "swipe_left", t)
        }
        return null
    }

    private fun updatePinch(f: Features, t: Float): Pair<List<GestureEvent>, Boolean> {
        val events = mutableListOf<GestureEvent>()
        val canPinch = f.indexReach > 1.15f && stable !in setOf("fist", "thumb_up", "thumb_down")
        if (!pinching) {
            if (canPinch && f.pinchRatio < pinchEnter) {
                pinching = true; pinchStart = t; pinchOrigin = f.pinchPoint; dragging = false; dragDir = null
            }
            return events to pinching
        }
        if (f.pinchRatio > pinchExit) {
            val moved = dist(f.pinchPoint, pinchOrigin)
            if (!dragging && (t - pinchStart) * 1000 <= pinchTapMs && moved < 0.08f) start("pinch", t)?.let { events += it }
            pinching = false
            dragging = false
            return events to false
        }
        if (!dragging && (t - pinchStart) * 1000 >= pinchDragDelayMs) {
            dragging = true
            dragRef = f.pinchPoint.y
        }
        if (dragging) {
            var delta = dragRef - f.pinchPoint.y
            while (abs(delta) >= pinchDragStep) {
                val d = if (delta > 0) "up" else "down"
                events += GestureEvent("pinch_drag_$d", if (dragDir == d) "repeat" else "start", 1f, "hand")
                dragDir = d
                dragRef -= if (delta > 0) pinchDragStep else -pinchDragStep
                delta = dragRef - f.pinchPoint.y
            }
        }
        return events to true
    }

    private fun updateJoystick(f: Features, t: Float): List<GestureEvent> {
        if (stable != "point_up") {
            joyActive = false; joyDir = null
            return emptyList()
        }
        if (!joyActive) {
            if ((t - stableSince) * 1000 >= 220 * holdScale) {
                joyActive = true; joyAnchor = f.indexTip.y; joyLast = t
            }
            return emptyList()
        }
        val offset = joyAnchor - f.indexTip.y
        val excess = abs(offset) - joyDeadzone
        if (excess <= 0 || (t - joyLast) * 1000 < joyIntervalMs) {
            if (excess <= 0) joyDir = null
            return emptyList()
        }
        joyLast = t
        val d = if (offset > 0) "up" else "down"
        val magnitude = 0.25f + 0.75f * min(1f, excess / joyRange)
        val phase = if (joyDir == d) "repeat" else "start"
        joyDir = d
        return listOf(GestureEvent("index_up_move_$d", phase, magnitude, "hand"))
    }

    private fun updateStatic(t: Float): List<GestureEvent> {
        val label = stable ?: return emptyList()
        if (label !in STATIC_POSES) return emptyList()
        val hold = (holdMs[label] ?: 400) * holdScale / 1000f
        if (t - stableSince < hold) return emptyList()
        if (fired != label) {
            val ev = start(label, t) ?: return emptyList()
            fired = label
            lastRepeat = t
            return listOf(ev)
        }
        if ((t - lastRepeat) * 1000 >= repeatMs) {
            lastRepeat = t
            return listOf(GestureEvent(label, "repeat", 1f, "hand"))
        }
        return emptyList()
    }

    companion object {
        val STATIC_POSES = setOf("thumb_up", "thumb_down", "point_right", "point_left", "victory", "call", "fist", "rock", "three")
        private val FINGERS = listOf(intArrayOf(5, 6, 7, 8), intArrayOf(9, 10, 11, 12), intArrayOf(13, 14, 15, 16), intArrayOf(17, 18, 19, 20))

        fun analyze(lm: List<P>): Features {
            val wrist = lm[0]
            val palm = maxOf(dist(wrist, lm[9]), 1e-6f)
            val ext = BooleanArray(5)
            FINGERS.forEachIndexed { i, (mcp, pip, _, tip) ->
                val far = dist(wrist, lm[tip]) > dist(wrist, lm[pip]) * 1.2f
                val straight = angleAt(lm[mcp], lm[pip], lm[tip]) > 130f
                ext[i + 1] = far && straight
            }
            val thumbStraight = angleAt(lm[2], lm[3], lm[4]) > 140f
            val thumbAway = dist(lm[4], lm[5]) > 0.6f * palm && dist(lm[4], lm[17]) > dist(lm[2], lm[17]) * 1.05f
            ext[0] = thumbStraight && thumbAway
            return Features(
                palm = palm,
                extended = ext,
                thumbDir = direction(lm[2], lm[4]),
                indexDir = direction(lm[5], lm[8]),
                pinchRatio = dist(lm[4], lm[8]) / palm,
                indexReach = dist(wrist, lm[8]) / palm,
                center = Geo.mean(listOf(lm[0], lm[5], lm[9], lm[13], lm[17])),
                indexTip = lm[8],
                pinchPoint = Geo.mean(listOf(lm[4], lm[8])),
            )
        }

        fun classify(f: Features, tol: Float = 35f): String? {
            val (thumb, index, middle, ring, pinky) = f.extended.toList()
            val four = listOf(index, middle, ring, pinky)
            return when (four) {
                listOf(false, false, false, false) -> when {
                    !thumb -> "fist"
                    angleDiff(f.thumbDir, 90f) <= tol + 5 -> "thumb_up"
                    angleDiff(f.thumbDir, -90f) <= tol + 5 -> "thumb_down"
                    else -> null
                }
                listOf(true, false, false, false) -> when {
                    angleDiff(f.indexDir, 0f) <= tol -> "point_right"
                    angleDiff(f.indexDir, 180f) <= tol -> "point_left"
                    angleDiff(f.indexDir, 90f) <= tol -> "point_up"
                    else -> null
                }
                listOf(true, true, false, false) -> "victory"
                listOf(true, true, true, false) -> "three"
                listOf(true, false, false, true) -> "rock"
                listOf(false, false, false, true) -> if (thumb) "call" else null
                listOf(true, true, true, true) -> "open_palm"
                else -> null
            }
        }
    }
}
