"""Sweep's own update download: a connection cut in the middle is resumed, a wrong file is never kept.
Runs anywhere against a small local web server: python app/tests/test_selfupdate.py (or pytest)."""
from __future__ import annotations

import hashlib
import http.server
import json
import os
import sys
import tempfile
import threading
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
os.environ["no_proxy"] = os.environ["NO_PROXY"] = "127.0.0.1,localhost"

from sweep import selfupdate as SU  # noqa: E402

BLOB = os.urandom(300_000)
SHA = hashlib.sha256(BLOB).hexdigest()


class Handler(http.server.BaseHTTPRequestHandler):
    cuts = 0                  # how many more full answers to cut short
    requests: list = []

    def log_message(self, *a):
        pass

    def do_GET(self):  # noqa: N802
        Handler.requests.append(self.headers.get("Range", ""))
        if self.path != "/setup.exe":
            self.send_error(404)
            return
        rng = self.headers.get("Range", "")
        start = int(rng[6:-1]) if rng.startswith("bytes=") and rng.endswith("-") else 0
        if start >= len(BLOB):
            self.send_error(416)
            return
        body = BLOB[start:]
        self.send_response(206 if start else 200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if Handler.cuts:
            Handler.cuts -= 1
            self.wfile.write(body[:100_000])          # the provider drops the connection here
            self.wfile.flush()
            self.connection.shutdown(2)
            return
        self.wfile.write(body)


def serve():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def test_resumes_after_cut():
    srv, base = serve()
    try:
        Handler.cuts, Handler.requests = 2, []
        dst = os.path.join(tempfile.mkdtemp(), "Sweep-Setup.exe")
        seen = []
        SU.download(base + "/setup.exe", dst, SHA, pause=0, progress=lambda g, t: seen.append((g, t)))
        assert Path(dst).read_bytes() == BLOB
        assert not os.path.exists(dst + ".part")
        assert Handler.requests == ["", "bytes=100000-", "bytes=200000-"], Handler.requests
        assert seen[-1] == (len(BLOB), len(BLOB))
    finally:
        srv.shutdown()


def test_wrong_file_is_never_kept():
    srv, base = serve()
    try:
        Handler.cuts = 0
        dst = os.path.join(tempfile.mkdtemp(), "Sweep-Setup.exe")
        try:
            SU.download(base + "/setup.exe", dst, "0" * 64, pause=0)
            raise AssertionError("a file with another checksum was accepted")
        except SU.UpdateError as e:
            assert e.kind == "hash"
        assert not os.path.exists(dst) and not os.path.exists(dst + ".part")
    finally:
        srv.shutdown()


def test_stale_part_is_fetched_again():
    srv, base = serve()
    try:
        Handler.cuts, Handler.requests = 0, []
        dst = os.path.join(tempfile.mkdtemp(), "Sweep-Setup.exe")
        Path(dst + ".part").write_bytes(b"x" * 1000)     # left over from an older download
        SU.download(base + "/setup.exe", dst, SHA, pause=0)
        assert Path(dst).read_bytes() == BLOB
        assert Handler.requests == ["bytes=1000-", ""], Handler.requests
    finally:
        srv.shutdown()


def test_missing_file_fails_at_once():
    srv, base = serve()
    try:
        Handler.requests = []
        try:
            SU.download(base + "/nope.exe", os.path.join(tempfile.mkdtemp(), "x.exe"), SHA, pause=0)
            raise AssertionError("404 was not reported")
        except SU.UpdateError as e:
            assert e.kind == "download" and len(Handler.requests) == 1
    finally:
        srv.shutdown()


def test_server_gone_gives_up():
    srv, base = serve()
    srv.shutdown()
    srv.server_close()
    try:
        SU.download(base + "/setup.exe", os.path.join(tempfile.mkdtemp(), "x.exe"), SHA, attempts=2, pause=0)
        raise AssertionError("no error without a server")
    except SU.UpdateError as e:
        assert e.kind == "download" and SU.is_network_error(e.cause)


class GitHub(http.server.BaseHTTPRequestHandler):
    """A tiny GitHub: /api/... (the API) and /web/... (github.com) with what each test sets."""
    api = "reset"                 # reset | limit | ok
    web = "ok"                    # ok | reset
    sums = True                   # SHA256SUMS.txt published

    def log_message(self, *a):
        pass

    def do_GET(self):  # noqa: N802
        p = self.path
        if p.startswith(("/api/", "/apiall/")):
            if GitHub.api == "reset":
                self.close_connection = True      # the network drops it: no answer at all
                return
            if GitHub.api == "limit":
                self.send_error(403, "rate limit exceeded")
                return
        if p.startswith("/web/") and GitHub.web == "reset":
            self.close_connection = True
            return
        if p == "/web/r/x/releases/latest":
            self.send_response(302)
            self.send_header("Location", "/web/r/x/releases/tag/v1.2.3")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if p == "/web/r/x/releases/tag/v1.2.3":
            html = (f'<table><tr><td><a href="/r/x/releases/download/v1.2.3/Sweep-Setup-1.2.3.exe">Sweep-Setup-1.2.3.exe</a></td>'
                    f"<td>34.9 MB</td><td><code>{SHA}</code></td></tr></table>").encode()
            return self._send(html)
        if p == "/web/r/x/releases/download/v1.2.3/SHA256SUMS.txt" and GitHub.sums:
            return self._send(f"{SHA}  Sweep-Setup-1.2.3.exe\n".encode())
        if p.startswith("/apiall/r/x"):            # every release, pre-releases included (Sweep Beta)
            rels = [{"tag_name": t, "draft": d, "prerelease": "-beta" in t, "body": "",
                     "assets": [{"name": f"{'Sweep-Beta-Setup' if '-beta' in t else 'Sweep-Setup'}-{t[1:]}.exe",
                                 "browser_download_url": f"https://x/{t}.exe", "digest": "sha256:" + SHA}]}
                    for t, d in (("v1.2.3", False), ("v2.0.0-beta.10", True), ("v2.0.0-beta.2", False), ("v2.0.0-beta.1", False))]
            return self._send(json.dumps(rels).encode())
        if p == "/web/r/x/releases.atom":
            feed = "".join(f'<entry><link rel="alternate" type="text/html" href="https://github.com/r/x/releases/tag/{t}"/></entry>'
                           for t in ("v1.2.3", "v2.0.0-beta.2", "v2.0.0-beta.1"))
            return self._send(f"<feed>{feed}</feed>".encode())
        if p == "/web/r/x/releases/download/v2.0.0-beta.2/SHA256SUMS.txt":
            return self._send(f"{SHA}  Sweep-Beta-Setup-2.0.0-beta.2.exe\n".encode())
        self.send_error(404)

    def _send(self, body: bytes):
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _github(api, web="ok", sums=True):
    GitHub.api, GitHub.web, GitHub.sums = api, web, sums
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), GitHub)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    SU.API, SU.WEB = base + "/api/{repo}", base + "/web/{repo}/releases/latest"
    SU.API_ALL, SU.FEED = base + "/apiall/{repo}", base + "/web/{repo}/releases.atom"
    SU.CHANNEL, SU.SETUP = "stable", "Sweep-Setup"
    return srv, base


