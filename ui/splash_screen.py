import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF
from PyQt6.QtGui import QColor, QFont, QPixmap, QPainter, QPainterPath
from ui.styles import COLORS


def _load_rounded_logo(size: int) -> QPixmap:
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

class SplashScreen(QWidget):
    """
    Modern startup splash screen with logo, animated progress bar,
    and step-by-step loading status indicators.
    """
    loading_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(520, 320)

        # Center on primary screen
        screen_geo = self.screen().geometry()
        x = (screen_geo.width() - self.width()) // 2
        y = (screen_geo.height() - self.height()) // 2
        self.move(x, y)

        self.current_step = 0
        self.loading_steps = [
            (15, "⚡ Initializing hardware telemetry engine..."),
            (35, "🎮 Scanning Steam, Riot & installed game libraries..."),
            (60, "🚀 Discovering startup applications & boot services..."),
            (85, "🎯 Preparing 250ms Auto-Killer loop & blacklist rules..."),
            (100, "✓ Ready! Starting WinGame...")
        ]

        self._setup_ui()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)

        # Main Card Container with soft drop shadow
        card = QFrame()
        card.setObjectName("SplashCard")
        card.setStyleSheet(f"""
            QFrame#SplashCard {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 20px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(15, 23, 42, 40))
        shadow.setOffset(0, 10)
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(36, 32, 36, 28)
        layout.setSpacing(12)

        # Top Logo + Title
        logo_row = QHBoxLayout()
        logo_row.setSpacing(14)
        logo_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Real WinGame Logo
        logo_pm = _load_rounded_logo(68)
        if not logo_pm.isNull():
            lbl_logo = QLabel()
            lbl_logo.setFixedSize(68, 68)
            lbl_logo.setPixmap(logo_pm)
            logo_row.addWidget(lbl_logo)
        else:
            icon_box = QFrame()
            icon_box.setFixedSize(54, 54)
            icon_box.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['primary_light']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 14px;
                }}
            """)
            ib_layout = QVBoxLayout(icon_box)
            ib_layout.setContentsMargins(0, 0, 0, 0)
            lbl_sparkle = QLabel("✦")
            lbl_sparkle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_sparkle.setStyleSheet(f"font-size: 26px; color: {COLORS['primary']}; font-weight: 900;")
            ib_layout.addWidget(lbl_sparkle)
            logo_row.addWidget(icon_box)

        # Title + Beta
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        t_row = QHBoxLayout()
        t_row.setSpacing(8)
        lbl_name = QLabel("WinGame")
        lbl_name.setStyleSheet(f"font-size: 28px; font-weight: 900; color: {COLORS['text_primary']}; letter-spacing: -0.5px;")
        t_row.addWidget(lbl_name)

        lbl_beta = QLabel("Beta")
        lbl_beta.setStyleSheet(f"""
            background-color: {COLORS['primary_light']};
            color: {COLORS['primary']};
            border: 1px solid {COLORS['border']};
            border-radius: 10px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 800;
        """)
        t_row.addWidget(lbl_beta)
        t_row.addStretch()
        title_box.addLayout(t_row)

        lbl_sub = QLabel("Gaming & Hardware Performance Optimizer")
        lbl_sub.setStyleSheet(f"font-size: 13px; color: {COLORS['text_secondary']}; font-weight: 500;")
        title_box.addWidget(lbl_sub)

        logo_row.addLayout(title_box)
        layout.addLayout(logo_row)

        layout.addStretch()

        # Status text
        self.lbl_status = QLabel("Starting initialization...")
        self.lbl_status.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {COLORS['text_primary']};")
        layout.addWidget(self.lbl_status)

        # Modern Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['border']};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLORS['primary']}, stop:1 #3B82F6);
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.progress_bar)

        # Footer row with version & loading %
        foot_row = QHBoxLayout()
        lbl_foot = QLabel("Engine BETA-0.16A • Continuous 250ms Loop")
        lbl_foot.setStyleSheet(f"font-size: 10px; color: {COLORS['text_muted']}; font-weight: 600;")
        foot_row.addWidget(lbl_foot)
        foot_row.addStretch()

        self.lbl_pct = QLabel("0%")
        self.lbl_pct.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLORS['primary']};")
        foot_row.addWidget(self.lbl_pct)
        layout.addLayout(foot_row)

        root_layout.addWidget(card)

    def start_animation(self, on_finish_callback=None):
        if on_finish_callback:
            self.loading_finished.connect(on_finish_callback)

        self.step_idx = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance_progress)
        self.timer.start(140)

    def _advance_progress(self):
        if self.step_idx < len(self.loading_steps):
            target_pct, message = self.loading_steps[self.step_idx]
            current_pct = self.progress_bar.value()

            if current_pct < target_pct:
                new_pct = min(target_pct, current_pct + 4)
                self.progress_bar.setValue(new_pct)
                self.lbl_pct.setText(f"{new_pct}%")
                self.lbl_status.setText(message)
            else:
                self.step_idx += 1
        else:
            self.timer.stop()
            self.progress_bar.setValue(100)
            self.lbl_pct.setText("100%")
            self.lbl_status.setText("✓ Ready! Starting WinGame...")
            # Short delay to show 100% then finish
            QTimer.singleShot(250, self._on_complete)

    def _on_complete(self):
        self.loading_finished.emit()
        self.close()
