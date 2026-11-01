"""Windows self-test, run by GitHub Actions on a real Windows machine (see .github/workflows/selftest.yml).
Checks privacy switches, startup switches and browser history cleaning, then puts everything back."""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
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
TEST_RUN = "SweepSelfTest Тест"          # a Cyrillic name: PowerShell must hand it over in UTF-8, not in the console code page
for hive, root in ((winreg.HKEY_CURRENT_USER, "User"), (winreg.HKEY_LOCAL_MACHINE, "System")):
    with winreg.CreateKeyEx(hive, RUN, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
        winreg.SetValueEx(k, TEST_RUN, 0, winreg.REG_SZ, r"C:\Windows\notepad.exe /Проверка")
    e = next((x for x in tweaks.startup_entries() if x["name"] == TEST_RUN and x["source"] == root), None)
    check(e is not None, f"startup entry listed ({root})")
    check(e is not None and e["command"].endswith("/Проверка"), f"Cyrillic name and command read correctly ({root})")
    if e:
        tweaks.set_startup(e, False)
        e2 = next(x for x in tweaks.startup_entries() if x["name"] == TEST_RUN and x["source"] == root)
        check(e2["enabled"] is False, f"startup disabled ({root})")
        tweaks.set_startup(e2, True)
        e3 = next(x for x in tweaks.startup_entries() if x["name"] == TEST_RUN and x["source"] == root)
        check(e3["enabled"] is True, f"startup enabled again ({root})")
        root_s, path = tweaks._split_ps_path(e["approved"])
        tweaks.reg_del(root_s, path, TEST_RUN)
    with winreg.OpenKey(hive, RUN, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
        winreg.DeleteValue(k, TEST_RUN)

# what Task Manager shows beyond the Run keys, and states written by other tools
APPROVED = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN, 0, winreg.KEY_SET_VALUE) as k:
    winreg.SetValueEx(k, "PSweepProbe", 0, winreg.REG_SZ, r"C:\Windows\notepad.exe")      # a name starting with "PS" is a program, not a PowerShell field
for first, expect in ((0x07, False), (0x06, True), (0x01, False), (0x02, True)):
    tweaks.reg_set("HKCU", APPROVED, "PSweepProbe", bytes([first]) + bytes(11))
    e = next((x for x in tweaks.startup_entries() if x["name"] == "PSweepProbe"), None)
    check(e is not None and e["enabled"] is expect, f"StartupApproved first byte {first:#04x} read as {'on' if expect else 'off'}")
tweaks.reg_del("HKCU", APPROVED, "PSweepProbe")
with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN, 0, winreg.KEY_SET_VALUE) as k:
    winreg.DeleteValue(k, "PSweepProbe")
common = P.powershell("[Environment]::GetFolderPath('CommonStartup')", 30).strip()
lnk = Path(common) / "SweepSelfTest.lnk"
P.powershell(f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}'); $s.TargetPath='C:\\Windows\\notepad.exe'; $s.Arguments='/startup'; $s.Save()", 30)
e = next((x for x in tweaks.startup_entries() if x["name"] == "SweepSelfTest.lnk"), None)
check(e is not None and e["source"] == "FolderAll" and e["command"].lower().endswith("notepad.exe /startup"),
      f"shortcut in the all-users Startup folder listed with its target: {e and (e['source'], e['command'])}")
