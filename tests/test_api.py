from __future__ import annotations

import json
import time


def test_health(client):
    assert client.get("/healthz").json()["ok"] is True
    assert client.get("/readyz").json()["ready"] is True


def test_auth_required(client):
    r = client.get("/v1/models")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_api_key"


def test_models(client, auth):
    ids = {m["id"] for m in client.get("/v1/models", headers=auth).json()["data"]}
    assert {"muse-chat", "muse-image", "muse-video", "gpt-4o"} <= ids


def test_chat_non_stream(client, auth):
    r = client.post("/v1/chat/completions", headers=auth, json={
        "model": "gpt-4o", "messages": [{"role": "user", "content": "hello"}]})
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "chat.completion"
    assert body["model"] == "gpt-4o"
    assert "hello" in body["choices"][0]["message"]["content"]


def test_chat_stream(client, auth):
    with client.stream("POST", "/v1/chat/completions", headers=auth, json={
        "messages": [{"role": "user", "content": "stream me"}], "stream": True,
        "stream_options": {"include_usage": True},
    }) as r:
        assert r.status_code == 200
        lines = [ln[6:] for ln in r.iter_lines() if ln.startswith("data: ")]
    assert lines[-1] == "[DONE]"
    chunks = [json.loads(x) for x in lines[:-1]]
    text = "".join(c["choices"][0]["delta"].get("content", "") for c in chunks if c["choices"])
    assert "stream me" in text
    assert chunks[-1]["usage"]["total_tokens"] > 0


def test_chat_wrong_model_kind(client, auth):
    r = client.post("/v1/chat/completions", headers=auth, json={
        "model": "muse-video", "messages": [{"role": "user", "content": "x"}]})
    assert r.status_code == 400


