import os
import re
import glob
import winreg
import subprocess
from typing import List, Dict, Any, Optional

def extract_clean_path(raw_command: str) -> str:
    """Extracts the actual executable path from a command line string."""
    if not raw_command:
        return ""
    raw = raw_command.strip()
    
    # Handle quoted path: "C:\path\to\app.exe" --arg
    if raw.startswith('"'):
        end_idx = raw.find('"', 1)
        if end_idx != -1:
            candidate = raw[1:end_idx]
            return os.path.expandvars(candidate)

    # Handle unquoted path: split at arguments or .exe
    match = re.search(r'([a-zA-Z]:\\[^/\:\*\?\"\<\>\|]+\.exe)', raw, re.IGNORECASE)
    if match:
        return os.path.expandvars(match.group(1))

    # Fallback to first token
    parts = raw.split()
    if parts:
        candidate = os.path.expandvars(parts[0])
        return candidate
    return raw

def resolve_fallback_path(app_name: str) -> str:
    """Finds shortcut or binary path for apps found in StartupApproved without direct Run values."""
    clean = os.path.splitext(app_name)[0].strip().lower()
    start_dirs = [
        os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
        os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs")
    ]
    for sdir in start_dirs:
        if os.path.exists(sdir):
            for root, dirs, files in os.walk(sdir):
                for f in files:
                    if f.lower().endswith(".lnk") and clean in f.lower():
                        return os.path.join(root, f)

    candidates = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), clean, f"{clean}.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), f"Programs/{clean}", f"{clean}.exe"),
        os.path.join(os.environ.get("ProgramFiles", "C:/Program Files"), clean, f"{clean}.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"), clean, f"{clean}.exe"),
        os.path.join(os.environ.get("SystemRoot", "C:/Windows"), "System32", f"{clean}.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return ""

class StartupEngine:
    @staticmethod
    def get_startup_apps() -> List[Dict[str, Any]]:
        """
        Discovers all startup applications across registry run keys,
        StartupApproved states, and user/common startup folders.
        """
        apps = {}

        # 1. Inspect StartupApproved state maps first
        approved_states = {}
        approved_locations = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run", "HKCU Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run", "HKLM Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run", "WOW64 Run"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder", "User Startup Folder"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder", "Common Startup Folder"),
        ]

        for hive, subkey, loc_name in approved_locations:
            try:
                key = winreg.OpenKey(hive, subkey)
                i = 0
                while True:
                    try:
                        name, val, _ = winreg.EnumValue(key, i)
                        is_disabled = isinstance(val, (bytes, bytearray)) and len(val) > 0 and (val[0] % 2 != 0)
                        approved_states[name.lower()] = {
                            "disabled": is_disabled,
                            "hive": hive,
                            "approved_key": subkey,
                            "loc_name": loc_name
                        }
                        i += 1
                    except OSError:
                        break
            except Exception:
                pass

        # 2. Inspect Registry Run and RunOnce keys
        run_locations = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "User (Registry Run)"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "System (Registry Run)"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "WOW6432 (Registry Run)"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "User (RunOnce)"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "System (RunOnce)"),
        ]

        for hive, subkey, loc_name in run_locations:
            try:
                key = winreg.OpenKey(hive, subkey)
                i = 0
                while True:
                    try:
                        name, raw_cmd, _ = winreg.EnumValue(key, i)
                        if name:
                            clean_path = extract_clean_path(str(raw_cmd))
                            app_key = name.lower()
                            
                            # Check approval status
                            is_enabled = True
                            if app_key in approved_states:
                                is_enabled = not approved_states[app_key]["disabled"]

                            apps[app_key] = {
                                "name": name,
                                "command": str(raw_cmd),
                                "path": clean_path,
                                "location": loc_name,
                                "enabled": is_enabled,
                                "type": "registry",
                                "hive": hive,
                                "subkey": subkey
                            }
                        i += 1
                    except OSError:
                        break
            except Exception:
                pass

        # 3. Add items that only exist in StartupApproved
        for app_key, state_info in approved_states.items():
            if app_key not in apps and not app_key.endswith(".ini"):
                resolved = resolve_fallback_path(app_key)
                apps[app_key] = {
                    "name": app_key,
                    "command": resolved,
                    "path": resolved,
                    "location": state_info["loc_name"],
                    "enabled": not state_info["disabled"],
                    "type": "registry_approved",
                    "hive": state_info["hive"],
                    "subkey": state_info["approved_key"]
                }

        # 4. Inspect Startup folders
        folder_paths = [
            (os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup"), "User Startup Folder", winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder"),
            (os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup"), "Common Startup Folder", winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder"),
        ]

        for folder, loc_name, hkey, app_sub in folder_paths:
            if os.path.exists(folder):
                for item_name in os.listdir(folder):
                    if item_name.lower() in ("desktop.ini",):
                        continue
                    full_path = os.path.join(folder, item_name)
                    clean_name = os.path.splitext(item_name)[0]
                    app_key = item_name.lower()

                    is_enabled = True
                    if app_key in approved_states:
                        is_enabled = not approved_states[app_key]["disabled"]

                    if app_key not in apps:
                        apps[app_key] = {
                            "name": clean_name,
                            "command": full_path,
                            "path": full_path,
                            "location": loc_name,
                            "enabled": is_enabled,
                            "type": "folder",
                            "folder_path": full_path,
                            "hive": hkey,
                            "approved_key": app_sub
                        }

        result = list(apps.values())
        result.sort(key=lambda x: (not x["enabled"], x["name"].lower()))
        return result

    @staticmethod
    def toggle_startup_state(item: Dict[str, Any]) -> tuple[bool, str]:
        """
        Enables or disables a startup application using Windows StartupApproved registry standards.
        """
        name = item.get("name", "")
        if not name:
            return False, "Invalid item name."

        new_state = not item.get("enabled", True)
        
        # Decide StartupApproved registry path
        hive = item.get("hive", winreg.HKEY_CURRENT_USER)
        approved_subkey = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
        if "folder" in item.get("location", "").lower():
            approved_subkey = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder"

        # 0x02 = Enabled, 0x03 = Disabled (12 bytes struct)
        first_byte = 0x02 if new_state else 0x03
        data_bytes = bytes([first_byte, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

        try:
            key = winreg.CreateKey(hive, approved_subkey)
            winreg.SetValueEx(key, name, 0, winreg.REG_BINARY, data_bytes)
            winreg.CloseKey(key)
            item["enabled"] = new_state
            status_text = "Enabled" if new_state else "Disabled"
            return True, f"'{name}' is now {status_text} at Windows startup."
        except Exception as e:
            # Try in HKCU fallback if HKLM required admin
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, approved_subkey)
                winreg.SetValueEx(key, name, 0, winreg.REG_BINARY, data_bytes)
                winreg.CloseKey(key)
                item["enabled"] = new_state
                status_text = "Enabled" if new_state else "Disabled"
                return True, f"'{name}' is now {status_text} at Windows startup."
            except Exception as e2:
                return False, f"Failed to modify startup state: {str(e2)}"

    @staticmethod
    def open_file_location(path: str) -> tuple[bool, str]:
        """
        Opens Windows File Explorer highlighting the target executable file.
        """
        if not path:
            return False, "No file path available for this item."

        clean = os.path.expandvars(path).strip('"\'' )
        
        # Check if direct path exists
        if os.path.exists(clean):
            try:
                subprocess.Popen(["explorer.exe", f"/select,{clean}"])
                return True, "Opened in Explorer."
            except Exception as e:
                return False, str(e)

        # Try to resolve directory
        parent_dir = os.path.dirname(clean)
        if os.path.exists(parent_dir):
            try:
                subprocess.Popen(["explorer.exe", parent_dir])
                return True, "Opened directory in Explorer."
            except Exception as e:
                return False, str(e)

        return False, f"File does not exist: {clean}"

    @staticmethod
    def is_run_at_startup() -> bool:
        """Checks if WinGame is registered to run on Windows boot."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, "WinGame")
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    @staticmethod
    def set_run_at_startup(enable: bool) -> tuple[bool, str]:
        """Adds or removes WinGame from Windows user startup."""
        run_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key, 0, winreg.KEY_SET_VALUE)
            if enable:
                import sys as _sys
                if getattr(_sys, "frozen", False):
                    cmd = f'"{_sys.executable}" --minimized'
                else:
                    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    bat_path = os.path.join(base_dir, "lancer_wingames.bat")
                    main_py = os.path.join(base_dir, "main.py")
                    cmd = f'"{bat_path}" --minimized' if os.path.exists(bat_path) else f'pythonw.exe "{main_py}" --minimized'
                winreg.SetValueEx(key, "WinGame", 0, winreg.REG_SZ, cmd)
                winreg.CloseKey(key)
                return True, "WinGame will start automatically with Windows (minimized)."
            else:
                try:
                    winreg.DeleteValue(key, "WinGame")
                except FileNotFoundError:
                    pass
                winreg.CloseKey(key)
                return True, "WinGame removed from Windows boot startup."
        except Exception as e:
            return False, str(e)
