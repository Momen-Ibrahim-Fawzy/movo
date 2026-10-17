from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from imaa.core.catalog import ACTIONS_BY_ID, ALL_GESTURES
from imaa.i18n import tr
from imaa.ui import theme
from imaa.ui.pages import Page
from imaa.ui.widgets import Card, PowerButton, PreviewView, StatusDot, Toggle, combo, label, page_header


def profile_name(settings, pid: str) -> str:
    p = settings.get("profiles", {}).get(pid, {})
    return p.get("name") or tr(f"profile.{pid}")


class HomePage(Page):
    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        pal = theme.current()
        self.body.addWidget(page_header(tr("home.title"), tr("home.subtitle")))

        top = QHBoxLayout()
        top.setSpacing(18)

        # ---------------- control card
        control = Card()
        control.setMinimumWidth(320)
        control.lay.setAlignment(Qt.AlignTop)
        self.power = PowerButton()
        self.power.setToolTip(tr("home.power_tip"))
        self.power.clicked.connect(self._power_clicked)
        control.lay.addWidget(self.power, 0, Qt.AlignHCenter)

        status_row = QHBoxLayout()
        status_row.setAlignment(Qt.AlignHCenter)
        self.dot = StatusDot(pal.text_muted)
        self.status = label("", "BigStatus")
        status_row.addWidget(self.dot)
        status_row.addWidget(self.status)
        control.lay.addLayout(status_row)
        self.detail = label("", "Muted")
        self.detail.setAlignment(Qt.AlignHCenter)
        self.detail.setWordWrap(True)
        control.lay.addWidget(self.detail)

        btns = QHBoxLayout()
        self.pause_btn = QPushButton()
        self.pause_btn.clicked.connect(self.controller.toggle_pause)
        self.recal_btn = QPushButton(theme.icon("refresh", pal.text_muted, 16), tr("home.recalibrate"))
        self.recal_btn.setToolTip(tr("head.recalibrate_tip"))
        self.recal_btn.clicked.connect(self.controller.engine.recalibrate_head)
        btns.addWidget(self.pause_btn)
        btns.addWidget(self.recal_btn)
        control.lay.addLayout(btns)

        prof_row = QHBoxLayout()
        prof_row.addWidget(label(tr("home.profile"), "Muted"))
        self.profile_combo = combo(
            [(pid, profile_name(self.settings, pid)) for pid in self.settings.get("profiles", {})],
            self.settings.get("active_profile"),
            lambda v: self.settings.set("active_profile", v),
            width=150,
        )
        prof_row.addWidget(self.profile_combo, 1)
        control.lay.addLayout(prof_row)
        self.auto_profile = label("", "Small")
        self.auto_profile.setWordWrap(True)
        control.lay.addWidget(self.auto_profile)
        control.lay.addStretch(1)
        top.addWidget(control, 0)

        # ---------------- preview card
        preview_card = Card()
        head = QHBoxLayout()
        head.addWidget(label(tr("home.preview"), "SectionTitle"))
        head.addStretch(1)
        head.addWidget(label(tr("home.show_camera"), "Muted"))
        self.preview_toggle = Toggle(bool(self.settings.get("show_preview", True)))
        self.preview_toggle.toggled.connect(self._preview_toggled)
        head.addWidget(self.preview_toggle)
        preview_card.lay.addLayout(head)
        self.preview = PreviewView()
        self.preview.setMinimumHeight(300)
        preview_card.lay.addWidget(self.preview, 1)
        self.chips = QHBoxLayout()
        self.fps_label = label("", "Small")
        self.light_label = label("", "Small")
        self.chips.addWidget(self.fps_label)
        self.chips.addStretch(1)
        self.chips.addWidget(self.light_label)
        preview_card.lay.addLayout(self.chips)
        top.addWidget(preview_card, 1)
        self.body.addLayout(top)

        # ---------------- quick toggles
        quick = Card()
        quick.lay.addWidget(label(tr("home.quick"), "SectionTitle"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(10)
        items = [
            ("hand.enabled", "home.q_hand", "home.q_hand_d"),
            ("head.enabled", "home.q_head", "home.q_head_d"),
            ("pointer.air_mouse", "home.q_air", "home.q_air_d"),
            ("pointer.head_pointer", "home.q_headptr", "home.q_headptr_d"),
            ("hud.enabled", "home.q_hud", "home.q_hud_d"),
            ("__practice__", "home.q_practice", "home.q_practice_d"),
        ]
        for i, (key, title, desc) in enumerate(items):
            grid.addWidget(self._quick_item(key, tr(title), tr(desc)), i // 2, i % 2)
        quick.lay.addLayout(grid)
        self.body.addWidget(quick)

        # ---------------- activity
        activity = Card()
        activity.lay.addWidget(label(tr("home.activity"), "SectionTitle"))
        self.feed = QVBoxLayout()
        self.feed.setSpacing(6)
        self.empty_feed = label(tr("home.activity_empty"), "Muted", wrap=True)
        self.feed.addWidget(self.empty_feed)
        activity.lay.addLayout(self.feed)
        self.body.addWidget(activity)

        privacy = QWidget()
        privacy.setObjectName("Banner")
        pl = QHBoxLayout(privacy)
        pl.setContentsMargins(16, 12, 16, 12)
        lock = QLabel()
        lock.setPixmap(theme.icon_pixmap("lock", pal.accent, 18))
        pl.addWidget(lock)
        pl.addWidget(label(tr("home.privacy"), wrap=True), 1)
        self.body.addWidget(privacy)
        self.body.addStretch(1)

        c = self.controller
        c.state_changed.connect(self._on_state)
        c.stats_changed.connect(self._on_stats)
        c.preview_frame.connect(self._on_preview)
        c.action_done.connect(self._on_action)
        c.profile_changed.connect(self._on_profile)
        self._on_state(c.state)
        self._on_profile(c.effective_profile)
        self._feed_items: list[QWidget] = []

    # ------------------------------------------------------------------ pieces
    def _quick_item(self, key: str, title: str, desc: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 4, 0, 4)
        text = QVBoxLayout()
        text.setSpacing(1)
        text.addWidget(label(title))
        text.addWidget(label(desc, "Small", wrap=True))
        lay.addLayout(text, 1)
        if key == "__practice__":
            t = Toggle(self.controller.dispatcher.practice)
            t.toggled.connect(self.controller.set_practice)
        else:
            t = Toggle(bool(self.settings.get(key)))
            t.toggled.connect(lambda v, k=key: self.settings.set(k, v))
        lay.addWidget(t)
        return w

    def _power_clicked(self) -> None:
        self.controller.toggle()
        self.power.setChecked(self.controller.running)

    def _preview_toggled(self, on: bool) -> None:
        self.settings.set("show_preview", on)
        self.controller.set_preview_enabled(on and self.isVisible())
        if not on:
            self.preview.placeholder = tr("home.preview_hidden")
            self.preview.set_frame(None)

    def on_shown(self) -> None:
        self.controller.set_preview_enabled(bool(self.settings.get("show_preview", True)))

    def on_hidden(self) -> None:
        self.controller.set_preview_enabled(False)

    # ------------------------------------------------------------------ signals
    def _on_state(self, state: str) -> None:
        pal = theme.current()
        running = state in ("running", "paused", "starting")
        self.power.setChecked(running)
        self.power.set_busy(state == "starting")
        self.pause_btn.setEnabled(running)
        self.recal_btn.setEnabled(
            running and bool(self.settings.get("head.enabled") or self.settings.get("pointer.head_pointer"))
        )
        self.pause_btn.setText(tr("home.resume") if state == "paused" else tr("home.pause"))
        self.pause_btn.setIcon(theme.icon("play" if state == "paused" else "pause", pal.text_muted, 16))
        if state.startswith("error:"):
            key = state.split(":", 1)[1]
            self.status.setText(tr("state.error"))
            self.detail.setText(tr(f"error.{key}"))
            self.dot.set_color(pal.danger)
            self.dot.set_pulse(False)
        else:
            self.status.setText(tr(f"state.{state}"))
            self.detail.setText(tr(f"state.{state}_d", hotkey=_pretty_hotkey(self.settings.get("hotkey_pause", ""))))
            color = {"running": pal.success, "paused": pal.warning, "starting": pal.accent}.get(state, pal.text_muted)
            self.dot.set_color(color)
            self.dot.set_pulse(state == "running")
        if not running:
            self.preview.placeholder = tr("home.preview_off")
            self.preview.set_frame(None)
            self.fps_label.setText("")
            self.light_label.setText("")

    def _on_stats(self, s) -> None:
        if self.controller.state not in ("running", "paused"):
            return
        parts = [tr("home.fps", fps=int(s.fps))]
        if s.idle:
            parts.append(tr("home.idle"))
        self.fps_label.setText(" · ".join(parts))
        self.light_label.setText("💡 " + tr("home.low_light") if s.low_light else "")
        live = s.hand_pose or s.head_pose
        self.preview.overlay_text = _live_text(live)

    def _on_preview(self, img) -> None:
        if self.preview_toggle.isChecked() and self.isVisible():
            self.preview.set_frame(img)

    def _on_profile(self, pid: str) -> None:
        manual = self.settings.get("active_profile")
        idx = self.profile_combo.findData(manual)
        if idx >= 0 and idx != self.profile_combo.currentIndex():
            self.profile_combo.blockSignals(True)
            self.profile_combo.setCurrentIndex(idx)
            self.profile_combo.blockSignals(False)
        if pid and pid != manual:
            self.auto_profile.setText(tr("home.auto_profile", profile=profile_name(self.settings, pid)))
        else:
            self.auto_profile.setText("")

    def _on_action(self, result) -> None:
        info = ACTIONS_BY_ID.get(result.action)
        if info is None:
            return
        text = tr(f"hud.{result.message}", **result.args) if result.message else tr(f"a.{result.action}")
        g = ALL_GESTURES.get(result.gesture)
        who = f"{g.emoji} {tr(f'g.{g.id}')}" if g else (tr("home.from_phone") if result.source == "remote" else "")
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.addWidget(label(info.emoji))
        lay.addWidget(label(text), 1)
        lay.addWidget(label(who, "Small"))
        lay.addWidget(label(datetime.now().strftime("%H:%M:%S"), "Small"))
        if not result.ok:
            row.setToolTip(tr("home.action_failed"))
        self.empty_feed.hide()
        self.feed.insertWidget(0, row)
        self._feed_items.insert(0, row)
        while len(self._feed_items) > 6:
            old = self._feed_items.pop()
            old.deleteLater()


def _live_text(pose) -> str:
    if not pose:
        return ""
    g = ALL_GESTURES.get(pose)
    if g:
        return f"{g.emoji}  {tr(f'g.{pose}')}"
    return tr(f"pose.{pose}")


def _pretty_hotkey(combo: str) -> str:
    return "+".join(p.strip("<>").capitalize() for p in combo.split("+")) if combo else ""
