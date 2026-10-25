"""Thorough uninstaller.

1. Installed programs are read from the three Uninstall registry branches (64-bit, 32-bit, current user).
2. The program's own uninstaller runs first (interactive, or quiet when it is known to support it),
   Sweep waits for it and for the helper processes it spawns.
3. Leftovers are searched in program folders, AppData, ProgramData, the registry, Start menu and desktop
   shortcuts, scheduled tasks, services and Run entries. Exact matches are ticked, look-alikes are not.
4. Removal is reversible: files go to quarantine, registry keys, tasks and services are exported first.
   Files that are locked are removed at the next restart.
Forced mode skips step 2 for programs whose uninstaller is missing, broken or refuses to work.
"""
from __future__ import annotations

import ntpath
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from . import cleaner, platform as P

if P.IS_WINDOWS:
    import winreg

UNINSTALL = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
SOURCES = [("HKLM", UNINSTALL, 64), ("HKLM", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall", 64), ("HKCU", UNINSTALL, 64)]

# folder or registry names that are shared by many products and must never be removed as a whole
SHARED = {"microsoft", "windows", "common files", "microsoft shared", "windowsapps", "installer", "package cache", "packages", "programs",
          "temp", "intel", "nvidia", "nvidia corporation", "amd", "realtek", "google", "mozilla", "adobe", "apple", "apple computer, inc.",
          "classes", "policies", "wow6432node", "clients", "registeredapplications", "software", "system", "update", "updates", "app", "apps",
          "tools", "utilities", "games", "users", "public", "default", "data", "cache", "logs", "config", "plugins", "crashdumps",
          "microsoft corporation", "windows defender", "windows nt", "internet explorer", "windowspowershell", "dotnet", "reference assemblies",
          "msbuild", "uninstall information", "modifiablewindowsapps", "steamapps", "nuget", "npm", "pip", "python", "java", "desktop",
          "documents", "downloads", "pictures", "music", "videos", "start menu", "startup", "local", "roaming", "locallow", "appdata"}


# ---------------- demo data (Linux development) ----------------
_DEMO = [
    {"name": "Discord", "publisher": "Discord Inc.", "version": "1.0.9168", "size": 412 * 2**20, "date": "2026-09-14", "location": r"C:\Users\Alex\AppData\Local\Discord", "quiet": False, "msi": False},
    {"name": "Steam", "publisher": "Valve Corporation", "version": "2.10.91.91", "size": 812 * 2**20, "date": "2025-12-02", "location": r"C:\Program Files (x86)\Steam", "quiet": False, "msi": False},
    {"name": "Yandex", "publisher": "ООО «ЯНДЕКС»", "version": "25.8.1.865", "size": 690 * 2**20, "date": "2026-10-20", "location": r"C:\Users\Alex\AppData\Local\Yandex\YandexBrowser\Application", "quiet": False, "msi": False},
    {"name": "7-Zip 24.08 (x64)", "publisher": "Igor Pavlov", "version": "24.08", "size": 5 * 2**20, "date": "2025-03-11", "location": r"C:\Program Files\7-Zip", "quiet": True, "msi": False},
    {"name": "Avast Free Antivirus", "publisher": "Avast Software", "version": "25.9.10453", "size": 1.4 * 2**30, "date": "2026-02-27", "location": r"C:\Program Files\Avast Software\Avast", "quiet": False, "msi": False},
    {"name": "Mail.ru Агент", "publisher": "VK", "version": "10.0.30123", "size": 186 * 2**20, "date": "2024-11-05", "location": r"C:\Users\Alex\AppData\Roaming\Mail.Ru\Agent", "quiet": False, "msi": False},
    {"name": "NVIDIA App", "publisher": "NVIDIA Corporation", "version": "11.0.5.245", "size": 655 * 2**20, "date": "2026-08-30", "location": r"C:\Program Files\NVIDIA Corporation\NVIDIA app", "quiet": False, "msi": False},
    {"name": "Telegram Desktop", "publisher": "Telegram FZ-LLC", "version": "6.1.3", "size": 128 * 2**20, "date": "2026-10-01", "location": r"C:\Users\Alex\AppData\Roaming\Telegram Desktop", "quiet": True, "msi": False},
    {"name": "WinRAR 7.11 (64-bit)", "publisher": "win.rar GmbH", "version": "7.11.0", "size": 9 * 2**20, "date": "2025-06-17", "location": r"C:\Program Files\WinRAR", "quiet": False, "msi": False},
    {"name": "Microsoft Visual C++ 2015-2022 Redistributable (x64)", "publisher": "Microsoft Corporation", "version": "14.44.35211", "size": 20 * 2**20, "date": "2025-07-08", "location": "", "quiet": True, "msi": True},
    {"name": "Zoom Workplace", "publisher": "Zoom Communications, Inc.", "version": "6.5.12", "size": 340 * 2**20, "date": "2025-10-19", "location": r"C:\Users\Alex\AppData\Roaming\Zoom\bin", "quiet": False, "msi": False},
    {"name": "Kaspersky Total Security", "publisher": "АО «Лаборатория Касперского»", "version": "21.19.7.527", "size": 980 * 2**20, "date": "2026-01-15", "location": r"C:\Program Files (x86)\Kaspersky Lab\Kaspersky Total Security 21.19", "quiet": False, "msi": False},
]
for _i, _d in enumerate(_DEMO):
    _d.update(id=f"demo:{_i}", icon="", uninstall="uninst.exe", exists=True, system=False)


# ---------------- registry helpers ----------------
def _hive(root: str):
    return winreg.HKEY_LOCAL_MACHINE if root == "HKLM" else winreg.HKEY_CURRENT_USER


def _val(k, name):
    try:
        return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def _key_exists(root: str, path: str) -> bool:
    try:
        winreg.CloseKey(winreg.OpenKey(_hive(root), path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY))
        return True
    except OSError:
        return False


def _icon_path(raw: str | None) -> str:
    if not raw:
        return ""
    p = os.path.expandvars(str(raw)).strip().strip('"')
    p = re.sub(r",\s*-?\d+$", "", p).strip().strip('"')
    return p if p and os.path.exists(p) else ""


def list_programs() -> list[dict]:
    """Programs the user can remove, newest first; Windows components, updates and duplicates are skipped."""
    if not P.IS_WINDOWS:
        return [dict(d) for d in _DEMO]
    out, seen = [], set()
    for root, path, _ in SOURCES:
        try:
            base = winreg.OpenKey(_hive(root), path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        except OSError:
            continue
        with base:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(base, i)
                except OSError:
                    break
                i += 1
                try:
                    with winreg.OpenKey(base, sub) as k:
                        name = _val(k, "DisplayName")
                        un = _val(k, "UninstallString")
                        if not name or _val(k, "SystemComponent") == 1 or _val(k, "ParentKeyName") or str(_val(k, "ReleaseType") or "").lower() in ("update", "hotfix", "security update"):
                            continue
                        if not un and not _val(k, "QuietUninstallString"):
                            continue
                        name = str(name).strip()
                        ver = str(_val(k, "DisplayVersion") or "")
                        if (name.lower(), ver) in seen:
                            continue
                        seen.add((name.lower(), ver))
                        size_kb = _val(k, "EstimatedSize")
                        date = str(_val(k, "InstallDate") or "")
                        loc = os.path.expandvars(str(_val(k, "InstallLocation") or "")).strip().strip('"').rstrip("\\")
                        msi = bool(_val(k, "WindowsInstaller")) or bool(re.search(r"msiexec", str(un or ""), re.I))
                        quiet = _val(k, "QuietUninstallString")
                        out.append({
                            "id": f"{root}|{path}|{sub}", "name": name, "publisher": str(_val(k, "Publisher") or "").strip(), "version": ver,
                            "size": int(size_kb) * 1024 if isinstance(size_kb, int) else 0,
                            "date": f"{date[:4]}-{date[4:6]}-{date[6:8]}" if re.fullmatch(r"\d{8}", date) else "",
                            "location": loc if loc and os.path.isdir(loc) else "", "icon": _icon_path(_val(k, "DisplayIcon")),
                            "uninstall": str(un or ""), "quietCmd": str(quiet or ""), "quiet": bool(quiet) or msi or bool(re.search(r"unins\d{3}\.exe", str(un or ""), re.I)),
                            "msi": msi, "key": sub, "noRemove": _val(k, "NoRemove") == 1, "exists": True,
                        })
                except OSError:
                    continue
    out.sort(key=lambda p: p["name"].lower())
    return out


def still_installed(prog: dict) -> bool:
    if not P.IS_WINDOWS:
        return False
    root, path, sub = prog["id"].split("|", 2)
    return _key_exists(root, f"{path}\\{sub}")


# ---------------- step 1: close the program ----------------
def running_processes(prog: dict) -> list[dict]:
    loc = (prog.get("location") or "").lower()
    if not P.IS_WINDOWS or not loc:
        return []
    import psutil
    out = []
    for p in psutil.process_iter(["pid", "name", "exe"]):
        exe = (p.info.get("exe") or "").lower()
        if exe.startswith(loc + "\\"):
            out.append({"pid": p.info["pid"], "name": p.info["name"]})
    return out


def close_processes(prog: dict) -> int:
    if not P.IS_WINDOWS:
        return 0
    import psutil
    n = 0
    for r in running_processes(prog):
        try:
            pr = psutil.Process(r["pid"])
            pr.terminate()
            try:
                pr.wait(4)
            except psutil.TimeoutExpired:
                pr.kill()
            n += 1
        except Exception:  # noqa: BLE001
            pass
    return n


# ---------------- step 2: the program's own uninstaller ----------------
def _uninstall_command(prog: dict, quiet: bool) -> str:
    if prog.get("msi"):
        m = re.search(r"\{[0-9A-Fa-f\-]{36}\}", prog.get("uninstall", "")) or re.search(r"\{[0-9A-Fa-f\-]{36}\}", prog.get("key", ""))
        if m:
            return f"msiexec.exe /x {m.group(0)}" + (" /qn /norestart" if quiet else "")
    if quiet and prog.get("quietCmd"):
        return os.path.expandvars(prog["quietCmd"])
    cmd = os.path.expandvars(prog.get("uninstall", ""))
    if quiet and re.search(r"unins\d{3}\.exe", cmd, re.I):
        cmd += " /VERYSILENT /SUPPRESSMSGBOXES /NORESTART"
    return cmd


def run_uninstaller(prog: dict, quiet: bool, cancel=lambda: False, timeout: int = 900) -> dict:
    """Start the uninstaller and wait for it and for the helper processes it starts (NSIS, Inno copy themselves to Temp)."""
    if not P.IS_WINDOWS:
        time.sleep(1.5)
        return {"ok": True, "code": 0, "still": False}
    cmd = _uninstall_command(prog, quiet)
    if not cmd:
        return {"ok": False, "code": -1, "still": True, "error": "no uninstaller"}
    import psutil
    started = time.time()
    try:
        proc = subprocess.Popen(cmd)
    except OSError as e:
        P.log(f"uninstall {prog['name']}: {cmd}: {e}")
        return {"ok": False, "code": -1, "still": True, "error": str(e)}
    temp = os.environ.get("TEMP", "").lower()
    loc = (prog.get("location") or "").lower()
    helper = re.compile(r"^(au_|un_?a?|_iu|unins|uninst|uninstall|setup|msiexec)", re.I)
    code = None
    while time.time() - started < timeout and not cancel():
        if code is None:
            code = proc.poll()
        busy = code is None
        if not busy:
            for p in psutil.process_iter(["name", "exe", "create_time"]):
                try:
                    if (p.info.get("create_time") or 0) < started - 1:
                        continue
                    exe = (p.info.get("exe") or "").lower()
                    if helper.match(p.info.get("name") or "") or (temp and exe.startswith(temp)) or (loc and exe.startswith(loc)):
                        busy = True
                        break
                except Exception:  # noqa: BLE001
                    continue
        if not busy:
            break
        time.sleep(1.0)
    still = still_installed(prog)
    P.log(f"uninstall {prog['name']}: '{cmd}' exit {code}, entry still present: {still}")
    return {"ok": not still, "code": code, "still": still}


# ---------------- step 3: leftovers ----------------
def _norm(s: str) -> str:
    return re.sub(r"[^a-zа-я0-9]+", " ", s.lower()).strip()


def _names(prog: dict) -> set[str]:
    """Names a leftover folder or key may carry: the product name without version and bitness, the install folder name."""
    raw = prog.get("name", "")
    n = re.sub(r"\(.*?\)", " ", raw)
    n = re.sub(r"\b(x64|x86|64-bit|32-bit|64 bit|32 bit|win64|win32)\b", " ", n, flags=re.I)
    n = re.sub(r"\bv?\d+(\.\d+)+\b", " ", n)
    n = re.sub(r"\s\d+$", "", n.strip())
    out = {_norm(n)} if _norm(n) else {_norm(raw)}
    if prog.get("location"):
        out.add(_norm(ntpath.basename(prog["location"].rstrip("\\"))))
    for p in _pubs(prog):                       # "Google Chrome" also lives in Google\Chrome
        for x in list(out):
            if x.startswith(p + " ") and len(x) - len(p) > 3:
                out.add(x[len(p) + 1:])
    return {x for x in out if len(x) >= 3 and x not in SHARED and re.search(r"[a-zа-я]{2}", x)}


def _pubs(prog: dict) -> set[str]:
    """Publisher folder names: full name and first word ("Google LLC" -> google llc, google)."""
    pub = _norm(prog.get("publisher", ""))
    out = {pub, pub.split(" ")[0] if pub else ""}
    return {x for x in out if len(x) >= 3}


def _safe_dir(path: str) -> bool:
    """Never treat a drive root, a system folder, a user folder or one of the search roots as a program's own folder."""
    p = ntpath.normpath(path).rstrip("\\").lower()
    parts = [x for x in p.split("\\") if x]
    if len(parts) < 2:
        return False
    env = os.environ
    forbidden = {ntpath.normpath(r).rstrip("\\").lower() for r in _roots()}
    forbidden |= {ntpath.normpath(env.get(v, "")).rstrip("\\").lower() for v in ("WINDIR", "SystemRoot", "USERPROFILE", "PUBLIC", "ProgramFiles", "ProgramFiles(x86)", "ProgramData") if env.get(v)}
    forbidden |= {parts[0] + "\\users", parts[0] + "\\program files", parts[0] + "\\program files (x86)", parts[0] + "\\programdata", parts[0] + "\\windows"}
    if len(parts) == 3 and parts[1] == "users":       # a user profile (C:\\Users\\Name)
        return False
    return p not in forbidden and _norm(parts[-1]) not in SHARED


def _dir_size(p: str) -> int:
    total = 0
    for dp, _, fs in os.walk(p):
        for f in fs:
            try:
                total += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return total


def _roots() -> list[str]:
    e = os.environ
    la, ra, up = e.get("LOCALAPPDATA", ""), e.get("APPDATA", ""), e.get("USERPROFILE", "")
    return [r for r in (e.get("ProgramFiles", ""), e.get("ProgramFiles(x86)", ""), e.get("ProgramW6432", ""), e.get("ProgramData", ""),
                         la, os.path.join(la, "Programs"), ra, os.path.join(up, "AppData", "LocalLow")) if r and os.path.isdir(r)]


def _demo_leftovers(prog: dict) -> list[dict]:
    n = prog["name"].split()[0]
    return [
        {"kind": "folder", "path": prog.get("location") or rf"C:\Program Files\{n}", "size": 38 * 2**20, "exact": True},
        {"kind": "folder", "path": rf"C:\Users\Alex\AppData\Roaming\{n}", "size": 212 * 2**20, "exact": True},
        {"kind": "folder", "path": rf"C:\ProgramData\{n}", "size": 6 * 2**20, "exact": True},
        {"kind": "folder", "path": rf"C:\Users\Alex\AppData\Local\{n}Updater", "size": 2 * 2**20, "exact": False},
        {"kind": "reg", "path": rf"HKCU\Software\{prog.get('publisher') or n}\{n}", "size": 0, "exact": True},
        {"kind": "reg", "path": rf"HKLM\SOFTWARE\WOW6432Node\{n}", "size": 0, "exact": True},
        {"kind": "shortcut", "path": rf"C:\Users\Alex\Desktop\{n}.lnk", "size": 2048, "exact": True},
        {"kind": "task", "path": rf"\{n}UpdateTaskMachineUA", "size": 0, "exact": True},
        {"kind": "service", "path": f"{n}Update", "size": 0, "exact": True},
        {"kind": "run", "path": rf"HKCU\Software\Microsoft\Windows\CurrentVersion\Run\{n}", "size": 0, "exact": True},
    ]


def find_leftovers(prog: dict) -> list[dict]:
    """Everything the program left behind. 'exact' items are ticked by default."""
    if not P.IS_WINDOWS:
        return _with_ids(_demo_leftovers(prog))
    names = _names(prog)
    pubs = _pubs(prog)
    loc = (prog.get("location") or "").rstrip("\\")
    if loc and not _safe_dir(loc):
        P.log(f"uninstall {prog['name']}: install location {loc} is not a program folder, ignored")
        loc = ""
    found: list[dict] = []
    seen: set[str] = set()

    def add(kind, path, exact, size=0):
        key = f"{kind}:{path.lower()}"
        if key not in seen:
            seen.add(key)
            found.append({"kind": kind, "path": path, "exact": exact, "size": size})

    # install folder and same-named folders in Program Files, ProgramData, AppData
    if loc and os.path.isdir(loc):
        add("folder", loc, True, _dir_size(loc))
    for root in _roots():
        try:
            entries = list(os.scandir(root))
        except OSError:
            continue
        for d in entries:
            if not d.is_dir(follow_symlinks=False):
                continue
            nd = _norm(d.name)
            if nd in names and _safe_dir(d.path):
                add("folder", d.path, True, _dir_size(d.path))
            elif nd in pubs:      # Publisher\Product (the publisher folder itself stays)
                try:
                    for s in os.scandir(d.path):
                        if s.is_dir(follow_symlinks=False) and _norm(s.name) in names and _safe_dir(s.path):
                            add("folder", s.path, True, _dir_size(s.path))
                except OSError:
                    pass
            elif any(len(n) >= 5 and nd.startswith(n) for n in names) and _safe_dir(d.path):
                add("folder", d.path, False, _dir_size(d.path))

    # registry: Software\Product and Software\Publisher\Product in both hives and both views
    for root, base in (("HKCU", "Software"), ("HKLM", "SOFTWARE"), ("HKLM", r"SOFTWARE\WOW6432Node"), ("HKCU", r"Software\WOW6432Node")):
        try:
            k = winreg.OpenKey(_hive(root), base, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        except OSError:
            continue
        with k:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(k, i)
                except OSError:
                    break
                i += 1
                ns = _norm(sub)
                if ns in names:
                    add("reg", f"{root}\\{base}\\{sub}", True)
                elif ns in pubs:
                    try:
                        with winreg.OpenKey(k, sub) as pk:
                            j = 0
                            while True:
                                try:
                                    s2 = winreg.EnumKey(pk, j)
                                except OSError:
                                    break
                                j += 1
                                if _norm(s2) in names:
                                    add("reg", f"{root}\\{base}\\{sub}\\{s2}", True)
                    except OSError:
                        pass
    if still_installed(prog):                                   # orphaned entry in Programs and Features
        r, path, sub = prog["id"].split("|", 2)
        add("reg", f"{r}\\{path}\\{sub}", True)

    # Run entries, shortcuts, scheduled tasks and services pointing into the install folder or named like the program
    pat = [n for n in names if len(n) >= 4]
    for root in ("HKCU", "HKLM"):
        for run in (r"Software\Microsoft\Windows\CurrentVersion\Run", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"):
            try:
                with winreg.OpenKey(_hive(root), run, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
                    i = 0
                    while True:
                        try:
                            vname, vdata, _ = winreg.EnumValue(k, i)
                        except OSError:
                            break
                        i += 1
                        d = str(vdata).lower()
                        if (loc and loc.lower() in d) or _norm(vname) in names:
                            add("run", f"{root}\\{run}\\{vname}", True)
            except OSError:
                pass
    locq = loc.replace("'", "''")
    patq = "|".join(re.escape(n) for n in pat).replace("'", "''") or "^$"
    data = P.ps_json(rf'''
$loc='{locq}'; $pat='{patq}'; $out=@()
$sh=New-Object -ComObject WScript.Shell
$dirs=@([Environment]::GetFolderPath('Programs'),[Environment]::GetFolderPath('CommonPrograms'),[Environment]::GetFolderPath('Desktop'),[Environment]::GetFolderPath('CommonDesktopDirectory'))
foreach($d in $dirs){{ if(-not $d -or -not (Test-Path $d)){{continue}}
  foreach($f in Get-ChildItem $d -Recurse -Filter *.lnk -EA SilentlyContinue){{ $t=''; try{{$t=$sh.CreateShortcut($f.FullName).TargetPath}}catch{{}}
    $n=($f.BaseName.ToLower() -replace '[^a-zа-я0-9]+',' ').Trim()
    if(($loc -and $t -and $t.ToLower().StartsWith($loc.ToLower())) -or ($n -match "^($pat)$")){{ $out+=@{{kind='shortcut';path=$f.FullName;exact=$true}} }} }}
  foreach($f in Get-ChildItem $d -Directory -EA SilentlyContinue){{ $n=($f.Name.ToLower() -replace '[^a-zа-я0-9]+',' ').Trim(); if($n -match "^($pat)$"){{ $out+=@{{kind='folder';path=$f.FullName;exact=$true}} }} }} }}
foreach($t in Get-ScheduledTask -EA SilentlyContinue){{ $a=($t.Actions | % {{ $_.Execute }}) -join ' '
  $n=($t.TaskName.ToLower() -replace '[^a-zа-я0-9]+',' ').Trim()
  if(($loc -and $a -and $a.ToLower().Contains($loc.ToLower())) -or ($n -match "^($pat)")){{ $out+=@{{kind='task';path=($t.TaskPath + $t.TaskName);exact=[bool]($loc -and $a.ToLower().Contains($loc.ToLower()))}} }} }}
if($loc){{ foreach($s in Get-CimInstance Win32_Service -EA SilentlyContinue){{ if($s.PathName -and $s.PathName.ToLower().Contains($loc.ToLower())){{ $out+=@{{kind='service';path=$s.Name;exact=$true}} }} }} }}
,$out''', 120)
    for it in (data if isinstance(data, list) else [data] if isinstance(data, dict) else []):
        if it and it.get("path"):
            size = os.path.getsize(it["path"]) if it["kind"] == "shortcut" and os.path.exists(it["path"]) else 0
            add(it["kind"], it["path"], bool(it.get("exact")), size)
    return _with_ids(found)


def _with_ids(items: list[dict]) -> list[dict]:
    order = {"folder": 0, "file": 1, "shortcut": 2, "reg": 3, "run": 4, "task": 5, "service": 6}
    items.sort(key=lambda x: (order.get(x["kind"], 9), not x["exact"], x["path"].lower()))
    for i, it in enumerate(items):
        it["id"] = i
    return items


# ---------------- step 4: removal ----------------
MOVEFILE_DELAY_UNTIL_REBOOT = 4


def _delete_on_reboot(path: str) -> None:
    import ctypes
    for dp, dirs, files in os.walk(path, topdown=False):
        for f in files:
            ctypes.windll.kernel32.MoveFileExW(os.path.join(dp, f), None, MOVEFILE_DELAY_UNTIL_REBOOT)
        for d in dirs:
            ctypes.windll.kernel32.MoveFileExW(os.path.join(dp, d), None, MOVEFILE_DELAY_UNTIL_REBOOT)
    ctypes.windll.kernel32.MoveFileExW(path, None, MOVEFILE_DELAY_UNTIL_REBOOT)


def _reg_export(path: str, session: str, n: int) -> None:
    f = P.REG_BACKUP / f"{session}_uninstall_{n:03d}.reg"
    subprocess.run(["reg.exe", "export", path, str(f), "/y", "/reg:64"], capture_output=True, timeout=60)


def remove_leftovers(items: list[dict], session: str, label: str) -> dict:
    """Removes ticked leftovers; returns {removed, reboot, failed, freed}."""
    res = {"removed": 0, "reboot": 0, "failed": [], "freed": 0}
    if not P.IS_WINDOWS:
        time.sleep(1.2)
        res["removed"] = len(items)
        res["freed"] = sum(i.get("size", 0) for i in items)
        return res
    qdir = P.QUARANTINE / session / ("uninstall_" + re.sub(r"[^\w]+", "_", label)[:40])
    manifest = P.QUARANTINE / session / "manifest.txt"
    for n, it in enumerate(items, 1):
        kind, path = it["kind"], it["path"]
        try:
            if kind in ("folder", "file", "shortcut"):
                if not os.path.exists(path):
                    continue
                qdir.mkdir(parents=True, exist_ok=True)
                target = qdir / f"{n:03d}_{os.path.basename(path.rstrip(chr(92)))}"
                try:
                    shutil.move(path, str(target))
                    with manifest.open("a", encoding="utf-8") as m:
                        m.write(f"{target}|{path}\n")
                    res["freed"] += it.get("size", 0)
                except OSError:
                    _delete_on_reboot(path)       # locked by a running service or driver: gone after restart
                    res["reboot"] += 1
                    continue
                parent = os.path.dirname(path)      # empty Publisher folder left behind
                try:
                    if parent and _norm(os.path.basename(parent)) not in SHARED and not os.listdir(parent):
                        os.rmdir(parent)
                except OSError:
                    pass
            elif kind == "reg":
                _reg_export(path, session, n)
                r = subprocess.run(["reg.exe", "delete", path, "/f", "/reg:64"], capture_output=True, timeout=60)
                if r.returncode != 0:
                    raise OSError((r.stderr or r.stdout or b"").decode("cp866", "replace").strip())
            elif kind == "run":
                key, _, value = path.rpartition("\\")
                _reg_export(key, session, n)
                r = subprocess.run(["reg.exe", "delete", key, "/v", value, "/f", "/reg:64"], capture_output=True, timeout=60)
                if r.returncode != 0:
                    raise OSError("reg delete failed")
            elif kind == "task":
                bdir = str(P.REG_BACKUP).replace("'", "''")
                tp, _, tn = path.rpartition("\\")
                P.powershell(f"$t=Get-ScheduledTask -TaskName '{tn}' -TaskPath '{tp}\\' -EA Stop; "
                             f"Export-ScheduledTask -TaskName '{tn}' -TaskPath '{tp}\\' | Set-Content -Path (Join-Path '{bdir}' '{session}_task_{n:03d}.xml') -Encoding Unicode; "
                             f"Unregister-ScheduledTask -TaskName '{tn}' -TaskPath '{tp}\\' -Confirm:$false", 60)
            elif kind == "service":
                _reg_export(f"HKLM\\SYSTEM\\CurrentControlSet\\Services\\{path}", session, n)
                subprocess.run(["sc.exe", "stop", path], capture_output=True, timeout=60)
                r = subprocess.run(["sc.exe", "delete", path], capture_output=True, timeout=60)
                if r.returncode != 0:
                    raise OSError("sc delete failed")
            res["removed"] += 1
        except Exception as e:  # noqa: BLE001
            P.log(f"uninstall leftover {kind} {path}: {e}")
            res["failed"].append(path)
    return res


def uninstall_icon_key(prog: dict) -> str:
    """Path the icon provider should use: DisplayIcon, else the main exe in the install folder."""
    if prog.get("icon"):
        return prog["icon"]
    loc = prog.get("location")
    if loc and os.path.isdir(loc):
        exes = [f for f in os.listdir(loc) if f.lower().endswith(".exe") and not re.match(r"(unins|uninst|update)", f, re.I)]
        if exes:
            return os.path.join(loc, sorted(exes, key=len)[0])
    return ""


__all__ = ["list_programs", "running_processes", "close_processes", "run_uninstaller", "find_leftovers", "remove_leftovers", "still_installed", "cleaner"]
