import sys
import os
import ctypes

# Add current workspace directory to python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _ensure_admin_privileges():
    """Relaunches WinGame with Administrator privileges (required for full WinMemoryCleaner kernel RAM purge)."""
    if "--no-uac" in sys.argv:
        return
    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            return
        extra_args = " ".join(f'"{a}"' if " " in a else a for a in sys.argv[1:])
        if getattr(sys, "frozen", False):
            exe = sys.executable
            params = extra_args
        else:
            script = os.path.abspath(sys.argv[0])
            params = f'"{script}" {extra_args}'.strip()
            exe = sys.executable
            if exe.lower().endswith("python.exe"):
                pythonw = exe[:-10] + "pythonw.exe"
                if os.path.exists(pythonw):
                    exe = pythonw
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
        if ret > 32:
            sys.exit(0)
    except Exception:
        pass


_ensure_admin_privileges()

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.splash_screen import SplashScreen
from ui.main_window import MainWindow

def main():
    # Ensure Windows Taskbar displays WinGame's custom logo instead of Python's icon
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("WinGame.Optimizer.App")
    except Exception:
        pass

    # Enable High DPI scaling
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("WinGame")
    app.setOrganizationName("WinGame")

    # If launched with --minimized (e.g. from Windows boot startup), run silently in tray
    if "--minimized" in sys.argv:
        window = MainWindow()
        sys.exit(app.exec())

    # If user opted to skip the startup splash animation in Settings
    from config import ConfigManager
    if ConfigManager().get("skip_splash", False):
        window = MainWindow()
        window.show()
        sys.exit(app.exec())

    # 1. Instantiate and display modern animated splash screen
    splash = SplashScreen()
    splash.show()

    # Hold reference to prevent garbage collection
    container = {}

    def on_loading_finished():
        window = MainWindow()
        container["window"] = window
        window.show()

    splash.start_animation(on_finish_callback=on_loading_finished)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
