"""Camera capture that always hands out the newest frame.

Frames are kept in memory only and replaced by the next one; nothing is written anywhere.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from typing import Optional

import cv2
import numpy as np

log = logging.getLogger(__name__)


def _backends() -> list[int]:
    if sys.platform == "win32":
        return [cv2.CAP_MSMF, cv2.CAP_DSHOW]
    if sys.platform == "darwin":
        return [cv2.CAP_AVFOUNDATION]
    return [cv2.CAP_V4L2, cv2.CAP_ANY]


class Camera:
    def __init__(self, index: int = 0, width: int = 640, height: int = 480, fps: int = 30):
        self.index = index
        self.width = width
        self.height = height
        self.fps = fps
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._seq = 0
        self._lock = threading.Lock()
        self._new = threading.Condition(self._lock)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.error: Optional[str] = None

    def open(self) -> bool:
        cap = None
        for backend in _backends():
            cap = cv2.VideoCapture(self.index, backend)
            if cap.isOpened():
                break
            cap.release()
            cap = None
        if cap is None:
            self.error = "camera_unavailable"
            return False
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        ok, frame = cap.read()
        if not ok or frame is None:
            cap.release()
            self.error = "camera_unavailable"
            return False
        self._cap = cap
        self._frame = frame
        self.error = None
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="movo-camera", daemon=True)
        self._thread.start()
        return True

    def _loop(self) -> None:
        failures = 0
        while not self._stop.is_set():
            ok, frame = self._cap.read() if self._cap else (False, None)
            if not ok or frame is None:
                failures += 1
                if failures > 30:
                    self.error = "camera_lost"
                    log.warning("camera stopped delivering frames")
                    with self._new:
                        self._new.notify_all()
                    return
                time.sleep(0.03)
                continue
            failures = 0
            with self._new:
                self._frame = frame
                self._seq += 1
                self._new.notify_all()

    def latest(self, after_seq: int, timeout: float = 0.5) -> tuple[int, Optional[np.ndarray]]:
        """Wait for a frame newer than ``after_seq`` and return ``(seq, frame)``."""
        with self._new:
            if self._seq <= after_seq:
                self._new.wait(timeout)
            return self._seq, self._frame

    def close(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.5)
        if self._cap is not None:
            self._cap.release()
        self._cap = None
        with self._lock:
            self._frame = None


def list_cameras() -> list[tuple[int, str]]:
    """Camera names from Qt when available (index order matches the system order on most platforms)."""
    try:
        from PySide6.QtMultimedia import QMediaDevices

        devices = QMediaDevices.videoInputs()
        if devices:
            return [(i, d.description()) for i, d in enumerate(devices)]
    except Exception:  # QtMultimedia missing or no permission
        pass
    return [(0, "Camera 1")]
