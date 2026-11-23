"""`postq branding`: YouTube channel art queued as its own kind of item, next to video posts."""
import json
import shutil
import subprocess
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

postq = SourceFileLoader("postq_cli", str(Path(__file__).parent.parent / "tools" / "postq" / "postq")).load_module()
FOLLOW = Path(__file__).parent.parent / "tools" / "postq" / "ext" / "follow.js"


@pytest.fixture
def queue(monkeypatch, tmp_path):
    root = tmp_path / "queue"
    monkeypatch.setattr(postq, "ROOT", root)
    monkeypatch.setattr(postq, "DONE", root / "done")
    monkeypatch.setattr(postq, "ensure_server", lambda: None)
    monkeypatch.setattr(postq, "auto_blocked", lambda: False)
    return root


def _cli(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["postq", *args])
    postq.main()


def _image(tmp_path, name, size=10):
    f = tmp_path / name
    with f.open("wb") as fh:
        fh.truncate(size)
    return f


def _video_item(root, iid="v1"):
    item = {"id": iid, "platform": "youtube", "account": "Curious Mechanim", "source": "/gone/a.mp4",
            "video": {"file": f"{iid}-video.mp4", "name": "a.mp4"}, "cover": None, "title": "A", "caption": "",
            "schedule_at": None, "dry_run": False}
    (root / f"{iid}.json").write_text(json.dumps(item))
    (root / f"{iid}-video.mp4").write_bytes(b"x")


def test_branding_stages_the_images_and_lists_the_item(monkeypatch, tmp_path, queue, capsys):
    _cli(monkeypatch, "branding", "--account", "Curious Mechanim", "--auto",
         "--watermark", str(_image(tmp_path, "w.png")), "--avatar", str(_image(tmp_path, "a.jpg")))
    item_id = capsys.readouterr().out.strip()
    item = json.loads((queue / f"{item_id}.json").read_text())
    assert item["kind"] == "branding" and item["platform"] == "youtube" and item["auto"] is True
    assert list(item["images"]) == ["avatar", "watermark"]  # Studio's order, whatever the flag order
    for media in item["images"].values():
        assert (queue / media["file"]).read_bytes() == b"\0" * 10 and media["size"] == 10
    _cli(monkeypatch, "list")
    assert f"{item_id}  youtube  Curious Mechanim  now  'channel art: avatar, watermark'" in capsys.readouterr().out


def test_branding_without_an_image_is_refused(monkeypatch, queue):
    with pytest.raises(SystemExit, match="at least one of --avatar, --banner, --watermark"):
        _cli(monkeypatch, "branding", "--account", "Curious Mechanim")


def test_oversize_banner_is_refused_before_anything_is_staged(monkeypatch, tmp_path, queue):
    big = _image(tmp_path, "b.jpg", (6 << 20) + 1)
    with pytest.raises(SystemExit, match="banner is 6.0 MB, YouTube takes at most 6 MB"):
        _cli(monkeypatch, "branding", "--account", "C", "--avatar", str(_image(tmp_path, "a.png")), "--banner", str(big))
    assert not queue.exists() or not list(queue.iterdir())


def test_wrong_type_and_missing_file_are_refused(monkeypatch, tmp_path, queue):
    with pytest.raises(SystemExit) as e:
        _cli(monkeypatch, "branding", "--account", "C", "--avatar", str(_image(tmp_path, "a.webp")),
             "--banner", str(tmp_path / "nope.jpg"))
    assert "a.webp: avatar must be one of" in str(e.value) and "file not found" in str(e.value)


def test_cleanup_and_sync_paths_take_a_branding_item_next_to_a_video(monkeypatch, tmp_path, queue, capsys):
    _cli(monkeypatch, "branding", "--account", "Curious Mechanim", "--banner", str(_image(tmp_path, "b.jpg")))
    art = capsys.readouterr().out.strip()
    _video_item(queue)
    assert {i["id"] for i in postq.pending()} == {art, "v1"}
    assert postq.retire_duplicates() == []
    assert postq.retire_renamed("/new/a.mp4", "youtube", "Curious Mechanim") == ["v1"]
    assert postq.retire_gone({"videos": []}) == []  # channel art is no dashboard video: never "gone"
    monkeypatch.setattr(postq, "cmd_episode", lambda a: pytest.fail("channel art must not reach episode"))
    assert postq.sync_dashboard(fetch=lambda: {"videos": []}) == []
    assert [i["id"] for i in postq.pending()] == [art]
    postq.cmd_results(None)
    assert "v1  youtube  superseded" in capsys.readouterr().out


def test_finished_branding_item_archives_its_images_and_ticks_no_dashboard(monkeypatch, tmp_path, queue, capsys):
    _cli(monkeypatch, "branding", "--account", "C", "--avatar", str(_image(tmp_path, "a.png")),
         "--banner", str(_image(tmp_path, "b.jpg")))
    art = capsys.readouterr().out.strip()
    files = [m["file"] for m in json.loads((queue / f"{art}.json").read_text())["images"].values()]
    monkeypatch.setattr(postq, "mark_dashboard", lambda item: pytest.fail("channel art has no dashboard card"))
    monkeypatch.setattr(postq, "page_outcome", lambda *a, **k: None)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), postq.Handler)
    monkeypatch.setattr(postq, "PORT", srv.server_address[1])
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{postq.PORT}/api/items/{art}", method="POST",
                                     data=json.dumps({"status": "posted", "log": "avatar ✓"}).encode(),
                                     headers={"X-Postq": "1", "Content-Type": "application/json"})
        assert urllib.request.urlopen(req).status == 200
    finally:
        srv.shutdown()
    assert not (queue / f"{art}.json").exists()
    assert all((queue / "done" / f).is_file() and not (queue / f).exists() for f in files)
    monkeypatch.setattr(sys, "argv", ["postq", "wait", art])
    with pytest.raises(SystemExit) as e:
        postq.main()
    assert e.value.code == 0 and f"{art}  youtube  posted" in capsys.readouterr().out


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_popup_lists_channel_art_although_the_dashboard_does_not():
    art = {"id": "b1", "kind": "branding", "platform": "youtube", "account": "C", "images": {}}
    post = {"id": "p1", "platform": "youtube", "video": {"name": "gone.mp4"}}
    js = f"const {{followDashboard}} = require({json.dumps(str(FOLLOW))});" \
         f"console.log(JSON.stringify(followDashboard({json.dumps([art, post])}, [], 0)));"
    out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert [i["id"] for i in out["items"]] == ["b1"]
    assert [i["id"] for i in out["off"]] == ["p1"]
