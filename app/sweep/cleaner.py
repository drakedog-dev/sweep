"""Junk categories, quarantine and restore."""
from __future__ import annotations

import glob
import ntpath
import os
import re
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import platform as P

LA = os.environ.get("LOCALAPPDATA", "")
RA = os.environ.get("APPDATA", "")
WINDIR = os.environ.get("WINDIR", r"C:\Windows")
TEMP = os.environ.get("TEMP", "")
PD = os.environ.get("ProgramData", r"C:\ProgramData")

CHROMIUM_ROOTS = [
    rf"{LA}\Google\Chrome\User Data", rf"{LA}\Microsoft\Edge\User Data", rf"{LA}\Yandex\YandexBrowser\User Data",
    rf"{LA}\BraveSoftware\Brave-Browser\User Data", rf"{LA}\Vivaldi\User Data", rf"{LA}\Chromium\User Data",
    rf"{LA}\Opera Software\Opera Stable", rf"{LA}\Opera Software\Opera GX Stable",
]
# Browsing history in Chromium browsers lives in these profile files. Passwords (Login Data), bookmarks,
# autofill and cards (Web Data), extensions, settings and open tabs (Sessions) are never touched.
CHROMIUM_HISTORY = ("History", "History-journal", "Visited Links", "Top Sites", "Top Sites-journal", "Shortcuts", "Shortcuts-journal",
                    "Network Action Predictor", "Network Action Predictor-journal", "History Provider Cache", "Media History", "Media History-journal")
_cache, _cookies, _history = [], [], []
for _r in CHROMIUM_ROOTS:
    for _sub in (r"Cache\*", r"Code Cache\*", r"GPUCache\*", r"Service Worker\CacheStorage\*", r"Media Cache\*"):
        _cache += [rf"{_r}\*\{_sub}", rf"{_r}\{_sub}"]
    _cookies += [rf"{_r}\*\Network\Cookies*", rf"{_r}\Network\Cookies*"]
    for _f in CHROMIUM_HISTORY:
        _history += [rf"{_r}\*\{_f}", rf"{_r}\{_f}"]
FIREFOX_PROFILES = [rf"{RA}\Mozilla\Firefox\Profiles\*", rf"{RA}\LibreWolf\Profiles\*", rf"{RA}\Waterfox\Profiles\*"]


@dataclass
class Category:
    id: str
    name: dict
    hint: dict
    default: bool
    paths: list = field(default_factory=list)
    older_than_days: int = 0
    size: int = 0


