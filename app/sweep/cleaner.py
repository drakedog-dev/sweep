"""Junk categories, quarantine and restore."""
from __future__ import annotations

import glob
import os
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
_cache, _cookies = [], []
for _r in CHROMIUM_ROOTS:
    for _sub in (r"Cache\*", r"Code Cache\*", r"GPUCache\*", r"Service Worker\CacheStorage\*", r"Media Cache\*"):
        _cache += [rf"{_r}\*\{_sub}", rf"{_r}\{_sub}"]
    _cookies += [rf"{_r}\*\Network\Cookies*", rf"{_r}\Network\Cookies*"]


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
    Category("cookies", {"ru": "Куки браузеров", "en": "Browser cookies"}, {"ru": "Выйдете из всех сайтов. По умолчанию выключено", "en": "You will be signed out of all sites. Off by default"}, False, _cookies + [rf"{RA}\Mozilla\Firefox\Profiles\*\cookies.sqlite*"]),
]

DEMO_SIZES = {"temp": 1.8 * 2**30, "bin": 612 * 2**20, "thumbs": 140 * 2**20, "wu": 1.1 * 2**30, "dumps": 96 * 2**20, "logs": 38 * 2**20, "cache": 1.5 * 2**30, "cookies": 24 * 2**20}


def _items(cat: Category) -> list[Path]:
    out: list[Path] = []
    for pat in cat.paths:
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
    return cat.size


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
    return moved


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
    for line in manifest.read_text("utf-8").splitlines():
        if "|" not in line:
            continue
        src, dst = line.split("|", 1)
        if not Path(src).exists():
            continue
        try:
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src, dst)
            n += 1
        except Exception as e:
            P.log(f"restore {dst}: {e}")
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
