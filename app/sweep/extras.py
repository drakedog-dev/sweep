"""Registry cleaning with backups, disks and large files, bloat apps, system info, PC profile, live monitors."""
from __future__ import annotations

import os
import platform as pyplatform
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import psutil

from . import platform as P

# ---------------- registry ----------------
@dataclass
class RegCategory:
    id: str
    name: dict
    hint: dict
    keys: list[str]
    mode: str  # clear / dead / deadvalues
    found: int = -1


REG_CATEGORIES = [
    RegCategory("mru", {"ru": "Списки недавних документов и команд", "en": "Recent documents and commands"}, {"ru": "RecentDocs, RunMRU, история диалогов «Открыть» и «Сохранить»", "en": "RecentDocs, RunMRU, Open and Save dialog history"},
                [r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32\OpenSavePidlMRU", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32\LastVisitedPidlMRU", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\TypedPaths"], "clear"),
    RegCategory("muicache", {"ru": "Кэш названий программ (MuiCache)", "en": "Program name cache (MuiCache)"}, {"ru": "Названия давно удалённых программ, Windows пересоздаёт при необходимости", "en": "Names of long-removed programs, Windows rebuilds it"}, [r"HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache"], "clear"),
    RegCategory("apppaths", {"ru": "Пути к удалённым программам (App Paths)", "en": "Paths to removed programs (App Paths)"}, {"ru": "Записи, у которых исполняемый файл уже не существует", "en": "Entries whose executable no longer exists"}, [r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths", r"HKCU\Software\Microsoft\Windows\CurrentVersion\App Paths"], "dead"),
    RegCategory("deadrun", {"ru": "Автозагрузка несуществующих программ", "en": "Startup entries for missing programs"}, {"ru": "Записи Run, чей файл удалён с диска", "en": "Run entries whose file was deleted"}, [r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run", r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"], "deadvalues"),
]
_DEMO_REG = {"mru": 143, "muicache": 61, "apppaths": 4, "deadrun": 1}

_REG_PS = r'''
function P($k){ $k -replace '^HKCU\\','HKCU:\' -replace '^HKLM\\','HKLM:\' }
function Exe($c){ if(-not $c){return $null}; $c=[Environment]::ExpandEnvironmentVariables($c.Trim()); if($c.StartsWith('"')){$e=$c.IndexOf('"',1); if($e -gt 0){return $c.Substring(1,$e-1)}}; $m=[regex]::Match($c,'^(.*?\.(exe|cmd|bat|com))','IgnoreCase'); if($m.Success){return $m.Groups[1].Value}; return $c.Split(' ')[0] }
function Find($keys,$mode){ $items=@()
  foreach($k in $keys){ $ps=P $k; if(-not (Test-Path $ps)){continue}
    switch($mode){
      'clear'{ $n=@(Get-ChildItem $ps -EA SilentlyContinue).Count + @((Get-ItemProperty $ps -EA SilentlyContinue).PSObject.Properties | ? Name -notlike 'PS*').Count; if($n -gt 0){$items+=@{Key=$k;Value=$null}} }
      'dead'{ foreach($s in (Get-ChildItem $ps -EA SilentlyContinue)){ $e=(Get-ItemProperty $s.PSPath -EA SilentlyContinue).'(default)'; $p=Exe $e; if($p -and -not (Test-Path -LiteralPath $p)){$items+=@{Key="$k\$($s.PSChildName)";Value=$null}} } }
      'deadvalues'{ foreach($p in (Get-ItemProperty $ps -EA SilentlyContinue).PSObject.Properties){ if($p.Name -like 'PS*'){continue}; $x=Exe ([string]$p.Value); if($x -and -not (Test-Path -LiteralPath $x)){$items+=@{Key=$k;Value=$p.Name}} } }
    } }
  return ,$items }
'''


def reg_scan(cat: RegCategory) -> int:
    if not P.IS_WINDOWS:
        cat.found = _DEMO_REG.get(cat.id, 0)
        return cat.found
    keys = ",".join(f"'{k}'" for k in cat.keys)
    out = P.ps_json(_REG_PS + f"(Find @({keys}) '{cat.mode}').Count", 60)
    cat.found = int(out or 0)
    return cat.found


def reg_clean(cat: RegCategory, session: str) -> int:
    if not P.IS_WINDOWS:
        n, cat.found = cat.found, 0
        return n
    keys = ",".join(f"'{k}'" for k in cat.keys)
    bdir = str(P.REG_BACKUP).replace("'", "''")
    script = _REG_PS + f'''
$items=Find @({keys}) '{cat.mode}'; $done=0; $backed=@{{}}
foreach($it in $items){{ $root = if('{cat.mode}' -eq 'dead'){{Split-Path $it.Key -Parent}}else{{$it.Key}}
  if(-not $backed.ContainsKey($root)){{ $f=Join-Path '{bdir}' ("{session}_" + (($root -replace '[\\\\:]','_') -replace '[^\\w_\\.]','') + ".reg"); reg.exe export $root $f /y 2>&1 | Out-Null; $backed[$root]=$true }}
  try{{ $ps=P $it.Key
    if('{cat.mode}' -eq 'clear'){{ Get-ChildItem $ps -EA SilentlyContinue | Remove-Item -Recurse -Force -EA SilentlyContinue; foreach($p in (Get-ItemProperty $ps -EA SilentlyContinue).PSObject.Properties){{ if($p.Name -notlike 'PS*'){{Remove-ItemProperty $ps -Name $p.Name -EA SilentlyContinue}} }} }}
    elseif('{cat.mode}' -eq 'dead'){{ Remove-Item $ps -Recurse -Force -EA Stop }} else {{ Remove-ItemProperty $ps -Name $it.Value -EA Stop }}
    $done++ }} catch {{}} }}
$done'''
    out = P.powershell(script, 120).strip()
    cat.found = 0
    try:
        return int(out)
    except ValueError:
        return 0


def reg_backups() -> list[dict]:
    groups: dict[str, int] = {}
    for f in P.REG_BACKUP.glob("*.reg"):
        groups[f.name[:15]] = groups.get(f.name[:15], 0) + 1
    out = []
    for s, n in sorted(groups.items(), reverse=True):
        try:
            date = datetime.strptime(s, "%Y%m%d_%H%M%S").strftime("%d.%m.%Y %H:%M")
        except ValueError:
            date = s
        out.append({"session": s, "date": date, "count": n})
    return out


def reg_restore(session: str) -> int:
    n = 0
    for f in P.REG_BACKUP.glob(f"{session}*.reg"):
        P.powershell(f"reg.exe import '{f}' 2>&1 | Out-Null", 60)
        f.unlink(missing_ok=True)
        n += 1
    return n


# ---------------- disks ----------------
def volumes() -> list[dict]:
    out = []
    for part in psutil.disk_partitions(all=False):
        if P.IS_WINDOWS and ("fixed" not in part.opts.lower() and "cdrom" in part.opts.lower()):
            continue
        try:
            u = psutil.disk_usage(part.mountpoint)
        except Exception:
            continue
        if u.total <= 0:
            continue
        letter = part.mountpoint.rstrip("\\/").rstrip(":") if P.IS_WINDOWS else part.mountpoint
        out.append({"letter": letter, "label": "", "total": u.total, "free": u.free, "used": u.used, "pct": round(u.used * 100 / u.total)})
    if not P.IS_WINDOWS:
        out = [{"letter": "C", "label": "Windows", "total": 930 * 2**30, "free": 700 * 2**30, "used": 230 * 2**30, "pct": 25},
               {"letter": "D", "label": "Data", "total": 1863 * 2**30, "free": 212 * 2**30, "used": 1651 * 2**30, "pct": 89}]
    return out


def system_drive() -> str:
    return os.environ.get("SystemDrive", "C:").rstrip(":") if P.IS_WINDOWS else "C"


DRIVE_JUNK = [
    ("bin", {"ru": "Корзина на этом диске", "en": "Recycle Bin on this drive"}, {"ru": "Удалённые файлы, которые ещё занимают место", "en": "Deleted files that still take up space"}),
    ("tmp", {"ru": "Временные и недокачанные файлы", "en": "Temporary and unfinished downloads"}, {"ru": "*.tmp, *.temp, *.crdownload, *.part, ~$-файлы Office", "en": "*.tmp, *.temp, *.crdownload, *.part, Office ~$ files"}),
    ("logs", {"ru": "Старые журналы и дампы", "en": "Old logs and dumps"}, {"ru": "*.log старше 30 дней, *.dmp, *.chk, папки found.000 после проверки диска", "en": "*.log older than 30 days, *.dmp, *.chk, found.000 folders left by disk check"}),
    ("thumbs", {"ru": "Служебные файлы эскизов", "en": "Thumbnail leftovers"}, {"ru": "Thumbs.db, ehthumbs.db, .DS_Store", "en": "Thumbs.db, ehthumbs.db, .DS_Store"}),
    ("oldwin", {"ru": "Старые установки Windows", "en": "Old Windows installations"}, {"ru": "Windows.old и $WINDOWS.~BT после обновления системы", "en": "Windows.old and $WINDOWS.~BT left after a system upgrade"}),
]
_TMP_EXT = {".tmp", ".temp", ".crdownload", ".part", ".partial", ".download", ".bak~"}
_LOG_EXT = {".dmp", ".chk", ".mdmp", ".hdmp"}
_THUMBS = {"thumbs.db", "ehthumbs.db", "ehthumbs_vista.db", ".ds_store"}
_DEMO_DRIVE_JUNK = {"C": {"bin": (612 * 2**20, 38), "tmp": (210 * 2**20, 52), "logs": (96 * 2**20, 14), "thumbs": (4 * 2**20, 120), "oldwin": (11.2 * 2**30, 1)},
                    "D": {"bin": (1.3 * 2**30, 9), "tmp": (2.8 * 2**30, 7), "logs": (0, 0), "thumbs": (9 * 2**20, 300), "oldwin": (0, 0)}}


def drive_junk(letter: str) -> dict:
    """Scan one drive for junk. Returns {cat: {"size": int, "count": int, "paths": [..]}}."""
    res = {c[0]: {"size": 0, "count": 0, "paths": []} for c in DRIVE_JUNK}
    if not P.IS_WINDOWS:
        for k, (sz, n) in _DEMO_DRIVE_JUNK.get(letter, {}).items():
            res[k]["size"], res[k]["count"] = int(sz), n
        return res
    root = f"{letter}:\\"
    # recycle bin size for this drive
    try:
        rb = os.path.join(root, "$Recycle.Bin")
        for dp, _, fs in os.walk(rb):
            for f in fs:
                try:
                    res["bin"]["size"] += os.path.getsize(os.path.join(dp, f)); res["bin"]["count"] += 1
                except OSError:
                    pass
    except OSError:
        pass
    # old windows installs
    for name in ("Windows.old", "$WINDOWS.~BT", "$WINDOWS.~WS"):
        pth = os.path.join(root, name)
        if os.path.isdir(pth):
            total = 0
            for dp, _, fs in os.walk(pth):
                for f in fs:
                    try:
                        total += os.path.getsize(os.path.join(dp, f))
                    except OSError:
                        pass
            res["oldwin"]["size"] += total; res["oldwin"]["count"] += 1; res["oldwin"]["paths"].append(pth)
    skip_names = {"$recycle.bin", "system volume information", "windows", "windows.old", "$windows.~bt", "$windows.~ws", "program files", "program files (x86)", "programdata"}
    limit = time.time() - 30 * 86400
    for dp, dns, fs in os.walk(root):
        if dp == root:
            dns[:] = [d for d in dns if d.lower() not in skip_names]
        low = os.path.basename(dp).lower()
        if low.startswith("found.") and low[6:].isdigit():
            total = 0
            for dp2, _, fs2 in os.walk(dp):
                for f in fs2:
                    try:
                        total += os.path.getsize(os.path.join(dp2, f))
                    except OSError:
                        pass
            res["logs"]["size"] += total; res["logs"]["count"] += 1; res["logs"]["paths"].append(dp); dns[:] = []
            continue
        for f in fs:
            fl = f.lower(); ext = os.path.splitext(fl)[1]
            cat = None
            if fl in _THUMBS:
                cat = "thumbs"
            elif ext in _TMP_EXT or (fl.startswith("~$") and ext in (".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt")):
                cat = "tmp"
            elif ext in _LOG_EXT:
                cat = "logs"
            elif ext == ".log":
                try:
                    if os.path.getmtime(os.path.join(dp, f)) < limit:
                        cat = "logs"
                except OSError:
                    pass
            if cat:
                fp = os.path.join(dp, f)
                try:
                    res[cat]["size"] += os.path.getsize(fp); res[cat]["count"] += 1; res[cat]["paths"].append(fp)
                except OSError:
                    pass
    return res


def empty_drive_bin(letter: str) -> None:
    if P.IS_WINDOWS:
        P.powershell(f"Clear-RecycleBin -DriveLetter {letter} -Force -ErrorAction SilentlyContinue", 120)


# ---------------- apps ----------------
BLOAT = [
    ("Microsoft.XboxApp", "Xbox", {"ru": "Игровой клиент Xbox", "en": "Xbox game client"}),
    ("Microsoft.GamingApp", "Xbox (new)", {"ru": "Магазин игр Xbox", "en": "Xbox game store"}),
    ("Microsoft.XboxGamingOverlay", "Xbox Game Bar", {"ru": "Оверлей для записи игр", "en": "Game recording overlay"}),
    ("Microsoft.ZuneMusic", "Media Player", {"ru": "Проигрыватель Microsoft", "en": "Microsoft media player"}),
    ("Microsoft.ZuneVideo", "Movies & TV", {"ru": "Видеопроигрыватель и магазин фильмов", "en": "Video player and movie store"}),
    ("Microsoft.BingNews", "News", {"ru": "Лента новостей Microsoft", "en": "Microsoft news feed"}),
    ("Microsoft.BingWeather", "Weather", {"ru": "Погода от MSN", "en": "MSN weather"}),
    ("Microsoft.BingSearch", "Bing Search", {"ru": "Веб-поиск в меню Пуск", "en": "Web search in Start menu"}),
    ("Microsoft.GetHelp", "Get Help", {"ru": "Чат с поддержкой Microsoft", "en": "Microsoft support chat"}),
    ("Microsoft.Getstarted", "Tips", {"ru": "Приложение «Начало работы»", "en": "Get Started app"}),
    ("Microsoft.MicrosoftSolitaireCollection", "Solitaire Collection", {"ru": "Пасьянсы с рекламой", "en": "Card games with ads"}),
    ("Microsoft.People", "People", {"ru": "Контакты Microsoft", "en": "Microsoft contacts"}),
    ("Microsoft.MicrosoftOfficeHub", "Office Hub", {"ru": "Реклама подписки Microsoft 365", "en": "Microsoft 365 subscription promo"}),
    ("Microsoft.SkypeApp", "Skype", {"ru": "Мессенджер", "en": "Messenger"}),
    ("Microsoft.WindowsFeedbackHub", "Feedback Hub", {"ru": "Отправка отзывов в Microsoft", "en": "Sends feedback to Microsoft"}),
    ("Microsoft.Microsoft3DViewer", "3D Viewer", {"ru": "Просмотр 3D-моделей", "en": "3D model viewer"}),
    ("Microsoft.MixedReality.Portal", "Mixed Reality Portal", {"ru": "Нужен только для VR-шлема", "en": "Only for a VR headset"}),
    ("Microsoft.WindowsMaps", "Maps", {"ru": "Офлайн-карты Windows", "en": "Windows offline maps"}),
    ("Microsoft.549981C3F5F10", "Cortana", {"ru": "Голосовой помощник", "en": "Voice assistant"}),
    ("Clipchamp.Clipchamp", "Clipchamp", {"ru": "Видеоредактор с подпиской", "en": "Video editor with subscription"}),
    ("Microsoft.Todos", "Microsoft To Do", {"ru": "Список задач", "en": "To-do list"}),
    ("MicrosoftTeams", "Teams (personal)", {"ru": "Чат Teams для дома", "en": "Teams chat for home"}),
    ("MSTeams", "Teams", {"ru": "Чат Teams", "en": "Teams chat"}),
    ("Microsoft.PowerAutomateDesktop", "Power Automate", {"ru": "Автоматизация для бизнеса", "en": "Business automation"}),
    ("Microsoft.Copilot", "Copilot", {"ru": "Приложение помощника Microsoft", "en": "Microsoft assistant app"}),
    ("Microsoft.OutlookForWindows", "Outlook (new)", {"ru": "Почтовый клиент с рекламой", "en": "Mail client with ads"}),
    ("Microsoft.MicrosoftJournal", "Journal", {"ru": "Рукописные заметки", "en": "Handwritten notes"}),
    ("Microsoft.Whiteboard", "Whiteboard", {"ru": "Доска для рисования", "en": "Drawing board"}),
    ("king.com.CandyCrushSaga", "Candy Crush Saga", {"ru": "Игра", "en": "Game"}),
    ("king.com.CandyCrushSodaSaga", "Candy Crush Soda", {"ru": "Игра", "en": "Game"}),
    ("SpotifyAB.SpotifyMusic", "Spotify", {"ru": "Рекламная предустановка", "en": "Promotional pre-install"}),
    ("Disney.37853FC22B2CE", "Disney+", {"ru": "Рекламная предустановка", "en": "Promotional pre-install"}),
    ("BytedancePte.Ltd.TikTok", "TikTok", {"ru": "Рекламная предустановка", "en": "Promotional pre-install"}),
    ("Facebook.InstagramBeta", "Instagram", {"ru": "Рекламная предустановка", "en": "Promotional pre-install"}),
    ("AmazonVideo.PrimeVideo", "Prime Video", {"ru": "Рекламная предустановка", "en": "Promotional pre-install"}),
]


def installed_bloat() -> list[dict]:
    if not P.IS_WINDOWS:
        demo = {"Microsoft.XboxApp", "Microsoft.MicrosoftSolitaireCollection", "Microsoft.BingNews", "Microsoft.BingWeather", "Microsoft.MicrosoftOfficeHub", "Clipchamp.Clipchamp", "king.com.CandyCrushSaga"}
        return [{"id": i, "name": n, "hint": h} for i, n, h in BLOAT if i in demo]
    names = P.ps_json("Get-AppxPackage -AllUsers | Select-Object -ExpandProperty Name -Unique", 90) or []
    names = set(names if isinstance(names, list) else [names])
    return [{"id": i, "name": n, "hint": h} for i, n, h in BLOAT if i in names]


def remove_app(app_id: str) -> None:
    if not P.IS_WINDOWS:
        return
    P.powershell(f"Get-AppxPackage -Name '{app_id}' -AllUsers -EA SilentlyContinue | Remove-AppxPackage -AllUsers -EA SilentlyContinue; Get-AppxProvisionedPackage -Online -EA SilentlyContinue | ? DisplayName -eq '{app_id}' | Remove-AppxProvisionedPackage -Online -EA SilentlyContinue | Out-Null", 180)


# ---------------- system info ----------------
def system_info() -> dict:
    """Returns {section: [(label, value)]} with raw language-neutral values where possible."""
    mem = psutil.virtual_memory()
    boot = datetime.fromtimestamp(psutil.boot_time())
    info: dict = {"uptime": time.time() - psutil.boot_time(), "ram_total": mem.total, "ram_free": mem.available, "cores": psutil.cpu_count(False) or 0, "threads": psutil.cpu_count() or 0}
    if P.IS_WINDOWS:
        d = P.ps_json(r'''
$os=Get-CimInstance Win32_OperatingSystem; $cs=Get-CimInstance Win32_ComputerSystem; $cpu=Get-CimInstance Win32_Processor|select -First 1
$vram=@{}; Get-ChildItem 'HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}' -EA SilentlyContinue|%{ $p=Get-ItemProperty $_.PSPath -EA SilentlyContinue; $q=$p.'HardwareInformation.qwMemorySize'; if($p.DriverDesc -and $q){ if($q -is [byte[]]){$q=[BitConverter]::ToInt64($q,0)}; $vram[[string]$p.DriverDesc]=[long]$q } }
$gpu=Get-CimInstance Win32_VideoController|%{ $r=[long]$_.AdapterRAM; if($vram.ContainsKey([string]$_.Name)){$r=$vram[[string]$_.Name]}; @{name=$_.Name;ram=$r;driver=$_.DriverVersion}}
$mb=Get-CimInstance Win32_BaseBoard; $bios=Get-CimInstance Win32_BIOS
$mods=Get-CimInstance Win32_PhysicalMemory|%{@{slot=$_.DeviceLocator;size=[long]$_.Capacity;speed=$_.Speed;maker=$_.Manufacturer}}
$disks=Get-PhysicalDisk -EA SilentlyContinue|%{@{name=$_.FriendlyName;size=[long]$_.Size;media=[string]$_.MediaType;bus=[string]$_.BusType}}
$t=@(); try{ foreach($z in (Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -EA Stop)){ $c=[math]::Round(($z.CurrentTemperature/10)-273.15,1); if($c -gt 0 -and $c -lt 130){$t+=$c} } }catch{}
@{os="$($os.Caption) $($os.Version) (build $($os.BuildNumber))"; pc="$($cs.Manufacturer) $($cs.Model)"; cpu=$cpu.Name.Trim(); mhz=$cpu.MaxClockSpeed; gpu=@($gpu); board="$($mb.Manufacturer) $($mb.Product)"; bios="$($bios.SMBIOSBIOSVersion) $($bios.ReleaseDate.ToString('d'))"; mods=@($mods); disks=@($disks); temps=@($t); laptop=[bool]($cs.PCSystemType -eq 2)}''', 90) or {}
        info.update(d)
    else:
        info.update({"os": "Windows 11 Pro 10.0.26100 (build 26100)", "pc": "ASUS TUF H370-PRO GAMING", "cpu": "Intel Core i7-8700 @ 3.20GHz", "mhz": 3200,
                     "gpu": [{"name": "NVIDIA GeForce RTX 3060", "ram": 12 * 2**30, "driver": "566.14"}], "board": "ASUSTeK TUF H370-PRO GAMING", "bios": "2203 12.04.2021",
                     "mods": [{"slot": "DIMM_A2", "size": 16 * 2**30, "speed": 2666, "maker": "Kingston"}, {"slot": "DIMM_B2", "size": 16 * 2**30, "speed": 2666, "maker": "Kingston"}],
                     "disks": [{"name": "Samsung SSD 970 EVO 1TB", "size": 1000 * 10**9, "media": "SSD", "bus": "NVMe"}, {"name": "WDC WD20EZRZ", "size": 2000 * 10**9, "media": "HDD", "bus": "SATA"}],
                     "temps": [], "laptop": False, "ram_total": 32 * 2**30, "ram_free": 19 * 2**30, "cores": 6, "threads": 12})
    return info


# ---------------- PC profile ----------------
def pc_profile(info: dict) -> dict:
    """Classify the machine: weak / mid / strong, with a short reasoning list."""
    ram_gb = info.get("ram_total", 0) / 2**30
    threads = info.get("threads", 0) or 0
    disks = info.get("disks") or []
    has_ssd = any("ssd" in str(d.get("media", "")).lower() or "nvme" in str(d.get("bus", "")).lower() for d in disks)
    score = 0
    score += 0 if ram_gb < 6 else 1 if ram_gb < 12 else 2 if ram_gb < 24 else 3
    score += 0 if threads <= 2 else 1 if threads <= 4 else 2 if threads <= 8 else 3
    score += 2 if has_ssd else 0
    cls = "weak" if score <= 3 else "mid" if score <= 6 else "strong"
    return {"class": cls, "ram_gb": round(ram_gb), "threads": threads, "ssd": has_ssd, "score": score}


# ---------------- live monitors ----------------
class Monitor:
    def __init__(self):
        psutil.cpu_percent(None)
        self._last_disk = psutil.disk_io_counters()
        self._last_t = time.time()

    def sample(self) -> dict:
        cpu = psutil.cpu_percent(None)
        mem = psutil.virtual_memory()
        now = time.time()
        io = psutil.disk_io_counters()
        dt = max(0.001, now - self._last_t)
        mbps = 0.0
        if io and self._last_disk:
            mbps = ((io.read_bytes - self._last_disk.read_bytes) + (io.write_bytes - self._last_disk.write_bytes)) / dt / 2**20
        self._last_disk, self._last_t = io, now
        return {"cpu": cpu, "ram": mem.percent, "ram_used": mem.used, "ram_total": mem.total, "disk_mbps": round(mbps, 1)}
