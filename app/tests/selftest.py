"""Windows self-test, run by GitHub Actions on a real Windows machine (see .github/workflows/selftest.yml).
Checks privacy switches, startup switches and browser history cleaning, then puts everything back."""
from __future__ import annotations

import os
import sqlite3
import sys
import winreg
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sweep import cleaner, platform as P, tweaks  # noqa: E402

fails: list[str] = []


def check(cond: bool, what: str):
    print(("OK   " if cond else "FAIL ") + what, flush=True)
    if not cond:
        fails.append(what)


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

print()
print("FAILED:" if fails else "ALL PASSED", *fails, sep="\n  ")
sys.exit(1 if fails else 0)
