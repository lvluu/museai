"""A generated image is downloaded at full size from muse's viewer, not as the chat preview."""

from __future__ import annotations

import asyncio
import base64

from museai.config import Settings
from museai.drivers.browser.driver import BrowserDriver, _Tab


class FakeSession:
    def __init__(self, full):
        self.full, self.calls = full, []

    async def evaluate(self, expr, **_k):
        self.calls.append(expr)
        if "naturalWidth > pre.naturalWidth" in expr:  # dom.fetch_full_image
            return self.full
        return {"ok": True, "mime": "image/webp", "b64": base64.b64encode(b"preview").decode()}


def download(full):
    sess = FakeSession(full)
    tab = _Tab(account_id="a", context_id="c", target_id="t", session=sess)
    att = {"src": "blob:https://muse.ai/x", "kind": "image", "w": 498, "h": 498}
    return asyncio.run(BrowserDriver(Settings())._download(tab, att, "image")), sess


def test_image_comes_from_the_viewer_at_full_size():
    full = {"ok": True, "mime": "image/webp", "b64": base64.b64encode(b"big").decode(), "w": 1600, "h": 1600}
    res, sess = download(full)
    assert (res.data, res.width, res.height) == (b"big", 1600, 1600)
    assert len(sess.calls) == 1


def test_preview_is_kept_when_the_viewer_fails():
    res, sess = download({"ok": False, "err": "no viewer button"})
    assert (res.data, res.width) == (b"preview", 498)
    assert len(sess.calls) == 2
