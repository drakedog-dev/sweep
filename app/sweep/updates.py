"""Program updates and installs through winget, the Windows Package Manager that ships with Windows 10 and 11.

Every package in the winget catalogue points to the vendor's own download address (7-zip.org, videolan.org,
github.com/<vendor>) and carries the SHA-256 of the installer; winget refuses to run a file whose hash differs.
Sweep lists what is out of date, checks that the catalogue entry really is the installed program, and updates
or installs only what the user picks."""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from . import platform as P

SOURCE = "winget"
COMMON = ["--accept-source-agreements", "--disable-interactivity"]
_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_SEP = re.compile(r"^\s*-{8,}\s*$")
_ELLIPSIS = ("\u2026", "...")
CAP_COLS, CAP_ROWS = 512, 600      # pseudo console size for tables: wide enough that winget never shortens a name or an id

NOT_FOUND = 0x8A150014             # NO_APPLICATIONS_FOUND: for `upgrade`, winget does not see the program installed
NOT_APPLICABLE = 0x8A15002B        # UPDATE_NOT_APPLICABLE

# winget exit codes (AppInstallerErrors.h) turned into a short reason shown next to the program
REASONS = {
    0x8A15002B: "uptodate",   # UPDATE_NOT_APPLICABLE
    0x8A150014: "notfound",   # NO_APPLICATIONS_FOUND
    0x8A150011: "hash",       # INSTALLER_HASH_MISMATCH: the downloaded file is not the one in the catalogue
    0x8A150008: "download",   # DOWNLOAD_FAILED
    0x8A15002E: "download",   # DOWNLOAD_SIZE_MISMATCH
    0x8A150101: "inuse",      # INSTALL_PACKAGE_IN_USE
    0x8A150102: "busy",       # INSTALL_INSTALL_IN_PROGRESS
    0x8A150103: "inuse",      # INSTALL_FILE_IN_USE
    0x8A150104: "deps",       # INSTALL_MISSING_DEPENDENCY
    0x8A150105: "disk",       # INSTALL_DISK_FULL
    0x8A150106: "memory",     # INSTALL_INSUFFICIENT_MEMORY
    0x8A150107: "network",    # INSTALL_NO_NETWORK
    0x8A150109: "reboot",     # INSTALL_REBOOT_REQUIRED_TO_FINISH: installed, a restart finishes it
    0x8A15010A: "rebootfirst",  # INSTALL_REBOOT_REQUIRED_TO_INSTALL
    0x8A15010B: "reboot",     # INSTALL_REBOOT_INITIATED
    0x8A15010C: "cancel",     # INSTALL_CANCELLED_BY_USER
    0x8A15010D: "uptodate",   # INSTALL_ALREADY_INSTALLED
    0x8A15010E: "uptodate",   # INSTALL_DOWNGRADE
    0x8A15010F: "policy",     # INSTALL_BLOCKED_BY_POLICY
    0x8A150110: "deps",       # INSTALL_DEPENDENCIES
    0x8A150111: "inuse",      # INSTALL_PACKAGE_IN_USE_BY_APPLICATION
    0x8A150056: "noadmin",    # INSTALLER_PROHIBITS_ELEVATION: tried as the signed-in user too, and that did not work
    0x8A15000A: "source",     # INDEX_INTEGRITY_COMPROMISED
    0x8A15000B: "source",     # SOURCES_INVALID
    0x8A15000F: "source",     # SOURCE_DATA_MISSING: "Failed when opening source(s)", repair was tried and did not help
}
PROHIBITS_ELEVATION = 0x8A150056
SUCCESS_REASONS = ("reboot", "uptodate")

# ---------------- demo data (Linux / screenshots) ----------------
_DEMO = [
    {"id": "Spotify.Spotify", "name": "Spotify", "version": "1.2.40.599", "available": "1.2.48.405", "publisher": "Spotify AB",
     "installer": "https://download.scdn.co/SpotifyFullSetup.exe", "homepage": "https://www.spotify.com", "notes": "", "notesUrl": ""},
    {"id": "7zip.7zip", "name": "7-Zip 23.01 (x64)", "version": "23.01", "available": "24.09", "publisher": "Igor Pavlov",
     "installer": "https://7-zip.org/a/7z2409-x64.exe", "homepage": "https://www.7-zip.org/",
     "notes": "Improved code for unpacking Z archives and Mach-O files.\nSome bugs and vulnerabilities were fixed.",
     "notesUrl": "https://github.com/ip7z/7zip/releases/tag/24.09"},
    {"id": "Notepad++.Notepad++", "name": "Notepad++ (64-bit x64)", "version": "8.6.9", "available": "8.7.8", "publisher": "Notepad++ Team",
     "installer": "https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.7.8/npp.8.7.8.Installer.x64.exe",
     "homepage": "https://notepad-plus-plus.org/", "notes": "", "notesUrl": "https://notepad-plus-plus.org/news/v878-released/"},
    {"id": "VideoLAN.VLC", "name": "VLC media player", "version": "3.0.20", "available": "3.0.21", "publisher": "VideoLAN",
     "installer": "https://get.videolan.org/vlc/3.0.21/win64/vlc-3.0.21-win64.exe", "homepage": "https://www.videolan.org/", "notes": "", "notesUrl": ""},
    {"id": "Telegram.TelegramDesktop", "name": "Telegram Desktop", "version": "5.9.0", "available": "5.12.3", "publisher": "Telegram FZ-LLC",
     "installer": "https://td.telegram.org/tx64/tsetup-x64.5.12.3.exe", "homepage": "https://desktop.telegram.org/", "notes": "", "notesUrl": ""},
    {"id": "Microsoft.PowerShell", "name": "PowerShell 7-x64", "version": "7.6.6.0", "available": "7.6.8.0", "publisher": "Microsoft Corporation",
     "installer": "https://github.com/PowerShell/PowerShell/releases/download/v7.6.8/PowerShell-7.6.8-win-x64.msi",
     "homepage": "https://github.com/PowerShell/PowerShell", "notes": "", "notesUrl": "https://github.com/PowerShell/PowerShell/releases/tag/v7.6.8"},
    {"id": "Python.Launcher", "name": "Python Launcher", "version": "< 3.14.7", "available": "3.14.8", "publisher": "Python Software Foundation",
     "installer": "https://www.python.org/ftp/python/3.14.8/python-3.14.8-amd64.exe", "homepage": "https://www.python.org/", "notes": "", "notesUrl": ""},
    {"id": "chen08209.FlClash", "name": "FlClash X", "version": "0.3.2", "available": "0.9.2+2026102401", "publisher": "chen08209",
     "installer": "https://github.com/chen08209/FlClash/releases/download/v0.9.2/FlClash-0.9.2-windows-amd64-setup.exe",
     "homepage": "https://github.com/chen08209/FlClash", "notes": "", "notesUrl": ""},
]
_DEMO_SEARCH = [
    ("VLC media player", "VideoLAN.VLC", "3.0.21"), ("Notepad++", "Notepad++.Notepad++", "8.7.8"), ("OBS Studio", "OBSProject.OBSStudio", "31.1.2"),
    ("Krita", "KDE.Krita", "5.2.9"), ("Inkscape", "Inkscape.Inkscape", "1.4.2"), ("HandBrake", "HandBrake.HandBrake", "1.9.2"),
]
_DEMO_INSTALLED = {"7zip.7zip", "Telegram.TelegramDesktop", "VideoLAN.VLC", "Google.Chrome", "Valve.Steam", "Notepad++.Notepad++"}


# ---------------- running winget ----------------
def _ver_key(path: str) -> tuple:
    m = re.search(r"DesktopAppInstaller_([\d.]+)_", path)
    return tuple(int(x) for x in m.group(1).split(".")) if m else ()


