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
