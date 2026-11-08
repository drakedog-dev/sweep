"""Sweep's own updates: the latest release on GitHub and a download that survives a dropped connection.

A dropped connection is common on the way to GitHub's download servers (a VPN switching, a provider resetting long
transfers), so the installer is fetched into a .part file, resumed with a Range request after a break, and started only
when its SHA-256 matches the one published with the release.
"""
from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import socket
import ssl
import time
import urllib.error
import urllib.request

from . import platform as P

API = "https://api.github.com/repos/{repo}/releases/latest"
WEB = "https://github.com/{repo}/releases/latest"


class UpdateError(Exception):
    """kind: "network" (GitHub not reachable), "limit" (GitHub refuses for a while), "download" or "hash"."""

    def __init__(self, kind: str, cause: BaseException | None = None):
        super().__init__(f"{kind}: {cause!r}" if cause else kind)
        self.kind, self.cause = kind, cause


def is_network_error(e: BaseException) -> bool:
    """A cut, refused or timed out connection, as opposed to an answer from the server."""
    if isinstance(e, UpdateError):
        return e.kind == "network"
    if isinstance(e, urllib.error.HTTPError):
        return e.code >= 500
    return isinstance(e, (urllib.error.URLError, ConnectionError, http.client.HTTPException, TimeoutError, socket.timeout, ssl.SSLError))


def _ua() -> dict:
    return {"User-Agent": f"Sweep/{P.APP_VERSION}"}


def _sha_near(name: str, text: str) -> str:
    """The 64-digit hex closest to the file name: "hash  name" in SHA256SUMS.txt, a table row in the release notes."""
    names = [m.start() for m in re.finditer(re.escape(name), text)]
    best, dist = "", 1000
    for m in re.finditer(r"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])", text):
        for at in names:
            d = abs(m.start() - at)
            if d < dist:
                best, dist = m.group(0).lower(), d
    return best


def _sha_for(asset: dict, body: str) -> str:
    """The installer's SHA-256: the digest GitHub keeps for the asset, or the one in the release notes table."""
    d = (asset.get("digest") or "").lower()
    if d.startswith("sha256:") and len(d) == 71:
        return d[7:]
    return _sha_near(asset["name"], body)


def _get(url: str, timeout: int = 20) -> tuple[str, bytes]:
    with urllib.request.urlopen(urllib.request.Request(url, headers=_ua()), timeout=timeout) as r:
        return r.geturl(), r.read()


def _with_retries(fn, attempts: int, what: str):
    """fn() with more tries after a dropped connection or a 5xx; a rate limit or another answer is final."""
    last: BaseException | None = None
    for n in range(attempts):
        try:
            return fn()
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):                 # rate limit: asking again now does not help
                raise UpdateError("limit", e) from e
            if e.code < 500:
                raise
            last = e
        except Exception as e:  # noqa: BLE001
            if not is_network_error(e):
                raise
            last = e
        P.log(f"self update: {what} attempt {n + 1}: {last!r}")
        if n + 1 < attempts:
            time.sleep(2 + 3 * n)
    raise UpdateError("network", last)


def _from_api(repo: str, attempts: int) -> dict:
    _, raw = _with_retries(lambda: _get(API.format(repo=repo)), attempts, "release check")
    rel = json.loads(raw.decode("utf-8"))
    body = rel.get("body") or ""
    asset = next((a for a in rel.get("assets", []) if a["name"].startswith("Sweep-Setup") and a["name"].endswith(".exe")), None)
    return {"tag": rel.get("tag_name", "").lstrip("v"), "url": asset["browser_download_url"] if asset else "",
            "sha256": _sha_for(asset, body) if asset else "", "body": body}


def _from_web(repo: str, attempts: int) -> dict:
    """The same answer from github.com itself, for networks that cut api.github.com or share one address among many
    users (GitHub allows 60 API requests an hour per address). /releases/latest redirects to /releases/tag/vX.Y.Z."""
    final, page = _with_retries(lambda: _get(WEB.format(repo=repo)), attempts, "release page")
    m = re.search(r"/releases/tag/v?(\d+(?:\.\d+)+)/?$", final)
    if not m:
        raise UpdateError("network", ValueError(f"unexpected release address {final}"))
    tag = m.group(1)
    name = f"Sweep-Setup-{tag}.exe"
    base = WEB.format(repo=repo).rsplit("/latest", 1)[0] + f"/download/v{tag}/"
    sha = ""
    try:
        sha = _sha_near(name, _get(base + "SHA256SUMS.txt")[1].decode("utf-8", "replace"))
    except Exception as e:  # noqa: BLE001
        P.log(f"self update: SHA256SUMS.txt: {e!r}")
    if not sha:
        sha = _sha_near(name, page.decode("utf-8", "replace"))
    return {"tag": tag, "url": base + name, "sha256": sha, "body": ""}


def fetch_release(repo: str, attempts: int = 3) -> dict:
    """{"tag", "url", "sha256", "body"} of the latest release. A dropped connection is tried again; when the GitHub API
    cannot be reached or limits requests, the release page on github.com answers instead (without release notes)."""
    try:
        return _from_api(repo, attempts)
    except UpdateError as api_err:
        P.log(f"self update: GitHub API {api_err!r}, asking github.com")
        try:
            return _from_web(repo, attempts)
        except UpdateError as web_err:
            raise (web_err if web_err.kind == "network" and api_err.kind == "network" else api_err) from web_err


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dst: str, sha256: str = "", attempts: int = 5, progress=None, pause: float = 2.0) -> str:
    """Download url to dst. After a break the transfer continues where it stopped; a file that does not match sha256
    is thrown away and fetched once more from the start. progress(got, total) is called from this thread."""
    part = dst + ".part"
    fresh_done = False
    last: BaseException | None = None
    n = 0
    while n < attempts:
        have = os.path.getsize(part) if os.path.exists(part) else 0
        headers = dict(_ua(), **({"Range": f"bytes={have}-"} if have else {}))
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
                if have and r.status != 206:         # the server ignored the range: start over
                    have = 0
                size = r.headers.get("Content-Length")
                total = have + int(size) if size and size.isdigit() else 0
                got = have
                with open(part, "ab" if have else "wb") as f:
                    while chunk := r.read(1 << 16):
                        f.write(chunk)
                        got += len(chunk)
                        if progress:
                            progress(got, total)
                if total and got < total:
                    raise http.client.IncompleteRead(b"", total - got)
        except urllib.error.HTTPError as e:
            if e.code == 416 and have:               # the part is already complete
                pass
            elif e.code < 500:
                raise UpdateError("download", e) from e
            else:
                last = e
        except Exception as e:  # noqa: BLE001
            if not is_network_error(e):
                raise
            last = e
        else:
            last = None
        if last is None:
            if sha256 and _sha256(part) != sha256.lower():
                os.remove(part)
                if fresh_done or not have:           # a clean download that does not match: never run it
                    raise UpdateError("hash")
                fresh_done = True                    # an old resumed part was wrong: one more try from scratch
                continue
            os.replace(part, dst)
            return dst
        n += 1
        P.log(f"self update: download attempt {n}: {last!r}")
        if n < attempts:
            time.sleep(pause * n)
    raise UpdateError("download", last)
