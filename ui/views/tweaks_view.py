from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QScrollArea, QLineEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from core.tweaks_engine import TweaksEngine, TWEAK_CATALOG
from ui.animated_widgets import AnimatedButton, AnimatedToggleSwitch
from ui.styles import COLORS


_CAT_COLORS = {
    "Gaming": ("tweaks_bg", "tweaks_fg", "🎮"),
    "Privacy": ("ram_bg", "ram_fg", "🔒"),
    "System": ("cpu_bg", "cpu_fg", "⚡"),
    "Network": ("gpu_bg", "gpu_fg", "🌐"),
}


class _RestorePointWorker(QThread):
    finished_result = pyqtSignal(bool, str)

    def run(self):
        ok, msg = TweaksEngine.create_restore_point()
        self.finished_result.emit(ok, msg)


class TweakStatCard(QFrame):
    """Compact KPI metric card matching WinGame's Sparkle style."""
    def __init__(self, title: str, initial_val: str, subtitle: str, bg_color: str, fg_color: str, icon_symbol: str, parent=None):
        super().__init__(parent)
        self.setObjectName("TweakStatCard")
        self.setStyleSheet(f"""
            QFrame#TweakStatCard {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 14px;
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        icon_box = QLabel(icon_symbol)
        icon_box.setFixedSize(40, 40)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setStyleSheet(f"""
            background-color: {bg_color};
            color: {fg_color};
            border-radius: 10px;
            font-size: 18px;
        """)
        layout.addWidget(icon_box)

        txt = QVBoxLayout()
        txt.setSpacing(1)
        lbl_t = QLabel(title.upper())
        lbl_t.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {COLORS['text_muted']}; letter-spacing: 0.5px;")
        self.lbl_val = QLabel(initial_val)
        self.lbl_val.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {COLORS['text_primary']};")
        lbl_s = QLabel(subtitle)
        lbl_s.setStyleSheet(f"font-size: 11px; color: {COLORS['text_secondary']};")
        txt.addWidget(lbl_t)
        txt.addWidget(self.lbl_val)
        txt.addWidget(lbl_s)
        layout.addLayout(txt, 1)


class TweakCard(QFrame):
    """Individual Sparkle/RyTuneX/Winhance tweak card with live toggle switch and badges."""
    tweak_toggled = pyqtSignal(str, bool)

    def __init__(self, tweak: dict, is_applied: bool, parent=None):
        super().__init__(parent)
        self.tweak = tweak
        self.tweak_id = tweak["id"]
        self._suppress = False
        self.setObjectName("TweakCard")
        self._update_border(is_applied)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Top row: icon + title + toggle switch
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        cat = tweak.get("category", "System")
        bg_k, fg_k, _ = _CAT_COLORS.get(cat, ("cpu_bg", "cpu_fg", "⚡"))

        icon_lbl = QLabel(tweak.get("icon", "⚡"))
        icon_lbl.setFixedSize(36, 36)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"""
            background-color: {COLORS[bg_k]};
            color: {COLORS[fg_k]};
            border-radius: 9px;
            font-size: 16px;
        """)
        top_row.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        lbl_title = QLabel(tweak["title"])
        lbl_title.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {COLORS['text_primary']};")
        lbl_title.setWordWrap(True)
        title_col.addWidget(lbl_title)

        # Badges row
        badges = QHBoxLayout()
        badges.setSpacing(6)

        cat_pill = QLabel(cat)
        cat_pill.setStyleSheet(f"""
            background-color: {COLORS[bg_k]};
            color: {COLORS[fg_k]};
            font-size: 10px;
            font-weight: 800;
            padding: 2px 7px;
            border-radius: 6px;
        """)
        badges.addWidget(cat_pill)

        if tweak.get("recommended"):
            rec_pill = QLabel("★ Recommended")
            rec_pill.setStyleSheet(f"""
                background-color: {COLORS['primary_light']};
                color: {COLORS['primary']};
                font-size: 10px;
                font-weight: 800;
                padding: 2px 7px;
                border-radius: 6px;
            """)
            badges.addWidget(rec_pill)

        if tweak.get("restart_needed"):
            rst_pill = QLabel("↻ Restart")
            rst_pill.setStyleSheet(f"""
                background-color: {COLORS['storage_bg']};
                color: {COLORS['storage_fg']};
                font-size: 10px;
                font-weight: 800;
                padding: 2px 7px;
                border-radius: 6px;
            """)
            badges.addWidget(rst_pill)

        badges.addStretch()
        title_col.addLayout(badges)
        top_row.addLayout(title_col, 1)

        self.switch = AnimatedToggleSwitch(checked=is_applied)
        self.switch.toggled.connect(self._on_switch_changed)
        top_row.addWidget(self.switch, 0, Qt.AlignmentFlag.AlignTop)

        layout.addLayout(top_row)

        # Description
        lbl_desc = QLabel(tweak["desc"])
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']};")
        layout.addWidget(lbl_desc)
        layout.addStretch()

    def _update_border(self, active: bool):
        border_col = COLORS["primary"] if active else COLORS["border"]
        self.setStyleSheet(f"""
            QFrame#TweakCard {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {border_col};
                border-radius: 13px;
            }}
            QFrame#TweakCard:hover {{
                border: 1px solid {COLORS['primary']};
            }}
        """)

    def set_checked_silently(self, state: bool):
        self._suppress = True
        self.switch.setChecked(state)
        self._update_border(state)
        self._suppress = False

    def _on_switch_changed(self, checked: bool):
        if self._suppress:
            return
        self._update_border(checked)
        self.tweak_toggled.emit(self.tweak_id, checked)


class TweaksView(QWidget):
    tweaks_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_category = "All"
        self._cards = {}
        self._restore_worker = None
        self._setup_ui()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 22, 28, 28)
        layout.setSpacing(18)

        # ---------------- HEADER ----------------
        hdr = QHBoxLayout()
        t_box = QVBoxLayout()
        t_box.setSpacing(2)
        lbl_title = QLabel("Windows Tweaks & Debloat")
        lbl_title.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {COLORS['text_primary']};")
        lbl_sub = QLabel("Reversible gaming, privacy, latency & debloat tweaks inspired by Sparkle, RyTuneX & Winhance")
        lbl_sub.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']};")
        t_box.addWidget(lbl_title)
        t_box.addWidget(lbl_sub)
        hdr.addLayout(t_box, 1)

        self.btn_restore = AnimatedButton("🛡️ Restore Point", variant="secondary", compact=True)
        self.btn_restore.setMinimumWidth(140)
        self.btn_restore.setFixedHeight(34)
        self.btn_restore.clicked.connect(self._create_restore_point)
        hdr.addWidget(self.btn_restore)
        layout.addLayout(hdr)

        # ---------------- 3 KPI METRIC CARDS ----------------
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(14)

        self.kpi_total = TweakStatCard(
            "Applied Tweaks", "0 / 0", "Active Windows optimizations",
            COLORS["primary_light"], COLORS["primary"], "⚡"
        )
        self.kpi_gaming = TweakStatCard(
            "Gaming & Latency", "0 Active", "FPS, GPU & input response",
            COLORS["tweaks_bg"], COLORS["tweaks_fg"], "🎮"
        )
        self.kpi_privacy = TweakStatCard(
            "Privacy & Debloat", "0 Active", "Telemetry, ads & background apps",
            COLORS["ram_bg"], COLORS["ram_fg"], "🔒"
        )
        kpi_row.addWidget(self.kpi_total, 1)
        kpi_row.addWidget(self.kpi_gaming, 1)
        kpi_row.addWidget(self.kpi_privacy, 1)
        layout.addLayout(kpi_row)

        # ---------------- PRESETS & FILTER BAR ----------------
        bar = QFrame()
        bar.setObjectName("TweakToolbar")
        bar.setStyleSheet(f"""
            QFrame#TweakToolbar {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 13px;
            }}
        """)
        bar_layout = QVBoxLayout(bar)
        bar_layout.setContentsMargins(16, 12, 16, 12)
        bar_layout.setSpacing(10)

        # Row 1: Presets
        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        lbl_pre = QLabel("1-CLICK PRESETS:")
        lbl_pre.setStyleSheet(f"font-size: 11px; font-weight: 800; color: {COLORS['text_muted']}; letter-spacing: 0.6px;")
        preset_row.addWidget(lbl_pre)

        self.btn_preset_gaming = AnimatedButton("🎮 Gaming Preset", variant="primary", compact=True)
        self.btn_preset_gaming.setMinimumWidth(135)
        self.btn_preset_gaming.setFixedHeight(30)
        self.btn_preset_gaming.clicked.connect(lambda: self._apply_preset("gaming"))
        preset_row.addWidget(self.btn_preset_gaming)

        self.btn_preset_privacy = AnimatedButton("🔒 Privacy Preset", variant="secondary", compact=True)
        self.btn_preset_privacy.setMinimumWidth(135)
        self.btn_preset_privacy.setFixedHeight(30)
        self.btn_preset_privacy.clicked.connect(lambda: self._apply_preset("privacy"))
        preset_row.addWidget(self.btn_preset_privacy)

        preset_row.addStretch()

        self.btn_revert_all = AnimatedButton("↩️ Revert All", variant="danger", compact=True)
        self.btn_revert_all.setMinimumWidth(115)
        self.btn_revert_all.setFixedHeight(30)
        self.btn_revert_all.clicked.connect(self._confirm_revert_all)
        preset_row.addWidget(self.btn_revert_all)
        bar_layout.addLayout(preset_row)

        # Row 2: Category filter pills + search
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        self.filter_btns = {}
        categories = [
            ("All", f"All ({len(TWEAK_CATALOG)})"),
            ("Gaming", "🎮 Gaming"),
            ("Privacy", "🔒 Privacy"),
            ("System", "⚡ System"),
            ("Network", "🌐 Network"),
        ]
        for cat_id, label in categories:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(cat_id == "All")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['bg_table_header']};
                    color: {COLORS['text_secondary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                    padding: 4px 12px;
                    font-size: 12px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    border-color: {COLORS['primary']};
                    color: {COLORS['text_primary']};
                }}
                QPushButton:checked {{
                    background-color: {COLORS['primary']};
                    color: #FFFFFF;
                    border-color: {COLORS['primary']};
                }}
            """)
            btn.clicked.connect(lambda _chk, c=cat_id: self._set_category(c))
            self.filter_btns[cat_id] = btn
            filter_row.addWidget(btn)

        filter_row.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search tweaks (HAGS, Telemetry, Nagle, Copilot...)")
        self.search_input.setFixedWidth(290)
        self.search_input.textChanged.connect(self._apply_filters)
        filter_row.addWidget(self.search_input)
        bar_layout.addLayout(filter_row)

        layout.addWidget(bar)

        # ---------------- LIVE STATUS TOAST ----------------
        self.lbl_toast = QLabel("")
        self.lbl_toast.setWordWrap(True)
        self.lbl_toast.setStyleSheet(f"""
            background-color: {COLORS['primary_light']};
            color: {COLORS['primary']};
            border: 1px solid {COLORS['border']};
            border-radius: 10px;
            padding: 10px 14px;
            font-size: 12px;
            font-weight: 700;
        """)
        self.lbl_toast.setVisible(False)
        layout.addWidget(self.lbl_toast)

        # ---------------- 2-COLUMN TWEAK CARDS GRID ----------------
        self.grid_container = QWidget()
        self.grid = QGridLayout(self.grid_container)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(14)
        self.grid.setVerticalSpacing(14)
        layout.addWidget(self.grid_container)

        # Build cards from live Windows state (parented to grid_container so they NEVER spawn top-level windows)
        for tweak in TWEAK_CATALOG:
            applied = TweaksEngine.is_applied(tweak["id"])
            card = TweakCard(tweak, is_applied=applied, parent=self.grid_container)
            card.tweak_toggled.connect(self._on_tweak_toggled)
            self._cards[tweak["id"]] = card

        self._apply_filters()
        self._update_kpis()

        layout.addStretch(1)
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def refresh_states(self):
        """Re-reads live Windows Registry/Powercfg state for every tweak."""
        for tid, card in self._cards.items():
            card.set_checked_silently(TweaksEngine.is_applied(tid))
        self._update_kpis()

    def _update_kpis(self):
        stats = TweaksEngine.get_summary_stats()
        self.kpi_total.lbl_val.setText(f"{stats['applied']} / {stats['total']}")
        self.kpi_gaming.lbl_val.setText(f"{stats['gaming_applied']} Active")
        self.kpi_privacy.lbl_val.setText(f"{stats['privacy_applied']} Active")

    def _set_category(self, category: str):
        self._active_category = category
        for cid, btn in self.filter_btns.items():
            btn.setChecked(cid == category)
        self._apply_filters()

    def _apply_filters(self):
        query = self.search_input.text().strip().lower()

        # Detach all cards cleanly from grid without deleting them
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().setVisible(False)

        col_idx = 0
        row_idx = 0
        for tweak in TWEAK_CATALOG:
            card = self._cards[tweak["id"]]
            cat_ok = (self._active_category == "All") or (tweak["category"] == self._active_category)
            q_ok = (not query) or (query in tweak["title"].lower()) or (query in tweak["desc"].lower()) or (query in tweak["category"].lower())
            if cat_ok and q_ok:
                self.grid.addWidget(card, row_idx, col_idx)
                card.setVisible(True)
                col_idx += 1
                if col_idx >= 2:
                    col_idx = 0
                    row_idx += 1

        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)

    def _show_toast(self, msg: str, is_error: bool = False):
        bg = COLORS["danger_light"] if is_error else COLORS["tweaks_bg"]
        fg = COLORS["danger"] if is_error else COLORS["tweaks_fg"]
        self.lbl_toast.setStyleSheet(f"""
            background-color: {bg};
            color: {fg};
            border: 1px solid {COLORS['border']};
            border-radius: 10px;
            padding: 10px 14px;
            font-size: 12px;
            font-weight: 700;
        """)
        self.lbl_toast.setText(msg)
        self.lbl_toast.setVisible(True)

    def _on_tweak_toggled(self, tweak_id: str, enable: bool):
        ok, msg = TweaksEngine.apply_tweak(tweak_id, enable)
        if not ok:
            # Revert switch visually if failed (e.g. insufficient privileges)
            self._cards[tweak_id].set_checked_silently(TweaksEngine.is_applied(tweak_id))
            self._show_toast(f"⚠️ {msg}", is_error=True)
        else:
            self._show_toast(f"✓ {msg}", is_error=False)
        self._update_kpis()
        self.tweaks_updated.emit()

    def _apply_preset(self, preset: str):
        ok_cnt, fail_cnt = TweaksEngine.apply_preset(preset)
        self.refresh_states()
        self.tweaks_updated.emit()
        label = "Gaming Preset" if preset == "gaming" else "Privacy Preset"
        if fail_cnt == 0:
            self._show_toast(f"✓ {label} applied successfully ({ok_cnt} tweaks enabled)!", is_error=False)
        else:
            self._show_toast(f"⚠️ {label}: {ok_cnt} applied, {fail_cnt} failed (ensure WinGame runs as Administrator).", is_error=True)

    def _confirm_revert_all(self):
        reply = QMessageBox.question(
            self,
            "Revert All Tweaks",
            "Revert all active Windows Tweaks back to their default Windows settings?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            ok_cnt, fail_cnt = TweaksEngine.apply_preset("revert_all")
            self.refresh_states()
            self.tweaks_updated.emit()
            if fail_cnt == 0:
                self._show_toast(f"✓ Reverted {ok_cnt} tweak(s) cleanly back to Windows defaults.", is_error=False)
            else:
                self._show_toast(f"⚠️ Reverted {ok_cnt} tweak(s), {fail_cnt} could not be reverted (Admin required).", is_error=True)

    def _create_restore_point(self):
        self.btn_restore.setEnabled(False)
        self.btn_restore.setText("⏳ Creating...")
        self._show_toast("🛡️ Creating Windows System Restore Point... please wait a few seconds.", is_error=False)
        self._restore_worker = _RestorePointWorker(self)
        self._restore_worker.finished_result.connect(self._on_restore_point_done)
        self._restore_worker.start()

    def _on_restore_point_done(self, ok: bool, msg: str):
        self.btn_restore.setEnabled(True)
        self.btn_restore.setText("🛡️ Restore Point")
        self._show_toast(f"{'✓' if ok else '⚠️'} {msg}", is_error=not ok)
