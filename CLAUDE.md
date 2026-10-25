# Sweep: working notes for Claude

Sweep is a free, open-source (MIT) Windows 10/11 cleaner and optimiser: Python 3.12, PySide6 6.8 with a QML interface drawn by the CPU (`QT_QUICK_BACKEND=software`). Maintainer: Alex (Drakedog), GitHub `drakedog-dev`.

## Talking to the maintainer

- Reply in Russian. Be direct and concrete; give copy-paste-ready results.
- No em dashes in any text written for him or for users (UI strings, README, changelog, messages).
- The changelog, release notes and code comments are in English.

## Where things are

| Path | What |
|---|---|
| `app/main.py` | Entry point: UAC, `--auto`, `--guard`, `--ui-test`, themed title bar |
| `app/sweep/bridge.py` | `App` QObject: every property and slot QML uses; `_run` (busy) and `_bg` (not busy) workers |
| `app/sweep/*.py` | One module per feature: `cleaner`, `tweaks` (privacy, services, startup), `uninstall`, `updates` (winget: scan, look-alike check, upgrade, install, search), `catalog` (programs offered on the Install tab), `conpty` (pseudo console for live winget progress), `guard`, `boot`, `extras`, `winframe` |
| `app/sweep/i18n.py` | All UI strings, `ru` and `en` |
| `app/qml/` | `Main.qml`, `pages/`, `components/`, `Sweep/Theme.qml` (colours, Lucide icon map) |
| `app/tests/` | `test_updates.py` (runs anywhere), `selftest.py` (Windows only, changes and restores real settings) |
| `tools/` | `make_icon_font.py` (Lucide subset), `ci_report.py` (CI reports as git notes) |

## Run and check

```bash
pip install -r app/requirements.txt ruff
python app/main.py                                # Linux/macOS: demo mode with sample data
QT_QPA_PLATFORM=offscreen python app/main.py --ui-test --no-elevate   # every page, fails on any QML warning
python app/tests/test_updates.py
ruff check app tools
```

## Rules for every change

- Nothing happens without the user's click; everything is reversible (quarantine, `.reg` backups, restore point before big changes).
- No telemetry. A new network connection must be described in `PRIVACY.md`, `app/installer/terms-*.txt` and `terms.4`, and `TERMS_VERSION` in `bridge.py` is raised so users accept again.
- Never touch Windows activation or licensing.
- New strings go to `i18n.py` in both languages; new icons go to the `icons` map in `Theme.qml`, then run `tools/make_icon_font.py`.
- Every Windows call needs demo data for non-Windows systems.

## Releases

- A release is built when `APP_VERSION` in `app/sweep/platform.py` changes on `main` (keep `pyproject.toml` in step). Release notes come from the matching `## x.y.z` section of `CHANGELOG.md`.
- Push code changes first without a version bump, let the Windows self-test pass, then bump the version in a second commit.
- Code signing through SignPath Foundation is prepared in `release.yml` and switches on once `SIGNPATH_API_TOKEN` and `SIGNPATH_ORGANIZATION_ID` exist. The application has not been sent yet.

## Reading CI results

Every workflow attaches a report to the tested commit as a git note, so results can be read with git alone:

```bash
git fetch origin "+refs/notes/*:refs/notes/*"
git notes --ref=selftest show HEAD     # Windows self-test: all checks, winget, title bar, log tail
git notes --ref=build show HEAD        # release build: version, release notes, smoke test
git notes --ref=lint show HEAD         # Linux: ruff, unit tests, demo UI test
```

## Good to know

- The repository was renamed from `pabloescobarbl-ops/sweep`. Versions up to 1.0.16 check for updates at the old address and rely on GitHub's redirect, so that name must never be used again.
- Kaspersky puts unsigned programs into a restricted group and silently blocks their registry writes; Sweep detects this and shows a hint.
- winget holds back its progress bar when its output goes to a pipe; `conpty.py` runs it in a hidden pseudo console so the download progress arrives live.
- winget tables (upgrade, search, show, list) are read from a 512-column pseudo console through `updates.vt_screen`, so nothing is shortened with "…"; the pipe is only the fallback.
- winget sometimes links a fork to the original (FlClash X to chen08209.FlClash). `updates.check_identity` compares the installed name and GitHub author with the catalogue; suspect rows cannot be ticked until the user presses "Same program".
- When `winget upgrade` answers NO_APPLICATIONS_FOUND, `updates.upgrade` installs over the old version (only if Windows still lists the program) and then reads the installed version again.
- Open questions: a paid Pro tier (the leaning is open code with a licence key, to stay eligible for SignPath) and the SignPath application.
