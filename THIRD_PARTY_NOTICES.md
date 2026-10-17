# Third-party notices

Imaa is built on the following open-source components. Each remains under its own licence.
Full licence texts are shipped inside each installer next to the component.

## Desktop

| Component | Licence | Use |
|-----------|---------|-----|
| [MediaPipe](https://github.com/google-ai-edge/mediapipe) and its Hand Landmarker, Face Detector (BlazeFace) and Face Landmarker models | Apache License 2.0 | On-device hand, face and expression tracking |
| [OpenCV](https://opencv.org/) | Apache License 2.0 | Camera capture and image conversion |
| [Qt 6](https://www.qt.io/) / [Qt for Python (PySide6)](https://doc.qt.io/qtforpython/) | LGPL v3 | User interface. Qt libraries are dynamically linked and can be replaced by the user. |
| [NumPy](https://numpy.org/) | BSD 3-Clause | Image buffers |
| [pynput](https://github.com/moses-palmer/pynput) | LGPL v3 | Keyboard and mouse input |
| [websockets](https://github.com/python-websockets/websockets) | BSD 3-Clause | Local browser helper and phone remote |
| [segno](https://github.com/heuer/segno) | BSD 3-Clause | Pairing QR code |
| [pycaw](https://github.com/AndreMiras/pycaw) | MIT | Windows microphone control |
| [comtypes](https://github.com/enthought/comtypes) | MIT | Windows audio and UI Automation |
| [PyInstaller](https://pyinstaller.org/) bootloader | GPL v2 with bootloader exception | Packaging |

## Android

| Component | Licence |
|-----------|---------|
| MediaPipe Tasks Vision | Apache License 2.0 |
| AndroidX (CameraX, Compose, Lifecycle, Core, AppCompat) | Apache License 2.0 |
| Kotlin standard library and coroutines | Apache License 2.0 |
| OkHttp | Apache License 2.0 |

## iOS

Uses only Apple system frameworks (SwiftUI, Vision, AVFoundation, PDFKit, Network, CryptoKit).
