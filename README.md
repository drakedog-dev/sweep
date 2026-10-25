# Sweep

Clean, de-bloat and speed up Windows in one click. Free, open source, works offline.

Windows 10 and 11. Sweep never connects to the internet except when you press "Check for updates".

[Русская версия](README.ru.md)

## Download

Grab `Sweep-Setup-x.y.exe` from the [latest release](../../releases/latest) and run it. A portable `Sweep.exe` is attached too if you prefer no installation.

Windows SmartScreen may warn about an unknown publisher because the build is not code-signed yet. Click **More info**, then **Run anyway**. The full source is in this repository: the whole program is one file, `Sweep.ps1`.

## What it does

**Overview.** A health index (0 to 100) with concrete tips, disk and memory at a glance, and a one-click quick clean.

**Junk.** Shows how much space each category takes and removes only what you tick:
temp folders, Recycle Bin, thumbnail cache, Windows Update cache, crash dumps and error reports, old Windows logs, browser caches (Chrome, Edge, Yandex, Brave, Vivaldi, Opera, Firefox) and, optionally, cookies.

**Privacy.** 17 switches in three groups: data collection (telemetry, advertising ID, activity history, error reporting), ads and suggestions (Start menu, lock screen, Explorer, search box, news and widgets, "what's new" screen), Microsoft assistants (Cortana, Copilot, Edge telemetry). Every switch can be flipped back.

**Registry.** Safe categories only: recent-file lists, MuiCache, App Paths and Run entries pointing to deleted programs. Every key is exported to a `.reg` file before it is touched, and a **Restore** button imports it back.

**Services.** Twelve services that slow down older PCs (SysMain, Windows Search indexing, Xbox services, Maps, Fax, Remote Registry and more). The original startup type is remembered, so everything is reversible.

**Startup.** What launches with Windows, with a switch per entry. Nothing is deleted.

**Boost.** Free RAM, optimise drives (TRIM for SSD, defrag for HDD), open Windows Update, and a weekly **scheduled auto-clean** that runs silently.

**Disks.** Usage bar per drive and a finder for the largest files outside system folders, with one-click move to quarantine.

**Apps.** Pre-installed Microsoft and partner apps most people never use (Xbox, Solitaire, News, Weather, Office Hub, Candy Crush and so on). Remove what you tick; anything can be reinstalled from Microsoft Store.

**System.** Windows build, CPU, GPU, motherboard, BIOS, RAM modules, disks, uptime, temperatures where Windows exposes them. Copy as text.

**Quarantine.** Nothing is deleted outright. Files are moved to `ProgramData\Sweep\Quarantine`, and **Restore** puts them back. Purge the quarantine yourself when you are sure.

Dark and light themes, English and Russian interface (switch in the sidebar). Resizable, full-screen friendly.

## Safety rules

- Files are moved, not deleted. Only the Recycle Bin is emptied for real, and it is off by default.
- Documents, photos, programs and licences are never touched.
- Privacy switches and services are reversible with the same switch.
- Registry cleaning backs up every key first.
- Files in use are skipped.

## Building from source

Releases are built automatically by GitHub Actions on every `v*` tag (see `.github/workflows/release.yml`): `Sweep.exe` via ps2exe and the installer via Inno Setup.

To build locally on Windows: run `build-exe.bat`, then install [Inno Setup 6](https://jrsoftware.org/isdl.php) and run `build-setup.bat`. See `INSTRUCTIONS.md`.

To run without building: `Start.bat` (asks for administrator rights). `Debug.bat` keeps the console open to show errors.

## Command line

`Sweep.exe -auto` runs a silent clean with default categories and exits. This is what the scheduled task uses.

## License

MIT.
