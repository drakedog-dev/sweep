# Changelog

All notable changes to Sweep. The newest version is at the top; the in-app update dialog and the GitHub release notes are built from this file.

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
