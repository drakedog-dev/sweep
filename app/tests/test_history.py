"""The history of actions: kept newest first, capped, and never in the way of the action itself. Runs anywhere."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sweep import history as H  # noqa: E402


def test_entries_are_kept_newest_first():
    H.FILE = Path(tempfile.mkdtemp()) / "history.json"
    assert H.load() == []
    H.add("clean", freed=1024.0, session="20261114_101500")
    H.add("startup", what="Discord", on=False)
    rows = H.load()
    assert [r["kind"] for r in rows] == ["startup", "clean"], rows
    assert rows[1]["session"] == "20261114_101500" and rows[1]["freed"] == 1024.0
    assert rows[0]["on"] is False and "session" not in rows[0]       # empty fields are not stored, False is


def test_list_is_capped():
    H.FILE = Path(tempfile.mkdtemp()) / "history.json"
    for i in range(H.KEEP + 25):
        H.add("registry", n=i)
    rows = H.load()
    assert len(rows) == H.KEEP and rows[0]["n"] == H.KEEP + 24, (len(rows), rows[0])


def test_a_broken_or_unwritable_file_never_breaks_the_action():
    d = Path(tempfile.mkdtemp())
    H.FILE = d / "history.json"
    H.FILE.write_text("{ not json", "utf-8")
    assert H.load() == []
    H.add("clean", freed=1.0)                       # starts over instead of failing
    assert len(H.load()) == 1
    H.FILE = d / "no such folder" / "history.json"
    row = H.add("clean", freed=2.0)                 # cannot be written: logged, not raised
    assert row["kind"] == "clean" and H.load() == []


def test_clear_forgets_the_list_only():
    d = Path(tempfile.mkdtemp())
    H.FILE = d / "history.json"
    other = d / "settings.json"
    other.write_text("{}", "utf-8")
    H.add("drives", freed=5.0)
    H.clear()
    assert H.load() == [] and other.exists()
    H.clear()                                        # nothing to clear is fine


def test_demo_entries_have_what_the_page_needs():
    for r in H.demo():
        assert r["t"] and r["kind"], r


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("  ok", name)
    print("ALL PASSED")
