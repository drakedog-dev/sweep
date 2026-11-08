# Changelog

All notable changes to Sweep. The newest version is at the top; the in-app update dialog and the GitHub release notes are built from this file.

## 1.0.25
- Checking for a new Sweep version works on networks that cut the connection to api.github.com or share one address among many users (GitHub allows 60 API checks an hour per address): Sweep then reads the latest release from github.com itself and takes the installer's SHA-256 from SHA256SUMS.txt

## 1.0.24
- Sweep's own update no longer pops up or starts while programs are updating or installing, or while Sweep cleans: it waits until the task is done. "Update" pressed meanwhile installs Sweep right after it
- The download of a new Sweep version survives a dropped connection: it continues where it stopped, up to five tries, instead of failing with "connection closed"
- The downloaded installer is started only when its SHA-256 matches the one published with the release
- Clear messages instead of raw errors when GitHub cannot be reached or limits update checks, with the download progress in percent
- Program updates and installs: a dropped connection or a busy vendor server (for example HTTP 504 from GitHub, where 7-Zip and many others are hosted) gets one more try a few seconds later, and is then reported as a connection or server problem instead of "Installer error"

## 1.0.23
- Program updates: the ticks next to "Catalogue" and "Sources" no longer stand crooked after the check moves on
- Temp files are cleaned only when older than a day, so an installer or program that is running keeps what it unpacked today
- Files Windows will replace at the next restart are never moved, and the Windows Update cache stays while an update is installing or waits for a restart
- Junk on drives: temp files and unfinished downloads from today are kept, and program data (AppData, browser and app databases) is no longer searched, so a database journal is never taken for an old log
- Recent-file lists are your history, not errors: they are not ticked on the Registry page and "Clean what was found" leaves them alone
- Removing Xbox Game Bar also switches game capture off, so Windows no longer asks for an app to open "ms-gamingoverlay" links
- Built-in Windows apps: an app set to open links (new Outlook for mail, say) is marked too; Teams, Xbox and Outlook say when to keep them

## 1.0.22
- Overview: one "Analyze" button checks junk, junk on every drive, the registry, startup, privacy and program updates, with a result row for each that opens its page. Nothing runs until you press it
- "Clean what was found" moves the ticked junk and drive junk to quarantine and fixes the registry problems with a backup and a restore point; startup, privacy and updates are only shown, never changed by it
- Cleaning keeps the programs you chose to open videos, photos and documents. The thumbnail cache no longer takes the icon cache with it, so file icons do not turn blank or wrong until a restart
- MuiCache loses only the names of programs that are gone, so "Open with" and Default apps keep their program names
- Microsoft Store app aliases and plain commands such as rundll32.exe are no longer taken for missing files in App Paths and startup entries
- Built-in Windows apps: an app that opens some file types now (Media Player for videos, say) is marked with those types, because removing it makes Windows forget that choice
- Guard never removes an app you picked again to open files, and stops watching it
- Disks: a drive's Recycle Bin is no longer ticked by default, like the Recycle Bin on the Junk page
- Registry page: backup labels show the date instead of "{0}"

## 1.0.21
- Startup is read again every time you open the page, come back to Sweep's window or press "Scan again": programs that add themselves while Sweep is open now show up, marked "new"
- Startup shows everything Task Manager shows: Microsoft Store apps (new Teams, Spotify and others) and the all-users Startup folder join the Run keys and your own Startup folder
- Startup states are read like Task Manager reads them, so items switched off elsewhere no longer look switched on; entries whose name starts with "PS" are no longer dropped
- Nothing is checked by itself at start: system facts are read quietly in the background and junk is measured only when you press Check
- Quarantine and registry backups can be deleted one by one; "Delete everything" also removes registry, task and service backups
- After an uninstall, "All works, delete the copies" removes the program's last traces; copies older than 30 days go by themselves (can be turned off in Settings)
- Leftover registry keys that an installer locked against deletion are unlocked, backed up in full and removed; system keys are never touched
- Read-only files in quarantine are deleted too
- Started from a PowerShell 7 window, Sweep no longer loses PowerShell features such as scheduled tasks and permissions

## 1.0.20
Bug fixes and polish, nothing new.
- Russian Windows: startup entries, folders and program paths with Cyrillic names are read correctly, so their switches work (PowerShell answered in the console code page)
- Quarantine: restoring never deletes what could not be put back; such files stay in the quarantine
- Uninstall leftovers that are locked keep a copy in quarantine before they are removed at the next restart
- Scheduled tasks removed with a program come back with the rest of its backup on the Registry page
- Junk cleaning never reaches outside known folders, even when a Windows folder variable is empty
- The drive scan no longer follows links into other folders and drives
- One task at a time: a second click while Sweep works shows a hint instead of starting a parallel job
- Numbers in Russian use a decimal comma (4,7 ГБ, 29,4 с); big sizes have no ".0"
- Nothing is cut or runs out of its card in a narrow window: Programs tabs, Overview, Boost buttons, Disks, About buttons, Boot chart labels
- Settings and About describe correctly when Sweep goes online
- Restore points: the Windows frequency limit is always put back
- No console window flashes while leftovers are removed

## 1.0.19
- Store apps (App Installer, Teams, ChatGPT, Claude and others) show their own logo in the updates list
- An "open" badge on programs that are running right now: an open program often cannot be replaced by its installer
- When an update leaves the version unchanged, the row says why (for example, the program was open), stays in the list and can be updated again with one click
- The update counter and the badges count only updates that surely belong to your programs; look-alikes are shown but not counted
- Look-alikes are named without the version: "FlClashX" instead of "FlClashX, версия 0.4.2"

## 1.0.18
- Program updates: nothing is ticked by itself any more. Tick what you want and press "Update selected", or take everything with "Update all"
- A progress bar with a percentage while Sweep looks for updates, in three steps: the winget catalogue, the sources, the final check
- Every update shows a percentage for its download and install, and the queue shows an overall one
- Correct versions: winget's tables are read in full, so no name, id or version is cut short; where winget only knows "older than 3.14.7", Sweep shows the real version from Windows
- After an update Sweep reads the installed version again and shows "Updated to x.y"; if the version did not change, it says so
- Forks and look-alikes are caught: when the catalogue entry is another program (FlClash X was offered FlClash by another author), the row is marked and cannot be ticked; "Same program" overrides it if you are sure
- "Package not found" fixed: when winget lists an update but then does not see the program installed, Sweep installs the new version over the old one, as long as Windows still lists the program
- What's new: the release notes of each update, straight from the catalogue
- New Install tab on the Programs page: 45 popular free programs by category, ready-made sets (fresh Windows, gaming, work) and a search through the whole winget catalogue, with the same live progress and SHA-256 check
- Terms of use and the privacy policy describe catalogue search and installs, so they are shown once more for your consent

## 1.0.17
- Program updates: a selection bar above the list with a select-all checkbox, "All", "All but major" and "None", and a counter of selected programs
- Click anywhere on a program's row to tick or untick it
- "Update selected" installs the ticked programs one after another, and each waiting program shows its place in the queue
- Live progress for every update: a bar with the megabytes downloaded, the total size and the speed, then an installing stage, so it is always clear that Sweep is working. winget now runs inside a hidden pseudo console, the only way it reports its download as it happens
- The window title bar follows Sweep's theme: dark in the dark theme and light in the light one (exact colours on Windows 11, a dark frame on Windows 10)
- The project moved to github.com/drakedog-dev/sweep; Sweep checks for its own updates at the new address
- Build tools updated (GitHub Actions on Node 24)

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
