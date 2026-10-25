# Changelog

All notable changes to Sweep. The newest version is at the top; the in-app update dialog and the GitHub release notes are built from this file.

## 1.0.17
- Program updates: a selection bar above the list with a select-all checkbox, "All", "All but major" and "None", and a counter of selected programs
- Click anywhere on a program's row to tick or untick it
- "Update selected" installs the ticked programs one after another, and each waiting program shows its place in the queue
- Live progress for every update: a bar with the megabytes downloaded, the total size and the speed, then an installing stage, so it is always clear that Sweep is working
- The window title bar follows Sweep's theme: dark in the dark theme and light in the light one (exact colours on Windows 11, a dark frame on Windows 10)

## 1.0.16
- Program updates: a new Updates tab on the Programs page finds installed programs that have a newer version, using winget, the package manager built into Windows 10 and 11
- Every update shows where the installer comes from (7-zip.org, videolan.org, github.com/notepad-plus-plus and so on) and is checked against its SHA-256 before it runs
- Update the ticked programs one by one or a single program with its own button; major upgrades are not ticked by default, any program can be hidden, and a restore point is created first
- Optional daily check with a counter on the Programs item in the sidebar and a tip on the Overview; nothing is installed without your click
- Uninstalling Sweep now also removes its scheduled tasks (Guard and the weekly clean)
- Terms of use and the privacy policy describe the new winget connections, so they are shown once more for your consent
- New repository look: redesigned README, privacy policy, security policy, contribution guide, issue forms, and a Linux pipeline with lint, unit tests and an interface test next to the Windows self-test
- Release pages now list the SHA-256 of the installer

## 1.0.15
- Programs: a thorough uninstaller that lists every installed program with its real icon, size, publisher and install date, with search and sorting
- Runs the program's own uninstaller (quietly when it supports it), waits for it to finish, then finds what it left behind in program folders, AppData, ProgramData, the registry, shortcuts, Run entries, scheduled tasks and services
- Force mode for programs whose uninstaller is broken, missing or refuses to work; locked files are removed at the next restart
- Only items that surely belong to the program are ticked; files go to quarantine, registry keys, tasks and services are backed up, and a restore point is created first
- Built-in Windows apps moved to a second tab of the same page
- Every page of the released build is opened automatically before publishing, and the Windows self-test uninstalls a test program end to end

## 1.0.14
- Boot X-ray: how long Windows takes to start, split into "until the desktop" and "after sign-in", a chart of recent boots and what slows them down in seconds, straight from Windows' own diagnostics log
- Remove a boot culprit from startup in one click, then restart and watch the new bar show the seconds you saved
- Guard: big Windows updates often switch tracking back on and reinstall promoted apps; Guard checks after sign-in and once a day, notifies you or puts everything back by itself, and keeps a history
- A Windows restore point is created before big changes (at most once a day; can be turned off in Settings)
- Overview shows the last boot time; confirmation before restarting the PC

## 1.0.13
- Privacy switches now work like Windows Settings: on means the Windows feature (tracking, ads, suggestions) is active, off means it is disabled
- New version reminder that lists what changed, with Update, Remind me later and Skip this version
- Settings: choose how new versions arrive (ask me, install automatically or do not check)
- What's new window after every update
- Terms of use on first start and in the installer
- Release notes are now published from this changelog

## 1.0.12
- One consistent icon set across the menu, tiles and lists
- Cleaner light theme with a light status bar and clearly visible switches
- Overview: tiles of equal height with disk and startup bars, quick actions for tracking, memory and drives
- Real video memory size for modern graphics cards (Windows reports at most 4 GB)
- Complete Russian translation of startup sources, CPU details and accent colours

## 1.0.11
- Prepared for free code signing by SignPath Foundation; product name and version in file properties
- The privacy warning appears only when an item really stayed on

## 1.0.10
- Recognises an antivirus blocking privacy changes and explains how to add Sweep to Kaspersky trusted applications

## 1.0.9
- Open log button on the Privacy and Settings pages

## 1.0.8
- Every privacy change is verified after writing; the log records what was written, what was read back and the installed antivirus

## 1.0.7
- Asks for administrator rights when needed and continues the action after the UAC prompt
- Privacy items are applied one by one and the real state is read back afterwards
- Browser history cleaning for Chrome, Edge, Yandex, Brave, Vivaldi, Opera and Firefox; passwords, bookmarks, autofill and open tabs are kept
- The interface is always drawn by the CPU, so the mouse cursor and games stay smooth

## 1.0.6
- Automatic update check on start

## 1.0.0
- Full rewrite in Python and Qt Quick: new interface, PC profile with adaptive recommendations, live monitors, quarantine, English and Russian