if e:
    tweaks.set_startup(e, False)
    check(next(x for x in tweaks.startup_entries() if x["name"] == "SweepSelfTest.lnk")["enabled"] is False, "all-users Startup folder item switched off")
    tweaks.set_startup(e, True)
    check(next(x for x in tweaks.startup_entries() if x["name"] == "SweepSelfTest.lnk")["enabled"] is True, "all-users Startup folder item switched on again")
    tweaks.reg_del("HKLM", r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder", "SweepSelfTest.lnk")
lnk.unlink(missing_ok=True)
# a Microsoft Store startup task, made the way Windows records one
store_key = tweaks._split_ps_path(tweaks.STORE_TASKS)[1] + r"\SweepSelfTest_8wekyb3d8bbwe\SweepStartupTask"
tweaks.reg_set("HKCU", store_key, "State", 2)
e = next((x for x in tweaks.startup_entries() if x["source"] == "Store" and x["name"] == "SweepStartupTask"), None)
check(e is not None and e["enabled"] is True and e["display"] == "SweepSelfTest", f"Store app startup task listed: {e}")
if e:
    tweaks.set_startup(e, False)
    check(tweaks.reg_get("HKCU", store_key, "State") == 1, "Store startup task switched off the way Task Manager does (State 1)")
    check(next(x for x in tweaks.startup_entries() if x["name"] == "SweepStartupTask")["enabled"] is False, "Store startup task reads as off")
tweaks.reg_set("HKCU", store_key, "State", 4)
e = next((x for x in tweaks.startup_entries() if x["name"] == "SweepStartupTask"), None)
check(e is not None and e["locked"] is True and e["enabled"] is True, "Store startup task set by policy is shown as locked")
P.powershell(f"Remove-Item -LiteralPath 'HKCU:\\{tweaks._split_ps_path(tweaks.STORE_TASKS)[1]}\\SweepSelfTest_8wekyb3d8bbwe' -Recurse -Force", 30)
real_store = [x for x in tweaks.startup_entries() if x["source"] == "Store"]
note(f"Store startup tasks on this machine: {[(x['display'], x['enabled']) for x in real_store][:10]}")

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

# ---------- cleaning keeps the programs chosen to open files ----------
ASSOC_PS = r"""$r=@{}
foreach($k in (Get-ChildItem 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts' -EA SilentlyContinue)){
  foreach($s in 'UserChoice','UserChoiceLatest','UserChoiceLatest\ProgId','OpenWithProgids','OpenWithList'){
    $i=Get-ItemProperty -LiteralPath (Join-Path $k.PSPath $s) -EA SilentlyContinue
    if($i){ $r["$($k.PSChildName)|$s"]=(($i.PSObject.Properties | ? Name -notlike 'PS*' | % { "$($_.Name)=$($_.Value)" }) -join ';') } } }
foreach($k in (Get-ChildItem 'HKCU:\Software\Microsoft\Windows\Shell\Associations\UrlAssociations' -EA SilentlyContinue)){
  $v=(Get-ItemProperty -LiteralPath (Join-Path $k.PSPath 'UserChoice') -EA SilentlyContinue).ProgId; if($v){ $r["$($k.PSChildName)|url"]=$v } }
$r['classes keys']=@(Get-ChildItem 'HKCU:\Software\Classes' -EA SilentlyContinue).Count
$r"""
FE = r"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.sweeptest"
MUI = r"Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache"
APPP = r"Software\Microsoft\Windows\CurrentVersion\App Paths"
GONE = r"C:\SweepGone\gone.exe"


def _set(path, name, value, kind=winreg.REG_SZ):
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, name, 0, kind, value)


def _has(path, name=""):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as k:
            winreg.QueryValueEx(k, name)
        return True
    except OSError:
        return False


# a file type with a chosen program, the way Windows stores it
_set(r"Software\Classes\.sweeptest", "", "SweepTest.File")
_set(r"Software\Classes\SweepTest.File\shell\open\command", "", r'"C:\Windows\System32\notepad.exe" "%1"')
_set(FE + r"\OpenWithProgids", "SweepTest.File", b"", winreg.REG_NONE)
try:
    _set(FE + r"\UserChoice", "ProgId", "SweepTest.File")
    _set(FE + r"\UserChoice", "Hash", "SweepSelfTest")
except OSError as e:
    note(f"UserChoice for .sweeptest not written ({e}), the real ones are compared anyway")
# names of an installed and of a removed program; App Paths and Run entries that only look missing
_set(MUI, sys.executable + ".FriendlyAppName", "Python (Sweep self-test)")
_set(MUI, GONE + ".FriendlyAppName", "Gone (Sweep self-test)")
_set(APPP + r"\sweeptest-here.exe", "", sys.executable)
_set(APPP + r"\sweeptest-gone.exe", "", GONE)
alias = next(iter(sorted((Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "WindowsApps").glob("*.exe"))), None)
if alias:
    _set(APPP + r"\sweeptest-alias.exe", "", str(alias))
_set(RUN, "SweepTest bare", "rundll32.exe shell32.dll,Control_RunDLL")
_set(RUN, "SweepTest gone", f'"{GONE}" /quiet')

