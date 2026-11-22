import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QFrame, QComboBox,
    QCheckBox, QFileDialog, QMessageBox, QSplitter, QFileIconProvider
)
from PyQt6.QtCore import Qt, pyqtSignal, QFileInfo, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap
from core.game_engine import GameEngine, DEFAULT_GAME_SETTINGS
from ui.animated_widgets import AnimatedButton
from ui.styles import COLORS

class GameBoosterView(QWidget):
    game_launched = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.games = []
        self.selected_game = None
        self.icon_provider = QFileIconProvider()
        self._setup_ui()
        self.refresh_games()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(18)

        # Header Title
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_title = QLabel("Game Booster & Library")
        lbl_title.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {COLORS['text_primary']};")
        lbl_sub = QLabel("Auto-detects Steam and Riot games with genuine game logos. Customize CPU priority and auto-kill rules.")
        lbl_sub.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']};")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        top_bar.addLayout(title_box)

        top_bar.addStretch()

        # Add Local Game Button
        self.btn_add_local = AnimatedButton("+ Add Local Game", variant="primary")
        self.btn_add_local.clicked.connect(self._on_add_local_game_clicked)
        top_bar.addWidget(self.btn_add_local)

        # Refresh
        self.btn_refresh = AnimatedButton("Scan Games", variant="secondary")
        self.btn_refresh.clicked.connect(self.refresh_games)
        top_bar.addWidget(self.btn_refresh)

        layout.addLayout(top_bar)

        # Active Boosted Game Status Banner
        self.status_banner = QFrame()
        self.status_banner.setFixedHeight(38)
        self.status_banner.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
            }}
        """)
        sb_layout = QHBoxLayout(self.status_banner)
        sb_layout.setContentsMargins(14, 4, 14, 4)
        self.lbl_active_boost = QLabel("● GAME WATCHER ACTIVE — Ready to optimize detected games automatically")
        self.lbl_active_boost.setStyleSheet(f"color: {COLORS['primary']}; font-weight: bold; font-size: 12px;")
        sb_layout.addWidget(self.lbl_active_boost)
        layout.addWidget(self.status_banner)

        # Splitter Layout: Left Games List / Right Profile Settings
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: transparent; }")

        # LEFT PANE: Games List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(10)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search installed games...")
        self.search_input.textChanged.connect(self._filter_games_list)
        left_layout.addWidget(self.search_input)

        # Games ListWidget with Real Icons
        self.list_games = QListWidget()
        self.list_games.setIconSize(QSize(32, 32))
        self.list_games.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 14px;
                padding: 8px;
            }}
            QListWidget::item {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                padding: 10px 14px;
                margin-bottom: 6px;
                color: {COLORS['text_primary']};
                font-weight: 600;
                font-size: 13px;
            }}
            QListWidget::item:hover {{
                background-color: {COLORS['bg_table_header']};
                border-color: #CBD5E1;
            }}
            QListWidget::item:selected {{
                background-color: #EFF6FF;
                border: 1px solid #3B82F6;
                color: #1D4ED8;
            }}
        """)
        self.list_games.currentRowChanged.connect(self._on_game_selected)
        left_layout.addWidget(self.list_games)

        splitter.addWidget(left_widget)

        # RIGHT PANE: Selected Game Profile Settings
        self.right_widget = QFrame()
        self.right_widget.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 14px;
                padding: 22px;
            }}
        """)
        self.right_layout = QVBoxLayout(self.right_widget)
        self.right_layout.setSpacing(16)

        # Header Box with Real Game Icon & Title
        header_card = QHBoxLayout()
        header_card.setSpacing(16)

        # Large Game Icon Label
        self.lbl_game_icon_large = QLabel()
        self.lbl_game_icon_large.setFixedSize(48, 48)
        self.lbl_game_icon_large.setStyleSheet(f"background-color: {COLORS['bg_card_hover']}; border-radius: 10px;")
        self.lbl_game_icon_large.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_card.addWidget(self.lbl_game_icon_large)

        titles_vbox = QVBoxLayout()
        titles_vbox.setSpacing(2)
        self.lbl_selected_title = QLabel("Select a game to configure")
        self.lbl_selected_title.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {COLORS['text_primary']};")
        self.lbl_selected_meta = QLabel("Platform • Executable")
        self.lbl_selected_meta.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']};")
        titles_vbox.addWidget(self.lbl_selected_title)
        titles_vbox.addWidget(self.lbl_selected_meta)
        header_card.addLayout(titles_vbox, 1)

        self.right_layout.addLayout(header_card)

        # Launch Button
        self.btn_launch = AnimatedButton("Launch Game With Boost", variant="primary")
        self.btn_launch.setFixedHeight(42)
        self.btn_launch.clicked.connect(self._on_launch_clicked)
        self.right_layout.addWidget(self.btn_launch)

        # Settings Container
        settings_frame = QFrame()
        settings_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_table_header']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                padding: 16px;
            }}
        """)
        sf_layout = QVBoxLayout(settings_frame)
        sf_layout.setSpacing(14)

        # 1. CPU Priority
        prio_row = QHBoxLayout()
        lbl_p = QLabel("CPU Process Priority:")
        lbl_p.setStyleSheet(f"font-weight: 700; color: {COLORS['text_primary']};")
        prio_row.addWidget(lbl_p)

        self.combo_prio = QComboBox()
        self.combo_prio.addItems(["Normal", "AboveNormal", "High", "Realtime"])
        self.combo_prio.setFixedWidth(140)
        prio_row.addWidget(self.combo_prio)
        sf_layout.addLayout(prio_row)

        # 2. Checkboxes
        self.chk_autokill = QCheckBox("Activate Auto-Killer (250ms loop) while playing")
        self.chk_autokill.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {COLORS['text_primary']};")
        sf_layout.addWidget(self.chk_autokill)

        self.chk_explorer = QCheckBox("Kill Windows Explorer while playing (Auto-restores when game closes)")
        self.chk_explorer.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {COLORS['text_primary']};")
        sf_layout.addWidget(self.chk_explorer)

        self.chk_clean_ram = QCheckBox("Auto-Clean & Trim RAM on game startup")
        self.chk_clean_ram.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {COLORS['text_primary']};")
        sf_layout.addWidget(self.chk_clean_ram)

        self.right_layout.addWidget(settings_frame)

        # Save Button
        self.btn_save_profile = AnimatedButton("Save Optimization Profile", variant="secondary")
        self.btn_save_profile.clicked.connect(self._on_save_profile_clicked)
        self.right_layout.addWidget(self.btn_save_profile)

        self.right_layout.addStretch()
        splitter.addWidget(self.right_widget)

        splitter.setSizes([380, 520])
        layout.addWidget(splitter, 1)

    def _get_game_icon(self, exe_path: str) -> QIcon:
        """Extracts the genuine Windows executable game icon."""
        if exe_path and os.path.exists(exe_path):
            try:
                icon = self.icon_provider.icon(QFileInfo(exe_path))
                if not icon.isNull():
                    return icon
            except Exception:
                pass
        return self.style().standardIcon(self.style().StandardPixmap.SP_FileIcon)

    def refresh_games(self):
        self.games = GameEngine.scan_installed_games()
        self._populate_list(self.games)

    def _populate_list(self, games):
        filter_text = self.search_input.text().lower().strip()
        filtered = [g for g in games if filter_text in g["name"].lower() or filter_text in g["platform"].lower()]

        self.list_games.clear()
        for g in filtered:
            exe_path = g.get("exe_path", "")
            icon = self._get_game_icon(exe_path)
            
            # Real game icon, NO emojis
            item = QListWidgetItem(icon, f"  {g['name']}  ({g['platform']})")
            item.setData(Qt.ItemDataRole.UserRole, g)
            self.list_games.addItem(item)

        if self.list_games.count() > 0:
            self.list_games.setCurrentRow(0)

    def _filter_games_list(self):
        self._populate_list(self.games)

    def _on_game_selected(self, row: int):
        if row < 0:
            return
        item = self.list_games.item(row)
        if not item:
            return

        self.selected_game = item.data(Qt.ItemDataRole.UserRole)
        g = self.selected_game

        self.lbl_selected_title.setText(g["name"])
        self.lbl_selected_meta.setText(f"Platform: {g['platform']} • File: {g.get('exe_name') or 'N/A'}")

        # Extract and display large logo
        exe_path = g.get("exe_path", "")
        icon = self._get_game_icon(exe_path)
        pix = icon.pixmap(48, 48)
        self.lbl_game_icon_large.setPixmap(pix)

        # Settings
        settings = g.get("settings", DEFAULT_GAME_SETTINGS)
        prio = settings.get("priority", "High")
        idx = self.combo_prio.findText(prio)
        if idx >= 0:
            self.combo_prio.setCurrentIndex(idx)

        self.chk_autokill.setChecked(settings.get("auto_kill_blacklist", True))
        self.chk_explorer.setChecked(settings.get("auto_kill_explorer", False))
        self.chk_clean_ram.setChecked(settings.get("auto_clean_ram", True))

    def _on_save_profile_clicked(self):
        if not self.selected_game:
            return

        new_settings = {
            "priority": self.combo_prio.currentText(),
            "auto_kill_blacklist": self.chk_autokill.isChecked(),
            "auto_kill_explorer": self.chk_explorer.isChecked(),
            "auto_clean_ram": self.chk_clean_ram.isChecked()
        }

        self.selected_game["settings"] = new_settings
        GameEngine.update_game_settings(self.selected_game["id"], new_settings)
        QMessageBox.information(self, "Profile Saved", f"Profile for '{self.selected_game['name']}' saved successfully!")

    def _on_launch_clicked(self):
        if not self.selected_game:
            return

        self._on_save_profile_clicked()

        ok, msg = GameEngine.launch_game(self.selected_game)
        if ok:
            self.game_launched.emit(self.selected_game["name"])
            self.set_active_boost_status(self.selected_game["name"], "Game running — Optimizations active!")
        else:
            QMessageBox.warning(self, "Launch Notice", msg)

    def _on_add_local_game_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Game Executable",
            "C:\\",
            "Executable Files (*.exe)"
        )
        if not file_path:
            return

        base_name = os.path.splitext(os.path.basename(file_path))[0]
        ok, msg = GameEngine.add_custom_game(base_name, file_path)
        if ok:
            self.refresh_games()
            QMessageBox.information(self, "Game Added", msg)
        else:
            QMessageBox.warning(self, "Notice", msg)

    def set_active_boost_status(self, game_name: str, action_summary: str):
        self.lbl_active_boost.setText(f"🔥 BOOSTED: {game_name.upper()} • {action_summary}")
        self.lbl_active_boost.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold; font-size: 12px;")

    def set_game_closed_status(self, game_name: str):
        self.lbl_active_boost.setText(f"✓ {game_name} closed — System restored to normal mode.")
        self.lbl_active_boost.setStyleSheet(f"color: {COLORS['primary']}; font-weight: bold; font-size: 12px;")
