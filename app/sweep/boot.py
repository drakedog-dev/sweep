"""Boot X-ray: how long Windows takes to start and what slows it down.

Windows records this itself in the Microsoft-Windows-Diagnostics-Performance/Operational log:
event 100 is one boot (BootTime = MainPathBootTime + BootPostBootTime, in ms),
events 101-110 name what made that boot slower (apps, drivers, services...) and by how much.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from . import platform as P

LOG = "Microsoft-Windows-Diagnostics-Performance/Operational"
KINDS = {101: "app", 102: "driver", 103: "service", 104: "system", 105: "system", 106: "system",
         107: "policy", 108: "policy", 109: "device", 110: "system"}

_SCRIPT = r'''
$out=@()
$ev=Get-WinEvent -LogName 'Microsoft-Windows-Diagnostics-Performance/Operational' -MaxEvents 600 -ErrorAction SilentlyContinue | ? { $_.Id -ge 100 -and $_.Id -le 110 }
foreach($e in $ev){
  $x=[xml]$e.ToXml(); $d=@{}
  foreach($n in $x.Event.EventData.Data){ if($n.Name){ $d[[string]$n.Name]=[string]$n.'#text' } }
  $out+=@{id=$e.Id; t=$e.TimeCreated.ToString('o'); d=$d}
}
,$out'''


def _demo_events() -> list[dict]:
    now = datetime.now().replace(microsecond=0)
    out = []
    boots = [(0, 29400, 21300), (1, 31200, 22800), (2, 47800, 28900), (4, 52100, 30100), (5, 49600, 29500), (7, 55300, 31800),
             (9, 51000, 30500), (11, 58700, 33000), (13, 50200, 30300), (15, 54100, 31700)]
    for days, total, main in boots:
        t = now - timedelta(days=days, hours=days % 3)
        out.append({"id": 100, "t": t.isoformat(), "d": {"BootTime": str(total), "MainPathBootTime": str(main), "BootPostBootTime": str(total - main)}})
        if days >= 2:
            out.append({"id": 101, "t": (t + timedelta(seconds=2)).isoformat(), "d": {"Name": "Discord.exe", "FriendlyName": "Discord", "DegradationTime": "6200", "TotalTime": "9100"}})
            out.append({"id": 101, "t": (t + timedelta(seconds=2)).isoformat(), "d": {"Name": "OneDrive.exe", "FriendlyName": "Microsoft OneDrive", "DegradationTime": "4100", "TotalTime": "5600"}})
            out.append({"id": 103, "t": (t + timedelta(seconds=3)).isoformat(), "d": {"Name": "SysMain", "FriendlyName": "SysMain", "DegradationTime": "2300", "TotalTime": "3900"}})
        if days >= 4:
            out.append({"id": 101, "t": (t + timedelta(seconds=2)).isoformat(), "d": {"Name": "steam.exe", "FriendlyName": "Steam Client Bootstrapper", "DegradationTime": "3800", "TotalTime": "5200"}})
            out.append({"id": 102, "t": (t + timedelta(seconds=3)).isoformat(), "d": {"Name": "RtkAudUService64.exe", "FriendlyName": "Realtek HD Audio", "DegradationTime": "1700", "TotalTime": "2400"}})
    return out


def read_events() -> list[dict]:
    if not P.IS_WINDOWS:
        return _demo_events()
    data = P.ps_json(_SCRIPT, 90)
    if isinstance(data, dict):
        data = [data]
    return data if isinstance(data, list) else []


def _ms(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _time(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def analyse(events: list[dict], max_boots: int = 15, culprit_boots: int = 5) -> dict:
    """{boots: [{t, total, main, post}] newest first, culprits: [{name, file, kind, avg, max, count}], last, avg}"""
    boots = []
    for e in events:
        if e.get("id") != 100:
            continue
        t = _time(e.get("t", ""))
        d = e.get("d") or {}
        total = _ms(d.get("BootTime"))
        if t is None or total <= 0 or total > 30 * 60 * 1000:     # ignore broken records
            continue
        main = _ms(d.get("MainPathBootTime"))
        post = _ms(d.get("BootPostBootTime")) or max(0.0, total - main)
        boots.append({"t": t, "total": total / 1000, "main": main / 1000, "post": post / 1000, "items": []})
    boots.sort(key=lambda b: b["t"], reverse=True)
    boots = boots[:max_boots]

    for e in events:
        k = KINDS.get(e.get("id"))
        t = _time(e.get("t", ""))
        if not k or t is None or not boots:
            continue
        b = min(boots, key=lambda x: abs((x["t"] - t).total_seconds()))
        if abs((b["t"] - t).total_seconds()) > 15 * 60:
            continue
        d = e.get("d") or {}
        deg = _ms(d.get("DegradationTime")) / 1000
        if deg <= 0:
            continue
        name = (d.get("FriendlyName") or d.get("Name") or "").strip() or "?"
        b["items"].append({"name": name, "file": (d.get("Name") or "").strip(), "kind": k, "deg": deg})

    agg: dict[str, dict] = {}
    for b in boots[:culprit_boots]:
        for it in b["items"]:
            a = agg.setdefault(it["name"].lower(), {"name": it["name"], "file": it["file"], "kind": it["kind"], "sum": 0.0, "max": 0.0, "count": 0})
            a["sum"] += it["deg"]
            a["max"] = max(a["max"], it["deg"])
            a["count"] += 1
    culprits = sorted(({"name": a["name"], "file": a["file"], "kind": a["kind"], "avg": round(a["sum"] / a["count"], 1),
                        "max": round(a["max"], 1), "count": a["count"]} for a in agg.values()), key=lambda c: c["avg"], reverse=True)[:12]
    totals = [b["total"] for b in boots]
    return {
        "boots": [{"t": b["t"].isoformat(timespec="minutes"), "total": round(b["total"], 1), "main": round(b["main"], 1), "post": round(b["post"], 1)} for b in boots],
        "culprits": culprits,
        "last": round(totals[0], 1) if totals else 0.0,
        "avg": round(sum(totals) / len(totals), 1) if totals else 0.0,
        "best": round(min(totals), 1) if totals else 0.0,
        "seen": len(culprits),
        "window": min(culprit_boots, len(boots)),
    }


def verdict(seconds: float) -> str:
    """fast / ok / slow, for colours and the headline."""
    if seconds <= 0:
        return "none"
    return "fast" if seconds < 30 else "ok" if seconds < 60 else "slow"


def restart_now() -> None:
    if P.IS_WINDOWS:
        import subprocess
        subprocess.Popen(["shutdown.exe", "/r", "/t", "5", "/c", "Sweep: restart to measure boot time"])