CATEGORIES: list[Category] = [
    Category("temp", {"ru": "Временные файлы", "en": "Temporary files"}, {"ru": "Папки Temp пользователя и Windows", "en": "User and Windows Temp folders"}, True, [rf"{TEMP}\*", rf"{WINDIR}\Temp\*"]),
    Category("bin", {"ru": "Корзина", "en": "Recycle Bin"}, {"ru": "Очищается без карантина, вернуть будет нельзя", "en": "Emptied without quarantine, cannot be undone"}, False, []),
    Category("thumbs", {"ru": "Кэш эскизов Проводника", "en": "Explorer thumbnail cache"}, {"ru": "Картинки предпросмотра, Windows создаёт их заново", "en": "Preview images, Windows rebuilds them"}, True, [rf"{LA}\Microsoft\Windows\Explorer\thumbcache_*.db", rf"{LA}\Microsoft\Windows\Explorer\iconcache_*.db"]),
    Category("wu", {"ru": "Кэш обновлений Windows", "en": "Windows Update cache"}, {"ru": "Установщики уже установленных обновлений", "en": "Installers of updates already applied"}, True, [rf"{WINDIR}\SoftwareDistribution\Download\*"]),
    Category("dumps", {"ru": "Отчёты об ошибках и дампы", "en": "Error reports and dumps"}, {"ru": "Файлы о сбоях программ, нужны только разработчикам", "en": "Crash files, useful only to developers"}, True, [rf"{LA}\CrashDumps\*", rf"{WINDIR}\Minidump\*", rf"{PD}\Microsoft\Windows\WER\ReportQueue\*", rf"{PD}\Microsoft\Windows\WER\ReportArchive\*"]),
    Category("logs", {"ru": "Старые журналы Windows", "en": "Old Windows logs"}, {"ru": "Логи установки и обслуживания старше 30 дней", "en": "Setup and servicing logs older than 30 days"}, True, [rf"{WINDIR}\Logs\CBS\*.log", rf"{WINDIR}\Logs\DISM\*.log", rf"{WINDIR}\Panther\*.log"], 30),
    Category("cache", {"ru": "Кэш браузеров", "en": "Browser caches"}, {"ru": "Chrome, Edge, Яндекс, Brave, Vivaldi, Opera, Firefox. Лучше закрыть браузеры", "en": "Chrome, Edge, Yandex, Brave, Vivaldi, Opera, Firefox. Close browsers first"}, True, _cache + [rf"{LA}\Mozilla\Firefox\Profiles\*\cache2\*", rf"{LA}\Mozilla\Firefox\Profiles\*\startupCache\*"]),
    Category("history", {"ru": "История браузеров", "en": "Browser history"},
             {"ru": "Посещённые сайты, загрузки, подсказки адресной строки во всех браузерах. Пароли, закладки, автозаполнение и открытые вкладки не трогаются. Закройте браузеры",
              "en": "Visited sites, downloads list, address bar suggestions in every browser. Passwords, bookmarks, autofill and open tabs stay. Close browsers first"},
             False, _history),
    Category("cookies", {"ru": "Куки браузеров", "en": "Browser cookies"}, {"ru": "Выйдете из всех сайтов. По умолчанию выключено", "en": "You will be signed out of all sites. Off by default"}, False, _cookies + [rf"{RA}\Mozilla\Firefox\Profiles\*\cookies.sqlite*"]),
]

DEMO_SIZES = {"history": 212 * 2**20, "temp": 1.8 * 2**30, "bin": 612 * 2**20, "thumbs": 140 * 2**20, "wu": 1.1 * 2**30, "dumps": 96 * 2**20, "logs": 38 * 2**20, "cache": 1.5 * 2**30, "cookies": 24 * 2**20}


def _safe_pattern(pat: str) -> bool:
    """Only patterns inside a real folder at least two levels deep, never a drive root or a relative path."""
    base = re.split(r"[*?\[]", pat, maxsplit=1)[0].rstrip("\\/")
    drive, rest = ntpath.splitdrive(base)
    return bool(drive) and len([x for x in re.split(r"[\\/]", rest) if x]) >= 2


def _items(cat: Category) -> list[Path]:
    out: list[Path] = []
    for pat in cat.paths:
        if P.IS_WINDOWS and not _safe_pattern(pat):
            P.log(f"junk: pattern skipped, its folder is unknown: {pat}")
            continue
        for p in glob.glob(pat):
            out.append(Path(p))
    if cat.older_than_days:
        limit = time.time() - cat.older_than_days * 86400
        out = [p for p in out if p.exists() and p.stat().st_mtime < limit]
    return out


def _size(p: Path) -> int:
    try:
        if p.is_file():
            return p.stat().st_size
        total = 0
        for root, _, files in os.walk(p):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
        return total
    except OSError:
        return 0


def recycle_bin_size() -> int:
    if not P.IS_WINDOWS:
        return int(DEMO_SIZES["bin"])
    out = P.powershell("$s=0; foreach($i in (New-Object -ComObject Shell.Application).Namespace(0xA).Items()){$s+=$i.Size}; $s", 30).strip()
    try:
        return int(float(out))
    except ValueError:
        return 0


def scan(cat: Category) -> int:
    if not P.IS_WINDOWS:
        cat.size = int(DEMO_SIZES.get(cat.id, 0))
        return cat.size
    if cat.id == "bin":
        cat.size = recycle_bin_size()
    else:
        cat.size = sum(_size(p) for p in _items(cat))
        if cat.id == "history":
            cat.size += sum(_size(Path(db)) for db in _firefox_places())
    return cat.size


