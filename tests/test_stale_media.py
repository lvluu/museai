"""A new thread that still shows the previous thread's video must not return that video."""

from __future__ import annotations

import asyncio

from museai.config import Settings
from museai.drivers.browser.driver import BrowserDriver, _Tab


def test_wait_media_skips_media_returned_before(monkeypatch):
    drv = BrowserDriver(Settings())
    tab = _Tab(account_id="a", context_id="c", target_id="t", session=None)
    tab.media_srcs.add("old.mp4")
    old = {"src": "old.mp4", "kind": "video"}
    new = {"src": "new.mp4", "kind": "video"}
    # Base snapshot taken before the old thread's DOM rendered; the old video then
    # appears on /thread/new, and only later the new one.
    states = iter([{"attachments": [old]}, {"attachments": [old]}, {"attachments": [old, new]}])

    async def fake_state(_tab):
        return next(states)

    monkeypatch.setattr(drv, "_state", fake_state)
    got = asyncio.run(drv._wait_media(tab, {"attachments": []}, "video", 30, None, None))
    assert got == new
    assert tab.media_srcs == {"old.mp4", "new.mp4"}
