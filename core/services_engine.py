import os
import winreg
import subprocess
import psutil
from typing import List, Dict, Any, Optional

START_TYPE_NAMES = {
    0: "Boot",
    1: "System",
    2: "Automatic",
    3: "Manual",
    4: "Disabled"
}

def clean_service_image(raw_path: str) -> str:
    if not raw_path:
        return ""
    clean = raw_path.strip()
    if clean.startswith(r"\??\\"):
        clean = clean[4:]
    if clean.startswith('"'):
        end = clean.find('"', 1)
        if end != -1:
            clean = clean[1:end]
    else:
        parts = clean.split()
        if parts:
            clean = parts[0]
    return os.path.expandvars(clean)

class ServicesEngine:
    @staticmethod
    def get_all_services(filter_startup_only: bool = False) -> List[Dict[str, Any]]:
        """
        Retrieves all registered Windows Services from registry and active process mappings.
        """
        services = []
        base_path = r"SYSTEM\CurrentControlSet\Services"
        
        # Get set of active process executable names to quickly determine if running
        active_exes = set()
        for p in psutil.process_iter(['name']):
            try:
                n = p.info.get('name')
                if n:
                    active_exes.add(n.lower())
            except Exception:
                pass

        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_path)
            count = winreg.QueryInfoKey(key)[0]
            
            for i in range(count):
                svc_name = winreg.EnumKey(key, i)
                try:
                    sub = winreg.OpenKey(key, svc_name)
                    
                    try:
                        start_code, _ = winreg.QueryValueEx(sub, "Start")
                    except Exception:
                        continue # Skip drivers or entries without Start type
                    
                    if filter_startup_only and start_code not in (2,):
                        continue

                    try:
                        disp_name, _ = winreg.QueryValueEx(sub, "DisplayName")
                        if disp_name.startswith("@"):
                            # Resolve resource strings gracefully
                            disp_name = svc_name
                    except Exception:
                        disp_name = svc_name

                    try:
                        desc, _ = winreg.QueryValueEx(sub, "Description")
                        if desc.startswith("@"):
                            desc = ""
                    except Exception:
                        desc = ""

                    try:
                        raw_image, _ = winreg.QueryValueEx(sub, "ImagePath")
                        image_path = clean_service_image(str(raw_image))
                    except Exception:
                        image_path = ""

                    # Running status estimation
                    exe_name = os.path.basename(image_path).lower()
                    is_running = exe_name in active_exes if (exe_name and exe_name != "svchost.exe") else False

                    # Check if third party (non-system32)
                    is_third_party = "system32" not in image_path.lower() and "syswow64" not in image_path.lower() and bool(image_path)

                    services.append({
                        "name": svc_name,
                        "display_name": disp_name or svc_name,
                        "description": desc,
                        "image_path": image_path,
                        "start_type_code": start_code,
                        "start_type_name": START_TYPE_NAMES.get(start_code, "Unknown"),
                        "is_running": is_running,
                        "is_third_party": is_third_party
                    })
                except Exception:
                    continue
        except Exception as e:
            print(f"[ServicesEngine] Registry error: {e}")

        services.sort(key=lambda s: (not s["is_third_party"], s["start_type_code"] != 2, s["name"].lower()))
        return services

    @staticmethod
    def stop_service(service_name: str) -> tuple[bool, str]:
        """Stops a Windows service using sc.exe."""
        try:
            res = subprocess.run(["sc.exe", "stop", service_name], capture_output=True, text=True, shell=True)
            if res.returncode == 0 or "STOP_PENDING" in res.stdout or "STOPPED" in res.stdout:
                return True, f"Service '{service_name}' stopped."
            return False, res.stdout or res.stderr or "Requires Administrator privileges."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def start_service(service_name: str) -> tuple[bool, str]:
        """Starts a Windows service using sc.exe."""
        try:
            res = subprocess.run(["sc.exe", "start", service_name], capture_output=True, text=True, shell=True)
            if res.returncode == 0 or "START_PENDING" in res.stdout or "RUNNING" in res.stdout:
                return True, f"Service '{service_name}' started."
            return False, res.stdout or res.stderr or "Requires Administrator privileges."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def set_service_start_type(service_name: str, mode: str = "disabled") -> tuple[bool, str]:
        """
        Configures service startup type: 'auto', 'demand', or 'disabled'.
        """
        # Mode for sc.exe: auto | demand | disabled
        sc_mode = "disabled" if mode == "disabled" else ("auto" if mode == "auto" else "demand")
        try:
            res = subprocess.run(["sc.exe", "config", service_name, f"start={sc_mode}"], capture_output=True, text=True, shell=True)
            if res.returncode == 0 or "SUCCESS" in res.stdout:
                return True, f"Service '{service_name}' startup type changed to {sc_mode}."
            return False, res.stdout or res.stderr or "Requires Administrator privileges."
        except Exception as e:
            return False, str(e)
