from __future__ import annotations

import random
from pathlib import Path

from PySide6.QtCore import QRectF, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget

from movo.core.camera import list_cameras
from movo.i18n import LANGUAGES, tr
from movo.paths import default_screenshot_dir, resource_dir
from movo.ui import theme
from movo.ui.pages import Page
from movo.ui.widgets import Card, SettingRow, combo, label, page_header, toggle_row


def section(title: str, icon_name: str = "") -> Card:
    card = Card()
    head = QHBoxLayout()
    if icon_name:
        ic = QLabel()
        ic.setPixmap(theme.icon_pixmap(icon_name, theme.current().accent, 18))
        head.addWidget(ic)
    head.addWidget(label(title, "SectionTitle"))
    head.addStretch(1)
    card.lay.addLayout(head)
    return card


def qr_pixmap(text: str, size: int = 168) -> QPixmap:
    import segno

    qr = segno.make(text, error="m")
    matrix = list(qr.matrix)
    n = len(matrix)
    quiet = 2
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(QColor("#FFFFFF"))
    p = QPainter(img)
    cell = size / (n + quiet * 2)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#111111"))
    for y, row in enumerate(matrix):
        for x, v in enumerate(row):
            if v:
                p.drawRect(QRectF((x + quiet) * cell, (y + quiet) * cell, cell + 0.3, cell + 0.3))
    p.end()
    return QPixmap.fromImage(img)


