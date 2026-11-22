import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QFrame, QMessageBox, QPushButton, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont
from core.startup_engine import StartupEngine
from core.services_engine import ServicesEngine
from ui.animated_widgets import AnimatedButton
from ui.styles import COLORS

class StartupStatCard(QFrame):
    """Modern KPI summary card for startup metrics."""
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


class StartupView(QWidget):
    add_to_blacklist_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cached_apps = []
        self.cached_services = []
        self.active_filter = "all"  # "all", "enabled", "disabled"
        self._setup_ui()
        self.refresh_all()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(18)

        # ---------------- TOP TITLE & ACTIONS BAR ----------------
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_title = QLabel("Startup Manager")
        lbl_title.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {COLORS['text_primary']};")
        lbl_sub = QLabel("Manage background startup applications and boot services to maximize boot speed and free RAM")
        lbl_sub.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']};")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        top_bar.addLayout(title_box)

        top_bar.addStretch()

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search startup apps or services...")
        self.search_input.setFixedWidth(280)
        self.search_input.textChanged.connect(self._filter_current_tab)
        top_bar.addWidget(self.search_input)

        # Refresh Button
        self.btn_refresh = AnimatedButton("Refresh", variant="secondary")
        self.btn_refresh.clicked.connect(self.refresh_all)
        top_bar.addWidget(self.btn_refresh)

        layout.addLayout(top_bar)

        # ---------------- 3 KPI METRIC STAT CARDS ----------------
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        # Card 1: Total Apps
        self.card_total = StartupStatCard(
            title="Total Applications",
            initial_val="0 Apps",
            subtitle="Discovered in Registry & Folders",
            bg_color="#E0F2FE",
            fg_color="#0284C7",
            icon_symbol="🚀"
        )
        stats_row.addWidget(self.card_total)

        # Card 2: Enabled at Boot
        self.card_enabled = StartupStatCard(
            title="Enabled at Boot",
            initial_val="0 Active",
            subtitle="Launches automatically at Windows boot",
            bg_color="#DCFCE7",
            fg_color="#16A34A",
            icon_symbol="⚡"
        )
        stats_row.addWidget(self.card_enabled)

        # Card 3: Disabled / Optimized
        self.card_disabled = StartupStatCard(
            title="Optimized / Blocked",
            initial_val="0 Disabled",
            subtitle="Boot time saved & background RAM freed",
            bg_color="#F3E8FF",
            fg_color="#9333EA",
            icon_symbol="🛡"
        )
        stats_row.addWidget(self.card_disabled)

        layout.addLayout(stats_row)

        # ---------------- TABS: APPLICATIONS vs SERVICES ----------------
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {COLORS['border']};
                background-color: {COLORS['bg_card']};
                border-radius: 14px;
                top: -1px;
            }}
            QTabBar::tab {{
                background-color: {COLORS['bg_card_hover']};
                color: {COLORS['text_secondary']};
                padding: 10px 24px;
                margin-right: 6px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                font-weight: 700;
                font-size: 13px;
            }}
            QTabBar::tab:hover {{
                color: {COLORS['text_primary']};
                background-color: #E2E8F0;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['primary']};
                color: #FFFFFF;
            }}
        """)
        self.tabs.currentChanged.connect(self._filter_current_tab)

        # ==============================================================
        # TAB 1: Startup Applications
        # ==============================================================
        tab_apps = QWidget()
        t1_layout = QVBoxLayout(tab_apps)
        t1_layout.setContentsMargins(18, 16, 18, 16)
        t1_layout.setSpacing(14)

        # Segmented Filter Bar for Apps
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        lbl_filter = QLabel("Filter:")
        lbl_filter.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {COLORS['text_muted']};")
        filter_row.addWidget(lbl_filter)

        self.btn_f_all = QPushButton("All Applications")
        self.btn_f_enabled = QPushButton("● Enabled Only")
        self.btn_f_disabled = QPushButton("○ Disabled Only")

        self.filter_buttons = [self.btn_f_all, self.btn_f_enabled, self.btn_f_disabled]
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
        self.btn_f_all.setChecked(True)
        self.btn_f_all.clicked.connect(lambda: self._set_app_filter("all"))
        self.btn_f_enabled.clicked.connect(lambda: self._set_app_filter("enabled"))
        self.btn_f_disabled.clicked.connect(lambda: self._set_app_filter("disabled"))

        for b in self.filter_buttons:
            filter_row.addWidget(b)
        filter_row.addStretch()

        self.lbl_apps_count = QLabel("0 apps displayed")
        self.lbl_apps_count.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        filter_row.addWidget(self.lbl_apps_count)
        t1_layout.addLayout(filter_row)

        # Apps Table
        self.table_apps = QTableWidget()
        self.table_apps.setColumnCount(4)
        self.table_apps.setHorizontalHeaderLabels([
            "Application Name", "Registry / Startup Location", "Executable Path", "Startup Status"
        ])
        h1 = self.table_apps.horizontalHeader()
        h1.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h1.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h1.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        h1.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_apps.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_apps.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_apps.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_apps.verticalHeader().setVisible(False)
        self.table_apps.verticalHeader().setDefaultSectionSize(44)
        self.table_apps.setShowGrid(False)
        self.table_apps.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
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
        t1_layout.addWidget(self.table_apps)

        # Bottom Actions for Apps
        act_row1 = QHBoxLayout()
        act_row1.setSpacing(10)

        lbl_hint = QLabel("💡 Select an item to manage:")
        lbl_hint.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; font-weight: 600;")
        act_row1.addWidget(lbl_hint)
        act_row1.addStretch()

        self.btn_toggle_app = AnimatedButton("🔄 Enable / Disable", variant="primary")
        self.btn_toggle_app.clicked.connect(self._on_toggle_app_clicked)
        act_row1.addWidget(self.btn_toggle_app)

        self.btn_open_app = AnimatedButton("📂 Open File Location", variant="secondary")
        self.btn_open_app.clicked.connect(self._on_open_app_clicked)
        act_row1.addWidget(self.btn_open_app)

        self.btn_kill_app = AnimatedButton("⚡ Add to Auto-Kill", variant="danger")
        self.btn_kill_app.clicked.connect(self._on_add_app_to_autokill)
        act_row1.addWidget(self.btn_kill_app)

        t1_layout.addLayout(act_row1)
        self.tabs.addTab(tab_apps, "🚀 Startup Applications")

        # ==============================================================
        # TAB 2: Startup Services
        # ==============================================================
        tab_svcs = QWidget()
        t2_layout = QVBoxLayout(tab_svcs)
        t2_layout.setContentsMargins(18, 16, 18, 16)
        t2_layout.setSpacing(14)

        # Services Header Info
        s_top = QHBoxLayout()
        self.lbl_svcs_count = QLabel("0 automatic boot services")
        self.lbl_svcs_count.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 600; font-size: 12px;")
        s_top.addWidget(self.lbl_svcs_count)
        s_top.addStretch()
        t2_layout.addLayout(s_top)

        # Services Table
        self.table_svcs = QTableWidget()
        self.table_svcs.setColumnCount(4)
        self.table_svcs.setHorizontalHeaderLabels([
            "Service Name", "Display Name", "Executable Image Path", "Startup Mode"
        ])
        h2 = self.table_svcs.horizontalHeader()
        h2.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h2.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h2.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        h2.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_svcs.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_svcs.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_svcs.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_svcs.verticalHeader().setVisible(False)
        self.table_svcs.verticalHeader().setDefaultSectionSize(44)
        self.table_svcs.setShowGrid(False)
        self.table_svcs.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
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
        t2_layout.addWidget(self.table_svcs)

        # Bottom Actions for Services
        act_row2 = QHBoxLayout()
        act_row2.setSpacing(10)

        lbl_s_hint = QLabel("💡 Manage background Windows services:")
        lbl_s_hint.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; font-weight: 600;")
        act_row2.addWidget(lbl_s_hint)
        act_row2.addStretch()

        self.btn_disable_svc = AnimatedButton("⚙ Disable at Startup", variant="primary")
        self.btn_disable_svc.clicked.connect(self._on_disable_service_clicked)
        act_row2.addWidget(self.btn_disable_svc)

        self.btn_stop_svc = AnimatedButton("🛑 Stop Service", variant="danger")
        self.btn_stop_svc.clicked.connect(self._on_stop_service_clicked)
        act_row2.addWidget(self.btn_stop_svc)

        self.btn_open_svc = AnimatedButton("📂 Open Location", variant="secondary")
        self.btn_open_svc.clicked.connect(self._on_open_svc_clicked)
        act_row2.addWidget(self.btn_open_svc)

        t2_layout.addLayout(act_row2)
        self.tabs.addTab(tab_svcs, "⚙ Startup Services")

        layout.addWidget(self.tabs)

    def _set_app_filter(self, filter_mode: str):
        self.active_filter = filter_mode
        self.btn_f_all.setChecked(filter_mode == "all")
        self.btn_f_enabled.setChecked(filter_mode == "enabled")
        self.btn_f_disabled.setChecked(filter_mode == "disabled")
        self._populate_apps(self.cached_apps)

    def refresh_all(self):
        self.cached_apps = StartupEngine.get_startup_apps()
        self.cached_services = ServicesEngine.get_all_services(filter_startup_only=True)
        self._update_kpi_cards()
        self._populate_apps(self.cached_apps)
        self._populate_services(self.cached_services)

    def _update_kpi_cards(self):
        total = len(self.cached_apps)
        enabled = sum(1 for a in self.cached_apps if a.get("enabled", False))
        disabled = total - enabled

        self.card_total.set_value(f"{total} Apps", f"{len(self.cached_services)} Boot Services")
        self.card_enabled.set_value(f"{enabled} Active", "Consuming boot velocity")
        self.card_disabled.set_value(f"{disabled} Blocked", "Boot time & RAM preserved")

    def _create_badge_widget(self, text: str, bg_color: str, fg_color: str, border_color: str) -> QWidget:
        """Helper to create a colorful pill badge inside a centered container widget."""
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

    def _populate_apps(self, apps):
        filter_text = self.search_input.text().lower().strip()
        
        filtered = []
        for a in apps:
            if self.active_filter == "enabled" and not a.get("enabled", False):
                continue
            if self.active_filter == "disabled" and a.get("enabled", False):
                continue
            if filter_text:
                in_name = filter_text in a["name"].lower()
                in_path = filter_text in a.get("path", "").lower()
                in_loc = filter_text in a.get("location", "").lower()
                if not (in_name or in_path or in_loc):
                    continue
            filtered.append(a)

        self.table_apps.setUpdatesEnabled(False)
        self.table_apps.setRowCount(len(filtered))

        for row, a in enumerate(filtered):
            # 0. App Name
            app_name = a["name"]
            # Clean up display name
            display_name = app_name
            if display_name.lower().endswith(".lnk"):
                display_name = display_name[:-4]
            name_item = QTableWidgetItem(f"  {display_name}")
            name_item.setData(Qt.ItemDataRole.UserRole, a)
            name_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            name_item.setForeground(QBrush(QColor(COLORS['text_primary'])))
            self.table_apps.setItem(row, 0, name_item)

            # 1. Location Pill Badge
            loc = a.get("location", "Registry")
            if "HKCU" in loc or "User" in loc:
                loc_widget = self._create_badge_widget(loc, "#E0F2FE", "#0369A1", "#BAE6FD")
            elif "HKLM" in loc or "System" in loc:
                loc_widget = self._create_badge_widget(loc, "#EDE9FE", "#6D28D9", "#DDD6FE")
            elif "Folder" in loc:
                loc_widget = self._create_badge_widget(loc, "#FEF3C7", "#B45309", "#FDE68A")
            else:
                loc_widget = self._create_badge_widget(loc, "#F1F5F9", "#475569", "#CBD5E1")
            self.table_apps.setCellWidget(row, 1, loc_widget)

            # 2. Executable Path
            path_str = a.get("path") or a.get("command") or "(Managed by Windows)"
            path_item = QTableWidgetItem(path_str)
            path_item.setToolTip(path_str)
            path_item.setForeground(QBrush(QColor(COLORS["text_secondary"])))
            self.table_apps.setItem(row, 2, path_item)

            # 3. Status Pill Badge
            is_enabled = a.get("enabled", False)
            if is_enabled:
                status_widget = self._create_badge_widget("● ENABLED", "#DCFCE7", "#15803D", "#86EFAC")
            else:
                status_widget = self._create_badge_widget("○ DISABLED", "#FEE2E2", "#B91C1C", "#FCA5A5")
            self.table_apps.setCellWidget(row, 3, status_widget)

        self.table_apps.setUpdatesEnabled(True)
        enabled_total = sum(1 for a in apps if a.get("enabled", False))
        self.lbl_apps_count.setText(f"Showing {len(filtered)} of {len(apps)} apps ({enabled_total} active)")

    def _populate_services(self, services):
        filter_text = self.search_input.text().lower().strip()
        filtered = [
            s for s in services
            if not filter_text or (
                filter_text in s["name"].lower() or
                filter_text in s["display_name"].lower() or
                filter_text in s["image_path"].lower()
            )
        ]

        self.table_svcs.setUpdatesEnabled(False)
        self.table_svcs.setRowCount(len(filtered))

        for row, s in enumerate(filtered):
            name_item = QTableWidgetItem(f"  {s['name']}")
            name_item.setData(Qt.ItemDataRole.UserRole, s)
            name_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            name_item.setForeground(QBrush(QColor(COLORS['text_primary'])))
            self.table_svcs.setItem(row, 0, name_item)

            disp_item = QTableWidgetItem(s["display_name"])
            disp_item.setForeground(QBrush(QColor(COLORS["text_secondary"])))
            self.table_svcs.setItem(row, 1, disp_item)

            path_item = QTableWidgetItem(s["image_path"])
            path_item.setToolTip(s["image_path"])
            path_item.setForeground(QBrush(QColor(COLORS["text_muted"])))
            self.table_svcs.setItem(row, 2, path_item)

            # Startup Mode Badge
            mode_name = s.get("start_type_name", "Unknown")
            if "Auto" in mode_name:
                mode_widget = self._create_badge_widget(mode_name, "#DCFCE7", "#15803D", "#86EFAC")
            elif "Manual" in mode_name:
                mode_widget = self._create_badge_widget(mode_name, "#E0F2FE", "#0369A1", "#BAE6FD")
            elif "Disabled" in mode_name:
                mode_widget = self._create_badge_widget(mode_name, "#F1F5F9", "#64748B", "#CBD5E1")
            else:
                mode_widget = self._create_badge_widget(mode_name, "#FEF3C7", "#B45309", "#FDE68A")
            self.table_svcs.setCellWidget(row, 3, mode_widget)

        self.table_svcs.setUpdatesEnabled(True)
        self.lbl_svcs_count.setText(f"Showing {len(filtered)} of {len(services)} automatic boot services")

    def _filter_current_tab(self):
        if self.tabs.currentIndex() == 0:
            self._populate_apps(self.cached_apps)
        else:
            self._populate_services(self.cached_services)

    def _get_selected_app(self):
        row = self.table_apps.currentRow()
        if row < 0:
            return None
        item = self.table_apps.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _get_selected_service(self):
        row = self.table_svcs.currentRow()
        if row < 0:
            return None
        item = self.table_svcs.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_toggle_app_clicked(self):
        app = self._get_selected_app()
        if not app:
            QMessageBox.information(self, "No Selection", "Please select a startup application from the table.")
            return

        success, msg = StartupEngine.toggle_startup_state(app)
        if success:
            self.refresh_all()
        else:
            QMessageBox.warning(self, "Permission Notice", f"{msg}\n\nRunning WinGame as Administrator may be required for system-wide keys.")

    def _on_open_app_clicked(self):
        app = self._get_selected_app()
        if not app:
            QMessageBox.information(self, "No Selection", "Please select a startup application first.")
            return

        path = app.get("path") or app.get("command") or ""
        success, msg = StartupEngine.open_file_location(path)
        if not success:
            QMessageBox.warning(self, "Location Unavailable", msg)

    def _on_add_app_to_autokill(self):
        app = self._get_selected_app()
        if not app:
            QMessageBox.information(self, "No Selection", "Please select a startup application first.")
            return

        name = app.get("name", "")
        path = app.get("path", "")
        target = os.path.basename(path) if (path and path.lower().endswith(".exe")) else f"{name}.exe"
        self.add_to_blacklist_requested.emit(target)
        QMessageBox.information(self, "Added to Auto-Killer", f"'{target}' was queued into the 250ms Auto-Killer blacklist.")

    def _on_disable_service_clicked(self):
        svc = self._get_selected_service()
        if not svc:
            QMessageBox.information(self, "No Selection", "Please select a service from the table.")
            return

        name = svc.get("name", "")
        reply = QMessageBox.question(
            self, "Confirm Disable Service",
            f"Are you sure you want to disable startup for service '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = ServicesEngine.disable_service(name)
            if success:
                QMessageBox.information(self, "Service Disabled", msg)
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Notice", f"{msg}\n\nMake sure WinGame is running with Administrator privileges.")

    def _on_stop_service_clicked(self):
        svc = self._get_selected_service()
        if not svc:
            QMessageBox.information(self, "No Selection", "Please select a service from the table.")
            return

        name = svc.get("name", "")
        success, msg = ServicesEngine.stop_service(name)
        if success:
            QMessageBox.information(self, "Service Stopped", msg)
            self.refresh_all()
        else:
            QMessageBox.warning(self, "Notice", f"{msg}\n\nMake sure WinGame is running with Administrator privileges.")

    def _on_open_svc_clicked(self):
        svc = self._get_selected_service()
        if not svc:
            QMessageBox.information(self, "No Selection", "Please select a service first.")
            return

        path = svc.get("image_path", "")
        success, msg = StartupEngine.open_file_location(path)
        if not success:
            QMessageBox.warning(self, "Location Unavailable", msg)
