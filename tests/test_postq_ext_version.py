"""postq refuses a post-approve extension older than the one shipped beside it (loaded from a stale checkout)."""
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path

postq = SourceFileLoader("postq_cli", str(Path(__file__).parent.parent / "tools" / "postq" / "postq")).load_module()
SHIPPED = json.loads((postq.EXT_DIR / "manifest.json").read_text())["version"]


def test_shipped_version_passes():
    assert postq.ext_stale(SHIPPED) is None
    major, minor = SHIPPED.split(".")
    assert postq.ext_stale(f"{major}.{int(minor) + 1}") is None


def test_older_extension_is_refused_with_the_folder_to_load():
    why = postq.ext_stale("0.32")
    assert "0.32" in why and SHIPPED in why and str(postq.EXT_DIR) in why
    assert postq.ext_stale("") and postq.ext_stale("junk")


def test_ext_ready_uses_the_polled_version(monkeypatch, tmp_path):
    polled = tmp_path / ".polled"
    monkeypatch.setattr(postq, "POLLED", polled)
    polled.write_text("0.32")
    assert "0.32" in postq.ext_ready()
    polled.write_text(SHIPPED)
    assert postq.ext_ready() is None


def test_claim_refuses_a_stale_extension(monkeypatch, tmp_path):
    import threading
    import urllib.error
    import urllib.request
    from http.server import ThreadingHTTPServer

    monkeypatch.setattr(postq, "ROOT", tmp_path)
    monkeypatch.setattr(postq, "POLLED", tmp_path / ".polled")
    (tmp_path / "x1.json").write_text('{"id": "x1", "platform": "tiktok"}')
    srv = ThreadingHTTPServer(("127.0.0.1", 0), postq.Handler)
    port = srv.server_address[1]
    monkeypatch.setattr(postq, "PORT", port)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def claim(ver):
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/items/x1/claim", data=b"{}", method="POST",
                                     headers={"X-Postq": "1", "X-Postq-Ext": ver})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    try:
        code, body = claim("0.32")
        assert code == 426 and "Load unpacked" in body
        assert not (tmp_path / "x1.claim").exists()
        assert claim(SHIPPED)[0] == 200
    finally:
        srv.shutdown()