class SettingsPage(Page):
    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        s = self.settings
        self.body.addWidget(page_header(tr("settings.title"), tr("settings.subtitle")))

        # ---------------- appearance
        c = section(tr("settings.appearance"), "sun")
        c.lay.addWidget(
            SettingRow(
                tr("settings.language"),
                tr("settings.language_d"),
                combo([("system", tr("settings.system"))] + list(LANGUAGES.items()), s.get("language"), self._set_language),
            )
        )
        c.lay.addWidget(
            SettingRow(
                tr("settings.theme"),
                tr("settings.theme_d"),
                combo(
                    [("system", tr("settings.system")), ("light", tr("settings.light")), ("dark", tr("settings.dark"))],
                    s.get("theme"),
                    self._set_theme,
                ),
            )
        )
        self.body.addWidget(c)

        # ---------------- startup
        c = section(tr("settings.startup"), "play")
        c.lay.addWidget(
            toggle_row(
                tr("settings.login"),
                tr("settings.login_d"),
                bool(s.get("launch_at_login")),
                lambda v: s.set("launch_at_login", v),
            )
        )
        c.lay.addWidget(
            toggle_row(
                tr("settings.autostart"),
                tr("settings.autostart_d"),
                bool(s.get("start_detection_on_launch")),
                lambda v: s.set("start_detection_on_launch", v),
            )
        )
        c.lay.addWidget(
            toggle_row(
                tr("settings.minimized"),
                tr("settings.minimized_d"),
                bool(s.get("start_minimized")),
                lambda v: s.set("start_minimized", v),
            )
        )
        c.lay.addWidget(
            toggle_row(
                tr("settings.tray"),
                tr("settings.tray_d"),
                bool(s.get("close_to_tray", True)),
                lambda v: s.set("close_to_tray", v),
            )
        )
        hk = QLineEdit(s.get("hotkey_pause", ""))
        hk.setPlaceholderText("<ctrl>+<alt>+g")
        hk.setFixedWidth(200)
        hk.editingFinished.connect(lambda: s.set("hotkey_pause", hk.text().strip()))
        c.lay.addWidget(SettingRow(tr("settings.hotkey"), tr("settings.hotkey_d"), hk))
        self.body.addWidget(c)

        # ---------------- camera & performance
        c = section(tr("settings.camera"), "camera")
        cams = list_cameras()
        c.lay.addWidget(
            SettingRow(
                tr("settings.camera_device"),
                "",
                combo([(str(i), n) for i, n in cams], str(s.get("camera.index", 0)), lambda v: s.set("camera.index", int(v))),
            )
        )
        res_items = [("320x240", "320 × 240"), ("640x480", "640 × 480"), ("960x540", "960 × 540"), ("1280x720", "1280 × 720")]
        current_res = f"{s.get('camera.width', 640)}x{s.get('camera.height', 480)}"
        c.lay.addWidget(
            SettingRow(
                tr("settings.resolution"), tr("settings.resolution_d"), combo(res_items, current_res, self._set_resolution)
            )
        )
        c.lay.addWidget(
            SettingRow(
                tr("settings.power"),
                tr("settings.power_d"),
                combo(
                    [
                        ("eco", tr("settings.power_eco")),
                        ("balanced", tr("settings.power_balanced")),
                        ("performance", tr("settings.power_performance")),
                    ],
                    s.get("power_mode", "balanced"),
                    lambda v: s.set("power_mode", v),
                ),
            )
        )
        c.lay.addWidget(
            toggle_row(
                tr("settings.mirror"),
                tr("settings.mirror_d"),
                bool(s.get("camera.mirror", True)),
                lambda v: s.set("camera.mirror", v),
            )
        )
        c.lay.addWidget(
            toggle_row(
                tr("settings.skeleton"),
                tr("settings.skeleton_d"),
                bool(s.get("show_skeleton", True)),
                lambda v: s.set("show_skeleton", v),
            )
        )
        self.body.addWidget(c)

        # ---------------- feedback
        c = section(tr("settings.feedback"), "info")
        c.lay.addWidget(
            toggle_row(tr("home.q_hud"), tr("home.q_hud_d"), bool(s.get("hud.enabled", True)), lambda v: s.set("hud.enabled", v))
        )
        c.lay.addWidget(
            SettingRow(
                tr("settings.hud_pos"),
                "",
                combo(
                    [("bottom", tr("settings.bottom")), ("top", tr("settings.top"))],
                    s.get("hud.position", "bottom"),
                    lambda v: s.set("hud.position", v),
                ),
            )
        )
        c.lay.addWidget(
            toggle_row(tr("settings.sounds"), tr("settings.sounds_d"), bool(s.get("sounds")), lambda v: s.set("sounds", v))
        )
        self.body.addWidget(c)

        # ---------------- screenshots
        c = section(tr("settings.screenshots"), "camera")
        folder_row = QHBoxLayout()
        self.folder = QLineEdit(s.get("screenshots.folder") or str(default_screenshot_dir()))
        self.folder.setReadOnly(True)
        folder_row.addWidget(self.folder, 1)
        choose = QPushButton(tr("settings.choose"))
        choose.clicked.connect(self._choose_folder)
        folder_row.addWidget(choose)
        open_btn = QPushButton(tr("settings.open"))
        open_btn.clicked.connect(lambda: self._open_folder(Path(self.folder.text())))
        folder_row.addWidget(open_btn)
        c.lay.addWidget(label(tr("settings.folder"), "Muted"))
        c.lay.addLayout(folder_row)
        c.lay.addWidget(
            toggle_row(
                tr("settings.clipboard"),
                "",
                bool(s.get("screenshots.copy_to_clipboard", True)),
                lambda v: s.set("screenshots.copy_to_clipboard", v),
            )
        )
        self.body.addWidget(c)

        # ---------------- integrations
        c = section(tr("settings.integrations"), "puzzle")
        c.lay.addWidget(
            toggle_row(
                tr("settings.bridge"),
                tr("settings.bridge_d"),
                bool(s.get("browser_bridge.enabled", True)),
                lambda v: s.set("browser_bridge.enabled", v),
            )
        )
        bridge_row = QHBoxLayout()
        self.bridge_status = label("", "Small")
        bridge_row.addWidget(self.bridge_status, 1)
        helper = QPushButton(tr("settings.bridge_install"))
        helper.clicked.connect(self._open_extension)
        bridge_row.addWidget(helper)
        c.lay.addLayout(bridge_row)
        c.lay.addSpacing(8)
        c.lay.addWidget(
            toggle_row(
                tr("settings.remote"),
                tr("settings.remote_d"),
                bool(s.get("remote.enabled")),
                lambda v: s.set("remote.enabled", v),
            )
        )
        self.remote_box = QWidget()
        rb = QHBoxLayout(self.remote_box)
        rb.setContentsMargins(0, 0, 0, 0)
        self.qr = QLabel()
        self.qr.setFixedSize(168, 168)
        rb.addWidget(self.qr)
        info = QVBoxLayout()
        self.remote_info = label("", wrap=True)
        self.remote_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info.addWidget(self.remote_info)
        self.remote_devices = label("", "Small", wrap=True)
        info.addWidget(self.remote_devices)
        regen = QPushButton(theme.icon("refresh", theme.current().text_muted, 16), tr("settings.remote_new_code"))
        regen.clicked.connect(lambda: s.set("remote.code", f"{random.SystemRandom().randrange(0, 1_000_000):06d}"))
        info.addWidget(regen, 0, Qt.AlignLeft)
        info.addStretch(1)
        rb.addLayout(info, 1)
        c.lay.addWidget(self.remote_box)
        self.body.addWidget(c)

        # ---------------- privacy
        c = section(tr("settings.privacy"), "lock")
        c.lay.addWidget(label(tr("settings.privacy_text"), wrap=True))
        self.body.addWidget(c)

        # ---------------- data
        c = section(tr("settings.data"), "layers")
        row = QHBoxLayout()
        exp = QPushButton(tr("settings.export"))
        exp.clicked.connect(self._export)
        imp = QPushButton(tr("settings.import"))
        imp.clicked.connect(self._import)
        reset = QPushButton(tr("settings.reset"))
        reset.setObjectName("Danger")
        reset.clicked.connect(self._reset)
        row.addWidget(exp)
        row.addWidget(imp)
        row.addStretch(1)
        row.addWidget(reset)
        c.lay.addLayout(row)
        self.body.addWidget(c)
        self.body.addStretch(1)

        self.controller.integrations_changed.connect(self._integrations)
        self._integrations()

    # ------------------------------------------------------------------ handlers
    def _set_language(self, v: str) -> None:
        self.settings.set("language", v)
        self.ctx.rebuild_soon()

    def _set_theme(self, v: str) -> None:
        self.settings.set("theme", v)
        self.ctx.rebuild_soon()

    def _set_resolution(self, v: str) -> None:
        w, h = (int(x) for x in v.split("x"))
        cam = dict(self.settings.get("camera"))
        cam.update(width=w, height=h)
        self.settings.set("camera", cam)

    def _choose_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, tr("settings.choose"), self.folder.text())
        if path:
            self.folder.setText(path)
            self.settings.set("screenshots.folder", path)

    @staticmethod
    def _open_folder(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _open_extension(self) -> None:
        candidates = [resource_dir() / "browser-extension", resource_dir().parents[1] / "browser-extension"]
        for c in candidates:
            if c.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(c)))
                break
        QMessageBox.information(self, tr("settings.bridge_install"), tr("settings.bridge_steps"))

    def _integrations(self) -> None:
        c = self.controller
        if not self.settings.get("browser_bridge.enabled", True):
            self.bridge_status.setText(tr("settings.bridge_off"))
        elif c.bridge is None:
            self.bridge_status.setText(tr("settings.bridge_error"))
        elif c.bridge.connected:
            self.bridge_status.setText("✅ " + tr("settings.bridge_connected", n=c.bridge.connected))
        else:
            self.bridge_status.setText("⏳ " + tr("settings.bridge_waiting"))

        on = bool(self.settings.get("remote.enabled"))
        self.remote_box.setVisible(on)
        if on:
            if c.remote is None:
                self.remote_info.setText(tr("settings.remote_error"))
                self.qr.clear()
                return
            from movo.services.remote_server import local_addresses

            ip = local_addresses()[0]
            self.remote_info.setText(tr("settings.remote_info", ip=ip, port=c.remote.port, code=c.remote.code))
            self.qr.setPixmap(qr_pixmap(c.remote.pairing_uri()))
            devs = c.remote.devices
            self.remote_devices.setText(
                tr("settings.remote_devices", devices=", ".join(devs)) if devs else tr("settings.remote_none")
            )

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, tr("settings.export"), str(Path.home() / "movo-settings.json"), "JSON (*.json)"
        )
        if path:
            self.settings.export_to(Path(path))

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("settings.import"), str(Path.home()), "JSON (*.json)")
        if path:
            try:
                self.settings.import_from(Path(path))
                self.ctx.rebuild_soon()
            except (OSError, ValueError):
                QMessageBox.warning(self, tr("settings.import"), tr("settings.import_failed"))

    def _reset(self) -> None:
        if QMessageBox.question(self, tr("settings.reset"), tr("settings.reset_q")) == QMessageBox.Yes:
            self.settings.reset()
            self.ctx.rebuild_soon()
