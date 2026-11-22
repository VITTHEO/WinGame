# WinGame Multi-Theme Engine & Dynamic Stylesheets
from config import ConfigManager

THEMES = {
    "sparkle_light": {
        "name": "Sparkle Light",
        "emoji": "☀️",
        "desc": "Clean & bright",
        "is_dark": False,
        "bg_main": "#F8FAFC",
        "bg_secondary": "#FFFFFF",
        "bg_card": "#FFFFFF",
        "bg_card_hover": "#F1F5F9",
        "bg_input": "#FFFFFF",
        "bg_table_header": "#F8FAFC",
        "border": "#E2E8F0",
        "border_focus": "#3B82F6",
        "scrollbar": "#CBD5E1",
        "scrollbar_hover": "#94A3B8",

        "text_primary": "#0F172A",
        "text_secondary": "#64748B",
        "text_muted": "#94A3B8",
        "text_gradient_green": "#059669",

        "primary": "#2563EB",
        "primary_hover": "#1D4ED8",
        "primary_pressed": "#1E40AF",
        "primary_light": "#EFF6FF",
        "accent_cyan": "#0D9488",

        "cpu_bg": "#E0F2FE",
        "cpu_fg": "#0284C7",
        "gpu_bg": "#CCFBF1",
        "gpu_fg": "#0D9488",
        "ram_bg": "#F3E8FF",
        "ram_fg": "#9333EA",
        "system_bg": "#FFE4E6",
        "system_fg": "#E11D48",
        "storage_bg": "#FFEDD5",
        "storage_fg": "#EA580C",
        "tweaks_bg": "#DCFCE7",
        "tweaks_fg": "#16A34A",

        "danger": "#EF4444",
        "danger_hover": "#DC2626",
        "danger_pressed": "#B91C1C",
        "danger_light": "#FEE2E2",

        "success": "#10B981",
        "success_hover": "#059669",
        "warning": "#F59E0B",
    },
    "midnight_dark": {
        "name": "Midnight Dark",
        "emoji": "🌙",
        "desc": "Deep slate & blue",
        "is_dark": True,
        "bg_main": "#0B1120",
        "bg_secondary": "#111827",
        "bg_card": "#111827",
        "bg_card_hover": "#1E293B",
        "bg_input": "#1E293B",
        "bg_table_header": "#0F172A",
        "border": "#1F2937",
        "border_focus": "#3B82F6",
        "scrollbar": "#334155",
        "scrollbar_hover": "#475569",

        "text_primary": "#F1F5F9",
        "text_secondary": "#94A3B8",
        "text_muted": "#64748B",
        "text_gradient_green": "#34D399",

        "primary": "#3B82F6",
        "primary_hover": "#2563EB",
        "primary_pressed": "#1D4ED8",
        "primary_light": "#1E3A5F",
        "accent_cyan": "#14B8A6",

        "cpu_bg": "#0C2D48",
        "cpu_fg": "#38BDF8",
        "gpu_bg": "#0D3331",
        "gpu_fg": "#2DD4BF",
        "ram_bg": "#2E1065",
        "ram_fg": "#C084FC",
        "system_bg": "#4C0519",
        "system_fg": "#FB7185",
        "storage_bg": "#431407",
        "storage_fg": "#FB923C",
        "tweaks_bg": "#052E16",
        "tweaks_fg": "#4ADE80",

        "danger": "#EF4444",
        "danger_hover": "#DC2626",
        "danger_pressed": "#B91C1C",
        "danger_light": "#450A0A",

        "success": "#10B981",
        "success_hover": "#059669",
        "warning": "#F59E0B",
    },
    "cyber_neon": {
        "name": "Cyber Neon",
        "emoji": "⚡",
        "desc": "Gaming violet",
        "is_dark": True,
        "bg_main": "#09090B",
        "bg_secondary": "#13131A",
        "bg_card": "#13131A",
        "bg_card_hover": "#1E1E2A",
        "bg_input": "#1A1A24",
        "bg_table_header": "#0F0F16",
        "border": "#27273A",
        "border_focus": "#8B5CF6",
        "scrollbar": "#3F3F56",
        "scrollbar_hover": "#5B5B7A",

        "text_primary": "#F8FAFC",
        "text_secondary": "#A1A1AA",
        "text_muted": "#71717A",
        "text_gradient_green": "#A78BFA",

        "primary": "#8B5CF6",
        "primary_hover": "#7C3AED",
        "primary_pressed": "#6D28D9",
        "primary_light": "#2E1065",
        "accent_cyan": "#06B6D4",

        "cpu_bg": "#172554",
        "cpu_fg": "#60A5FA",
        "gpu_bg": "#083344",
        "gpu_fg": "#22D3EE",
        "ram_bg": "#3B0764",
        "ram_fg": "#D8B4FE",
        "system_bg": "#500724",
        "system_fg": "#F472B6",
        "storage_bg": "#451A03",
        "storage_fg": "#FBBF24",
        "tweaks_bg": "#064E3B",
        "tweaks_fg": "#34D399",

        "danger": "#F43F5E",
        "danger_hover": "#E11D48",
        "danger_pressed": "#BE123C",
        "danger_light": "#4C0519",

        "success": "#10B981",
        "success_hover": "#059669",
        "warning": "#F59E0B",
    },
    "emerald_pro": {
        "name": "Emerald Pro",
        "emoji": "🌲",
        "desc": "Fresh & crisp",
        "is_dark": False,
        "bg_main": "#F0FDF4",
        "bg_secondary": "#FFFFFF",
        "bg_card": "#FFFFFF",
        "bg_card_hover": "#ECFDF5",
        "bg_input": "#FFFFFF",
        "bg_table_header": "#F0FDF4",
        "border": "#D1FAE5",
        "border_focus": "#059669",
        "scrollbar": "#A7F3D0",
        "scrollbar_hover": "#6EE7B7",

        "text_primary": "#064E3B",
        "text_secondary": "#475569",
        "text_muted": "#94A3B8",
        "text_gradient_green": "#059669",

        "primary": "#059669",
        "primary_hover": "#047857",
        "primary_pressed": "#065F46",
        "primary_light": "#D1FAE5",
        "accent_cyan": "#0D9488",

        "cpu_bg": "#E0F2FE",
        "cpu_fg": "#0284C7",
        "gpu_bg": "#CCFBF1",
        "gpu_fg": "#0D9488",
        "ram_bg": "#F3E8FF",
        "ram_fg": "#9333EA",
        "system_bg": "#FFE4E6",
        "system_fg": "#E11D48",
        "storage_bg": "#FFEDD5",
        "storage_fg": "#EA580C",
        "tweaks_bg": "#DCFCE7",
        "tweaks_fg": "#16A34A",

        "danger": "#EF4444",
        "danger_hover": "#DC2626",
        "danger_pressed": "#B91C1C",
        "danger_light": "#FEE2E2",

        "success": "#10B981",
        "success_hover": "#059669",
        "warning": "#F59E0B",
    },
    "crimson_esports": {
        "name": "Crimson Esports",
        "emoji": "🔥",
        "desc": "Obsidian & red",
        "is_dark": True,
        "bg_main": "#0F0A0C",
        "bg_secondary": "#1A1215",
        "bg_card": "#1A1215",
        "bg_card_hover": "#26191E",
        "bg_input": "#24181D",
        "bg_table_header": "#140D10",
        "border": "#332026",
        "border_focus": "#EF4444",
        "scrollbar": "#4A2C35",
        "scrollbar_hover": "#693E4B",

        "text_primary": "#FAF5F6",
        "text_secondary": "#B49CA3",
        "text_muted": "#7D656C",
        "text_gradient_green": "#F87171",

        "primary": "#EF4444",
        "primary_hover": "#DC2626",
        "primary_pressed": "#B91C1C",
        "primary_light": "#450A0A",
        "accent_cyan": "#F97316",

        "cpu_bg": "#1E293B",
        "cpu_fg": "#38BDF8",
        "gpu_bg": "#451A03",
        "gpu_fg": "#FB923C",
        "ram_bg": "#3B0764",
        "ram_fg": "#E879F9",
        "system_bg": "#450A0A",
        "system_fg": "#F87171",
        "storage_bg": "#431407",
        "storage_fg": "#FBBF24",
        "tweaks_bg": "#052E16",
        "tweaks_fg": "#4ADE80",

        "danger": "#F43F5E",
        "danger_hover": "#E11D48",
        "danger_pressed": "#BE123C",
        "danger_light": "#4C0519",

        "success": "#10B981",
        "success_hover": "#059669",
        "warning": "#F59E0B",
    },
}

