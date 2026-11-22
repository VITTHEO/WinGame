import os
import sys
import platform
import subprocess
import webbrowser
import psutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QFrame, QMessageBox, QScrollArea, QPushButton, QGridLayout, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from config import ConfigManager, DEFAULT_CONFIG
from core.startup_engine import StartupEngine
from core.winmemorycleaner import is_admin
from core.update_engine import (
    APP_VERSION, DEFAULT_GITHUB_REPO, UpdateEngine,
    UpdateCheckerThread, UpdateDownloadThread
)
from ui.animated_widgets import AnimatedButton, AnimatedToggleSwitch, ModernIntervalStepper
from ui.styles import COLORS, THEMES, get_current_theme_id


class ThemeCard(QFrame):
    """Clickable visual theme swatch card with live color preview."""
    clicked = pyqtSignal(str)

    def __init__(self, theme_id: str, theme_data: dict, is_selected: bool = False, parent=None):
        super().__init__(parent)
        self.theme_id = theme_id
        self.theme_data = theme_data
        self.is_selected = is_selected
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(108)
        self._build_ui()
        self.set_selected(is_selected)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Mini UI Preview Swatch (shows bg_main, bg_card, and primary accent)
        preview = QFrame()
        preview.setFixedHeight(42)
        preview.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme_data['bg_main']};
                border: 1px solid {self.theme_data['border']};
                border-radius: 8px;
            }}
        """)
        p_layout = QHBoxLayout(preview)
        p_layout.setContentsMargins(6, 6, 6, 6)
        p_layout.setSpacing(5)

        mini_card = QFrame()
        mini_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme_data['bg_card']};
                border: 1px solid {self.theme_data['border']};
                border-radius: 5px;
            }}
        """)
        p_layout.addWidget(mini_card, 2)

        mini_accent = QFrame()
        mini_accent.setFixedWidth(24)
        mini_accent.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme_data['primary']};
                border-radius: 5px;
            }}
        """)
        p_layout.addWidget(mini_accent)
        layout.addWidget(preview)

        # Theme Name + Active Check
        name_row = QHBoxLayout()
        name_row.setSpacing(4)
        self.lbl_name = QLabel(f"{self.theme_data['emoji']} {self.theme_data['name']}")
        self.lbl_name.setStyleSheet(f"font-size: 12px; font-weight: 800; color: {COLORS['text_primary']};")
        name_row.addWidget(self.lbl_name)
        name_row.addStretch()

        self.lbl_check = QLabel("✓")
        self.lbl_check.setStyleSheet(f"font-size: 12px; font-weight: 900; color: {COLORS['primary']};")
        self.lbl_check.setVisible(self.is_selected)
        name_row.addWidget(self.lbl_check)
        layout.addLayout(name_row)

        # Short subtitle
        lbl_desc = QLabel(self.theme_data["desc"])
        lbl_desc.setStyleSheet(f"font-size: 11px; color: {COLORS['text_secondary']};")
        layout.addWidget(lbl_desc)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.lbl_check.setVisible(selected)
        border_col = COLORS["primary"] if selected else COLORS["border"]
        border_w = "2px" if selected else "1px"
        bg_col = COLORS["primary_light"] if selected else COLORS["bg_card"]
        self.setObjectName("ThemeCard")
        self.setStyleSheet(f"""
            QFrame#ThemeCard {{
                background-color: {bg_col};
                border: {border_w} solid {border_col};
                border-radius: 12px;
            }}
            QFrame#ThemeCard:hover {{
                border: 2px solid {COLORS['primary']};
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.theme_id)
        super().mousePressEvent(event)


