"""
WinGame Windows Optimization Tweaks Engine
Inspired by Sparkle, RyTuneX, and Winhance — 100% safe, live-detected, and reversible.
"""

import winreg
import subprocess
from typing import List, Dict, Any, Tuple, Optional


_HIVE_MAP = {
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
}

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


def _reg_read(hive_name: str, path: str, name: str) -> Optional[Any]:
    hive = _HIVE_MAP[hive_name]
    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, name)
            return val
    except Exception:
        return None


def _reg_key_exists(hive_name: str, path: str) -> bool:
    hive = _HIVE_MAP[hive_name]
    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_READ):
            return True
    except Exception:
        return False


def _reg_write(hive_name: str, path: str, name: str, value: Any, reg_type: int) -> None:
    hive = _HIVE_MAP[hive_name]
    with winreg.CreateKeyEx(hive, path, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, name, 0, reg_type, value)


def _reg_delete_value(hive_name: str, path: str, name: str) -> None:
    hive = _HIVE_MAP[hive_name]
    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, name)
    except FileNotFoundError:
        pass


def _reg_delete_tree(hive_name: str, path: str) -> None:
    hive = _HIVE_MAP[hive_name]
    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_ALL_ACCESS) as key:
            while True:
                try:
                    sub = winreg.EnumKey(key, 0)
                    _reg_delete_tree(hive_name, f"{path}\\{sub}")
                except OSError:
                    break
        winreg.DeleteKey(hive, path)
    except FileNotFoundError:
        pass


def _run_cmd(args: List[str], timeout: float = 8.0) -> Tuple[int, str, str]:
    res = subprocess.run(
        args,
        capture_output=True,
        timeout=timeout,
        creationflags=_NO_WINDOW,
    )
    out = (res.stdout or b"").decode("cp850", errors="replace").strip()
    err = (res.stderr or b"").decode("cp850", errors="replace").strip()
    return res.returncode, out, err


