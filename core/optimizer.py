import os
import time
import shutil
import ctypes
from ctypes import wintypes
import subprocess
import psutil
from datetime import datetime
from typing import Dict, Any, List
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker
from config import ConfigManager
from core.winmemorycleaner import WinMemoryCleanerEngine, MemoryAreas, is_admin


class _SHQUERYRBINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("i64Size", ctypes.c_int64),
        ("i64NumItems", ctypes.c_int64),
    ]


class SystemOptimizer:
    @staticmethod
    def clean_ram(mode: str = "industrial") -> Dict[str, Any]:
        """
        Two-tier memory cleaner powered by the direct Python port of WinMemoryCleaner:
        - "quick" (Petit Clean): Working Set trim + GC only. Fast, zero disk I/O, non-intrusive.
        - "industrial" (Gros Clean / WinMemoryCleaner): All 7 WinMemoryCleaner areas
          (Working Set, System File Cache, Modified Page List, Standby List, Combined Page List,
          Registry Cache, Modified File Cache with DeviceIoControl + FlushFileBuffers) + GC.
        """
        initial_mem = psutil.virtual_memory()
        mode_clean = mode.lower().strip()
        is_industrial = (mode_clean == "industrial")

        areas = MemoryAreas.ALL_DEEP if is_industrial else MemoryAreas.WORKING_SET
        result = WinMemoryCleanerEngine.optimize(areas=areas)

        # Brief settle delay so Windows memory manager finishes releasing pages
        time.sleep(0.15)

        final_mem = psutil.virtual_memory()
        freed_mb = max(0.0, round((initial_mem.used - final_mem.used) / (1024 * 1024), 1))

        return {
            "mode": "industrial" if is_industrial else "quick",
            "mode_name": "Deep Industrial (WinMemoryCleaner)" if is_industrial else "Quick Clean (Léger)",
            "freed_mb": freed_mb,
            "processes_trimmed": result.get("processes_trimmed", 0),
            "areas_cleaned": result.get("areas_cleaned", []),
            "is_admin": result.get("is_admin", is_admin()),
            "initial_percent": initial_mem.percent,
            "new_used_gb": round(final_mem.used / (1024**3), 2),
            "new_percent": final_mem.percent
        }

    @staticmethod
    def _get_temp_paths() -> List[str]:
        return list(dict.fromkeys([
            p for p in [
                os.environ.get("TEMP", ""),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp"),
                r"C:\Windows\Temp",
            ] if p
        ]))

    @staticmethod
    def _get_shader_paths() -> List[str]:
        local = os.environ.get("LOCALAPPDATA", "")
        progdata = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
        return [
            os.path.join(local, "D3DSCache"),
            os.path.join(local, "NVIDIA", "DXCache"),
            os.path.join(local, "NVIDIA", "GLCache"),
            os.path.join(local, "AMD", "DxCache"),
            os.path.join(progdata, "NVIDIA Corporation", "NV_Cache"),
        ]

    @staticmethod
    def _dir_size_bytes(paths: List[str]) -> int:
        total = 0
        for base in paths:
            if not base or not os.path.exists(base):
                continue
            for root, _dirs, files in os.walk(base):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except Exception:
                        continue
        return total

    @staticmethod
    def _purge_directories(paths: List[str]) -> Dict[str, Any]:
        deleted_files = 0
        freed_bytes = 0
        for base_path in paths:
            if not base_path or not os.path.exists(base_path):
                continue
            for root, dirs, files in os.walk(base_path, topdown=False):
                for f in files:
                    filepath = os.path.join(root, f)
                    try:
                        size = os.path.getsize(filepath)
                        os.remove(filepath)
                        deleted_files += 1
                        freed_bytes += size
                    except Exception:
                        continue
                for d in dirs:
                    dirpath = os.path.join(root, d)
                    try:
                        shutil.rmtree(dirpath, ignore_errors=True)
                    except Exception:
                        continue
        return {
            "deleted_files": deleted_files,
            "freed_mb": round(freed_bytes / (1024 * 1024), 2),
        }

    @staticmethod
    def _get_recycle_bin_info() -> tuple[int, int]:
        try:
            info = _SHQUERYRBINFO()
            info.cbSize = ctypes.sizeof(_SHQUERYRBINFO)
            shell32 = ctypes.windll.shell32
            shell32.SHQueryRecycleBinW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(_SHQUERYRBINFO)]
            shell32.SHQueryRecycleBinW.restype = ctypes.c_long
            if shell32.SHQueryRecycleBinW(None, ctypes.byref(info)) == 0:
                return max(0, int(info.i64Size)), max(0, int(info.i64NumItems))
        except Exception:
            pass
        return 0, 0

    @classmethod
    def scan_cleanable_space(cls) -> Dict[str, float]:
        """Scans reclaimable disk space (MB) across all junk & gaming cache categories."""
        temp_b = cls._dir_size_bytes(cls._get_temp_paths())
        shaders_b = cls._dir_size_bytes(cls._get_shader_paths())
        winupd_b = cls._dir_size_bytes([r"C:\Windows\SoftwareDistribution\Download"])
        prefetch_b = cls._dir_size_bytes([r"C:\Windows\Prefetch"])
        recycle_b, _ = cls._get_recycle_bin_info()

        to_mb = lambda b: round(b / (1024 * 1024), 1)
        temp_mb = to_mb(temp_b)
        shaders_mb = to_mb(shaders_b)
        winupd_mb = to_mb(winupd_b)
        prefetch_mb = to_mb(prefetch_b)
        recycle_mb = to_mb(recycle_b)

        return {
            "temp_mb": temp_mb,
            "shaders_mb": shaders_mb,
            "winupdate_mb": winupd_mb,
            "prefetch_mb": prefetch_mb,
            "recycle_mb": recycle_mb,
            "total_mb": round(temp_mb + shaders_mb + winupd_mb + prefetch_mb + recycle_mb, 1),
        }

    @classmethod
    def clean_temp_files(cls) -> Dict[str, Any]:
        """Cleans Windows %TEMP% and user temporary folders safely."""
        return cls._purge_directories(cls._get_temp_paths())

    @classmethod
    def clean_shader_cache(cls) -> Dict[str, Any]:
        """Cleans DirectX, NVIDIA (DXCache/GLCache/NV_Cache), and AMD shader caches."""
        return cls._purge_directories(cls._get_shader_paths())

    @classmethod
    def clean_windows_update_cache(cls) -> Dict[str, Any]:
        """Cleans downloaded Windows Update installer cache."""
        return cls._purge_directories([r"C:\Windows\SoftwareDistribution\Download"])

    @classmethod
    def clean_prefetch(cls) -> Dict[str, Any]:
        """Cleans Windows Prefetch files safely."""
        return cls._purge_directories([r"C:\Windows\Prefetch"])

    @classmethod
    def clean_recycle_bin(cls) -> Dict[str, Any]:
        """Silently empties the Windows Recycle Bin across all drives."""
        size_before, items_before = cls._get_recycle_bin_info()
        try:
            shell32 = ctypes.windll.shell32
            shell32.SHEmptyRecycleBinW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.DWORD]
            shell32.SHEmptyRecycleBinW.restype = ctypes.c_long
            # SHERB_NOCONFIRMATION (1) | SHERB_NOPROGRESSUI (2) | SHERB_NOSOUND (4) = 0x7
            shell32.SHEmptyRecycleBinW(None, None, 0x07)
            size_after, _ = cls._get_recycle_bin_info()
            freed_b = max(0, size_before - size_after)
            return {
                "success": True,
                "deleted_files": items_before,
                "freed_mb": round(freed_b / (1024 * 1024), 2),
            }
        except Exception as e:
            return {"success": False, "deleted_files": 0, "freed_mb": 0.0, "output": str(e)}

    @staticmethod
    def flush_dns() -> Dict[str, Any]:
        """
        Flushes Windows DNS Resolver cache via ipconfig.
        """
        try:
            res = subprocess.run(
                ["ipconfig", "/flushdns"],
                capture_output=True,
                text=True,
                shell=True
            )
            success = res.returncode == 0
            return {
                "success": success,
                "output": "Successfully flushed the DNS Resolver Cache." if success else res.stderr
            }
        except Exception as e:
            return {"success": False, "output": str(e)}

    @staticmethod
    def restart_explorer() -> Dict[str, Any]:
        """
        Launches or restarts Windows Explorer.
        """
        try:
            subprocess.Popen(["explorer.exe"], shell=False)
            return {"success": True, "output": "Windows Explorer started successfully."}
        except Exception as e:
            return {"success": False, "output": str(e)}


