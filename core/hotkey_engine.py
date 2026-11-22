"""
Windows Native Global Hotkey Engine (zero external dependencies).
Uses user32.RegisterHotKey + PyQt6 QAbstractNativeEventFilter (WM_HOTKEY = 0x0312).
"""

import ctypes
from ctypes import wintypes
from PyQt6.QtCore import QAbstractNativeEventFilter, QObject, pyqtSignal


WM_HOTKEY = 0x0312

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
_user32.RegisterHotKey.restype = wintypes.BOOL
_user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.UnregisterHotKey.restype = wintypes.BOOL


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


class GlobalHotkeyManager(QObject, QAbstractNativeEventFilter):
    """
    Listens for system-wide Windows hotkeys even when WinGame is minimized to tray
    or while gaming.
    """
    hotkey_triggered = pyqtSignal(str)  # action_name: 'deep_ram' | 'quick_ram' | 'toggle_killer'

    HOTKEY_DEFS = [
        (101, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, ord("R"), "deep_ram", "Ctrl + Shift + R"),
        (102, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, ord("Q"), "quick_ram", "Ctrl + Shift + Q"),
        (103, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, ord("K"), "toggle_killer", "Ctrl + Shift + K"),
    ]

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        QAbstractNativeEventFilter.__init__(self)
        self._registered_ids = {}
        self._active = False

    def register_all(self) -> int:
        """Registers all configured global hotkeys. Returns count of registered shortcuts."""
        self.unregister_all()
        count = 0
        for hk_id, mods, vk, action, _label in self.HOTKEY_DEFS:
            try:
                if _user32.RegisterHotKey(None, hk_id, mods, vk):
                    self._registered_ids[hk_id] = action
                    count += 1
            except Exception:
                pass
        self._active = count > 0
        return count

    def unregister_all(self):
        for hk_id in list(self._registered_ids.keys()):
            try:
                _user32.UnregisterHotKey(None, hk_id)
            except Exception:
                pass
        self._registered_ids.clear()
        self._active = False

    def is_active(self) -> bool:
        return self._active

    def nativeEventFilter(self, eventType, message):
        try:
            if eventType in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
                msg = _MSG.from_address(int(message))
                if msg.message == WM_HOTKEY:
                    hk_id = int(msg.wParam)
                    action = self._registered_ids.get(hk_id)
                    if action:
                        self.hotkey_triggered.emit(action)
                        return True, 0
        except Exception:
            pass
        return False, 0
