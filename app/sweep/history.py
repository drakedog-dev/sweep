"""A plain record of what Sweep did and when: cleaning, registry fixes, programs updated or removed, switches changed.

It only remembers; undoing is done by what already exists (quarantine sessions, .reg backups), found by the session name
stored with the entry. The file stays on this PC, next to the settings.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta

from . import platform as P

FILE = P.ROOT / "history.json"
KEEP = 300
_lock = threading.Lock()


def load() -> list[dict]:
    """Newest first."""
    try:
        rows = json.loads(FILE.read_text("utf-8"))
        return [r for r in rows if isinstance(r, dict) and r.get("t") and r.get("kind")]
    except (OSError, ValueError):
        return []


def add(kind: str, **fields) -> dict:
    """Remember one action. Never raises: a history that cannot be written must not break the action itself."""
    row = {"t": datetime.now().isoformat(timespec="seconds"), "kind": kind, **{k: v for k, v in fields.items() if v not in (None, "", [])}}
    with _lock:
        try:
            rows = [row] + load()
            FILE.write_text(json.dumps(rows[:KEEP], ensure_ascii=False, indent=1), "utf-8")
        except OSError as e:
            P.log(f"history: not saved: {e!r}")
    return row


def clear() -> None:
    with _lock:
        try:
            FILE.unlink(missing_ok=True)
        except OSError as e:
            P.log(f"history: not cleared: {e!r}")


def demo() -> list[dict]:
    """Sample entries for the demo mode on Linux and macOS."""
    now = datetime.now().replace(minute=10, second=0)

    def ago(days, hours=0):
        return (now - timedelta(days=days, hours=hours)).isoformat(timespec="seconds")
    return [
        {"t": ago(0, 2), "kind": "found", "freed": 4.7 * 2**30, "n": 28, "session": "demo1"},
        {"t": ago(0, 3), "kind": "updates", "n": 6, "names": ["PowerShell", "Git", "Telegram Desktop", "7-Zip", "VLC media player", "Notepad++"]},
        {"t": ago(1), "kind": "startup", "what": "Discord", "on": False},
        {"t": ago(2), "kind": "uninstall", "what": "McAfee WebAdvisor", "freed": 310 * 2**20, "n": 41},
        {"t": ago(3), "kind": "privacy", "n": 12, "on": True},
        {"t": ago(6), "kind": "clean", "freed": 640 * 2**20, "session": "demo2"},
    ]
