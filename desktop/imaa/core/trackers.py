"""Thin wrappers around the MediaPipe Tasks models (bundled with the app, loaded from memory)."""

from __future__ import annotations

import os
from typing import Optional

import numpy as np

os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")


def _stub_matplotlib() -> None:
    """MediaPipe's vision package imports matplotlib for a 3-D plotting helper we never call.
    The packaged app leaves matplotlib out (~40 MB), so provide an empty stand-in."""
    import importlib.util
    import sys
    import types

    if importlib.util.find_spec("matplotlib") is None:
        mpl = types.ModuleType("matplotlib")
        mpl.pyplot = types.ModuleType("matplotlib.pyplot")  # type: ignore[attr-defined]
        sys.modules.setdefault("matplotlib", mpl)
        sys.modules.setdefault("matplotlib.pyplot", mpl.pyplot)  # type: ignore[attr-defined]


_stub_matplotlib()

import mediapipe as mp  # noqa: E402
from mediapipe.tasks.python import BaseOptions, vision  # noqa: E402

from imaa.core.eyes import EyeFeatures  # noqa: E402
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

    def detect(self, rgb: np.ndarray, ts_ms: int, aspect: float, mirrored: bool = True) -> Optional[FaceObservation]:
        if self.accurate:
            return self._detect_accurate(rgb, ts_ms, aspect, mirrored)
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

    def _detect_accurate(self, rgb, ts_ms, aspect, mirrored=True) -> Optional[FaceObservation]:
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
        bs: dict = {}
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
        eyes = eye_features(p, lm, bs, mirrored, expressions)
        if len(lm) > 473:
            self.points += [(lm[i].x, lm[i].y) for i in (468, 473)]
        return FaceObservation(yaw, pitch, roll, expressions, eyes)

    def close(self) -> None:
        self._task.close()


# Face Landmarker indices. The eye on the *screen-left* uses 33/133 (corners), 160/158 (upper lid), 144/153 (lower lid),
# 159/145 (lid centre) and iris centre 468; the screen-right eye uses 263/362, 385/387, 380/373, 386/374 and 473.
# MediaPipe's eyeBlinkLeft blendshape always refers to the eye that appears on the screen-right.
_EYES = (
    dict(
        outer=33,
        inner=133,
        up=(160, 158),
        low=(144, 153),
        top=159,
        bottom=145,
        iris=468,
        blink="eyeBlinkRight",
        lu="eyeLookUpRight",
        ld="eyeLookDownRight",
    ),
    dict(
        outer=263,
        inner=362,
        up=(385, 387),
        low=(380, 373),
        top=386,
        bottom=374,
        iris=473,
        blink="eyeBlinkLeft",
        lu="eyeLookUpLeft",
        ld="eyeLookDownLeft",
    ),
)


def _d(a, b) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def eye_features(p, lm, bs: dict, mirrored: bool, expressions: Optional[dict]) -> Optional[EyeFeatures]:
    """Per-eye openness (EAR), learned blink scores, iris position and look scores, in the user's left/right."""
    if len(lm) < 478:
        return None
    sides = []
    for e in _EYES:
        width = max(_d(p(e["outer"]), p(e["inner"])), 1e-6)
        ear = (_d(p(e["up"][0]), p(e["low"][0])) + _d(p(e["up"][1]), p(e["low"][1]))) / (2 * width)
        xs = sorted((p(e["outer"])[0], p(e["inner"])[0]))
        iris = p(e["iris"])
        hx = (iris[0] - xs[0]) / max(xs[1] - xs[0], 1e-6) - 0.5  # + = towards screen-right
        top, bottom = p(e["top"])[1], p(e["bottom"])[1]
        vy = 0.5 - (iris[1] - top) / max(bottom - top, 1e-6)  # + = up
        sides.append((ear, bs.get(e["blink"]) if bs else None, hx, vy, bs.get(e["lu"], 0.0), bs.get(e["ld"], 0.0)))
    screen_left, screen_right = sides
    # In a mirrored view the user's left eye is on the screen-left; without mirroring it is on the screen-right.
    user_left, user_right = (screen_left, screen_right) if mirrored else (screen_right, screen_left)
    gaze_x = (screen_left[2] + screen_right[2]) / 2
    if not mirrored:
        gaze_x = -gaze_x
    return EyeFeatures(
        ear_left=user_left[0],
        ear_right=user_right[0],
        blink_left=user_left[1],
        blink_right=user_right[1],
        gaze_x=gaze_x,
        gaze_y=(screen_left[3] + screen_right[3]) / 2,
        look_up=(screen_left[4] + screen_right[4]) / 2,
        look_down=(screen_left[5] + screen_right[5]) / 2,
        smile=(expressions or {}).get("smile", 0.0),
    )
