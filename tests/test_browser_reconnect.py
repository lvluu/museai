"""BrowserDriver recovers from a dropped CDP connection without a server restart."""

from __future__ import annotations

import asyncio
import itertools

import pytest

from museai.accounts.model import Account
from museai.config import Settings
from museai.drivers.browser import driver as driver_mod
from museai.drivers.browser.cdp import CDPError
from museai.drivers.browser.driver import BrowserDriver

_ids = itertools.count(1)


class FakeSession:
    """Stands in for CDPSession: answers Target.* calls, fails once `closed`."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.closed = False
        self.calls: list[tuple[str, dict]] = []

    @classmethod
    async def connect(cls, url: str) -> FakeSession:
        session = cls(url)
        sessions.append(session)
        return session

    async def send(self, method: str, params: dict | None = None, timeout: float = 30.0) -> dict:
        if self.closed:
            raise CDPError("cdp connection closed")
        self.calls.append((method, params or {}))
        if method == "Target.createBrowserContext":
            return {"browserContextId": f"ctx{next(_ids)}"}
        if method == "Target.createTarget":
            return {"targetId": f"tgt{next(_ids)}"}
        return {}

    async def close(self) -> None:
        self.closed = True


class FakeProc:
    returncode: int | None = None


class FakeChromium:
    def __init__(self, executable, port, profile_dir, headless=True, proxy=""):
        self.port = port
        self.proc: FakeProc | None = None
        self.launches = 0

    async def start(self) -> str:
        if self.proc is None:
            self.proc = FakeProc()
            self.launches += 1
        return f"ws://127.0.0.1:{self.port}/devtools/browser/b{self.launches}"

    async def stop(self) -> None:
        self.proc = None


sessions: list[FakeSession] = []


@pytest.fixture
async def driver(monkeypatch, tmp_path):
    sessions.clear()
    monkeypatch.setattr(driver_mod, "find_chromium", lambda configured="": "chromium")
    monkeypatch.setattr(driver_mod, "ChromiumProcess", FakeChromium)
    monkeypatch.setattr(driver_mod, "CDPSession", FakeSession)
    drv = BrowserDriver(Settings(_env_file=None, data_dir=tmp_path, driver="browser"))
    await drv.startup()
    yield drv
    await drv.shutdown()


@pytest.fixture
def account() -> Account:
    return Account(
        cookies={"hatch_sess": "v1%3Aabc", "hatch_native_auth_device": "dev-1"},
    )


def _browsers() -> list[FakeSession]:
    return [s for s in sessions if "/devtools/browser/" in s.url]


def _cookie_domains(session: FakeSession) -> set[str]:
    return {p["domain"] for m, p in session.calls if m == "Network.setCookie"}


async def test_next_job_reconnects_after_cdp_connection_closed(driver, account):
    first = await driver._tab(account)
    old_browser = driver._browser
    old_browser.closed = True  # websocket dropped while the server sat idle
    assert (await driver.health())["ok"] is False

    tab = await driver._tab(account)

    assert driver._browser is not old_browser and not driver._browser.closed
    assert driver._chromium.launches == 1  # Chromium still alive: reattach, no relaunch
    assert tab is not first and first.session.closed
    assert tab.context_id != first.context_id
    assert ("Target.createBrowserContext", {"disposeOnDetach": False}) in driver._browser.calls
    assert (
        "Target.disposeBrowserContext", {"browserContextId": first.context_id}
    ) in driver._browser.calls
    assert _cookie_domains(tab.session) == {".muse.ai", "muse.ai"}
    hatch = [p["value"] for m, p in tab.session.calls if p.get("name") == "hatch_sess"]
    assert hatch == ["v1:abc", "v1:abc"]  # URL-decoded on both domains
    assert (await driver.health())["ok"] is True


async def test_next_job_relaunches_chromium_after_it_exited(driver, account):
    await driver._tab(account)
    driver._chromium.proc.returncode = -9  # Chromium process gone
    driver._browser.closed = True

    tab = await driver._tab(account)

    assert driver._chromium.launches == 2
    assert len(_browsers()) == 2
    assert not tab.session.closed
    assert driver._tabs[account.id] == [tab]


async def test_concurrent_jobs_reconnect_once(driver, account):
    other = Account(cookies=dict(account.cookies))
    await driver._tab(account)
    driver._browser.closed = True

    await asyncio.gather(driver._tab(account), driver._tab(other))

    assert len(_browsers()) == 2  # startup + exactly one reconnect
    assert {acc for acc, tabs in driver._tabs.items() if tabs} == {account.id, other.id}


async def test_concurrent_jobs_on_one_account_get_their_own_tabs(driver, account):
    tabs = await asyncio.gather(*(driver._tab(account) for _ in range(3)))

    assert len({t.target_id for t in tabs}) == 3
    assert len({t.context_id for t in tabs}) == 3
    assert (await driver.health())["tabs"] == 3

    await driver._release(tabs[1])
    again = await driver._tab(account)

    assert again is tabs[1]  # an idle tab is reused, not reopened
    assert (await driver.health())["tabs"] == 3


async def test_renew_closes_busy_tab_only_after_its_job(driver, account, monkeypatch):
    async def renewed(cookies):
        return None

    monkeypatch.setattr(driver_mod.muse, "renew_session", renewed)
    busy = await driver._tab(account)
    idle = await driver._tab(account)
    await driver._release(idle)

    await driver.renew_session(account)

    assert idle.session.closed  # idle tab picks up rotated cookies right away
    assert not busy.session.closed  # the running render keeps its tab
    await driver._release(busy)
    assert busy.session.closed
    assert (await driver.health())["tabs"] == 0