# ---------------- Firefox history ----------------
# In Firefox history and bookmarks share one database (places.sqlite), so the file cannot simply be moved away.
# Sweep copies it to quarantine first, then deletes only visits and pages that are not bookmarked.
FIREFOX_SQL = [
    "PRAGMA foreign_keys = ON",
    "DELETE FROM moz_historyvisits",
    "DELETE FROM moz_inputhistory",
    "DELETE FROM moz_places_metadata",
    "DELETE FROM moz_places_metadata_search_queries",
    "DELETE FROM moz_places WHERE id NOT IN (SELECT fk FROM moz_bookmarks WHERE fk IS NOT NULL)"
    " AND id NOT IN (SELECT place_id FROM moz_keywords WHERE place_id IS NOT NULL)"
    " AND id NOT IN (SELECT place_id FROM moz_annos WHERE place_id IS NOT NULL)",
    "UPDATE moz_places SET visit_count = 0, last_visit_date = NULL",
    "DELETE FROM moz_origins WHERE id NOT IN (SELECT origin_id FROM moz_places WHERE origin_id IS NOT NULL)",
]


def _firefox_places() -> list[str]:
    out = []
    for pat in FIREFOX_PROFILES:
        out += glob.glob(os.path.join(pat, "places.sqlite"))
    return out


def clean_firefox_history(db: str, backup_dir: Path | None = None, manifest: Path | None = None) -> int:
    """Remove history from one places.sqlite, keeping bookmarks. Returns bytes freed, 0 if the browser is open."""
    import sqlite3
    src = Path(db)
    before = _size(src) + _size(Path(db + "-wal"))
    copy = None
    if backup_dir is not None:
        backup_dir.mkdir(parents=True, exist_ok=True)
        copy = backup_dir / f"{src.parent.name}_places.sqlite"
    try:
        con = sqlite3.connect(f"file:{src.as_posix()}?mode=rw", uri=True, timeout=1, isolation_level=None)
    except Exception as e:
        P.log(f"firefox {db}: {e}")
        return 0
    try:
        con.execute("BEGIN EXCLUSIVE")          # fails at once while Firefox has the database open
        if copy is not None:
            con.execute("COMMIT")
            con.execute(f"VACUUM INTO '{str(copy).replace(chr(39), chr(39) * 2)}'")
            con.execute("BEGIN EXCLUSIVE")
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for q in FIREFOX_SQL:
            words = q.split()
            target = words[2] if words[0] in ("DELETE",) else words[1] if words[0] == "UPDATE" else None
            if target and target not in tables:
                continue
            if "moz_annos" in q and "moz_annos" not in tables:
                q = q.replace(" AND id NOT IN (SELECT place_id FROM moz_annos WHERE place_id IS NOT NULL)", "")
            if "moz_keywords" in q and "moz_keywords" not in tables:
                q = q.replace(" AND id NOT IN (SELECT place_id FROM moz_keywords WHERE place_id IS NOT NULL)", "")
            con.execute(q)
        con.execute("COMMIT")
        con.execute("VACUUM")
    except Exception as e:
        P.log(f"firefox {db}: {e}")
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        con.close()
        if copy is not None and copy.exists():
            copy.unlink(missing_ok=True)
        return 0
    con.close()
    if copy is not None and manifest is not None:
        with manifest.open("a", encoding="utf-8") as m:
            m.write(f"{copy}|{src}\n")
    return max(0, before - _size(src) - _size(Path(db + "-wal")))


