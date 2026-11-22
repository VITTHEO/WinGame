import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from core.hardware_engine import HardwareEngine
from core.optimizer import SystemOptimizer
from core.tweaks_engine import TweaksEngine
from ui.animated_widgets import AnimatedButton, CircularGauge, LiveSparklineWidget
from ui.styles import COLORS

class SparkleInfoCard(QFrame):
    """
    Exact replica of Sparkle's dashboard card with icon container,
    metadata labels, and circular progress gauge ("camembert rond").
    """
    def __init__(self, title: str, subtitle: str, bg_color: str, fg_color: str, icon_symbol: str, parent=None):
        super().__init__(parent)
        self.setObjectName("SparkleInfoCard")
        self.setStyleSheet(f"""
            QFrame#SparkleInfoCard {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 16px;
            }}
            QFrame#SparkleInfoCard:hover {{
                border-color: #CBD5E1;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        
        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(18, 16, 18, 14)
        self.outer_layout.setSpacing(10)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        # Left Info Stack
        left_box = QVBoxLayout()
        left_box.setSpacing(10)

        # Header: Icon Container + Titles
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        icon_frame = QFrame()
        icon_frame.setObjectName("IconFrame")
        icon_frame.setFixedSize(42, 42)
        icon_frame.setStyleSheet(f"""
            QFrame#IconFrame {{
                background-color: {bg_color};
                border-radius: 10px;
                border: none;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        ic_layout = QVBoxLayout(icon_frame)
        ic_layout.setContentsMargins(0, 0, 0, 0)
        lbl_icon = QLabel(icon_symbol)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet(f"font-size: 20px; color: {fg_color}; font-weight: bold;")
        ic_layout.addWidget(lbl_icon)
        top_row.addWidget(icon_frame)

        titles_box = QVBoxLayout()
        titles_box.setSpacing(2)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {COLORS['text_primary']};")
        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet(f"font-size: 11px; color: {COLORS['text_secondary']};")
        titles_box.addWidget(lbl_t)
        titles_box.addWidget(lbl_sub)
        top_row.addLayout(titles_box)
        top_row.addStretch()

        left_box.addLayout(top_row)

        # Metadata Details (Model & Spec)
        self.meta_layout = QVBoxLayout()
        self.meta_layout.setSpacing(4)

        self.lbl_field1_title = QLabel("Model")
        self.lbl_field1_title.setStyleSheet(f"font-size: 11px; color: {COLORS['text_muted']}; font-weight: 600;")
        self.lbl_field1_val = QLabel("Detecting...")
        self.lbl_field1_val.setWordWrap(True)
        self.lbl_field1_val.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {COLORS['text_primary']};")
        self.meta_layout.addWidget(self.lbl_field1_title)
        self.meta_layout.addWidget(self.lbl_field1_val)

        self.lbl_field2_title = QLabel("Cores")
        self.lbl_field2_title.setStyleSheet(f"font-size: 11px; color: {COLORS['text_muted']}; font-weight: 600;")
        self.lbl_field2_val = QLabel("...")
        self.lbl_field2_val.setWordWrap(True)
        self.lbl_field2_val.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {COLORS['text_primary']};")
        self.meta_layout.addWidget(self.lbl_field2_title)
        self.meta_layout.addWidget(self.lbl_field2_val)

        left_box.addLayout(self.meta_layout)
        main_layout.addLayout(left_box, 1)

        # Right Side: Circular Gauge (Camembert Rond)
        self.gauge = CircularGauge(value=0, accent_color=fg_color)
        main_layout.addWidget(self.gauge, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.outer_layout.addLayout(main_layout, 1)

    def add_footer_widget(self, widget: QWidget):
        self.outer_layout.addWidget(widget)


class HardwareHomeView(QWidget):
    navigate_to_page = pyqtSignal(int)
    stats_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

        # Telemetry refresh timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start(1500)
        self.update_telemetry()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(24)

        # ---------------- GREETING HEADER ----------------
        # Matches "Welcome Back, VIT THEO" from Sparkle screenshot
        greet_box = QHBoxLayout()
        lbl_welcome = QLabel("Welcome Back, ")
        lbl_welcome.setStyleSheet(f"font-size: 26px; font-weight: 800; color: {COLORS['text_primary']};")
        
        # User name in emerald green like Sparkle
        user_name = os.environ.get("USERNAME", "VIT THEO").upper()
        if "VIT" in user_name:
            user_name = "VIT THEO"
        lbl_name = QLabel(user_name)
        lbl_name.setStyleSheet(f"font-size: 26px; font-weight: 900; color: {COLORS['text_gradient_green']};")
        
        greet_box.addWidget(lbl_welcome)
        greet_box.addWidget(lbl_name)
        greet_box.addStretch()
        layout.addLayout(greet_box)

        # ---------------- 6 SPARKLE HARDWARE CARDS GRID (2x3) ----------------
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(20)

        # 1. CPU Card
        self.card_cpu = SparkleInfoCard(
            title="CPU",
            subtitle="Processor Information",
            bg_color=COLORS["cpu_bg"],
            fg_color=COLORS["cpu_fg"],
            icon_symbol="⚡"
        )
        self.card_cpu.lbl_field1_title.setText("Model")
        self.card_cpu.lbl_field2_title.setText("Cores")
        self.spark_cpu = LiveSparklineWidget(accent_color=COLORS["cpu_fg"])
        self.card_cpu.add_footer_widget(self.spark_cpu)
        grid.addWidget(self.card_cpu, 0, 0)

        # 2. GPU Card
        self.card_gpu = SparkleInfoCard(
            title="GPU",
            subtitle="Graphics Information",
            bg_color=COLORS["gpu_bg"],
            fg_color=COLORS["gpu_fg"],
            icon_symbol="🖥"
        )
        self.card_gpu.lbl_field1_title.setText("Model")
        self.card_gpu.lbl_field2_title.setText("Type")
        self.lbl_gpu_temp = QLabel("🌡️ --°C  •  VRAM --")
        self.lbl_gpu_temp.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLORS['gpu_fg']};")
        self.card_gpu.meta_layout.addSpacing(4)
        self.card_gpu.meta_layout.addWidget(self.lbl_gpu_temp)
        self.spark_gpu = LiveSparklineWidget(accent_color=COLORS["gpu_fg"])
        self.card_gpu.add_footer_widget(self.spark_gpu)
        grid.addWidget(self.card_gpu, 0, 1)

        # 3. Memory (RAM) Card
        self.card_ram = SparkleInfoCard(
            title="Memory",
            subtitle="RAM Information",
            bg_color=COLORS["ram_bg"],
            fg_color=COLORS["ram_fg"],
            icon_symbol="🧠"
        )
        self.card_ram.lbl_field1_title.setText("Total Memory")
        self.card_ram.lbl_field2_title.setText("Type")

        # Dual RAM Cleaner buttons on dashboard: Quick & Deep (WinMemoryCleaner)
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        self.btn_quick_ram = AnimatedButton("⚡ Quick", variant="secondary", compact=True)
        self.btn_quick_ram.setMinimumWidth(84)
        self.btn_quick_ram.setFixedHeight(28)
        self.btn_quick_ram.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_quick_ram.clicked.connect(lambda: self._on_quick_clear_ram_clicked("quick"))
        btn_box.addWidget(self.btn_quick_ram)

        self.btn_deep_ram = AnimatedButton("🚀 Deep", variant="primary", compact=True)
        self.btn_deep_ram.setMinimumWidth(84)
        self.btn_deep_ram.setFixedHeight(28)
        self.btn_deep_ram.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_deep_ram.clicked.connect(lambda: self._on_quick_clear_ram_clicked("industrial"))
        btn_box.addWidget(self.btn_deep_ram)

        btn_box.addStretch()
        self.card_ram.meta_layout.addSpacing(6)
        self.card_ram.meta_layout.addLayout(btn_box)
        self.spark_ram = LiveSparklineWidget(accent_color=COLORS["ram_fg"])
        self.card_ram.add_footer_widget(self.spark_ram)

        grid.addWidget(self.card_ram, 0, 2)

        # 4. System (OS) Card
        self.card_sys = SparkleInfoCard(
            title="System",
            subtitle="OS Information",
            bg_color=COLORS["system_bg"],
            fg_color=COLORS["system_fg"],
            icon_symbol="💻"
        )
        self.card_sys.lbl_field1_title.setText("Operating System")
        self.card_sys.lbl_field2_title.setText("Version")
        self.card_sys.gauge.setVisible(False) # System card has no gauge in Sparkle
        grid.addWidget(self.card_sys, 1, 0)

        # 5. Storage Card
        self.card_disk = SparkleInfoCard(
            title="Storage",
            subtitle="Disk Information",
            bg_color=COLORS["storage_bg"],
            fg_color=COLORS["storage_fg"],
            icon_symbol="💾"
        )
        self.card_disk.lbl_field1_title.setText("Primary Disk")
        self.card_disk.lbl_field2_title.setText("Total Space")
        grid.addWidget(self.card_disk, 1, 1)

        # 6. Tweaks / Game Booster Card
        self.card_tweaks = SparkleInfoCard(
            title="Optimization Tweaks",
            subtitle="Sparkle / RyTuneX / Winhance",
            bg_color=COLORS["tweaks_bg"],
            fg_color=COLORS["tweaks_fg"],
            icon_symbol="🚀"
        )
        self.card_tweaks.lbl_field1_title.setText("Applied Tweaks")
        self.card_tweaks.lbl_field2_title.setText("Game Watcher")
        self.card_tweaks.gauge.setVisible(False)

        self.btn_open_tweaks = AnimatedButton("⚡ Open Tweaks", variant="secondary", compact=True)
        self.btn_open_tweaks.setMinimumWidth(116)
        self.btn_open_tweaks.setFixedHeight(28)
        self.btn_open_tweaks.clicked.connect(lambda: self.navigate_to_page.emit(2))
        tw_row = QHBoxLayout()
        tw_row.addWidget(self.btn_open_tweaks)
        tw_row.addStretch()
        self.card_tweaks.meta_layout.addSpacing(6)
        self.card_tweaks.meta_layout.addLayout(tw_row)
        grid.addWidget(self.card_tweaks, 1, 2)
        self._tweaks_summary_str = "0 / 22 Applied"
        self.refresh_tweaks_summary()

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        layout.addLayout(grid)

        # ---------------- BOTTOM BANNER ----------------
        # Matches Sparkle bottom banner with rounded green icon & action button
        bot_banner = QFrame()
        bot_banner.setObjectName("BottomBanner")
        bot_banner.setFixedHeight(68)
        bot_banner.setStyleSheet(f"""
            QFrame#BottomBanner {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 14px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        bb_layout = QHBoxLayout(bot_banner)
        bb_layout.setContentsMargins(18, 10, 18, 10)
        bb_layout.setSpacing(14)

        # Icon container
        icon_cont = QFrame()
        icon_cont.setObjectName("BannerIconCont")
        icon_cont.setFixedSize(38, 38)
        icon_cont.setStyleSheet(f"""
            QFrame#BannerIconCont {{
                background-color: {COLORS['tweaks_bg']};
                border-radius: 10px;
                border: none;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        ic_lay = QVBoxLayout(icon_cont)
        ic_lay.setContentsMargins(0, 0, 0, 0)
        lbl_b_ic = QLabel("⚡")
        lbl_b_ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_b_ic.setStyleSheet(f"font-size: 18px; color: {COLORS['tweaks_fg']};")
        ic_lay.addWidget(lbl_b_ic)
        bb_layout.addWidget(icon_cont)

        # Text
        txt_box = QVBoxLayout()
        txt_box.setSpacing(2)
        lbl_q = QLabel("PC Running slow?")
        lbl_q.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {COLORS['text_primary']};")
        lbl_hint = QLabel("Try using Game Booster and Deep RAM Clean to improve system performance and privacy.")
        lbl_hint.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']};")
        txt_box.addWidget(lbl_q)
        txt_box.addWidget(lbl_hint)
        bb_layout.addLayout(txt_box, 1)

        # Action Buttons
        self.btn_boost_now = AnimatedButton("⚡ Boost Gaming Now", variant="primary")
        self.btn_boost_now.setFixedHeight(36)
        self.btn_boost_now.clicked.connect(self._on_boost_now_clicked)
        bb_layout.addWidget(self.btn_boost_now)

        self.btn_go_tweaks = AnimatedButton("Visit Game Booster", variant="secondary")
        self.btn_go_tweaks.setFixedHeight(36)
        self.btn_go_tweaks.clicked.connect(lambda: self.navigate_to_page.emit(1))
        bb_layout.addWidget(self.btn_go_tweaks)

        layout.addWidget(bot_banner)
        layout.addStretch(1)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _on_quick_clear_ram_clicked(self, mode: str = "industrial"):
        target_btn = self.btn_deep_ram if mode == "industrial" else self.btn_quick_ram
        orig_text = "🚀 Deep" if mode == "industrial" else "⚡ Quick"

        res = SystemOptimizer.clean_ram(mode=mode)
        freed = res.get("freed_mb", 0)
        if freed > 0:
            target_btn.setText(f"-{int(freed)}M")
        else:
            target_btn.setText("✓ Done")
        self.update_telemetry()
        self.stats_updated.emit()
        QTimer.singleShot(2500, lambda: target_btn.setText(orig_text))

    def update_telemetry(self):
        # 1. CPU
        cpu = HardwareEngine.get_cpu_info()
        self.card_cpu.lbl_field1_val.setText(cpu["name"])
        self.card_cpu.lbl_field2_val.setText(f"{cpu['physical_cores']} Cores ({cpu['logical_cores']} Threads)")
        self.card_cpu.gauge.set_value(cpu["usage_percent"])
        self.spark_cpu.push_value(cpu["usage_percent"])

        # 2. GPU
        gpus = HardwareEngine.get_gpu_info()
        if gpus:
            g = gpus[0]
            self.card_gpu.lbl_field1_val.setText(g["name"])
            self.card_gpu.lbl_field2_val.setText(g.get("type_label", "Dedicated GPU"))
            gpu_pct = g.get("usage_percent") or 0
            self.card_gpu.gauge.set_value(gpu_pct)
            self.spark_gpu.push_value(gpu_pct)

            temp_c = g.get("temperature_c")
            v_used = g.get("vram_used_mb")
            v_total = g.get("vram_total_mb")
            if temp_c is not None and v_used is not None and v_total:
                temp_color = COLORS["danger"] if temp_c >= 80 else (COLORS["warning"] if temp_c >= 68 else COLORS["gpu_fg"])
                self.lbl_gpu_temp.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {temp_color};")
                self.lbl_gpu_temp.setText(f"🌡️ {temp_c}°C  •  {v_used / 1024:.1f} / {v_total / 1024:.1f} GB VRAM")
            elif temp_c is not None:
                self.lbl_gpu_temp.setText(f"🌡️ {temp_c}°C")
            else:
                self.lbl_gpu_temp.setText("🌡️ Sensor requires Admin / NVIDIA")
        else:
            self.card_gpu.lbl_field1_val.setText("Intel(R) UHD Graphics")
            self.card_gpu.lbl_field2_val.setText("Integrated Graphics")
            self.card_gpu.gauge.set_value(0)
            self.spark_gpu.push_value(0)
            self.lbl_gpu_temp.setText("🌡️ Integrated GPU")

        # 3. RAM
        ram = HardwareEngine.get_ram_info()
        self.card_ram.lbl_field1_val.setText(f"{ram['total_gb']} GB")
        self.card_ram.lbl_field2_val.setText(ram.get("type_str", "DDR4 High Speed"))
        self.card_ram.gauge.set_value(ram["percent"])
        self.spark_ram.push_value(ram["percent"])

        # 4. System (OS)
        os_info = HardwareEngine.get_os_info()
        self.card_sys.lbl_field1_val.setText(os_info["name"])
        self.card_sys.lbl_field2_val.setText(os_info["version"])

        # 5. Storage (Disk)
        disks = HardwareEngine.get_disks_info()
        if disks:
            d = disks[0]
            self.card_disk.lbl_field1_val.setText(d.get("model", "Primary Solid State Drive"))
            self.card_disk.lbl_field2_val.setText(f"{d['total_gb']} GB ({d['free_gb']} GB Free)")
            self.card_disk.gauge.set_value(d["percent"])

        # 6. Tweaks / Booster
        self.card_tweaks.lbl_field1_val.setText(self._tweaks_summary_str)
        self.card_tweaks.lbl_field2_val.setText("Auto-Detect Active (250 ms)")

    def refresh_tweaks_summary(self):
        try:
            stats = TweaksEngine.get_summary_stats()
            self._tweaks_summary_str = f"{stats['applied']} / {stats['total']} Active"
            self.card_tweaks.lbl_field1_val.setText(self._tweaks_summary_str)
        except Exception:
            pass

    def _on_boost_now_clicked(self):
        res_ram = SystemOptimizer.clean_ram()
        SystemOptimizer.flush_dns()
        self.update_telemetry()
        self.stats_updated.emit()
        self.btn_boost_now.setText("✓ System Boosted!")
        QTimer.singleShot(2500, lambda: self.btn_boost_now.setText("⚡ Boost Gaming Now"))
