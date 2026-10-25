"""Operating-system layer. On Windows it talks to the registry, services and WMI;
anywhere else it serves demo data so the UI can be developed and screenshotted."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"
APP_VERSION = "1.0.16"
UPDATE_REPO = "drakedog-dev/sweep"


def data_root() -> Path:
    if IS_WINDOWS:
        base = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
    else:
        base = Path.home() / ".local" / "share"
    p = base / "Sweep"
    p.mkdir(parents=True, exist_ok=True)
    return p


ROOT = data_root()
QUARANTINE = ROOT / "Quarantine"
REG_BACKUP = ROOT / "RegBackup"
LOG_FILE = ROOT / "log.txt"
SETTINGS_FILE = ROOT / "settings.json"
for _d in (QUARANTINE, REG_BACKUP):
    _d.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    try:
        from datetime import datetime
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}\n")
    except Exception:
        pass


def load_settings() -> dict:
    try:
        return json.loads(SETTINGS_FILE.read_text("utf-8"))
    except Exception:
        return {}


def save_settings(d: dict) -> None:
    try:
        SETTINGS_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), "utf-8")
    except Exception as e:
        log(f"settings: {e}")


def powershell(script: str, timeout: int = 120) -> str:
    """Run a PowerShell snippet hidden and return stdout. Windows only."""
    if not IS_WINDOWS:
        return ""
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    try:
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, startupinfo=si,
        )
        return r.stdout
    except Exception as e:
        log(f"powershell: {e}")
        return ""


def ps_json(script: str, timeout: int = 120):
    out = powershell(f"$__r = & {{ {script} }}; ConvertTo-Json -InputObject $__r -Depth 6 -Compress", timeout)
    out = out.strip()
    if not out:
        return None
    try:
        return json.loads(out)
    except Exception:
        return None


def expand(p: str) -> str:
    return os.path.expandvars(p)


# ---------------- administrator rights ----------------
def is_admin() -> bool:
    """True when the process runs elevated (or on a non-Windows demo machine)."""
    if not IS_WINDOWS:
        return True
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


_SKIP_WITH_VALUE = ("--page", "--do")
_SKIP_FLAGS = ("--limited", "--no-elevate")


def _own_args() -> list[str]:
    """Current command line without the one-shot flags used for relaunching."""
    out, skip = [], False
    for a in sys.argv[1:]:
        if skip:
            skip = False
            continue
        if a in _SKIP_WITH_VALUE:
            skip = True
            continue
        if a in _SKIP_FLAGS:
            continue
        out.append(a)
    return out


def relaunch_elevated(extra: list[str] | None = None) -> bool:
    """Start an elevated copy of Sweep through the UAC prompt.
    Returns True when the new copy was started (the caller should quit), False when the user declined."""
    if not IS_WINDOWS:
        return False
    import ctypes
    from ctypes import wintypes
    args = _own_args() + list(extra or [])
    if getattr(sys, "frozen", False):
        exe = sys.executable
    else:
        exe = sys.executable
        args = [os.path.abspath(sys.argv[0])] + args
    params = subprocess.list2cmdline(args)
    fn = ctypes.windll.shell32.ShellExecuteW
    fn.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_int]
    fn.restype = ctypes.c_void_p
    try:
        rc = fn(None, "runas", exe, params, None, 1) or 0
    except Exception as e:
        log(f"elevate: {e}")
        return False
    if rc <= 32:
        log(f"elevate: declined or failed ({rc})")
        return False
    return True


def is_access_denied(e: BaseException) -> bool:
    return isinstance(e, PermissionError) or getattr(e, "winerror", None) == 5 or "WinError 5" in str(e)


ANTIVIRUS = ""   # filled by log_context(): names reported by Windows Security Center


def third_party_av() -> str:
    """Antivirus other than Microsoft Defender, e.g. 'Kaspersky Total Security' (empty if none)."""
    names = [n.strip() for n in ANTIVIRUS.split(",") if n.strip()]
    return ", ".join(n for n in names if "defender" not in n.lower())


def log_context() -> None:
    """One line in the log describing how Sweep runs: helps when settings do not stick on a particular PC."""
    if not IS_WINDOWS:
        return
    import platform as _pf
    try:
        info = ps_json("$id=[Security.Principal.WindowsIdentity]::GetCurrent(); "
                   "$av=@(Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct -ErrorAction SilentlyContinue | % { $_.displayName }) -join ', '; "
                   "$os=Get-CimInstance Win32_OperatingSystem; "
                   "@{user=$id.Name; av=$av; os=[string]$os.Caption + ' ' + [string]$os.BuildNumber}", 40)
    except Exception:
        info = None
    if not isinstance(info, dict):
        info = {}
    global ANTIVIRUS
    ANTIVIRUS = str(info.get("av") or "")
    log(f"context: Sweep {APP_VERSION}, admin={is_admin()}, {_pf.architecture()[0]}, user={info.get('user', '?')}, "
        f"os={info.get('os', '?')}, antivirus={info.get('av') or 'none reported'}, exe={sys.executable}")

