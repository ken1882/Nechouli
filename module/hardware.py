# hardware_fingerprint.py
"""
Cross-platform “hardware hash” helper
  • Windows   → SMBIOS UUID  → MachineGuid  → CPU + MAC
  • macOS     → IOPlatformUUID → IOPlatformSerialNumber → CPU + MAC
  • Linux     → product_uuid → /etc/machine-id         → CPU + MAC
The final digest is SHA-256(app_id + json(fields)).
"""

import hashlib, json, os, platform, re, subprocess, uuid, sys, pathlib

APP_SALT = "nechouli"

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

# ---------- helpers shared by all OSes ----------
def _primary_mac() -> str:
    m = uuid.getnode()
    return ("%012X" % m) if (m >> 40) % 2 == 0 else ""   # ignore random MACs

def _cpu_sig() -> str:
    # just vendor + family/model/stepping
    if sys.platform == "win32":
        try:
            import ctypes, ctypes.wintypes as wt
            class SYSTEM_INFO(ctypes.Structure):
                _fields_ = [("wProcessorArchitecture", wt.WORD),
                            ("wReserved", wt.WORD),
                            ("dwPageSize", wt.DWORD),
                            ("lpMinimumApplicationAddress", wt.LPVOID),
                            ("lpMaximumApplicationAddress", wt.LPVOID),
                            ("dwActiveProcessorMask", wt.LPVOID),
                            ("dwNumberOfProcessors", wt.DWORD),
                            ("dwProcessorType", wt.DWORD),
                            ("dwAllocationGranularity", wt.DWORD),
                            ("wProcessorLevel", wt.WORD),
                            ("wProcessorRevision", wt.WORD)]
            GetNativeSystemInfo = ctypes.windll.kernel32.GetNativeSystemInfo
            info = SYSTEM_INFO()
            GetNativeSystemInfo(ctypes.byref(info))
            return f"{info.wProcessorArchitecture:04x}-{info.wProcessorLevel:04x}-{info.wProcessorRevision:04x}"
        except Exception:
            return ""
    else:
        try:
            out = pathlib.Path("/proc/cpuinfo").read_text()
            m = re.search(r"model name\s*:\s*(.+)", out)
            return _sha256(m.group(1))[:16] if m else ""
        except Exception:
            return ""
# ---------- Windows ----------
def _win_bios_uuid() -> str:
    try:
        import subprocess, json
        o = subprocess.check_output(["wmic", "csproduct", "get", "uuid", "/format:list"],
                                    stderr=subprocess.DEVNULL, text=True)
        m = re.search(r"UUID=(.*)", o)
        return m.group(1).strip() if m else ""
    except Exception:
        return ""

def _win_machine_guid() -> str:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography") as k:
            return winreg.QueryValueEx(k, "MachineGuid")[0]
    except Exception:
        return ""

# ---------- macOS ----------
def _mac_ioplatform_uuid() -> str:
    try:
        o = subprocess.check_output(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                                    text=True)
        m = re.search(r'"IOPlatformUUID" = "(.+?)"', o)
        return m.group(1) if m else ""
    except Exception:
        return ""

def _mac_serial() -> str:
    try:
        o = subprocess.check_output(["system_profiler", "SPHardwareDataType"],
                                    text=True)
        m = re.search(r"Serial Number.*: (.+)", o)
        return m.group(1).strip() if m else ""
    except Exception:
        return ""

# ---------- Linux ----------
def _linux_product_uuid() -> str:
    p = pathlib.Path("/sys/class/dmi/id/product_uuid")
    try:
        return p.read_text().strip()
    except Exception:
        return ""

def _linux_machine_id() -> str:
    for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            t = pathlib.Path(path).read_text().strip()
            if t: return t
        except Exception:
            pass
    return ""

# ---------- Main public API ----------
def hardware_hash(app_salt: str = APP_SALT) -> str:
    fields = {}

    if sys.platform == "win32":
        fields["uuid"] = _win_bios_uuid()
        if not fields["uuid"]:
            fields["uuid"] = _win_machine_guid()
    elif sys.platform == "darwin":
        fields["uuid"] = _mac_ioplatform_uuid() or _mac_serial()
    else:  # assume Linux/Unix
        fields["uuid"] = _linux_product_uuid() or _linux_machine_id()

    # fallbacks for any platform
    fields.setdefault("cpu", _cpu_sig())
    fields.setdefault("mac", _primary_mac())

    blob = json.dumps({k:v for k,v in fields.items() if v}, separators=(",",":"))
    return _sha256(app_salt + blob)

if __name__ == "__main__":
    print(hardware_hash())
