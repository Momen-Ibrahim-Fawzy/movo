import pytest

from imaa.core.eyes import EyeFeatures, EyeRecognizer, EyeSettings

FPS = 20
OPEN, CLOSED = 0.30, 0.08


def eye(left=OPEN, r=OPEN, bl=None, br=None, gx=0.0, gy=0.0, up=0.0, down=0.0, smile=0.0):
    if bl is None:
        bl = 0.05 if left > 0.2 else 0.9
    if br is None:
        br = 0.05 if r > 0.2 else 0.9
    return EyeFeatures(left, r, bl, br, gx, gy, up, down, smile)


def frames(f, seconds):
    return [f] * max(1, round(seconds * FPS))


def run(rec, seq, t0=0.0, head=(0.0, 0.0, 0.0)):
    events, t = [], t0
    for f in seq:
        events += rec.update(f, t, head)
        t += 1 / FPS
    return [e.gesture for e in events if e.phase == "start"], t


@pytest.fixture(params=[False, True], ids=["no-glasses", "glasses"])
def rec(request):
    r = EyeRecognizer(EyeSettings(glasses=request.param))
    run(r, frames(eye(), 1.5))  # warm-up: auto-learn the open level and gaze centre
    return r


def test_natural_single_blink_does_nothing(rec):
    names, _ = run(rec, frames(eye(), 0.5) + frames(eye(CLOSED, CLOSED), 0.15) + frames(eye(), 2.0))
    assert names == []


def test_double_blink(rec):
    seq = frames(eye(CLOSED, CLOSED), 0.2) + frames(eye(), 0.25) + frames(eye(CLOSED, CLOSED), 0.2) + frames(eye(), 0.5)
    names, _ = run(rec, seq)
    assert names == ["blink_double"]


def test_long_blink(rec):
    names, _ = run(rec, frames(eye(CLOSED, CLOSED), 1.0) + frames(eye(), 0.5))
    assert names == ["blink_long"]


def test_eyes_closed_fires_once_and_not_long_blink(rec):
    names, _ = run(rec, frames(eye(CLOSED, CLOSED), 3.0) + frames(eye(), 0.5))
    assert names == ["eyes_closed"]


@pytest.mark.parametrize("side,expected", [("left", "wink_left"), ("right", "wink_right")])
def test_winks(rec, side, expected):
    f = eye(CLOSED, OPEN) if side == "left" else eye(OPEN, CLOSED)
    names, _ = run(rec, frames(f, 0.6) + frames(eye(), 0.4))
    assert names == [expected]


def test_wink_suppressed_while_smiling(rec):
    names, _ = run(rec, frames(eye(CLOSED, OPEN, smile=0.8), 0.8) + frames(eye(), 0.4))
    assert names == []


@pytest.mark.parametrize(
    "f,expected",
    [
        (dict(gx=0.15), "eye_look_right"),
        (dict(gx=-0.15), "eye_look_left"),
        (dict(gy=0.12, up=0.6), "eye_look_up"),
        (dict(gy=-0.12, down=0.6), "eye_look_down"),
    ],
)
def test_glances_fire_and_repeat(rec, f, expected):
    events, t = [], 1.5
    for x in frames(eye(**f), 1.5):
        events += rec.update(x, t)
        t += 1 / FPS
    assert [e.gesture for e in events if e.phase == "start"] == [expected]
    assert any(e.phase == "repeat" for e in events)


def test_looking_down_is_not_a_blink(rec):
    # Looking down lowers the lids (EAR drops, blink score rises a little) but must not count as closed.
    names, _ = run(rec, frames(eye(0.17, 0.17, bl=0.45, br=0.45, gy=-0.12, down=0.8), 1.2) + frames(eye(), 0.5))
    assert "blink_long" not in names and "eyes_closed" not in names


def test_single_glare_frame_is_ignored(rec):
    seq = frames(eye(), 0.3) + [eye(CLOSED, OPEN)] + frames(eye(), 0.3) + [eye(OPEN, CLOSED)] + frames(eye(), 1.0)
    names, _ = run(rec, seq)
    assert names == []


def test_turned_head_blocks_eye_gestures(rec):
    names, _ = run(rec, frames(eye(CLOSED, OPEN), 0.8), head=(30.0, 0.0, 0.0))
    assert names == []


def test_head_motion_blocks_glances(rec):
    # Turning the head makes the eyes counter-rotate; that must not read as a glance.
    names, _ = run(rec, frames(eye(gx=-0.15), 1.2), head=(12.0, 0.0, 0.0))
    assert names == []


def test_calibration_with_magnifying_glasses():
    # Strong reading glasses magnify the eyes: open EAR 0.42, closed 0.20 (closed would look "open" with fixed thresholds).
    r = EyeRecognizer(EyeSettings(glasses=True))
    r.begin_capture("open")
    run(r, frames(eye(0.42, 0.42), 2.0))
    r.begin_capture("closed")
    run(r, frames(eye(0.20, 0.20, bl=0.8, br=0.8), 2.0), t0=2.0)
    r.end_capture()
    assert r.finish_calibration() is not None
    names, _ = run(
        r, frames(eye(0.42, 0.42), 2.0) + frames(eye(0.20, 0.42, bl=0.8, br=0.05), 0.6) + frames(eye(0.42, 0.42), 0.4), t0=5
    )
    assert names == ["wink_left"]


def test_calibration_rejects_unclear_eyes():
    r = EyeRecognizer()
    r.begin_capture("open")
    run(r, frames(eye(), 1.0))
    r.begin_capture("closed")
    run(r, frames(eye(0.29, 0.29, bl=0.05, br=0.05), 1.0), t0=1)
    r.end_capture()
    assert r.finish_calibration() is None


def test_face_lost_resets(rec):
    run(rec, frames(eye(CLOSED, CLOSED), 0.3))
    assert rec.update(None, 10.0) == []
    names, _ = run(rec, frames(eye(), 0.5), t0=10.1)
    assert names == []