def winget_exe() -> str:
    """Path to winget.exe, or "" when App Installer is missing.
    The WindowsApps alias exists per user; the package folder is the fallback for an elevated session of another account."""
    if not P.IS_WINDOWS:
        return ""
    w = shutil.which("winget")
    if w:
        return w
    local = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\winget.exe")
    if os.path.lexists(local):
        return local
    pf = os.environ.get("ProgramW6432") or os.environ.get("ProgramFiles", r"C:\Program Files")
    found = sorted(glob.glob(os.path.join(pf, "WindowsApps", "Microsoft.DesktopAppInstaller_*_x64__8wekyb3d8bbwe", "winget.exe")), key=_ver_key)
    return found[-1] if found else ""


def available() -> bool:
    return bool(winget_exe()) if P.IS_WINDOWS else True


# Flags newer than the winget an old Windows 10 may still have (App Installer never updated): an unknown flag makes
# winget print its help and stop, which used to look like "no updates".
NEW_FLAGS = {"--disable-interactivity": (1, 4)}
OLD_WINGET = (1, 6)               # below this, Sweep suggests updating App Installer from Microsoft Store
_wg_ver: tuple[int, ...] | None = None


def winget_version() -> tuple[int, ...]:
    """(1, 9, 25200) from `winget --version`; () when unknown."""
    global _wg_ver
    if _wg_ver is None:
        _wg_ver = ()
        exe = winget_exe() if P.IS_WINDOWS else ""
        if exe:
            try:
                r = subprocess.run([exe, "--version"], stdin=subprocess.DEVNULL, capture_output=True, timeout=30, creationflags=0x08000000)
                m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", r.stdout.decode("utf-8", "replace"))
                _wg_ver = tuple(int(x) for x in m.groups() if x) if m else ()
            except Exception as e:  # noqa: BLE001
                P.log(f"winget --version: {e}")
            P.log(f"winget version {'.'.join(map(str, _wg_ver)) or 'unknown'}")
    return _wg_ver


def _args(args: list[str], version: tuple[int, ...] | None = None) -> list[str]:
    v = winget_version() if version is None else version
    return [a for a in args if not (v and a in NEW_FLAGS and v < NEW_FLAGS[a])]


def _run(args: list[str], timeout: int) -> tuple[int, bytes]:
    rc, raw = _run_once(args, timeout)
    if source_broken(rc) and repair_source():
        rc, raw = _run_once(args, timeout)
    return rc, raw


def _run_once(args: list[str], timeout: int) -> tuple[int, bytes]:
    exe = winget_exe()
    if not exe:
        return -1, b""
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    try:
        r = subprocess.run([exe] + _args(args), stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout, startupinfo=si, creationflags=0x08000000)
        return r.returncode, r.stdout + (b"\n" + r.stderr if r.stderr else b"")
    except subprocess.TimeoutExpired:
        P.log(f"winget {args[:3]}: timed out after {timeout} s")
        return -2, b""
    except Exception as e:  # noqa: BLE001
        P.log(f"winget {args[:3]}: {e}")
        return -1, b""


# The winget source cannot be opened: its data package is missing or damaged ("Failed when opening source(s); try the
# 'source reset' command", 0x8A15000F Data required by the source is missing). Common after an interrupted update or
# on a PC where App Installer was never updated; every check, search and install fails until it is repaired.
SOURCE_BROKEN = {0x8A15000A, 0x8A15000B, 0x8A15000F}
_REGISTER_SOURCE_PS = r'''
$p = Get-AppxPackage -AllUsers -Name Microsoft.Winget.Source -ErrorAction SilentlyContinue | Sort-Object { [version]$_.Version } | Select-Object -Last 1
$m = if ($p) { Join-Path $p.InstallLocation 'AppxManifest.xml' } else {
  Get-ChildItem "$env:ProgramFiles\WindowsApps\Microsoft.Winget.Source_*_neutral__8wekyb3d8bbwe\AppxManifest.xml" -ErrorAction SilentlyContinue |
    Select-Object -Last 1 -ExpandProperty FullName }
if (-not $m -or -not (Test-Path $m)) { 'no package on this PC'; return }
try { Add-AppxPackage -DisableDevelopmentMode -Register $m -ErrorAction Stop; "registered $m" } catch { "failed: $($_.Exception.Message)" }
'''
_fix_lock = threading.Lock()
_fix = {"at": 0.0, "ok": False}


def source_broken(rc: int) -> bool:
    return (rc & 0xFFFFFFFF) in SOURCE_BROKEN


def _source_works() -> bool:
    rc, _ = _run_once(["search", "--id", "7zip.7zip", "--exact", "--source", SOURCE] + COMMON, 180)
    return rc != -1 and not source_broken(rc)


def repair_source() -> bool:
    """Repair the winget source, gentlest step first, and say whether it works now: refresh its data; register again
    the source package Windows already has (the usual cure for "Data required by the source is missing"); reset the
    winget source alone. Sources the user added are never touched. Tried at most once in 10 minutes."""
    if not P.IS_WINDOWS:
        return False
    with _fix_lock:
        if _fix["at"] and time.monotonic() - _fix["at"] < 600:
            return _fix["ok"]
        P.log("winget: the source cannot be opened, repairing it")
        ok = False
        steps = [("source update", lambda: _run_once(["source", "update", "--name", SOURCE], 300)[0]),
                 ("register the source package", lambda: P.powershell(_REGISTER_SOURCE_PS, 180).strip()),
                 ("source reset", lambda: _run_once(["source", "reset", "--name", SOURCE, "--force"], 300)[0])]
        for what, step in steps:
            try:
                res = step()
            except Exception as e:  # noqa: BLE001
                res = e
            if isinstance(res, int):
                res = f"rc=0x{res & 0xFFFFFFFF:x}"
            ok = _source_works()
            P.log(f"winget: {what}: {res}; the source {'works' if ok else 'still fails'}")
            if ok:
                break
        _fix.update(at=time.monotonic(), ok=ok)
        return ok


def lines(raw: bytes | str) -> list[str]:
    """Console output as clean lines: no colour codes, and only the final state of lines that a spinner
    or a progress bar rewrote with carriage returns."""
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
    text = _ANSI.sub("", text).replace("\ufeff", "")
    out = []
    for line in text.split("\n"):
        line = line.rstrip("\r")
        out.append(line.split("\r")[-1].rstrip())
    return out


_CSI = re.compile(r"\x1b\[([0-9;?]*)([ -/]*)([@-~])")
_OSC_ANY = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)?")


