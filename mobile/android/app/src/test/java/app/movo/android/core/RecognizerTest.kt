package app.movo.android.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.cos
import kotlin.math.sin

/** Same synthetic hands and faces as desktop/tests, so both platforms are held to the same behaviour. */
class RecognizerTest {
    private val mcps = mapOf(1 to P(-0.045f, -0.17f), 2 to P(0f, -0.18f), 3 to P(0.04f, -0.17f), 4 to P(0.075f, -0.15f))

    private fun finger(m: P, ext: Boolean) = if (ext) {
        listOf(m, P(m.x, m.y - 0.06f), P(m.x, m.y - 0.10f), P(m.x, m.y - 0.135f))
    } else {
        listOf(m, P(m.x, m.y - 0.045f), P(m.x + 0.005f, m.y - 0.015f), P(m.x + 0.005f, m.y + 0.02f))
    }

    private fun thumb(ext: Boolean) = if (ext) {
        listOf(P(-0.03f, -0.03f), P(-0.07f, -0.07f), P(-0.11f, -0.085f), P(-0.15f, -0.10f))
    } else {
        listOf(P(-0.03f, -0.03f), P(-0.06f, -0.07f), P(-0.05f, -0.11f), P(-0.01f, -0.13f))
    }

    private fun hand(
        t: Boolean = false, i: Boolean = false, m: Boolean = false, r: Boolean = false, p: Boolean = false,
        rotate: Float = 0f, atX: Float = 0.65f, atY: Float = 0.6f,
    ): List<P> {
        val pts = mutableListOf(P(0f, 0f)) + thumb(t) + finger(mcps[1]!!, i) + finger(mcps[2]!!, m) + finger(mcps[3]!!, r) + finger(mcps[4]!!, p)
        val rad = Math.toRadians(rotate.toDouble())
        return pts.map {
            val rx = it.x * cos(rad) + it.y * sin(rad)
            val ry = -it.x * sin(rad) + it.y * cos(rad)
            P(atX + rx.toFloat(), atY + ry.toFloat())
        }
    }

    private fun pinchHand(closed: Boolean, atY: Float = 0.6f): List<P> {
        val tip = if (closed) P(-0.112f, -0.20f) else P(-0.16f, -0.12f)
        val pts = listOf(P(0f, 0f), P(-0.03f, -0.03f), P(-0.07f, -0.07f), P(-0.10f, -0.13f), tip) +
            listOf(P(-0.045f, -0.17f), P(-0.07f, -0.21f), P(-0.09f, -0.22f), P(-0.11f, -0.21f)) +
            finger(mcps[2]!!, true) + finger(mcps[3]!!, true) + finger(mcps[4]!!, true)
        return pts.map { P(0.65f + it.x, atY + it.y) }
    }

    private fun run(rec: HandRecognizer, frames: List<List<P>>): List<GestureEvent> {
        var t = 0f
        return frames.flatMap { lm -> rec.update(lm, t).also { t += 1 / 30f } }
    }

    @Test
    fun classifiesPoses() {
        val cases = mapOf(
            "open_palm" to hand(t = true, i = true, m = true, r = true, p = true),
            "fist" to hand(),
            "victory" to hand(i = true, m = true),
            "three" to hand(i = true, m = true, r = true),
            "rock" to hand(i = true, p = true),
            "call" to hand(t = true, p = true),
            "point_up" to hand(i = true),
            "thumb_up" to hand(t = true, rotate = -90f),
            "thumb_down" to hand(t = true, rotate = 90f),
            "point_right" to hand(i = true, rotate = -90f),
            "point_left" to hand(i = true, rotate = 90f),
        )
        cases.forEach { (label, lm) -> assertEquals(label, label, HandRecognizer.classify(HandRecognizer.analyze(lm))) }
    }

    @Test
    fun heldPoseFiresOnceThenRepeats() {
        val events = run(HandRecognizer(), List(36) { hand(t = true, rotate = -90f) })
        assertEquals(listOf("thumb_up"), events.filter { it.phase == "start" }.map { it.gesture })
        assertTrue(events.count { it.phase == "repeat" } >= 2)
    }

    @Test
    fun pinchTap() {
        val frames = List(3) { hand(t = true, i = true, m = true, r = true, p = true) } + List(6) { pinchHand(true) } + List(3) { pinchHand(false) }
        assertEquals(listOf("pinch"), run(HandRecognizer(), frames).map { it.gesture })
    }

    @Test
    fun swipeRight() {
        val frames = List(10) { hand(t = true, i = true, m = true, r = true, p = true, atX = 0.3f + 0.05f * it) }
        assertEquals(listOf("swipe_right"), run(HandRecognizer(), frames).map { it.gesture })
    }

    @Test
    fun headTurnAndNod() {
        fun obs(yaw: Float = 0f, pitch: Float = 0f): FaceObservation {
            // eyes ±0.5 and nose (0, 0.7, 0.5) in eye units, rotated by yaw then pitch, scaled to 0.12
            val pr = Math.toRadians(pitch.toDouble()); val yr = Math.toRadians(yaw.toDouble())
            fun proj(x: Double, y: Double, z: Double): P {
                val y1 = y * cos(pr) - z * sin(pr); val z1 = y * sin(pr) + z * cos(pr)
                val x2 = x * cos(yr) + z1 * sin(yr)
                return P((0.65 + x2 * 0.12).toFloat(), (0.5 + y1 * 0.12).toFloat())
            }
            val (yw, pt, rl) = HeadRecognizer.poseFromPoints(proj(-0.5, 0.0, 0.0), proj(0.5, 0.0, 0.0), proj(0.0, 0.7, 0.5))
            return FaceObservation(yw, pt, rl)
        }
        val rec = HeadRecognizer()
        var t = 0f
        repeat(15) { rec.update(obs(), t); t += 1 / 15f }
        val turn = (0 until 12).flatMap { rec.update(obs(yaw = 30f), t).also { t += 1 / 15f } }
        assertEquals(listOf("turn_right"), turn.filter { it.phase == "start" }.map { it.gesture })
        repeat(20) { rec.update(obs(), t); t += 1 / 15f }
        val nod = listOf(0f, -6f, -14f, -16f, -12f, -4f, 0f, 0f).flatMap { rec.update(obs(pitch = it), t).also { t += 1 / 15f } }
        assertEquals(listOf("nod"), nod.map { it.gesture })
    }
}