def new_session() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def quarantine(cat: Category, session: str) -> int:
    """Move every item of the category into the quarantine folder; return bytes moved."""
    if not P.IS_WINDOWS:
        time.sleep(0.3)
        return cat.size
    if cat.id == "bin":
        before = recycle_bin_size()
        P.powershell("Clear-RecycleBin -Force -ErrorAction SilentlyContinue", 60)
        return before
    dest = P.QUARANTINE / session / cat.id
    dest.mkdir(parents=True, exist_ok=True)
    manifest = P.QUARANTINE / session / "manifest.txt"
    moved = 0
    if cat.id == "wu":
        P.powershell("Stop-Service wuauserv -Force -ErrorAction SilentlyContinue", 30)
    for i, item in enumerate(_items(cat), 1):
        size = _size(item)
        target = dest / f"{i:05d}_{item.name}"
        try:
            shutil.move(str(item), str(target))
            with manifest.open("a", encoding="utf-8") as m:
                m.write(f"{target}|{item}\n")
            moved += size
        except Exception:
            pass  # file in use
    if cat.id == "wu":
        P.powershell("Start-Service wuauserv -ErrorAction SilentlyContinue", 30)
    if cat.id == "history":
        if _running(("firefox.exe", "librewolf.exe", "waterfox.exe")):
            P.log("firefox is open, its history was skipped")
        else:
            for db in _firefox_places():
                moved += clean_firefox_history(db, dest / "firefox", manifest)
    return moved


def _running(names: tuple[str, ...]) -> bool:
    try:
        import psutil
        return any((p.info.get("name") or "").lower() in names for p in psutil.process_iter(["name"]))
    except Exception:
        return False


def quarantine_files(paths: list[str], session: str, bucket: str = "files") -> int:
    dest = P.QUARANTINE / session / bucket
    dest.mkdir(parents=True, exist_ok=True)
    manifest = P.QUARANTINE / session / "manifest.txt"
    moved = 0
    for i, src in enumerate(paths, 1):
        p = Path(src)
        try:
            size = p.stat().st_size
            target = dest / f"{i:03d}_{p.name}"
            shutil.move(str(p), str(target))
            with manifest.open("a", encoding="utf-8") as m:
                m.write(f"{target}|{p}\n")
            moved += size
        except Exception as e:
            P.log(f"quarantine {src}: {e}")
    return moved


def sessions() -> list[dict]:
    out = []
    if not P.QUARANTINE.exists():
        return out
    for d in sorted(P.QUARANTINE.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        size = _size(d)
        try:
            date = datetime.strptime(d.name, "%Y%m%d_%H%M%S")
        except ValueError:
            date = datetime.fromtimestamp(d.stat().st_mtime)
        out.append({"path": str(d), "date": date.strftime("%d.%m.%Y %H:%M"), "size": size})
    if not out and not P.IS_WINDOWS:
        out = [{"path": "demo1", "date": "24.10.2026 21:10", "size": 2.3 * 2**30}, {"path": "demo2", "date": "18.10.2026 12:00", "size": 640 * 2**20}]
    return out


def restore(session_path: str) -> int:
    d = Path(session_path)
    manifest = d / "manifest.txt"
    if not manifest.exists():
        return 0
    n = 0
    left: list[str] = []          # lines that could not be restored stay in the quarantine, nothing is lost
    for line in manifest.read_text("utf-8").splitlines():
        if "|" not in line:
            continue
        src, dst = line.split("|", 1)
        if not Path(src).exists():
            continue
        if Path(dst).exists():        # moving onto an existing folder would put the copy inside it
            P.log(f"restore {dst}: already exists, kept in quarantine")
            left.append(line)
            continue
        try:
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src, dst)
            n += 1
        except Exception as e:
            P.log(f"restore {dst}: {e}")
            left.append(line)
    if left:
        manifest.write_text("\n".join(left) + "\n", "utf-8")
    else:
        shutil.rmtree(d, ignore_errors=True)
    return n


def purge(max_age_days: int | None = None) -> None:
    if not P.QUARANTINE.exists():
        return
    for d in P.QUARANTINE.iterdir():
        if not d.is_dir():
            continue
        if max_age_days is not None and (time.time() - d.stat().st_ctime) < max_age_days * 86400:
            continue
        shutil.rmtree(d, ignore_errors=True)


def total_quarantined() -> int:
    return sum(s["size"] for s in sessions())
