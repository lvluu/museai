from __future__ import annotations

import asyncio
import time

from museai.api.routes import posting


def test_overlapping_listings_share_one_pass_off_the_event_loop(monkeypatch):
    """Pollers asking while a listing runs get its answer, and the slow file pass does not stall
    other requests (it used to run on the event loop, one pass per poller, for minutes)."""
    passes = []

    def slow_view(svc):
        passes.append(1)
        time.sleep(0.3)  # the Desktop folders
        return [], {}, {"videos": [], "n": len(passes)}

    monkeypatch.setattr(posting, "_posts_view", slow_view)

    async def main():
        svc = object()
        ticks = 0

        async def ticker():
            nonlocal ticks
            while True:
                await asyncio.sleep(0.01)
                ticks += 1

        t = asyncio.create_task(ticker())
        answers = await asyncio.gather(*(posting.list_posts(svc) for _ in range(3)))
        t.cancel()
        later = await posting.list_posts(svc)
        return answers, later, ticks

    answers, later, ticks = asyncio.run(main())
    assert answers == [{"videos": [], "n": 1}] * 3
    assert later["n"] == 2  # a finished pass is not reused
    assert ticks > 10  # other work ran during the pass


def test_queued_skips_a_video_that_vanishes_while_listing(tmp_path, monkeypatch):
    """A folder renumbered or a file moved mid-listing used to raise FileNotFoundError (a 500, so the
    dashboard kept showing the old list); it is now just left out of that pass."""
    from types import SimpleNamespace

    keep = tmp_path / "keep.mp4"
    keep.write_bytes(b"x")
    gone = tmp_path / "gone.mp4"
    gone.write_bytes(b"x")
    real_stat = type(gone).stat

    def stat(self, *a, **k):
        if self.name == "gone.mp4":
            raise FileNotFoundError(2, "No such file or directory", str(self))
        return real_stat(self, *a, **k)

    monkeypatch.setattr(posting, "_is_video", lambda p: p.suffix == ".mp4")  # it passed this check, then vanished
    monkeypatch.setattr(type(gone), "stat", stat)
    svc = SimpleNamespace(settings=SimpleNamespace(post_dir=tmp_path))
    assert [p.name for p in posting.queued(svc)] == ["keep.mp4"]
