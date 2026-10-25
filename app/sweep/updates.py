"""Program updates through winget, the Windows Package Manager that ships with Windows 10 and 11.

Every package in the winget catalogue points to the vendor's own download address (7-zip.org, videolan.org,
github.com/<vendor>) and carries the SHA-256 of the installer; winget refuses to run a file whose hash differs.
Sweep lists what is out of date and updates only what the user ticks."""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from . import platform as P

SOURCE = "winget"
COMMON = ["--accept-source-agreements", "--disable-interactivity"]
_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_SEP = re.compile(r"^\s*-{8,}\s*$")
_ELLIPSIS = ("\u2026", "...")

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
}
SUCCESS_REASONS = ("reboot", "uptodate")

# ---------------- demo data (Linux / screenshots) ----------------
_DEMO = [
    {"id": "7zip.7zip", "name": "7-Zip 23.01 (x64)", "version": "23.01", "available": "24.09",
     "installer": "https://7-zip.org/a/7z2409-x64.exe", "homepage": "https://www.7-zip.org/"},
    {"id": "Notepad++.Notepad++", "name": "Notepad++ (64-bit x64)", "version": "8.6.9", "available": "8.7.8",
     "installer": "https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.7.8/npp.8.7.8.Installer.x64.exe", "homepage": "https://notepad-plus-plus.org/"},
    {"id": "VideoLAN.VLC", "name": "VLC media player", "version": "3.0.20", "available": "3.0.21",
     "installer": "https://get.videolan.org/vlc/3.0.21/win64/vlc-3.0.21-win64.exe", "homepage": "https://www.videolan.org/"},
    {"id": "Telegram.TelegramDesktop", "name": "Telegram Desktop", "version": "5.9.0", "available": "5.12.3",
     "installer": "https://td.telegram.org/tx64/tsetup-x64.5.12.3.exe", "homepage": "https://desktop.telegram.org/"},
    {"id": "Python.Python.3.12", "name": "Python 3.12.4 (64-bit)", "version": "3.12.4", "available": "3.12.10",
     "installer": "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe", "homepage": "https://www.python.org/"},
]


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


def _run(args: list[str], timeout: int) -> tuple[int, bytes]:
    exe = winget_exe()
    if not exe:
        return -1, b""
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    try:
        r = subprocess.run([exe] + args, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout, startupinfo=si, creationflags=0x08000000)
        return r.returncode, r.stdout + (b"\n" + r.stderr if r.stderr else b"")
    except subprocess.TimeoutExpired:
        P.log(f"winget {args[:3]}: timed out after {timeout} s")
        return -2, b""
    except Exception as e:  # noqa: BLE001
        P.log(f"winget {args[:3]}: {e}")
        return -1, b""


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


# ---------------- parsing the table that `winget upgrade` prints ----------------
def _looks_like_version(s: str) -> bool:
    return bool(re.search(r"\d", s))


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


def parse_upgrades(raw: bytes | str) -> list[dict]:
    """Rows of every table in the output (the second table lists packages that need explicit targeting)."""
    ls = lines(raw)
    rows, seen = [], set()
    i = 0
    while i < len(ls):
        if _SEP.match(ls[i]) and i > 0 and ls[i - 1].strip():
            ncols = len(ls[i - 1].split())
            j = i + 1
            while j < len(ls) and ls[j].strip() and not _SEP.match(ls[j]):
                r = _row(ls[j], ncols)
                if r and r["id"] not in seen and r["source"].lower() in (SOURCE, "winget"):
                    seen.add(r["id"])
                    rows.append(r)
                j += 1
            i = j
        else:
            i += 1
    return rows


def parse_show(raw: bytes | str) -> dict:
    """Name, homepage and installer address from `winget show`. Labels are translated, so only the shape is used:
    the first line is "Found <name> [<id>]", the first link is the publisher's site, the last one the installer."""
    ls = [ln for ln in lines(raw) if ln.strip()]
    out = {"name": "", "homepage": "", "installer": "", "sha256": False}
    for ln in ls[:4]:
        m = re.search(r"\s(.+?)\s+\[([^\]\s]+)\]\s*$", ln)
        if m:
            out["name"] = m.group(1).strip()
            break
    urls = [u.rstrip(").,;") for ln in ls for u in re.findall(r"https?://\S+", ln)]
    if urls:
        out["homepage"], out["installer"] = urls[0], urls[-1]
    out["sha256"] = any(re.search(r"\b[0-9a-fA-F]{64}\b", ln) for ln in ls)
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


