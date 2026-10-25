"""Programs Sweep offers to install in one click: popular, free, from the vendors' own sites through winget.
Descriptions live in i18n.py as "ins.d.<key>", category names as "ins.cat.<category>"."""
from __future__ import annotations

import re

# (category, icon) in the order they are shown
CATEGORIES = [
    ("browsers", "globe"), ("chat", "messages-square"), ("media", "clapperboard"), ("office", "file-text"), ("tools", "wrench"),
    ("security", "shield-check"), ("games", "gamepad-2"), ("dev", "code"), ("runtimes", "puzzle"),
]

# (winget id, name, category)
PROGRAMS = [
    ("Google.Chrome", "Google Chrome", "browsers"),
    ("Mozilla.Firefox", "Firefox", "browsers"),
    ("Yandex.Browser", "Яндекс Браузер", "browsers"),
    ("Brave.Brave", "Brave", "browsers"),
    ("Opera.Opera", "Opera", "browsers"),
    ("Telegram.TelegramDesktop", "Telegram", "chat"),
    ("Discord.Discord", "Discord", "chat"),
    ("Zoom.Zoom", "Zoom", "chat"),
    ("Rakuten.Viber", "Viber", "chat"),
    ("VideoLAN.VLC", "VLC", "media"),
    ("Daum.PotPlayer", "PotPlayer", "media"),
    ("AIMP.AIMP", "AIMP", "media"),
    ("OBSProject.OBSStudio", "OBS Studio", "media"),
    ("Audacity.Audacity", "Audacity", "media"),
    ("HandBrake.HandBrake", "HandBrake", "media"),
    ("TheDocumentFoundation.LibreOffice", "LibreOffice", "office"),
    ("ONLYOFFICE.DesktopEditors", "ONLYOFFICE", "office"),
    ("SumatraPDF.SumatraPDF", "SumatraPDF", "office"),
    ("Adobe.Acrobat.Reader.64-bit", "Acrobat Reader", "office"),
    ("Notepad++.Notepad++", "Notepad++", "office"),
    ("Obsidian.Obsidian", "Obsidian", "office"),
    ("7zip.7zip", "7-Zip", "tools"),
    ("RARLab.WinRAR", "WinRAR", "tools"),
    ("voidtools.Everything", "Everything", "tools"),
    ("ShareX.ShareX", "ShareX", "tools"),
    ("Microsoft.PowerToys", "PowerToys", "tools"),
    ("qBittorrent.qBittorrent", "qBittorrent", "tools"),
    ("Rufus.Rufus", "Rufus", "tools"),
    ("CrystalDewWorld.CrystalDiskInfo", "CrystalDiskInfo", "tools"),
    ("CPUID.CPU-Z", "CPU-Z", "tools"),
    ("AnyDesk.AnyDesk", "AnyDesk", "tools"),
    ("KeePassXCTeam.KeePassXC", "KeePassXC", "security"),
    ("Bitwarden.Bitwarden", "Bitwarden", "security"),
    ("Malwarebytes.Malwarebytes", "Malwarebytes", "security"),
    ("Valve.Steam", "Steam", "games"),
    ("EpicGames.EpicGamesLauncher", "Epic Games", "games"),
    ("GOG.Galaxy", "GOG Galaxy", "games"),
    ("Microsoft.VisualStudioCode", "VS Code", "dev"),
    ("Git.Git", "Git", "dev"),
    ("Python.Python.3.14", "Python 3.14", "dev"),
    ("OpenJS.NodeJS.LTS", "Node.js LTS", "dev"),
    ("Microsoft.VCRedist.2015+.x64", "Visual C++ 2015-2022", "runtimes"),
    ("Microsoft.DotNet.DesktopRuntime.8", ".NET Desktop Runtime 8", "runtimes"),
    ("Microsoft.DirectX", "DirectX", "runtimes"),
    ("Oracle.JavaRuntimeEnvironment", "Java", "runtimes"),
]

# ready-made sets: everything a fresh Windows usually needs, a gaming PC, a work PC
PRESETS = {
    "basics": ["Google.Chrome", "7zip.7zip", "VideoLAN.VLC", "Telegram.TelegramDesktop", "SumatraPDF.SumatraPDF",
               "Microsoft.VCRedist.2015+.x64", "Microsoft.DotNet.DesktopRuntime.8"],
    "games": ["Valve.Steam", "EpicGames.EpicGamesLauncher", "Discord.Discord", "Microsoft.VCRedist.2015+.x64", "Microsoft.DirectX"],
    "work": ["ONLYOFFICE.DesktopEditors", "Zoom.Zoom", "Telegram.TelegramDesktop", "Notepad++.Notepad++", "ShareX.ShareX", "voidtools.Everything"],
}


def key(pid: str) -> str:
    """i18n key part for a package id: Notepad++.Notepad++ -> notepadnotepad."""
    return re.sub(r"[^a-z0-9]+", "", pid.lower())


IDS = {p[0] for p in PROGRAMS}
