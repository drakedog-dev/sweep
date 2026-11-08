"""Sweep's own update download: a connection cut in the middle is resumed, a wrong file is never kept.
Runs anywhere against a small local web server: python app/tests/test_selfupdate.py (or pytest)."""
from __future__ import annotations

import hashlib
import http.server
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


def test_checksum_from_release():
    asset = {"name": "Sweep-Setup-1.0.23.exe", "digest": "sha256:" + SHA}
    assert SU._sha_for(asset, "") == SHA
    body = f"### Download\n\n| File | Size | SHA-256 |\n|---|---|---|\n| [Sweep-Setup-1.0.23.exe](https://x/Sweep-Setup-1.0.23.exe) | 34.8 MB | `{SHA}` |"
    assert SU._sha_for({"name": "Sweep-Setup-1.0.23.exe"}, body) == SHA
    assert SU._sha_for({"name": "Sweep-Setup-1.0.24.exe"}, body) == ""


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
