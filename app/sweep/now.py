"""What is slowing the PC down right now: running processes grouped by program, in plain words.

Nothing here changes Windows. The only actions are the ones a person would take in Task Manager, and only on a click:
closing a program the normal way (as if its window was closed) and lowering its priority until it restarts.
"""
from __future__ import annotations

import os
import subprocess
import time

import psutil

from . import platform as P

# Parts of Windows and of security software: explained, never closed from Sweep
_SYSTEM = {
    "defender": ("msmpeng.exe", "nissrv.exe", "mpcmdrun.exe", "mpdefendercoreservice.exe", "securityhealthservice.exe", "smartscreen.exe"),
    "update": ("tiworker.exe", "trustedinstaller.exe", "mousocoreworker.exe", "usocoreworker.exe", "wuauclt.exe", "waasmedicagent.exe",
               "sihclient.exe", "usoclient.exe", "musnotification.exe", "dismhost.exe"),
    "search": ("searchindexer.exe", "searchprotocolhost.exe", "searchfilterhost.exe"),
    "compression": ("memory compression",),
    "kernel": ("system", "registry", "secure system", "interrupts"),
    "dwm": ("dwm.exe",),
    "explorer": ("explorer.exe", "searchhost.exe", "startmenuexperiencehost.exe", "shellexperiencehost.exe", "textinputhost.exe"),
    "wmi": ("wmiprvse.exe",),
    "telemetry": ("compattelrunner.exe", "devicecensus.exe"),
    "antivirus": ("avp.exe", "avpui.exe", "kavfs.exe", "ekrn.exe", "egui.exe", "avastsvc.exe", "avastui.exe", "avgsvc.exe", "avgui.exe",
                  "mbamservice.exe", "mbam.exe", "bdservicehost.exe", "bdagent.exe", "dwservice.exe", "spideragent.exe", "nortonsecurity.exe",
                  "mcshield.exe", "psanhost.exe"),
    "installer": ("msiexec.exe",),
    "services": ("svchost.exe", "services.exe", "lsass.exe", "csrss.exe", "wininit.exe", "winlogon.exe", "smss.exe", "fontdrvhost.exe",
                 "spoolsv.exe", "audiodg.exe", "sihost.exe", "taskhostw.exe", "runtimebroker.exe", "conhost.exe", "ctfmon.exe", "dllhost.exe",
                 "lsaiso.exe", "wudfhost.exe", "dashost.exe", "msdtc.exe", "sgrmbroker.exe", "unsecapp.exe", "systemsettings.exe"),
}
_OWNER = {exe: kind for kind, names in _SYSTEM.items() for exe in names}
# services inside svchost.exe that deserve their own explanation
_SERVICES = {"wuauserv": "update", "bits": "update", "dosvc": "update", "usosvc": "update", "diagtrack": "telemetry", "sysmain": "sysmain"}
_SECURITY = {"defender", "antivirus"}

BROWSERS = {"chrome.exe": "chrome", "msedge.exe": "edge", "firefox.exe": "firefox", "opera.exe": "opera", "brave.exe": "brave",
            "vivaldi.exe": "vivaldi", "browser.exe": "yandex"}
BROWSER_NAMES = {"chrome": "Google Chrome", "edge": "Microsoft Edge", "firefox": "Firefox", "opera": "Opera", "brave": "Brave",
                 "vivaldi": "Vivaldi", "yandex": "Яндекс Браузер"}
# where the browser's own memory saving is switched on (pasted into its address bar)
MEMORY_SAVER = {"chrome": "chrome://settings/performance", "edge": "edge://settings/system/managePerformance",
                "brave": "brave://settings/performance", "vivaldi": "vivaldi://settings/performance", "opera": "opera://settings/performance"}

_desc_cache: dict[str, str] = {}


