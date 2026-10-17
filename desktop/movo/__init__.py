"""Movo — control your computer with hand and head gestures, privately."""

import os as _os

# Media Foundation opens cameras ~5x faster without hardware transforms (must be set before cv2 loads).
_os.environ.setdefault("OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS", "0")
_os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

__app_name__ = "Movo"
__app_id__ = "app.movo.desktop"
__version__ = "1.1.0"
