import os
import psutil
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker

class ProcessEngine:
    @staticmethod
    def get_system_stats() -> Dict[str, Any]:
        """Returns overall CPU, RAM and disk statistics."""
        cpu_pct = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('C:\\')
        
        return {
            "cpu_percent": cpu_pct,
            "ram_percent": mem.percent,
            "ram_used_gb": round(mem.used / (1024**3), 2),
            "ram_total_gb": round(mem.total / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 1),
            "process_count": len(psutil.pids())
        }

    @staticmethod
    def get_running_processes() -> List[Dict[str, Any]]:
        """
        Fast non-blocking retrieval of all active processes.
        Omits slow RPC lookups (like username) for maximum UI responsiveness.
        """
        processes = []
        # Query only essential fast attributes
        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'status']):
            try:
                info = proc.info
                name = info.get('name')
                if not name:
                    continue

                mem_info = info.get('memory_info')
                mem_bytes = mem_info.rss if mem_info else 0
                mem_mb = round(mem_bytes / (1024 * 1024), 1)

                processes.append({
                    "pid": info['pid'],
                    "name": name,
                    "memory_mb": mem_mb,
                    "status": info.get('status', 'running')
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception:
                continue

        # Sort by memory usage descending by default
        processes.sort(key=lambda x: x["memory_mb"], reverse=True)
        return processes

    @staticmethod
    def force_kill_pid(pid: int, kill_tree: bool = True) -> tuple[bool, str]:
        """Forcefully kills a process by its PID, optionally terminating its children tree."""
        try:
            parent = psutil.Process(pid)
            proc_name = parent.name()
            
            if kill_tree:
                children = parent.children(recursive=True)
                for child in children:
                    try:
                        child.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
            parent.kill()
            return True, f"Process {proc_name} (PID: {pid}) successfully terminated."
        except psutil.NoSuchProcess:
            return False, f"Process (PID: {pid}) does not exist anymore."
        except psutil.AccessDenied:
            return False, f"Access denied to terminate (PID: {pid}). Run as Administrator."
        except Exception as e:
            return False, f"Error terminating (PID: {pid}): {str(e)}"

    @staticmethod
    def force_kill_by_name(process_name: str, kill_tree: bool = True) -> List[Dict[str, Any]]:
        """
        Force kills all running instances matching a process name.
        """
        target = process_name.strip().lower()
        results = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                p_name = proc.info.get('name')
                if p_name and p_name.lower() == target:
                    pid = proc.info['pid']
                    success, msg = ProcessEngine.force_kill_pid(pid, kill_tree)
                    results.append({
                        "pid": pid,
                        "name": p_name,
                        "success": success,
                        "message": msg
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                results.append({
                    "pid": -1,
                    "name": process_name,
                    "success": False,
                    "message": str(e)
                })
        return results


class AsyncProcessScanner(QThread):
    """
    Background worker thread that scans running processes without blocking the UI.
    """
    processes_ready = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mutex = QMutex()
        self._running = True

    def stop(self):
        with QMutexLocker(self.mutex):
            self._running = False
        self.wait(1000)

    def run(self):
        # Scan in background
        procs = ProcessEngine.get_running_processes()
        self.processes_ready.emit(procs)
