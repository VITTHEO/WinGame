import os
import time
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker
import psutil
from config import ConfigManager, PROTECTED_PROCESSES

class AutoKillerWorker(QThread):
    # Signals
    process_killed = pyqtSignal(str, int, bool, str, str) # name, pid, success, message, time_str
    stats_updated = pyqtSignal(int, int) # total_killed, scan_count
    status_changed = pyqtSignal(bool) # is_running

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_mgr = ConfigManager()
        self.mutex = QMutex()
        self._is_active = self.config_mgr.get("auto_kill_enabled", False)
        self._stop_requested = False
        
        self.interval_ms = self.config_mgr.get("auto_kill_interval_ms", 250)
        self.blacklist = [p.lower() for p in self.config_mgr.get("blacklist", [])]
        self.kill_children = self.config_mgr.get("kill_children", True)
        
        self.total_killed_count = 0
        self.scan_count = 0

    def set_active(self, active: bool):
        with QMutexLocker(self.mutex):
            self._is_active = active
        self.status_changed.emit(active)

    def is_active(self) -> bool:
        with QMutexLocker(self.mutex):
            return self._is_active

    def set_interval(self, interval_ms: int):
        with QMutexLocker(self.mutex):
            self.interval_ms = max(200, interval_ms)
        self.config_mgr.set("auto_kill_interval_ms", self.interval_ms)

    def reload_blacklist(self):
        with QMutexLocker(self.mutex):
            raw_list = self.config_mgr.get("blacklist", [])
            self.blacklist = [
                p.lower() for p in raw_list
                if p.lower() not in PROTECTED_PROCESSES and p.lower().replace(".exe", "") not in PROTECTED_PROCESSES
            ]
            self.kill_children = self.config_mgr.get("kill_children", True)

    def stop(self):
        with QMutexLocker(self.mutex):
            self._stop_requested = True
        self.wait(2000)

    def _get_immune_pids(self, targets: set[str]) -> set[int]:
        """Returns PIDs of this application and direct launcher processes that must never be terminated."""
        immune = {os.getpid()}
        try:
            curr = psutil.Process()
            for parent in curr.parents():
                pname = (parent.name() or "").lower()
                # If the parent itself is explicitly targeted (e.g. explorer.exe), do not add parent to immune,
                # but our own process remains strictly immune.
                if pname not in targets and pname.replace(".exe", "") not in targets:
                    immune.add(parent.pid)
        except Exception:
            pass
        return immune

    def run(self):
        while True:
            try:
                with QMutexLocker(self.mutex):
                    if self._stop_requested:
                        break
                    is_active = self._is_active
                    interval = self.interval_ms
                    targets = set(self.blacklist)
                    kill_tree = self.kill_children

                if is_active and targets:
                    self.scan_count += 1
                    self._scan_and_kill(targets, kill_tree)
                    self.stats_updated.emit(self.total_killed_count, self.scan_count)

                # Sleep in small slices for instant responsiveness
                sleep_time = interval / 1000.0
                elapsed = 0.0
                slice_sec = 0.1
                while elapsed < sleep_time:
                    with QMutexLocker(self.mutex):
                        if self._stop_requested:
                            return
                    time.sleep(slice_sec)
                    elapsed += slice_sec
            except Exception as e:
                print(f"[AutoKillerWorker] Unexpected loop error: {e}")
                time.sleep(1.0)

    def _scan_and_kill(self, targets: set[str], kill_tree: bool):
        now_str = datetime.now().strftime("%H:%M:%S")
        immune_pids = self._get_immune_pids(targets)
        my_pid = os.getpid()

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pid = proc.info.get('pid')
                if not pid or pid <= 4 or pid in immune_pids or pid == my_pid:
                    continue

                name = proc.info.get('name')
                if not name:
                    continue
                
                name_clean = name.lower()
                if name_clean in PROTECTED_PROCESSES or name_clean.replace(".exe", "") in PROTECTED_PROCESSES:
                    continue

                matched = False
                for target in targets:
                    if name_clean == target or name_clean == target.replace(".exe", "") + ".exe" or name_clean.replace(".exe", "") == target:
                        matched = True
                        break

                if matched:
                    try:
                        p = psutil.Process(pid)
                        
                        # If terminating explorer.exe, only kill explorer itself to avoid terminating other user apps/win-games
                        is_shell = "explorer" in name_clean
                        if kill_tree and not is_shell:
                            try:
                                for child in p.children(recursive=True):
                                    if child.pid in immune_pids or child.pid == my_pid or child.pid <= 4:
                                        continue
                                    try:
                                        c_name = (child.name() or "").lower()
                                        if c_name in PROTECTED_PROCESSES or "python" in c_name:
                                            continue
                                        child.kill()
                                    except Exception:
                                        pass
                            except Exception:
                                pass

                        p.kill()
                        self.total_killed_count += 1
                        self.process_killed.emit(
                            name,
                            pid,
                            True,
                            "Auto-killed by blacklist rule",
                            now_str
                        )
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        self.process_killed.emit(
                            name,
                            pid,
                            False,
                            f"Kill failed ({type(e).__name__})",
                            now_str
                        )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception:
                continue
