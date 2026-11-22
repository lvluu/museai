"""A chat that did not finish leaves its tab stale, so `_release` closes it instead of keeping a spinning page."""

from __future__ import annotations

from museai.config import Settings
from museai.drivers.browser.driver import BrowserDriver, _Tab


async def test_unfinished_chat_marks_tab_stale() -> None:
    driver = BrowserDriver(Settings())
    tab = _Tab(account_id="a", context_id="c", target_id="t", session=None, thread_url="https://muse.ai/thread/x")
    await driver._finish_chat(tab, None, None, finished=False)
    assert tab.stale
    assert tab.thread_url == ""