# ==============================================================================
# Tweak Catalog (21 curated tweaks inspired by Sparkle, RyTuneX & Winhance)
# ==============================================================================
# Each reg entry tuple: (hive, path, name, reg_type, on_value, off_value)
#   - off_value == "__DELETE__" deletes the registry value on revert.
TWEAK_CATALOG: List[Dict[str, Any]] = [
    # ---------------- GAMING & PERFORMANCE ----------------
    {
        "id": "ultimate_power_plan",
        "title": "Ultimate Performance Power Plan",
        "desc": "Unlocks and activates Windows' hidden Ultimate Performance scheme to eliminate micro-latencies and CPU parking.",
        "category": "Gaming",
        "icon": "⚡",
        "recommended": True,
        "restart_needed": False,
        "presets": ["gaming"],
        "custom": True,
    },
    {
        "id": "game_mode",
        "title": "Enable Windows Game Mode",
        "desc": "Prioritizes active games, prevents Windows Update driver installs during play, and stabilizes frame pacing.",
        "category": "Gaming",
        "icon": "🎮",
        "recommended": True,
        "restart_needed": False,
        "presets": ["gaming"],
        "regs": [
            ("HKCU", r"Software\Microsoft\GameBar", "AutoGameModeEnabled", winreg.REG_DWORD, 1, 0),
            ("HKCU", r"Software\Microsoft\GameBar", "AllowAutoGameMode", winreg.REG_DWORD, 1, 0),
        ],
    },
    {
        "id": "disable_gamedvr",
        "title": "Disable Xbox GameDVR & Capture",
        "desc": "Turns off background Xbox Game Bar video recording that steals GPU encoding power and causes FPS drops.",
        "category": "Gaming",
        "icon": "🎬",
        "recommended": True,
        "restart_needed": False,
        "presets": ["gaming"],
        "regs": [
            ("HKCU", r"System\GameConfigStore", "GameDVR_Enabled", winreg.REG_DWORD, 0, 1),
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", winreg.REG_DWORD, 0, 1),
            ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR", winreg.REG_DWORD, 0, "__DELETE__"),
        ],
    },
    {
        "id": "enable_hags",
        "title": "Hardware-Accelerated GPU Scheduling (HAGS)",
        "desc": "Lets your GPU manage its own VRAM scheduling directly, reducing CPU overhead and enabling DLSS 3 Frame Gen.",
        "category": "Gaming",
        "icon": "🖥",
        "recommended": True,
        "restart_needed": True,
        "presets": ["gaming"],
        "regs": [
            ("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "HwSchMode", winreg.REG_DWORD, 2, 1),
        ],
    },
    {
        "id": "mmcss_gaming",
        "title": "MMCSS High Gaming CPU/GPU Priority",
        "desc": "Sets Windows Multimedia Class Scheduler to High priority and 0% background reserve for lower frametime spikes.",
        "category": "Gaming",
        "icon": "🚀",
        "recommended": True,
        "restart_needed": True,
        "presets": ["gaming"],
        "regs": [
            ("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", "SystemResponsiveness", winreg.REG_DWORD, 0, 20),
            ("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "GPU Priority", winreg.REG_DWORD, 8, 8),
            ("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Priority", winreg.REG_DWORD, 6, 2),
            ("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Scheduling Category", winreg.REG_SZ, "High", "Medium"),
            ("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "SFIO Priority", winreg.REG_SZ, "High", "Normal"),
        ],
    },
    {
        "id": "disable_mouse_accel",
        "title": "Disable Mouse Acceleration (1:1 Raw Aim)",
        "desc": "Turns off Windows 'Enhance pointer precision' for consistent 1:1 raw mouse tracking in FPS games.",
        "category": "Gaming",
        "icon": "🖱️",
        "recommended": True,
        "restart_needed": False,
        "presets": ["gaming"],
        "regs": [
            ("HKCU", r"Control Panel\Mouse", "MouseSpeed", winreg.REG_SZ, "0", "1"),
            ("HKCU", r"Control Panel\Mouse", "MouseThreshold1", winreg.REG_SZ, "0", "6"),
            ("HKCU", r"Control Panel\Mouse", "MouseThreshold2", winreg.REG_SZ, "0", "10"),
        ],
    },
    {
        "id": "disable_fso",
        "title": "Disable Fullscreen Optimizations Globally",
        "desc": "Forces DirectX games to bypass DWM composition in exclusive fullscreen for lower display input latency.",
        "category": "Gaming",
        "icon": "🪟",
        "recommended": False,
        "restart_needed": False,
        "presets": [],
        "regs": [
            ("HKCU", r"System\GameConfigStore", "GameDVR_FSEBehaviorMode", winreg.REG_DWORD, 2, 0),
            ("HKCU", r"System\GameConfigStore", "GameDVR_HonorUserFSEBehaviorMode", winreg.REG_DWORD, 1, 0),
            ("HKCU", r"System\GameConfigStore", "GameDVR_DXGIHonorFSEWindowsCompatible", winreg.REG_DWORD, 1, 0),
        ],
    },

    # ---------------- PRIVACY & DEBLOAT (WINHANCE / RYTUNEX) ----------------
    {
        "id": "disable_telemetry",
        "title": "Disable Windows Telemetry & Diagnostics",
        "desc": "Stops Windows from collecting and uploading diagnostic usage telemetry and tailored experience logs.",
        "category": "Privacy",
        "icon": "🔒",
        "recommended": True,
        "restart_needed": False,
        "presets": ["privacy", "gaming"],
        "regs": [
            ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", winreg.REG_DWORD, 0, "__DELETE__"),
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Privacy", "TailoredExperiencesWithDiagnosticDataEnabled", winreg.REG_DWORD, 0, 1),
        ],
    },
    {
        "id": "disable_ads",
        "title": "Disable Ads, Suggestions & Silent Bloatware",
        "desc": "Turns off Advertising ID, Start Menu suggestions, tips, and automatic silent installation of sponsored apps.",
        "category": "Privacy",
        "icon": "🚫",
        "recommended": True,
        "restart_needed": False,
        "presets": ["privacy"],
        "regs": [
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "Enabled", winreg.REG_DWORD, 0, 1),
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SystemPaneSuggestionsEnabled", winreg.REG_DWORD, 0, 1),
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SilentInstalledAppsEnabled", winreg.REG_DWORD, 0, 1),
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SubscribedContent-338389Enabled", winreg.REG_DWORD, 0, 1),
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SubscribedContent-310093Enabled", winreg.REG_DWORD, 0, 1),
        ],
    },
    {
        "id": "disable_bing_search",
        "title": "Disable Bing Web Search in Start Menu",
        "desc": "Makes Windows Search strictly local and instant by blocking Bing web results and search box suggestions.",
        "category": "Privacy",
        "icon": "🔍",
        "recommended": True,
        "restart_needed": False,
        "presets": ["privacy"],
        "regs": [
            ("HKCU", r"Software\Policies\Microsoft\Windows\Explorer", "DisableSearchBoxSuggestions", winreg.REG_DWORD, 1, 0),
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Search", "BingSearchEnabled", winreg.REG_DWORD, 0, 1),
        ],
    },
    {
        "id": "disable_copilot",
        "title": "Disable Windows Copilot & AI Recall",
        "desc": "Disables the integrated Windows Copilot sidebar and Windows AI Recall snapshot analysis via system policy.",
        "category": "Privacy",
        "icon": "🤖",
        "recommended": False,
        "restart_needed": False,
        "presets": ["privacy"],
        "regs": [
            ("HKCU", r"Software\Policies\Microsoft\Windows\WindowsCopilot", "TurnOffWindowsCopilot", winreg.REG_DWORD, 1, 0),
            ("HKCU", r"Software\Policies\Microsoft\Windows\WindowsAI", "DisableAIDataAnalysis", winreg.REG_DWORD, 1, 0),
        ],
    },
    {
        "id": "disable_bg_apps",
        "title": "Disable UWP Background Apps Globally",
        "desc": "Stops Microsoft Store / UWP apps from silently running, syncing, and consuming RAM & CPU in the background.",
        "category": "Privacy",
        "icon": "💤",
        "recommended": True,
        "restart_needed": False,
        "presets": ["privacy", "gaming"],
        "regs": [
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications", "GlobalUserDisabled", winreg.REG_DWORD, 1, 0),
            ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Search", "BackgroundAppGlobalToggle", winreg.REG_DWORD, 0, 1),
        ],
    },
    {
        "id": "disable_activity_history",
        "title": "Disable Activity History & Cloud Sync",
        "desc": "Prevents Windows from tracking your open apps, documents, and browsing timeline to Microsoft servers.",
        "category": "Privacy",
        "icon": "📜",
        "recommended": True,
        "restart_needed": False,
        "presets": ["privacy"],
        "regs": [
            ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System", "EnableActivityFeed", winreg.REG_DWORD, 0, 1),
            ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System", "PublishUserActivities", winreg.REG_DWORD, 0, 1),
            ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System", "UploadUserActivities", winreg.REG_DWORD, 0, 1),
        ],
    },

    # ---------------- SYSTEM, UI & LATENCY (SPARKLE / WINHANCE) ----------------
    {
        "id": "disable_power_throttling",
        "title": "Disable CPU Power Throttling",
        "desc": "Prevents Windows from aggressively downclocking background/helper threads, reducing sudden game stutters.",
        "category": "System",
        "icon": "🔋",
        "recommended": True,
        "restart_needed": True,
        "presets": ["gaming"],
        "regs": [
            ("HKLM", r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling", "PowerThrottlingOff", winreg.REG_DWORD, 1, 0),
        ],
    },
    {
        "id": "classic_context_menu",
        "title": "Classic Windows 10 Right-Click Menu",
        "desc": "Restores the full, faster classic right-click context menu on Windows 11 without clicking 'Show more options'.",
        "category": "System",
        "icon": "📋",
        "recommended": False,
        "restart_needed": False,
        "presets": [],
        "custom": True,
    },
    {
        "id": "fast_ui_menus",
        "title": "Zero Menu Delay & Faster App Shutdown",
        "desc": "Sets UI menu pop delay to 0 ms and speeds up hung app termination during shutdown or restart.",
        "category": "System",
        "icon": "✨",
        "recommended": True,
        "restart_needed": False,
        "presets": ["gaming"],
        "regs": [
            ("HKCU", r"Control Panel\Desktop", "MenuShowDelay", winreg.REG_SZ, "0", "400"),
            ("HKCU", r"Control Panel\Desktop", "AutoEndTasks", winreg.REG_SZ, "1", "0"),
            ("HKCU", r"Control Panel\Desktop", "HungAppTimeout", winreg.REG_SZ, "2000", "5000"),
            ("HKCU", r"Control Panel\Desktop", "WaitToKillAppTimeout", winreg.REG_SZ, "2000", "20000"),
        ],
    },
    {
        "id": "disable_sticky_keys",
        "title": "Disable Sticky Keys & Filter Keys Popups",
        "desc": "Stops the disruptive 'Sticky Keys' dialog from minimizing your game when pressing Shift 5 times rapidly.",
        "category": "System",
        "icon": "⌨️",
        "recommended": True,
        "restart_needed": False,
        "presets": ["gaming"],
        "regs": [
            ("HKCU", r"Control Panel\Accessibility\StickyKeys", "Flags", winreg.REG_SZ, "506", "510"),
            ("HKCU", r"Control Panel\Accessibility\ToggleKeys", "Flags", winreg.REG_SZ, "58", "62"),
            ("HKCU", r"Control Panel\Accessibility\Keyboard Response", "Flags", winreg.REG_SZ, "122", "126"),
        ],
    },
    {
        "id": "disable_hibernation",
        "title": "Disable Hibernation (Free hiberfil.sys)",
        "desc": "Turns off Windows Hibernation to reclaim 4–12 GB of SSD space occupied by hiberfil.sys (desktop recommended).",
        "category": "System",
        "icon": "💾",
        "recommended": False,
        "restart_needed": False,
        "presets": [],
        "custom": True,
    },
    {
        "id": "disable_ntfs_last_access",
        "title": "Disable NTFS Last-Access Disk Writes",
        "desc": "Stops Windows from writing a timestamp to your SSD every time a file is simply read, lowering disk I/O.",
        "category": "System",
        "icon": "⚡",
        "recommended": True,
        "restart_needed": False,
        "presets": ["gaming"],
        "custom": True,
    },

    # ---------------- NETWORK & PING (SPARKLE / RYTUNEX) ----------------
    {
        "id": "disable_net_throttling",
        "title": "Disable Windows Network Throttling",
        "desc": "Removes Windows' default 10-packets/ms multimedia network throttle for smoother online gaming latency.",
        "category": "Network",
        "icon": "🌐",
        "recommended": True,
        "restart_needed": True,
        "presets": ["gaming"],
        "regs": [
            ("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", "NetworkThrottlingIndex", winreg.REG_DWORD, 0xFFFFFFFF, 10),
        ],
    },
    {
        "id": "tcp_nodelay",
        "title": "Disable Nagle's Algorithm (TCPNoDelay)",
        "desc": "Disables TCP packet buffering (TcpAckFrequency=1, TCPNoDelay=1) on active network adapters for lower game ping.",
        "category": "Network",
        "icon": "📡",
        "recommended": True,
        "restart_needed": True,
        "presets": ["gaming"],
        "custom": True,
    },
    {
        "id": "disable_delivery_opt",
        "title": "Disable Windows Update P2P Bandwidth Sharing",
        "desc": "Blocks Windows Delivery Optimization from uploading updates to other PCs and causing ping spikes in games.",
        "category": "Network",
        "icon": "🛡️",
        "recommended": True,
        "restart_needed": False,
        "presets": ["gaming", "privacy"],
        "regs": [
            ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization", "DODownloadMode", winreg.REG_DWORD, 0, 1),
        ],
    },
]

_TWEAK_BY_ID = {t["id"]: t for t in TWEAK_CATALOG}


class TweaksEngine:
    """Executes, inspects, and reverts Windows Registry & Powercfg optimization tweaks."""

    ULTIMATE_GUID = "e9a42b02-d5df-448d-aa00-03f14749eb61"
    BALANCED_GUID = "381b4222-f694-41f0-9685-ff5bb260df2e"
    CLSID_CONTEXT_PATH = r"Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32"
    CLSID_CONTEXT_ROOT = r"Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}"

    @classmethod
    def get_catalog(cls) -> List[Dict[str, Any]]:
        return TWEAK_CATALOG

    @classmethod
    def is_applied(cls, tweak_id: str) -> bool:
        tweak = _TWEAK_BY_ID.get(tweak_id)
        if not tweak:
            return False

        if tweak.get("custom"):
            return cls._is_custom_applied(tweak_id)

        regs = tweak.get("regs", [])
        if not regs:
            return False

        # Check primary registry value (first entry)
        hive, path, name, _rtype, on_val, _off_val = regs[0]
        cur = _reg_read(hive, path, name)
        if cur is None:
            return False
        if isinstance(on_val, int) and isinstance(cur, int):
            return (cur & 0xFFFFFFFF) == (on_val & 0xFFFFFFFF)
        return str(cur) == str(on_val)

    @classmethod
    def _is_custom_applied(cls, tweak_id: str) -> bool:
        try:
            if tweak_id == "ultimate_power_plan":
                code, out, _ = _run_cmd(["powercfg", "/getactivescheme"], timeout=4.0)
                if code == 0:
                    low = out.lower()
                    return "ultimate" in low or "performances optimales" in low or cls.ULTIMATE_GUID in low
                return False

            if tweak_id == "classic_context_menu":
                return _reg_key_exists("HKCU", cls.CLSID_CONTEXT_PATH)

            if tweak_id == "disable_hibernation":
                val = _reg_read("HKLM", r"SYSTEM\CurrentControlSet\Control\Power", "HibernateEnabled")
                return val == 0

            if tweak_id == "disable_ntfs_last_access":
                val = _reg_read("HKLM", r"SYSTEM\CurrentControlSet\Control\FileSystem", "NtfsDisableLastAccessUpdate")
                if isinstance(val, int):
                    # Low nibble 1 = User Managed Disabled, 3 = System Managed Disabled
                    return (val & 0xF) in (1, 3)
                return False

            if tweak_id == "tcp_nodelay":
                base = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base, 0, winreg.KEY_READ) as key:
                    i = 0
                    while True:
                        try:
                            sub_name = winreg.EnumKey(key, i)
                            i += 1
                            sub_path = f"{base}\\{sub_name}"
                            if _reg_read("HKLM", sub_path, "TCPNoDelay") == 1:
                                return True
                        except OSError:
                            break
                return False
        except Exception:
            return False
        return False

    @classmethod
    def apply_tweak(cls, tweak_id: str, enable: bool) -> Tuple[bool, str]:
        tweak = _TWEAK_BY_ID.get(tweak_id)
        if not tweak:
            return False, f"Unknown tweak: {tweak_id}"

        try:
            if tweak.get("custom"):
                return cls._apply_custom_tweak(tweak_id, enable)

            for hive, path, name, reg_type, on_val, off_val in tweak.get("regs", []):
                if enable:
                    _reg_write(hive, path, name, on_val, reg_type)
                else:
                    if off_val == "__DELETE__":
                        _reg_delete_value(hive, path, name)
                    else:
                        _reg_write(hive, path, name, off_val, reg_type)

            state_txt = "applied" if enable else "reverted to Windows default"
            restart_hint = " (restart recommended)" if tweak.get("restart_needed") else ""
            return True, f"{tweak['title']} {state_txt}{restart_hint}."
        except PermissionError:
            return False, f"Administrator rights required for '{tweak['title']}'."
        except Exception as e:
            return False, f"Failed on '{tweak['title']}': {e}"

    @classmethod
    def _apply_custom_tweak(cls, tweak_id: str, enable: bool) -> Tuple[bool, str]:
        if tweak_id == "ultimate_power_plan":
            if enable:
                # Check if an Ultimate Performance scheme already exists
                code, out, _ = _run_cmd(["powercfg", "/list"])
                target_guid = None
                if code == 0:
                    for line in out.splitlines():
                        low = line.lower()
                        if "ultimate" in low or "performances optimales" in low:
                            parts = line.split()
                            for p in parts:
                                if len(p) == 36 and p.count("-") == 4:
                                    target_guid = p
                                    break
                            if target_guid:
                                break
                if not target_guid:
                    code_d, out_d, err_d = _run_cmd(["powercfg", "-duplicatescheme", cls.ULTIMATE_GUID])
                    if code_d == 0:
                        for p in out_d.split():
                            if len(p) == 36 and p.count("-") == 4:
                                target_guid = p
                                break
                    if not target_guid:
                        target_guid = cls.ULTIMATE_GUID

                c_act, _, err_act = _run_cmd(["powercfg", "/setactive", target_guid])
                if c_act == 0:
                    return True, "Ultimate Performance Power Plan activated!"
                return False, f"Could not activate Ultimate Performance ({err_act or 'Admin required'})."
            else:
                c_bal, _, err_bal = _run_cmd(["powercfg", "/setactive", cls.BALANCED_GUID])
                if c_bal == 0:
                    return True, "Power Plan reverted to Windows Balanced."
                return False, f"Could not restore Balanced plan ({err_bal})."

        if tweak_id == "classic_context_menu":
            if enable:
                _reg_write("HKCU", cls.CLSID_CONTEXT_PATH, "", "", winreg.REG_SZ)
                return True, "Classic Right-Click Menu enabled (restart Explorer to see immediately)."
            else:
                _reg_delete_tree("HKCU", cls.CLSID_CONTEXT_ROOT)
                return True, "Windows 11 modern Right-Click Menu restored."

        if tweak_id == "disable_hibernation":
            arg = "off" if enable else "on"
            code, _, err = _run_cmd(["powercfg", "/h", arg])
            if code == 0:
                return True, f"Windows Hibernation turned {arg.upper()}."
            return False, f"Failed to toggle hibernation ({err or 'Admin required'})."

        if tweak_id == "disable_ntfs_last_access":
            mode = "1" if enable else "0"
            code, _, err = _run_cmd(["fsutil", "behavior", "set", "disablelastaccess", mode])
            if code == 0:
                return True, "NTFS Last-Access writes disabled." if enable else "NTFS Last-Access restored to default."
            return False, f"fsutil failed ({err or 'Admin required'})."

        if tweak_id == "tcp_nodelay":
            base = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
            updated = 0
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        sub_name = winreg.EnumKey(key, i)
                        i += 1
                        sub_path = f"{base}\\{sub_name}"
                        # Target interfaces with an assigned IP or DHCP IP
                        ip = _reg_read("HKLM", sub_path, "DhcpIPAddress") or _reg_read("HKLM", sub_path, "IPAddress")
                        if not ip or ip == "0.0.0.0":
                            continue
                        if enable:
                            _reg_write("HKLM", sub_path, "TcpAckFrequency", 1, winreg.REG_DWORD)
                            _reg_write("HKLM", sub_path, "TCPNoDelay", 1, winreg.REG_DWORD)
                        else:
                            _reg_delete_value("HKLM", sub_path, "TcpAckFrequency")
                            _reg_delete_value("HKLM", sub_path, "TCPNoDelay")
                        updated += 1
                    except OSError:
                        break
            if updated > 0:
                return True, (
                    f"TCPNoDelay / Nagle's Algorithm disabled on {updated} active adapter(s) (restart recommended)."
                    if enable
                    else f"TCPNoDelay reverted on {updated} adapter(s)."
                )
            return False, "No active TCP/IP network interfaces found or Admin required."

        return False, f"Unsupported custom tweak: {tweak_id}"

    @classmethod
    def apply_preset(cls, preset: str) -> Tuple[int, int]:
        """
        Applies a curated preset ('gaming', 'privacy', or 'revert_all').
        Returns (succeeded_count, failed_count).
        """
        ok_cnt = 0
        fail_cnt = 0
        if preset == "revert_all":
            for t in TWEAK_CATALOG:
                if cls.is_applied(t["id"]):
                    ok, _ = cls.apply_tweak(t["id"], False)
                    if ok:
                        ok_cnt += 1
                    else:
                        fail_cnt += 1
            return ok_cnt, fail_cnt

        for t in TWEAK_CATALOG:
            if preset in t.get("presets", []):
                ok, _ = cls.apply_tweak(t["id"], True)
                if ok:
                    ok_cnt += 1
                else:
                    fail_cnt += 1
        return ok_cnt, fail_cnt

    @classmethod
    def create_restore_point(cls) -> Tuple[bool, str]:
        """Creates a real Windows System Restore Point before tweaking."""
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-Command",
                "Checkpoint-Computer -Description 'WinGame Pre-Tweak Backup' -RestorePointType 'MODIFY_SETTINGS'",
            ]
            code, _out, err = _run_cmd(cmd, timeout=30.0)
            if code == 0:
                return True, "Windows System Restore Point 'WinGame Pre-Tweak Backup' created successfully!"
            return False, f"Could not create restore point ({err or 'System Protection may be disabled or Admin required'})."
        except Exception as e:
            return False, f"Restore point error: {e}"

    @classmethod
    def get_summary_stats(cls) -> Dict[str, int]:
        total = len(TWEAK_CATALOG)
        applied = 0
        gaming_applied = 0
        privacy_applied = 0
        for t in TWEAK_CATALOG:
            if cls.is_applied(t["id"]):
                applied += 1
                if t["category"] == "Gaming":
                    gaming_applied += 1
                elif t["category"] == "Privacy":
                    privacy_applied += 1
        return {
            "total": total,
            "applied": applied,
            "gaming_applied": gaming_applied,
            "privacy_applied": privacy_applied,
        }
