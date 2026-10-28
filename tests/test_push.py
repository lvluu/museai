from __future__ import annotations

import os
import time

from museai.services.push import Push


async def test_new_video_is_announced_once(tmp_path, monkeypatch):
    desk = tmp_path / "desk"
    desk.mkdir()
    (desk / "old.mp4").write_bytes(b"x")
    push = Push(tmp_path / "data", desk)
    sent = []

    async def notify(title, body, url="/dashboard#post"):
        sent.append((title, body))
        return 1

    monkeypatch.setattr(push, "notify", notify)
    assert await push.check_new_videos() == []  # first look only records what is there

    new = desk / "Italy reel.mp4"
    new.write_bytes(b"x")
    assert await push.check_new_videos() == []  # still settling
    old = time.time() - 60
    os.utime(new, (old, old))
    captions = {"Italy reel.mp4": "Italy in 12 seconds\n#italy"}
    assert await push.check_new_videos(captions) == ["Italy reel.mp4"]
    assert await push.check_new_videos(captions) == []
    assert sent == [("Ready to post: Italy reel", "Italy in 12 seconds")]


def test_push_routes(client, admin):
    info = client.get("/dashboard/push", headers=admin).json()
    assert len(info["key"]) == 87 and info["devices"] == 0  # uncompressed P-256 point
    sub = {"endpoint": "https://web.push.apple.com/abc", "keys": {"p256dh": "p", "auth": "a"}}
    assert client.post("/dashboard/push/subscribe", headers=admin, json={"endpoint": "x"}).status_code == 400
    assert client.post("/dashboard/push/subscribe", headers=admin, json=sub).json() == {"devices": 1}
    assert client.post("/dashboard/push/subscribe", headers=admin, json=sub).json() == {"devices": 1}
    assert client.post("/dashboard/push/unsubscribe", headers=admin,
                       json={"endpoint": sub["endpoint"]}).json() == {"devices": 0}
    assert client.get("/dashboard/push").status_code == 401


def test_pwa_files(client):
    r = client.get("/dashboard/static/sw.js")
    assert r.status_code == 200 and r.headers["service-worker-allowed"] == "/dashboard"
    assert client.get("/dashboard/static/manifest.webmanifest").json()["scope"] == "/dashboard"
    assert client.get("/dashboard/static/../app.py").status_code == 404
    assert client.get("/dashboard/static/dashboard.html").status_code == 404
