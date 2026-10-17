from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QInputDialog, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton

from movo.i18n import tr
from movo.ui import theme
from movo.ui.pages import Page
from movo.ui.pages.home import profile_name
from movo.ui.widgets import Card, SettingRow, label, page_header, toggle_row

PROFILE_EMOJI = {"general": "🧭", "presentation": "📽️", "media": "🎬", "browser": "🌐", "meeting": "🎥"}


class ProfilesPage(Page):
    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        s = self.settings
        self.body.addWidget(page_header(tr("profiles.title"), tr("profiles.subtitle")))

        auto = Card()
        auto.lay.addWidget(
            toggle_row(
                tr("profiles.auto"),
                tr("profiles.auto_d"),
                bool(s.get("auto_profiles", True)),
                lambda v: s.set("auto_profiles", v),
            )
        )
        self.body.addWidget(auto)

        row = QHBoxLayout()
        row.setSpacing(18)
        left = Card()
        left.setFixedWidth(280)
        left.lay.addWidget(label(tr("profiles.list"), "SectionTitle"))
        self.list = QListWidget()
        self.list.setMinimumHeight(300)
        self.list.currentItemChanged.connect(self._select)
        left.lay.addWidget(self.list, 1)
        btns = QHBoxLayout()
        add = QPushButton(theme.icon("plus", theme.current().text_muted, 16), tr("profiles.new"))
        add.clicked.connect(self._add)
        btns.addWidget(add)
        left.lay.addLayout(btns)
        row.addWidget(left)

        self.editor = Card()
        row.addWidget(self.editor, 1)
        self.body.addLayout(row)
        self.body.addStretch(1)
        self._reload()

    def _reload(self, select: str = "") -> None:
        self.list.blockSignals(True)
        self.list.clear()
        active = self.settings.get("active_profile")
        for pid in self.settings.get("profiles", {}):
            text = f"{PROFILE_EMOJI.get(pid, '⭐')}  {profile_name(self.settings, pid)}"
            if pid == active:
                text += f"   · {tr('profiles.active')}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, pid)
            self.list.addItem(item)
            if pid == (select or active):
                self.list.setCurrentItem(item)
        self.list.blockSignals(False)
        self._select(self.list.currentItem())

    def _select(self, item, _prev=None) -> None:
        lay = self.editor.lay
        while lay.count():
            it = lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
            elif it.layout():
                _clear_layout(it.layout())
        if item is None:
            return
        pid = item.data(Qt.UserRole)
        s = self.settings
        p = s.get("profiles")[pid]
        lay.addWidget(label(f"{PROFILE_EMOJI.get(pid, '⭐')}  {profile_name(s, pid)}", "SectionTitle"))
        lay.addWidget(label(tr(f"profile.{pid}.d") if pid in PROFILE_EMOJI else tr("profiles.custom_d"), "Muted", wrap=True))

        apps = QLineEdit(", ".join(p.get("apps", [])))
        apps.setPlaceholderText(tr("profiles.apps_ph"))
        apps.setMinimumWidth(260)

        def save_apps():
            p["apps"] = [a.strip().lower() for a in apps.text().split(",") if a.strip()]
            s.save()
            s.notify(f"profiles.{pid}")

        apps.editingFinished.connect(save_apps)
        lay.addWidget(SettingRow(tr("profiles.apps"), tr("profiles.apps_d"), apps))
        current = self.controller.active_app
        if current:
            lay.addWidget(label(tr("profiles.current_app", app=current), "Small"))

        n = len(p.get("bindings", {}))
        lay.addWidget(label(tr("profiles.overrides", n=n), "Muted"))

        btns = QHBoxLayout()
        use = QPushButton(tr("profiles.use"))
        use.setObjectName("Primary")
        use.setEnabled(pid != s.get("active_profile"))
        use.clicked.connect(lambda: (s.set("active_profile", pid), self._reload(pid)))
        btns.addWidget(use)
        edit = QPushButton(tr("profiles.edit_gestures"))
        edit.clicked.connect(lambda: self.ctx.go("hand"))
        btns.addWidget(edit)
        dup = QPushButton(tr("profiles.duplicate"))
        dup.clicked.connect(lambda: self._add(copy_from=pid))
        btns.addWidget(dup)
        btns.addStretch(1)
        if pid not in PROFILE_EMOJI:
            ren = QPushButton(tr("profiles.rename"))
            ren.clicked.connect(lambda: self._rename(pid))
            btns.addWidget(ren)
        if pid != "general":
            delete = QPushButton(theme.icon("trash", theme.current().danger, 16), tr("profiles.delete"))
            delete.setObjectName("Danger")
            delete.clicked.connect(lambda: self._delete(pid))
            btns.addWidget(delete)
        lay.addLayout(btns)
        lay.addStretch(1)

    def _add(self, copy_from: str = "") -> None:
        name, ok = QInputDialog.getText(self, tr("profiles.new"), tr("profiles.name"))
        if ok and name.strip():
            pid = self.settings.add_profile(name.strip()[:40], copy_from or "general")
            self._reload(pid)

    def _rename(self, pid: str) -> None:
        name, ok = QInputDialog.getText(self, tr("profiles.rename"), tr("profiles.name"), text=profile_name(self.settings, pid))
        if ok and name.strip():
            self.settings.data["profiles"][pid]["name"] = name.strip()[:40]
            self.settings.save()
            self.settings.notify("profiles")
            self._reload(pid)

    def _delete(self, pid: str) -> None:
        if (
            QMessageBox.question(self, tr("profiles.delete"), tr("profiles.delete_q", name=profile_name(self.settings, pid)))
            == QMessageBox.Yes
        ):
            self.settings.delete_profile(pid)
            self._reload()


def _clear_layout(layout) -> None:
    while layout.count():
        it = layout.takeAt(0)
        if it.widget():
            it.widget().deleteLater()
        elif it.layout():
            _clear_layout(it.layout())
