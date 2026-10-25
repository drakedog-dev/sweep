"""Attach a short CI report to the tested commit as a git note (refs/notes/<name>).

Notes do not show up as branches or files on GitHub, but anyone can read them with git:
    git fetch origin "refs/notes/*:refs/notes/*"
    git notes --ref=selftest show <commit>

    python tools/ci_report.py <name> <status> [file ...]     # the last lines of every file are included
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", check=check)


def main() -> int:
    name, status, files = sys.argv[1], sys.argv[2], sys.argv[3:]
    env = os.environ
    lines = [f"{name}: {status}",
             f"run: {env.get('GITHUB_SERVER_URL', '')}/{env.get('GITHUB_REPOSITORY', '')}/actions/runs/{env.get('GITHUB_RUN_ID', '')}",
             f"commit: {env.get('GITHUB_SHA', '')}"]
    for f in files:
        p = Path(f)
        if not p.is_file():
            continue
        text = p.read_text("utf-8", errors="replace").splitlines()
        lines += ["", f"--- {p.name} (last {min(len(text), 250)} of {len(text)} lines)"] + text[-250:]
    body = "\n".join(lines)[-120_000:]
    note = Path(tempfile.gettempdir()) / f"ci-note-{name}.txt"
    note.write_text(body, "utf-8")
    ref = f"refs/notes/{name}"
    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    for attempt in range(4):
        git("fetch", "--quiet", "origin", f"+{ref}:{ref}", check=False)
        git("notes", f"--ref={name}", "add", "-f", "-F", str(note), env.get("GITHUB_SHA", "HEAD"))
        r = git("push", "--quiet", "origin", ref, check=False)
        if r.returncode == 0:
            print(f"report saved to {ref}")
            return 0
        time.sleep(3 + attempt * 3)
    print("could not push the report:", r.stderr.strip()[-300:])
    return 0      # a missing report never fails the build


if __name__ == "__main__":
    sys.exit(main())
