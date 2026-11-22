from PyQt6.QtWidgets import (
    QPushButton, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QSpinBox, QFrame
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRectF,
    pyqtProperty, QVariantAnimation
)
from PyQt6.QtGui import (
    QColor, QPainter, QBrush, QPen, QFont, QPainterPath, QLinearGradient
)
from ui.styles import COLORS

class CircularGauge(QWidget):
    """
    Sparkle circular donut progress meter ("camembert rond de consommation").
    Draws a smooth circular progress ring with centered percentage and custom colors.
    """
    def __init__(self, value: float = 0.0, accent_color=COLORS["cpu_fg"], parent=None):
        super().__init__(parent)
        self._value = value
        self.accent_color = QColor(accent_color)
        self.track_color = QColor(COLORS["border"])
        self.setFixedSize(68, 68)

    def set_value(self, val: float):
        self._value = max(0.0, min(100.0, float(val)))
        self.update()

    def set_accent_color(self, color_hex: str):
        self.accent_color = QColor(color_hex)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Gauge dimensions
        width = self.width()
        height = self.height()
        pen_width = 7.0
        margin = pen_width / 2.0 + 3.0
        rect = QRectF(margin, margin, width - 2 * margin, height - 2 * margin)

        # 1. Background Track Ring
        bg_pen = QPen(self.track_color, pen_width)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawEllipse(rect)

        # 2. Foreground Active Progress Arc
        if self._value > 0:
            fg_pen = QPen(self.accent_color, pen_width)
            fg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(fg_pen)
            
            # Start angle at 90 degrees (top), span clockwise
            start_angle = 90 * 16
            span_angle = -int((self._value / 100.0) * 360.0 * 16)
            painter.drawArc(rect, start_angle, span_angle)

        # 3. Center Percentage Text
        painter.setPen(QColor(COLORS["text_primary"]))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        text = f"{int(self._value)}%"
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)


class AnimatedButton(QPushButton):
    """
    Sparkle styled button with smooth color transition animations.
    """
    def __init__(self, text: str, variant="primary", parent=None, compact: bool = False):
        super().__init__(text, parent)
        self.variant = variant
        self.compact = compact
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 9 if compact else 10, QFont.Weight.DemiBold))
        
        if variant == "primary":
            self.base_color = QColor(COLORS["primary"])
            self.hover_color = QColor(COLORS["primary_hover"])
            self.pressed_color = QColor("#1E40AF")
            self.text_color = QColor("#FFFFFF")
            self.border_color = "transparent"
        elif variant == "danger":
            self.base_color = QColor(COLORS["danger"])
            self.hover_color = QColor(COLORS["danger_hover"])
            self.pressed_color = QColor("#B91C1C")
            self.text_color = QColor("#FFFFFF")
            self.border_color = "transparent"
        elif variant == "secondary":
            self.base_color = QColor(COLORS["bg_card"])
            self.hover_color = QColor(COLORS["bg_card_hover"])
            self.pressed_color = QColor(COLORS["border"])
            self.text_color = QColor(COLORS["text_primary"])
            self.border_color = COLORS["border"]
        else:
            self.base_color = QColor(COLORS["bg_card"])
            self.hover_color = QColor(COLORS["bg_card_hover"])
            self.pressed_color = QColor(COLORS["border"])
            self.text_color = QColor(COLORS["text_primary"])
            self.border_color = COLORS["border"]

        self._current_bg = self.base_color

        self.anim = QVariantAnimation(self)
        self.anim.setDuration(160)
        self.anim.valueChanged.connect(self._on_anim_value_changed)

        self.setFixedHeight(28 if compact else 38)
        self._update_style()

    def _on_anim_value_changed(self, color: QColor):
        self._current_bg = color
        self._update_style()

    def _update_style(self):
        pad = "2px 10px" if self.compact else "6px 16px"
        radius = "7px" if self.compact else "8px"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._current_bg.name()};
                color: {self.text_color.name()};
                border: 1px solid {self.border_color};
                border-radius: {radius};
                padding: {pad};
                font-weight: 600;
            }}
        """)

    def enterEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._current_bg)
        self.anim.setEndValue(self.hover_color)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._current_bg)
        self.anim.setEndValue(self.base_color)
        self.anim.start()
        super().leaveEvent(event)


class AnimatedToggleSwitch(QWidget):
    """
    Sparkle modern sliding toggle switch.
    """
    toggled = pyqtSignal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(50, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._thumb_position = 26.0 if checked else 3.0

        self.anim = QPropertyAnimation(self, b"thumb_position", self)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.anim.setDuration(160)

    @pyqtProperty(float)
    def thumb_position(self):
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, pos):
        self._thumb_position = pos
        self.update()

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self.anim.stop()
            self.anim.setStartValue(self._thumb_position)
            self.anim.setEndValue(26.0 if checked else 3.0)
            self.anim.start()
            self.toggled.emit(checked)
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        track_color = QColor(COLORS["primary"]) if self._checked else QColor(COLORS["scrollbar"])
        painter.setBrush(QBrush(track_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 13, 13)

        painter.setBrush(QBrush(QColor("#FFFFFF")))
        thumb_rect = QRectF(self._thumb_position, 3.0, 20.0, 20.0)
        painter.drawEllipse(thumb_rect)


class ModernIntervalStepper(QFrame):
    """
    Modern interval selector with styled [+] and [-] action buttons
    and a wide, centered numeric field.
    """
    valueChanged = pyqtSignal(int)

    def __init__(self, value=250, min_val=50, max_val=10000, step=50, parent=None):
        super().__init__(parent)
        self.step = step
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border-color: {COLORS['primary']};
            }}
        """)
        self.setFixedSize(140, 34)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 2, 3, 2)
        layout.setSpacing(2)

        btn_style = f"""
            QPushButton {{
                background-color: {COLORS['bg_card_hover']};
                color: {COLORS['primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                font-size: 16px;
                font-weight: 900;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary_light']};
                border-color: {COLORS['primary']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['border']};
            }}
        """

        # Minus button
        self.btn_minus = QPushButton("−")
        self.btn_minus.setFixedSize(28, 28)
        self.btn_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_minus.setStyleSheet(btn_style)
        self.btn_minus.clicked.connect(self._decrement)
        layout.addWidget(self.btn_minus)

        # Value SpinBox (clean, borderless, centered)
        self.spin = QSpinBox()
        self.spin.setRange(min_val, max_val)
        self.spin.setSingleStep(step)
        self.spin.setValue(value)
        self.spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.spin.setStyleSheet(f"""
            QSpinBox {{
                border: none;
                background: transparent;
                color: {COLORS['text_primary']};
                font-size: 13px;
                font-weight: 800;
            }}
        """)
        self.spin.valueChanged.connect(self.valueChanged.emit)
        layout.addWidget(self.spin, 1)

        # Plus button
        self.btn_plus = QPushButton("+")
        self.btn_plus.setFixedSize(28, 28)
        self.btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_plus.setStyleSheet(btn_style)
        self.btn_plus.clicked.connect(self._increment)
        layout.addWidget(self.btn_plus)

    def _decrement(self):
        self.spin.setValue(max(self.spin.minimum(), self.spin.value() - self.step))

    def _increment(self):
        self.spin.setValue(min(self.spin.maximum(), self.spin.value() + self.step))

    def value(self) -> int:
        return self.spin.value()

    def setValue(self, val: int):
        self.spin.setValue(val)


