from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSpinBox, QComboBox, QCheckBox, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
import psutil
from config import ConfigManager
from core.optimizer import SystemOptimizer
from ui.animated_widgets import AnimatedButton, CircularGauge
from ui.styles import COLORS

class OptimizerCard(QFrame):
    """Card item representing an optimization tool with action button and optional gauge."""
    def __init__(self, icon: str, title: str, description: str, btn_text: str, on_click, variant="primary", gauge_widget=None, parent=None):
        super().__init__(parent)
        self.setObjectName("OptimizerCard")
        self.setStyleSheet(f"""
            QFrame#OptimizerCard {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 16px;
            }}
            QFrame#OptimizerCard:hover {{
                border-color: #CBD5E1;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(16)

        # Icon
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet("font-size: 28px;")
        layout.addWidget(lbl_icon)

        # Text Info
        info_box = QVBoxLayout()
        info_box.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {COLORS['text_primary']};")
        title_row.addWidget(lbl_title)

        self.lbl_size_badge = QLabel("")
        self.lbl_size_badge.setStyleSheet(f"""
            background-color: {COLORS['storage_bg']};
            color: {COLORS['storage_fg']};
            font-size: 11px;
            font-weight: 800;
            padding: 2px 8px;
            border-radius: 8px;
        """)
        self.lbl_size_badge.setVisible(False)
        title_row.addWidget(self.lbl_size_badge)
        title_row.addStretch()
        info_box.addLayout(title_row)

        lbl_desc = QLabel(description)
        lbl_desc.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']};")
        lbl_desc.setWordWrap(True)
        info_box.addWidget(lbl_desc)

        # Live outcome status label
        self.lbl_card_status = QLabel("")
        self.lbl_card_status.setStyleSheet("color: #10B981; font-weight: 700; font-size: 11px;")
        self.lbl_card_status.setVisible(False)
        info_box.addWidget(self.lbl_card_status)

        layout.addLayout(info_box, 1)

        # Optional Gauge (e.g. RAM Gauge on RAM card)
        if gauge_widget:
            layout.addWidget(gauge_widget)

        # Action Button
        self.btn = AnimatedButton(btn_text, variant=variant)
        self.btn.setFixedWidth(150)
        self.btn.clicked.connect(on_click)
        layout.addWidget(self.btn)

    def set_size_badge(self, mb: float):
        if mb >= 1024:
            txt = f"{mb / 1024:.2f} GB"
        else:
            txt = f"{mb:.1f} MB"
        self.lbl_size_badge.setText(txt)
        bg = COLORS["tweaks_bg"] if mb < 1.0 else COLORS["storage_bg"]
        fg = COLORS["tweaks_fg"] if mb < 1.0 else COLORS["storage_fg"]
        self.lbl_size_badge.setStyleSheet(f"""
            background-color: {bg};
            color: {fg};
            font-size: 11px;
            font-weight: 800;
            padding: 2px 8px;
            border-radius: 8px;
        """)
        self.lbl_size_badge.setVisible(True)

    def set_result(self, text: str, is_success: bool = True):
        color = "#10B981" if is_success else "#EF4444"
        self.lbl_card_status.setText(text)
        self.lbl_card_status.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 11px;")
        self.lbl_card_status.setVisible(True)


class OptimizerView(QWidget):
    stats_refresh_requested = pyqtSignal()
    automation_settings_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_mgr = ConfigManager()
        self._setup_ui()

        # Live RAM Gauge refresh timer (every 2.5s)
        self.ram_timer = QTimer(self)
        self.ram_timer.timeout.connect(self._update_live_ram_gauge)
        self.ram_timer.start(2500)
        self._update_live_ram_gauge()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(18)

        # Header Title
        title_box = QVBoxLayout()
        lbl_title = QLabel("System & Memory Optimizations")
        lbl_title.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {COLORS['text_primary']};")
        lbl_sub = QLabel("Dual-tier memory cleaner (Quick Trim & WinMemoryCleaner Engine), automated triggers, and junk purgers")
        lbl_sub.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']};")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        layout.addLayout(title_box)

        # ---------------- AUTOMATION SETTINGS CARD ----------------
        auto_card = QFrame()
        auto_card.setObjectName("AutoCard")
        auto_card.setStyleSheet(f"""
            QFrame#AutoCard {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 14px;
                padding: 18px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        ac_layout = QVBoxLayout(auto_card)
        ac_layout.setSpacing(14)

        lbl_ac_title = QLabel("🤖 AUTOMATED RAM & CACHE CLEANER")
        lbl_ac_title.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {COLORS['primary']}; letter-spacing: 1px;")
        ac_layout.addWidget(lbl_ac_title)

        # 1. Threshold Auto-Clean: if RAM >= X %
        row_thresh = QHBoxLayout()
        self.chk_thresh = QCheckBox("Auto-Clean RAM when consumption reaches:")
        self.chk_thresh.setChecked(self.config_mgr.get("auto_ram_threshold_enabled", False))
        self.chk_thresh.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 600;")
        row_thresh.addWidget(self.chk_thresh)

        self.spin_thresh = QSpinBox()
        self.spin_thresh.setRange(40, 95)
        self.spin_thresh.setSingleStep(5)
        self.spin_thresh.setValue(self.config_mgr.get("auto_ram_threshold_percent", 80))
        self.spin_thresh.setFixedWidth(80)
        row_thresh.addWidget(self.spin_thresh)

        lbl_pct = QLabel("%")
        lbl_pct.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 700; font-size: 13px;")
        row_thresh.addWidget(lbl_pct)
        row_thresh.addStretch()
        ac_layout.addLayout(row_thresh)

        # 2. Timer Auto-Clean: every X sec/min/hours
        row_timer = QHBoxLayout()
        self.chk_timer = QCheckBox("Auto-Clean Cache & RAM periodically every:")
        self.chk_timer.setChecked(self.config_mgr.get("auto_ram_timer_enabled", False))
        self.chk_timer.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 600;")
        row_timer.addWidget(self.chk_timer)

        self.spin_interval_val = QSpinBox()
        self.spin_interval_val.setRange(1, 999)
        self.spin_interval_val.setValue(self.config_mgr.get("auto_ram_timer_val", 5))
        self.spin_interval_val.setFixedWidth(80)
        row_timer.addWidget(self.spin_interval_val)

        self.combo_timer_unit = QComboBox()
        self.combo_timer_unit.addItems(["Seconds", "Minutes", "Hours"])
        unit_saved = self.config_mgr.get("auto_ram_timer_unit", "Minutes")
        idx = self.combo_timer_unit.findText(unit_saved)
        if idx >= 0:
            self.combo_timer_unit.setCurrentIndex(idx)
        self.combo_timer_unit.setFixedWidth(110)
        row_timer.addWidget(self.combo_timer_unit)
        row_timer.addStretch()
        ac_layout.addLayout(row_timer)

        # 3. Automation Intensity Mode
        row_mode = QHBoxLayout()
        lbl_mode = QLabel("Automated Cleaning Intensity:")
        lbl_mode.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 600;")
        row_mode.addWidget(lbl_mode)

        self.combo_auto_mode = QComboBox()
        self.combo_auto_mode.addItems([
            "🚀 Deep Industrial Purge (WinMemoryCleaner Engine)",
            "⚡ Quick Clean (Lightweight Working Set Trim)"
        ])
        saved_mode = self.config_mgr.get("auto_ram_mode", "industrial")
        self.combo_auto_mode.setCurrentIndex(0 if saved_mode == "industrial" else 1)
        self.combo_auto_mode.setFixedWidth(330)
        row_mode.addWidget(self.combo_auto_mode)
        row_mode.addStretch()
        ac_layout.addLayout(row_mode)

        # Save Automation Button & Status
        bot_ac = QHBoxLayout()
        self.lbl_auto_status = QLabel("Automation is ready.")
        self.lbl_auto_status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        bot_ac.addWidget(self.lbl_auto_status)
        bot_ac.addStretch()

        self.btn_save_auto = AnimatedButton("💾 Save Automation Rules", variant="primary")
        self.btn_save_auto.clicked.connect(self._save_automation_settings)
        bot_ac.addWidget(self.btn_save_auto)
        ac_layout.addLayout(bot_ac)

        layout.addWidget(auto_card)

        # ---------------- MANUAL ONE-CLICK TOOLS ----------------
        # Live RAM Gauge widget for Card 2
        self.ram_gauge = CircularGauge(value=0, accent_color=COLORS['ram_fg'])

        # Card 1: Quick RAM Clean (Léger & Rapide)
        self.card_ram_quick = OptimizerCard(
            icon="⚡",
            title="Quick RAM Clean (Soft Working Set Trim)",
            description="Fast and lightweight working set trim across background applications. Non-intrusive with zero disk I/O, ideal during active gameplay.",
            btn_text="Quick Clean",
            on_click=self._clean_ram_quick,
            variant="secondary"
        )
        layout.addWidget(self.card_ram_quick)

        # Card 2: Deep Industrial RAM Purge (WinMemoryCleaner Engine)
        self.card_ram_deep = OptimizerCard(
            icon="🚀",
            title="Deep Industrial RAM Purge (WinMemoryCleaner Engine)",
            description="Industrial multi-list purge: empties working sets, purges standby lists 0-7, flushes modified pages, and resets system file cache to reclaim maximum RAM.",
            btn_text="Deep Purge Now",
            on_click=self._clean_ram_deep,
            variant="primary",
            gauge_widget=self.ram_gauge
        )
        layout.addWidget(self.card_ram_deep)

        # ---------------- ADVANCED GAMING & DISK CLEANERS ----------------
        disk_hdr = QHBoxLayout()
        disk_hdr.setSpacing(10)
        lbl_disk_sec = QLabel("🎮 ADVANCED GAMING & DISK CLEANERS")
        lbl_disk_sec.setStyleSheet(f"font-size: 12px; font-weight: 800; color: {COLORS['primary']}; letter-spacing: 0.8px;")
        disk_hdr.addWidget(lbl_disk_sec)

        self.lbl_scan_total = QLabel("")
        self.lbl_scan_total.setStyleSheet(f"""
            background-color: {COLORS['primary_light']};
            color: {COLORS['primary']};
            font-size: 11px;
            font-weight: 800;
            padding: 3px 10px;
            border-radius: 8px;
        """)
        self.lbl_scan_total.setVisible(False)
        disk_hdr.addWidget(self.lbl_scan_total)
        disk_hdr.addStretch()

        self.btn_scan_junk = AnimatedButton("🔍 Scan Reclaimable Space", variant="secondary", compact=True)
        self.btn_scan_junk.setMinimumWidth(185)
        self.btn_scan_junk.setFixedHeight(30)
        self.btn_scan_junk.clicked.connect(self._scan_cleanable_space)
        disk_hdr.addWidget(self.btn_scan_junk)
        layout.addLayout(disk_hdr)

        # Card 3: Temp Files Cleaner
        self.card_temp = OptimizerCard(
            icon="🧹",
            title="Clean Temporary Files",
            description="Purges Windows %TEMP% and cached temporary application junk to reclaim free disk space.",
            btn_text="Clean Temp",
            on_click=self._clean_temp,
            variant="accent"
        )
        layout.addWidget(self.card_temp)

        # Card 4: DirectX / NVIDIA / AMD Shader Cache
        self.card_shaders = OptimizerCard(
            icon="🎮",
            title="DirectX & GPU Shader Cache",
            description="Clears compiled DirectX, NVIDIA (DXCache/GLCache/NV_Cache), and AMD shader caches to fix game stutters and free space.",
            btn_text="Clean Shaders",
            on_click=self._clean_shaders,
            variant="secondary"
        )
        layout.addWidget(self.card_shaders)

        # Card 5: Windows Update Download Cache
        self.card_winupd = OptimizerCard(
            icon="📦",
            title="Windows Update Cache",
            description="Removes leftover Windows Update installer packages from SoftwareDistribution\\Download safely.",
            btn_text="Clean Updates",
            on_click=self._clean_winupdate,
            variant="secondary"
        )
        layout.addWidget(self.card_winupd)

        # Card 6: Prefetch Cache
        self.card_prefetch = OptimizerCard(
            icon="⚡",
            title="Windows Prefetch Cache",
            description="Clears stale C:\\Windows\\Prefetch traces so Windows rebuilds fresh, faster app launch profiles.",
            btn_text="Clean Prefetch",
            on_click=self._clean_prefetch,
            variant="secondary"
        )
        layout.addWidget(self.card_prefetch)

        # Card 7: Recycle Bin
        self.card_recycle = OptimizerCard(
            icon="🗑️",
            title="Empty Recycle Bin",
            description="Silently empties the Windows Recycle Bin across all drives to recover disk storage instantly.",
            btn_text="Empty Bin",
            on_click=self._clean_recycle_bin,
            variant="secondary"
        )
        layout.addWidget(self.card_recycle)

        # Card 8: DNS Cache Flush
        self.card_dns = OptimizerCard(
            icon="🌐",
            title="Flush DNS Cache",
            description="Resets the Windows DNS resolver cache to eliminate network lags and refresh IP routes.",
            btn_text="Flush DNS",
            on_click=self._flush_dns,
            variant="secondary"
        )
        layout.addWidget(self.card_dns)

        # Card 9: Restart Explorer
        self.card_exp = OptimizerCard(
            icon="🖥",
            title="Restart Windows Explorer",
            description="Restores the Windows shell and taskbar after terminating explorer.exe for gaming.",
            btn_text="Start Explorer",
            on_click=self._restart_explorer,
            variant="secondary"
        )
        layout.addWidget(self.card_exp)

        # Result Banner
        self.lbl_result = QLabel("")
        self.lbl_result.setStyleSheet(f"""
            background-color: {COLORS['primary_light']};
            border: 1px solid {COLORS['border']};
            border-radius: 10px;
            padding: 14px;
            color: {COLORS['primary']};
            font-size: 13px;
            font-weight: 600;
        """)
        self.lbl_result.setVisible(False)
        layout.addWidget(self.lbl_result)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _update_live_ram_gauge(self):
        try:
            mem = psutil.virtual_memory()
            self.ram_gauge.set_value(mem.percent)
        except Exception:
            pass

    def _save_automation_settings(self):
        val = self.spin_interval_val.value()
        unit = self.combo_timer_unit.currentText()
        if unit == "Seconds":
            secs = val
        elif unit == "Minutes":
            secs = val * 60
        else: # Hours
            secs = val * 3600

        mode_val = "industrial" if self.combo_auto_mode.currentIndex() == 0 else "quick"

        self.config_mgr.set("auto_ram_threshold_enabled", self.chk_thresh.isChecked())
        self.config_mgr.set("auto_ram_threshold_percent", self.spin_thresh.value())
        self.config_mgr.set("auto_ram_timer_enabled", self.chk_timer.isChecked())
        self.config_mgr.set("auto_ram_timer_val", val)
        self.config_mgr.set("auto_ram_timer_unit", unit)
        self.config_mgr.set("auto_ram_timer_seconds", secs)
        self.config_mgr.set("auto_ram_mode", mode_val)

        self.automation_settings_updated.emit()
        self.lbl_auto_status.setText(f"✓ Automation rules saved! Mode: ({'Deep WinMemoryCleaner' if mode_val == 'industrial' else 'Quick Trim'})")
        self.lbl_auto_status.setStyleSheet(f"color: {COLORS['success']}; font-size: 11px; font-weight: bold;")
        QMessageBox.information(self, "Automation Saved", "Automated RAM cleaning rules updated successfully!")

    def _clean_ram_quick(self):
        res = SystemOptimizer.clean_ram(mode="quick")
        freed = res.get("freed_mb", 0.0)
        procs = res.get("processes_trimmed", 0)
        init_pct = res.get("initial_percent", 0.0)
        new_pct = res.get("new_percent", 0.0)
        msg = f"✓ Quick Clean: {freed:.1f} MB freed ({init_pct:.0f}% → {new_pct:.0f}%) across {procs} trimmed processes."
        self.card_ram_quick.set_result(msg, is_success=True)
        self._show_result(msg)
        self.ram_gauge.set_value(new_pct)
        self.stats_refresh_requested.emit()

    def _clean_ram_deep(self):
        res = SystemOptimizer.clean_ram(mode="industrial")
        freed = res.get("freed_mb", 0.0)
        procs = res.get("processes_trimmed", 0)
        init_pct = res.get("initial_percent", 0.0)
        new_pct = res.get("new_percent", 0.0)
        areas = res.get("areas_cleaned", [])
        if areas:
            msg = f"✓ Deep Purge: {freed:.1f} MB freed ({init_pct:.0f}% → {new_pct:.0f}%) — {len(areas)} WinMemoryCleaner kernel areas purged."
        elif not res.get("is_admin", False):
            msg = f"✓ Deep Purge: {freed:.1f} MB freed ({init_pct:.0f}% → {new_pct:.0f}%) across {procs} procs (Run as Administrator for full kernel Standby/Cache purge)."
        else:
            msg = f"✓ Deep Purge: {freed:.1f} MB freed ({init_pct:.0f}% → {new_pct:.0f}%) via WinMemoryCleaner Engine."
        self.card_ram_deep.set_result(msg, is_success=True)
        self._show_result(msg)
        self.ram_gauge.set_value(new_pct)
        self.stats_refresh_requested.emit()

    def _scan_cleanable_space(self):
        sizes = SystemOptimizer.scan_cleanable_space()
        self.card_temp.set_size_badge(sizes["temp_mb"])
        self.card_shaders.set_size_badge(sizes["shaders_mb"])
        self.card_winupd.set_size_badge(sizes["winupdate_mb"])
        self.card_prefetch.set_size_badge(sizes["prefetch_mb"])
        self.card_recycle.set_size_badge(sizes["recycle_mb"])
        total = sizes["total_mb"]
        total_txt = f"{total / 1024:.2f} GB reclaimable" if total >= 1024 else f"{total:.1f} MB reclaimable"
        self.lbl_scan_total.setText(total_txt)
        self.lbl_scan_total.setVisible(True)
        self._show_result(f"🔍 Scan complete: {total_txt} found across Temp, Shaders, Windows Update, Prefetch, and Recycle Bin.")

    def _clean_temp(self):
        res = SystemOptimizer.clean_temp_files()
        freed = res.get("freed_mb", 0.0)
        files = res.get("deleted_files", 0)
        msg = f"✓ Purged {freed:.1f} MB of junk ({files} temporary files removed)."
        self.card_temp.set_result(msg, is_success=True)
        self.card_temp.set_size_badge(0.0)
        self._show_result(msg)
        self.stats_refresh_requested.emit()

    def _clean_shaders(self):
        res = SystemOptimizer.clean_shader_cache()
        freed = res.get("freed_mb", 0.0)
        files = res.get("deleted_files", 0)
        msg = f"✓ Shader Cache cleaned: {freed:.1f} MB freed ({files} shader files removed)."
        self.card_shaders.set_result(msg, is_success=True)
        self.card_shaders.set_size_badge(0.0)
        self._show_result(msg)
        self.stats_refresh_requested.emit()

    def _clean_winupdate(self):
        res = SystemOptimizer.clean_windows_update_cache()
        freed = res.get("freed_mb", 0.0)
        files = res.get("deleted_files", 0)
        msg = f"✓ Windows Update Cache cleaned: {freed:.1f} MB freed ({files} files removed)."
        self.card_winupd.set_result(msg, is_success=True)
        self.card_winupd.set_size_badge(0.0)
        self._show_result(msg)
        self.stats_refresh_requested.emit()

    def _clean_prefetch(self):
        res = SystemOptimizer.clean_prefetch()
        freed = res.get("freed_mb", 0.0)
        files = res.get("deleted_files", 0)
        msg = f"✓ Prefetch cleaned: {freed:.1f} MB freed ({files} files removed)."
        self.card_prefetch.set_result(msg, is_success=True)
        self.card_prefetch.set_size_badge(0.0)
        self._show_result(msg)
        self.stats_refresh_requested.emit()

    def _clean_recycle_bin(self):
        res = SystemOptimizer.clean_recycle_bin()
        freed = res.get("freed_mb", 0.0)
        files = res.get("deleted_files", 0)
        msg = f"✓ Recycle Bin emptied: {freed:.1f} MB freed ({files} items permanently removed)."
        self.card_recycle.set_result(msg, is_success=True)
        self.card_recycle.set_size_badge(0.0)
        self._show_result(msg)
        self.stats_refresh_requested.emit()

    def _flush_dns(self):
        res = SystemOptimizer.flush_dns()
        if res["success"]:
            msg = f"✓ {res['output']}"
            self.card_dns.set_result(msg, is_success=True)
        else:
            msg = f"⚠ Error: {res['output']}"
            self.card_dns.set_result(msg, is_success=False)
        self._show_result(msg)

    def _restart_explorer(self):
        res = SystemOptimizer.restart_explorer()
        if res["success"]:
            msg = f"✓ {res['output']}"
            self.card_exp.set_result(msg, is_success=True)
        else:
            msg = f"⚠ Error: {res['output']}"
            self.card_exp.set_result(msg, is_success=False)
        self._show_result(msg)

    def on_ram_auto_cleaned(self, reason: str, freed_mb: float, new_percent: float, timestamp: str):
        msg = f"[{timestamp}] [Auto-Clean] {reason} -> Freed {freed_mb:.1f} MB (New load: {new_percent:.1f}%)"
        self._show_result(msg)
        self.ram_gauge.set_value(new_percent)
        self.card_ram_deep.set_result(msg, is_success=True)
        self.stats_refresh_requested.emit()

    def _show_result(self, text: str):
        self.lbl_result.setText(text)
        self.lbl_result.setVisible(True)