class AutoRamCleanerWorker(QThread):
    """
    Background worker that handles automated RAM & Cache cleaning:
    1. Periodic timer (every X seconds / minutes / hours)
    2. Threshold monitoring (auto-cleans whenever RAM >= X %)
    """
    ram_auto_cleaned = pyqtSignal(str, float, float, str)  # reason, freed_mb, new_percent, timestamp

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_mgr = ConfigManager()
        self.mutex = QMutex()
        self._running = True
        self._last_timer_clean = time.time()
        self._last_threshold_clean = 0

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
                self._check_triggers()
            except Exception as e:
                print(f"[AutoRamCleaner] Error: {e}")

            time.sleep(2.0)  # Check conditions every 2 seconds

    def _check_triggers(self):
        now = time.time()
        now_str = datetime.now().strftime("%H:%M:%S")

        mode = self.config_mgr.get("auto_ram_mode", "industrial")

        # 1. Threshold Trigger
        thresh_enabled = self.config_mgr.get("auto_ram_threshold_enabled", False)
        threshold_pct = self.config_mgr.get("auto_ram_threshold_percent", 80)

        if thresh_enabled:
            current_pct = psutil.virtual_memory().percent
            # Cooldown of at least 30 seconds between threshold triggers
            if current_pct >= threshold_pct and (now - self._last_threshold_clean > 30):
                self._last_threshold_clean = now
                res = SystemOptimizer.clean_ram(mode=mode)
                reason = f"RAM reached {current_pct:.1f}% (Threshold: {threshold_pct}% - {res['mode_name']})"
                self.ram_auto_cleaned.emit(reason, res["freed_mb"], res["new_percent"], now_str)

        # 2. Timer Interval Trigger
        timer_enabled = self.config_mgr.get("auto_ram_timer_enabled", False)
        timer_seconds = self.config_mgr.get("auto_ram_timer_seconds", 300)  # default 5 min

        if timer_enabled and timer_seconds > 0:
            if (now - self._last_timer_clean) >= timer_seconds:
                self._last_timer_clean = now
                res = SystemOptimizer.clean_ram(mode=mode)
                reason = f"Periodic Timer ({timer_seconds}s - {res['mode_name']})"
                self.ram_auto_cleaned.emit(reason, res["freed_mb"], res["new_percent"], now_str)
