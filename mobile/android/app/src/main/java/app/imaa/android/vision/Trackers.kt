package app.imaa.android.vision

import android.content.Context
import app.imaa.android.core.EyeFeatures
import app.imaa.android.core.FaceObservation
import app.imaa.android.core.Geo
import app.imaa.android.core.HeadRecognizer
import app.imaa.android.core.P
import com.google.mediapipe.framework.image.MPImage
import com.google.mediapipe.tasks.core.BaseOptions
import com.google.mediapipe.tasks.core.Delegate
import com.google.mediapipe.tasks.vision.core.RunningMode
import com.google.mediapipe.tasks.vision.facedetector.FaceDetector
import com.google.mediapipe.tasks.vision.facelandmarker.FaceLandmarker
import com.google.mediapipe.tasks.vision.handlandmarker.HandLandmarker

private fun base(model: String) = BaseOptions.builder().setModelAssetPath(model).setDelegate(Delegate.CPU).build()

class HandTracker(context: Context) : AutoCloseable {
    private val landmarker = HandLandmarker.createFromOptions(
        context,
        HandLandmarker.HandLandmarkerOptions.builder()
            .setBaseOptions(base("hand_landmarker.task"))
            .setRunningMode(RunningMode.VIDEO)
            .setNumHands(1)
            .setMinHandDetectionConfidence(0.6f)
            .setMinHandPresenceConfidence(0.6f)
            .setMinTrackingConfidence(0.5f)
            .build(),
    )

    /** Landmarks of the most confident hand in height units (x × aspect), or null. */
    fun detect(image: MPImage, timestampMs: Long, aspect: Float): List<P>? {
        val result = landmarker.detectForVideo(image, timestampMs)
        val hand = result.landmarks().firstOrNull() ?: return null
        return hand.map { P(it.x() * aspect, it.y()) }
    }

    override fun close() = landmarker.close()
}

class FaceTracker(context: Context, val accurate: Boolean) : AutoCloseable {
    private val detector: FaceDetector? = if (!accurate) {
        FaceDetector.createFromOptions(
            context,
            FaceDetector.FaceDetectorOptions.builder()
                .setBaseOptions(base("blaze_face_short_range.tflite"))
                .setRunningMode(RunningMode.VIDEO)
                .setMinDetectionConfidence(0.6f)
                .build(),
        )
    } else null

    private val landmarker: FaceLandmarker? = if (accurate) {
        FaceLandmarker.createFromOptions(
            context,
            FaceLandmarker.FaceLandmarkerOptions.builder()
                .setBaseOptions(base("face_landmarker.task"))
                .setRunningMode(RunningMode.VIDEO)
                .setNumFaces(1)
                .setOutputFaceBlendshapes(true)
                .setMinFaceDetectionConfidence(0.6f)
                .setMinTrackingConfidence(0.5f)
                .build(),
        )
    } else null

    fun detect(image: MPImage, timestampMs: Long, aspect: Float): FaceObservation? {
        detector?.let { d ->
            val det = d.detectForVideo(image, timestampMs).detections()
                .maxByOrNull { it.boundingBox().width() * it.boundingBox().height() } ?: return null
            val kp = det.keypoints().orElse(null) ?: return null
            if (kp.size < 3) return null
            val (yaw, pitch, roll) = HeadRecognizer.poseFromPoints(
                P(kp[0].x() * aspect, kp[0].y()), P(kp[1].x() * aspect, kp[1].y()), P(kp[2].x() * aspect, kp[2].y()),
            )
            return FaceObservation(yaw, pitch, roll)
        }
        val result = landmarker!!.detectForVideo(image, timestampMs)
        val lm = result.faceLandmarks().firstOrNull() ?: return null
        fun p(i: Int) = P(lm[i].x() * aspect, lm[i].y())
        val eyeA = P((p(33).x + p(133).x) / 2, (p(33).y + p(133).y) / 2)
        val eyeB = P((p(362).x + p(263).x) / 2, (p(362).y + p(263).y) / 2)
        val (yaw, pitch, roll) = HeadRecognizer.poseFromPoints(eyeA, eyeB, p(1))
        val blend = result.faceBlendshapes().orElse(null)?.firstOrNull()?.associate { it.categoryName() to it.score() } ?: emptyMap()
        val expressions = mapOf(
            "mouth_open" to (blend["jawOpen"] ?: 0f),
            "smile" to ((blend["mouthSmileLeft"] ?: 0f) + (blend["mouthSmileRight"] ?: 0f)) / 2,
            "brows_up" to maxOf(blend["browInnerUp"] ?: 0f, ((blend["browOuterUpLeft"] ?: 0f) + (blend["browOuterUpRight"] ?: 0f)) / 2),
        )
        return FaceObservation(yaw, pitch, roll, expressions, eyeFeatures(::p, lm.size, blend, expressions["smile"] ?: 0f))
    }

    /** Same landmark/blendshape mapping as desktop (eyeBlinkLeft = the eye on the screen-right). Frames are mirrored. */
    private fun eyeFeatures(p: (Int) -> P, count: Int, bs: Map<String, Float>, smile: Float): EyeFeatures? {
        if (count < 478) return null
        data class Side(val ear: Float, val blink: Float?, val hx: Float, val vy: Float, val up: Float, val down: Float)
        fun side(outer: Int, inner: Int, up: IntArray, low: IntArray, top: Int, bottom: Int, iris: Int, blink: String, lu: String, ld: String): Side {
            val width = maxOf(Geo.dist(p(outer), p(inner)), 1e-6f)
            val ear = (Geo.dist(p(up[0]), p(low[0])) + Geo.dist(p(up[1]), p(low[1]))) / (2 * width)
            val x0 = minOf(p(outer).x, p(inner).x); val x1 = maxOf(p(outer).x, p(inner).x)
            val hx = (p(iris).x - x0) / maxOf(x1 - x0, 1e-6f) - 0.5f
            val t = p(top).y; val b = p(bottom).y
            val vy = 0.5f - (p(iris).y - t) / maxOf(b - t, 1e-6f)
            return Side(ear, bs[blink], hx, vy, bs[lu] ?: 0f, bs[ld] ?: 0f)
        }
        val l = side(33, 133, intArrayOf(160, 158), intArrayOf(144, 153), 159, 145, 468, "eyeBlinkRight", "eyeLookUpRight", "eyeLookDownRight")
        val r = side(263, 362, intArrayOf(385, 387), intArrayOf(380, 373), 386, 374, 473, "eyeBlinkLeft", "eyeLookUpLeft", "eyeLookDownLeft")
        // Mirrored: the user's left eye is on the screen-left.
        return EyeFeatures(l.ear, r.ear, l.blink, r.blink, (l.hx + r.hx) / 2, (l.vy + r.vy) / 2, (l.up + r.up) / 2, (l.down + r.down) / 2, smile)
    }

    override fun close() {
        detector?.close()
        landmarker?.close()
    }
}
