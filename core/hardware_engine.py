import os
import sys
import time
import platform
import winreg
import subprocess
import psutil
from typing import Dict, Any, List

class HardwareEngine:
    _cpu_name_cache = None
    _gpus_cache = None
    _ram_type_cache = None
    _disk_model_cache = None
    _os_info_cache = None
    _last_net_bytes = (0, 0, 0) # sent, recv, timestamp

    @classmethod
    def get_cpu_info(cls) -> Dict[str, Any]:
        """Retrieves CPU model name, core counts, and frequency."""
        if cls._cpu_name_cache is None:
            name = platform.processor()
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                val, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                if val:
                    name = str(val).strip()
            except Exception:
                pass
            cls._cpu_name_cache = name

        # Frequencies
        freq_current = 0.0
        try:
            freq = psutil.cpu_freq()
            if freq:
                freq_current = round(freq.current / 1000.0, 2)
        except Exception:
            pass

        return {
            "name": cls._cpu_name_cache,
            "logical_cores": psutil.cpu_count(logical=True) or 0,
            "physical_cores": psutil.cpu_count(logical=False) or 0,
            "frequency_ghz": freq_current,
            "usage_percent": psutil.cpu_percent(interval=None)
        }

    @classmethod
    def classify_gpu_type(cls, gpu_name: str, is_dedicated: bool) -> str:
        """Classifies GPU into precise architecture/series instead of hardcoded labels."""
        if not is_dedicated:
            return "Integrated Graphics"
        name_l = (gpu_name or "").lower()
        if "rtx 50" in name_l:
            return "Dedicated (RTX 50 Series)"
        if "rtx 40" in name_l:
            return "Dedicated (RTX 40 Series)"
        if "rtx 30" in name_l:
            return "Dedicated (RTX 30 Series)"
        if "rtx 20" in name_l:
            return "Dedicated (RTX 20 Series)"
        if "gtx 16" in name_l or "1650" in name_l or "1660" in name_l:
            return "Dedicated (GTX 16 Series)"
        if "gtx 10" in name_l or "1050" in name_l or "1060" in name_l or "1070" in name_l or "1080" in name_l:
            return "Dedicated (GTX 10 Series)"
        if "gtx 9" in name_l or "970" in name_l or "980" in name_l:
            return "Dedicated (GTX 900 Series)"
        if "gtx" in name_l:
            return "Dedicated (NVIDIA GeForce GTX)"
        if "rtx" in name_l:
            return "Dedicated (NVIDIA GeForce RTX)"
        if "geforce" in name_l or "nvidia" in name_l:
            return "Dedicated (NVIDIA GeForce)"
        if "rx 7" in name_l:
            return "Dedicated (Radeon RX 7000 Series)"
        if "rx 6" in name_l:
            return "Dedicated (Radeon RX 6000 Series)"
        if "rx 5" in name_l:
            return "Dedicated (Radeon RX 5000/500 Series)"
        if "radeon" in name_l:
            return "Dedicated (AMD Radeon)"
        if "arc" in name_l:
            return "Dedicated (Intel Arc Graphics)"
        return "Dedicated GPU"

    @classmethod
    def get_gpu_info(cls) -> List[Dict[str, Any]]:
        """Retrieves GPU models and live telemetry."""
        if cls._gpus_cache is None:
            gpus = []
            base_path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_path)
                for i in range(20):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        sub = winreg.OpenKey(key, subkey_name)
                        try:
                            name, _ = winreg.QueryValueEx(sub, "DriverDesc")
                            if name and name not in [g["name"] for g in gpus]:
                                nl = name.lower()
                                is_dedicated = not ("intel" in nl or "uhd" in nl or "iris" in nl or "radeon(tm) graphics" in nl or "basic display" in nl)
                                gpus.append({
                                    "name": name,
                                    "dedicated": is_dedicated,
                                    "type_label": cls.classify_gpu_type(name, is_dedicated)
                                })
                        except Exception:
                            pass
                    except OSError:
                        break
            except Exception:
                pass
            
            # Sort dedicated GPUs first
            gpus.sort(key=lambda x: not x["dedicated"])
            cls._gpus_cache = gpus

        # Try live telemetry via NVML if available
        gpu_telemetry = []
        try:
            import pynvml
            pynvml.nvmlInit()
            dev_count = pynvml.nvmlDeviceGetCount()
            for i in range(dev_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                raw_name = pynvml.nvmlDeviceGetName(handle)
                name_str = raw_name.decode("utf-8") if isinstance(raw_name, bytes) else str(raw_name)
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu_telemetry.append({
                    "name": name_str,
                    "dedicated": True,
                    "type_label": cls.classify_gpu_type(name_str, True),
                    "temperature_c": temp,
                    "usage_percent": util.gpu,
                    "vram_used_mb": mem.used // (1024**2),
                    "vram_total_mb": mem.total // (1024**2)
                })
        except Exception:
            pass

        if gpu_telemetry:
            return gpu_telemetry

        # Try live telemetry via nvidia-smi (zero pip deps, works with Admin on NVIDIA GPUs)
        try:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            res = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,utilization.gpu,temperature.gpu,memory.used,memory.total",
                    "--format=csv,noheader,nounits"
                ],
                capture_output=True,
                text=True,
                timeout=1.0,
                creationflags=creationflags
            )
            if res.returncode == 0 and res.stdout.strip():
                for line in res.stdout.strip().splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 5:
                        name_str = parts[0]
                        try:
                            util_val = float(parts[1])
                        except ValueError:
                            util_val = 0.0
                        try:
                            temp_val = int(float(parts[2]))
                        except ValueError:
                            temp_val = None
                        try:
                            vram_used = int(float(parts[3]))
                            vram_total = int(float(parts[4]))
                        except ValueError:
                            vram_used, vram_total = None, None
                        gpu_telemetry.append({
                            "name": name_str,
                            "dedicated": True,
                            "type_label": cls.classify_gpu_type(name_str, True),
                            "temperature_c": temp_val,
                            "usage_percent": util_val,
                            "vram_used_mb": vram_used,
                            "vram_total_mb": vram_total
                        })
        except Exception:
            pass

        if gpu_telemetry:
            return gpu_telemetry

        # Fallback to cached registry GPUs
        results = []
        for g in cls._gpus_cache:
            results.append({
                "name": g["name"],
                "dedicated": g["dedicated"],
                "type_label": g.get("type_label", cls.classify_gpu_type(g["name"], g["dedicated"])),
                "temperature_c": None,
                "usage_percent": None,
                "vram_used_mb": None,
                "vram_total_mb": None
            })
        return results

    @classmethod
    def get_ram_type_speed(cls) -> str:
        """Dynamically detects RAM type (DDR4 vs DDR5 vs DDR3) and configured speed."""
        if cls._ram_type_cache is not None:
            return cls._ram_type_cache

        try:
            # Query CIM Instance via powershell
            cmd = ['powershell', '-NoProfile', '-Command', '(Get-CimInstance Win32_PhysicalMemory | Select-Object -First 1 | Select-Object Speed, SMBIOSMemoryType | ConvertTo-Csv -NoTypeInformation)[1]']
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            line = proc.stdout.strip()
            if line:
                parts = [p.strip('"\'' ) for p in line.split(',')]
                speed = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
                smbios = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0

                gen = "DDR4"
                if smbios in (34, 35) or speed >= 4800:
                    gen = "DDR5"
                elif smbios in (26, 30) or (2133 <= speed <= 3600):
                    gen = "DDR4"
                elif smbios == 24 or (speed > 0 and speed <= 1866):
                    gen = "DDR3"

                speed_label = f"{speed} MHz" if speed > 0 else "High Speed"
                res = f"{gen} ({speed_label})"
                cls._ram_type_cache = res
                return res
        except Exception:
            pass

        # Intelligent fallback by CPU generation
        cpu_name = (cls._cpu_name_cache or "").lower()
        if "12450h" in cpu_name or "13" in cpu_name or "14" in cpu_name:
            res = "DDR5 (4800 MHz)"
        else:
            res = "DDR4 (3200 MHz)"
        cls._ram_type_cache = res
        return res

    @classmethod
    def get_ram_info(cls) -> Dict[str, Any]:
        """Retrieves RAM usage and capacity."""
        mem = psutil.virtual_memory()
        swap_used = 0.0
        swap_total = 0.0
        try:
            swap = psutil.swap_memory()
            swap_used = round(swap.used / (1024**3), 1)
            swap_total = round(swap.total / (1024**3), 1)
        except Exception:
            pass

        return {
            "total_gb": round(mem.total / (1024**3), 1),
            "used_gb": round(mem.used / (1024**3), 1),
            "free_gb": round(mem.available / (1024**3), 1),
            "percent": mem.percent,
            "type_str": cls.get_ram_type_speed(),
            "swap_used_gb": swap_used,
            "swap_total_gb": swap_total
        }

    @classmethod
    def get_primary_disk_model(cls) -> str:
        """Retrieves the actual hardware model name of the primary disk drive."""
        if cls._disk_model_cache is not None:
            return cls._disk_model_cache

        # 1. Fast registry inspection
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\disk\Enum")
            val_0, _ = winreg.QueryValueEx(k, "0")
            dev_k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Enum\\" + val_0)
            try:
                fn, _ = winreg.QueryValueEx(dev_k, "FriendlyName")
                if fn and str(fn).strip():
                    cls._disk_model_cache = str(fn).strip()
                    return cls._disk_model_cache
            except Exception:
                pass
        except Exception:
            pass

        # 2. PowerShell CimInstance fallback
        try:
            cmd = ['powershell', '-NoProfile', '-Command', '(Get-CimInstance Win32_DiskDrive | Select-Object -First 1).Model']
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            out = proc.stdout.strip()
            if out:
                cls._disk_model_cache = out
                return out
        except Exception:
            pass

        cls._disk_model_cache = "NVMe / SSD Primary Drive"
        return cls._disk_model_cache

    @classmethod
    def get_disks_info(cls) -> List[Dict[str, Any]]:
        """Retrieves all connected storage partitions with usage and physical model."""
        disks = []
        primary_model = cls.get_primary_disk_model()
        try:
            for part in psutil.disk_partitions(all=False):
                if os.name == 'nt' and ('cdrom' in part.opts or part.fstype == ''):
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disks.append({
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "model": primary_model if part.mountpoint.upper().startswith("C:") else f"Storage Drive ({part.mountpoint})",
                        "total_gb": round(usage.total / (1024**3), 1),
                        "used_gb": round(usage.used / (1024**3), 1),
                        "free_gb": round(usage.free / (1024**3), 1),
                        "percent": usage.percent
                    })
                except PermissionError:
                    continue
        except Exception:
            pass
        return disks

    @classmethod
    def get_os_info(cls) -> Dict[str, str]:
        """Dynamically queries the Windows product name, edition, and display version."""
        if cls._os_info_cache is not None:
            return cls._os_info_cache

        os_name = "Microsoft Windows 11"
        version_str = "Version 24H2"
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
            try:
                build_str, _ = winreg.QueryValueEx(k, "CurrentBuild")
                build_num = int(build_str)
                is_w11 = build_num >= 22000
            except Exception:
                is_w11 = True

            try:
                ed, _ = winreg.QueryValueEx(k, "EditionID")
                ed_map = {
                    "Core": "Home",
                    "CoreSingleLanguage": "Home Single Language",
                    "Professional": "Pro",
                    "Enterprise": "Enterprise"
                }
                edition_clean = ed_map.get(ed, ed)
            except Exception:
                edition_clean = "Home"

            os_name = f"Microsoft Windows {'11' if is_w11 else '10'} {edition_clean}"

            try:
                dv, _ = winreg.QueryValueEx(k, "DisplayVersion")
                version_str = f"Version {dv}"
            except Exception:
                try:
                    rel, _ = winreg.QueryValueEx(k, "ReleaseId")
                    version_str = f"Version {rel}"
                except Exception:
                    version_str = "Latest"
        except Exception:
            pass

        cls._os_info_cache = {"name": os_name, "version": version_str}
        return cls._os_info_cache

    @classmethod
    def get_network_speed(cls) -> tuple[float, float]:
        """Returns upload and download speeds in KB/s."""
        now = time.time()
        try:
            net = psutil.net_io_counters()
            bytes_sent, bytes_recv = net.bytes_sent, net.bytes_recv
            
            last_sent, last_recv, last_time = cls._last_net_bytes
            cls._last_net_bytes = (bytes_sent, bytes_recv, now)
            
            if last_time == 0:
                return (0.0, 0.0)
            
            dt = max(0.1, now - last_time)
            up_kb = round((bytes_sent - last_sent) / (1024 * dt), 1)
            down_kb = round((bytes_recv - last_recv) / (1024 * dt), 1)
            return (max(0.0, up_kb), max(0.0, down_kb))
        except Exception:
            return (0.0, 0.0)

    @classmethod
    def get_system_uptime(cls) -> str:
        """Returns formatted system uptime."""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = int(time.time() - boot_time)
            hours = uptime_seconds // 3600
            minutes = (uptime_seconds % 3600) // 60
            return f"{hours}h {minutes:02d}m"
        except Exception:
            return "N/A"
