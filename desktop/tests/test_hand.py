import pytest
from synthetic import POSES, hand, pinch_hand

from imaa.core.hand import HandRecognizer, analyze, classify

FPS = 30


def run(rec, frames, t0=0.0):
    events, t = [], t0
    for lm in frames:
        events += rec.update(lm, t)
        t += 1 / FPS
    return events, t


@pytest.mark.parametrize("label", sorted(POSES))
def test_classify_poses(label):
    assert classify(analyze(hand(**POSES[label]))) == label


@pytest.mark.parametrize("angle", [-45, 45, 135])
def test_diagonal_pointing_is_ignored(angle):
    assert classify(analyze(hand(index=True, rotate=angle))) is None


def test_held_pose_fires_once_then_repeats():
    rec = HandRecognizer()
    events, _ = run(rec, [hand(**POSES["thumb_up"])] * int(FPS * 1.2))
    starts = [e for e in events if e.phase == "start"]
    repeats = [e for e in events if e.phase == "repeat"]
    assert [e.gesture for e in starts] == ["thumb_up"]
    assert len(repeats) >= 2


def test_pose_must_change_before_firing_again():
    rec = HandRecognizer()
    events, t = run(rec, [hand(**POSES["victory"])] * FPS)
    events2, t = run(rec, [hand(**POSES["open_palm"])] * 10, t)
    events3, _ = run(rec, [hand(**POSES["victory"])] * FPS, t)
    assert [e.gesture for e in events if e.phase == "start"] == ["victory"]
    assert [e.gesture for e in events3 if e.phase == "start"] == ["victory"]


def test_short_flash_does_not_fire():
    rec = HandRecognizer()
    events, _ = run(rec, [hand(**POSES["fist"])] * 5)  # ~170 ms < 600 ms hold
    assert events == []


def test_hand_lost_resets():
    rec = HandRecognizer()
    run(rec, [hand(**POSES["fist"])] * 10)
    assert rec.update(None, 1.0) == []
    assert rec.live_pose is None


def test_pinch_tap():
    rec = HandRecognizer()
    frames = [hand(**POSES["open_palm"])] * 3 + [pinch_hand(True)] * 6 + [pinch_hand(False)] * 3
    events, _ = run(rec, frames)
    assert [e.gesture for e in events] == ["pinch"]


def test_pinch_drag_zooms_not_taps():
    rec = HandRecognizer()
    frames = [pinch_hand(True)] * 15  # hold 0.5 s → drag mode
    frames += [pinch_hand(True, at=(0.65, 0.6 - 0.02 * i)) for i in range(1, 12)]  # move up 0.22
    frames += [pinch_hand(False, at=(0.65, 0.38))] * 3
    events, _ = run(rec, frames)
    names = [e.gesture for e in events]
    assert "pinch" not in names
    assert names.count("pinch_drag_up") >= 3
    assert events[0].phase == "start" and events[1].phase == "repeat"


def test_swipe_right():
    rec = HandRecognizer()
    frames = [hand(**POSES["open_palm"], at=(0.3 + 0.05 * i, 0.6)) for i in range(10)]
    events, _ = run(rec, frames)
    assert [e.gesture for e in events] == ["swipe_right"]


def test_swipe_left():
    rec = HandRecognizer()
    frames = [hand(**POSES["open_palm"], at=(1.0 - 0.05 * i, 0.6)) for i in range(10)]
    events, _ = run(rec, frames)
    assert [e.gesture for e in events] == ["swipe_left"]


def test_fast_motion_blocks_static_pose():
    rec = HandRecognizer()
    frames = [hand(**POSES["fist"], at=(0.3 + 0.03 * i, 0.3 + 0.03 * i)) for i in range(25)]
    events, _ = run(rec, frames)
    assert not [e for e in events if e.gesture == "fist"]


def test_index_up_joystick_scrolls():
    rec = HandRecognizer()
    frames = [hand(**POSES["point_up"])] * 12
    frames += [hand(**POSES["point_up"], at=(0.65, 0.5))] * 20  # raised by 0.1
    events, _ = run(rec, frames)
    ups = [e for e in events if e.gesture == "index_up_move_up"]
    assert len(ups) >= 3
    assert all(0.25 <= e.magnitude <= 1.0 for e in ups)
    assert not [e for e in events if e.gesture == "index_up_move_down"]


def test_hold_scale_makes_it_slower():
    rec = HandRecognizer()
    rec.s.hold_scale = 3.0
    events, _ = run(rec, [hand(**POSES["thumb_up"])] * 15)  # 0.5 s < 0.9 s
    assert events == []
