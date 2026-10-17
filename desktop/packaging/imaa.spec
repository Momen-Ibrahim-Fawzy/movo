# PyInstaller spec for Imaa (one-folder build). Run from the desktop/ folder:
#   pyinstaller packaging/imaa.spec --noconfirm
# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

ROOT = Path(SPECPATH).parent
REPO = ROOT.parent
IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

datas = [
    (str(ROOT / "imaa" / "i18n"), "imaa/i18n"),
    (str(ROOT / "imaa" / "assets"), "imaa/assets"),
    (str(REPO / "browser-extension"), "imaa/browser-extension"),
    (str(REPO / "LICENSE"), "."),
    (str(REPO / "THIRD_PARTY_NOTICES.md"), "."),
]
datas += collect_data_files("mediapipe", includes=["**/*.so", "**/*.dll", "**/*.dylib", "**/*.pyd"], excludes=["**/test/**"])
binaries = collect_dynamic_libs("mediapipe")
hiddenimports = [
    m for m in collect_submodules("mediapipe.tasks.python") if ".test" not in m
] + collect_submodules("websockets") + ["segno"]
if IS_WIN:
    hiddenimports += ["pynput.keyboard._win32", "pynput.mouse._win32", "comtypes.stream", "pycaw.pycaw"]
elif IS_MAC:
    hiddenimports += ["pynput.keyboard._darwin", "pynput.mouse._darwin"]
else:
    hiddenimports += ["pynput.keyboard._xorg", "pynput.mouse._xorg", "pynput.keyboard._uinput"]

excludes = [
    "tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQuick", "PySide6.QtQml",
    "PySide6.Qt3DCore", "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtPdf", "matplotlib",
    "PySide6.QtDesigner", "PySide6.QtBluetooth", "PySide6.QtLocation", "PySide6.QtSql", "PySide6.QtTest",
    "sounddevice", "PIL",
]

a = Analysis(
    [str(ROOT / "imaa" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=excludes,
    noarchive=False,
)

# Trim what a gesture app never uses: video-file codecs, software OpenGL, QML/Quick, PDF, extra translations.
DROP = (
    "opencv_videoio_ffmpeg", "opengl32sw", "Qt6Quick", "Qt6Qml", "Qt6Pdf", "Qt6VirtualKeyboard",
    "_sounddevice_data", "portaudio", "Qt6Designer", "Qt6Charts", "Qt6WebEngine", "QtWebEngineProcess",
)
KEEP_TRANSLATIONS = ("qtbase_ar", "qtbase_en", "qt_ar", "qt_en")


def _keep(entry) -> bool:
    name = entry[0].replace("\\", "/")
    base = name.rsplit("/", 1)[-1]
    if any(d in base for d in DROP):
        return False
    if "/translations/" in name and name.endswith(".qm") and not base.startswith(KEEP_TRANSLATIONS):
        return False
    return True


a.binaries = [b for b in a.binaries if _keep(b)]
a.datas = [d for d in a.datas if _keep(d)]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Imaa",
    console=False,
    icon=str(ROOT / "packaging" / ("imaa.icns" if IS_MAC else "imaa.ico")),
    version=str(ROOT / "packaging" / "version_info.txt") if IS_WIN else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Imaa")

if IS_MAC:
    app = BUNDLE(
        coll,
        name="Imaa.app",
        icon=str(ROOT / "packaging" / "imaa.icns"),
        bundle_identifier="app.imaa.desktop",
        info_plist={
            "CFBundleDisplayName": "Imaa",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "LSMinimumSystemVersion": "12.0",
            "NSHighResolutionCapable": True,
            "LSUIElement": False,
            "NSCameraUsageDescription": "Imaa looks at your hand and head gestures. The picture is processed on this Mac only and never saved or sent.",
            "NSAppleEventsUsageDescription": "Imaa uses this to mute the microphone and read which app is in front.",
            "CFBundleLocalizations": ["en", "ar"],
        },
    )