# Active palette dict (mutated in-place when switching themes so all imports stay synced)
_initial_theme = ConfigManager().get("theme", "sparkle_light")
if _initial_theme not in THEMES:
    _initial_theme = "sparkle_light"

COLORS = dict(THEMES[_initial_theme])


def get_current_theme_id() -> str:
    t = ConfigManager().get("theme", "sparkle_light")
    return t if t in THEMES else "sparkle_light"


def apply_theme(theme_id: str) -> str:
    """Updates COLORS in-place and returns the regenerated global stylesheet."""
    if theme_id not in THEMES:
        theme_id = "sparkle_light"
    COLORS.clear()
    COLORS.update(THEMES[theme_id])
    global MAIN_STYLESHEET
    MAIN_STYLESHEET = get_stylesheet()
    return MAIN_STYLESHEET


def get_stylesheet() -> str:
    return f"""
QMainWindow, QDialog {{
    background-color: {COLORS['bg_main']};
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
}}

QWidget {{
    color: {COLORS['text_primary']};
    font-size: 13px;
}}

QLabel {{
    border: none;
    background: transparent;
}}

QFrame {{
    border: none;
}}

QMessageBox {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
}}

QMessageBox QLabel {{
    color: {COLORS['text_primary']};
}}

QMessageBox QPushButton {{
    background-color: {COLORS['primary']};
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: 600;
    min-width: 72px;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['scrollbar']};
    min-height: 24px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS['scrollbar_hover']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 0px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {COLORS['scrollbar']};
    min-width: 24px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {COLORS['scrollbar_hover']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Tables */
QTableWidget {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    gridline-color: transparent;
    outline: none;
    selection-background-color: {COLORS['primary_light']};
    selection-color: {COLORS['primary']};
}}

QTableWidget::item {{
    padding: 10px 14px;
    border-bottom: 1px solid {COLORS['border']};
    color: {COLORS['text_primary']};
}}

QTableWidget::item:hover {{
    background-color: {COLORS['bg_card_hover']};
}}

QTableWidget::item:selected {{
    background-color: {COLORS['primary_light']};
    color: {COLORS['primary']};
    font-weight: 600;
}}

QHeaderView::section {{
    background-color: {COLORS['bg_table_header']};
    color: {COLORS['text_secondary']};
    padding: 10px 14px;
    border: none;
    border-bottom: 1px solid {COLORS['border']};
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* Inputs */
QLineEdit {{
    background-color: {COLORS['bg_input']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px 14px;
    color: {COLORS['text_primary']};
    font-size: 13px;
}}

QLineEdit:focus {{
    border: 1px solid {COLORS['primary']};
    background-color: {COLORS['bg_input']};
}}

QSpinBox {{
    background-color: {COLORS['bg_input']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 6px 10px;
    color: {COLORS['text_primary']};
    font-size: 13px;
}}

QSpinBox:focus {{
    border: 1px solid {COLORS['primary']};
}}

QComboBox {{
    background-color: {COLORS['bg_input']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 6px 14px;
    color: {COLORS['text_primary']};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['primary_light']};
    selection-color: {COLORS['primary']};
    color: {COLORS['text_primary']};
    border-radius: 8px;
    padding: 4px;
}}

QToolTip {{
    background-color: #1E293B;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}
"""


MAIN_STYLESHEET = get_stylesheet()
