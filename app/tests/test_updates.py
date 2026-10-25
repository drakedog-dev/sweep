"""Unit tests for reading winget output. Fixtures are real winget 1.11 output captured on a Windows runner,
plus a Russian one in the same shape. Runs anywhere: python app/tests/test_updates.py (or pytest)."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from sweep import updates as U  # noqa: E402

FX = HERE / "fixtures"


def raw(name: str) -> bytes:
    return (FX / name).read_bytes()


def test_upgrade_table_english():
    rows = U.parse_upgrades(raw("winget-upgrade-en.txt"))
    assert len(rows) == 24
    assert rows[0] == {"name": "7-Zip 26.04 (x64)", "id": "7zip.7zip", "version": "26.04", "available": "26.05", "source": "winget"}
    ids = [r["id"] for r in rows]
    assert "Microsoft.VCRedist.2013.x64" in ids and "Anaconda.Miniconda3" in ids
    mini = next(r for r in rows if r["id"] == "Anaconda.Miniconda3")
    assert (mini["version"], mini["available"]) == ("py314_26.9.3-0", "py314_26.9.4-0")
    assert not any("upgrades" in r["name"] for r in rows), "the footer line is not a program"


def test_upgrade_table_with_source_column():
    rows = U.parse_upgrades(raw("winget-upgrade-all-en.txt"))
    assert len(rows) == 24 and all(r["source"] == "winget" for r in rows)
    assert next(r for r in rows if r["id"] == "ImageMagick.ImageMagick")["name"].endswith("…")


def test_upgrade_table_russian_and_second_table():
    rows = U.parse_upgrades(raw("winget-upgrade-ru.txt"))
    ids = [r["id"] for r in rows]
    assert ids == ["7zip.7zip", "Microsoft.VCRedist.2015+.x6…", "Yandex.Browser", "Python.Launcher", "Discord.Discord"], ids
    assert rows[2]["name"] == "Яндекс Браузер"
    assert rows[3]["version"] == "< 3.14.7"


def test_shortened_id_is_repaired():
    rows = U.parse_upgrades(raw("winget-upgrade-ru.txt"))
    U._installed_ids = lambda: {"Microsoft.VCRedist.2015+.x64": "14.38", "Microsoft.VCRedist.2015+.x86": "14.38", "7zip.7zip": "23.01"}
    fixed = U._repair_ids(rows)
    assert "Microsoft.VCRedist.2015+.x64" in [r["id"] for r in fixed]
    assert not any(r["id"].endswith("…") for r in fixed)


def test_nothing_to_upgrade():
    assert U.parse_upgrades(raw("winget-upgrade-none-en.txt")) == []


def test_show():
    d = U.parse_show(raw("winget-show-en.txt"))
    assert d["name"] == "7-Zip"
    assert d["homepage"] == "https://7-zip.org/"
    assert d["installer"] == "https://github.com/ip7z/7zip/releases/download/26.05/7z2605-x64.exe"
    assert d["sha256"] is True
    assert U.host(d["installer"]) == "github.com/ip7z"
    assert U.host("https://www.7-zip.org/a/7z.exe") == "7-zip.org"


def test_progress_noise_is_dropped():
    ls = U.lines(raw("winget-upgrade-one-en.txt"))
    assert "Successfully verified installer hash" in ls and "Successfully installed" in ls
    assert not any("\r" in ln or ("\u2588" in ln and "MB" not in ln) for ln in ls)


def test_live_progress():
    import re
    events = []
    p = U.Progress(lambda *a: events.append(a))
    for part in re.split(r"[\r\n]", raw("winget-upgrade-one-en.txt").decode("utf-8")):
        p.feed(part)
    assert events[0][0] == "download"
    assert events[-1][0] == "install" and abs(events[-1][2] - 1.58 * 2 ** 20) < 1024
    events.clear()
    p = U.Progress(lambda *a: events.append(a))
    for seg in ["\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 https://x/y.exe", "  \u2588\u2588\u2592  1,2 \u041c\u0411 / 4,5 \u041c\u0411", "  \u2588\u2588\u2588  4,5 \u041c\u0411 / 4,5 \u041c\u0411"]:
        p.feed(seg)
    assert [e[0] for e in events] == ["download", "download", "install"]
    assert events[1][1] == 1.2 * 2 ** 20


def test_live_progress_in_a_pseudo_console():
    """Inside ConPTY winget redraws the bar with cursor moves and reports the taskbar percentage (OSC 9;4)."""
    events = []
    p = U.Progress(lambda *a: events.append(a))
    bar = "\u2588\u2592\u2592"
    text = ("\x1b[?25l\x1b]9;4;3;0\x1b\\Found \x1b[96mLLVM\x1b[0m [LLVM.LLVM] Version 23.1.4\r\n"
            "Downloading https://github.com/llvm/x.exe\r\n\x1b]9;4;1;5\x1b\\\x1b[2K\r  " + bar + "  32.0 MB /  639 MB\x1b[1G"
            "\x1b]9;4;1;50\x1b\\\x1b[2K  " + bar + "  320 MB /  639 MB\x1b[1G\x1b]9;4;1;100\x1b\\  " + bar + "  639 MB /  639 MB\r\n"
            "\x1b]9;4;0;0\x1b\\Successfully verified installer hash\r\n")
    for i in range(0, len(text), 7):          # arrives in small, awkward chunks
        p.feed_text(text[i:i + 7])
    p.feed_text("\n")
    phases = [e[0] for e in events]
    assert phases[0] == "download" and phases[-1] == "install"
    assert (32 * 2 ** 20, 639 * 2 ** 20) in [(e[1], e[2]) for e in events]
    assert (320 * 2 ** 20, 639 * 2 ** 20) in [(e[1], e[2]) for e in events]
    events.clear()
    p = U.Progress(lambda *a: events.append(a))   # no megabytes printed: the taskbar percentage is used
    text = "Downloading https://x/y.msi\r\n\x1b]9;4;1;10\x1b\\\x1b]9;4;1;60\x1b\\\x1b]9;4;0;0\x1b\\Installing\r\n"
    for i in range(0, len(text), 5):
        p.feed_text(text[i:i + 5])
    assert [(e[0], e[1]) for e in events] == [("download", 0.0), ("download", 10.0), ("download", 60.0), ("install", 60.0)]


def test_exit_codes():
    assert U.REASONS[0x8A15002B] == "uptodate" and "uptodate" in U.SUCCESS_REASONS
    assert U.REASONS[0x8A150011] == "hash"
    assert U.REASONS[0x8A150101] == "inuse"


if __name__ == "__main__":
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("  ok  ", name)
            except Exception as e:  # noqa: BLE001
                failed += 1
                print("  FAIL", name, repr(e))
    print("ALL PASSED" if not failed else f"{failed} FAILED")
    sys.exit(1 if failed else 0)
