"""Windows self-test, run by GitHub Actions on a real Windows machine (see .github/workflows/selftest.yml).
Checks privacy switches, startup switches and browser history cleaning, then puts everything back."""
from __future__ import annotations

import os
import sqlite3
import sys
import winreg
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sweep import cleaner, tweaks  # noqa: E402
from sweep import platform as P

fails: list[str] = []


def check(cond: bool, what: str):
    print(("OK   " if cond else "FAIL ") + what, flush=True)
    if not cond:
        fails.append(what)
        if os.environ.get("GITHUB_ACTIONS"):      # shows up on the run page without opening the log
            print(f"::error title=Self test::{what[:900]}", flush=True)


def note(what: str):
    print("     " + what, flush=True)
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::notice title=Self test::{what[:900]}", flush=True)


print(f"admin: {P.is_admin()}  python: {sys.version.split()[0]}")
check(P.is_admin(), "runner is elevated")

# ---------- privacy ----------
before = {p.id: tweaks.privacy_state(p) for p in tweaks.PRIVACY}
print("privacy before:", sum(before.values()), "of", len(before))
for p in tweaks.PRIVACY:
    bad = tweaks.set_privacy(p, True)
    check(not bad and tweaks.privacy_state(p), f"privacy on: {p.id} {bad or ''}")
for p in tweaks.PRIVACY:
    if not before[p.id]:
        bad = tweaks.set_privacy(p, False)
        check(not bad, f"privacy revert: {p.id} {bad or ''}")
        print("     state after revert:", p.id, tweaks.privacy_state(p))

