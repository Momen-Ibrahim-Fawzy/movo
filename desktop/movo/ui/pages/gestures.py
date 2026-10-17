"""Hand gestures and head gestures pages: bindings, sensitivity, practice highlights."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QGridLayout, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget

from movo.core.catalog import ACTION_CATEGORIES, ACTIONS, EYE_GESTURES, HAND_GESTURES, HEAD_GESTURES
from movo.i18n import tr
from movo.ui import theme
from movo.ui.pages import Page
from movo.ui.pages.home import profile_name
from movo.ui.widgets import Card, SettingRow, Toggle, combo, flash, label, page_header, slider, toggle_row


def action_combo(current: str) -> QComboBox:
    c = QComboBox()
    c.setMinimumWidth(210)
    c.setMaxVisibleItems(18)
    c.addItem(f"∅  {tr('a.none')}", "none")
    for cat in ACTION_CATEGORIES:
        items = [a for a in ACTIONS if a.category == cat and a.id != "none"]
        if not items:
            continue
        c.insertSeparator(c.count())
        for a in items:
            c.addItem(f"{a.emoji}  {tr(f'a.{a.id}')}", a.id)
    idx = c.findData(current)
    c.setCurrentIndex(max(0, idx))
    return c


class GestureCard(Card):
    def __init__(self, page: GesturesPage, gesture):
        super().__init__(padding=16, spacing=8, shadow=False)
        self.page = page
        self.g = gesture
        s = page.settings
        top = QHBoxLayout()
        emoji = label(gesture.emoji, "Emoji")
        emoji.setFixedWidth(46)
        top.addWidget(emoji, 0, Qt.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(2)
        name_row = QHBoxLayout()
        name_row.addWidget(label(tr(f"g.{gesture.id}"), "SectionTitle"))
        if gesture.accurate_only and gesture.source == "head":
            badge = label(tr("head.accurate_badge"), "Small")
            badge.setStyleSheet(
                f"background:{theme.current().accent_soft}; color:{theme.current().accent}; border-radius:8px; padding:2px 8px;"
            )
            name_row.addWidget(badge)
        name_row.addStretch(1)
        text.addLayout(name_row)
        text.addWidget(label(tr(f"g.{gesture.id}.how"), "Small", wrap=True))
        top.addLayout(text, 1)
        self.enabled = Toggle(s.gesture_enabled(gesture.id))
        self.enabled.setToolTip(tr("gestures.enable_tip"))
        self.enabled.toggled.connect(lambda v: s.set_gesture_enabled(gesture.id, v))
        top.addWidget(self.enabled, 0, Qt.AlignTop)
        self.lay.addLayout(top)

        row = QHBoxLayout()
        row.addWidget(label(tr("gestures.does"), "Muted"))
        self.combo = action_combo(s.binding(gesture.id, page.profile))
        self.combo.currentIndexChanged.connect(self._changed)
        row.addWidget(self.combo, 1)
        self.lay.addLayout(row)
        self.shortcut = QLineEdit(s.shortcut(gesture.id, page.profile))
        self.shortcut.setPlaceholderText(tr("gestures.shortcut_ph"))
        self.shortcut.editingFinished.connect(self._shortcut_changed)
        self.lay.addWidget(self.shortcut)
        self.shortcut.setVisible(self.combo.currentData() == "custom_shortcut")

    def _changed(self, _i: int) -> None:
        action = self.combo.currentData()
        self.shortcut.setVisible(action == "custom_shortcut")
        self.page.settings.set_binding(self.page.profile, self.g.id, action)

    def _shortcut_changed(self) -> None:
        from movo.actions.keys import parse_shortcut

        text = self.shortcut.text().strip()
        try:
            if text:
                parse_shortcut(text)
            self.shortcut.setStyleSheet("")
            self.page.settings.set_binding(self.page.profile, self.g.id, "custom_shortcut", text)
        except ValueError:
            self.shortcut.setStyleSheet(f"border: 1px solid {theme.current().danger};")


class GesturesPage(Page):
    source = "hand"

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self.profile = self.settings.get("active_profile")
        self.body.addWidget(
            page_header(
                tr(f"{self.source if self.source != 'eye' else 'eyes'}.title"),
                tr(f"{self.source if self.source != 'eye' else 'eyes'}.subtitle"),
            )
        )
        self.body.addWidget(self._settings_card())

        bar = QHBoxLayout()
        bar.addWidget(label(tr("gestures.editing"), "Muted"))
        self.profile_combo = combo(
            [(pid, profile_name(self.settings, pid)) for pid in self.settings.get("profiles", {})],
            self.profile,
            self._profile_selected,
            width=180,
        )
        bar.addWidget(self.profile_combo)
        bar.addStretch(1)
        reset = QPushButton(tr("gestures.reset"))
        reset.setObjectName("Ghost")
        reset.clicked.connect(self._reset_profile)
        bar.addWidget(reset)
        self.body.addLayout(bar)

        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(14)
        self.body.addWidget(self.grid_host)
        self.cards: dict[str, GestureCard] = {}
        self._fill()
        self.body.addStretch(1)
        self.controller.gesture_seen.connect(self._seen)
        self.controller.stats_changed.connect(self._stats)

    # ------------------------------------------------------------------ settings card
    def _settings_card(self) -> Card:
        s = self.settings
        card = Card()
        if self.source == "hand":
            card.lay.addWidget(
                toggle_row(
                    tr("hand.enable"), tr("hand.enable_d"), bool(s.get("hand.enabled", True)), lambda v: s.set("hand.enabled", v)
                )
            )
            card.lay.addWidget(
                SettingRow(
                    tr("hand.hold"),
                    tr("hand.hold_d"),
                    slider(float(s.get("hand.hold_scale", 1.0)), 0.5, 2.0, lambda v: s.set("hand.hold_scale", round(v, 2))),
                )
            )
            card.lay.addWidget(
                SettingRow(
                    tr("hand.scroll"),
                    tr("hand.scroll_d"),
                    slider(float(s.get("hand.scroll_speed", 1.0)), 0.3, 3.0, lambda v: s.set("hand.scroll_speed", round(v, 2))),
                )
            )
            card.lay.addWidget(
                toggle_row(
                    tr("hand.swipe"),
                    tr("hand.swipe_d"),
                    bool(s.get("hand.swipe_enabled", True)),
                    lambda v: s.set("hand.swipe_enabled", v),
                )
            )
            card.lay.addWidget(
                toggle_row(
                    tr("home.q_air"), tr("hand.air_d"), bool(s.get("pointer.air_mouse")), lambda v: s.set("pointer.air_mouse", v)
                )
            )
        else:
            card.lay.addWidget(
                toggle_row(
                    tr("head.enable"), tr("head.enable_d"), bool(s.get("head.enabled")), lambda v: s.set("head.enabled", v)
                )
            )
            card.lay.addWidget(
                SettingRow(
                    tr("head.mode"),
                    tr("head.mode_d"),
                    combo(
                        [("light", tr("head.mode_light")), ("accurate", tr("head.mode_accurate"))],
                        s.get("head.mode", "light"),
                        lambda v: (s.set("head.mode", v), self.ctx.rebuild_soon()),
                    ),
                )
            )
            card.lay.addWidget(
                SettingRow(
                    tr("head.sensitivity"),
                    tr("head.sensitivity_d"),
                    slider(float(s.get("head.sensitivity", 1.0)), 0.6, 1.8, lambda v: s.set("head.sensitivity", round(v, 2))),
                )
            )
            card.lay.addWidget(
                SettingRow(
                    tr("hand.hold"),
                    tr("head.hold_d"),
                    slider(float(s.get("head.hold_scale", 1.0)), 0.5, 2.0, lambda v: s.set("head.hold_scale", round(v, 2))),
                )
            )
            card.lay.addWidget(
                toggle_row(
                    tr("home.q_headptr"),
                    tr("head.pointer_d"),
                    bool(s.get("pointer.head_pointer")),
                    lambda v: s.set("pointer.head_pointer", v),
                )
            )
            card.lay.addWidget(
                SettingRow(
                    tr("head.pointer_speed"),
                    "",
                    slider(float(s.get("pointer.speed", 1.0)), 0.3, 3.0, lambda v: s.set("pointer.speed", round(v, 2))),
                )
            )
            recal = QPushButton(theme.icon("refresh", theme.current().text_muted, 16), tr("home.recalibrate"))
            recal.clicked.connect(self.controller.engine.recalibrate_head)
            card.lay.addWidget(SettingRow(tr("head.recalibrate"), tr("head.recalibrate_tip"), recal))
        return card

    # ------------------------------------------------------------------ grid
    def _gestures(self):
        return {"hand": HAND_GESTURES, "head": HEAD_GESTURES, "eye": EYE_GESTURES}[self.source]

    def _fill(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.cards.clear()
        cols = 2
        for i, g in enumerate(self._gestures()):
            card = GestureCard(self, g)
            self.cards[g.id] = card
            self.grid.addWidget(card, i // cols, i % cols)

    def _profile_selected(self, pid: str) -> None:
        self.profile = pid
        self._fill()

    def _reset_profile(self) -> None:
        p = self.settings.data["profiles"][self.profile]
        ids = {g.id for g in self._gestures()}
        from movo.core.catalog import PROFILE_PRESETS

        preset = PROFILE_PRESETS.get(self.profile, {}).get("overrides", {})
        for gid in ids:
            p["bindings"].pop(gid, None)
            if gid in preset:
                p["bindings"][gid] = preset[gid]
        self.settings.save()
        self.settings.notify(f"profiles.{self.profile}")
        self._fill()

    # ------------------------------------------------------------------ live feedback
    def _seen(self, ev, _action) -> None:
        card = self.cards.get(ev.gesture)
        if card is not None and self.isVisible():
            flash(card)

    def _stats(self, s) -> None:
        if not self.isVisible():
            return
        pose = s.hand_pose if self.source == "hand" else s.head_pose
        for gid, card in self.cards.items():
            card.set_active(gid == pose)


class HandPage(GesturesPage):
    source = "hand"


class HeadPage(GesturesPage):
    source = "head"