class SettingsView(QWidget):
    settings_saved = pyqtSignal()
    theme_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_mgr = ConfigManager()
        self.theme_cards = {}
        self._update_thread = None
        self._download_thread = None
        self._latest_update_info = None
        self._setup_ui()

    def _make_section_card(self, icon: str, title: str, subtitle: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("SettingsSectionCard")
        card.setStyleSheet(f"""
            QFrame#SettingsSectionCard {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 14px;
            }}
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(20, 18, 20, 18)
        c_layout.setSpacing(14)

        hdr = QVBoxLayout()
        hdr.setSpacing(2)
        lbl_t = QLabel(f"{icon}  {title}")
        lbl_t.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {COLORS['text_primary']};")
        lbl_s = QLabel(subtitle)
        lbl_s.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']};")
        hdr.addWidget(lbl_t)
        hdr.addWidget(lbl_s)
        c_layout.addLayout(hdr)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {COLORS['border']};")
        c_layout.addWidget(sep)

        return card, c_layout

    def _make_row(self, title: str, desc: str, right_widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(16)
        info = QVBoxLayout()
        info.setSpacing(2)
        lbl = QLabel(title)
        lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {COLORS['text_primary']};")
        sub = QLabel(desc)
        sub.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']};")
        sub.setWordWrap(True)
        info.addWidget(lbl)
        info.addWidget(sub)
        row.addLayout(info, 1)
        row.addWidget(right_widget, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return row

    def _add_divider(self, layout: QVBoxLayout):
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {COLORS['border']};")
        layout.addWidget(sep)

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
        layout.setSpacing(20)

        # ---------------- HEADER ----------------
        hdr_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        lbl_title = QLabel("Settings & Preferences")
        lbl_title.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {COLORS['text_primary']};")
        lbl_sub = QLabel("Personalize appearance themes, background behavior, and optimization engines")
        lbl_sub.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']};")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        hdr_row.addLayout(title_box, 1)

        # Admin status pill
        admin_ok = is_admin()
        badge_bg = COLORS["tweaks_bg"] if admin_ok else COLORS["storage_bg"]
        badge_fg = COLORS["tweaks_fg"] if admin_ok else COLORS["storage_fg"]
        badge_txt = "🛡️ Administrator Mode" if admin_ok else "⚠️ Standard Mode"
        lbl_admin = QLabel(badge_txt)
        lbl_admin.setStyleSheet(f"""
            background-color: {badge_bg};
            color: {badge_fg};
            font-size: 11px;
            font-weight: 800;
            padding: 6px 12px;
            border-radius: 10px;
        """)
        hdr_row.addWidget(lbl_admin, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(hdr_row)

        # ---------------- SECTION 1: APPEARANCE & THEMES ----------------
        theme_card, theme_layout = self._make_section_card(
            "🎨", "Appearance & Themes",
            "Switch WinGame's color palette instantly — changes are saved automatically"
        )

        theme_grid = QHBoxLayout()
        theme_grid.setSpacing(12)
        current_theme = get_current_theme_id()
        for tid, tdata in THEMES.items():
            tc = ThemeCard(tid, tdata, is_selected=(tid == current_theme))
            tc.clicked.connect(self._on_theme_card_clicked)
            self.theme_cards[tid] = tc
            theme_grid.addWidget(tc, 1)
        theme_layout.addLayout(theme_grid)
        layout.addWidget(theme_card)

        # ---------------- SECTION 2: GENERAL & BACKGROUND ----------------
        gen_card, gen_layout = self._make_section_card(
            "⚙️", "General & Background Behavior",
            "Control system tray integration, Windows startup, and desktop notifications"
        )

        self.sw_tray = AnimatedToggleSwitch(checked=self.config_mgr.get("minimize_to_tray", True))
        gen_layout.addLayout(self._make_row(
            "Minimize to System Tray on close",
            "Keep Auto-Killer, Game Watcher, and RAM Cleaner active near the Windows clock when closing the window.",
            self.sw_tray
        ))
        self._add_divider(gen_layout)

        self.sw_autostart = AnimatedToggleSwitch(checked=StartupEngine.is_run_at_startup())
        gen_layout.addLayout(self._make_row(
            "Start WinGame automatically with Windows (minimized)",
            "Launch WinGame silently in the background on boot so your PC stays optimized from the start.",
            self.sw_autostart
        ))
        self._add_divider(gen_layout)

        self.sw_notifs = AnimatedToggleSwitch(checked=self.config_mgr.get("show_notifications", True))
        gen_layout.addLayout(self._make_row(
            "Show System Tray notifications",
            "Display Windows balloon notifications after tray RAM cleanups or when minimizing to background.",
            self.sw_notifs
        ))
        self._add_divider(gen_layout)

        self.sw_skip_splash = AnimatedToggleSwitch(checked=self.config_mgr.get("skip_splash", False))
        gen_layout.addLayout(self._make_row(
            "Skip startup splash animation",
            "Open the main dashboard immediately without waiting for the startup loading animation.",
            self.sw_skip_splash
        ))
        layout.addWidget(gen_card)

        # ---------------- SECTION 3: OPTIMIZATION ENGINES ----------------
        eng_card, eng_layout = self._make_section_card(
            "🚀", "Memory & Auto-Killer Engines",
            "Fine-tune process termination speed and automated WinMemoryCleaner intensity"
        )

        # Interval stepper + ms
        interval_box = QWidget()
        ib_layout = QHBoxLayout(interval_box)
        ib_layout.setContentsMargins(0, 0, 0, 0)
        ib_layout.setSpacing(8)
        self.spin_interval = ModernIntervalStepper(
            value=self.config_mgr.get("auto_kill_interval_ms", 250),
            min_val=50, max_val=10000, step=50
        )
        lbl_ms = QLabel("ms")
        lbl_ms.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 700; font-size: 13px;")
        ib_layout.addWidget(self.spin_interval)
        ib_layout.addWidget(lbl_ms)
        eng_layout.addLayout(self._make_row(
            "Auto-Kill Scan Interval",
            "How often the Auto-Killer scans and terminates blacklisted background processes (Default: 250 ms).",
            interval_box
        ))
        self._add_divider(eng_layout)

        self.sw_tree = AnimatedToggleSwitch(checked=self.config_mgr.get("kill_children", True))
        eng_layout.addLayout(self._make_row(
            "Terminate entire process tree",
            "Also terminate all child processes and subprocesses spawned by blacklisted applications.",
            self.sw_tree
        ))
        self._add_divider(eng_layout)

        self.combo_ram_mode = QComboBox()
        self.combo_ram_mode.addItems([
            "🚀 Deep Industrial (WinMemoryCleaner)",
            "⚡ Quick Clean (Léger)"
        ])
        saved_mode = self.config_mgr.get("auto_ram_mode", "industrial")
        self.combo_ram_mode.setCurrentIndex(0 if saved_mode == "industrial" else 1)
        self.combo_ram_mode.setFixedWidth(290)
        eng_layout.addLayout(self._make_row(
            "Automated RAM Cleaning Engine",
            "Choose whether automatic RAM cleanups run the full 7-area WinMemoryCleaner purge or lightweight Quick Trim.",
            self.combo_ram_mode
        ))
        layout.addWidget(eng_card)

        # ---------------- SECTION 3B: GLOBAL HOTKEYS ----------------
        hk_card, hk_layout = self._make_section_card(
            "⌨️", "Global Gaming Hotkeys",
            "Trigger RAM purges or toggle Auto-Killer instantly while gaming without Alt-Tabbing"
        )

        self.sw_hotkeys = AnimatedToggleSwitch(checked=self.config_mgr.get("hotkeys_enabled", True))
        hk_layout.addLayout(self._make_row(
            "Enable Global Windows Hotkeys",
            "Listen for system-wide keyboard shortcuts even when WinGame is minimized to the System Tray.",
            self.sw_hotkeys
        ))
        self._add_divider(hk_layout)

        hk_grid = QHBoxLayout()
        hk_grid.setSpacing(10)
        hotkey_items = [
            ("Ctrl + Shift + R", "🚀 Deep RAM Purge"),
            ("Ctrl + Shift + Q", "⚡ Quick RAM Clean"),
            ("Ctrl + Shift + K", "🎯 Toggle Auto-Killer"),
        ]
        for keys_txt, action_txt in hotkey_items:
            pill = QFrame()
            pill.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['bg_table_header']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 10px;
                    padding: 8px 12px;
                }}
            """)
            pl = QVBoxLayout(pill)
            pl.setContentsMargins(6, 4, 6, 4)
            pl.setSpacing(4)
            lbl_k = QLabel(keys_txt)
            lbl_k.setStyleSheet(f"""
                background-color: {COLORS['primary_light']};
                color: {COLORS['primary']};
                font-size: 11px;
                font-weight: 800;
                padding: 3px 8px;
                border-radius: 6px;
            """)
            lbl_k.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_a = QLabel(action_txt)
            lbl_a.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {COLORS['text_primary']};")
            lbl_a.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pl.addWidget(lbl_k)
            pl.addWidget(lbl_a)
            hk_grid.addWidget(pill, 1)
        hk_layout.addLayout(hk_grid)
        layout.addWidget(hk_card)

        # ---------------- SECTION 3C: UPDATES & VERSION ----------------
        upd_card, upd_layout = self._make_section_card(
            "🔄", f"Updates & Version  ({APP_VERSION})",
            "Check GitHub Releases for new WinGame versions and install updates in one click"
        )

        self.sw_auto_update = AnimatedToggleSwitch(checked=self.config_mgr.get("auto_check_updates", True))
        upd_layout.addLayout(self._make_row(
            "Check for updates automatically on startup",
            "Silently queries GitHub Releases in the background when WinGame starts.",
            self.sw_auto_update
        ))
        self._add_divider(upd_layout)

        self.input_github_repo = QLineEdit()
        self.input_github_repo.setText(self.config_mgr.get("github_repo", DEFAULT_GITHUB_REPO))
        self.input_github_repo.setPlaceholderText("username/WinGame")
        self.input_github_repo.setFixedWidth(250)
        upd_layout.addLayout(self._make_row(
            "GitHub Repository (owner/repo)",
            "Repository checked for latest GitHub Releases (e.g. YourName/WinGame).",
            self.input_github_repo
        ))
        self._add_divider(upd_layout)

        upd_action_row = QHBoxLayout()
        upd_action_row.setSpacing(10)
        self.lbl_update_status = QLabel(f"Installed version: {APP_VERSION}")
        self.lbl_update_status.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {COLORS['text_secondary']};")
        self.lbl_update_status.setWordWrap(True)
        upd_action_row.addWidget(self.lbl_update_status, 1)

        self.btn_install_update = AnimatedButton("⬇️ Download & Install", variant="primary", compact=True)
        self.btn_install_update.setMinimumWidth(165)
        self.btn_install_update.setFixedHeight(32)
        self.btn_install_update.setVisible(False)
        self.btn_install_update.clicked.connect(self._download_or_open_update)
        upd_action_row.addWidget(self.btn_install_update)

        self.btn_check_update = AnimatedButton("🔄 Check for Updates", variant="secondary", compact=True)
        self.btn_check_update.setMinimumWidth(155)
        self.btn_check_update.setFixedHeight(32)
        self.btn_check_update.clicked.connect(self._check_for_updates)
        upd_action_row.addWidget(self.btn_check_update)
        upd_layout.addLayout(upd_action_row)
        layout.addWidget(upd_card)

        # ---------------- SECTION 4: SYSTEM ENVIRONMENT & MAINTENANCE ----------------
        sys_card, sys_layout = self._make_section_card(
            "💻", "System Environment & Maintenance",
            "Hardware runtime overview and configuration utilities"
        )

        env_grid = QGridLayout()
        env_grid.setSpacing(12)

        cpu_count = psutil.cpu_count(logical=True)
        ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
        os_info = f"{platform.system()} {platform.release()} ({platform.architecture()[0]})"
        py_ver = f"Python {platform.python_version()}"

        env_items = [
            ("Operating System", os_info),
            ("CPU Logical Cores", f"{cpu_count} Threads"),
            ("Physical Memory", f"{ram_gb} GB RAM"),
            ("Runtime Engine", f"{py_ver} • WMC Port"),
        ]
        for idx, (k, v) in enumerate(env_items):
            pill = QFrame()
            pill.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['bg_table_header']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 10px;
                    padding: 10px 14px;
                }}
            """)
            pl = QVBoxLayout(pill)
            pl.setContentsMargins(6, 4, 6, 4)
            pl.setSpacing(2)
            lk = QLabel(k.upper())
            lk.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {COLORS['text_muted']}; letter-spacing: 0.5px;")
            lv = QLabel(v)
            lv.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {COLORS['text_primary']};")
            pl.addWidget(lk)
            pl.addWidget(lv)
            env_grid.addWidget(pill, idx // 2, idx % 2)
        sys_layout.addLayout(env_grid)
        layout.addWidget(sys_card)

        # ---------------- FEEDBACK TOAST BANNER ----------------
        self.lbl_toast = QLabel("")
        self.lbl_toast.setStyleSheet(f"""
            background-color: {COLORS['tweaks_bg']};
            color: {COLORS['tweaks_fg']};
            border: 1px solid {COLORS['border']};
            border-radius: 10px;
            padding: 10px 14px;
            font-weight: 700;
            font-size: 12px;
        """)
        self.lbl_toast.setVisible(False)
        layout.addWidget(self.lbl_toast)

        # ---------------- ACTION BUTTONS ROW ----------------
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_open_folder = AnimatedButton("📂 Open App Folder", variant="secondary")
        self.btn_open_folder.clicked.connect(self._open_app_folder)
        btn_row.addWidget(self.btn_open_folder)

        self.btn_reset = AnimatedButton("🔄 Reset Defaults", variant="danger")
        self.btn_reset.clicked.connect(self._reset_defaults)
        btn_row.addWidget(self.btn_reset)

        btn_row.addStretch()

        self.btn_save = AnimatedButton("💾 Save Configuration", variant="primary")
        self.btn_save.clicked.connect(self._save_settings)
        btn_row.addWidget(self.btn_save)

        layout.addLayout(btn_row)
        layout.addStretch(1)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _show_toast(self, text: str):
        self.lbl_toast.setText(text)
        self.lbl_toast.setVisible(True)
        QTimer.singleShot(3000, lambda: self.lbl_toast.setVisible(False))

    def _on_theme_card_clicked(self, theme_id: str):
        self.config_mgr.set("theme", theme_id)
        for tid, card in self.theme_cards.items():
            card.set_selected(tid == theme_id)
        self.theme_changed.emit(theme_id)

    def _open_app_folder(self):
        folder = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        try:
            subprocess.Popen(["explorer.exe", folder])
        except Exception:
            pass

    def _reset_defaults(self):
        reply = QMessageBox.question(
            self,
            "Reset Configuration",
            "Reset all WinGame settings to their default values?\n(Your blacklist will be restored to defaults and theme to Sparkle Light.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config_mgr.config = DEFAULT_CONFIG.copy()
            self.config_mgr.set("theme", "sparkle_light")
            self.config_mgr.set("minimize_to_tray", True)
            self.config_mgr.set("show_notifications", True)
            self.config_mgr.set("skip_splash", False)
            self.config_mgr.set("hotkeys_enabled", True)
            self.config_mgr.set("auto_check_updates", True)
            self.config_mgr.set("auto_ram_mode", "industrial")
            StartupEngine.set_run_at_startup(False)
            self.theme_changed.emit("sparkle_light")
            self.settings_saved.emit()

    def _check_for_updates(self):
        repo = self.input_github_repo.text().strip() or DEFAULT_GITHUB_REPO
        self.config_mgr.set("github_repo", repo)
        self.btn_check_update.setEnabled(False)
        self.btn_check_update.setText("⏳ Checking...")
        self.btn_install_update.setVisible(False)
        self.lbl_update_status.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {COLORS['primary']};")
        self.lbl_update_status.setText(f"Checking GitHub Releases for '{repo}'...")

        self._update_thread = UpdateCheckerThread(repo_override=repo, parent=self)
        self._update_thread.check_finished.connect(self._on_update_check_done)
        self._update_thread.start()

    def _on_update_check_done(self, info: dict):
        self.btn_check_update.setEnabled(True)
        self.btn_check_update.setText("🔄 Check for Updates")
        self._latest_update_info = info
        status = info.get("status")
        msg = info.get("message", "")

        if status == "update_available":
            self.lbl_update_status.setStyleSheet(f"font-size: 12px; font-weight: 800; color: {COLORS['success']};")
            self.lbl_update_status.setText(f"🎉 {msg}")
            if info.get("installer_url"):
                self.btn_install_update.setText(f"⬇️ Install {info.get('latest_version', '')}")
            else:
                self.btn_install_update.setText("🌐 Open Release")
            self.btn_install_update.setVisible(True)
        elif status == "up_to_date":
            self.lbl_update_status.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {COLORS['success']};")
            self.lbl_update_status.setText(f"✓ {msg}")
        else:
            self.lbl_update_status.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {COLORS['warning']};")
            self.lbl_update_status.setText(f"ℹ️ {msg}")

    def _download_or_open_update(self):
        if not self._latest_update_info:
            return
        dl_url = self._latest_update_info.get("installer_url")
        html_url = self._latest_update_info.get("html_url")
        if not dl_url:
            if html_url:
                webbrowser.open(html_url)
            return

        fname = self._latest_update_info.get("installer_name") or "WinGame_Installer.exe"
        self.btn_install_update.setEnabled(False)
        self.btn_install_update.setText("⏳ Downloading 0%")
        self.lbl_update_status.setText(f"Downloading {fname}...")
        self._download_thread = UpdateDownloadThread(dl_url, fname, parent=self)
        self._download_thread.progress.connect(lambda p: self.btn_install_update.setText(f"⏳ Downloading {p}%"))
        self._download_thread.download_finished.connect(self._on_download_done)
        self._download_thread.start()

    def _on_download_done(self, ok: bool, path_or_err: str):
        self.btn_install_update.setEnabled(True)
        if ok and os.path.exists(path_or_err):
            self.lbl_update_status.setText(f"✓ Downloaded! Launching installer...")
            try:
                subprocess.Popen([path_or_err], shell=False)
            except Exception as e:
                QMessageBox.warning(self, "Launch Failed", f"Downloaded to:\n{path_or_err}\n\nError: {e}")
        else:
            self.btn_install_update.setText("⬇️ Retry Download")
            self.lbl_update_status.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {COLORS['danger']};")
            self.lbl_update_status.setText(f"⚠️ Download failed: {path_or_err}")

    def _save_settings(self):
        self.config_mgr.set("auto_kill_interval_ms", self.spin_interval.value())
        self.config_mgr.set("kill_children", self.sw_tree.isChecked())
        self.config_mgr.set("minimize_to_tray", self.sw_tray.isChecked())
        self.config_mgr.set("show_notifications", self.sw_notifs.isChecked())
        self.config_mgr.set("skip_splash", self.sw_skip_splash.isChecked())
        self.config_mgr.set("hotkeys_enabled", self.sw_hotkeys.isChecked())
        self.config_mgr.set("auto_check_updates", self.sw_auto_update.isChecked())
        repo = self.input_github_repo.text().strip() or DEFAULT_GITHUB_REPO
        self.config_mgr.set("github_repo", repo)
        self.config_mgr.set("auto_ram_mode", "industrial" if self.combo_ram_mode.currentIndex() == 0 else "quick")

        # Configure boot startup in Windows registry
        StartupEngine.set_run_at_startup(self.sw_autostart.isChecked())

        self.settings_saved.emit()
        self._show_toast("✓ Configuration and startup preferences saved successfully!")
