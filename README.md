# Sweep

Clean, de-bloat and speed up Windows in one click. Free, open source, works offline.

**Version 1.0** is a full rewrite: a native-feeling Qt interface with smooth animations, live CPU, memory and disk monitors, a **PC profile** that adapts recommendations to weak, mid-range and powerful machines, Windows visual-effects and power-plan presets, English and Russian, dark and light themes with five accent colours.

Windows 10 and 11. Sweep never connects to the internet except when you press "Check for updates".

[Русская версия](README.ru.md)

## Download

Grab `Sweep-Setup-x.y.exe` from the [latest release](../../releases/latest) and run it. A portable `Sweep.exe` is attached too if you prefer no installation.

Windows SmartScreen may warn about an unknown publisher because the build is not code-signed yet. Click **More info**, then **Run anyway**. The full source is in this repository: the whole program is one file, `Sweep.ps1`.

## What it does

**Overview.** A health index (0 to 100) with concrete tips, your PC profile with one-click recommendations, live CPU and memory graphs, disk and startup at a glance, and a quick clean button.

**Junk.** Shows how much space each category takes and removes only what you tick:
temp folders, Recycle Bin, thumbnail cache, Windows Update cache, crash dumps and error reports, old Windows logs, browser caches (Chrome, Edge, Yandex, Brave, Vivaldi, Opera, Firefox) and, optionally, cookies.

**Privacy.** 17 switches in three groups: data collection (telemetry, advertising ID, activity history, error reporting), ads and suggestions (Start menu, lock screen, Explorer, search box, news and widgets, "what's new" screen), Microsoft assistants (Cortana, Copilot, Edge telemetry). Every switch can be flipped back.

**Registry.** Safe categories only: recent-file lists, MuiCache, App Paths and Run entries pointing to deleted programs. Every key is exported to a `.reg` file before it is touched, and a **Restore** button imports it back.

**Services.** Twelve services that slow down older PCs (SysMain, Windows Search indexing, Xbox services, Maps, Fax, Remote Registry and more). The original startup type is remembered, so everything is reversible.

**Startup.** What launches with Windows, with a switch per entry. Nothing is deleted.

**Boost.** Free RAM, optimise drives (TRIM for SSD, defrag for HDD), Windows visual-effects presets (performance, balanced, appearance), power plan, Windows Update, and a weekly **scheduled auto-clean** that runs silently.

**Disks.** Usage bar per drive and a finder for the largest files outside system folders, with one-click move to quarantine.

**Apps.** Pre-installed Microsoft and partner apps most people never use (Xbox, Solitaire, News, Weather, Office Hub, Candy Crush and so on). Remove what you tick; anything can be reinstalled from Microsoft Store.

**System.** Windows build, CPU, GPU, motherboard, BIOS, RAM modules, disks, uptime, temperatures where Windows exposes them. Copy as text.

**Quarantine.** Nothing is deleted outright. Files are moved to `ProgramData\Sweep\Quarantine`, and **Restore** puts them back. Purge the quarantine yourself when you are sure.

**Settings.** English or Russian, dark or light theme, five accent colours, animations on or off, update check.

## Safety rules

- Files are moved, not deleted. Only the Recycle Bin is emptied for real, and it is off by default.
- Documents, photos, programs and licences are never touched.
- Privacy switches and services are reversible with the same switch.
- Registry cleaning backs up every key first.
- Files in use are skipped.

## Building from source

The app lives in `app/`: Python 3.12, PySide6 (Qt 6) with a QML interface, psutil. Run it from source with `python app/main.py` (on Linux or macOS it starts in demo mode with sample data, which is how the interface is developed and screenshotted).

Releases are built automatically by GitHub Actions on every push to `main` (see `.github/workflows/release.yml`): PyInstaller produces `dist/Sweep`, Inno Setup packs the installer, and a tag is created from `APP_VERSION` in `app/sweep/platform.py`.

The original PowerShell version (0.x) is kept in `legacy/`.

## Command line

`Sweep.exe --auto` runs a silent clean with default categories and exits. This is what the scheduled task uses.

## License

MIT.
