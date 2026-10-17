package app.movo.android.core

import kotlin.math.abs
import kotlin.math.acos
import kotlin.math.atan2
import kotlin.math.hypot

/** 2-D point in height units (x multiplied by the frame aspect ratio), y pointing down. */
data class P(val x: Float, val y: Float)

object Geo {
    fun dist(a: P, b: P): Float = hypot(a.x - b.x, a.y - b.y)

    /** Angle ABC in degrees (180 = straight). */
    fun angleAt(a: P, b: P, c: P): Float {
        val v1x = a.x - b.x
        val v1y = a.y - b.y
        val v2x = c.x - b.x
        val v2y = c.y - b.y
        val n1 = hypot(v1x, v1y)
        val n2 = hypot(v2x, v2y)
        if (n1 < 1e-9f || n2 < 1e-9f) return 180f
        val cos = ((v1x * v2x + v1y * v2y) / (n1 * n2)).coerceIn(-1f, 1f)
        return Math.toDegrees(acos(cos).toDouble()).toFloat()
    }

    /** Direction a→b in degrees with y pointing up: 0 right, 90 up, ±180 left, -90 down. */
    fun direction(a: P, b: P): Float = Math.toDegrees(atan2(-(b.y - a.y), b.x - a.x).toDouble()).toFloat()

    fun angleDiff(a: Float, b: Float): Float {
        var d = (a - b + 180f) % 360f
        if (d < 0) d += 360f
        return abs(d - 180f)
    }

    fun mean(points: List<P>): P = P(points.map { it.x }.average().toFloat(), points.map { it.y }.average().toFloat())
}
