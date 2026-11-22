import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QTableWidget,
    QTableWidgetItem, QHeaderView, QSpinBox, QCheckBox, QFrame,
    QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont
from config import ConfigManager
from ui.animated_widgets import AnimatedButton, AnimatedToggleSwitch, ModernIntervalStepper
from ui.styles import COLORS

class AutoKillerStatCard(QFrame):
    """Modern KPI summary card for auto-killer metrics."""
    def __init__(self, title: str, initial_val: str, subtitle: str, bg_color: str, fg_color: str, icon_symbol: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 14px;
            }}
            QFrame:hover {{
                border-color: #CBD5E1;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # Icon box
        icon_frame = QFrame()
        icon_frame.setFixedSize(46, 46)
        icon_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 12px;
                border: none;
            }}
        """)
        ic_layout = QVBoxLayout(icon_frame)
        ic_layout.setContentsMargins(0, 0, 0, 0)
        lbl_icon = QLabel(icon_symbol)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet(f"font-size: 20px; color: {fg_color}; font-weight: bold;")
        ic_layout.addWidget(lbl_icon)
        layout.addWidget(icon_frame)

        # Info texts
        info_box = QVBoxLayout()
        info_box.setSpacing(2)
        
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLORS['text_muted']}; text-transform: uppercase; letter-spacing: 0.5px;")
        info_box.addWidget(self.lbl_title)

        self.lbl_val = QLabel(initial_val)
        self.lbl_val.setStyleSheet(f"font-size: 20px; font-weight: 900; color: {COLORS['text_primary']};")
        info_box.addWidget(self.lbl_val)

        self.lbl_sub = QLabel(subtitle)
        self.lbl_sub.setStyleSheet(f"font-size: 11px; color: {COLORS['text_secondary']};")
        info_box.addWidget(self.lbl_sub)

        layout.addLayout(info_box, 1)

    def set_value(self, val_text: str, sub_text: str = None):
        self.lbl_val.setText(val_text)
        if sub_text:
            self.lbl_sub.setText(sub_text)


class AutoKillerView(QWidget):
    blacklist_updated = pyqtSignal()
    interval_changed = pyqtSignal(int)
    toggle_active = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_mgr = ConfigManager()
        self._setup_ui()
        self.refresh_blacklist()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(18)

        # ---------------- TOP TITLE & SUBTITLE ----------------
        title_box = QVBoxLayout()
        lbl_title = QLabel("Auto-Killer & Blacklist")
        lbl_title.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {COLORS['text_primary']};")
        lbl_sub = QLabel("Continuous force-termination engine running in ultra-fast loops (default 250ms) to kill unwanted background tasks")
        lbl_sub.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']};")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        layout.addLayout(title_box)

        # ---------------- 3 KPI METRIC STAT CARDS ----------------
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        is_active = self.config_mgr.get("auto_kill_enabled", False)
        ms = self.config_mgr.get("auto_kill_interval_ms", 250)

        # Card 1: Loop Status
        status_text = f"ACTIVE ({ms}ms)" if is_active else "PAUSED"
        self.card_status = AutoKillerStatCard(
            title="Loop Engine Status",
            initial_val=status_text,
            subtitle="Continuous task scanner",
            bg_color="#DCFCE7" if is_active else "#FEE2E2",
            fg_color="#16A34A" if is_active else "#DC2626",
            icon_symbol="⚡"
        )
        stats_row.addWidget(self.card_status)

        # Card 2: Monitored Targets
        targets_count = len(self.config_mgr.get("blacklist", []))
        self.card_targets = AutoKillerStatCard(
            title="Blacklisted Targets",
            initial_val=f"{targets_count} Targets",
            subtitle="Monitored for instant force-kill",
            bg_color="#E0F2FE",
            fg_color="#0284C7",
            icon_symbol="🎯"
        )
        stats_row.addWidget(self.card_targets)

        # Card 3: Total Eliminations
        self.card_kills = AutoKillerStatCard(
            title="Total Eliminations",
            initial_val="0 Kills",
            subtitle="Processes terminated in background",
            bg_color="#F3E8FF",
            fg_color="#9333EA",
            icon_symbol="🛡"
        )
        stats_row.addWidget(self.card_kills)

        layout.addLayout(stats_row)

        # ---------------- CONTROL PANEL BANNER ----------------
        ctrl_card = QFrame()
        ctrl_card.setObjectName("CtrlCard")
        ctrl_card.setStyleSheet(f"""
            QFrame#CtrlCard {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 14px;
                padding: 14px 18px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        ctrl_layout = QHBoxLayout(ctrl_card)
        ctrl_layout.setContentsMargins(16, 10, 16, 10)
        ctrl_layout.setSpacing(20)

        # Toggle Switch Row
        switch_box = QHBoxLayout()
        switch_box.setSpacing(12)
        self.toggle_switch = AnimatedToggleSwitch(checked=is_active)
        self.toggle_switch.toggled.connect(self._on_switch_toggled)
        self.lbl_switch_status = QLabel(f"MONITORING ACTIVE ({ms}ms)" if is_active else "MONITORING PAUSED (Click switch to start)")
        status_color = COLORS['success'] if is_active else COLORS['danger']
        self.lbl_switch_status.setStyleSheet(f"font-weight: 800; color: {status_color}; font-size: 13px;")
        switch_box.addWidget(self.toggle_switch)
        switch_box.addWidget(self.lbl_switch_status)
        ctrl_layout.addLayout(switch_box)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {COLORS['border']};")
        ctrl_layout.addWidget(sep)

        # Interval settings (Modern Stepper with generous width & clean buttons)
        lbl_interval = QLabel("Scan Interval:")
        lbl_interval.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 600;")
        ctrl_layout.addWidget(lbl_interval)

        self.spin_interval = ModernIntervalStepper(value=ms, min_val=50, max_val=10000, step=50)
        self.spin_interval.valueChanged.connect(self._on_interval_changed)
        ctrl_layout.addWidget(self.spin_interval)

        lbl_unit = QLabel("ms")
        lbl_unit.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 700; font-size: 13px;")
        ctrl_layout.addWidget(lbl_unit)

        # Checkbox kill children
        self.chk_tree = QCheckBox("Kill process tree (children)")
        self.chk_tree.setChecked(self.config_mgr.get("kill_children", True))
        self.chk_tree.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 600;")
        self.chk_tree.toggled.connect(self._on_tree_toggled)
        ctrl_layout.addWidget(self.chk_tree)

        ctrl_layout.addStretch()

        layout.addWidget(ctrl_card)

        # ---------------- MAIN CONTENT: BLACKLIST & LIVE FEED ----------------
        split_layout = QHBoxLayout()
        split_layout.setSpacing(18)

        # LEFT PANE: Blacklisted Targets Card
        left_card = QFrame()
        left_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 14px;
                padding: 16px;
            }}
        """)
        left_box = QVBoxLayout(left_card)
        left_box.setSpacing(12)
        
        lbl_bl_title = QLabel("🎯 Blacklisted Targets (Auto-Kill)")
        lbl_bl_title.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {COLORS['text_primary']};")
        left_box.addWidget(lbl_bl_title)

        # Add target input row
        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        self.txt_new_proc = QLineEdit()
        self.txt_new_proc.setPlaceholderText("File name (e.g. EpicGamesLauncher.exe)")
        self.txt_new_proc.returnPressed.connect(self._add_process_to_blacklist)
        add_row.addWidget(self.txt_new_proc)

        self.btn_add = AnimatedButton("+ Add Target", variant="primary")
        self.btn_add.clicked.connect(self._add_process_to_blacklist)
        add_row.addWidget(self.btn_add)
        left_box.addLayout(add_row)

        # Quick Preset Suggestions
        presets_row = QHBoxLayout()
        presets_row.setSpacing(6)
        lbl_presets = QLabel("Quick Add:")
        lbl_presets.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLORS['text_muted']};")
        presets_row.addWidget(lbl_presets)

        for p_name in ["EpicGamesLauncher.exe", "Discord.exe", "Spotify.exe", "explorer.exe"]:
            btn_p = QPushButton(f"+ {p_name}")
            btn_p.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_p.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['bg_table_header']};
                    color: {COLORS['primary']};
                    border: 1px solid #E2E8F0;
                    border-radius: 6px;
                    padding: 3px 8px;
                    font-size: 10px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background-color: #EFF6FF;
                    border-color: {COLORS['primary']};
                }}
            """)
            btn_p.clicked.connect(lambda _, n=p_name: self._quick_add_preset(n))
            presets_row.addWidget(btn_p)

        presets_row.addStretch()
        left_box.addLayout(presets_row)

        # Blacklist ListWidget
        self.list_blacklist = QListWidget()
        self.list_blacklist.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS['bg_table_header']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                padding: 6px;
                outline: none;
            }}
            QListWidget::item {{
                background-color: {COLORS['bg_card']};
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 10px 14px;
                margin-bottom: 6px;
                color: {COLORS['text_primary']};
                font-weight: 700;
                font-size: 13px;
            }}
            QListWidget::item:hover {{
                border-color: #CBD5E1;
                background-color: {COLORS['bg_card']};
            }}
            QListWidget::item:selected {{
                background-color: #EFF6FF;
                border-color: {COLORS['primary']};
                color: #1D4ED8;
            }}
        """)
        left_box.addWidget(self.list_blacklist)

        # Delete from Blacklist button
        self.btn_remove = AnimatedButton("🗑️ Remove Selected Target", variant="secondary")
        self.btn_remove.clicked.connect(self._remove_selected_from_blacklist)
        left_box.addWidget(self.btn_remove)

        split_layout.addWidget(left_card, 1)

        # RIGHT PANE: Live Kill Log Feed Card
        right_card = QFrame()
        right_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 14px;
                padding: 16px;
            }}
        """)
        right_box = QVBoxLayout(right_card)
        right_box.setSpacing(12)

        log_top = QHBoxLayout()
        lbl_log_title = QLabel("⚡ Live Execution Kill Feed")
        lbl_log_title.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {COLORS['text_primary']};")
        log_top.addWidget(lbl_log_title)
        log_top.addStretch()

        self.btn_clear_log = AnimatedButton("Clear Feed", variant="secondary")
        self.btn_clear_log.setFixedHeight(28)
        self.btn_clear_log.clicked.connect(self._clear_logs)
        log_top.addWidget(self.btn_clear_log)
        right_box.addLayout(log_top)

        # Log Table
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(4)
        self.log_table.setHorizontalHeaderLabels(["Timestamp", "Target Executable", "PID", "Result"])
        header = self.log_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.log_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.log_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.verticalHeader().setDefaultSectionSize(38)
        self.log_table.setShowGrid(False)
        self.log_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_table_header']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 6px 12px;
                border-bottom: 1px solid #E2E8F0;
            }}
        """)
        right_box.addWidget(self.log_table)

        split_layout.addWidget(right_card, 1)
        layout.addLayout(split_layout)

    def _quick_add_preset(self, exe_name: str):
        success, msg = self.add_target(exe_name)
        if not success:
            QMessageBox.information(self, "Preset Notice", msg)

    def refresh_blacklist(self):
        try:
            self.list_blacklist.clear()
            blacklist = self.config_mgr.get("blacklist", [])
            for name in blacklist:
                item = QListWidgetItem(f"🎯   {name}")
                item.setData(Qt.ItemDataRole.UserRole, name)
                self.list_blacklist.addItem(item)
            self.card_targets.set_value(f"{len(blacklist)} Targets", "Active blacklisted executables")
        except Exception as e:
            print(f"[AutoKillerView] refresh_blacklist error: {e}")

    def add_target(self, process_name: str) -> tuple[bool, str]:
        success, msg = self.config_mgr.add_to_blacklist(process_name)
        if success:
            self.refresh_blacklist()
            self.blacklist_updated.emit()
        return success, msg

    def _add_process_to_blacklist(self):
        try:
            name = self.txt_new_proc.text().strip()
            if not name:
                return
            
            success, message = self.add_target(name)
            if success:
                self.txt_new_proc.clear()
            else:
                QMessageBox.warning(self, "Invalid Target", message)
        except Exception as e:
            print(f"[AutoKillerView] _add_process_to_blacklist error: {e}")

    def _remove_selected_from_blacklist(self):
        try:
            current_item = self.list_blacklist.currentItem()
            if not current_item:
                return
            name = current_item.data(Qt.ItemDataRole.UserRole)
            if name:
                self.config_mgr.remove_from_blacklist(name)
                self.refresh_blacklist()
                self.blacklist_updated.emit()
        except Exception as e:
            print(f"[AutoKillerView] _remove_selected_from_blacklist error: {e}")

    def _on_switch_toggled(self, checked: bool):
        self.config_mgr.set("auto_kill_enabled", checked)
        ms = self.spin_interval.value()
        if checked:
            self.lbl_switch_status.setText(f"MONITORING ACTIVE ({ms}ms)")
            self.lbl_switch_status.setStyleSheet(f"font-weight: 800; color: {COLORS['success']}; font-size: 13px;")
            self.card_status.set_value(f"ACTIVE ({ms}ms)", "Continuous task scanner")
        else:
            self.lbl_switch_status.setText("MONITORING PAUSED")
            self.lbl_switch_status.setStyleSheet(f"font-weight: 800; color: {COLORS['danger']}; font-size: 13px;")
            self.card_status.set_value("PAUSED", "Click switch to resume")
        self.toggle_active.emit(checked)

    def _on_interval_changed(self, val: int):
        self.interval_changed.emit(val)
        if self.toggle_switch.isChecked():
            self.lbl_switch_status.setText(f"MONITORING ACTIVE ({val}ms)")
            self.card_status.set_value(f"ACTIVE ({val}ms)")

    def _on_tree_toggled(self, checked: bool):
        self.config_mgr.set("kill_children", checked)
        self.blacklist_updated.emit()

    def _create_badge_widget(self, text: str, bg_color: str, fg_color: str, border_color: str) -> QWidget:
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(2, 2, 2, 2)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"""
            background-color: {bg_color};
            color: {fg_color};
            border: 1px solid {border_color};
            border-radius: 6px;
            padding: 2px 10px;
            font-size: 10px;
            font-weight: 800;
        """)
        c_layout.addWidget(lbl)
        return container

    def add_kill_log(self, name: str, pid: int, success: bool, message: str, time_str: str):
        try:
            self.log_table.setUpdatesEnabled(False)
            row = 0
            self.log_table.insertRow(row)

            time_item = QTableWidgetItem(time_str)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            time_item.setForeground(QBrush(QColor(COLORS["text_secondary"])))
            self.log_table.setItem(row, 0, time_item)

            name_item = QTableWidgetItem(f"  {name}")
            name_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            name_item.setForeground(QBrush(QColor(COLORS['text_primary'])))
            self.log_table.setItem(row, 1, name_item)

            pid_widget = self._create_badge_widget(str(pid), "#F1F5F9", "#475569", "#CBD5E1")
            self.log_table.setCellWidget(row, 2, pid_widget)

            if success:
                res_widget = self._create_badge_widget("● FORCE KILLED", "#DCFCE7", "#15803D", "#86EFAC")
            else:
                res_widget = self._create_badge_widget("✕ FAILED", "#FEE2E2", "#B91C1C", "#FCA5A5")
            self.log_table.setCellWidget(row, 3, res_widget)

            if self.log_table.rowCount() > 200:
                self.log_table.removeRow(self.log_table.rowCount() - 1)
        except Exception as e:
            print(f"[AutoKillerView] add_kill_log error: {e}")
        finally:
            self.log_table.setUpdatesEnabled(True)

    def update_stats(self, total_killed: int, scan_count: int):
        try:
            self.card_kills.set_value(f"{total_killed} Kills", "Zero CPU waste achieved")
        except Exception:
            pass

    def _clear_logs(self):
        try:
            self.log_table.setRowCount(0)
        except Exception:
            pass
