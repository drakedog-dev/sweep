# Contributing to Sweep

Thanks for helping. Bug reports, translations, ideas and pull requests are all welcome.

## Ground rules

Sweep changes real Windows systems, so every contribution follows the same four rules:

1. **Nothing happens without the user's click.** No silent changes, no background actions the user did not turn on.
2. **Everything can be undone.** Files go to quarantine, registry keys are exported first, switches flip back.
3. **No telemetry, ever.** No analytics, no tracking, no new network connections without a clear reason in the interface and in [PRIVACY.md](PRIVACY.md).
4. **Never touch user data.** Documents, photos, passwords, licences and bookmarks are off limits.

## Getting started

```powershell
git clone https://github.com/drakedog-dev/sweep.git
cd sweep
pip install -r app/requirements.txt
python app/main.py
```

On Linux and macOS Sweep runs in **demo mode** with sample data. This is the fastest way to work on the interface.

## Project layout

| Path | What lives there |
|---|---|
| `app/main.py` | Entry point: UAC prompt, `--auto`, `--guard`, `--ui-test` |
| `app/sweep/` | All logic in plain Python, one module per feature (`cleaner`, `tweaks`, `uninstall`, `updates`, `guard`, `boot`, `extras`) |
| `app/sweep/bridge.py` | The `App` object that QML talks to: properties, slots, worker threads |
| `app/sweep/i18n.py` | Every interface string in English and Russian |
| `app/qml/` | The interface: `Main.qml`, `pages/`, `components/`, `Sweep/Theme.qml` |
| `app/tests/` | Unit tests and the Windows self-test |
| `tools/` | Helper scripts, for example `make_icon_font.py` for new Lucide icons |

## Making a change

- **Strings:** add a key to `app/sweep/i18n.py` with both `ru` and `en`. Never hard-code text in QML.
- **Icons:** add the Lucide name to the `icons` map in `Theme.qml`, then run `python tools/make_icon_font.py <lucide-static>/font`.
- **Long operations** run in a worker thread through `App._run` (blocks other actions) or `App._bg` (does not).
- **Windows calls** go through `platform.py` helpers (`powershell`, `ps_json`, `log`) and must have demo data for non-Windows systems.
- **Changelog:** add a line to the top section of [CHANGELOG.md](CHANGELOG.md) in English. The in-app "What's new" dialog and the GitHub release notes are built from it.

## Checks

Run these before opening a pull request:

```powershell
pip install ruff
ruff check app tools                              # style and common mistakes
python app/tests/test_updates.py                  # unit tests
python app/main.py --ui-test --no-elevate         # every page; fails on any QML warning
```

GitHub Actions runs the same checks on Linux, then a full self-test on a real Windows machine (`app/tests/selftest.py`) that changes and restores real settings. Do not run the self-test on your own PC unless you understand what it does.

## Releases

A release is published automatically when `APP_VERSION` in `app/sweep/platform.py` changes on `main`: PyInstaller builds the app, Inno Setup packs the installer, the packaged app opens every page as a smoke test, and the release notes come from `CHANGELOG.md`.

## Pull requests

- Keep each pull request to one topic.
- Describe what changed and how you tested it; screenshots help for interface changes.
- By contributing you agree that your work is released under the [MIT licence](LICENSE).
