from __future__ import annotations

import asyncio

from museai.accounts.model import Account
from museai.drivers.browser.driver import BrowserDriver


class FakeSession:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, method: str, params: dict) -> None:
        self.sent.append(params)


def _set(cookies: dict[str, str]) -> list[dict]:
    session = FakeSession()
    account = Account(id="acc", cookies=cookies)
    asyncio.run(BrowserDriver._set_cookies(session, account))
    return session.sent


def test_host_prefixed_cookie_is_host_only():
    sent = _set({"__Host-hatch_one_tap": "x"})
    assert len(sent) == 1
    assert sent[0]["url"] == "https://muse.ai/"
    assert "domain" not in sent[0]


def test_regular_cookie_is_decoded_and_set_on_both_domains():
    sent = _set({"hatch_sess": "v1%3Aabc"})
    assert [c["domain"] for c in sent] == [".muse.ai", "muse.ai"]
    assert {c["value"] for c in sent} == {"v1:abc"}


def test_value_chrome_would_reject_after_decoding_stays_encoded():
    raw = "%7B%22mode%22%3A%22dark%22%2C%22x%22%3A1%7D"
    sent = _set({"theme": raw})
    assert {c["value"] for c in sent} == {raw}
