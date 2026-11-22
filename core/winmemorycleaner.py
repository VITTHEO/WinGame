"""
Direct Python port of WinMemoryCleaner (IgorMundstein/WinMemoryCleaner)
Ported from:
  - src/Core/Constants.cs
  - src/Core/Structs.cs
  - src/Service/ComputerService.cs
"""

import ctypes
from ctypes import wintypes
import gc
import platform
from enum import IntFlag
from typing import Dict, Any, List, Optional, Set
import psutil


# ==============================================================================
# Constants (from Constants.cs)
# ==============================================================================
class DriveConstants:
    FSCTL_DISCARD_VOLUME_CACHE = 589828    # 0x00090054
    IO_CONTROL_RESET_WRITE_ORDER = 589832  # 0x000900F8


class FileConstants:
    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x00000080
    FLAGS_NO_BUFFERING = 536870912         # 0x20000000 - FILE_FLAG_NO_BUFFERING


class PrivilegeConstants:
    SE_DEBUG_NAME = "SeDebugPrivilege"
    SE_INCREASE_QUOTA_NAME = "SeIncreaseQuotaPrivilege"
    SE_PROF_SINGLE_PROCESS_NAME = "SeProfileSingleProcessPrivilege"
    SE_PRIVILEGE_ENABLED = 2


class SystemErrorCode:
    ERROR_SUCCESS = 0
    ERROR_ACCESS_DENIED = 5


class SystemInformationClass:
    SYSTEM_FILE_CACHE_INFORMATION = 21                 # 0x15
    SYSTEM_MEMORY_LIST_INFORMATION = 80                # 0x50
    SYSTEM_COMBINE_PHYSICAL_MEMORY_INFORMATION = 130   # 0x82
    SYSTEM_REGISTRY_RECONCILIATION_INFORMATION = 155   # 0x9B


class SystemMemoryListCommand:
    MEMORY_EMPTY_WORKING_SETS = 2
    MEMORY_FLUSH_MODIFIED_LIST = 3
    MEMORY_PURGE_STANDBY_LIST = 4
    MEMORY_PURGE_LOW_PRIORITY_STANDBY_LIST = 5


class MemoryAreas(IntFlag):
    NONE = 0
    COMBINED_PAGE_LIST = 1 << 0
    MODIFIED_FILE_CACHE = 1 << 1
    MODIFIED_PAGE_LIST = 1 << 2
    REGISTRY_CACHE = 1 << 3
    STANDBY_LIST = 1 << 4
    STANDBY_LIST_LOW_PRIORITY = 1 << 5
    SYSTEM_FILE_CACHE = 1 << 6
    WORKING_SET = 1 << 7

    ALL_DEEP = (
        WORKING_SET
        | SYSTEM_FILE_CACHE
        | MODIFIED_PAGE_LIST
        | STANDBY_LIST
        | COMBINED_PAGE_LIST
        | REGISTRY_CACHE
        | MODIFIED_FILE_CACHE
    )


# ==============================================================================
# Structs (from Structs.cs - exact Pack=1 layouts)
# ==============================================================================
class MemoryCombineInformationEx(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("Handle", ctypes.c_void_p),
        ("PagesCombined", ctypes.c_void_p),
        ("Flags", ctypes.c_int64),
    ]


class SystemFileCacheInformation32(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("CurrentSize", ctypes.c_int32),
        ("PeakSize", ctypes.c_int32),
        ("PageFaultCount", ctypes.c_int32),
        ("MinimumWorkingSet", ctypes.c_int32),
        ("MaximumWorkingSet", ctypes.c_int32),
        ("CurrentSizeIncludingTransitionInPages", ctypes.c_int32),
        ("PeakSizeIncludingTransitionInPages", ctypes.c_int32),
        ("TransitionRePurposeCount", ctypes.c_int32),
        ("Flags", ctypes.c_int32),
    ]