# a value Windows Settings writes is recognised even without Sweep's own keys
tweaks.reg_set("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "ShowCopilotButton", 0)
tweaks.reg_del("HKCU", r"Software\Policies\Microsoft\Windows\WindowsCopilot", "TurnOffWindowsCopilot")
check(tweaks.privacy_state(next(p for p in tweaks.PRIVACY if p.id == "copilot")), "copilot hidden in Settings counts as off")

# ---------- startup ----------
RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
for hive, root in ((winreg.HKEY_CURRENT_USER, "User"), (winreg.HKEY_LOCAL_MACHINE, "System")):
    with winreg.CreateKeyEx(hive, RUN, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
        winreg.SetValueEx(k, "SweepSelfTest", 0, winreg.REG_SZ, r"C:\Windows\notepad.exe")
    e = next((x for x in tweaks.startup_entries() if x["name"] == "SweepSelfTest" and x["source"] == root), None)
    check(e is not None, f"startup entry listed ({root})")
    if e:
        tweaks.set_startup(e, False)
        e2 = next(x for x in tweaks.startup_entries() if x["name"] == "SweepSelfTest" and x["source"] == root)
        check(e2["enabled"] is False, f"startup disabled ({root})")
        tweaks.set_startup(e2, True)
        e3 = next(x for x in tweaks.startup_entries() if x["name"] == "SweepSelfTest" and x["source"] == root)
        check(e3["enabled"] is True, f"startup enabled again ({root})")
        root_s, path = tweaks._split_ps_path(e["approved"])
        tweaks.reg_del(root_s, path, "SweepSelfTest")
    with winreg.OpenKey(hive, RUN, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
        winreg.DeleteValue(k, "SweepSelfTest")

# ---------- browser history ----------
la, ra = Path(os.environ["LOCALAPPDATA"]), Path(os.environ["APPDATA"])
chrome = la / "Google" / "Chrome" / "User Data" / "Default"
opera = la / "Opera Software" / "Opera Stable"
for d in (chrome, opera):
    d.mkdir(parents=True, exist_ok=True)
    for f in ("History", "Visited Links", "Top Sites", "Shortcuts"):
        (d / f).write_bytes(os.urandom(4096))
    for f in ("Login Data", "Web Data", "Bookmarks", "Preferences"):
        (d / f).write_bytes(b"keep")
    (d / "Sessions").mkdir(exist_ok=True)
    (d / "Sessions" / "Session_1").write_bytes(b"keep")

fx = ra / "Mozilla" / "Firefox" / "Profiles" / "test.default"
fx.mkdir(parents=True, exist_ok=True)
for f in fx.glob("places.sqlite*"):
    f.unlink()
c = sqlite3.connect(fx / "places.sqlite")
c.executescript("""
PRAGMA journal_mode=WAL;
CREATE TABLE moz_origins (id INTEGER PRIMARY KEY, prefix TEXT, host TEXT, frecency INTEGER);
CREATE TABLE moz_places (id INTEGER PRIMARY KEY, url TEXT, title TEXT, visit_count INTEGER DEFAULT 0, last_visit_date INTEGER, frecency INTEGER, origin_id INTEGER REFERENCES moz_origins(id));
CREATE TABLE moz_historyvisits (id INTEGER PRIMARY KEY, place_id INTEGER, visit_date INTEGER);
CREATE TABLE moz_inputhistory (place_id INTEGER, input TEXT, use_count INTEGER, PRIMARY KEY (place_id, input));
CREATE TABLE moz_bookmarks (id INTEGER PRIMARY KEY, type INTEGER, fk INTEGER DEFAULT NULL, parent INTEGER, title TEXT);
CREATE TABLE moz_keywords (id INTEGER PRIMARY KEY, keyword TEXT, place_id INTEGER);
CREATE TABLE moz_annos (id INTEGER PRIMARY KEY, place_id INTEGER, content TEXT);
""")
c.execute("INSERT INTO moz_origins VALUES (1,'https://','a.com',1),(2,'https://','bm.com',1)")
for i in range(1, 501):
    c.execute("INSERT INTO moz_places VALUES (?,?,?,?,?,?,1)", (i, f"https://a.com/{i}", "t", 2, 1, 10))
    c.execute("INSERT INTO moz_historyvisits (place_id, visit_date) VALUES (?,1)", (i,))
c.execute("INSERT INTO moz_places VALUES (900,'https://bm.com/','bm',3,1,10,2)")
c.execute("INSERT INTO moz_bookmarks (type,fk,parent,title) VALUES (1,900,2,'bm')")
c.commit()
c.close()

cat = next(x for x in cleaner.CATEGORIES if x.id == "history")
size = cleaner.scan(cat)
check(size > 8192, f"history scan found {size} bytes")
session = cleaner.new_session()
freed = cleaner.quarantine(cat, session)
check(freed > 0, f"history freed {freed} bytes")
for d in (chrome, opera):
    check(not (d / "History").exists() and not (d / "Visited Links").exists(), f"history removed in {d.parent.name if d.name == 'Default' else d.name}")
    check(all((d / f).exists() for f in ("Login Data", "Web Data", "Bookmarks", "Preferences")), f"passwords, autofill, bookmarks kept in {d.name}")
    check((d / "Sessions" / "Session_1").exists(), f"open tabs kept in {d.name}")
c = sqlite3.connect(fx / "places.sqlite")
check(c.execute("SELECT COUNT(*) FROM moz_historyvisits").fetchone()[0] == 0, "firefox visits removed")
check(c.execute("SELECT COUNT(*) FROM moz_bookmarks").fetchone()[0] == 1 and c.execute("SELECT COUNT(*) FROM moz_places").fetchone()[0] == 1, "firefox bookmark kept")
c.close()
n = cleaner.restore(str(P.QUARANTINE / session))
check((chrome / "History").exists(), f"history restored from quarantine ({n} items)")
c = sqlite3.connect(fx / "places.sqlite")
check(c.execute("SELECT COUNT(*) FROM moz_historyvisits").fetchone()[0] == 500, "firefox history restored")
c.close()

# ---------- boot x-ray ----------
from sweep import boot as bootx  # noqa: E402
from sweep import extras, guard

ev = bootx.read_events()
check(isinstance(ev, list), f"boot diagnostics log readable ({len(ev)} events)")
r = bootx.analyse(ev)
print("     boots:", len(r["boots"]), "last:", r["last"], "culprits:", [c["name"] for c in r["culprits"]][:5])

# ---------- guard ----------
gs: dict = {}
guard.init_baseline(gs, {p.id: tweaks.privacy_state(p) for p in tweaks.PRIVACY})
adid = next(p for p in tweaks.PRIVACY if p.id == "adid")
tweaks.set_privacy(adid, True)
guard.remember_privacy(gs, "adid", True)
tweaks.set_privacy(adid, False)            # a "Windows update" switches it back on
found = guard.check(gs)
check("adid" in found["privacy"], "guard notices a setting Windows switched back on")
check(not guard.fix(found) and tweaks.privacy_state(adid), "guard puts it back")
check(bool(found["build"]), f"windows build read: {found['build']}")
guard.set_task(True, sys.executable)
check(guard.task_exists(), "guard scheduled task registered")
guard.set_task(False, sys.executable)
check(not guard.task_exists(), "guard scheduled task removed")

# ---------- restore point (skipped by Windows when System Protection is off) ----------
try:
    print("     restore point created:", extras.create_restore_point("Sweep self-test"))
except Exception as e:  # noqa: BLE001
    check(False, f"restore point raised {e}")

# ---------- every module on real Windows (read only) ----------
import subprocess  # noqa: E402

from sweep import uninstall as U  # noqa: E402

for c in cleaner.CATEGORIES:
    check(cleaner.scan(c) >= 0, f"junk scan {c.id}: {c.size} bytes")
for c in extras.REG_CATEGORIES:
    print(f"     registry {c.id}: {extras.reg_scan(c)} found")
states = {s.name: tweaks.service_state(s.name) for s in tweaks.SERVICES}
check(any(v is not None for v in states.values()), f"service states read: {sum(v is not None for v in states.values())}")
info = extras.system_info()
check(bool(info.get("cpu")) and bool(info.get("os")), f"system info: {info.get('os')} / {info.get('cpu')}")
print("     profile:", extras.pc_profile(info))
vols = extras.volumes()
check(len(vols) > 0, f"volumes: {[v['letter'] for v in vols]}")
dj = extras.drive_junk(vols[0]["letter"])
check(isinstance(dj, dict), f"drive junk {vols[0]['letter']}: {sum(c['size'] for c in dj.values())} bytes")
print("     built-in apps found:", len(extras.installed_bloat()))
print("     fx:", tweaks.visual_fx_mode(), "power:", tweaks.power_plan(), "schedule:", tweaks.schedule_state())
progs = U.list_programs()
check(len(progs) > 3, f"installed programs listed: {len(progs)}")

# ---------- forced uninstall of a program that leaves things everywhere ----------
APPD = Path("C:/SweepTestApp")
APPD.mkdir(exist_ok=True)
(APPD / "app.exe").write_bytes(b"MZ fake")
(APPD / "uninstall.cmd").write_text("@exit /b 0\r\n")          # a "broken" uninstaller that removes nothing
for d in (Path(os.environ["APPDATA"]) / "SweepTestApp", Path(os.environ["LOCALAPPDATA"]) / "SweepTestApp", Path(os.environ["ProgramData"]) / "SweepTestApp"):
    d.mkdir(parents=True, exist_ok=True)
    (d / "settings.ini").write_text("x=1")
UN = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\SweepTestApp"
for path, vals in ((UN, {"DisplayName": "SweepTestApp", "Publisher": "Sweep Test", "DisplayVersion": "1.2.3", "InstallLocation": str(APPD).replace("/", "\\"),
                         "UninstallString": r"C:\SweepTestApp\uninstall.cmd"}), (r"SOFTWARE\WOW6432Node\SweepTestApp", {"Path": "C:\\SweepTestApp"})):
    with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
        for n, v in vals.items():
            winreg.SetValueEx(k, n, 0, winreg.REG_SZ, v)
with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Software\SweepTestApp\Settings", 0, winreg.KEY_SET_VALUE) as k:
    winreg.SetValueEx(k, "Theme", 0, winreg.REG_SZ, "dark")
with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as k:
    winreg.SetValueEx(k, "SweepTestApp", 0, winreg.REG_SZ, r"C:\SweepTestApp\app.exe --tray")
P.powershell(r"$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\SweepTestApp.lnk'); $s.TargetPath='C:\SweepTestApp\app.exe'; $s.Save(); "
             r"Register-ScheduledTask -TaskName 'SweepTestApp Update' -Action (New-ScheduledTaskAction -Execute 'C:\SweepTestApp\app.exe') -Trigger (New-ScheduledTaskTrigger -Daily -At 03:00) -Force | Out-Null", 60)
subprocess.run(["sc.exe", "create", "SweepTestAppSvc", "binPath=", r"C:\SweepTestApp\app.exe", "start=", "demand"], capture_output=True)

prog = next((p for p in U.list_programs() if p["name"] == "SweepTestApp"), None)
check(prog is not None and prog["location"].lower() == r"c:\sweeptestapp", f"test program listed with its folder: {prog and prog['location']}")
if prog:
    r = U.run_uninstaller(prog, quiet=False, timeout=60)
    check(r["still"], "broken uninstaller ran and left the program registered")
    items = U.find_leftovers(prog)
    kinds = {it["kind"] for it in items if it["exact"]}
    print("     leftovers:", [(it["kind"], it["path"], it["exact"]) for it in items])
    for k in ("folder", "reg", "run", "shortcut", "task", "service"):
        check(k in kinds, f"leftover kind found: {k}")
    stray = [it["path"] for it in items if it["exact"] and "sweeptestapp" not in it["path"].lower().replace(" ", "")]
    check(not stray, f"nothing unrelated is ticked {stray}")
    session = cleaner.new_session()
    res = U.remove_leftovers([it for it in items if it["exact"]], session, "SweepTestApp")
    print("     removal:", res)
    check(not res["failed"], f"all leftovers removed {res['failed']}")
    check(not APPD.exists() or res["reboot"] > 0, "program folder gone (or queued for restart)")
    check(not (Path(os.environ["APPDATA"]) / "SweepTestApp").exists(), "AppData folder gone")
    check(not U.still_installed(prog), "uninstall entry gone")
    check(tweaks.reg_get("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run", "SweepTestApp") is None, "Run entry gone")
    check(P.powershell("if(Get-ScheduledTask -TaskName 'SweepTestApp Update' -EA SilentlyContinue){'yes'}", 30).strip() != "yes", "task gone")
    check(subprocess.run(["sc.exe", "query", "SweepTestAppSvc"], capture_output=True).returncode != 0, "service gone")
    check(any(f.name.startswith(session) for f in P.REG_BACKUP.iterdir()), "registry backup written")
    check((P.QUARANTINE / session / "manifest.txt").exists(), "files are in quarantine")
    n = cleaner.restore(str(P.QUARANTINE / session))
    check((Path(os.environ["APPDATA"]) / "SweepTestApp").exists(), f"restore from quarantine works ({n} items)")

# ---------------- program updates through winget: real catalogue, real download, real install ----------------
print("\n== program updates (winget)")
from sweep import updates as UPD  # noqa: E402

exe = UPD.winget_exe()
check(bool(exe), f"winget found: {exe}")
if exe:
    res = UPD.scan()
    items = res["items"]
    note("winget updates: " + ", ".join(f"{i['id']} {i['version']}>{i['available']} @{i['host'] or '?'}" for i in items[:12]))
    check(res["winget"] and len(items) > 0, f"outdated programs found on this machine: {len(items)}")
    check(all(i["id"] and "." in i["id"] and i["available"] and i["title"] for i in items), "every row has an id, a title and a new version")
    known = [i for i in items if i["host"] and i["sha256"]]
    check(len(known) >= max(1, len(items) * 0.8), f"vendor address and SHA-256 known for most packages ({len(known)}/{len(items)})")
    pick = next((i for k in ("7zip.7zip", "GitHub.cli", "JRSoftware.InnoSetup", "Microsoft.PowerShell") for i in items if i["id"] == k), None)
    if pick:
        before = UPD.installed_version(pick["id"])
        r = UPD.upgrade(pick["id"])
        after = UPD.installed_version(pick["id"])
        check(r["ok"], f"{pick['id']} updated {before} -> {after}: {r}")
        note(f"winget upgrade {pick['id']}: {before} -> {after}, {r}")
        check(bool(after) and after != before, f"installed version changed ({before} -> {after}, catalogue {pick['available']})")
        again = UPD.upgrade(pick["id"])
        check(again["ok"] and again["reason"] == "uptodate", f"second run reports up to date: {again}")
        rest = UPD.scan(details=False)["items"]
        check(pick["id"] not in [i["id"] for i in rest], "updated program left the list")
    else:
        print("     no small package to update on this machine: install step skipped")

print()
print("FAILED:" if fails else "ALL PASSED", *fails, sep="\n  ")
sys.exit(1 if fails else 0)
