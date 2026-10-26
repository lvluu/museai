from __future__ import annotations

import asyncio
import math
import time

import pytest

from museai.accounts import Account, AccountPool, AccountStatus, JsonAccountStore
from museai.drivers.base import ChatRequest, VideoRequest
from museai.drivers.mock import MockDriver
from museai.errors import (
    GenerationTimeout,
    NoAccountAvailable,
    UpstreamAuthError,
    UpstreamError,
)
from museai.services.gateway import Gateway


async def _pool(tmp_path, n=2, **kw) -> AccountPool:
    pool = AccountPool(JsonAccountStore(tmp_path / "acc.json"), acquire_timeout=0.2, **kw)
    for i in range(n):
        await pool.upsert(Account(id=f"a{i}", cookies={"hatch_sess": "x"}))
    return pool


async def test_empty_pool_raises(tmp_path):
    pool = await _pool(tmp_path, n=0)
    with pytest.raises(NoAccountAvailable):
        await pool.acquire()


async def test_lru_spreads_load(tmp_path):
    pool = await _pool(tmp_path, strategy="lru")
    first = await pool.acquire()
    await pool.release(first)
    second = await pool.acquire()
    assert first.id != second.id


async def test_concurrency_limit_waits_then_times_out(tmp_path):
    pool = await _pool(tmp_path, n=1)
    held = await pool.acquire()
    with pytest.raises(NoAccountAvailable, match="busy"):
        await pool.acquire()
    waiter = asyncio.create_task(pool.acquire())
    await asyncio.sleep(0.05)
    await pool.release(held)
    assert (await waiter).id == held.id


async def test_auth_error_invalidates(tmp_path):
    pool = await _pool(tmp_path, n=1)
    with pytest.raises(UpstreamAuthError):
        async with pool.lease():
            raise UpstreamAuthError("bad cookie")
    assert pool.get("a0").status == AccountStatus.INVALID
    with pytest.raises(NoAccountAvailable):
        await pool.acquire()


async def test_all_cooling_waits_for_cooldown_instead_of_failing(tmp_path):
    pool = await _pool(tmp_path, n=1)
    acc = pool.get("a0")
    acc.status, acc.cooldown_until = AccountStatus.COOLING, time.time() + 0.15
    got = await pool.acquire(timeout=2)
    assert got.id == "a0"


async def test_cooling_past_the_deadline_still_times_out(tmp_path):
    pool = await _pool(tmp_path, n=1)
    acc = pool.get("a0")
    acc.status, acc.cooldown_until = AccountStatus.COOLING, time.time() + 60
    with pytest.raises(NoAccountAvailable, match="cooling"):
        await pool.acquire()


async def test_unlimited_queue_waits_for_busy_account(tmp_path):
    pool = await _pool(tmp_path, n=1)
    held = await pool.acquire()
    waiter = asyncio.create_task(pool.acquire(timeout=math.inf))
    await asyncio.sleep(0.4)  # longer than acquire_timeout: must still be queued
    assert not waiter.done()
    await pool.release(held)
    assert (await asyncio.wait_for(waiter, 1)).id == "a0"


async def test_persistence_roundtrip(tmp_path):
    await _pool(tmp_path, n=2)
    reloaded = AccountPool(JsonAccountStore(tmp_path / "acc.json"))
    await reloaded.load()
    assert {a.id for a in reloaded.all()} == {"a0", "a1"}


class _FlakyDriver(MockDriver):
    requires_account = True

    def __init__(self, bad: set[str]):
        super().__init__(delay=0)
        self.bad = bad

    async def chat_stream(self, account, req):
        if account.id in self.bad:
            raise UpstreamError("boom")
        async for d in super().chat_stream(account, req):
            yield d


async def test_gateway_fails_over(tmp_path):
    pool = await _pool(tmp_path, n=2, strategy="round_robin")
    gw = Gateway(pool, _FlakyDriver({"a0"}), max_failover=2)
    text = "".join([d async for d in gw.chat_stream(ChatRequest(prompt="hi", model="m"))])
    assert "hi" in text
    assert pool.get("a0").status == AccountStatus.COOLING
    assert pool.get("a1").success_count == 1


class _SlowVideoDriver(MockDriver):
    requires_account = True

    def __init__(self):
        super().__init__(delay=0)
        self.calls = 0

    async def generate_video(self, account, req):
        self.calls += 1
        raise GenerationTimeout("video generation timed out")


async def test_generation_timeout_keeps_account_and_does_not_fail_over(tmp_path):
    pool = await _pool(tmp_path, n=1)
    driver = _SlowVideoDriver()
    gw = Gateway(pool, driver, max_failover=2)
    with pytest.raises(GenerationTimeout):
        await gw.generate_video(VideoRequest(prompt="p", model="m"))
    assert driver.calls == 1
    assert pool.get("a0").status == AccountStatus.ACTIVE
    assert (await pool.acquire()).id == "a0"


class _HeldVideoDriver(MockDriver):
    """Each video runs until its test releases it; records the account it ran on."""

    def __init__(self) -> None:
        super().__init__(delay=0)
        self.running: dict[str, str] = {}  # prompt -> account id
        self.release: dict[str, asyncio.Event] = {}

    async def generate_video(self, account, req):
        self.running[req.prompt] = account.id
        self.release[req.prompt] = done = asyncio.Event()
        await done.wait()
        return await super().generate_video(account, req)


async def test_videos_run_in_parallel_one_per_account_and_queue_for_the_next_free(tmp_path):
    pool = await _pool(tmp_path, n=4)
    driver = _HeldVideoDriver()
    # Waits far longer than the pool's own 0.2 s acquire timeout.
    gw = Gateway(pool, driver, media_queue_timeout=5)

    def submit(name):
        return asyncio.create_task(gw.generate_video(VideoRequest(prompt=name, model="muse-video")))

    async def settle():
        for _ in range(20):
            await asyncio.sleep(0.01)

    jobs = {f"v{i}": submit(f"v{i}") for i in range(1, 5)}
    await settle()
    assert sorted(driver.running.values()) == ["a0", "a1", "a2", "a3"]

    jobs["v5"] = submit("v5")
    await asyncio.sleep(0.4)
    assert "v5" not in driver.running

    driver.release["v4"].set()
    await jobs["v4"]
    await settle()
    assert driver.running["v5"] == driver.running["v4"]

    jobs["v6"] = submit("v6")
    driver.release["v2"].set()
    await jobs["v2"]
    await settle()
    assert driver.running["v6"] == driver.running["v2"]

    for name in ("v1", "v3", "v5", "v6"):
        driver.release[name].set()
    await asyncio.gather(*jobs.values())
