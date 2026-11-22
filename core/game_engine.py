import os
import re
import time
import glob
import json
import psutil
import subprocess
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker
from config import ConfigManager
from core.optimizer import SystemOptimizer

DEFAULT_GAME_SETTINGS = {
    "priority": "High",           # Normal, AboveNormal, High, Realtime
    "auto_kill_blacklist": True,  # Activate auto-killer while playing
    "auto_kill_explorer": False,  # Kill Windows Explorer to free FPS & input lag
    "auto_clean_ram": True,       # Clean RAM on game launch
    "custom_args": ""             # Optional launch arguments
}

class GameEngine:
    @staticmethod
    def scan_installed_games() -> List[Dict[str, Any]]:
        """
        Scans Steam libraries, Riot Games, Epic Games, and custom games.
        """
        games = []
        found_exes = set()

        # 1. STEAM SCAN
        steam_roots = [
            r"C:\Program Files (x86)\Steam",
            r"C:\Program Files\Steam",
            r"D:\Steam",
            r"E:\Steam",
            r"D:\SteamLibrary",
            r"E:\SteamLibrary"
        ]

        for root in steam_roots:
            if not os.path.exists(root):
                continue

            lib_paths = [root]
            vdf_path = os.path.join(root, "steamapps", "libraryfolders.vdf")
            if os.path.exists(vdf_path):
                try:
                    with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if '"path"' in line:
                                parts = line.split('"path"')
                                if len(parts) > 1:
                                    clean_p = parts[1].strip().strip('"').replace(r"\\", "\\")
                                    if os.path.exists(clean_p) and clean_p not in lib_paths:
                                        lib_paths.append(clean_p)
                except Exception:
                    pass

            for lib in lib_paths:
                steamapps = os.path.join(lib, "steamapps")
                if not os.path.exists(steamapps):
                    continue

                for acf in glob.glob(os.path.join(steamapps, "appmanifest_*.acf")):
                    try:
                        with open(acf, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            name = ""
                            installdir = ""
                            appid = ""
                            for l in content.splitlines():
                                if '"name"' in l and not name:
                                    name = l.split('"name"')[1].strip().strip('"')
                                elif '"installdir"' in l and not installdir:
                                    installdir = l.split('"installdir"')[1].strip().strip('"')
                                elif '"appid"' in l and not appid:
                                    appid = l.split('"appid"')[1].strip().strip('"')

                            if name and installdir:
                                game_dir = os.path.join(steamapps, "common", installdir)
                                main_exe = GameEngine._find_game_exe(game_dir, name)
                                game_id = f"steam_{appid}"
                                games.append({
                                    "id": game_id,
                                    "name": name,
                                    "platform": "Steam",
                                    "appid": appid,
                                    "game_dir": game_dir,
                                    "exe_path": main_exe,
                                    "exe_name": os.path.basename(main_exe).lower() if main_exe else ""
                                })
                                if main_exe:
                                    found_exes.add(main_exe.lower())
                    except Exception:
                        pass

        # 2. RIOT GAMES SCAN
        riot_root = r"C:\Riot Games"
        if os.path.exists(riot_root):
            for item in os.listdir(riot_root):
                folder = os.path.join(riot_root, item)
                if os.path.isdir(folder) and item.lower() != "riot client":
                    main_exe = GameEngine._find_game_exe(folder, item)
                    games.append({
                        "id": f"riot_{item.lower().replace(' ', '_')}",
                        "name": item,
                        "platform": "Riot Games",
                        "appid": "",
                        "game_dir": folder,
                        "exe_path": main_exe,
                        "exe_name": os.path.basename(main_exe).lower() if main_exe else ""
                    })

        # 3. EPIC GAMES SCAN
        epic_manifests = r"C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests"
        if os.path.exists(epic_manifests):
            for item_file in glob.glob(os.path.join(epic_manifests, "*.item")):
                try:
                    with open(item_file, "r", encoding="utf-8", errors="ignore") as f:
                        data = json.load(f)
                        name = data.get("DisplayName")
                        loc = data.get("InstallLocation")
                        app_exe = data.get("LaunchExecutable")
                        if name and loc:
                            full_exe = os.path.join(loc, app_exe) if app_exe else GameEngine._find_game_exe(loc, name)
                            games.append({
                                "id": f"epic_{name.lower().replace(' ', '_')}",
                                "name": name,
                                "platform": "Epic Games",
                                "appid": "",
                                "game_dir": loc,
                                "exe_path": full_exe,
                                "exe_name": os.path.basename(full_exe).lower() if full_exe else ""
                            })
                except Exception:
                    pass

        # 4. MERGE CUSTOM LOCAL GAMES FROM CONFIG
        cfg = ConfigManager()
        custom_games = cfg.get("custom_games", [])
        for cg in custom_games:
            games.append(cg)

        # Attach per-game settings
        profiles = cfg.get("game_profiles", {})
        for g in games:
            gid = g["id"]
            if gid not in profiles:
                profiles[gid] = DEFAULT_GAME_SETTINGS.copy()
            g["settings"] = profiles[gid]

        cfg.set("game_profiles", profiles)
        return games

    @staticmethod
    def _find_game_exe(game_dir: str, game_name: str) -> str:
        """Heuristic search for the main executable in a game directory."""
        if not os.path.exists(game_dir):
            return ""

        candidates = []
        for root, dirs, files in os.walk(game_dir):
            # Limit depth
            depth = root[len(game_dir):].count(os.sep)
            if depth > 2:
                continue
            for f in files:
                if f.lower().endswith(".exe"):
                    low = f.lower()
                    if any(bad in low for bad in ["crash", "report", "unity", "unreal", "redist", "setup", "install", "update", "eac", "battleye"]):
                        continue
                    candidates.append(os.path.join(root, f))

        if not candidates:
            return ""

        # Score by similarity to game name
        clean_name = re.sub(r"[^a-zA-Z0-9]", "", game_name).lower()
        for c in candidates:
            c_base = re.sub(r"[^a-zA-Z0-9]", "", os.path.splitext(os.path.basename(c))[0]).lower()
            if clean_name in c_base or c_base in clean_name:
                return c

        return candidates[0]

    @staticmethod
    def add_custom_game(name: str, exe_path: str) -> tuple[bool, str]:
        """Manually adds a local game executable."""
        name = name.strip()
        exe = os.path.expandvars(exe_path).strip('"\'' )
        if not name or not exe:
            return False, "Game name and executable path are required."
        if not os.path.exists(exe):
            return False, f"File does not exist: {exe}"

        cfg = ConfigManager()
        custom_games = cfg.get("custom_games", [])
        
        game_id = f"custom_{name.lower().replace(' ', '_')}"
        new_entry = {
            "id": game_id,
            "name": name,
            "platform": "Local Game",
            "appid": "",
            "game_dir": os.path.dirname(exe),
            "exe_path": exe,
            "exe_name": os.path.basename(exe).lower()
        }

        # Check existing
        for g in custom_games:
            if g["id"] == game_id or g["exe_path"].lower() == exe.lower():
                return False, f"Game '{name}' is already registered."

        custom_games.append(new_entry)
        cfg.set("custom_games", custom_games)
        
        # Save default profile
        profiles = cfg.get("game_profiles", {})
        profiles[game_id] = DEFAULT_GAME_SETTINGS.copy()
        cfg.set("game_profiles", profiles)

        return True, f"Game '{name}' successfully added!"

    @staticmethod
    def update_game_settings(game_id: str, new_settings: Dict[str, Any]):
        """Saves custom optimization settings for a specific game."""
        cfg = ConfigManager()
        profiles = cfg.get("game_profiles", {})
        profiles[game_id] = new_settings
        cfg.set("game_profiles", profiles)

    @staticmethod
    def launch_game(game: Dict[str, Any]) -> tuple[bool, str]:
        """Launches a game via Steam URI or direct executable."""
        appid = game.get("appid")
        exe = game.get("exe_path")
        
        try:
            if appid:
                # Steam URL launch is safest for Steam games
                os.startfile(f"steam://rungameid/{appid}")
                return True, f"Launching {game['name']} via Steam..."
            elif exe and os.path.exists(exe):
                subprocess.Popen([exe], cwd=os.path.dirname(exe), shell=False)
                return True, f"Launched {game['name']}."
            else:
                return False, "No valid launch executable found."
        except Exception as e:
            return False, str(e)


class GameWatcherThread(QThread):
    """
    Background daemon that monitors running games and applies per-game optimization profiles.
    """
    game_boost_applied = pyqtSignal(str, str) # game_name, action_summary
    game_closed = pyqtSignal(str)             # game_name

    PRIORITY_MAP = {
        "Normal": psutil.NORMAL_PRIORITY_CLASS,
        "AboveNormal": psutil.ABOVE_NORMAL_PRIORITY_CLASS,
        "High": psutil.HIGH_PRIORITY_CLASS,
        "Realtime": psutil.REALTIME_PRIORITY_CLASS
    }

    def __init__(self, auto_killer_ref=None, parent=None):
        super().__init__(parent)
        self.auto_killer_ref = auto_killer_ref
        self.mutex = QMutex()
        self._running = True
        self.active_boosted_game = None # (game_dict, pid, explorer_killed_flag)

    def stop(self):
        with QMutexLocker(self.mutex):
            self._running = False
        self.wait(1500)

    def run(self):
        while True:
            with QMutexLocker(self.mutex):
                if not self._running:
                    break

            try:
                self._check_games_status()
            except Exception as e:
                print(f"[GameWatcher] Error: {e}")

            time.sleep(1.5)

    def _check_games_status(self):
        cfg = ConfigManager()
        profiles = cfg.get("game_profiles", {})

        # If a game is currently boosted, verify if it's still running
        if self.active_boosted_game:
            game_data, pid, exp_killed = self.active_boosted_game
            still_running = False
            try:
                p = psutil.Process(pid)
                if p.is_running():
                    still_running = True
            except Exception:
                still_running = False

            if not still_running:
                # Game just closed!
                game_name = game_data.get("name", "Game")
                if exp_killed:
                    # Restore Windows Explorer
                    SystemOptimizer.restart_explorer()
                
                self.game_closed.emit(game_name)
                self.active_boosted_game = None

        # Look for running registered games if none active
        if not self.active_boosted_game:
            games = GameEngine.scan_installed_games()
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    pname = (proc.info.get('name') or "").lower()
                    if not pname:
                        continue
                    
                    for g in games:
                        g_exe = g.get("exe_name", "").lower()
                        if g_exe and g_exe == pname:
                            # MATCH! Apply game profile!
                            pid = proc.info['pid']
                            gid = g["id"]
                            settings = profiles.get(gid, DEFAULT_GAME_SETTINGS)
                            exp_killed = self._apply_game_profile(g, pid, settings)
                            self.active_boosted_game = (g, pid, exp_killed)
                            return
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

    def _apply_game_profile(self, game: Dict[str, Any], pid: int, settings: Dict[str, Any]) -> bool:
        game_name = game.get("name", "Game")
        actions = []
        exp_killed = False

        # 1. Set CPU Priority
        prio_str = settings.get("priority", "High")
        prio_flag = self.PRIORITY_MAP.get(prio_str, psutil.HIGH_PRIORITY_CLASS)
        try:
            p = psutil.Process(pid)
            p.nice(prio_flag)
            actions.append(f"CPU Priority set to {prio_str}")
        except Exception:
            pass

        # 2. Clean RAM on launch
        if settings.get("auto_clean_ram", True):
            res = SystemOptimizer.clean_ram()
            actions.append(f"RAM Cleaned ({res['freed_mb']:.0f} MB)")

        # 3. Kill Explorer if configured
        if settings.get("auto_kill_explorer", False):
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if (proc.info.get('name') or "").lower() == "explorer.exe":
                        proc.kill()
                        exp_killed = True
                        actions.append("Explorer terminated for gaming")
                except Exception:
                    pass

        # 4. Activate Auto-Killer loop
        if settings.get("auto_kill_blacklist", True) and self.auto_killer_ref:
            self.auto_killer_ref.set_active(True)
            actions.append("Auto-Killer 250ms engaged")

        summary = " • ".join(actions)
        self.game_boost_applied.emit(game_name, summary)
        return exp_killed
