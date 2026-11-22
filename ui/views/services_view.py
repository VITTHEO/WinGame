import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame, QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont
from core.services_engine import ServicesEngine
from core.startup_engine import StartupEngine
from ui.animated_widgets import AnimatedButton
from ui.styles import COLORS

class ServiceStatCard(QFrame):
    """Modern KPI summary card for services metrics."""
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

        # Icon frame
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


class ServicesView(QWidget):
    add_to_blacklist_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cached_services = []
        self.active_filter = "third_party"  # "all", "third_party", "auto", "disabled"
        self._setup_ui()
        self.refresh_services()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(18)

        # ---------------- TOP TITLE & CONTROLS BAR ----------------
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_title = QLabel("Windows Services Killer")
        lbl_title.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {COLORS['text_primary']};")
        lbl_sub = QLabel("Inspect background services, stop telemetry daemons, and disable resource-heavy bloatware")
        lbl_sub.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']};")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        top_bar.addLayout(title_box)

        top_bar.addStretch()

        # Search field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search service name, path...")
        self.search_input.setFixedWidth(280)
        self.search_input.textChanged.connect(self._filter_table)
        top_bar.addWidget(self.search_input)

        # Refresh
        self.btn_refresh = AnimatedButton("Refresh", variant="secondary")
        self.btn_refresh.clicked.connect(self.refresh_services)
        top_bar.addWidget(self.btn_refresh)

        layout.addLayout(top_bar)

        # ---------------- 3 KPI METRIC STAT CARDS ----------------
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        # Card 1: Total Services
        self.card_total = ServiceStatCard(
            title="Total Registered Services",
            initial_val="0 Services",
            subtitle="Windows System & Drivers",
            bg_color="#E0F2FE",
            fg_color="#0284C7",
            icon_symbol="⚙"
        )
        stats_row.addWidget(self.card_total)

        # Card 2: Third-Party Services
        self.card_third_party = ServiceStatCard(
            title="Third-Party Services",
            initial_val="0 Apps",
            subtitle="Installed software & game launchers",
            bg_color="#CCFBF1",
            fg_color="#0D9488",
            icon_symbol="📦"
        )
        stats_row.addWidget(self.card_third_party)

        # Card 3: Automatic Boot Services
        self.card_auto = ServiceStatCard(
            title="Auto-Starting Services",
            initial_val="0 Auto",
            subtitle="Running on Windows startup",
            bg_color="#FFEDD5",
            fg_color="#EA580C",
            icon_symbol="⚡"
        )
        stats_row.addWidget(self.card_auto)

        layout.addLayout(stats_row)

        # ---------------- FILTER CHIPS BAR ----------------
        filter_card = QFrame()
        filter_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 4px;
            }}
        """)
        fc_layout = QHBoxLayout(filter_card)
        fc_layout.setContentsMargins(12, 8, 12, 8)
        fc_layout.setSpacing(10)

        lbl_f = QLabel("Filter:")
        lbl_f.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {COLORS['text_muted']};")
        fc_layout.addWidget(lbl_f)

        self.btn_f_third = QPushButton("📦 Third-Party Only (Recommended)")
        self.btn_f_all = QPushButton("All Services")
        self.btn_f_auto = QPushButton("⚡ Automatic Boot Only")
        self.btn_f_disabled = QPushButton("○ Disabled Only")

        self.filter_buttons = [self.btn_f_third, self.btn_f_all, self.btn_f_auto, self.btn_f_disabled]
        for b in self.filter_buttons:
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['bg_table_header']};
                    color: {COLORS['text_secondary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                    padding: 6px 14px;
                    font-weight: 600;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['bg_card_hover']};
                    color: {COLORS['text_primary']};
                }}
                QPushButton:checked {{
                    background-color: #EFF6FF;
                    border-color: {COLORS['primary']};
                    color: {COLORS['primary']};
                    font-weight: 700;
                }}
            """)

        self.btn_f_third.setChecked(True)
        self.btn_f_third.clicked.connect(lambda: self._set_filter("third_party"))
        self.btn_f_all.clicked.connect(lambda: self._set_filter("all"))
        self.btn_f_auto.clicked.connect(lambda: self._set_filter("auto"))
        self.btn_f_disabled.clicked.connect(lambda: self._set_filter("disabled"))

        for b in self.filter_buttons:
            fc_layout.addWidget(b)
        fc_layout.addStretch()

        self.lbl_count = QLabel("0 services listed")
        self.lbl_count.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; font-weight: 600;")
        fc_layout.addWidget(self.lbl_count)

        layout.addWidget(filter_card)

        # ---------------- SERVICES TABLE ----------------
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Service ID", "Display Name", "Startup Mode", "Origin", "Executable Image Path"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 8px 12px;
                border-bottom: 1px solid {COLORS['border']};
            }}
            QTableWidget::item:selected {{
                background-color: #EFF6FF;
                color: #1D4ED8;
            }}
        """)
        layout.addWidget(self.table)

        # ---------------- BOTTOM ACTIONS BAR ----------------
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        lbl_b_hint = QLabel("💡 Select a service to take action:")
        lbl_b_hint.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; font-weight: 600;")
        bottom_bar.addWidget(lbl_b_hint)
        bottom_bar.addStretch()

        self.btn_stop = AnimatedButton("🛑 Stop Service", variant="danger")
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        bottom_bar.addWidget(self.btn_stop)

        self.btn_disable = AnimatedButton("⚙ Disable Service", variant="primary")
        self.btn_disable.clicked.connect(self._on_disable_clicked)
        bottom_bar.addWidget(self.btn_disable)

        self.btn_open_loc = AnimatedButton("📂 Open File Location", variant="secondary")
        self.btn_open_loc.clicked.connect(self._on_open_loc_clicked)
        bottom_bar.addWidget(self.btn_open_loc)

        self.btn_autokill = AnimatedButton("⚡ Add Binary to Auto-Kill", variant="secondary")
        self.btn_autokill.clicked.connect(self._on_autokill_clicked)
        bottom_bar.addWidget(self.btn_autokill)

        layout.addLayout(bottom_bar)

    def _set_filter(self, filter_mode: str):
        self.active_filter = filter_mode
        self.btn_f_third.setChecked(filter_mode == "third_party")
        self.btn_f_all.setChecked(filter_mode == "all")
        self.btn_f_auto.setChecked(filter_mode == "auto")
        self.btn_f_disabled.setChecked(filter_mode == "disabled")
        self._filter_table()

    def refresh_services(self):
        self.cached_services = ServicesEngine.get_all_services(filter_startup_only=False)
        self._update_kpi_cards()
        self._filter_table()

    def _update_kpi_cards(self):
        total = len(self.cached_services)
        third_party = sum(1 for s in self.cached_services if s.get("is_third_party", False))
        auto_count = sum(1 for s in self.cached_services if s.get("start_type_code") == 2)

        self.card_total.set_value(f"{total} Services", "Windows Core & Applications")
        self.card_third_party.set_value(f"{third_party} Third-Party", "Safe candidates for tuning")
        self.card_auto.set_value(f"{auto_count} Auto", "Launches on Windows boot")

    def _create_badge_widget(self, text: str, bg_color: str, fg_color: str, border_color: str) -> QWidget:
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(4, 4, 4, 4)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"""
            background-color: {bg_color};
            color: {fg_color};
            border: 1px solid {border_color};
            border-radius: 8px;
            padding: 4px 12px;
            font-size: 11px;
            font-weight: 700;
        """)
        c_layout.addWidget(lbl)
        return container

    def _filter_table(self):
        filter_text = self.search_input.text().lower().strip()

        filtered = []
        for s in self.cached_services:
            if self.active_filter == "third_party" and not s.get("is_third_party", False):
                continue
            elif self.active_filter == "auto" and s.get("start_type_code") != 2:
                continue
            elif self.active_filter == "disabled" and s.get("start_type_code") != 4:
                continue

            if filter_text:
                if (filter_text not in s["name"].lower() and
                    filter_text not in s["display_name"].lower() and
                    filter_text not in s["image_path"].lower()):
                    continue

            filtered.append(s)

        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(filtered))

        for row, s in enumerate(filtered):
            # 0. Service ID
            name_item = QTableWidgetItem(f"  {s['name']}")
            name_item.setData(Qt.ItemDataRole.UserRole, s)
            name_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            name_item.setForeground(QBrush(QColor(COLORS['text_primary'])))
            self.table.setItem(row, 0, name_item)

            # 1. Display Name
            disp_item = QTableWidgetItem(s["display_name"])
            disp_item.setForeground(QBrush(QColor(COLORS["text_secondary"])))
            self.table.setItem(row, 1, disp_item)

            # 2. Startup Mode Badge
            mode_code = s.get("start_type_code", 3)
            mode_name = s.get("start_type_name", "Unknown")
            if mode_code == 2:
                mode_widget = self._create_badge_widget(mode_name, "#DCFCE7", "#15803D", "#86EFAC")
            elif mode_code == 4:
                mode_widget = self._create_badge_widget(mode_name, "#FEE2E2", "#B91C1C", "#FCA5A5")
            elif mode_code == 3:
                mode_widget = self._create_badge_widget(mode_name, "#E0F2FE", "#0369A1", "#BAE6FD")
            else:
                mode_widget = self._create_badge_widget(mode_name, "#F1F5F9", "#64748B", "#CBD5E1")
            self.table.setCellWidget(row, 2, mode_widget)

            # 3. Origin Badge
            is_tp = s.get("is_third_party", False)
            if is_tp:
                origin_widget = self._create_badge_widget("Third-Party App", "#CCFBF1", "#0F766E", "#99F6E4")
            else:
                origin_widget = self._create_badge_widget("Windows Core", "#F1F5F9", "#64748B", "#CBD5E1")
            self.table.setCellWidget(row, 3, origin_widget)

            # 4. Executable Path
            path_item = QTableWidgetItem(s["image_path"])
            path_item.setToolTip(s["image_path"])
            path_item.setForeground(QBrush(QColor(COLORS["text_muted"])))
            self.table.setItem(row, 4, path_item)

        self.table.setUpdatesEnabled(True)
        self.lbl_count.setText(f"Showing {len(filtered)} of {len(self.cached_services)} services")

    def _get_selected_service(self):
        indexes = self.table.selectionModel().selectedRows()
        if indexes:
            row = indexes[0].row()
            item = self.table.item(row, 0)
            if item:
                return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _on_stop_clicked(self):
        svc = self._get_selected_service()
        if not svc:
            QMessageBox.warning(self, "Selection Required", "Please select a service from the table.")
            return

        name = svc.get("name", "")
        ok, msg = ServicesEngine.stop_service(name)
        if ok:
            QMessageBox.information(self, "Service Stopped", f"Service '{name}' has been stopped.")
            self.refresh_services()
        else:
            QMessageBox.warning(self, "Notice", f"{msg}\n\nTip: Administrator rights required to stop Windows services.")

    def _on_disable_clicked(self):
        svc = self._get_selected_service()
        if not svc:
            QMessageBox.warning(self, "Selection Required", "Please select a service from the table.")
            return

        name = svc.get("name", "")
        ok, msg = ServicesEngine.set_service_start_type(name, mode="disabled")
        if ok:
            QMessageBox.information(self, "Service Disabled", f"Service '{name}' has been disabled.")
            self.refresh_services()
        else:
            QMessageBox.warning(self, "Notice", f"{msg}\n\nTip: Administrator rights required to disable services.")

    def _on_open_loc_clicked(self):
        svc = self._get_selected_service()
        if not svc:
            QMessageBox.warning(self, "Selection Required", "Please select a service from the table.")
            return

        path = svc.get("image_path", "")
        ok, msg = StartupEngine.open_file_location(path)
        if not ok:
            QMessageBox.warning(self, "Path Notice", msg)

    def _on_autokill_clicked(self):
        svc = self._get_selected_service()
        if not svc:
            QMessageBox.warning(self, "Selection Required", "Please select a service from the table.")
            return

        path = svc.get("image_path", "")
        exe = os.path.basename(path) if path.lower().endswith(".exe") else f"{svc['name']}.exe"
        if exe.lower() == "svchost.exe":
            QMessageBox.warning(self, "Protected", "Cannot auto-kill svchost.exe directly as it hosts multiple core Windows services.")
            return

        self.add_to_blacklist_requested.emit(exe)
        QMessageBox.information(self, "Queued to Auto-Killer", f"'{exe}' has been added to the continuous Auto-Killer loop.")