def vt_screen(text: str, cols: int = CAP_COLS, rows: int = CAP_ROWS) -> list[str]:
    """What a terminal shows after drawing `text`: a pseudo console moves the cursor and erases with escape
    sequences instead of printing spaces, so tables can only be read from the drawn screen."""
    scr: dict[int, list[str]] = {}
    r = c = top = 0                      # cursor (absolute row, column) and the absolute row at the top of the viewport

    def row(n: int) -> list[str]:
        return scr.setdefault(n, [])

    def newline():
        nonlocal r, top
        r += 1
        if r - top >= rows:
            top = r - rows + 1

    def put(ch: str):
        nonlocal c
        if c >= cols:
            c = 0
            newline()
        ln = row(r)
        if len(ln) < c:
            ln.extend(" " * (c - len(ln)))
        if len(ln) == c:
            ln.append(ch)
        else:
            ln[c] = ch
        c += 1

    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "\x1b":
            m = _CSI.match(text, i)
            if m:
                i = m.end()
                params, final = m.group(1), m.group(3)
                if params.startswith("?"):
                    continue
                nums = [int(x) if x.isdigit() else 0 for x in params.split(";")] if params else []
                a = nums[0] if nums else 0
                one = a or 1
                if final in "Hf":
                    r = top + max(1, a or 1) - 1
                    c = max(1, nums[1] if len(nums) > 1 and nums[1] else 1) - 1
                elif final in "G`":
                    c = one - 1
                elif final == "d":
                    r = top + one - 1
                elif final == "C":
                    c += one
                elif final == "D":
                    c = max(0, c - one)
                elif final == "A":
                    r = max(top, r - one)
                elif final == "B":
                    r += one
                elif final == "E":
                    r += one
                    c = 0
                elif final == "F":
                    r = max(top, r - one)
                    c = 0
                elif final == "K":
                    ln = row(r)
                    if a == 0:
                        del ln[c:]
                    elif a == 1:
                        ln[:c + 1] = [" "] * min(len(ln), c + 1)
                    else:
                        ln.clear()
                elif final == "X":
                    ln = row(r)
                    for k in range(c, min(len(ln), c + one)):
                        ln[k] = " "
                elif final == "P":
                    del row(r)[c:c + one]
                elif final == "@":
                    ln = row(r)
                    if c < len(ln):
                        ln[c:c] = [" "] * one
                elif final == "J":
                    if a in (2, 3):
                        for k in [k for k in scr if k >= top]:
                            del scr[k]
                    elif a == 0:
                        del row(r)[c:]
                        for k in [k for k in scr if k > r]:
                            del scr[k]
                elif final == "S":
                    top += one
                    r += one
                continue
            m = _OSC_ANY.match(text, i)
            if m and text.startswith("\x1b]", i):
                i = m.end()
                continue
            i += 2
            continue
        i += 1
        if ch == "\r":
            c = 0
        elif ch == "\n":
            newline()
        elif ch == "\b":
            c = max(0, c - 1)
        elif ch == "\t":
            c = (c // 8 + 1) * 8
        elif ch >= " " and ch != "\x7f" and ch != "\ufeff":
            put(ch)
    if not scr:
        return []
    return ["".join(scr.get(k, [])).rstrip() for k in range(min(scr), max(scr) + 1)]


def _capture(args: list[str], timeout: int, on_text=None) -> tuple[int, list[str], str]:
    """Run winget and return its screen as lines. Inside a wide pseudo console nothing is shortened with "…";
    a plain pipe (older Windows) is the fallback."""
    rc, screen, how = _capture_once(args, timeout, on_text)
    if source_broken(rc) and repair_source():
        rc, screen, how = _capture_once(args, timeout, on_text)
    return rc, screen, how


def _capture_once(args: list[str], timeout: int, on_text=None) -> tuple[int, list[str], str]:
    exe = winget_exe()
    if not exe:
        return -1, [], "none"
    from . import conpty
    out: list[str] = []

    def take(t: str):
        out.append(t)
        if on_text:
            on_text(t)

    args = _args(args)
    rc = conpty.run(subprocess.list2cmdline([exe] + args), take, timeout, cols=CAP_COLS, rows=CAP_ROWS)
    if rc is not None:
        return rc, vt_screen("".join(out)), "conpty"
    rc, raw = _run_once(args, timeout)
    return rc, lines(raw), "pipe"


# ---------------- reading the tables winget prints ----------------
def _looks_like_version(s: str) -> bool:
    return bool(re.search(r"\d", s))


def _ncols(header: str) -> int:
    return len([t for t in header.split() if not re.fullmatch(r"[-\\|/]", t)])


def _row(line: str, ncols: int) -> dict | None:
    """One table row, read from the right: the last columns never contain spaces, the name may.
    Works whatever the language of the headers and however wide the name column is."""
    toks = line.split()
    source = toks.pop() if ncols >= 5 and toks else SOURCE
    if len(toks) < 4:
        return None
    avail = toks.pop()
    ver = toks.pop()
    if toks and toks[-1] in ("<", ">"):
        ver = toks.pop() + " " + ver
    pid = toks.pop() if toks else ""
    name = " ".join(toks).strip()
    if not name or not pid or not _looks_like_version(avail):
        return None
    if "." not in pid and not pid.endswith(_ELLIPSIS):
        return None
    return {"name": name, "id": pid, "version": ver, "available": avail, "source": source}


def _tables(ls: list[str]):
    """(header, rows) of every table: a header line, a line of dashes, then rows up to an empty line."""
    i = 0
    while i < len(ls):
        if _SEP.match(ls[i]) and i > 0 and ls[i - 1].strip():
            j = i + 1
            body = []
            while j < len(ls) and ls[j].strip() and not _SEP.match(ls[j]):
                body.append(ls[j])
                j += 1
            yield ls[i - 1], body
            i = j
        else:
            i += 1


def parse_upgrades(raw: bytes | str | list) -> list[dict]:
    """Rows of every table in the output (the second table lists packages that need explicit targeting)."""
    ls = raw if isinstance(raw, list) else lines(raw)
    rows, seen = [], set()
    for header, body in _tables(ls):
        ncols = _ncols(header)
        for ln in body:
            r = _row(ln, ncols)
            if r and r["id"] not in seen and r["source"].lower() in (SOURCE, "winget"):
                seen.add(r["id"])
                rows.append(r)
    return rows


def parse_search(raw: bytes | str | list) -> list[dict]:
    """`winget search`: Name, Id, Version, then an optional Match ("Tag: video") and Source column.
    The columns after Version are cut off by their position in the header, the rest is read from the right."""
    ls = raw if isinstance(raw, list) else lines(raw)
    out, seen = [], set()
    for header, body in _tables(ls):
        starts = [m.start() for m in re.finditer(r"\S+", header) if not re.fullmatch(r"[-\\|/]", m.group(0))]
        if len(starts) < 3:
            continue
        cut = starts[3] if len(starts) > 3 else None
        for ln in body:
            core = ln[:cut] if cut else ln
            toks = core.split()
            if len(toks) < 3:
                continue
            ver, pid = toks[-1], toks[-2]
            name = " ".join(toks[:-2])
            if "." not in pid or pid.endswith(_ELLIPSIS) or pid in seen or not name:
                continue
            seen.add(pid)
            out.append({"name": name.rstrip("\u2026. "), "id": pid, "version": ver})
    return out


def _label_value(ln: str) -> str:
    return ln.split(":", 1)[1].strip() if ":" in ln else ""


def parse_show(raw: bytes | str | list) -> dict:
    """Name, version, publisher, links and release notes from `winget show`. Labels are translated, so only the
    shape is used: "Found <name> [<id>]", then Version and Publisher (always the first two fields of a manifest),
    the first link is the publisher's site, the last one the installer."""
    ls = [ln for ln in (raw if isinstance(raw, list) else lines(raw)) if ln.strip()]
    out = {"name": "", "version": "", "publisher": "", "homepage": "", "installer": "", "sha256": False, "notes": "", "notesUrl": "", "urls": []}
    start = -1
    for k, ln in enumerate(ls[:6]):
        m = re.search(r"\s(.+?)\s+\[([^\]\s]+)\]\s*$", ln)
        if m:
            out["name"] = m.group(1).strip()
            start = k
            break
    top = [ln for ln in ls[start + 1:] if not ln.startswith(" ")] if start >= 0 else []
    if len(top) >= 2:
        v = _label_value(top[0])
        if _looks_like_version(v):
            out["version"] = v
            out["publisher"] = _label_value(top[1])
    urls = [u.rstrip(").,;") for ln in ls for u in re.findall(r"https?://\S+", ln)]
    out["urls"] = urls
    if urls:
        out["homepage"], out["installer"] = urls[0], urls[-1]
    out["sha256"] = any(re.search(r"\b[0-9a-fA-F]{64}\b", ln) for ln in ls)
    notes_url = next((u for u in urls[:-1] if re.search(r"release|changelog|change-log|whatsnew|whats-new|news|history|/blog/", u, re.I)), "")
    out["notesUrl"] = notes_url
    # release notes: the indented block of sentences (Tags are single words, Documentation and Installer are "key: value")
    k = start + 1 if start >= 0 else 0
    while k < len(ls):
        ln = ls[k]
        if not ln.startswith(" ") and ln.rstrip().endswith(":"):
            block = []
            j = k + 1
            while j < len(ls) and ls[j].startswith(" "):
                block.append(ls[j].strip())
                j += 1
            sentences = [b for b in block if len(b.split()) >= 3 and not re.match(r"^[^:]{1,40}:\s*(https?://\S+|\S+)$", b)]
            if block and len(sentences) >= max(1, len(block) // 2):
                text = "\n".join(re.sub(r"^[-*\u2022]\s*", "", b) for b in block)
                out["notes"] = text[:1200]
                break
            k = j
        else:
            k += 1
    return out


def host(url: str) -> str:
    try:
        h = urlparse(url).hostname or ""
    except Exception:
        return ""
    h = h[4:] if h.startswith("www.") else h
    if h == "github.com":       # show whose GitHub it is: github.com/notepad-plus-plus
        parts = [p for p in urlparse(url).path.split("/") if p]
        if parts:
            return f"github.com/{parts[0]}"
    return h


def owners(urls) -> set[str]:
    """GitHub accounts that the links point to."""
    out = set()
    for u in urls or []:
        m = re.match(r"https?://(?:www\.)?github\.com/([A-Za-z0-9-]+)", u or "")
        if m and m.group(1).lower() not in ("orgs", "user-attachments", "sponsors", "apps", "settings", "marketplace"):
            out.add(m.group(1).lower())
    return out


# ---------------- is the catalogue entry really the installed program? ----------------
# winget links an installed program to a catalogue entry by its installer code or by its name. A fork that kept the
# original installer code (FlClash X, a fork of FlClash) is then offered the original program as an "update".
_NOISE = {"x64", "x86", "x32", "amd64", "arm64", "win64", "win32", "bit", "64bit", "32bit", "windows", "win", "for", "the",
          "version", "setup", "installer", "edition", "app", "stable", "release", "user", "machine", "only", "and"}
_EDITION = {"x", "pro", "plus", "lite", "next", "ce", "beta", "preview", "nightly", "dev", "canary", "insider", "insiders", "mod",
            "fork", "community", "enterprise", "portable", "classic", "legacy", "ultimate", "premium", "alpha", "reborn", "unofficial"}


def _tokens(name: str) -> list[str]:
    s = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", (name or "").lower())
    truncated = s.rstrip().endswith(_ELLIPSIS)
    toks = re.findall(r"[a-z\u0430-\u044f\u04510-9][a-z\u0430-\u044f\u04510-9+#.]*", s.replace("\u2026", " "))
    if truncated and toks:
        toks = toks[:-1]                 # the last word was cut
    return [t.rstrip(".") for t in toks if not re.search(r"\d", t) and t.rstrip(".") not in _NOISE]


def name_relation(installed: str, catalogue: str) -> str:
    """"same", "edition" (a different edition or a fork: FlClash X and FlClash), "partial", "different" or "" (unknown)."""
    a, b = _tokens(installed), _tokens(catalogue)
    if not a or not b:
        return ""
    sa, sb = set(a), set(b)
    ja, jb = "".join(a), "".join(b)
    if ja == jb or sa == sb:
        return "same"
    for x, y in ((ja, jb), (jb, ja)):
        if x.startswith(y) and x[len(y):] in _EDITION:
            return "edition"
    if (sa ^ sb) & _EDITION:
        return "edition"
    return "partial" if sa & sb else "different"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9\u0430-\u044f\u0451]+", "", (s or "").lower())


def match_installed(rows: list[dict], programs: list[dict]) -> None:
    """Find the Windows "Installed apps" entry of every row (by its name, which winget takes from there)."""
    table = [(_norm(p.get("name", "")), p) for p in programs or []]
    for r in rows:
        raw = r.get("name", "")
        cut = raw.rstrip().endswith(_ELLIPSIS)
        n = _norm(raw.rstrip("\u2026. "))
        hits = [p for k, p in table if k == n] if not cut else []
        if not hits and n:
            hits = [p for k, p in table if k.startswith(n) and len(n) > 3]
        if not hits and n and not cut:
            hits = [p for k, p in table if n.startswith(k) and len(k) > 3]
        if hits:
            exact = [p for p in hits if p.get("version") and p.get("version") == r.get("version")]
            r["_arp"] = (exact or hits)[0]


def check_identity(r: dict) -> None:
    """Mark a row as suspect when the catalogue entry looks like another program than the one installed."""
    arp = r.get("_arp") or {}
    inst_name = arp.get("name") or r.get("name", "")
    cat_name = r.get("catName") or ""
    rel = name_relation(inst_name, cat_name) if cat_name else ""
    mine = owners(arp.get("urls", []))
    theirs = owners(r.get("urls", []) or [r.get("installer", ""), r.get("homepage", "")])
    why = ""
    if mine and theirs and not (mine & theirs):
        why = "owner"
    elif rel == "edition":
        why = "edition"
    r.update(suspect=bool(why), why=why, installedName=clean_title(inst_name.rstrip("\u2026. ")),
             mineOwner=sorted(mine)[0] if mine else "", theirOwner=sorted(theirs)[0] if theirs else "")
    v = r.get("version", "")
    if (v[:1] in "<>" or v.lower() == "unknown") and arp.get("version"):
        r["current"] = arp["version"]      # winget only knows "older than x": Windows knows the real number
    else:
        r["current"] = v


def clean_title(name: str) -> str:
    """"FlClashX, версия 0.4.2" -> "FlClashX": the version is shown next to the name anyway."""
    t = re.sub(r"[,\s]+(?:version|versi\u00f3n|\u0432\u0435\u0440\u0441\u0438\u044f|\u0432\u0435\u0440\.|v)\s*\d[\w.+-]*.*$", "", name or "", flags=re.I)
    t = re.sub(r"\s+\d+(?:\.\d+){1,3}\s*$", "", t)
    return t.strip(" ,-") or (name or "")


# ---------------- Microsoft Store (MSIX) apps: no Installed apps entry, so their icon and folder come from the package ----------------
_STORE_PS = r"""
Get-AppxPackage | Where-Object { -not $_.IsFramework -and $_.InstallLocation } | ForEach-Object {
  $logo = ''; $sq = ''
  try {
    [xml]$x = Get-Content -LiteralPath (Join-Path $_.InstallLocation 'AppxManifest.xml') -Raw
    $logo = [string]$x.Package.Properties.Logo
    $app = @($x.Package.Applications.ChildNodes | Where-Object { $_.LocalName -eq 'Application' })[0]
    if ($app) { $ve = @($app.ChildNodes | Where-Object { $_.LocalName -eq 'VisualElements' })[0]; if ($ve) { $sq = [string]$ve.Square44x44Logo } }
  } catch {}
  [pscustomobject]@{ n = $_.Name; d = $_.InstallLocation; l = $logo; s = $sq }
}
"""


def _asset(folder: str, rel: str) -> str:
    """The real file behind a manifest image name: Assets\\Logo.png is shipped as Logo.scale-200.png, Logo.targetsize-48.png..."""
    if not rel or not folder:
        return ""
    base = os.path.join(folder, rel.replace("/", "\\"))
    if os.path.isfile(base):
        return base
    stem, ext = os.path.splitext(base)
    cands = [c for c in glob.glob(glob.escape(stem) + ".*" + ext) if "contrast-" not in os.path.basename(c).lower()]

    def score(c: str):
        n = os.path.basename(c).lower()
        m = re.search(r"targetsize-(\d+)", n)
        if m:
            return (0 if "altform-unplated" in n else 1 if "unplated" not in n else 2, abs(int(m.group(1)) - 64))   # sharp up to 200 %
        m = re.search(r"scale-(\d+)", n)
        return (3, abs(int(m.group(1)) - 200)) if m else (4, 0)

    return min(cands, key=score) if cands else ""


def store_apps() -> list[dict]:
    """[{name, folder, icon}] for the user's Store and other MSIX apps."""
    if not P.IS_WINDOWS:
        return [{"name": "Spotify Music", "folder": "", "icon": ""}]      # demo: Spotify from Microsoft Store
    data = P.ps_json(_STORE_PS, 90) or []
    if isinstance(data, dict):
        data = [data]
    out = []
    for d in data:
        folder = d.get("d") or ""
        icon = _asset(folder, d.get("s") or "") or _asset(folder, d.get("l") or "")
        out.append({"name": d.get("n") or "", "folder": folder, "icon": icon})
    return out


def match_store(rows: list[dict], apps: list[dict] | None = None) -> None:
    """Store apps (App Installer, Windows Terminal, Teams, ChatGPT...) by their package name."""
    todo = [r for r in rows if not r.get("_arp")]
    if not todo:
        return
    apps = store_apps() if apps is None else apps
    for r in todo:
        keys = {_norm("".join(t for t in _tokens(r.get("title") or r["name"]) if t != "microsoft")), _norm(r["id"].split(".")[-1])}
        keys = {k for k in keys if len(k) >= 4}
        hits = [a for a in apps if a["name"] and any(k in _norm(a["name"]) for k in keys)]
        if hits:
            r["_store"] = min(hits, key=lambda a: len(a["name"]))


_MSIX = (".msix", ".msixbundle", ".appx", ".appxbundle")


def is_msix(url: str) -> bool:
    return urlparse(url or "").path.lower().endswith(_MSIX)


def mark_store_only(rows: list[dict]) -> None:
    """A program installed from Microsoft Store that the catalogue would update with the vendor's website installer:
    that installer puts a second, separate copy next to the Store one (Spotify, Telegram...). Such rows are updated by
    the Store, not by Sweep. An MSIX installer is the same package as the Store one and stays allowed."""
    for r in rows:
        r["storeOnly"] = bool(r.get("_store")) and not is_msix(r.get("installer", ""))


# words a Store listing adds to a program's own name: "Spotify Music", "Telegram Desktop", "Zoom Workplace"
_STORE_EXTRA = {"music", "desktop", "app", "for", "windows", "pc", "workplace", "client"}


def _words(name: str) -> list[str]:
    """Words of a name with "+" kept, so Notepad++ is not Notepad; the word "microsoft" is dropped."""
    return [w for w in re.findall(r"[a-z0-9+а-яё]+", (name or "").lower()) if w != "microsoft"]


def store_name_match(name: str, apps: list[dict]) -> str:
    """Name of the Store app that is this program (catalogue name "Spotify" and Store app "Spotify Music"), or "".
    The Store name must start with every word of the program's name and add only listing words, so Notepad++ does
    not match Windows Notepad and Opera does not match Opera GX: a wrong hit would hide a program from installing."""
    want = _words(name)
    if len("".join(want)) < 4:
        return ""
    hits = []
    for a in apps:
        got = _words(a.get("name", ""))
        if got[:len(want)] == want and all(w in _STORE_EXTRA for w in got[len(want):]):
            hits.append(a["name"])
    return min(hits, key=len) if hits else ""


def mark_running(rows: list[dict]) -> None:
    """Which programs are open right now: an open program often cannot be replaced by its installer."""
    if not P.IS_WINDOWS:
        for r in rows:
            r["running"] = r["id"] == "Telegram.TelegramDesktop"
        return
    try:
        import psutil
        exes = [(p.info.get("exe") or "").lower() for p in psutil.process_iter(["exe"])]
    except Exception:  # noqa: BLE001
        return
    for r in rows:
        r["running"] = is_running(r, exes)


def is_running(r: dict, exes: list[str] | None = None) -> bool:
    if not P.IS_WINDOWS:
        return bool(r.get("running"))
    loc = ((r.get("_arp") or {}).get("location") or (r.get("_store") or {}).get("folder") or "").lower().rstrip("\\")
    if len(loc) < 4:
        return False
    if exes is None:
        import psutil
        exes = [(p.info.get("exe") or "").lower() for p in psutil.process_iter(["exe"])]
    return any(e.startswith(loc + "\\") for e in exes)


# ---------------- public API: scan ----------------
def _installed_ids() -> dict[str, str]:
    """Full package ids (and versions) of everything winget recognises as installed."""
    path = os.path.join(tempfile.gettempdir(), f"sweep-winget-{os.getpid()}.json")
    _run(["export", "-o", path, "--source", SOURCE, "--include-versions"] + COMMON, 300)
    try:
        data = json.loads(open(path, encoding="utf-8").read())
    except Exception:
        return {}
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    ids = {}
    for src in data.get("Sources", []):
        for p in src.get("Packages", []):
            if p.get("PackageIdentifier"):
                ids[p["PackageIdentifier"]] = p.get("Version", "")
    return ids


def installed_ids() -> dict[str, str]:
    if not P.IS_WINDOWS:
        time.sleep(0.8)
        return {i: "1.0" for i in _DEMO_INSTALLED}
    return _installed_ids()


def _repair_ids(rows: list[dict]) -> list[dict]:
    short = [r for r in rows if r["id"].endswith(_ELLIPSIS)]
    if not short:
        return rows
    full = _installed_ids()
    for r in short:
        prefix = r["id"].rstrip(".\u2026")
        hits = [i for i in full if i.startswith(prefix)]
        if len(hits) == 1:
            r["id"] = hits[0]
        else:
            P.log(f"updates: cannot resolve shortened id {r['id']} ({len(hits)} matches)")
            r["id"] = ""
    return [r for r in rows if r["id"]]


def _detail(r: dict, d: dict) -> None:
    r.update(installer=d["installer"], homepage=d["homepage"], host=host(d["installer"]), sha256=d["sha256"], urls=d.get("urls", []),
             notes=d.get("notes", ""), notesUrl=d.get("notesUrl", ""), publisher=d.get("publisher", ""))
    if d["name"]:
        r["title"] = d["name"]     # "7-Zip" rather than the installed entry "7-Zip 26.04 (x64)"
        r["catName"] = d["name"]


def scan(details: bool = True, progress=None, programs: list[dict] | None = None) -> dict:
    """{"winget": bool, "items": [...]}: installed programs that have a newer version in the winget catalogue.
    progress(stage, done, total) reports "list" (winget compares the PC with the catalogue) and "details"."""
    def report(stage, done=0, total=0):
        if progress:
            try:
                progress(stage, done, total)
            except Exception:  # noqa: BLE001
                pass

    t0 = time.time()
    report("list")
    if not P.IS_WINDOWS:
        time.sleep(2.0)
        rows = [{k: v for k, v in d.items() if k not in ("installer", "homepage", "notes", "notesUrl", "publisher")} | {"source": SOURCE}
                for d in _DEMO]
        how = "demo"
    else:
        if not winget_exe():
            P.log("updates: winget not found")
            return {"winget": False, "items": [], "listSecs": 0}
        rc, ls, how = _capture(["upgrade", "--source", SOURCE] + COMMON, 300)
        rows = _repair_ids(parse_upgrades(ls))
        P.log(f"updates: winget upgrade rc={rc & 0xFFFFFFFF:#x} via {how}, {len(rows)} updates, {time.time() - t0:.0f} s")
        why = list_failed(rc, ls, rows)
        if why:
            P.log(f"updates: the list failed: {why}  {' | '.join(x.strip() for x in ls if x.strip())[-600:]}")
            return {"winget": True, "items": [], "listSecs": 0, "error": f"{rc & 0xFFFFFFFF:#x}" if rc not in (-1, -2) else str(rc),
                    "errorText": why, "old": bool(winget_version()) and winget_version() < OLD_WINGET, "source": source_broken(rc)}
    list_secs = time.time() - t0
    for r in rows:
        r.update(title=r["name"].rstrip("\u2026. "), installer="", homepage="", host="", sha256=False, urls=[], notes="", notesUrl="",
                 publisher="", catName="")
    if rows and details:
        n = len(rows)
        report("details", 0, n)
        done = 0
        with ThreadPoolExecutor(max_workers=4) as ex:
            for r, d in zip(rows, ex.map(lambda r: show(r["id"]), rows), strict=True):
                _detail(r, d)
                done += 1
                report("details", done, n)
        for r in rows:                         # parallel calls sometimes trip over each other: one quiet retry
            if not r["installer"]:
                _detail(r, show(r["id"]))
    report("match", len(rows), len(rows))
    match_installed(rows, programs if programs is not None else _programs())
    for r in rows:
        check_identity(r)
    try:
        match_store(rows)
        mark_store_only(rows)
        mark_running(rows)
    except Exception as e:  # noqa: BLE001
        P.log(f"updates: store apps or running programs not read: {e}")
    return {"winget": True, "items": rows, "listSecs": round(list_secs, 1)}


_SPINNER = re.compile(r"^[\s\-\\|/█▒▓░■□.%0-9KMGBkmgb/]*$")


def list_failed(rc: int, screen: list[str], rows: list[dict]) -> str:
    """Why `winget upgrade` gave no usable list, or "" when an empty list really means "nothing to update".
    Nothing to update is exit code 0 or NO_APPLICATIONS_FOUND / UPDATE_NOT_APPLICABLE with no table; anything else
    (help text after an unknown flag, a source that could not be opened, a table the parser could not read) is a failure."""
    if rows:
        return ""
    code = rc & 0xFFFFFFFF
    if rc == -2:
        return "timeout"
    table = any(_SEP.match(x) for x in screen)
    if code in (0, NOT_FOUND, NOT_APPLICABLE) and not table:
        return ""
    said = [x.strip() for x in screen if x.strip() and not _SPINNER.match(x.strip())]
    msg = next((x for x in said if re.search(r"error|failed|not recognized|ошибк|не удалось|не распознан|0x8a15", x, re.I)), said[0] if said else "")
    return (msg[:200] or "no answer") if not table else "unreadable table"


def _programs() -> list[dict]:
    from . import uninstall
    try:
        return uninstall.list_programs()
    except Exception as e:  # noqa: BLE001
        P.log(f"updates: installed programs not read: {e}")
        return []


def show(pid: str) -> dict:
    empty = {"name": "", "version": "", "publisher": "", "homepage": "", "installer": "", "sha256": False, "notes": "", "notesUrl": "", "urls": []}
    if not P.IS_WINDOWS:
        time.sleep(0.3)
        d = next((dict(d) for d in _DEMO if d["id"] == pid), None)
        if not d:
            return empty
        title = {"chen08209.FlClash": "FlClash", "Microsoft.PowerShell": "PowerShell", "Python.Launcher": "Python Launcher"}.get(pid)
        title = title or re.sub(r"\s[\d.]+\s.*$|\s\(.*\)$", "", d["name"])
        return dict(empty, name=title, version=d["available"], publisher=d["publisher"], homepage=d["homepage"], installer=d["installer"],
                    sha256=True, notes=d.get("notes", ""), notesUrl=d.get("notesUrl", ""), urls=[d["homepage"], d["installer"]])
    rc, ls, _ = _capture(["show", "--id", pid, "--exact", "--source", SOURCE] + COMMON, 120)
    if rc != 0:
        return empty
    d = parse_show(ls)
    return d if d["name"] or d["installer"] else empty


def search(query: str, count: int = 40) -> list[dict]:
    """Any program in the winget catalogue: [{name, id, version}]."""
    q = re.sub(r"\s+", " ", (query or "").strip())[:60]
    if not q:
        return []
    if not P.IS_WINDOWS:
        time.sleep(0.7)
        ql = q.lower()
        return [{"name": n, "id": i, "version": v} for n, i, v in _DEMO_SEARCH if ql in n.lower() or ql in i.lower()] or \
               [{"name": n, "id": i, "version": v} for n, i, v in _DEMO_SEARCH[:3]]
    rc, ls, how = _capture(["search", q, "--source", SOURCE, "--count", str(count)] + COMMON, 120)
    res = parse_search(ls)
    P.log(f"install: search '{q}' rc={rc & 0xFFFFFFFF:#x} via {how}: {len(res)} found")
    return res


# ---------------- live progress of one update ----------------
_UNITS = {"b": 1, "kb": 1024, "mb": 1024 ** 2, "gb": 1024 ** 3, "tb": 1024 ** 4,
          "\u0431": 1, "\u043a\u0431": 1024, "\u043c\u0431": 1024 ** 2, "\u0433\u0431": 1024 ** 3, "\u0442\u0431": 1024 ** 4}
_SIZE = re.compile(r"(\d+(?:[.,]\d+)?)\s*([KMGT]?i?B|[\u041a\u041c\u0413\u0422]?\u0411)\s*/\s*(\d+(?:[.,]\d+)?)\s*([KMGT]?i?B|[\u041a\u041c\u0413\u0422]?\u0411)", re.I)
_PCT = re.compile(r"(\d{1,3})\s*%")
_BAR = ("\u2588", "\u2592", "\u2593")


def _bytes(num: str, unit: str) -> float:
    return float(num.replace(",", ".")) * _UNITS.get(unit.lower().replace("i", ""), 1)


_OSC = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
_OSC_PROGRESS = re.compile(r"\x1b\]9;4;(\d);?(\d*)")         # taskbar progress: ESC ] 9 ; 4 ; state ; percent
_FRAME = re.compile(r"\r\n|\r|\n|\x1b\[[0-9;]*[GKJHf]")      # new line, or the cursor jumping back to redraw


def _escape_complete(s: str) -> bool:
    if len(s) < 2:
        return False
    if s[1] == "]":
        return "\x07" in s or "\x1b\\" in s[1:]
    if s[1] == "[":
        return bool(re.match(r"\x1b\[[0-9;?]*[ -/]*[@-~]", s))
    return True


class Progress:
    """Turns winget's console output into phases: "prepare", "download" (bytes so far and total) and "install".
    winget redraws its progress bar in place, so the text is cut into frames at line breaks and cursor moves."""

    def __init__(self, callback=None):
        self.callback = callback
        self.phase = "prepare"
        self.got = 0.0
        self.total = 0.0
        self.sized = False          # winget printed "x MB / y MB" at least once
        self.log: list[tuple] = []  # (seconds since start, phase, bytes) for diagnostics
        self._t0 = time.time()
        self._buf = ""

    def _emit(self):
        self.log.append((round(time.time() - self._t0, 2), self.phase, int(self.got)))
        if self.callback:
            self.callback(self.phase, self.got, self.total)

    def feed_text(self, text: str) -> None:
        """Raw output as it arrives, in chunks of any size: complete frames are read in order, the rest waits for more."""
        buf = self._buf + text
        hold = len(buf)
        osc = buf.rfind("\x1b]")
        if osc >= 0 and not _escape_complete(buf[osc:]):
            hold = osc                                   # a taskbar message cut in half by the chunk border
        else:
            esc = buf.rfind("\x1b")
            if esc >= 0 and not _escape_complete(buf[esc:]):
                hold = esc                               # any other escape sequence cut in half
        work, rest = buf[:hold], buf[hold:]
        pending = ""
        for piece in re.split(r"(\x1b\][^\x07\x1b]*(?:\x07|\x1b\\))", work):
            if piece.startswith("\x1b]"):
                for frame in _FRAME.split(pending):    # a taskbar update closes the frame drawn before it
                    self.feed(frame)
                pending = ""
                m = _OSC_PROGRESS.match(piece)
                if m:
                    self._taskbar(int(m[1]), int(m[2] or 0))
            else:
                pending += piece
        frames = _FRAME.split(pending)
        self._buf = frames.pop() + rest                  # the frame being drawn right now is finished by the next one
        for frame in frames:
            self.feed(frame)

    def _taskbar(self, state: int, value: int) -> None:
        if self.phase != "download":
            return
        if state in (1, 4) and not self.sized and 0 <= value <= 100:
            if value != self.got or self.total != 100.0:
                self.got, self.total = float(value), 100.0
                self._emit()
        elif state == 0 and (self.got > 0 or self.sized):
            self.phase = "install"
            self._emit()

    def feed(self, segment: str) -> None:
        """One frame of text."""
        seg = re.sub(r"\x1b[^\[\]]?", "", _ANSI.sub("", _OSC.sub("", segment))).strip()
        if not seg:
            return
        if self.phase == "prepare":
            if re.search(r"https?://\S+", seg):          # "Downloading https://vendor/installer.exe"
                self.phase = "download"
                self._emit()
            return
        if self.phase != "download":
            return
        sizes = list(_SIZE.finditer(seg))
        if sizes:
            m = sizes[-1]
            got, total = _bytes(m[1], m[2]), _bytes(m[3], m[4])
            self.sized = True
            if (got, total) != (self.got, self.total):
                self.got, self.total = got, total
                if total and got >= total:
                    self.phase = "install"
                self._emit()
            return
        m = _PCT.search(seg)
        if m and any(ch in seg for ch in _BAR):
            if not self.sized:
                self.got, self.total = float(m[1]), 100.0
                if self.got >= 100:
                    self.phase = "install"
                self._emit()
            return
        if (self.sized or self.got > 0) and not any(ch in seg for ch in _BAR) and not re.fullmatch(r"[-\\|/]", seg):
            self.phase = "install"                       # "Successfully verified installer hash", "Starting package install"
            self._emit()


def _stream(args: list[str], timeout: int, prog: Progress) -> tuple[int, bytes, str]:
    """Run winget and read its output as it comes. Inside a pseudo console winget draws its progress live;
    through a plain pipe it holds the bar back until the end, so the pipe is only the fallback."""
    rc, raw, how = _stream_once(args, timeout, prog)
    if source_broken(rc) and repair_source():
        rc, raw, how = _stream_once(args, timeout, prog)
    return rc, raw, how


def _stream_once(args: list[str], timeout: int, prog: Progress) -> tuple[int, bytes, str]:
    exe = winget_exe()
    if not exe:
        return -1, b"", "none"
    out: list[str] = []

    def take(text: str) -> None:
        out.append(text)
        prog.feed_text(text)

    from . import conpty
    args = _args(args)
    rc = conpty.run(subprocess.list2cmdline([exe] + args), take, timeout)
    if rc is not None:
        prog.feed_text("\n")
        return rc, "".join(out).encode("utf-8"), "conpty"
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    try:
        proc = subprocess.Popen([exe] + args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                startupinfo=si, creationflags=0x08000000)
    except Exception as e:  # noqa: BLE001
        P.log(f"winget {args[:3]}: {e}")
        return -1, b"", "pipe"
    import codecs
    dec = codecs.getincrementaldecoder("utf-8")("replace")

    def reader():
        while True:
            data = os.read(proc.stdout.fileno(), 4096)
            if not data:
                break
            take(dec.decode(data))

    th = threading.Thread(target=reader, daemon=True)
    th.start()
    try:
        proc.wait(timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        P.log(f"winget {args[:3]}: timed out after {timeout} s")
        th.join(5)
        return -2, "".join(out).encode("utf-8"), "pipe"
    th.join(10)
    prog.feed_text("\n")
    return proc.returncode, "".join(out).encode("utf-8"), "pipe"


def _tail(raw: bytes) -> str:
    return " | ".join(ln.strip() for ln in lines(raw) if ln.strip())[-300:]


def _demo_run(prog: Progress, size_mb: float = 6.5) -> None:
    prog.phase = "download"
    total = size_mb * 2 ** 20
    for i in range(1, 13):
        time.sleep(0.16)
        prog.got, prog.total = total * i / 12, total
        prog._emit()
    prog.phase = "install"
    prog._emit()
    time.sleep(1.2)


# Download errors winget passes on from Windows' HTTP stack. 0x80072xxx: the connection itself (closed, reset, timed out,
# name not found, TLS); 0x8019xxxx: the server answered with an HTTP error (0x801901F8 is 504); 0x80D02xxx: Delivery
# Optimization made no progress. All of these are about the vendor's server or the way to it, not the installer.
_NET_CODES = {0x80072EE2, 0x80072EE7, 0x80072EFD, 0x80072EFE, 0x80072EFF, 0x80072F78, 0x80072F06, 0x80072F7D, 0x80072F8F,
              0x80072F05, 0x80072F0D, 0x80D02002, 0x80D0200B, 0x80D02011, 0x80D02017}
RETRY_REASONS = ("net", "server", "download")     # worth one more try after a short pause


def reason_for(code: int) -> str:
    if code in REASONS:
        return REASONS[code]
    if code in _NET_CODES or (code & 0xFFFFF000) == 0x80072000:
        return "net"
    if (code & 0xFFFF0000) == 0x80190000:
        return "gone" if (code & 0xFFFF) in (404, 410) else "server"
    return "code"


def _run_pkg(args: list[str], timeout: int, prog: Progress) -> tuple[int, bytes, str]:
    """winget install/upgrade. Some installers (Spotify, for one) refuse to run as administrator, and Sweep always
    runs as one: winget says INSTALLER_PROHIBITS_ELEVATION, and the same command is run again as the signed-in user."""
    rc, raw, how = _stream(args, timeout, prog)
    if (rc & 0xFFFFFFFF) == PROHIBITS_ELEVATION and P.is_admin():
        P.log(f"winget {args[:3]}: the installer refuses administrator rights, running it as the signed-in user")
        prog.phase, prog.got, prog.total = "install", 0.0, 0.0
        prog._emit()
        rc2, raw2 = as_user(args, timeout)
        if rc2 != -1:
            return rc2, raw2, "user"
    return rc, raw, how


_AS_USER_PS = r'''
$ErrorActionPreference = 'Stop'
$u = (Get-CimInstance Win32_ComputerSystem).UserName
if (-not $u) {
  $o = Get-CimInstance Win32_Process -Filter "Name='explorer.exe'" | Select-Object -First 1 | Invoke-CimMethod -MethodName GetOwner
  if ($o -and $o.User) { $u = "$($o.Domain)\$($o.User)" }
}
if (-not $u) { throw 'nobody is signed in' }
& icacls.exe $env:SWEEP_DIR /grant "$($u):(OI)(CI)M" | Out-Null
$a = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument ('//B //Nologo "' + $env:SWEEP_DIR + '\run.vbs"')
$p = New-ScheduledTaskPrincipal -UserId $u -LogonType Interactive -RunLevel Limited
$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName $env:SWEEP_TASK -TaskPath '\Sweep\' -Action $a -Principal $p -Settings $s -Force | Out-Null
Start-ScheduledTask -TaskName $env:SWEEP_TASK -TaskPath '\Sweep\'
$u
'''


def as_user(args: list[str], timeout: int) -> tuple[int, bytes]:
    """Run `winget <args>` hidden as the signed-in user without administrator rights (a one-off scheduled task with
    limited rights in that user's session). Returns (exit code, output); (-1, b"") when it could not be started."""
    if not P.IS_WINDOWS:
        return -1, b""
    import secrets
    tag = "AsUser-" + secrets.token_hex(4)
    work = os.path.join(str(P.ROOT), "asuser", tag)
    os.makedirs(work, exist_ok=True)
    out, rcf = os.path.join(work, "out.txt"), os.path.join(work, "rc.txt")
    cmd = subprocess.list2cmdline(["winget"] + _args(args)) + f' > "{out}" 2>&1'
    vbs = ('Set sh = CreateObject("WScript.Shell")\r\n'
           f'rc = sh.Run("cmd /c " & Chr(34) & {_vbs_str(cmd)} & Chr(34), 0, True)\r\n'
           'Set f = CreateObject("Scripting.FileSystemObject").CreateTextFile(' + _vbs_str(rcf) + ', True)\r\n'
           'f.WriteLine rc\r\nf.Close\r\n')
    with open(os.path.join(work, "run.vbs"), "w", encoding="utf-16", newline="") as f:
        f.write(vbs)
    env = dict(os.environ, SWEEP_DIR=work, SWEEP_TASK=tag)
    try:
        r = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", _AS_USER_PS],
                           capture_output=True, timeout=120, env={k: v for k, v in env.items() if k.upper() != "PSMODULEPATH"},
                           creationflags=0x08000000)
        if r.returncode != 0:
            P.log(f"as user: task not started: {r.stderr.decode('utf-8', 'replace').strip()[-300:]}")
            return -1, b""
        P.log(f"as user: {r.stdout.decode('utf-8', 'replace').strip()} runs winget {args[:3]}")
        started = time.time() + 45              # cmd creates out.txt at once; nothing after 45 s: the task never ran
        while time.time() < started and not os.path.exists(out):
            time.sleep(0.5)
        if not os.path.exists(out):
            P.log("as user: the task did not start (is the user signed in?)")
            return -1, b""
        end = time.time() + timeout
        while time.time() < end and not os.path.exists(rcf):
            time.sleep(1.0)
        time.sleep(0.5)
        try:
            rc = int(open(rcf, encoding="utf-8", errors="replace").read().strip() or "-1")
        except (OSError, ValueError):
            P.log("as user: winget did not finish in time")
            return -2, b""
        try:
            raw = open(out, "rb").read()
        except OSError:
            raw = b""
        return rc, raw
    finally:
        subprocess.run(["schtasks.exe", "/Delete", "/TN", "\\Sweep\\" + tag, "/F"], capture_output=True, creationflags=0x08000000)
        shutil.rmtree(work, ignore_errors=True)


def _vbs_str(s: str) -> str:
    """A VBScript string literal."""
    return '"' + s.replace('"', '""') + '"'


def _verdict(rc: int) -> tuple[int, str, bool]:
    code = rc & 0xFFFFFFFF
    reason = "" if rc == 0 else "timeout" if rc == -2 else reason_for(code)
    return code, reason, rc == 0 or reason in SUCCESS_REASONS


def upgrade(pid: str, timeout: int = 1800, progress=None, before: str = "", over=lambda: True, target: str = "") -> dict:
    """Download the new version from the vendor, check its SHA-256 and install it silently.
    When winget does not see the program installed (it listed it a minute ago, but cannot pick it now), the new
    version is installed over the old one, which is what its installer does on an update anyway. Afterwards the
    installed version is read again, so "updated" is never claimed for a version that did not change.
    over() says whether the program is still on the PC (Windows' own list), so a program removed meanwhile is never
    installed again. When winget answers "no applicable update" although the catalogue has `target`, the same
    route is taken unless the PC already has `target`. progress(phase, got, total) is called from this thread as the download goes on.
    Returns {"ok", "code", "reason", "route", "after"}; ok includes "installed, restart to finish"."""
    if not P.IS_WINDOWS:
        prog = Progress(progress)
        _demo_run(prog)
        d = next((d for d in _DEMO if d["id"] == pid), {})
        stuck = pid == "Telegram.TelegramDesktop"        # demo: an open program its installer could not replace
        return {"ok": True, "code": 0, "reason": "nochange" if stuck else "", "route": "install" if pid == "Microsoft.PowerShell" else "upgrade",
                "after": d.get("version", "") if stuck else d.get("available", ""), "via": "demo", "frames": len(prog.log)}
    t0 = time.time()
    prog = Progress(progress)
    rc, raw, how = _run_pkg(["upgrade", "--id", pid, "--exact", "--source", SOURCE, "--silent", "--accept-package-agreements"] + COMMON, timeout, prog)
    code, reason, ok = _verdict(rc)
    route = "upgrade"
    P.log(f"updates: {pid} upgrade rc={code:#x} ok={ok} {time.time() - t0:.0f} s via {how}, progress frames {len(prog.log)}  {_tail(raw)}")
    retry = code == NOT_FOUND
    if code == NOT_APPLICABLE and target:
        now = installed_version(pid)
        retry = bool(now) and now != target and now[:1] not in "<>"
    if retry and over():
        listed = installed_version(pid, raw=True)
        P.log(f"updates: {pid}: winget list says: {listed[-300:]}")
        prog = Progress(progress)
        rc, raw, how = _run_pkg(["install", "--id", pid, "--exact", "--source", SOURCE, "--silent", "--accept-package-agreements"] + COMMON, timeout, prog)
        code, reason, ok = _verdict(rc)
        route = "install"
        P.log(f"updates: {pid} install over the old version rc={code:#x} ok={ok} via {how}  {_tail(raw)}")
    after = installed_version(pid) if ok and reason != "reboot" else ""
    if ok and not reason and before and after and after == before and before[:1] not in "<>":
        reason = "nochange"
    P.log(f"updates: {pid} done: {before or '?'} -> {after or '?'} route={route} reason={reason or 'ok'}")
    return {"ok": ok, "code": code, "reason": reason, "route": route, "after": after, "via": how, "frames": len(prog.log)}


def install(pid: str, timeout: int = 1800, progress=None) -> dict:
    """Install a program from the catalogue: download from the vendor, SHA-256 check, silent install."""
    prog = Progress(progress)
    if not P.IS_WINDOWS:
        _demo_run(prog, 18.0)
        return {"ok": True, "code": 0, "reason": "", "via": "demo", "frames": len(prog.log)}
    t0 = time.time()
    rc, raw, how = _run_pkg(["install", "--id", pid, "--exact", "--source", SOURCE, "--silent", "--accept-package-agreements"] + COMMON, timeout, prog)
    code, reason, ok = _verdict(rc)
    if reason == "uptodate":
        reason = "already"
    P.log(f"install: {pid} rc={code:#x} ok={ok} {time.time() - t0:.0f} s via {how}, progress frames {len(prog.log)}  {_tail(raw)}")
    return {"ok": ok, "code": code, "reason": reason, "via": how, "frames": len(prog.log)}


def installed_version(pid: str, raw: bool = False) -> str:
    """Version winget sees installed now ("" when it does not see the program). raw=True returns the whole answer."""
    if not P.IS_WINDOWS:
        return ""
    rc, ls, _ = _capture(["list", "--id", pid, "--exact"] + COMMON, 120)
    if raw:
        return " | ".join(ln.strip() for ln in ls if ln.strip())
    for ln in ls:
        toks = ln.split()
        if pid in toks:
            i = toks.index(pid)
            if i + 1 < len(toks):
                v = toks[i + 1]
                if v in ("<", ">") and i + 2 < len(toks):
                    v = v + " " + toks[i + 2]
                return v
    return ""
