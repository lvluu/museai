"""fb-weekly skill: weekly-task plan math, reuse guards, backlog filter (offline)."""

import importlib.util
import json
from datetime import date, datetime
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / ".claude"
    / "skills"
    / "fb-weekly"
    / "scripts"
    / "fbweekly.py"
)


@pytest.fixture
def fb(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("fbweekly", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "STATE", tmp_path / "state")
    monkeypatch.setattr(mod, "QUEUE", tmp_path / "queue")
    (tmp_path / "queue" / "done").mkdir(parents=True)
    mod._meta_items.cache_clear()
    return mod


def at(fb, monkeypatch, iso):
    monkeypatch.setenv("FBWEEKLY_NOW", iso)


def test_week_runs_sunday_to_saturday(fb):
    assert fb.week_start(date(2026, 11, 22)) == date(2026, 11, 22)  # Sunday
    assert fb.week_start(date(2026, 11, 28)) == date(2026, 11, 22)  # Saturday
    assert fb.week_start(date(2026, 11, 29)) == date(2026, 11, 29)


def test_plan_spreads_remaining_over_days_left(fb, monkeypatch):
    at(fb, monkeypatch, "2026-11-23T09:00:00+07:00")
    fb.main(
        [
            "record",
            "Slow Sunlit Days",
            "--posts",
            "0/16",
            "--reels",
            "0/14",
            "--stories",
            "0/7",
            "--replies",
            "0/5",
            "--comments",
            "0/5",
        ]
    )
    p = fb.plan_page(fb.page_of("Slow Sunlit Days"), {"scheduled_counts": False}, fb.now())
    assert p["days_left"] == 6 and p["status_read"]
    # 14 reels / 6 days -> 3; each reel is also a post and a story, so no extra photo/story today
    assert p["today"] == {"reel": 3, "photo": 0, "story": 0, "reply": 1, "comment": 1}


def test_logged_actions_count_toward_today(fb, monkeypatch):
    at(fb, monkeypatch, "2026-11-23T09:00:00+07:00")
    fb.main(
        [
            "record",
            "Dream Jobs",
            "--posts",
            "1/16",
            "--reels",
            "1/14",
            "--stories",
            "1/7",
            "--replies",
            "0/5",
            "--comments",
            "0/5",
        ]
    )
    at(fb, monkeypatch, "2026-11-23T10:00:00+07:00")
    for _ in range(3):
        fb.main(["log", "Dream Jobs", "reel", "--ref", "x"])
    fb.main(["log", "Dream Jobs", "reply"])
    p = fb.plan_page(fb.page_of("Dream Jobs"), {}, fb.now())
    assert (
        p["counted"]["reels"] == 4 and p["counted"]["posts"] == 4 and p["counted"]["stories"] == 4
    )
    assert p["today"]["reel"] == 0 and p["today"]["reply"] == 0 and p["today"]["comment"] == 1


def test_last_day_takes_everything_left(fb, monkeypatch):
    at(fb, monkeypatch, "2026-11-28T09:00:00+07:00")
    fb.main(
        [
            "record",
            "Dream Jobs",
            "--posts",
            "10/16",
            "--reels",
            "9/14",
            "--stories",
            "7/7",
            "--replies",
            "2/5",
            "--comments",
            "5/5",
        ]
    )
    p = fb.plan_page(fb.page_of("Dream Jobs"), {}, fb.now())
    assert p["today"] == {"reel": 5, "photo": 1, "story": 0, "reply": 3, "comment": 0}


def test_scheduled_reels_credited_only_when_they_count(fb, monkeypatch):
    at(fb, monkeypatch, "2026-11-23T09:00:00+07:00")
    for i, when in enumerate(
        ["2026-11-24T00:00:00.000Z", "2026-11-25T00:00:00.000Z", "2026-12-01T00:00:00.000Z"]
    ):
        (fb.QUEUE / f"i{i}.json").write_text(
            json.dumps(
                {
                    "id": f"i{i}",
                    "platform": "meta",
                    "account": "Dream Jobs",
                    "targets": ["facebook"],
                    "status": "pending",
                    "schedule_at": when,
                }
            )
        )
    page = fb.page_of("Dream Jobs")
    assert fb.plan_page(page, {"scheduled_counts": True}, fb.now())["scheduled_reels_counted"] == 2
    assert fb.plan_page(page, {"scheduled_counts": False}, fb.now())["scheduled_reels_counted"] == 0


def test_backlog_only_beyond_business_suite_window_and_not_reused(fb, monkeypatch):
    at(fb, monkeypatch, "2026-11-23T09:00:00+07:00")
    feed = {
        "videos": [
            {
                "name": "near.mp4",
                "channel": "healing",
                "open": ["facebook"],
                "folder": "/f",
                "slot": "2026-12-01/1",
                "schedule": {"facebook": "2026-12-01T07:00:00+07:00"},
            },
            {
                "name": "far.mp4",
                "channel": "healing",
                "open": ["facebook"],
                "folder": "/f",
                "slot": "2027-01-05/1",
                "schedule": {"facebook": "2027-01-05T07:00:00+07:00"},
                "captions": {"facebook": "cap"},
            },
            {
                "name": "posted.mp4",
                "channel": "healing",
                "open": ["youtube"],
                "folder": "/f",
                "slot": "2027-01-06/1",
                "schedule": {"facebook": "2027-01-06T07:00:00+07:00"},
            },
            {
                "name": "other.mp4",
                "channel": "dream",
                "open": ["facebook"],
                "folder": "/f",
                "slot": "2027-01-07/1",
                "schedule": {"facebook": "2027-01-07T07:00:00+07:00"},
            },
        ]
    }
    page = fb.page_of("Slow Sunlit Days")
    got = fb.backlog(page, feed, fb.now(), 5)
    assert [g["name"] for g in got] == ["far.mp4"] and got[0]["caption"] == "cap"
    fb.main(["log", "Slow Sunlit Days", "reel", "--ref", "far.mp4"])
    assert fb.backlog(page, feed, fb.now(), 5) == []


def test_record_rejects_bad_fraction(fb):
    with pytest.raises(SystemExit):
        fb.main(
            [
                "record",
                "Dream Jobs",
                "--posts",
                "x",
                "--reels",
                "0/1",
                "--stories",
                "0/1",
                "--replies",
                "0/1",
                "--comments",
                "0/1",
            ]
        )


def test_now_is_page_clock(fb, monkeypatch):
    at(fb, monkeypatch, "2026-11-22T20:00:00+00:00")
    assert fb.now().date() == datetime(2026, 11, 23).date()  # already Monday in GMT+7