before_assoc = P.ps_json(ASSOC_PS, 120) or {}
check(len(before_assoc) > 1, f"associations read: {len(before_assoc)} entries")
s_junk = cleaner.new_session()
for c in cleaner.CATEGORIES:
    if c.default and c.id != "bin":
        cleaner.scan(c)
        cleaner.quarantine(c, s_junk)
check(not any("iconcache" in str(x).lower() for c in cleaner.CATEGORIES for x in c.paths), "icon cache is never cleaned")
s_reg = s_junk + "9"            # its own .reg files, restored below
fixed = {c.id: extras.reg_clean(c, s_reg) for c in extras.REG_CATEGORIES if extras.reg_scan(c) > 0}
print("     registry cleaned:", fixed)
after_assoc = P.ps_json(ASSOC_PS, 120) or {}
changed = sorted(k for k in set(before_assoc) | set(after_assoc) if before_assoc.get(k) != after_assoc.get(k))
check(not changed, f"file associations unchanged after junk and registry cleaning ({len(before_assoc)} entries){': ' + str(changed[:8]) if changed else ''}")
check(_has(FE + r"\OpenWithProgids", "SweepTest.File") and _has(r"Software\Classes\SweepTest.File\shell\open\command"), "test file type and its program kept")
check(_has(MUI, sys.executable + ".FriendlyAppName"), "MuiCache: name of an installed program kept")
check(not _has(MUI, GONE + ".FriendlyAppName"), "MuiCache: name of a removed program cleaned")
check(_has(APPP + r"\sweeptest-here.exe") and not _has(APPP + r"\sweeptest-gone.exe"), "App Paths: only the entry of a missing file removed")
if alias:
    check(_has(APPP + r"\sweeptest-alias.exe"), f"App Paths: a Store app alias ({alias.name}) is not taken for missing")
check(_has(RUN, "SweepTest bare") and not _has(RUN, "SweepTest gone"), "Run: a bare command kept, a missing file removed")

# put everything back
print("     junk restored:", cleaner.restore(str(P.QUARANTINE / s_junk)), " registry restored:", extras.reg_restore(s_reg))
for path in (r"Software\Classes\SweepTest.File", r"Software\Classes\.sweeptest", FE, APPP + r"\sweeptest-here.exe", APPP + r"\sweeptest-gone.exe", APPP + r"\sweeptest-alias.exe"):
    subprocess.run(["reg", "delete", "HKCU\\" + path, "/f"], capture_output=True)
for path, name in ((MUI, sys.executable + ".FriendlyAppName"), (MUI, GONE + ".FriendlyAppName"), (RUN, "SweepTest bare"), (RUN, "SweepTest gone")):
    tweaks.reg_del("HKCU", path, name)
