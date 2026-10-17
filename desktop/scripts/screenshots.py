"""Render every page in light, dark and Arabic to PNG (docs/screenshots). Also a UI smoke test.

Usage: python scripts/screenshots.py [output_dir]
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("IMAA_CONFIG_DIR", tempfile.mkdtemp(prefix="imaa-shots-"))


def main() -> int:
    import numpy as np
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from imaa.config import Settings
    from imaa.controller import Controller
    from imaa.core.engine import EngineStats
    from imaa.ui.main_window import NAV, MainWindow, apply_appearance

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "docs" / "screenshots"
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv[:1])
    settings = Settings()
    settings.set("first_run_done", True)
    settings.set("browser_bridge.enabled", False)
    settings.set("auto_profiles", False)
    controller = Controller(settings)
    shots = []

    # A soft gradient stands in for the camera picture in the preview.
    h, w = 360, 480
    yy, xx = np.mgrid[0:h, 0:w]
    fake = np.stack([90 + yy * 0.15, 95 + yy * 0.15, 100 + yy * 0.15 + xx * 0.02], axis=-1).astype(np.uint8)

    for lang, theme_name in (("en", "light"), ("en", "dark"), ("ar", "light"), ("ar", "dark")):
        settings.set("language", lang)
        settings.set("theme", theme_name)
        apply_appearance(app, settings)
        win = MainWindow(settings, controller)
        win.resize(1180, 820)
        win.show()
        for key, _icon, _cls in NAV:
            win.go(key)
            if key == "home":
                controller._set_state("running")
                stats = EngineStats(fps=20, process_ms=9, hand=True, hand_pose="thumb_up")
                controller.stats_changed.emit(stats)
                win.pages["home"].preview.set_frame(fake)
            for _ in range(5):
                app.processEvents()
            path = out / f"{lang}-{theme_name}-{key}.png"
            win.grab().save(str(path))
            shots.append(path)
        controller._set_state("stopped")
        win.close()
        win.deleteLater()
        app.processEvents()

    QTimer.singleShot(0, app.quit)
    app.exec()
    controller.shutdown()
    print("\n".join(str(s) for s in shots))
    return 0


if __name__ == "__main__":
    sys.exit(main())
