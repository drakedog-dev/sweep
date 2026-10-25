"""Privacy switches, services, startup entries, visual effects, power plan, schedule."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import platform as P

if P.IS_WINDOWS:
    import winreg

HKCU, HKLM = "HKCU", "HKLM"


@dataclass
class RegValue:
    root: str
    path: str
    name: str
    off: int           # value when protection is ON (tracking disabled)
    on: int | None     # value to restore; None = delete the value


@dataclass
class Privacy:
    id: str
    group: str  # data / ads / assist
    name: dict
    hint: dict
    reg: list[RegValue]
    services: list[str] = field(default_factory=list)
    tasks: list[str] = field(default_factory=list)
    alt: list[RegValue] = field(default_factory=list)  # other places where Windows Settings or other tools record the same choice


def _rv(root, path, name, off, on=None):
    return RegValue(root, path, name, off, on)


CDM = r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
PRIVACY: list[Privacy] = [
    Privacy("telemetry", "data", {"ru": "Телеметрия и сбор диагностики", "en": "Telemetry and diagnostics"}, {"ru": "Служба DiagTrack и задания сбора данных", "en": "DiagTrack service and data collection tasks"},
            [_rv(HKLM, r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0)], ["DiagTrack", "dmwappushservice"],
            [r"\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser", r"\Microsoft\Windows\Application Experience\ProgramDataUpdater", r"\Microsoft\Windows\Customer Experience Improvement Program\Consolidator", r"\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip", r"\Microsoft\Windows\DiskDiagnostic\Microsoft-Windows-DiskDiagnosticDataCollector"]),
    Privacy("adid", "data", {"ru": "Рекламный идентификатор", "en": "Advertising ID"}, {"ru": "Приложения не смогут показывать рекламу по вашим интересам", "en": "Apps cannot target ads to your interests"}, [_rv(HKCU, r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "Enabled", 0, 1)]),
    Privacy("activity", "data", {"ru": "История активности", "en": "Activity history"}, {"ru": "Windows не будет собирать, что вы открывали, и отправлять это в облако", "en": "Windows stops recording what you open and uploading it"},
            [_rv(HKLM, r"SOFTWARE\Policies\Microsoft\Windows\System", "EnableActivityFeed", 0), _rv(HKLM, r"SOFTWARE\Policies\Microsoft\Windows\System", "PublishUserActivities", 0), _rv(HKLM, r"SOFTWARE\Policies\Microsoft\Windows\System", "UploadUserActivities", 0)]),
    Privacy("feedback", "data", {"ru": "Запросы отзывов", "en": "Feedback prompts"}, {"ru": "Windows перестанет спрашивать «Как вам Windows?»", "en": "Windows stops asking how you like it"}, [_rv(HKCU, r"Software\Microsoft\Siuf\Rules", "NumberOfSIUFInPeriod", 0)]),
    Privacy("wer", "data", {"ru": "Отправка отчётов об ошибках", "en": "Error reporting"}, {"ru": "Сведения о сбоях не уходят в Microsoft", "en": "Crash details are not sent to Microsoft"}, [_rv(HKLM, r"SOFTWARE\Policies\Microsoft\Windows\Windows Error Reporting", "Disabled", 1)], ["WerSvc"]),
    Privacy("trackprogs", "data", {"ru": "Отслеживание запуска программ", "en": "App launch tracking"}, {"ru": "Используется для подсказок в Пуске", "en": "Used for Start menu suggestions"}, [_rv(HKCU, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "Start_TrackProgs", 0, 1)]),
    Privacy("tips", "ads", {"ru": "Реклама в Пуске и уведомлениях", "en": "Ads in Start and notifications"}, {"ru": "Предложения приложений, советы и автоустановка рекламных приложений", "en": "App suggestions, tips and silent installs of promoted apps"},
            [_rv(HKCU, CDM, n, 0, 1) for n in ("SubscribedContent-338388Enabled", "SubscribedContent-338389Enabled", "SubscribedContent-353694Enabled", "SubscribedContent-353696Enabled", "SystemPaneSuggestionsEnabled", "SilentInstalledAppsEnabled", "SoftLandingEnabled")]),
    Privacy("lockscreen", "ads", {"ru": "Реклама на экране блокировки", "en": "Lock screen ads"}, {"ru": "Факты и советы поверх картинки экрана блокировки", "en": "Fun facts and tips over the lock screen picture"}, [_rv(HKCU, CDM, "RotatingLockScreenOverlayEnabled", 0, 1), _rv(HKCU, CDM, "SubscribedContent-338387Enabled", 0, 1)]),
    Privacy("welcome", "ads", {"ru": "Экран «Что нового» после обновлений", "en": "What is new screen after updates"}, {"ru": "Без приветствия и предложений после каждого обновления", "en": "No welcome screen and offers after every update"}, [_rv(HKCU, CDM, "SubscribedContent-310093Enabled", 0, 1), _rv(HKCU, r"Software\Microsoft\Windows\CurrentVersion\UserProfileEngagement", "ScoobeSystemSettingEnabled", 0, 1)]),
    Privacy("explorerads", "ads", {"ru": "Реклама в Проводнике", "en": "Ads in File Explorer"}, {"ru": "Баннеры OneDrive и Microsoft 365 в окнах папок", "en": "OneDrive and Microsoft 365 banners in folder windows"}, [_rv(HKCU, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "ShowSyncProviderNotifications", 0, 1)]),
    Privacy("startrec", "ads", {"ru": "Рекомендации в меню Пуск (Windows 11)", "en": "Start menu recommendations (Windows 11)"}, {"ru": "Раздел «Рекомендуем» перестанет подсовывать сайты и приложения", "en": "The Recommended section stops pushing sites and apps"}, [_rv(HKCU, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "Start_IrisRecommendations", 0, 1)]),
    Privacy("searchhl", "ads", {"ru": "Картинки и новости в строке поиска", "en": "Search box highlights"}, {"ru": "Поле поиска на панели задач станет пустым", "en": "Taskbar search box stays empty"}, [_rv(HKCU, r"Software\Microsoft\Windows\CurrentVersion\SearchSettings", "IsDynamicSearchBoxEnabled", 0, 1)]),
    Privacy("search", "ads", {"ru": "Поиск в интернете из меню Пуск", "en": "Web search from Start menu"}, {"ru": "Пуск ищет только на компьютере и ничего не шлёт в Bing", "en": "Start searches only this PC and sends nothing to Bing"}, [_rv(HKCU, r"Software\Policies\Microsoft\Windows\Explorer", "DisableSearchBoxSuggestions", 1), _rv(HKCU, r"Software\Microsoft\Windows\CurrentVersion\Search", "BingSearchEnabled", 0)]),
    Privacy("feeds", "ads", {"ru": "Новости и виджеты на панели задач", "en": "News and widgets on the taskbar"}, {"ru": "«Новости и интересы» в Windows 10, виджеты в Windows 11", "en": "News and Interests in Windows 10, Widgets in Windows 11"}, [_rv(HKLM, r"SOFTWARE\Policies\Microsoft\Windows\Windows Feeds", "EnableFeeds", 0), _rv(HKLM, r"SOFTWARE\Policies\Microsoft\Dsh", "AllowNewsAndInterests", 0)]),
    Privacy("cortana", "assist", {"ru": "Кортана", "en": "Cortana"}, {"ru": "Голосовой помощник Microsoft", "en": "Microsoft voice assistant"}, [_rv(HKLM, r"SOFTWARE\Policies\Microsoft\Windows\Windows Search", "AllowCortana", 0)]),
    Privacy("copilot", "assist", {"ru": "Copilot", "en": "Copilot"}, {"ru": "Кнопка и панель Copilot исчезнут с панели задач", "en": "Copilot button and panel disappear from the taskbar"}, [_rv(HKCU, r"Software\Policies\Microsoft\Windows\WindowsCopilot", "TurnOffWindowsCopilot", 1)]),
    Privacy("edge", "assist", {"ru": "Сбор данных браузером Edge", "en": "Edge data collection"}, {"ru": "Edge перестанет отправлять историю и данные об использовании", "en": "Edge stops sending browsing and usage data"}, [_rv(HKLM, r"SOFTWARE\Policies\Microsoft\Edge", "MetricsReportingEnabled", 0), _rv(HKLM, r"SOFTWARE\Policies\Microsoft\Edge", "PersonalizationReportingEnabled", 0)]),
]

_ALT = {
    "telemetry": [_rv(HKLM, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection", "AllowTelemetry", 0), _rv(HKLM, r"SYSTEM\CurrentControlSet\Services\DiagTrack", "Start", 4)],
    "wer": [_rv(HKLM, r"SOFTWARE\Microsoft\Windows\Windows Error Reporting", "Disabled", 1), _rv(HKLM, r"SYSTEM\CurrentControlSet\Services\WerSvc", "Start", 4)],
    "feeds": [_rv(HKCU, r"Software\Microsoft\Windows\CurrentVersion\Feeds", "ShellFeedsTaskbarViewMode", 2), _rv(HKCU, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "TaskbarDa", 0)],
    "copilot": [_rv(HKCU, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "ShowCopilotButton", 0)],
    "edge": [_rv(HKLM, r"SOFTWARE\Policies\Microsoft\Edge", "DiagnosticData", 0)],
}
for _p in PRIVACY:
    _p.alt = _ALT.get(_p.id, [])

# The switch shows whether the Windows feature works (on) or is disabled (off), like Windows Settings,
# so each hint says what the feature does.
_HINTS = {
    "telemetry": {"ru": "Windows отправляет в Microsoft данные об использовании: служба DiagTrack и задания сбора данных", "en": "Windows sends usage data to Microsoft: DiagTrack service and data collection tasks"},
    "adid": {"ru": "По нему приложения показывают рекламу по вашим интересам", "en": "Lets apps show ads based on your interests"},
    "activity": {"ru": "Windows запоминает, что вы открывали, и отправляет это в облако", "en": "Windows records what you open and uploads it"},
    "feedback": {"ru": "Windows время от времени спрашивает «Как вам Windows?»", "en": "Windows asks how you like it from time to time"},
    "wer": {"ru": "Сведения о сбоях программ уходят в Microsoft", "en": "Crash details are sent to Microsoft"},
    "trackprogs": {"ru": "Windows запоминает, какие программы вы запускаете, для подсказок в Пуске", "en": "Windows tracks the apps you launch for Start menu suggestions"},
    "tips": {"ru": "Предложения приложений, советы и тихая установка рекламных приложений", "en": "App suggestions, tips and silent installs of promoted apps"},
    "lockscreen": {"ru": "Факты и советы поверх картинки экрана блокировки", "en": "Fun facts and tips over the lock screen picture"},
    "welcome": {"ru": "Приветствие и предложения Microsoft после каждого обновления", "en": "Welcome screen and Microsoft offers after every update"},
    "explorerads": {"ru": "Баннеры OneDrive и Microsoft 365 в окнах папок", "en": "OneDrive and Microsoft 365 banners in folder windows"},
    "startrec": {"ru": "Раздел «Рекомендуем» подсовывает сайты и приложения", "en": "The Recommended section pushes sites and apps"},
    "searchhl": {"ru": "В поле поиска на панели задач картинки дня и новости", "en": "Daily pictures and news in the taskbar search box"},
    "search": {"ru": "Всё, что вы набираете в Пуске, уходит в Bing", "en": "Everything you type in Start is sent to Bing"},
    "feeds": {"ru": "«Новости и интересы» в Windows 10, виджеты в Windows 11", "en": "News and Interests in Windows 10, Widgets in Windows 11"},
    "cortana": {"ru": "Голосовой помощник Microsoft", "en": "Microsoft voice assistant"},
    "copilot": {"ru": "Кнопка и панель Copilot на панели задач", "en": "Copilot button and panel on the taskbar"},
    "edge": {"ru": "Edge отправляет в Microsoft данные о просмотре и использовании", "en": "Edge sends browsing and usage data to Microsoft"},
}
for _p in PRIVACY:
    _p.hint = _HINTS.get(_p.id, _p.hint)

_demo_privacy = {"adid", "tips", "feedback"}


def _hive(root: str):
    return winreg.HKEY_CURRENT_USER if root == HKCU else winreg.HKEY_LOCAL_MACHINE


def reg_get(root: str, path: str, name: str):
    if not P.IS_WINDOWS:
        return None
    try:
        with winreg.OpenKey(_hive(root), path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def _reg_exe(args: list[str]) -> bool:
    """Fallback through reg.exe (64-bit view). Returns True on success."""
    import subprocess
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    try:
        r = subprocess.run(["reg.exe"] + args + ["/reg:64", "/f"], capture_output=True, text=True, timeout=30, startupinfo=si)
        if r.returncode != 0:
            P.log(f"reg.exe {' '.join(args[:2])}: {(r.stderr or r.stdout).strip()}")
        return r.returncode == 0
    except Exception as e:
        P.log(f"reg.exe: {e}")
        return False


def _reg_exe_query(root: str, path: str, name: str) -> str:
    """What another process sees for this value (to tell a silently dropped write from a sandboxed one)."""
    import subprocess
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    try:
        r = subprocess.run(["reg.exe", "query", f"{root}\\{path}", "/v", name, "/reg:64"], capture_output=True, text=True, timeout=20, startupinfo=si)
        line = next((ln.strip() for ln in r.stdout.splitlines() if name.lower() in ln.lower() and "REG_" in ln), "")
        return line or "no value"
    except Exception as e:
        return f"error {e}"


def reg_set(root: str, path: str, name: str, value):
    """Write a DWORD or binary value. Raises PermissionError when Windows refuses access."""
    if not P.IS_WINDOWS:
        return
    try:
        with winreg.CreateKeyEx(_hive(root), path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
            if isinstance(value, bytes):
                winreg.SetValueEx(k, name, 0, winreg.REG_BINARY, value)
            else:
                winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, int(value))
    except OSError as e:
        if not P.is_access_denied(e):
            raise
        kind, data = ("REG_BINARY", value.hex()) if isinstance(value, bytes) else ("REG_DWORD", str(int(value)))
        if not _reg_exe(["add", f"{root}\\{path}", "/v", name, "/t", kind, "/d", data]):
            raise PermissionError(5, f"{root}\\{path}\\{name}") from e


def reg_del(root: str, path: str, name: str):
    if not P.IS_WINDOWS:
        return
    try:
        with winreg.OpenKey(_hive(root), path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
            winreg.DeleteValue(k, name)
    except FileNotFoundError:
        pass
    except OSError as e:
        if not P.is_access_denied(e):
            return
        if reg_get(root, path, name) is not None and not _reg_exe(["delete", f"{root}\\{path}", "/v", name]):
            raise PermissionError(5, f"{root}\\{path}\\{name}") from e


def privacy_state(p: Privacy) -> bool:
    """True when tracking is switched off. Counts both Sweep's own values and the places where
    Windows Settings (or other tools) store the same choice, so manual changes are recognised."""
    if not P.IS_WINDOWS:
        return p.id in _demo_privacy
    hits = sum(1 for r in p.reg if reg_get(r.root, r.path, r.name) == r.off)
    if hits >= (len(p.reg) + 1) // 2:
        return True
    return any(reg_get(r.root, r.path, r.name) == r.off for r in p.alt)


def set_privacy(p: Privacy, protect: bool) -> list[str]:
    """Apply one privacy item value by value. Never stops halfway: returns the list of values Windows refused."""
    if not P.IS_WINDOWS:
        if protect:
            _demo_privacy.add(p.id)
        else:
            _demo_privacy.discard(p.id)
        return []
    failed: list[str] = []
    for r in p.reg:
        key = f"{r.root}\\{r.path}\\{r.name}"
        want = r.off if protect else r.on
        try:
            if want is None:
                reg_del(r.root, r.path, r.name)
            else:
                reg_set(r.root, r.path, r.name, want)
        except OSError as e:
            P.log(f"privacy {p.id}: {key}: {e}")
            failed.append(key)
            continue
        got = reg_get(r.root, r.path, r.name)
        if got != want:
            # Windows said "done" but the value is not there: something (usually an antivirus) dropped the write
            other = _reg_exe_query(r.root, r.path, r.name)
            P.log(f"privacy {p.id}: {key}: wrote {want!r}, read back {got!r}; reg.exe sees: {other}")
            failed.append(key)
    for s in p.services:
        set_service(s, not protect)
    for t in p.tasks:
        name, path = t.rsplit("\\", 1)[1], t.rsplit("\\", 1)[0] + "\\"
        verb = "Disable" if protect else "Enable"
        P.powershell(f"{verb}-ScheduledTask -TaskName '{name}' -TaskPath '{path}' -ErrorAction SilentlyContinue | Out-Null", 30)
    return failed


# ---------------- services ----------------
@dataclass
class Service:
    name: str
    title: dict
    hint: dict
    weak_only: bool = False   # recommended only on weak/mid PCs


SERVICES: list[Service] = [
    Service("SysMain", {"ru": "SysMain (Superfetch)", "en": "SysMain (Superfetch)"}, {"ru": "Предзагрузка программ. На старых HDD чаще мешает, на SSD не нужна", "en": "Preloads programs. Hurts on old HDDs, unnecessary on SSDs"}, True),
    Service("WSearch", {"ru": "Индексирование поиска", "en": "Windows Search indexing"}, {"ru": "Ускоряет поиск файлов, но постоянно грузит диск на слабых ПК", "en": "Speeds up file search but keeps the disk busy on weak PCs"}, True),
    Service("XblAuthManager", {"ru": "Xbox: вход", "en": "Xbox: sign-in"}, {"ru": "Нужна только для игр Xbox", "en": "Only needed for Xbox games"}),
    Service("XblGameSave", {"ru": "Xbox: сохранения", "en": "Xbox: game saves"}, {"ru": "Нужна только для игр Xbox", "en": "Only needed for Xbox games"}),
    Service("XboxNetApiSvc", {"ru": "Xbox: сеть", "en": "Xbox: networking"}, {"ru": "Нужна только для игр Xbox", "en": "Only needed for Xbox games"}),
    Service("XboxGipSvc", {"ru": "Xbox: геймпад", "en": "Xbox: controller"}, {"ru": "Нужна только для геймпада Xbox", "en": "Only needed for an Xbox controller"}),
    Service("MapsBroker", {"ru": "Загрузка карт", "en": "Maps download"}, {"ru": "Офлайн-карты Windows", "en": "Windows offline maps"}),
    Service("RetailDemo", {"ru": "Демо-режим магазина", "en": "Retail demo mode"}, {"ru": "Только для витринных компьютеров", "en": "Only for display PCs in shops"}),
    Service("Fax", {"ru": "Факс", "en": "Fax"}, {"ru": "Если нет факса, не нужна", "en": "Not needed without a fax machine"}),
    Service("RemoteRegistry", {"ru": "Удалённый реестр", "en": "Remote Registry"}, {"ru": "Правка реестра по сети. Дома не нужна", "en": "Registry editing over the network. Not for home use"}),
    Service("WMPNetworkSvc", {"ru": "Общий доступ Media Player", "en": "Media Player sharing"}, {"ru": "Раздача музыки по домашней сети", "en": "Streams music over the home network"}),
    Service("PhoneSvc", {"ru": "Телефонная служба", "en": "Phone service"}, {"ru": "Связь с телефоном через «Связь с Windows»", "en": "Phone Link connection"}),
]
SVC_BACKUP = P.ROOT / "services-backup.json"
_demo_services = {"RetailDemo": False, "Fax": False}


def _backup() -> dict:
    try:
        return json.loads(SVC_BACKUP.read_text("utf-8"))
    except Exception:
        return {}


def service_state(name: str):
    """True running/enabled, False disabled, None not installed."""
    if not P.IS_WINDOWS:
        return _demo_services.get(name, True)
    out = P.powershell(f"(Get-CimInstance Win32_Service -Filter \"Name='{name}'\").StartMode", 30).strip()
    if not out:
        return None
    return out != "Disabled"


def set_service(name: str, enabled: bool) -> None:
    if not P.IS_WINDOWS:
        _demo_services[name] = enabled
        return
    b = _backup()
    if enabled:
        t = b.get(name, "Manual")
        if t == "Disabled":
            t = "Manual"
        P.powershell(f"Set-Service -Name '{name}' -StartupType {t} -ErrorAction SilentlyContinue; if ('{t}' -eq 'Automatic') {{ Start-Service -Name '{name}' -ErrorAction SilentlyContinue }}", 60)
    else:
        if name not in b:
            mode = P.powershell(f"(Get-CimInstance Win32_Service -Filter \"Name='{name}'\").StartMode", 30).strip()
            b[name] = {"Auto": "Automatic", "Manual": "Manual", "Disabled": "Disabled"}.get(mode, "Manual")
            SVC_BACKUP.write_text(json.dumps(b), "utf-8")
        P.powershell(f"Stop-Service -Name '{name}' -Force -ErrorAction SilentlyContinue; Set-Service -Name '{name}' -StartupType Disabled -ErrorAction SilentlyContinue", 60)


# ---------------- startup ----------------
_DEMO_STARTUP = [
    {"name": "Discord", "command": r"C:\Users\Alex\AppData\Local\Discord\Update.exe --processStart Discord.exe", "source": "User", "enabled": True},
    {"name": "Steam", "command": r"C:\Program Files (x86)\Steam\steam.exe -silent", "source": "User", "enabled": True},
    {"name": "OneDrive", "command": r"C:\Users\Alex\AppData\Local\Microsoft\OneDrive\OneDrive.exe /background", "source": "User", "enabled": False},
    {"name": "Yandex Browser", "command": r"C:\Users\Alex\AppData\Local\Yandex\YandexBrowser\Application\browser.exe --no-startup-window", "source": "User", "enabled": True},
    {"name": "Spotify", "command": r"C:\Users\Alex\AppData\Roaming\Spotify\Spotify.exe --autostart --minimized", "source": "User", "enabled": True},
    {"name": "RtkAudUService", "command": r"C:\Windows\System32\RtkAudUService64.exe -background", "source": "System", "enabled": True},
    {"name": "SecurityHealth", "command": r"%windir%\system32\SecurityHealthSystray.exe", "source": "System", "enabled": True},
]


def startup_entries() -> list[dict]:
    if not P.IS_WINDOWS:
        return _DEMO_STARTUP
    script = r'''
$out=@()
$srcs=@(@{N='User';R='HKCU:\Software\Microsoft\Windows\CurrentVersion\Run';A='HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run'},
       @{N='System';R='HKLM:\Software\Microsoft\Windows\CurrentVersion\Run';A='HKLM:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run'},
       @{N='System32';R='HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run';A='HKLM:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run32'})
foreach($s in $srcs){ if(-not (Test-Path $s.R)){continue}
  foreach($p in (Get-ItemProperty $s.R).PSObject.Properties){ if($p.Name -like 'PS*'){continue}
    $en=$true; try{$b=(Get-ItemProperty -Path $s.A -Name $p.Name -ErrorAction Stop).($p.Name); if($b -and $b[0] -eq 3){$en=$false}}catch{}
    $out+=@{name=$p.Name;command=[string]$p.Value;source=$s.N;approved=$s.A;enabled=$en} } }
$sf=[Environment]::GetFolderPath('Startup'); $sa='HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder'
if(Test-Path $sf){ foreach($f in (Get-ChildItem $sf -File | ? Name -ne 'desktop.ini')){ $en=$true; try{$b=(Get-ItemProperty -Path $sa -Name $f.Name -ErrorAction Stop).($f.Name); if($b -and $b[0] -eq 3){$en=$false}}catch{}
  $out+=@{name=$f.Name;command=$f.FullName;source='Folder';approved=$sa;enabled=$en} } }
,$out'''
    data = P.ps_json(script, 60)
    return data if isinstance(data, list) else []


def _split_ps_path(ps_path: str) -> tuple[str, str]:
    """'HKLM:\\Software\\...' -> ('HKLM', 'Software\\...')"""
    root, _, rest = ps_path.partition(":\\")
    return root.upper(), rest


def set_startup(entry: dict, enabled: bool) -> None:
    """Same switch as Task Manager: StartupApproved value, first byte 02 = enabled, 03 = disabled.
    Raises PermissionError when Windows refuses (system-wide entries need administrator rights)."""
    if not P.IS_WINDOWS:
        entry["enabled"] = enabled
        return
    root, path = _split_ps_path(entry["approved"])
    value = bytes([2 if enabled else 3]) + bytes(11)
    reg_set(root, path, entry["name"], value)
    got = reg_get(root, path, entry["name"])
    if not got or got[0] != value[0]:
        raise PermissionError(5, f"{root}\\{path}\\{entry['name']}")
    entry["enabled"] = enabled


# ---------------- visual effects ----------------
def visual_fx_mode() -> str:
    """perf / balanced / pretty"""
    if not P.IS_WINDOWS:
        return "balanced"
    v = reg_get(HKCU, r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", "VisualFXSetting")
    return {2: "perf", 1: "pretty", 3: "balanced"}.get(v, "balanced")


def set_visual_fx(mode: str) -> None:
    if not P.IS_WINDOWS:
        return
    if mode == "perf":
        reg_set(HKCU, r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", "VisualFXSetting", 2)
        reg_set(HKCU, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "EnableTransparency", 0)
        reg_set(HKCU, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "TaskbarAnimations", 0)
        P.powershell(r"Set-ItemProperty 'HKCU:\Control Panel\Desktop\WindowMetrics' MinAnimate '0'; Set-ItemProperty 'HKCU:\Control Panel\Desktop' UserPreferencesMask ([byte[]](0x90,0x12,0x03,0x80,0x10,0x00,0x00,0x00))", 30)
    elif mode == "pretty":
        reg_set(HKCU, r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", "VisualFXSetting", 1)
        reg_set(HKCU, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "EnableTransparency", 1)
        reg_set(HKCU, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "TaskbarAnimations", 1)
        P.powershell(r"Set-ItemProperty 'HKCU:\Control Panel\Desktop\WindowMetrics' MinAnimate '1'; Set-ItemProperty 'HKCU:\Control Panel\Desktop' UserPreferencesMask ([byte[]](0x9E,0x3E,0x07,0x80,0x12,0x00,0x00,0x00))", 30)
    else:
        reg_set(HKCU, r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", "VisualFXSetting", 3)
        reg_set(HKCU, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "EnableTransparency", 0)
        reg_set(HKCU, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "TaskbarAnimations", 1)
        P.powershell(r"Set-ItemProperty 'HKCU:\Control Panel\Desktop\WindowMetrics' MinAnimate '1'; Set-ItemProperty 'HKCU:\Control Panel\Desktop' UserPreferencesMask ([byte[]](0x90,0x32,0x07,0x80,0x12,0x00,0x00,0x00))", 30)
    # ask Explorer to apply without logoff
    P.powershell("RUNDLL32.EXE user32.dll,UpdatePerUserSystemParameters 1, True", 30)


# ---------------- power plan ----------------
HIGH_PERF = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
BALANCED = "381b4222-f694-41f0-9685-ff5bb260df2e"


def power_plan() -> str:
    if not P.IS_WINDOWS:
        return "balanced"
    out = P.powershell("powercfg /getactivescheme", 20).lower()
    return "high" if HIGH_PERF in out else "balanced"


def set_power_plan(plan: str) -> None:
    if not P.IS_WINDOWS:
        return
    P.powershell(f"powercfg /setactive {HIGH_PERF if plan == 'high' else BALANCED}", 20)


# ---------------- schedule ----------------
TASK = "Sweep Auto Clean"


def schedule_state() -> dict:
    if not P.IS_WINDOWS:
        return {"enabled": False, "next": ""}
    out = P.ps_json(f"$t=Get-ScheduledTask -TaskName '{TASK}' -ErrorAction SilentlyContinue; if($t){{$i=Get-ScheduledTaskInfo -TaskName '{TASK}'; @{{enabled=$true;next=[string]$i.NextRunTime}}}}else{{@{{enabled=$false;next=''}}}}", 30)
    return out or {"enabled": False, "next": ""}


def set_schedule(enabled: bool, exe: str) -> None:
    if not P.IS_WINDOWS:
        return
    if enabled:
        P.powershell(
            f"$a=New-ScheduledTaskAction -Execute '{exe}' -Argument '--auto'; $tr=New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 12:00; "
            f"$s=New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30); "
            f"Register-ScheduledTask -TaskName '{TASK}' -Action $a -Trigger $tr -Settings $s -RunLevel Highest -User $env:USERNAME -Force | Out-Null", 60)
    else:
        P.powershell(f"Unregister-ScheduledTask -TaskName '{TASK}' -Confirm:$false -ErrorAction SilentlyContinue", 30)
