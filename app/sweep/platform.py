"""Operating-system layer. On Windows it talks to the registry, services and WMI;
anywhere else it serves demo data so the UI can be developed and screenshotted."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"
APP_VERSION = "1.0.3"
UPDATE_REPO = "pabloescobarbl-ops/sweep"


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