# ---------------- public API ----------------
def _installed_ids() -> dict[str, str]:
    """Full package ids of everything winget recognises, used to repair ids shortened with an ellipsis."""
    path = os.path.join(tempfile.gettempdir(), f"sweep-winget-{os.getpid()}.json")
    rc, _ = _run(["export", "-o", path, "--source", SOURCE, "--include-versions"] + COMMON, 300)
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


def scan(details: bool = True) -> dict:
    """{"winget": bool, "items": [...]}: installed programs that have a newer version in the winget catalogue."""
    if not P.IS_WINDOWS:
        time.sleep(1.2)
        items = [dict(d) for d in _DEMO]
        for it in items:
            it.update(host=host(it["installer"]), sha256=True, title=re.sub(r"\s[\d.]+\s.*$|\s\(.*\)$", "", it["name"]), source=SOURCE)
        return {"winget": True, "items": items}
    if not winget_exe():
        P.log("updates: winget not found")
        return {"winget": False, "items": []}
    t0 = time.time()
    rc, raw = _run(["upgrade", "--source", SOURCE] + COMMON, 300)
    rows = _repair_ids(parse_upgrades(raw))
    P.log(f"updates: winget upgrade rc={rc & 0xFFFFFFFF:#x}, {len(rows)} updates, {time.time() - t0:.0f} s")
    for r in rows:
        r.update(title=r["name"].rstrip("…. "), installer="", homepage="", host="", sha256=False)
    if rows and details:
        with ThreadPoolExecutor(max_workers=4) as ex:
            for r, d in zip(rows, ex.map(lambda r: show(r["id"]), rows), strict=True):
                r.update(installer=d["installer"], homepage=d["homepage"], host=host(d["installer"]), sha256=d["sha256"])
                if d["name"]:
                    r["title"] = d["name"]     # "7-Zip" rather than the installed entry "7-Zip 26.04 (x64)"
        for r in rows:                         # parallel calls sometimes trip over each other: one quiet retry
            if not r["installer"]:
                d = show(r["id"])
                r.update(installer=d["installer"], homepage=d["homepage"], host=host(d["installer"]), sha256=d["sha256"])
                r["title"] = d["name"] or r["title"]
    return {"winget": True, "items": rows}


def show(pid: str) -> dict:
    if not P.IS_WINDOWS:
        return next((dict(d, sha256=True) for d in _DEMO if d["id"] == pid), {"name": "", "homepage": "", "installer": "", "sha256": False})
    rc, raw = _run(["show", "--id", pid, "--exact", "--source", SOURCE] + COMMON, 120)
    return parse_show(raw) if rc == 0 else {"name": "", "homepage": "", "installer": "", "sha256": False}


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
    import threading
    exe = winget_exe()
    if not exe:
        return -1, b"", "none"
    out: list[str] = []

    def take(text: str) -> None:
        out.append(text)
        prog.feed_text(text)

    from . import conpty
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


def upgrade(pid: str, timeout: int = 1800, progress=None) -> dict:
    """Download the new version from the vendor, check its SHA-256 and install it silently.
    progress(phase, got, total) is called from this thread as the download goes on.
    Returns {"ok": bool, "code": int, "reason": str}; ok includes "installed, restart to finish"."""
    prog = Progress(progress)
    if not P.IS_WINDOWS:
        prog.phase = "download"
        total = 6.5 * 2 ** 20
        for i in range(1, 11):
            time.sleep(0.15)
            prog.got, prog.total = total * i / 10, total
            prog._emit()
        prog.phase = "install"
        prog._emit()
        time.sleep(0.6)
        return {"ok": True, "code": 0, "reason": ""}
    t0 = time.time()
    rc, raw, how = _stream(["upgrade", "--id", pid, "--exact", "--source", SOURCE, "--silent", "--accept-package-agreements"] + COMMON, timeout, prog)
    code = rc & 0xFFFFFFFF
    reason = "" if rc == 0 else REASONS.get(code, "timeout" if rc == -2 else "code")
    ok = rc == 0 or reason in SUCCESS_REASONS
    tail = " | ".join(ln.strip() for ln in lines(raw) if ln.strip())[-300:]
    P.log(f"updates: {pid} rc={code:#x} ok={ok} {time.time() - t0:.0f} s via {how}, progress frames {len(prog.log)}  {tail}")
    return {"ok": ok, "code": code, "reason": reason, "via": how, "frames": len(prog.log)}


def installed_version(pid: str) -> str:
    """Version winget sees installed now (used by the self-test)."""
    if not P.IS_WINDOWS:
        return ""
    rc, raw = _run(["list", "--id", pid, "--exact"] + COMMON, 120)
    for ln in lines(raw):
        toks = ln.split()
        if pid in toks:
            i = toks.index(pid)
            if i + 1 < len(toks):
                return toks[i + 1]
    return ""
