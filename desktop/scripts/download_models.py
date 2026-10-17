"""Download the on-device MediaPipe models (Apache 2.0) into imaa/assets/models.

The app never downloads anything at run time; this runs once for development and in CI before packaging.
Usage: python scripts/download_models.py
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

BASE = "https://storage.googleapis.com/mediapipe-models"
MODELS = {
    "hand_landmarker.task": f"{BASE}/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
    "blaze_face_short_range.tflite": f"{BASE}/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite",
    "face_landmarker.task": f"{BASE}/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
}
DEST = Path(__file__).resolve().parents[1] / "imaa" / "assets" / "models"


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    for name, url in MODELS.items():
        target = DEST / name
        if target.exists() and target.stat().st_size > 100_000:
            print(f"✓ {name} (already present)")
            continue
        print(f"↓ {name}")
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = resp.read()
        target.write_bytes(data)
        print(f"  {len(data) / 1e6:.1f} MB  sha256={hashlib.sha256(data).hexdigest()[:16]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