def test_beta_looks_among_prereleases():
    srv, base = _github("ok")
    try:
        SU.CHANNEL, SU.SETUP = "beta", "Sweep-Beta-Setup"
        rel = SU.fetch_release("r/x", attempts=1)       # the newest beta that is not a draft; never the stable one
        assert rel["tag"] == "2.0.0-beta.2" and rel["url"] == "https://x/v2.0.0-beta.2.exe" and rel["sha256"] == SHA, rel
        GitHub.api = "reset"                             # api.github.com cut: the releases feed on github.com
        rel = SU.fetch_release("r/x", attempts=1)
        assert rel["tag"] == "2.0.0-beta.2" and rel["sha256"] == SHA, rel
        assert rel["url"] == base + "/web/r/x/releases/download/v2.0.0-beta.2/Sweep-Beta-Setup-2.0.0-beta.2.exe", rel["url"]
    finally:
        SU.CHANNEL, SU.SETUP = "stable", "Sweep-Setup"
        srv.shutdown()


def test_release_from_github_page_when_api_is_cut():
    srv, base = _github("reset")
    try:
        rel = SU.fetch_release("r/x", attempts=1)
        assert rel["tag"] == "1.2.3" and rel["sha256"] == SHA, rel
        assert rel["url"] == base + "/web/r/x/releases/download/v1.2.3/Sweep-Setup-1.2.3.exe", rel["url"]
    finally:
        srv.shutdown()


def test_release_checksum_from_page_without_sums_file():
    srv, _ = _github("limit", sums=False)
    try:
        rel = SU.fetch_release("r/x", attempts=1)
        assert rel["tag"] == "1.2.3" and rel["sha256"] == SHA, rel
    finally:
        srv.shutdown()


def test_release_check_fails_when_all_github_is_cut():
    srv, _ = _github("reset", web="reset")
    try:
        SU.fetch_release("r/x", attempts=1)
        raise AssertionError("no error")
    except SU.UpdateError as e:
        assert e.kind == "network" and SU.is_network_error(e), e
    finally:
        srv.shutdown()


def test_checksum_from_release():
    asset = {"name": "Sweep-Setup-1.0.23.exe", "digest": "sha256:" + SHA}
    assert SU._sha_for(asset, "") == SHA
    body = f"### Download\n\n| File | Size | SHA-256 |\n|---|---|---|\n| [Sweep-Setup-1.0.23.exe](https://x/Sweep-Setup-1.0.23.exe) | 34.8 MB | `{SHA}` |"
    assert SU._sha_for({"name": "Sweep-Setup-1.0.23.exe"}, body) == SHA
    assert SU._sha_for({"name": "Sweep-Setup-1.0.24.exe"}, body) == ""
    assert SU._sha_near("Sweep-Setup-1.0.23.exe", f"{SHA}  Sweep-Setup-1.0.23.exe\n") == SHA


def test_network_errors():
    import http.client
    assert SU.is_network_error(http.client.RemoteDisconnected("Remote end closed connection without response"))
    assert SU.is_network_error(ConnectionResetError(10054, "closed"))
    assert SU.is_network_error(urllib.error.URLError("timed out"))
    assert not SU.is_network_error(urllib.error.HTTPError("u", 404, "nf", {}, None))
    assert not SU.is_network_error(ValueError("x"))
    assert not SU.is_network_error(SU.UpdateError("hash"))


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
