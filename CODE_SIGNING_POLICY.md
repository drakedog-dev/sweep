# Code signing policy

Windows releases of Sweep (`Sweep.exe` and `Sweep-Setup-x.y.z.exe`) are being prepared for free code signing provided by [SignPath.io](https://about.signpath.io/), certificate by [SignPath Foundation](https://signpath.org/). Until the project is approved, releases are published unsigned.

## How releases are built and signed

- Every release is built from the source code in this repository by GitHub Actions on GitHub-hosted runners (`.github/workflows/release.yml`): PyInstaller produces `Sweep.exe`, Inno Setup produces the installer.
- Only these CI-built files are submitted to SignPath. Nothing built on a personal computer is ever signed.
- Each signing request is approved manually by an approver listed below.
- Only Sweep's own executables are signed. Third-party libraries (Python, Qt and others) are shipped as they are.

## Team roles

| Role | Members |
|---|---|
| Committers and reviewers | [Alex (Drakedog), GitHub: pabloescobarbl-ops](https://github.com/pabloescobarbl-ops) |
| Approvers | [Alex (Drakedog), GitHub: pabloescobarbl-ops](https://github.com/pabloescobarbl-ops) |

Multi-factor authentication is enabled for all team members on GitHub and SignPath.

## Privacy policy

Sweep does not collect, store or send personal data, usage statistics or telemetry.

The only network connections Sweep makes are to `api.github.com` and `github.com`, to check for and download new Sweep releases:
- on start-up, which can be turned off in **Settings → Updates → New versions → Do not check**;
- when you press **Check for updates**.

This program will not transfer any other information to other networked systems unless specifically requested by the user or the person installing or operating it.

## System changes

Sweep changes Windows settings only when you press a button or flip a switch, and every change is described next to that switch. Deleted files go to a quarantine folder and can be restored; registry keys are backed up before cleaning; privacy switches and services can be switched back. Sweep is removed with the standard uninstaller (Settings → Apps in Windows).
