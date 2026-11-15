"""Free RAM on the machine and memory used by this process, standard library only."""
import ctypes
import os
import sys

MB = 1024 * 1024

if sys.platform == "win32":
    from ctypes import wintypes

    class _MemStatus(ctypes.Structure):
        _fields_ = [
            ("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    class _ProcMem(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _psapi = ctypes.WinDLL("psapi", use_last_error=True)
    _kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    _psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ProcMem), wintypes.DWORD]

    def free_ram_mb():
        st = _MemStatus()
        st.dwLength = ctypes.sizeof(st)
        if not _kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
            return None
        return int(st.ullAvailPhys // MB)

    def engine_mb():
        pm = _ProcMem()
        pm.cb = ctypes.sizeof(pm)
        if not _psapi.GetProcessMemoryInfo(_kernel32.GetCurrentProcess(), ctypes.byref(pm), pm.cb):
            return None
        return int(pm.WorkingSetSize // MB)

else:
    def _meminfo_kb(path, key):
        try:
            with open(path, encoding="ascii") as f:
                for line in f:
                    if line.startswith(key):
                        return int(line.split()[1])
        except OSError:
            pass
        return None

    def free_ram_mb():
        kb = _meminfo_kb("/proc/meminfo", "MemAvailable:")
        return None if kb is None else kb // 1024

    def engine_mb():
        kb = _meminfo_kb(f"/proc/{os.getpid()}/status", "VmRSS:")
        return None if kb is None else kb // 1024
