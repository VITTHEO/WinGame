import os
import ctypes
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QLabel, QPushButton, QFrame, QMessageBox,
    QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap, QPainter, QBrush, QPen, QAction, QPainterPath
from config import ConfigManager
from core.process_engine import ProcessEngine
from core.auto_killer import AutoKillerWorker
from core.optimizer import AutoRamCleanerWorker, SystemOptimizer
from core.game_engine import GameWatcherThread
from core.hotkey_engine import GlobalHotkeyManager
from core.update_engine import UpdateCheckerThread
from ui.animated_widgets import AnimatedButton
from ui.views.hardware_home_view import HardwareHomeView
from ui.views.game_booster_view import GameBoosterView
from ui.views.tweaks_view import TweaksView
from ui.views.startup_view import StartupView
from ui.views.services_view import ServicesView
from ui.views.auto_killer_view import AutoKillerView
from ui.views.optimizer_view import OptimizerView
from ui.views.settings_view import SettingsView
from ui.styles import COLORS, MAIN_STYLESHEET, apply_theme, get_stylesheet

class SidebarButton(QPushButton):
    """
    Exact replica of Sparkle's sleek sidebar item.
    """
    def __init__(self, text: str, icon_symbol: str, parent=None):
        super().__init__(parent)
        self.setText(f"  {icon_symbol}   {text}")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(42)
        self.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                border: none;
                border-radius: 10px;
                text-align: left;
                padding-left: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLORS['bg_card_hover']};
                color: {COLORS['text_primary']};
            }}
            QPushButton:checked {{
                background-color: {COLORS['primary_light']};
                color: {COLORS['primary']};
                font-weight: 700;
            }}
        """)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WinGame")
        self.resize(1280, 840)
        self.setMinimumSize(1080, 720)

        # Config & flags
        self.config_mgr = ConfigManager()
        self._is_exiting_completely = False
        self._tray_notified_once = False

        # Apply global Sparkle clean styling & window icon
        self.setStyleSheet(MAIN_STYLESHEET)
        self.setWindowIcon(self._create_tray_icon())

        # Initialize Background Workers
        self.auto_killer_worker = AutoKillerWorker()
        self.auto_ram_worker = AutoRamCleanerWorker()
        self.game_watcher = GameWatcherThread(auto_killer_ref=self.auto_killer_worker)

        # Setup System Tray & Global Hotkeys
        self._setup_tray_icon()
        self._setup_global_hotkeys()

        # Build UI
        self._setup_ui()
        self._connect_signals()

        # Start Workers
        self.auto_killer_worker.start()
        self.auto_ram_worker.start()
        self.game_watcher.start()

        # Initial Status & Native DWM Title Bar Theming
        self._on_worker_status_changed(self.auto_killer_worker.is_active())
        self._apply_dwm_titlebar()

        # Silent background update check (3s after launch)
        self._startup_update_thread = None
        if self.config_mgr.get("auto_check_updates", True):
            QTimer.singleShot(3000, self._run_silent_update_check)

    def _run_silent_update_check(self):
        self._startup_update_thread = UpdateCheckerThread(parent=self)
        self._startup_update_thread.check_finished.connect(self._on_silent_update_result)
        self._startup_update_thread.start()

    def _on_silent_update_result(self, info: dict):
        if info.get("status") == "update_available":
            if hasattr(self, "view_set"):
                self.view_set._on_update_check_done(info)
            if self.config_mgr.get("show_notifications", True) and hasattr(self, "tray_icon") and self.tray_icon.isVisible():
                self.tray_icon.showMessage(
                    "WinGame Update Available!",
                    f"Version {info.get('latest_version')} is out! Open Settings -> Updates to install.",
                    QSystemTrayIcon.MessageIcon.Information,
                    4000
                )

    @staticmethod
    def _hex_to_colorref(hex_str: str) -> int:
        h = hex_str.lstrip("#")
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        return (b << 16) | (g << 8) | r

    def _apply_dwm_titlebar(self):
        """Styles the native Windows 10/11 titlebar to match the active WinGame theme."""
        try:
            hwnd = int(self.winId())
            dwmapi = ctypes.windll.dwmapi
            is_dark = ctypes.c_int(1 if COLORS.get("is_dark", False) else 0)
            # DWMWA_USE_IMMERSIVE_DARK_MODE (20 on Win11 / 20H1+, 19 on older Win10)
            dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(is_dark), ctypes.sizeof(is_dark))
            dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(is_dark), ctypes.sizeof(is_dark))

            # DWMWA_CAPTION_COLOR (35), DWMWA_TEXT_COLOR (36), DWMWA_BORDER_COLOR (34) (Win11)
            caption_col = ctypes.c_uint32(self._hex_to_colorref(COLORS["bg_main"]))
            text_col = ctypes.c_uint32(self._hex_to_colorref(COLORS["text_primary"]))
            border_col = ctypes.c_uint32(self._hex_to_colorref(COLORS["border"]))
            dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption_col), ctypes.sizeof(caption_col))
            dwmapi.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(text_col), ctypes.sizeof(text_col))
            dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border_col), ctypes.sizeof(border_col))
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_dwm_titlebar()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ----------------- SIDEBAR (SPARKLE STYLE) -----------------
        sidebar = QFrame()
        sidebar.setObjectName("SidebarFrame")
        sidebar.setFixedWidth(230)
        sidebar.setStyleSheet(f"""
            QFrame#SidebarFrame {{
                background-color: {COLORS['bg_main']};
                border-right: 1px solid {COLORS['border']};
            }}
        """)
        s_layout = QVBoxLayout(sidebar)
        s_layout.setContentsMargins(16, 20, 16, 20)
        s_layout.setSpacing(6)

        # WinGame Logo + Beta Pill
        logo_box = QHBoxLayout()
        logo_box.setSpacing(8)

        logo_pm = self._load_logo_pixmap(30)
        if not logo_pm.isNull():
            lbl_logo_img = QLabel()
            lbl_logo_img.setFixedSize(30, 30)
            lbl_logo_img.setPixmap(logo_pm)
            logo_box.addWidget(lbl_logo_img)
        else:
            lbl_sparkle_icon = QLabel("✦")
            lbl_sparkle_icon.setStyleSheet(f"font-size: 20px; color: {COLORS['primary']}; font-weight: bold;")
            logo_box.addWidget(lbl_sparkle_icon)

        lbl_app = QLabel("WinGame")
        lbl_app.setStyleSheet(f"font-size: 19px; font-weight: 800; color: {COLORS['text_primary']};")
        logo_box.addWidget(lbl_app)

        lbl_beta = QLabel("Beta")
        lbl_beta.setStyleSheet(f"""
            background-color: {COLORS['bg_card']};
            color: {COLORS['text_secondary']};
            border: 1px solid {COLORS['border']};
            border-radius: 10px;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: 700;
        """)
        logo_box.addWidget(lbl_beta)
        logo_box.addStretch()
        s_layout.addLayout(logo_box)
        s_layout.addSpacing(18)

        # Navigation Buttons (Exact Sparkle Layout)
        self.nav_dash = SidebarButton("Dashboard", "⊞")
        self.nav_game = SidebarButton("Game Booster", "🎮")
        self.nav_tweaks = SidebarButton("Tweaks", "⚡")
        self.nav_start = SidebarButton("Startup", "🚀")
        self.nav_svcs = SidebarButton("Services", "⚙")
        self.nav_auto = SidebarButton("Auto-Killer", "🎯")
        self.nav_clean = SidebarButton("Cleaner", "🧹")
        self.nav_set = SidebarButton("Settings", "⚙")

        self.nav_buttons = [
            self.nav_dash, self.nav_game, self.nav_tweaks, self.nav_start,
            self.nav_svcs, self.nav_auto, self.nav_clean, self.nav_set
        ]
        for btn in self.nav_buttons:
            s_layout.addWidget(btn)

        self.nav_dash.setChecked(True)
        self.nav_dash.clicked.connect(lambda: self._switch_page(0))
        self.nav_game.clicked.connect(lambda: self._switch_page(1))
        self.nav_tweaks.clicked.connect(lambda: self._switch_page(2))
        self.nav_start.clicked.connect(lambda: self._switch_page(3))
        self.nav_svcs.clicked.connect(lambda: self._switch_page(4))
        self.nav_auto.clicked.connect(lambda: self._switch_page(5))
        self.nav_clean.clicked.connect(lambda: self._switch_page(6))
        self.nav_set.clicked.connect(lambda: self._switch_page(7))

        s_layout.addStretch()

        # Sidebar Footer: Auto-Kill Live Badge & Version
        status_box = QFrame()
        status_box.setObjectName("SidebarStatusBox")
        status_box.setStyleSheet(f"""
            QFrame#SidebarStatusBox {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                padding: 10px;
            }}
        """)
        sb_layout = QVBoxLayout(status_box)
        sb_layout.setSpacing(4)
        
        lbl_sb_title = QLabel("AUTO-KILL LOOP")
        lbl_sb_title.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {COLORS['text_muted']};")
        self.lbl_sidebar_status = QLabel("○ PAUSED")
        self.lbl_sidebar_status.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLORS['danger']};")
        
        sb_layout.addWidget(lbl_sb_title)
        sb_layout.addWidget(self.lbl_sidebar_status)
        s_layout.addWidget(status_box)

        main_layout.addWidget(sidebar)

        # ----------------- RIGHT CONTENT AREA -----------------
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Pages Stack
        self.pages_stack = QStackedWidget()
        
        self.view_hard = HardwareHomeView()
        self.view_game = GameBoosterView()
        self.view_tweaks = TweaksView()
        self.view_start = StartupView()
        self.view_svcs = ServicesView()
        self.view_auto = AutoKillerView()
        self.view_opt = OptimizerView()
        self.view_set = SettingsView()

        self.pages_stack.addWidget(self.view_hard)
        self.pages_stack.addWidget(self.view_game)
        self.pages_stack.addWidget(self.view_tweaks)
        self.pages_stack.addWidget(self.view_start)
        self.pages_stack.addWidget(self.view_svcs)
        self.pages_stack.addWidget(self.view_auto)
        self.pages_stack.addWidget(self.view_opt)
        self.pages_stack.addWidget(self.view_set)

        content_layout.addWidget(self.pages_stack)
        main_layout.addWidget(content_container)

    def _connect_signals(self):
        # Hardware Home Shortcuts
        self.view_hard.navigate_to_page.connect(self._switch_page)

        # Game Booster Signals
        self.game_watcher.game_boost_applied.connect(self.view_game.set_active_boost_status)
        self.game_watcher.game_closed.connect(self.view_game.set_game_closed_status)

        # Startup & Services to Auto-Kill integration
        self.view_start.add_to_blacklist_requested.connect(self._on_add_to_blacklist_requested)
        self.view_svcs.add_to_blacklist_requested.connect(self._on_add_to_blacklist_requested)

        # AutoKillerWorker signals
        self.auto_killer_worker.process_killed.connect(self.view_auto.add_kill_log)
        self.auto_killer_worker.stats_updated.connect(self.view_auto.update_stats)
        self.auto_killer_worker.status_changed.connect(self._on_worker_status_changed)

        # AutoKillerView controls
        self.view_auto.blacklist_updated.connect(self.auto_killer_worker.reload_blacklist)
        self.view_auto.interval_changed.connect(self.auto_killer_worker.set_interval)
        self.view_auto.toggle_active.connect(self.auto_killer_worker.set_active)

        # Optimizer Automation signals
        self.auto_ram_worker.ram_auto_cleaned.connect(self.view_opt.on_ram_auto_cleaned)

        # Settings saved & live theme switch
        self.view_tweaks.tweaks_updated.connect(self.view_hard.refresh_tweaks_summary)
        self.view_set.settings_saved.connect(self._on_settings_saved)
        self.view_set.theme_changed.connect(self._on_theme_changed)

    def _switch_page(self, index: int):
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        self.pages_stack.setCurrentIndex(index)
        
        if index == 0:
            self.view_hard.update_telemetry()
        elif index == 1:
            self.view_game.refresh_games()
        elif index == 2:
            self.view_tweaks.refresh_states()
        elif index == 3:
            self.view_start.refresh_all()
        elif index == 4:
            self.view_svcs.refresh_services()

    def _on_add_to_blacklist_requested(self, proc_name: str):
        ok, msg = self.view_auto.add_target(proc_name)
        if ok:
            self.auto_killer_worker.reload_blacklist()
            QMessageBox.information(
                self,
                "Target Added",
                f"'{proc_name}' has been added to the Auto-Kill Blacklist.\n\nWhenever the Auto-Killer switch is toggled ON, it will be terminated every {self.auto_killer_worker.interval_ms} ms."
            )
        else:
            QMessageBox.warning(self, "Notice", msg)

    @staticmethod
    def _load_logo_pixmap(size: int = 64) -> QPixmap:
        import sys as _sys
        candidates = []
        if getattr(_sys, "frozen", False):
            meipass = getattr(_sys, "_MEIPASS", "")
            exe_dir = os.path.dirname(_sys.executable)
            candidates.extend([
                os.path.join(meipass, "docs", "screenshots", "Wingame-logo.png"),
                os.path.join(exe_dir, "docs", "screenshots", "Wingame-logo.png"),
                os.path.join(exe_dir, "Wingame-logo.png"),
            ])
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates.append(os.path.join(base_dir, "docs", "screenshots", "Wingame-logo.png"))
        logo_path = next((p for p in candidates if p and os.path.exists(p)), "")
        if not logo_path:
            return QPixmap()
        src = QPixmap(logo_path)
        if src.isNull():
            return QPixmap()
        scaled = src.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        out = QPixmap(size, size)
        out.fill(Qt.GlobalColor.transparent)
        painter = QPainter(out)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, size, size), size * 0.22, size * 0.22)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, scaled)
        painter.end()
        return out

    def _create_tray_icon(self) -> QIcon:
        pm = self._load_logo_pixmap(64)
        if not pm.isNull():
            icon = QIcon()
            icon.addPixmap(pm)
            icon.addPixmap(self._load_logo_pixmap(32))
            icon.addPixmap(self._load_logo_pixmap(16))
            return icon

        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Rounded rectangle fallback
        painter.setBrush(QBrush(QColor(COLORS['primary'])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(2, 2, 60, 60, 16, 16)

        # Center symbol
        painter.setPen(QColor("#FFFFFF"))
        font = QFont("Segoe UI", 26, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "✦")
        painter.end()
        return QIcon(pixmap)

    def _setup_tray_icon(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self._create_tray_icon())
        self.tray_icon.setToolTip("WinGame // Hardware & Gaming Optimizer")

        tray_menu = QMenu()
        tray_menu.setStyleSheet(f"""
            QMenu {{
                background-color: #FFFFFF;
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI';
                font-size: 13px;
                color: #0F172A;
            }}
            QMenu::item {{
                padding: 6px 18px;
                border-radius: 6px;
            }}
            QMenu::item:selected {{
                background-color: #EFF6FF;
                color: {COLORS['primary']};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {COLORS['border']};
                margin: 4px 6px;
            }}
        """)

        # Open Window
        act_open = QAction("⊞ Open WinGame", self)
        act_open.triggered.connect(self._restore_from_tray)
        tray_menu.addAction(act_open)

        tray_menu.addSeparator()

        # Quick Clean
        act_quick = QAction("⚡ Quick RAM Clean", self)
        act_quick.triggered.connect(lambda: self._tray_clean_ram("quick"))
        tray_menu.addAction(act_quick)

        # Industrial Deep Purge
        act_deep = QAction("🚀 Deep Industrial RAM Purge", self)
        act_deep.triggered.connect(lambda: self._tray_clean_ram("industrial"))
        tray_menu.addAction(act_deep)

        tray_menu.addSeparator()

        # Toggle Auto-Killer
        self.act_tray_killer = QAction("🎯 Auto-Killer: Paused", self)
        self.act_tray_killer.triggered.connect(self._tray_toggle_killer)
        tray_menu.addAction(self.act_tray_killer)

        tray_menu.addSeparator()

        # Exit Completely
        act_exit = QAction("✕ Exit WinGame Completely", self)
        act_exit.triggered.connect(self._exit_completely)
        tray_menu.addAction(act_exit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            if self.isVisible() and not self.isMinimized():
                self.activateWindow()
                self.raise_()
            else:
                self._restore_from_tray()

    def _restore_from_tray(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _tray_clean_ram(self, mode: str):
        res = SystemOptimizer.clean_ram(mode=mode)
        freed = res.get("freed_mb", 0)
        mode_name = res.get("mode_name", "Clean")
        if self.config_mgr.get("show_notifications", True) and hasattr(self, "tray_icon") and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "WinGame Memory Optimizer",
                f"{mode_name}: {freed} MB freed instantly!",
                QSystemTrayIcon.MessageIcon.Information,
                2500
            )
        if hasattr(self, "view_hard"):
            self.view_hard.update_telemetry()
        if hasattr(self, "view_opt"):
            self.view_opt._update_live_ram_gauge()

    def _tray_toggle_killer(self):
        new_state = not self.auto_killer_worker.is_active()
        self.auto_killer_worker.set_active(new_state)
        self.view_auto.toggle_switch.setChecked(new_state)

    def _exit_completely(self):
        self._is_exiting_completely = True
        self.close()

    def _on_theme_changed(self, theme_id: str):
        """Schedules a flicker-free live theme rebuild on the next event loop tick."""
        QTimer.singleShot(0, lambda: self._apply_theme_rebuild(theme_id))

    def _apply_theme_rebuild(self, theme_id: str):
        """Applies the selected theme live across the entire application without restarting workers."""
        current_idx = self.pages_stack.currentIndex() if hasattr(self, "pages_stack") else 7
        self.setUpdatesEnabled(False)
        try:
            apply_theme(theme_id)
            self.setStyleSheet(get_stylesheet())

            # Disconnect worker signals from old views safely before rebuilding UI
            for sig in (
                self.game_watcher.game_boost_applied,
                self.game_watcher.game_closed,
                self.auto_killer_worker.process_killed,
                self.auto_killer_worker.stats_updated,
                self.auto_killer_worker.status_changed,
                self.auto_ram_worker.ram_auto_cleaned,
            ):
                try:
                    sig.disconnect()
                except Exception:
                    pass

            # Stop old view timers to avoid dangling timers
            for old_view in (self.view_hard, self.view_opt):
                for attr in ("timer", "ram_timer"):
                    t = getattr(old_view, attr, None)
                    if t is not None:
                        t.stop()

            # Detach & dispose old central widget cleanly before building the new one
            old_central = self.takeCentralWidget()
            if old_central is not None:
                old_central.hide()
                old_central.deleteLater()

            # Rebuild UI with the new COLORS palette & reconnect signals
            self._setup_ui()
            self._connect_signals()
            self._switch_page(current_idx)
            self._on_worker_status_changed(self.auto_killer_worker.is_active())

            # Refresh tray icon, window icon, and native DWM titlebar color
            new_icon = self._create_tray_icon()
            self.setWindowIcon(new_icon)
            if hasattr(self, "tray_icon"):
                self.tray_icon.setIcon(new_icon)
            self._apply_dwm_titlebar()
        finally:
            self.setUpdatesEnabled(True)

    def _on_worker_status_changed(self, is_active: bool):
        ms = self.auto_killer_worker.interval_ms
        if is_active:
            self.lbl_sidebar_status.setText(f"● ACTIVE ({ms}ms)")
            self.lbl_sidebar_status.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLORS['success']};")
        else:
            self.lbl_sidebar_status.setText("○ PAUSED")
            self.lbl_sidebar_status.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLORS['danger']};")

        if hasattr(self, "act_tray_killer"):
            status_text = "Active" if is_active else "Paused"
            self.act_tray_killer.setText(f"🎯 Auto-Killer: {status_text}")

    def _setup_global_hotkeys(self):
        self.hotkey_mgr = GlobalHotkeyManager(self)
        self.hotkey_mgr.hotkey_triggered.connect(self._on_global_hotkey)
        app = QApplication.instance()
        if app is not None:
            app.installNativeEventFilter(self.hotkey_mgr)
        if self.config_mgr.get("hotkeys_enabled", True):
            self.hotkey_mgr.register_all()

    def _on_global_hotkey(self, action: str):
        if action == "deep_ram":
            self._tray_clean_ram("industrial")
        elif action == "quick_ram":
            self._tray_clean_ram("quick")
        elif action == "toggle_killer":
            self._tray_toggle_killer()
            if self.config_mgr.get("show_notifications", True) and hasattr(self, "tray_icon") and self.tray_icon.isVisible():
                state = "ACTIVE" if self.auto_killer_worker.is_active() else "PAUSED"
                self.tray_icon.showMessage(
                    "WinGame Auto-Killer",
                    f"Auto-Killer toggled via hotkey: {state}",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )

    def _on_settings_saved(self):
        self.auto_killer_worker.reload_blacklist()
        self.auto_killer_worker.set_interval(self.auto_killer_worker.config_mgr.get("auto_kill_interval_ms", 250))
        self.view_auto.spin_interval.setValue(self.auto_killer_worker.interval_ms)
        saved_mode = self.config_mgr.get("auto_ram_mode", "industrial")
        if hasattr(self.view_opt, "combo_auto_mode"):
            self.view_opt.combo_auto_mode.setCurrentIndex(0 if saved_mode == "industrial" else 1)
        if hasattr(self, "hotkey_mgr"):
            if self.config_mgr.get("hotkeys_enabled", True):
                self.hotkey_mgr.register_all()
            else:
                self.hotkey_mgr.unregister_all()
        self._on_worker_status_changed(self.auto_killer_worker.is_active())

    def closeEvent(self, event):
        minimize_to_tray = self.config_mgr.get("minimize_to_tray", True)
        if minimize_to_tray and not self._is_exiting_completely and hasattr(self, "tray_icon") and self.tray_icon.isVisible():
            event.ignore()
            self.hide()
            if self.config_mgr.get("show_notifications", True) and not self._tray_notified_once:
                self.tray_icon.showMessage(
                    "WinGame Active in Background",
                    "WinGame continues protecting your PC in the tray. Double-click the tray icon to reopen.",
                    QSystemTrayIcon.MessageIcon.Information,
                    2500
                )
                self._tray_notified_once = True
        else:
            if hasattr(self, "hotkey_mgr"):
                self.hotkey_mgr.unregister_all()
            self.auto_killer_worker.stop()
            self.auto_ram_worker.stop()
            self.game_watcher.stop()
            if hasattr(self, "tray_icon"):
                self.tray_icon.hide()
            super().closeEvent(event)