class SystemFileCacheInformation64(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("CurrentSize", ctypes.c_int64),
        ("PeakSize", ctypes.c_int64),
        ("PageFaultCount", ctypes.c_int64),
        ("MinimumWorkingSet", ctypes.c_int64),
        ("MaximumWorkingSet", ctypes.c_int64),
        ("CurrentSizeIncludingTransitionInPages", ctypes.c_int64),
        ("PeakSizeIncludingTransitionInPages", ctypes.c_int64),
        ("TransitionRePurposeCount", ctypes.c_int64),
        ("Flags", ctypes.c_int64),
    ]


class TokenPrivileges(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("Count", ctypes.c_int32),
        ("Luid", ctypes.c_int64),
        ("Attr", ctypes.c_int32),
    ]


# ==============================================================================
# NativeMethods bindings (64-bit safe, use_last_error=True)
# ==============================================================================
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
_ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
_psapi = ctypes.WinDLL("psapi", use_last_error=True)
_shell32 = ctypes.WinDLL("shell32", use_last_error=True)

_kernel32.GetCurrentProcess.restype = wintypes.HANDLE
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL

_kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_kernel32.OpenProcess.restype = wintypes.HANDLE

_kernel32.CreateFileW.argtypes = [
    wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
    ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE
]
_kernel32.CreateFileW.restype = wintypes.HANDLE

_kernel32.DeviceIoControl.argtypes = [
    wintypes.HANDLE, wintypes.DWORD,
    ctypes.c_void_p, wintypes.DWORD,
    ctypes.c_void_p, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p
]
_kernel32.DeviceIoControl.restype = wintypes.BOOL

_kernel32.FlushFileBuffers.argtypes = [wintypes.HANDLE]
_kernel32.FlushFileBuffers.restype = wintypes.BOOL

_kernel32.SetSystemFileCacheSize.argtypes = [ctypes.c_size_t, ctypes.c_size_t, wintypes.DWORD]
_kernel32.SetSystemFileCacheSize.restype = wintypes.BOOL

_kernel32.SetProcessWorkingSetSize.argtypes = [wintypes.HANDLE, ctypes.c_size_t, ctypes.c_size_t]
_kernel32.SetProcessWorkingSetSize.restype = wintypes.BOOL

_advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
_advapi32.OpenProcessToken.restype = wintypes.BOOL

_advapi32.LookupPrivilegeValueW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int64)]
_advapi32.LookupPrivilegeValueW.restype = wintypes.BOOL

_advapi32.AdjustTokenPrivileges.argtypes = [
    wintypes.HANDLE, wintypes.BOOL, ctypes.POINTER(TokenPrivileges),
    wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p
]
_advapi32.AdjustTokenPrivileges.restype = wintypes.BOOL

_ntdll.NtSetSystemInformation.argtypes = [ctypes.c_int32, ctypes.c_void_p, ctypes.c_uint32]
_ntdll.NtSetSystemInformation.restype = ctypes.c_uint32

_psapi.EmptyWorkingSet.argtypes = [wintypes.HANDLE]
_psapi.EmptyWorkingSet.restype = wintypes.BOOL


def is_admin() -> bool:
    try:
        return bool(_shell32.IsUserAnAdmin())
    except Exception:
        return False


def is_64bit_os() -> bool:
    return platform.machine().endswith("64") or ctypes.sizeof(ctypes.c_void_p) == 8