check(not _has(r"Software\Classes\.sweeptest") and not _has(RUN, "SweepTest gone"), "association test entries removed")

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
    from sweep import extras
    check(any(b["session"] == session for b in extras.reg_backups()), "the uninstall backup is listed on the Registry page")
    nr = extras.reg_restore(session)
    check(P.powershell("if(Get-ScheduledTask -TaskName 'SweepTestApp Update' -EA SilentlyContinue){'yes'}", 30).strip() == "yes",
          f"scheduled task restored from the backup ({nr} files)")
    check(tweaks.reg_get("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run", "SweepTestApp") is not None, "Run entry restored from the backup")
    check(not any(b["session"] == session for b in extras.reg_backups()), "the restored backup is gone from the list")
    # tidy up what the restore brought back
    P.powershell("Unregister-ScheduledTask -TaskName 'SweepTestApp Update' -Confirm:$false -EA SilentlyContinue", 30)
    subprocess.run(["sc.exe", "delete", "SweepTestAppSvc"], capture_output=True)
    for k in (r"HKCU\Software\SweepTestApp", r"HKLM\SOFTWARE\WOW6432Node\SweepTestApp", r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\SweepTestApp"):
        subprocess.run(["reg.exe", "delete", k, "/f", "/reg:64"], capture_output=True)
    tweaks.reg_del("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run", "SweepTestApp")

# restoring never loses what cannot go back (here: the folder exists again, moving would nest the copy inside it)
keep = P.QUARANTINE / "selftest_keep"
(keep / "dir").mkdir(parents=True, exist_ok=True)
(keep / "dir" / "a.txt").write_text("quarantined copy", "utf-8")
taken = Path(tempfile.gettempdir()) / "sweep-selftest-taken"
taken.mkdir(exist_ok=True)
(keep / "manifest.txt").write_text(f"{keep / 'dir'}|{taken}\n", "utf-8")
check(cleaner.restore(str(keep)) == 0 and (keep / "dir" / "a.txt").exists() and not (taken / "dir").exists(),
      "a folder that cannot be restored stays in quarantine")
shutil.rmtree(keep, ignore_errors=True)
shutil.rmtree(taken, ignore_errors=True)

# ---------------- a leftover key the installer locked, and deleting copies for good ----------------
print("\n== locked leftovers and deleting copies")
lock_out = P.powershell(r"""try{ $p='HKLM:\SOFTWARE\SweepLockedTest'; New-Item "$p\Sub" -Force | Out-Null; Set-ItemProperty "$p\Sub" -Name V -Value 'x'
  # the way protective software locks its keys: only SYSTEM may write, Administrators are denied deletion
  foreach($k in @("$p\Sub",$p)){ $acl=Get-Acl $k; $acl.SetSecurityDescriptorSddlForm('D:P(A;CI;KA;;;SY)(A;CI;KR;;;BA)(D;CI;SD;;;BA)','Access'); Set-Acl $k $acl }
  (Get-Acl $p).Sddl }catch{ 'error: ' + $_ }""", 60)
note(f"locked test key: {lock_out.strip()[-160:]}")
locked = subprocess.run(["reg.exe", "delete", r"HKLM\SOFTWARE\SweepLockedTest", "/f", "/reg:64"], capture_output=True)
check(locked.returncode != 0, "test key is locked: reg.exe alone cannot delete it")
lsession = cleaner.new_session()
res = U.remove_leftovers([{"kind": "reg", "path": r"HKLM\SOFTWARE\SweepLockedTest", "size": 0}], lsession, "LockedTest")
check(res["removed"] == 1 and not res["failed"], f"locked leftover key removed: {res}")
check(P.powershell(r"Test-Path 'HKLM:\SOFTWARE\SweepLockedTest'", 30).strip() == "False", "locked key is gone")
backups = list(P.REG_BACKUP.glob(f"{lsession}_uninstall_*.reg"))
check(bool(backups) and "SweepLockedTest\\Sub" in backups[0].read_text("utf-16"), "the backup of the locked key is complete")
check(cleaner.delete_session(str(P.QUARANTINE / lsession)) >= 1 and not list(P.REG_BACKUP.glob(f"{lsession}_*")), "copies of the session deleted for good")
qs = cleaner.new_session()
ro = P.QUARANTINE / qs / "uninstall_RO"
ro.mkdir(parents=True, exist_ok=True)
(ro / "readonly.dll").write_bytes(b"x")
subprocess.run(["attrib", "+R", str(ro / "readonly.dll")], capture_output=True)
cleaner.delete_session(str(P.QUARANTINE / qs))
check(not (P.QUARANTINE / qs).exists(), "a quarantined read-only file is deleted for good too")

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
    pick = next((i for k in ("GitHub.cli", "7zip.7zip", "JRSoftware.InnoSetup", "Microsoft.PowerShell") for i in items if i["id"] == k), None)
    if pick:
        before = UPD.installed_version(pick["id"])
        events: list[tuple] = []
        r = UPD.upgrade(pick["id"], progress=lambda ph, got, total: events.append((ph, got, total)))
        after = UPD.installed_version(pick["id"])
        downloads = [e for e in events if e[0] == "download" and e[1] > 0]
        note(f"winget progress via {r.get('via')}: {len(events)} events, {len(downloads)} with bytes, phases {sorted({e[0] for e in events})}, "
             f"last {events[-1] if events else None}")
        check(any(e[0] == "install" for e in events), "install phase reported after the download")
        wg = Path(tempfile.gettempdir()) / "WinGet"
        note("winget temp folder after the update: " + (", ".join(sorted(p.name for p in wg.iterdir()))[:600] if wg.exists() else "missing"))
        check(r["ok"], f"{pick['id']} updated {before} -> {after}: {r}")
        note(f"winget upgrade {pick['id']}: {before} -> {after}, {r}")
        check(bool(after) and after != before, f"installed version changed ({before} -> {after}, catalogue {pick['available']})")
        again = UPD.upgrade(pick["id"])
        check(again["ok"] and again["reason"] == "uptodate", f"second run reports up to date: {again}")
        rest = UPD.scan(details=False)["items"]
        check(pick["id"] not in [i["id"] for i in rest], "updated program left the list")
    else:
        print("     no small package to update on this machine: install step skipped")

    # the table read from the wide pseudo console matches the one read through a pipe (no names or ids cut short)
    rc_p, raw_p = UPD._run(["upgrade", "--source", "winget"] + UPD.COMMON, 300)
    rc_c, scr, how_c = UPD._capture(["upgrade", "--source", "winget"] + UPD.COMMON, 300)
    pipe_rows = {r["id"]: r for r in UPD._repair_ids(UPD.parse_upgrades(raw_p))}
    con_rows = {r["id"]: r for r in UPD.parse_upgrades(scr)}
    note(f"upgrade table via {how_c}: {len(con_rows)} rows, pipe {len(pipe_rows)} rows; only pipe {sorted(set(pipe_rows) - set(con_rows))[:6]}, "
         f"only console {sorted(set(con_rows) - set(pipe_rows))[:6]}")
    check(how_c == "conpty", f"tables are read from a pseudo console ({how_c})")
    check(set(con_rows) == set(pipe_rows) and len(con_rows) > 0, "pseudo console and pipe list the same packages")
    check(all(con_rows[i]["version"] == pipe_rows[i]["version"] and con_rows[i]["available"] == pipe_rows[i]["available"] for i in con_rows if i in pipe_rows),
          "same versions in both")
    check(not any(r["name"].endswith(("\u2026", "...")) or r["id"].endswith(("\u2026", "...")) for r in con_rows.values()), "nothing shortened in the wide console")
    if any(not r.get("_arp") for r in items):
        note("not matched to Installed apps: " + ", ".join(r["id"] for r in items if not r.get("_arp"))[:400])
    check(sum(1 for r in items if r.get("_arp")) >= len(items) * 0.7, f"rows matched to Installed apps ({sum(1 for r in items if r.get('_arp'))}/{len(items)})")
    store = [r for r in items if not r.get("_arp")]
    note("Store apps: " + ", ".join(f"{r['id']} -> {(r.get('_store') or {}).get('name')} {os.path.basename((r.get('_store') or {}).get('icon', ''))}" for r in store))
    check(all(r.get("_store") and os.path.isfile(r["_store"]["icon"]) for r in store), f"Store apps found with their logo ({len(store)})")
    note("open programs: " + (", ".join(r["id"] for r in items if r.get("running")) or "none"))
    sus = [r for r in items if r.get("suspect")]
    note("look-alikes: " + (", ".join(f"{r['id']} ({r['why']}: {r.get('installedName')} / {r.get('catName')})" for r in sus) or "none"))
    check(len(sus) <= 2, f"almost no package marked as another program ({len(sus)})")
    with_notes = [r["id"] for r in items if r.get("notes") or r.get("notesUrl")]
    note(f"release notes known for {len(with_notes)}/{len(items)}: {with_notes[:8]}")

    # "install over the old version", the route taken when winget does not pick the installed program for an upgrade
    rest_items = UPD.scan(details=False)["items"]
    over = next((i for k in ("7zip.7zip", "Git.Git", "StrawberryPerl.StrawberryPerl", "ShiningLight.OpenSSL.Dev") for i in rest_items if i["id"] == k), None)
    if over:
        before = UPD.installed_version(over["id"])
        ev: list[tuple] = []
        r = UPD.install(over["id"], progress=lambda ph, got, total: ev.append(ph))
        after = UPD.installed_version(over["id"])
        note(f"install over {over['id']}: {before} -> {after}, {r}, phases {sorted(set(ev))}")
        check(r["ok"] and after and after != before, f"installing over the old version updates it ({over['id']} {before} -> {after})")
        again = UPD.upgrade(over["id"], before=after)
        note(f"upgrade after install-over: {again}")
        check(again["ok"] and again["reason"] == "uptodate", f"nothing left to update afterwards ({again['reason']})")

    # search the whole catalogue
    found = UPD.search("vlc")
    note("search vlc: " + ", ".join(f"{r['id']} {r['version']}" for r in found[:8]))
    check(any(r["id"] == "VideoLAN.VLC" for r in found), "search finds VideoLAN.VLC")
    check(all(r["id"] and not r["id"].endswith(("\u2026", "...")) for r in found), "search ids are complete")

    # every program Sweep offers to install exists in the catalogue
    from concurrent.futures import ThreadPoolExecutor

    from sweep import catalog as CAT
    with ThreadPoolExecutor(max_workers=4) as ex:
        shown = dict(zip([p[0] for p in CAT.PROGRAMS], ex.map(lambda p: UPD.show(p[0]), CAT.PROGRAMS), strict=True))
    missing = [pid for pid, d in shown.items() if not (d["name"] and d["installer"])]
    missing = [pid for pid in missing if not (UPD.show(pid)["installer"])]      # one quiet retry
    note(f"catalogue picks: {len(CAT.PROGRAMS) - len(missing)}/{len(CAT.PROGRAMS)} found" + (f", missing {missing}" if missing else ""))
    check(not missing, f"every program offered for installing is in the catalogue {missing}")
    note("pick sources: " + ", ".join(f"{pid}@{UPD.host(d['installer'])}" for pid, d in list(shown.items())[:46] if d["installer"])[:900])

    # a real install of a small program, then it shows up as installed
    target = "SumatraPDF.SumatraPDF"
    had = target in UPD.installed_ids()
    ev2: list[tuple] = []
    r = UPD.install(target, progress=lambda ph, got, total: ev2.append((ph, int(got), int(total))))
    note(f"install {target}: {r}, had it before: {had}, events {len(ev2)}: {ev2[:4]} ... {ev2[-2:]}")
    check(r["ok"], f"{target} installed: {r}")
    check(target in UPD.installed_ids(), f"{target} is listed as installed afterwards")
    check(any(e[0] == "download" for e in ev2) or had, "install reports download progress")
    # a big download (installer only, nothing installed) to see the progress arrive while it is still running
    import time as _time
    dest = Path(tempfile.gettempdir()) / "sweep-dl-test"
    shutil.rmtree(dest, ignore_errors=True)

    for big in ("LLVM.LLVM", "Unity.UnityHub"):
        prog = UPD.Progress()
        t0 = _time.time()
        rc, out, how = UPD._stream(["download", "--id", big, "--exact", "--source", "winget", "-d", str(dest), "--accept-package-agreements"] + UPD.COMMON,
                                   900, prog)
        took = _time.time() - t0
        mid = [e for e in prog.log if e[2] > 0 and e[0] < took - 0.5]
        note(f"download {big} via {how}: rc={rc & 0xFFFFFFFF:#x}, {took:.1f} s, events {len(prog.log)}, "
             f"before the end {len(mid)}: {prog.log[:8]} ... {prog.log[-3:]}")
        check(how == "conpty", f"winget runs inside a pseudo console ({how})")
        if rc == 0:
            check(len(mid) >= 2, f"live progress while downloading {big} ({len(mid)} updates before it finished)")
            break
    shutil.rmtree(dest, ignore_errors=True)

# ---------------- title bar in the theme's colours ----------------
print("\n== title bar")
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from sweep import winframe  # noqa: E402

qa = QApplication.instance() or QApplication([])
w = QWidget()
w.setWindowTitle("Sweep title bar test")
w.show()
qa.processEvents()
build = int(sys.getwindowsversion().build)
for theme in ("dark", "light"):
    res = winframe.apply(int(w.winId()), theme)
    note(f"title bar {theme} on build {build}: " + ", ".join(f"{k}={v:#x}" for k, v in res.items()))
    check(res.get("dark") == 0, f"{theme}: dark/light frame accepted by Windows")
    if build >= 22000:
        check(res.get("caption") == 0 and res.get("text") == 0, f"{theme}: caption colours accepted by Windows 11")
w.close()

print()
print("FAILED:" if fails else "ALL PASSED", *fails, sep="\n  ")
sys.exit(1 if fails else 0)