class LiveSparklineWidget(QWidget):
    """
    Smooth real-time mini history area chart (last ~60s of CPU / GPU / RAM load).
    """
    def __init__(self, accent_color: str = COLORS["cpu_fg"], max_points: int = 40, parent=None):
        super().__init__(parent)
        self.accent_color = QColor(accent_color)
        self.max_points = max_points
        self._data = [0.0] * 12
        self.setFixedHeight(32)
        self.setMinimumWidth(90)

    def push_value(self, val: float):
        clamped = max(0.0, min(100.0, float(val)))
        self._data.append(clamped)
        if len(self._data) > self.max_points:
            self._data.pop(0)
        self.update()

    def paintEvent(self, event):
        if len(self._data) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        pad_x = 3.0
        pad_y = 4.0
        usable_w = max(1.0, w - 2 * pad_x)
        usable_h = max(1.0, h - 2 * pad_y)

        # Subtle baseline
        base_pen = QPen(QColor(COLORS["border"]), 1.0)
        painter.setPen(base_pen)
        painter.drawLine(int(pad_x), int(h - pad_y), int(w - pad_x), int(h - pad_y))

        n = len(self._data)
        step_x = usable_w / max(1, n - 1)

        points = []
        for i, v in enumerate(self._data):
            x = pad_x + i * step_x
            y = (h - pad_y) - (v / 100.0) * usable_h
            points.append((x, y))

        # Smooth curve path
        line_path = QPainterPath()
        line_path.moveTo(points[0][0], points[0][1])
        for i in range(1, n):
            px, py = points[i - 1]
            cx, cy = points[i]
            mx = (px + cx) / 2.0
            line_path.cubicTo(mx, py, mx, cy, cx, cy)

        # Gradient fill under curve
        fill_path = QPainterPath(line_path)
        fill_path.lineTo(points[-1][0], h - pad_y)
        fill_path.lineTo(points[0][0], h - pad_y)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, pad_y, 0, h - pad_y)
        c_top = QColor(self.accent_color)
        c_top.setAlpha(60)
        c_bot = QColor(self.accent_color)
        c_bot.setAlpha(5)
        grad.setColorAt(0.0, c_top)
        grad.setColorAt(1.0, c_bot)
        painter.fillPath(fill_path, QBrush(grad))

        # Stroke curve
        pen = QPen(self.accent_color, 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawPath(line_path)

        # Live indicator dot at rightmost point
        lx, ly = points[-1]
        painter.setBrush(QBrush(self.accent_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(lx - 2.6, ly - 2.6, 5.2, 5.2))


