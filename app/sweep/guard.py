"""Guard: big Windows updates quietly switch tracking back on and reinstall promoted apps.
Sweep remembers what the user chose (the baseline), checks it at log-on and once a day through a
scheduled task, and either puts things back by itself or asks with a notification."""
from __future__ import annotations

from datetime import datetime

from . import extras, tweaks
from . import platform as P

TASK = "Sweep Guard"
DEFAULTS = {"enabled": False, "auto": False, "privacy": None, "apps": [], "lastRun": "", "lastBuild": "", "events": [], "pending": {}}


def state(settings: dict) -> dict:
    g = settings.setdefault("guard", {})
    for k, v in DEFAULTS.items():
        g.setdefault(k, v if not isinstance(v, (list, dict)) else type(v)())
    return g


def init_baseline(settings: dict, privacy_state: dict) -> None:
    """First start of a version with Guard: whatever is switched off now is what the user wants."""
    g = state(settings)
    if g["privacy"] is None:
        g["privacy"] = sorted(pid for pid, protected in privacy_state.items() if protected)


def remember_privacy(settings: dict, pid: str, protected: bool) -> None:
    g = state(settings)
    cur = set(g["privacy"] or [])
    (cur.add if protected else cur.discard)(pid)
    g["privacy"] = sorted(cur)


def remember_apps(settings: dict, ids) -> None:
    g = state(settings)
    g["apps"] = sorted(set(g["apps"]) | set(ids))


def windows_build() -> str:
    if not P.IS_WINDOWS:
        return "26100.4061"
    key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
    cur, ubr = tweaks.reg_get("HKLM", key, "CurrentBuild"), tweaks.reg_get("HKLM", key, "UBR")
    return f"{cur}.{ubr}" if cur and ubr is not None else str(cur or "")


def check(settings: dict) -> dict:
    """What Windows has put back since the user's choice."""
    g = state(settings)
    watched = set(g["privacy"] or [])
    reverted = [p.id for p in tweaks.PRIVACY if p.id in watched and not tweaks.privacy_state(p)]
    back = []
    if g["apps"]:
        present = {a["id"] for a in extras.installed_bloat()}
        back = [a for a in g["apps"] if a in present]
    build = windows_build()
    return {"privacy": reverted, "apps": back, "build": build, "t": datetime.now().isoformat(timespec="minutes"),
            "buildChanged": bool(g["lastBuild"]) and build != g["lastBuild"]}


def fix(found: dict) -> list[str]:
    """Switch reverted items off again and remove apps that came back. Returns what still failed."""
    failed: list[str] = []
    for p in tweaks.PRIVACY:
        if p.id in found.get("privacy", []):
            if tweaks.set_privacy(p, True) or not tweaks.privacy_state(p):
                failed.append(p.id)
    for app_id in found.get("apps", []):
        try:
            extras.remove_app(app_id)
        except Exception as e:  # noqa: BLE001
            P.log(f"guard: remove {app_id}: {e}")
            failed.append(app_id)
    return failed


def record(settings: dict, found: dict, fixed: bool) -> None:
    g = state(settings)
    g["lastRun"], g["lastBuild"] = found["t"], found["build"]
    old = g.get("pending") or {}
    same = sorted(old.get("privacy", [])) == sorted(found["privacy"]) and sorted(old.get("apps", [])) == sorted(found["apps"])
    if (found["privacy"] or found["apps"]) and (not same or fixed):
        g["events"].insert(0, {"t": found["t"], "build": found["build"], "buildChanged": found["buildChanged"],
                               "privacy": found["privacy"], "apps": found["apps"], "fixed": fixed})
        del g["events"][20:]
    g["pending"] = {} if fixed or not (found["privacy"] or found["apps"]) else {"privacy": found["privacy"], "apps": found["apps"], "build": found["build"]}


def set_task(enabled: bool, exe: str) -> None:
    """Scheduled task: three minutes after log-on and every day at noon, elevated, only while the user is signed in."""
    if not P.IS_WINDOWS:
        return
    if enabled:
        P.powershell(
            f"$a=New-ScheduledTaskAction -Execute '{exe}' -Argument '--guard'; "
            "$t1=New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME; $t1.Delay='PT3M'; "
            "$t2=New-ScheduledTaskTrigger -Daily -At 12:00; "
            "$s=New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 10); "
            f"Register-ScheduledTask -TaskName '{TASK}' -Action $a -Trigger @($t1,$t2) -Settings $s -RunLevel Highest -User $env:USERNAME -Force | Out-Null", 60)
    else:
        P.powershell(f"Unregister-ScheduledTask -TaskName '{TASK}' -Confirm:$false -ErrorAction SilentlyContinue", 30)


def task_exists() -> bool:
    if not P.IS_WINDOWS:
        return False
    return P.powershell(f"if(Get-ScheduledTask -TaskName '{TASK}' -ErrorAction SilentlyContinue){{'yes'}}", 30).strip() == "yes"
