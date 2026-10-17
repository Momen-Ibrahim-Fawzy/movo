import pytest
from synthetic import face_points

from imaa.core.head import FaceObservation, HeadRecognizer, pose_from_points

FPS = 15


def obs(**pose):
    return FaceObservation(*pose_from_points(*face_points(**pose)))


def feed(rec, observations, t0=0.0):
    events, t = [], t0
    for o in observations:
        events += rec.update(o, t)
        t += 1 / FPS
    return events, t


def calibrated():
    rec = HeadRecognizer()
    _, t = feed(rec, [obs()] * 15)
    assert rec.calibrated
    return rec, t


@pytest.mark.parametrize(
    "pose,index,sign",
    [
        ({"yaw": 25}, 0, 1),
        ({"yaw": -25}, 0, -1),
        ({"pitch": 20}, 1, 1),
        ({"pitch": -20}, 1, -1),
        ({"roll": 20}, 2, 1),
        ({"roll": -20}, 2, -1),
    ],
)
def test_pose_signs(pose, index, sign):
    neutral = pose_from_points(*face_points())
    moved = pose_from_points(*face_points(**pose))
    delta = moved[index] - neutral[index]
    assert delta * sign > 8
    for other in {0, 1, 2} - {index}:
        assert abs(moved[other] - neutral[other]) < abs(delta) * 0.5


def test_roll_estimate_is_accurate():
    neutral = pose_from_points(*face_points())
    assert pose_from_points(*face_points(roll=20))[2] - neutral[2] == pytest.approx(20, abs=0.5)


@pytest.mark.parametrize(
    "pose,expected",
    [
        ({"yaw": 30}, "turn_right"),
        ({"yaw": -30}, "turn_left"),
        ({"roll": 22}, "tilt_right"),
        ({"roll": -22}, "tilt_left"),
        ({"pitch": 20}, "look_up"),
        ({"pitch": -20}, "look_down"),
    ],
)
def test_holds(pose, expected):
    rec, t = calibrated()
    events, _ = feed(rec, [obs(**pose)] * 12, t)
    starts = [e.gesture for e in events if e.phase == "start"]
    assert starts == [expected]


def test_nod():
    rec, t = calibrated()
    seq = [obs(pitch=p) for p in (0, -6, -14, -16, -12, -4, 0, 0)]
    events, _ = feed(rec, seq, t)
    assert [e.gesture for e in events] == ["nod"]


def test_shake():
    rec, t = calibrated()
    seq = [obs(yaw=y) for y in (0, 14, 16, 0, -14, -16, 0, 14, 15, 0)]
    events, _ = feed(rec, seq, t)
    assert [e.gesture for e in events] == ["shake"]


def test_small_movements_do_nothing():
    rec, t = calibrated()
    seq = [obs(yaw=y, pitch=p) for y, p in [(3, -2), (-4, 3), (2, 4), (-3, -3)] * 6]
    events, _ = feed(rec, seq, t)
    assert events == []


def test_expressions_fire_once_per_activation():
    rec, t = calibrated()
    neutral = FaceObservation(*pose_from_points(*face_points()), {"mouth_open": 0.0})
    open_ = FaceObservation(*pose_from_points(*face_points()), {"mouth_open": 0.8})
    events, t = feed(rec, [open_] * 15, t)
    events2, t = feed(rec, [neutral] * 3 + [open_] * 15, t)
    assert [e.gesture for e in events] == ["mouth_open"]
    assert [e.gesture for e in events2] == ["mouth_open"]


def test_face_lost_clears_state():
    rec, t = calibrated()
    feed(rec, [obs(yaw=30)] * 3, t)
    assert rec.update(None, t + 1) == []
    assert rec.live_pose is None
