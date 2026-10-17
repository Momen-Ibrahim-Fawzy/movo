package app.movo.android.core

import org.junit.Assert.assertEquals
import org.junit.Test

/** Mirrors desktop/tests/test_eyes.py. */
class EyeRecognizerTest {
    private val open = 0.30f
    private val closed = 0.08f

    private fun eye(l: Float = open, r: Float = open, gx: Float = 0f) =
        EyeFeatures(l, r, if (l > 0.2f) 0.05f else 0.9f, if (r > 0.2f) 0.05f else 0.9f, gx)

    private fun frames(f: EyeFeatures, seconds: Float) = List(maxOf(1, Math.round(seconds * 20))) { f }

    private fun run(rec: EyeRecognizer, seq: List<EyeFeatures>, t0: Float = 0f, yaw: Float = 0f): Pair<List<String>, Float> {
        var t = t0
        val names = seq.flatMap { f -> rec.update(f, t, yaw).also { t += 0.05f } }.filter { it.phase == "start" }.map { it.gesture }
        return names to t
    }

    private fun warm(glasses: Boolean = false) = EyeRecognizer().apply { this.glasses = glasses; run(this, frames(eye(), 1.5f)) }

    @Test fun naturalBlinkIgnored() {
        assertEquals(emptyList<String>(), run(warm(), frames(eye(), 0.5f) + frames(eye(closed, closed), 0.15f) + frames(eye(), 2f), 1.5f).first)
    }

    @Test fun doubleBlink() {
        for (g in listOf(false, true)) {
            val seq = frames(eye(closed, closed), 0.2f) + frames(eye(), 0.25f) + frames(eye(closed, closed), 0.2f) + frames(eye(), 0.5f)
            assertEquals(listOf("blink_double"), run(warm(g), seq, 1.5f).first)
        }
    }

    @Test fun winksAndClosed() {
        assertEquals(listOf("wink_left"), run(warm(), frames(eye(closed, open), 0.6f) + frames(eye(), 0.4f), 1.5f).first)
        assertEquals(listOf("wink_right"), run(warm(true), frames(eye(open, closed), 0.6f) + frames(eye(), 0.4f), 1.5f).first)
        assertEquals(listOf("eyes_closed"), run(warm(), frames(eye(closed, closed), 3f) + frames(eye(), 0.5f), 1.5f).first)
    }

    @Test fun turnedHeadBlocks() {
        assertEquals(emptyList<String>(), run(warm(), frames(eye(closed, open), 0.8f), 1.5f, yaw = 30f).first)
    }

    @Test fun calibrationRoundTrip() {
        val c = EyeCalibration(0.42f, 0.41f, 0.2f, 0.21f, 0.05f, null, 0.01f, -0.02f)
        assertEquals(c, EyeCalibration.decode(c.encode()))
    }
}
