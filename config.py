import os
import sys
import json


def _resolve_config_path() -> str:
    if getattr(sys, "frozen", False):
        appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
        cfg_dir = os.path.join(appdata, "VIT THEO", "WinGame")
        os.makedirs(cfg_dir, exist_ok=True)
        return os.path.join(cfg_dir, "config.json")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


CONFIG_FILE = _resolve_config_path()

# Only protect our own runtime and BSOD-critical system processes
# Note: explorer.exe is allowed for gaming optimizations
PROTECTED_PROCESSES = {
    "wingame.exe",
    "python.exe",
    "pythonw.exe",
    "py.exe",
    "csrss.exe",
    "smss.exe",
    "winlogon.exe",
    "services.exe",
    "lsass.exe",
    "system",
    "registry",
    "idle"
}

DEFAULT_CONFIG = {
    "auto_kill_interval_ms": 250,
    "auto_kill_enabled": False,
    "kill_children": True,
    "blacklist": [
        "OneDrive.exe",
        "YourPhone.exe",
        "PhoneExperienceHost.exe",
        "GameBarPresenceWriter.exe",
        "mscorsvw.exe"
    ],
    "log_history_limit": 500,
    "clean_temp_directories": [
        os.path.expandvars(r"%TEMP%"),
        os.path.expandvars(r"%WINDIR%\Temp")
    ]
}

class ConfigManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance.config = cls._instance.load()
        return cls._instance

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    merged = DEFAULT_CONFIG.copy()
                    merged.update(data)
                    return merged
            except Exception as e:
                print(f"[Config] Error loading config: {e}")
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()

    def add_to_blacklist(self, process_name: str) -> tuple[bool, str]:
        name = process_name.strip()
        if not name:
            return False, "Process name cannot be empty."
        if not name.lower().endswith(".exe"):
            name += ".exe"

        clean_lower = name.lower()
        if clean_lower in PROTECTED_PROCESSES or clean_lower.replace(".exe", "") in PROTECTED_PROCESSES:
            return False, f"'{name}' cannot be killed (required for WinGames runtime or Windows kernel)."

        lower_list = [p.lower() for p in self.config.get("blacklist", [])]
        if clean_lower in lower_list:
            return False, f"'{name}' is already in the blacklist."

        self.config.setdefault("blacklist", []).append(name)
        self.save()
        return True, f"'{name}' successfully added to Auto-Kill blacklist."

    def remove_from_blacklist(self, process_name: str) -> bool:
        name_lower = process_name.strip().lower()
        old_list = self.config.get("blacklist", [])
        new_list = [p for p in old_list if p.lower() != name_lower]
        if len(new_list) != len(old_list):
            self.config["blacklist"] = new_list
            self.save()
            return True
        return False
