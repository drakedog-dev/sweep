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