# ==============================================================================
# WinMemoryCleaner Engine (ported from ComputerService.cs)
# ==============================================================================
class WinMemoryCleanerEngine:
    """
    Exact Python port of IgorMundstein/WinMemoryCleaner's ComputerService.cs.
    """

    @staticmethod
    def set_increase_privilege(privilege_name: str) -> bool:
        """Port of ComputerService.SetIncreasePrivilege (with safe ctypes.get_last_error)."""
        h_token = wintypes.HANDLE()
        # TOKEN_ADJUST_PRIVILEGES (0x20) | TOKEN_QUERY (0x08) = 0x28
        if not _advapi32.OpenProcessToken(_kernel32.GetCurrentProcess(), 0x28, ctypes.byref(h_token)):
            return False
        try:
            new_state = TokenPrivileges()
            new_state.Count = 1
            new_state.Luid = 0
            new_state.Attr = PrivilegeConstants.SE_PRIVILEGE_ENABLED

            luid_val = ctypes.c_int64(0)
            if _advapi32.LookupPrivilegeValueW(None, privilege_name, ctypes.byref(luid_val)):
                new_state.Luid = luid_val.value
                ctypes.set_last_error(0)
                ok = _advapi32.AdjustTokenPrivileges(
                    h_token, False, ctypes.byref(new_state), 0, None, None
                )
                return bool(ok) and (ctypes.get_last_error() == SystemErrorCode.ERROR_SUCCESS)
            return False
        finally:
            _kernel32.CloseHandle(h_token)

    @staticmethod
    def _open_volume_handle(drive_letter: str) -> Optional[int]:
        """Port of ComputerService.OpenVolumeHandle."""
        if not drive_letter or not drive_letter.strip():
            return None
        clean = drive_letter.strip().rstrip(":\\/")
        vol_path = f"\\\\.\\{clean}:"
        handle = _kernel32.CreateFileW(
            vol_path,
            FileConstants.GENERIC_READ | FileConstants.GENERIC_WRITE,
            FileConstants.FILE_SHARE_READ | FileConstants.FILE_SHARE_WRITE,
            None,
            FileConstants.OPEN_EXISTING,
            FileConstants.FILE_ATTRIBUTE_NORMAL | FileConstants.FLAGS_NO_BUFFERING,
            None,
        )
        invalid = ctypes.c_void_p(-1).value
        if not handle or handle == invalid:
            return None
        return handle

    @classmethod
    def optimize_working_set(cls, exclusion_list: Optional[Set[str]] = None) -> int:
        """
        Port of ComputerService.OptimizeWorkingSet.
        Uses Kernel MemoryEmptyWorkingSets when no exclusion list is provided,
        or per-process EmptyWorkingSet when exclusions are active (or as fallback).
        Returns number of processes trimmed (or 1 on kernel-wide trim).
        """
        trimmed = 0
        if exclusion_list:
            cls.set_increase_privilege(PrivilegeConstants.SE_DEBUG_NAME)
            excluded_lower = {p.lower().replace(".exe", "") for p in exclusion_list}
            access_flags = 0x1000 | 0x0100  # PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_SET_QUOTA
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    pid = proc.info["pid"]
                    name = (proc.info["name"] or "").lower().replace(".exe", "")
                    if pid <= 4 or name in excluded_lower:
                        continue
                    h = _kernel32.OpenProcess(access_flags, False, pid)
                    if h:
                        try:
                            if _psapi.EmptyWorkingSet(h):
                                trimmed += 1
                        finally:
                            _kernel32.CloseHandle(h)
                except Exception:
                    continue
            return trimmed

        # 1. Kernel-level empty working sets (exact WinMemoryCleaner path)
        kernel_ok = False
        if cls.set_increase_privilege(PrivilegeConstants.SE_PROF_SINGLE_PROCESS_NAME):
            cmd = ctypes.c_int32(SystemMemoryListCommand.MEMORY_EMPTY_WORKING_SETS)
            status = _ntdll.NtSetSystemInformation(
                SystemInformationClass.SYSTEM_MEMORY_LIST_INFORMATION,
                ctypes.byref(cmd),
                ctypes.sizeof(cmd),
            )
            if status == SystemErrorCode.ERROR_SUCCESS:
                kernel_ok = True

        # 2. Per-process EmptyWorkingSet sweep with SeDebugPrivilege
        cls.set_increase_privilege(PrivilegeConstants.SE_DEBUG_NAME)
        access_flags = 0x1000 | 0x0100
        for proc in psutil.process_iter(["pid"]):
            try:
                pid = proc.info["pid"]
                if pid <= 4:
                    continue
                h = _kernel32.OpenProcess(access_flags, False, pid)
                if h:
                    try:
                        if _psapi.EmptyWorkingSet(h):
                            trimmed += 1
                    finally:
                        _kernel32.CloseHandle(h)
            except Exception:
                continue
        return max(trimmed, 1 if kernel_ok else 0)

    @classmethod
    def optimize_system_file_cache(cls) -> bool:
        """Port of ComputerService.OptimizeSystemFileCache."""
        if not cls.set_increase_privilege(PrivilegeConstants.SE_INCREASE_QUOTA_NAME):
            return False

        if is_64bit_os():
            sfci = SystemFileCacheInformation64(MinimumWorkingSet=-1, MaximumWorkingSet=-1)
        else:
            sfci = SystemFileCacheInformation32(MinimumWorkingSet=0x7FFFFFFF, MaximumWorkingSet=0x7FFFFFFF)

        status = _ntdll.NtSetSystemInformation(
            SystemInformationClass.SYSTEM_FILE_CACHE_INFORMATION,
            ctypes.byref(sfci),
            ctypes.sizeof(sfci),
        )
        ok_nt = (status == SystemErrorCode.ERROR_SUCCESS)

        file_cache_size = ctypes.c_size_t(-1)  # IntPtr.Subtract(IntPtr.Zero, 1) -> Flush
        ok_k32 = bool(_kernel32.SetSystemFileCacheSize(file_cache_size, file_cache_size, 0))
        return ok_nt or ok_k32

    @classmethod
    def optimize_modified_page_list(cls) -> bool:
        """Port of ComputerService.OptimizeModifiedPageList."""
        if not cls.set_increase_privilege(PrivilegeConstants.SE_PROF_SINGLE_PROCESS_NAME):
            return False

        cmd = ctypes.c_int32(SystemMemoryListCommand.MEMORY_FLUSH_MODIFIED_LIST)
        status = _ntdll.NtSetSystemInformation(
            SystemInformationClass.SYSTEM_MEMORY_LIST_INFORMATION,
            ctypes.byref(cmd),
            ctypes.sizeof(cmd),
        )
        return status == SystemErrorCode.ERROR_SUCCESS

    @classmethod
    def optimize_standby_list(cls, low_priority: bool = False) -> bool:
        """Port of ComputerService.OptimizeStandbyList."""
        if not cls.set_increase_privilege(PrivilegeConstants.SE_PROF_SINGLE_PROCESS_NAME):
            return False

        cmd_val = (
            SystemMemoryListCommand.MEMORY_PURGE_LOW_PRIORITY_STANDBY_LIST
            if low_priority
            else SystemMemoryListCommand.MEMORY_PURGE_STANDBY_LIST
        )
        cmd = ctypes.c_int32(cmd_val)
        status = _ntdll.NtSetSystemInformation(
            SystemInformationClass.SYSTEM_MEMORY_LIST_INFORMATION,
            ctypes.byref(cmd),
            ctypes.sizeof(cmd),
        )
        return status == SystemErrorCode.ERROR_SUCCESS

    @classmethod
    def optimize_combined_page_list(cls) -> bool:
        """Port of ComputerService.OptimizeCombinedPageList."""
        if not cls.set_increase_privilege(PrivilegeConstants.SE_PROF_SINGLE_PROCESS_NAME):
            return False

        mci = MemoryCombineInformationEx()
        status = _ntdll.NtSetSystemInformation(
            SystemInformationClass.SYSTEM_COMBINE_PHYSICAL_MEMORY_INFORMATION,
            ctypes.byref(mci),
            ctypes.sizeof(mci),
        )
        return status == SystemErrorCode.ERROR_SUCCESS

    @classmethod
    def optimize_registry_cache(cls) -> bool:
        """Port of ComputerService.OptimizeRegistryCache."""
        status = _ntdll.NtSetSystemInformation(
            SystemInformationClass.SYSTEM_REGISTRY_RECONCILIATION_INFORMATION,
            None,
            0,
        )
        return status == SystemErrorCode.ERROR_SUCCESS

    @classmethod
    def optimize_modified_file_cache(cls) -> int:
        """Port of ComputerService.OptimizeModifiedFileCache (including DeviceIoControl calls)."""
        flushed_volumes = 0
        seen = set()

        for part in psutil.disk_partitions(all=False):
            if "fixed" not in part.opts.lower():
                continue
            drive_letter = part.device.rstrip("\\/").upper()
            if len(drive_letter) != 2 or not drive_letter.endswith(":") or drive_letter in seen:
                continue
            seen.add(drive_letter)

            handle = cls._open_volume_handle(drive_letter)
            if not handle:
                continue

            try:
                bytes_returned = wintypes.DWORD(0)

                # 1. IO_CONTROL_RESET_WRITE_ORDER (Windows 7+)
                try:
                    buf = (ctypes.c_byte * 1)(0)
                    _kernel32.DeviceIoControl(
                        handle,
                        DriveConstants.IO_CONTROL_RESET_WRITE_ORDER,
                        buf,
                        1,
                        None,
                        0,
                        ctypes.byref(bytes_returned),
                        None,
                    )
                except Exception:
                    pass

                # 2. FSCTL_DISCARD_VOLUME_CACHE (Windows 8+)
                try:
                    _kernel32.DeviceIoControl(
                        handle,
                        DriveConstants.FSCTL_DISCARD_VOLUME_CACHE,
                        None,
                        0,
                        None,
                        0,
                        ctypes.byref(bytes_returned),
                        None,
                    )
                except Exception:
                    pass

                # 3. FlushFileBuffers
                if _kernel32.FlushFileBuffers(handle):
                    flushed_volumes += 1
            finally:
                _kernel32.CloseHandle(handle)

        return flushed_volumes

    @classmethod
    def optimize(cls, areas: MemoryAreas = MemoryAreas.ALL_DEEP, exclusion_list: Optional[Set[str]] = None) -> Dict[str, Any]:
        """
        Port of ComputerService.Optimize(reason, areas) — exact same execution order:
        1. Working Set
        2. System File Cache
        3. Modified Page List
        4. Standby List (or Low Priority Standby List)
        5. Combined Page List
        6. Registry Cache
        7. Modified File Cache
        8. Garbage Collector & self trim
        """
        cleaned: List[str] = []
        trimmed_procs = 0

        if areas & MemoryAreas.WORKING_SET:
            trimmed_procs = cls.optimize_working_set(exclusion_list=exclusion_list)
            if trimmed_procs > 0:
                cleaned.append("Working Set")

        if areas & MemoryAreas.SYSTEM_FILE_CACHE:
            if cls.optimize_system_file_cache():
                cleaned.append("System File Cache")

        if areas & MemoryAreas.MODIFIED_PAGE_LIST:
            if cls.optimize_modified_page_list():
                cleaned.append("Modified Page List")

        if areas & (MemoryAreas.STANDBY_LIST | MemoryAreas.STANDBY_LIST_LOW_PRIORITY):
            low_prio = bool(areas & MemoryAreas.STANDBY_LIST_LOW_PRIORITY) and not bool(areas & MemoryAreas.STANDBY_LIST)
            if cls.optimize_standby_list(low_priority=low_prio):
                cleaned.append("Standby List (Low Priority)" if low_prio else "Standby List")

        if areas & MemoryAreas.COMBINED_PAGE_LIST:
            if cls.optimize_combined_page_list():
                cleaned.append("Combined Page List")

        if areas & MemoryAreas.REGISTRY_CACHE:
            if cls.optimize_registry_cache():
                cleaned.append("Registry Cache")

        if areas & MemoryAreas.MODIFIED_FILE_CACHE:
            if cls.optimize_modified_file_cache() > 0:
                cleaned.append("Modified File Cache")

        # Garbage Collector + release current process working set (App.ReleaseMemory equivalent)
        gc.collect()
        try:
            _kernel32.SetProcessWorkingSetSize(
                _kernel32.GetCurrentProcess(),
                ctypes.c_size_t(-1),
                ctypes.c_size_t(-1),
            )
        except Exception:
            pass

        return {
            "areas_cleaned": cleaned,
            "processes_trimmed": trimmed_procs,
            "is_admin": is_admin(),
        }
