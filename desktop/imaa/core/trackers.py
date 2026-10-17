"""Thin wrappers around the MediaPipe Tasks models (bundled with the app, loaded from memory)."""

from __future__ import annotations

import os
from typing import Optional

import numpy as np

os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import mediapipe as mp  # noqa: E402
from mediapipe.tasks.python import BaseOptions, vision  # noqa: E402

from imaa.core.head import FaceObservation, pose_from_points  # noqa: E402
from imaa.paths import asset  # noqa: E402

HAND_MODEL = "hand_landmarker.task"
FACE_LIGHT_MODEL = "blaze_face_short_range.tflite"
FACE_ACCURATE_MODEL = "face_landmarker.task"


def _base(model: str) -> BaseOptions:
    return BaseOptions(model_asset_buffer=asset("models", model).read_bytes())


def _image(rgb: np.ndarray) -> mp.Image:
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))


class HandTracker:
    def __init__(self, max_hands: int = 1):
        self._lm = vision.HandLandmarker.create_from_options(
            vision.HandLandmarkerOptions(
                base_options=_base(HAND_MODEL),
                running_mode=vision.RunningMode.VIDEO,
                num_hands=max_hands,
                min_hand_detection_confidence=0.6,
                min_hand_presence_confidence=0.6,
                min_tracking_confidence=0.5,
            )
        )

    def detect(self, rgb: np.ndarray, ts_ms: int) -> Optional[list[tuple[float, float, float]]]:
        """Landmarks of the most confident hand in normalised image coordinates, or None."""
        result = self._lm.detect_for_video(_image(rgb), ts_ms)
        if not result.hand_landmarks:
            return None
        return [(p.x, p.y, p.z) for p in result.hand_landmarks[0]]

    def close(self) -> None:
        self._lm.close()


class FaceTracker:
    """Light mode = BlazeFace keypoints; Accurate mode = Face Landmarker with blendshapes."""

    def __init__(self, accurate: bool = False):
        self.accurate = accurate
        if accurate:
            self._task = vision.FaceLandmarker.create_from_options(
                vision.FaceLandmarkerOptions(
                    base_options=_base(FACE_ACCURATE_MODEL),
                    running_mode=vision.RunningMode.VIDEO,
                    num_faces=1,
                    output_face_blendshapes=True,
                    min_face_detection_confidence=0.6,
                    min_tracking_confidence=0.5,
                )
            )
        else:
            self._task = vision.FaceDetector.create_from_options(
                vision.FaceDetectorOptions(
                    base_options=_base(FACE_LIGHT_MODEL),
                    running_mode=vision.RunningMode.VIDEO,
                    min_detection_confidence=0.6,
                )
            )
        self.points: list[tuple[float, float]] = []  # last keypoints (normalised), for the preview

    def detect(self, rgb: np.ndarray, ts_ms: int, aspect: float) -> Optional[FaceObservation]:
        if self.accurate:
            return self._detect_accurate(rgb, ts_ms, aspect)
        return self._detect_light(rgb, ts_ms, aspect)

    def _detect_light(self, rgb, ts_ms, aspect) -> Optional[FaceObservation]:
        result = self._task.detect_for_video(_image(rgb), ts_ms)
        if not result.detections:
            self.points = []
            return None
        det = max(result.detections, key=lambda d: d.bounding_box.width * d.bounding_box.height)
        kp = det.keypoints
        if len(kp) < 3:
            return None
        self.points = [(k.x, k.y) for k in kp]
        a, b, nose = ((kp[i].x * aspect, kp[i].y) for i in range(3))
        yaw, pitch, roll = pose_from_points(a, b, nose)
        return FaceObservation(yaw, pitch, roll)

    def _detect_accurate(self, rgb, ts_ms, aspect) -> Optional[FaceObservation]:
        result = self._task.detect_for_video(_image(rgb), ts_ms)
        if not result.face_landmarks:
            self.points = []
            return None
        lm = result.face_landmarks[0]

        def p(i):
            return (lm[i].x * aspect, lm[i].y)

        eye_a = ((p(33)[0] + p(133)[0]) / 2, (p(33)[1] + p(133)[1]) / 2)
        eye_b = ((p(362)[0] + p(263)[0]) / 2, (p(362)[1] + p(263)[1]) / 2)
        nose = p(1)
        self.points = [(lm[i].x, lm[i].y) for i in (33, 133, 362, 263, 1, 13, 14, 10, 152)]
        yaw, pitch, roll = pose_from_points(eye_a, eye_b, nose)
        expressions = None
        if result.face_blendshapes:
            bs = {c.category_name: c.score for c in result.face_blendshapes[0]}
            expressions = {
                "mouth_open": bs.get("jawOpen", 0.0),
                "smile": (bs.get("mouthSmileLeft", 0.0) + bs.get("mouthSmileRight", 0.0)) / 2,
                "brows_up": max(
                    bs.get("browInnerUp", 0.0),
                    (bs.get("browOuterUpLeft", 0.0) + bs.get("browOuterUpRight", 0.0)) / 2,
                ),
            }
        return FaceObservation(yaw, pitch, roll, expressions)

    def close(self) -> None:
        self._task.close()
