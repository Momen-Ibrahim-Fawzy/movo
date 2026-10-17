"""Imaa — control your computer with hand and head gestures, privately."""

import os as _os

# Media Foundation opens cameras ~5x faster without hardware transforms (must be set before cv2 loads).
_os.environ.setdefault("OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS", "0")
_os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

__app_name__ = "Imaa"
__app_id__ = "app.imaa.desktop"
__version__ = "1.0.0"