def file_description(path: str) -> str:
    """The name Windows shows in Task Manager ("Google Chrome", "Telegram Desktop"), from the program file itself."""
    if not path or not P.IS_WINDOWS:
        return ""
    if path in _desc_cache:
        return _desc_cache[path]
    name = ""
    try:
        import ctypes
        from ctypes import wintypes
        ver = ctypes.windll.version
        size = ver.GetFileVersionInfoSizeW(path, None)
        if size:
            buf = ctypes.create_string_buffer(size)
            if ver.GetFileVersionInfoW(path, 0, size, buf):
                ptr, ln = ctypes.c_void_p(), wintypes.UINT()
                langs = []
                if ver.VerQueryValueW(buf, r"\VarFileInfo\Translation", ctypes.byref(ptr), ctypes.byref(ln)) and ln.value >= 4:
                    arr = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_ushort * (ln.value // 2))).contents
                    langs = [f"{arr[i]:04x}{arr[i + 1]:04x}" for i in range(0, len(arr) - 1, 2)]
                for lang in langs + ["040904b0", "041904b0", "040904e4"]:
                    for field in ("FileDescription", "ProductName"):
                        if ver.VerQueryValueW(buf, rf"\StringFileInfo\{lang}\{field}", ctypes.byref(ptr), ctypes.byref(ln)) and ln.value > 1:
                            name = ctypes.wstring_at(ptr, ln.value - 1).strip()
                            if name:
                                break
                    if name:
                        break
    except Exception:  # noqa: BLE001
        name = ""
    _desc_cache[path] = name
    return name


class Sampler:
    """Keeps the processes between two looks: CPU and disk use are differences between samples."""

    def __init__(self):
        self._procs: dict[int, psutil.Process] = {}
        self._io: dict[int, int] = {}
        self._t = time.monotonic()
        self._disk = self._disk_times()
        self._svc: dict[int, str] = {}
        self._svc_at = 0.0
        self.lowered: set[str] = set()          # programs whose priority Sweep lowered (until they restart)
        self.cores = psutil.cpu_count() or 1

    @staticmethod
    def _disk_times():
        try:
            io = psutil.disk_io_counters()
            return (io.read_time + io.write_time) if io else None
        except Exception:  # noqa: BLE001
            return None

    def _services(self) -> dict[int, str]:
        """svchost.exe pid -> the explained service it runs (Windows Update, telemetry, SysMain); refreshed every 20 s."""
        if not P.IS_WINDOWS or time.monotonic() - self._svc_at < 20:
            return self._svc
        out: dict[int, str] = {}
        for s in psutil.win_service_iter():
            kind = _SERVICES.get(s.name().lower())
            if not kind:
                continue
            try:
                pid = s.pid()
            except Exception:  # noqa: BLE001
                continue
            if pid:
                out[pid] = kind
        self._svc, self._svc_at = out, time.monotonic()
        return out

    def sample(self) -> dict:
        if not P.IS_WINDOWS:
            return demo(self)
        now = time.monotonic()
        dt = max(0.2, now - self._t)
        self._t = now
        seen: set[int] = set()
        groups: dict[str, dict] = {}
        svc = self._services()
        me = os.getpid()
        for p in psutil.process_iter(["name", "exe"]):
            pid = p.pid
            if pid == 0:
                continue
            seen.add(pid)
            proc = self._procs.get(pid)
            if proc is None:
                proc = p
                self._procs[pid] = p
                try:
                    p.cpu_percent(None)                  # the first call only starts counting
                except psutil.Error:
                    pass
            try:
                cpu = proc.cpu_percent(None) / self.cores
                mem = proc.memory_info()
                ram = getattr(mem, "private", 0) or mem.rss
            except psutil.Error:
                continue
            disk = 0.0
            try:
                io = proc.io_counters()
                total = io.read_bytes + io.write_bytes
                if pid in self._io:
                    disk = max(0, total - self._io[pid]) / dt
                self._io[pid] = total
            except (psutil.Error, AttributeError):
                pass
            name = (p.info.get("name") or "").lower()
            exe = p.info.get("exe") or ""
            key, kind, title = self._identify(pid, name, exe, svc, me)
            g = groups.setdefault(key, {"key": key, "kind": kind, "title": title, "exe": exe, "pids": [], "cpu": 0.0, "ram": 0.0, "disk": 0.0})
            g["pids"].append(pid)
            g["cpu"] += cpu
            g["ram"] += ram
            g["disk"] += disk
            if not g["exe"] and exe:
                g["exe"] = exe
        for pid in list(self._procs):
            if pid not in seen:
                self._procs.pop(pid, None)
                self._io.pop(pid, None)
        return self._summary(list(groups.values()), dt)

    def _identify(self, pid: int, name: str, exe: str, svc: dict, me: int) -> tuple[str, str, str]:
        """(group key, kind, title). kind: a part of Windows (its explanation key), "browser", "self" or "app"."""
        if pid == me or (name == "sweep.exe" and "sweep" in exe.lower()):
            return "self", "self", P.APP_NAME
        if name == "svchost.exe" and pid in svc:
            return "sys:" + svc[pid], svc[pid], ""
        if name in _OWNER:
            kind = _OWNER[name]
            return "sys:" + kind, kind, ""
        b = BROWSERS.get(name)
        if b and (b != "yandex" or "yandex" in exe.lower()):
            return "browser:" + b, "browser", BROWSER_NAMES[b]
        title = file_description(exe) or (os.path.splitext(name)[0] if name else "?")
        return "app:" + (exe.lower() or name), "app", title

    def _summary(self, groups: list[dict], dt: float) -> dict:
        vm = psutil.virtual_memory()
        cpu = psutil.cpu_percent(None)
        busy = None
        t = self._disk_times()
        if t is not None and self._disk is not None:
            busy = min(100.0, max(0.0, (t - self._disk) / (dt * 1000) * 100))
        self._disk = t
        return finish(groups, cpu, vm.percent, vm.used, vm.total, busy, self.lowered)


def finish(groups: list[dict], cpu: float, ram_pct: float, ram_used: float, ram_total: float, disk_busy: float | None, lowered: set) -> dict:
    """Order the programs by how much they weigh on the PC and say what slows it down most."""
    total_disk = sum(g["disk"] for g in groups) or 1.0
    for g in groups:
        g["cpu"] = round(min(100.0, g["cpu"]), 1)
        g["n"] = len(g["pids"])
        g["lowered"] = g["key"] in lowered
        g["canClose"] = g["kind"] in ("app", "browser")
        g["canLower"] = g["kind"] in ("app", "browser")
        g["weight"] = max(g["cpu"] / 100 * 1.2, g["ram"] / max(1.0, ram_total) * 2.5, (g["disk"] / total_disk) * 0.6 if g["disk"] > 2**20 else 0)
    groups.sort(key=lambda g: g["weight"], reverse=True)
    top = [g for g in groups if g["kind"] != "kernel"] or groups
    by_cpu = max(top, key=lambda g: g["cpu"], default=None)
    by_ram = max(top, key=lambda g: g["ram"], default=None)
    by_disk = max(top, key=lambda g: g["disk"], default=None)
    if ram_pct >= 85:
        verdict, level, culprit = "ram", "bad", by_ram
    elif cpu >= 80:
        verdict, level, culprit = "cpu", "bad", by_cpu
    elif disk_busy is not None and disk_busy >= 80:
        verdict, level, culprit = "disk", "bad", by_disk
    elif ram_pct >= 75 or cpu >= 50 or (disk_busy or 0) >= 50:
        verdict, level = "busy", "warn"
        culprit = by_ram if ram_pct >= 75 else by_cpu if cpu >= 50 else by_disk
    else:
        verdict, level, culprit = "ok", "good", None
    browsers = [g for g in groups if g["kind"] == "browser"]
    heavy = max(browsers, key=lambda g: g["ram"], default=None)
    browser = None
    if heavy and (heavy["ram"] >= 1.5 * 2**30 or (ram_pct >= 75 and heavy["ram"] >= 0.6 * 2**30)):
        bid = heavy["key"].split(":", 1)[1]
        browser = {"id": bid, "title": heavy["title"], "ram": heavy["ram"], "n": heavy["n"], "url": MEMORY_SAVER.get(bid, "")}
    rows = [{k: v for k, v in g.items() if k not in ("weight",)} for g in groups[:14]]
    return {"cpu": round(cpu), "ram": round(ram_pct), "ramUsed": float(ram_used), "ramTotal": float(ram_total),
            "disk": None if disk_busy is None else round(disk_busy), "verdict": verdict, "level": level,
            "culprit": culprit["title"] or "" if culprit else "", "culpritKind": culprit["kind"] if culprit else "",
            "rows": rows, "browser": browser, "count": sum(g["n"] for g in groups)}


# ---------------- actions (only on a click) ----------------
def close(pids: list[int], force: bool = False) -> int:
    """Close a program the way its window's close button would (it may ask to save); force ends it at once."""
    pids = [int(p) for p in pids if int(p) > 4]
    if not pids or not P.IS_WINDOWS:
        return len(pids)
    args = ["taskkill.exe"] + (["/F"] if force else []) + ["/T"]
    for pid in pids:
        args += ["/PID", str(pid)]
    r = subprocess.run(args, capture_output=True, timeout=30, creationflags=0x08000000)
    P.log(f"now: close {pids[:6]} force={force}: rc={r.returncode}")
    time.sleep(2.5)
    return sum(1 for p in pids if not psutil.pid_exists(p))


def set_priority(pids: list[int], low: bool) -> int:
    """Below normal while low, normal again otherwise. Windows forgets it when the program restarts."""
    if not P.IS_WINDOWS:
        return len(pids)
    cls = psutil.BELOW_NORMAL_PRIORITY_CLASS if low else psutil.NORMAL_PRIORITY_CLASS
    n = 0
    for pid in pids:
        try:
            psutil.Process(int(pid)).nice(cls)
            n += 1
        except psutil.Error:
            pass
    return n


# ---------------- demo (Linux, screenshots) ----------------
_DEMO = [
    ("browser:chrome", "browser", "Google Chrome", "", 27, 9.0, 2.6 * 2**30, 0.4 * 2**20),
    ("sys:defender", "defender", "", "", 3, 14.0, 310 * 2**20, 18 * 2**20),
    ("app:telegram", "app", "Telegram Desktop", "", 1, 1.2, 420 * 2**20, 0),
    ("sys:update", "update", "", "", 2, 6.5, 180 * 2**20, 6 * 2**20),
    ("sys:compression", "compression", "", "", 1, 0.8, 640 * 2**20, 0),
    ("app:discord", "app", "Discord", "", 6, 0.6, 520 * 2**20, 0),
    ("sys:search", "search", "", "", 2, 2.1, 90 * 2**20, 3 * 2**20),
    ("sys:dwm", "dwm", "", "", 1, 3.2, 120 * 2**20, 0),
    ("self", "self", "Sweep Beta", "", 1, 1.0, 140 * 2**20, 0),
    ("sys:services", "services", "", "", 74, 2.4, 900 * 2**20, 0.2 * 2**20),
    ("sys:kernel", "kernel", "", "", 2, 1.1, 30 * 2**20, 1.5 * 2**20),
]


def demo(s: Sampler) -> dict:
    import math
    k = time.monotonic() / 3
    groups = []
    for i, (key, kind, title, exe, n, cpu, ram, disk) in enumerate(_DEMO):
        wob = 1 + 0.25 * math.sin(k + i)
        groups.append({"key": key, "kind": kind, "title": title, "exe": exe, "pids": list(range(1000 + i * 10, 1000 + i * 10 + n)),
                       "cpu": cpu * wob, "ram": ram, "disk": disk * wob})
    total = 8 * 2**30
    used = sum(g["ram"] for g in groups) + 1.1 * 2**30
    return finish(groups, 38 + 8 * math.sin(k), used / total * 100, used, total, 62 + 20 * math.sin(k / 2), s.lowered)