def test_image_url_and_media(client, auth):
    r = client.post("/v1/images/generations", headers=auth,
                    json={"prompt": "a cat", "n": 2, "size": "1:1"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) == 2
    path = data[0]["url"].split("testserver", 1)[1]
    media = client.get(path)
    assert media.status_code == 200
    assert media.headers["content-type"] == "image/png"


def test_image_b64(client, auth):
    r = client.post("/v1/images/generations", headers=auth,
                    json={"prompt": "a dog", "response_format": "b64_json"})
    assert r.json()["data"][0]["b64_json"]


def test_video_task(client, auth):
    r = client.post("/v1/videos", headers=auth, json={"prompt": "waves", "duration": 5})
    task_id = r.json()["id"]
    for _ in range(50):
        task = client.get(f"/v1/videos/{task_id}", headers=auth).json()
        if task["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.02)
    assert task["status"] == "succeeded", task
    assert task["result"]["url"].endswith(".mp4")


def test_finished_video_is_not_rendered_again(client, auth):
    def render(**headers):
        task_id = client.post("/v1/videos", headers={**auth, **headers},
                              json={"prompt": "same clip"}).json()["id"]
        for _ in range(50):
            if client.get(f"/v1/videos/{task_id}", headers=auth).json()["status"] == "succeeded":
                return task_id
            time.sleep(0.02)
        raise AssertionError("video did not finish")

    first = render()
    assert render() == first
    assert render(**{"X-Muse-Retake": "1"}) != first


def test_video_task_records_account(client, auth, admin):
    acc = client.post("/admin/accounts", headers=admin, json={
        "label": "a1", "cookies": {"hatch_sess": "s", "hatch_native_auth_device": "d"}},
    ).json()["account"]
    task_id = client.post("/v1/videos", headers=auth, json={"prompt": "waves"}).json()["id"]
    for _ in range(50):
        task = client.get(f"/v1/videos/{task_id}", headers=auth).json()
        if task["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.02)
    assert task["account_id"] == acc["id"]
    listed = next(t for t in client.get("/admin/tasks", headers=admin).json()["data"]
                  if t["id"] == task_id)
    assert (listed["account_label"], listed["attempts"]) == ("a1", [acc["id"]])
    assert listed["created_at"] <= listed["started_at"] <= listed["updated_at"]


def test_dashboard_page(client, admin):
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert "Ready to post" in r.text
    # TestClient's peer is "testclient", not loopback, so the admin key is required.
    assert client.get("/dashboard/data").status_code == 401
    data = client.get("/dashboard/data", headers=admin).json()
    assert data["system"]["level"] in {"ok", "busy", "overloaded"}
    assert {k: v for k, v in data.items() if k != "system"} == {
        "accounts": [],
        "usage": {},
        "videos": [],
    }


def test_dashboard_data_open_to_loopback(settings):
    from fastapi.testclient import TestClient

    from museai.app import create_app
    from museai.drivers.mock import MockDriver

    app = create_app(settings, MockDriver(delay=0))
    with TestClient(app, client=("127.0.0.1", 50000)) as c:
        assert c.get("/dashboard/data").status_code == 200


def test_dashboard_cookie_upload(client, admin):
    acc = client.post("/admin/accounts", headers=admin, json={
        "label": "a1", "cookies": {"hatch_sess": "old", "hatch_native_auth_device": "d"},
    }).json()["account"]
    client.patch(f"/admin/accounts/{acc['id']}", headers=admin, json={"enabled": True})
    url = f"/dashboard/accounts/{acc['id']}/cookies"
    export = [
        {"name": "hatch_sess", "value": "new", "domain": ".muse.ai", "expirationDate": 1893456000.5},
        {"name": "hatch_native_auth_device", "value": "d2", "domain": "muse.ai"},
        {"name": "other", "value": "x", "domain": ".example.com"},
    ]
    assert client.post(url, json=export).status_code == 401
    r = client.post(url, headers=admin, json=export)
    assert r.status_code == 200
    assert r.json()["account"]["status"] == "active"
    r = client.post(url, headers=admin, json=[{"name": "datr", "value": "x"}])
    assert r.status_code == 400
    assert "hatch_sess" in r.json()["error"]["message"]


def test_dashboard_rename(client, admin):
    acc = client.post("/admin/accounts", headers=admin, json={
        "label": "a1", "cookies": {"hatch_sess": "s", "hatch_native_auth_device": "d"},
    }).json()["account"]
    url = f"/dashboard/accounts/{acc['id']}/label"
    assert client.post(url, json={"label": "x"}).status_code == 401
    assert client.post(url, headers=admin, json={"label": " "}).status_code == 400
    r = client.post(url, headers=admin, json={"label": " me@example.com "})
    assert r.json()["account"]["label"] == "me@example.com"


def test_parse_cookie_export():
    from museai.upstream.muse import parse_cookie_export

    assert parse_cookie_export({"cookies": {"a": "1", "b": ""}}) == ({"a": "1"}, {})
    assert parse_cookie_export([{"name": "a", "value": "1", "expirationDate": 5.9}]) == (
        {"a": "1"}, {"a": 5})


def test_reserved_endpoints(client, auth):
    assert client.post("/v1/responses", headers=auth, json={}).status_code == 501
    assert client.post("/v1/images/edits", headers=auth).status_code == 501


def test_admin_accounts_crud(client, auth, admin):
    assert client.get("/admin/accounts", headers=auth).status_code == 401

    r = client.post("/admin/accounts", headers=admin,
                    json={"label": "a1", "cookies": {"hatch_sess": "secretvalue123"}})
    assert r.status_code == 200
    acc = r.json()["account"]
    assert acc["cookies"]["hatch_sess"] != "secretvalue123"
    assert "hatch_native_auth_device" in r.json()["missing_cookies"]

    r = client.patch(f"/admin/accounts/{acc['id']}", headers=admin, json={"enabled": False})
    assert r.json()["account"]["enabled"] is False

    assert len(client.get("/admin/accounts", headers=admin).json()["data"]) == 1
    assert client.post(f"/admin/accounts/{acc['id']}/renew", headers=admin).json()["ok"]
    assert client.delete(f"/admin/accounts/{acc['id']}", headers=admin).status_code == 200
    assert client.get("/admin/status", headers=admin).json()["accounts"]["total"] == 0


def test_posting_queue(client, admin, settings, monkeypatch):
    from museai.api.routes import posting

    trashed = []
    monkeypatch.setattr(posting, "_trash", lambda p: (trashed.append(p.name), p.unlink()))
    settings.post_dir.mkdir()
    (settings.post_dir / "ep1.mp4").write_bytes(b"video")
    (settings.post_dir / "notes.txt").write_text("not a video")

    d = client.get("/dashboard/posts", headers=admin).json()
    assert [v["name"] for v in d["videos"]] == ["ep1.mp4"]
    assert {p["id"] for p in d["platforms"]} == {
        "youtube", "tiktok", "facebook", "instagram", "x", "threads"
    }
    assert client.get("/dashboard/posts/ep1.mp4/file", headers=admin).content == b"video"
    assert client.get("/dashboard/posts/notes.txt/file", headers=admin).status_code == 404

    r = client.post("/dashboard/posts/ep1.mp4", headers=admin, json={"caption": "hi #fyp"}).json()
    assert r["video"]["caption"] == "hi #fyp"
    r = client.post("/dashboard/posts/ep1.mp4", headers=admin,
                    json={"captions": {"x": "short #a", "youtube": "Title\n\nDesc"}}).json()
    assert r["video"]["captions"] == {"x": "short #a", "youtube": "Title\n\nDesc"}
    assert r["video"]["caption"] == "hi #fyp"
    r = client.post("/dashboard/posts/ep1.mp4", headers=admin, json={"captions": {"x": ""}}).json()
    assert r["video"]["captions"] == {"youtube": "Title\n\nDesc"}
    assert client.post("/dashboard/posts/ep1.mp4", headers=admin,
                       json={"captions": {"myspace": "x"}}).status_code == 400
    assert {p["id"]: p["limit"] for p in client.get("/dashboard/posts", headers=admin)
            .json()["platforms"]}["x"] == 280
    for p in ("youtube", "tiktok", "facebook"):
        r = client.post("/dashboard/posts/ep1.mp4", headers=admin, json={"platform": p}).json()
        assert not r["trashed"]
    r = client.post("/dashboard/posts/ep1.mp4", headers=admin,
                    json={"platform": "tiktok", "posted": False}).json()
    assert set(r["video"]["posted"]) == {"youtube", "facebook"}
    for p in ("tiktok", "instagram", "x"):
        r = client.post("/dashboard/posts/ep1.mp4", headers=admin, json={"platform": p}).json()
        assert not r["trashed"]
    for p in ("threads",):
        r = client.post("/dashboard/posts/ep1.mp4", headers=admin, json={"platform": p}).json()
    assert r["trashed"] and trashed == ["ep1.mp4"]
    assert client.get("/dashboard/posts", headers=admin).json()["videos"] == []


def test_posting_slots(tmp_path):
    import os
    from datetime import datetime

    from museai.api.routes import posting

    # Thursday 2026-10-29 12:00 GMT+7: today's slot 1 for Vietnam (YouTube 12:00) has passed.
    now = datetime(2026, 10, 29, 12, 0, tzinfo=posting.TZ)
    times = posting._slot_times("2026-10-31/2")  # Saturday evening
    assert times["youtube"].isoformat() == "2026-10-31T19:00:00+07:00"
    assert times["x"].isoformat() == "2026-10-31T13:00:00+07:00"
    assert posting._slot_times("2026-11-01/1")["tiktok"].isoformat() == "2026-11-01T09:00:00+07:00"
    assert set(posting.TIMES) == set(posting.PLATFORMS)
    assert all(len(week) == 7 for week in posting.TIMES.values())

    videos = []
    for i, name in enumerate(("a.mp4", "b.mp4", "c.mp4")):
        (p := tmp_path / name).write_bytes(b"v")
        os.utime(p, (1000 + i, 1000 + i))
        videos.append(p)
    vn = {"caption": "Học tiếng Trung"}  # Vietnamese caption -> Vietnam audience
    state = {"a.mp4": dict(vn), "b.mp4": {**vn, "slot": "2026-10-29/1", "posted": {}},  # missed, not pinned
             "c.mp4": dict(vn)}
    assert posting._assign_slots(state, videos, now)
    assert [state[n]["slot"] for n in ("a.mp4", "b.mp4", "c.mp4")] == [
        "2026-10-29/2", "2026-10-30/1", "2026-10-30/2"]  # oldest delivery first
    assert not posting._assign_slots(state, videos, now)
    cal = posting._calendar(state, {"a.mp4", "b.mp4", "c.mp4"}, now)
    assert len(cal) == 7 and cal[0]["slots"][1]["video"] == "a.mp4" and cal[0]["slots"][0]["video"] is None


def test_posting_global_audience():
    from museai.api.routes import posting

    assert posting._audience({"caption": "This beach looks fake"}) == "global"
    assert posting._audience({"captions": {"tiktok": "Nói câu này"}}) == "vn"
    assert posting._audience({"caption": "Nói câu này", "audience": "global"}) == "global"
    # Global: slot 1 at Europe's evening peak, slot 2 at the US East evening peak.
    t1, t2 = posting._slot_times("2026-10-31/1", "global"), posting._slot_times("2026-10-31/2", "global")
    assert t1["youtube"].isoformat() == "2026-10-31T19:00:00+00:00"  # London, 02:00 Sunday in Vietnam
    assert t2["youtube"].isoformat() == "2026-10-31T19:00:00-04:00"  # New York


def test_posting_move_slot(client, admin, settings):
    settings.post_dir.mkdir()
    for name in ("a.mp4", "b.mp4"):
        (settings.post_dir / name).write_bytes(b"v")
    d = client.get("/dashboard/posts", headers=admin).json()
    slots = {v["name"]: v["slot"] for v in d["videos"]}
    assert len(set(slots.values())) == 2
    assert set(d["videos"][0]["schedule"]) == {"youtube", "tiktok", "facebook", "instagram", "x", "threads"}
    assert sum(s["video"] is not None for day in d["calendar"] for s in day["slots"]) == 2

    r = client.post("/dashboard/posts/a.mp4", headers=admin, json={"slot": slots["b.mp4"]}).json()
    assert r["video"]["slot"] == slots["b.mp4"]
    moved = {v["name"]: v["slot"] for v in client.get("/dashboard/posts", headers=admin).json()["videos"]}
    assert moved == {"a.mp4": slots["b.mp4"], "b.mp4": slots["a.mp4"]}  # swapped
    r = client.post("/dashboard/posts/a.mp4", headers=admin, json={"audience": "vn"}).json()["video"]
    assert r["audience"] == "vn" and r["schedule"]["youtube"].endswith("+07:00")
    assert client.post("/dashboard/posts/a.mp4", headers=admin, json={"audience": "mars"}).status_code == 400
    for bad in ("2026-10-30/3", "tomorrow", "2026-13-40/1", 5):
        assert client.post("/dashboard/posts/a.mp4", headers=admin, json={"slot": bad}).status_code == 400


def test_dashboard_cancel_and_retry(settings, auth, admin):
    from fastapi.testclient import TestClient

    from museai.app import create_app
    from museai.drivers.mock import MockDriver

    with TestClient(create_app(settings, MockDriver(delay=0.5))) as c:
        def status(task_id):
            for _ in range(100):
                task = c.get(f"/v1/videos/{task_id}", headers=auth).json()
                if task["status"] not in ("queued", "running"):
                    return task["status"]
                time.sleep(0.02)
            return task["status"]

        task_id = c.post("/v1/videos", headers=auth, json={"prompt": "waves"}).json()["id"]
        url = f"/dashboard/videos/{task_id}"
        assert c.post(url + "/retry", headers=admin).status_code == 400  # still rendering
        assert c.post(url + "/cancel", headers=admin).json() == {"cancelled": True}
        assert status(task_id) == "cancelled"

        again = c.post(url + "/retry", headers=admin).json()["id"]
        assert again != task_id
        # A second click while the retry renders joins it instead of rendering twice.
        assert c.post(url + "/retry", headers=admin).json()["id"] == again
        assert c.post("/dashboard/videos/nope/cancel", headers=admin).status_code == 404
