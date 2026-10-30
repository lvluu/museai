"""Gateway: runs driver calls on pooled accounts with automatic failover."""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import TypeVar

from ..accounts.model import Account, AccountStatus
from ..accounts.pool import AccountPool, Lease
from ..drivers.base import ChatRequest, ImageRequest, MediaResult, MuseDriver, VideoRequest
from ..errors import UpstreamError

log = logging.getLogger(__name__)
T = TypeVar("T")

_ANONYMOUS = Account(id="anonymous", label="driver without accounts")


class Gateway:
    def __init__(
        self,
        pool: AccountPool,
        driver: MuseDriver,
        *,
        max_failover: int = 2,
        media_queue_timeout: float | None = None,
    ) -> None:
        self.pool = pool
        self.driver = driver
        self.max_failover = max_failover
        # Image/video jobs run in the background, so they wait for the next free account
        # (one job per account) instead of failing after the chat acquire timeout.
        self.media_queue_timeout = media_queue_timeout
        # What each account is doing right now (chat, image, video), for the dashboard cards:
        # tasks only record videos, so an account busy with an image used to look idle.
        self.jobs: dict[str, list[dict]] = {}

    @asynccontextmanager
    async def _lease(
        self, exclude: list[str], hint: str | None, timeout: float | None = None,
        owner: str | None = None, kind: str = "chat", prompt: str = "",
    ) -> AsyncIterator[Lease]:
        if not self.driver.requires_account and not self.pool.all():
            yield Lease(_ANONYMOUS)
            return
        async with self.pool.lease(exclude=exclude, hint=hint, timeout=timeout,
                                   owner=owner) as lease:
            job = {"kind": kind, "prompt": prompt[:200], "since": time.time()}
            jobs = self.jobs.setdefault(lease.account.id, [])
            jobs.append(job)
            try:
                yield lease
            finally:
                jobs.remove(job)

    def _should_retry(self, exc: UpstreamError, attempt: int, tried: list[str]) -> bool:
        """Fail over only to an account not tried yet; with none left the caller gets
        the upstream error instead of "no usable account"."""
        if not exc.retryable or attempt >= self.max_failover:
            return False
        accounts = self.pool.all()
        return not accounts or any(
            a.enabled and a.status != AccountStatus.INVALID and a.id not in tried
            for a in accounts
        )

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[str]:
        tried: list[str] = []
        for attempt in range(self.max_failover + 1):
            async with self._lease(tried, req.conversation_hint) as lease:
                emitted = False
                try:
                    async for delta in self.driver.chat_stream(lease.account, req):
                        emitted = True
                        yield delta
                    return
                except UpstreamError as exc:
                    lease.fail(exc)
                    tried.append(lease.account.id)
                    # Once text reached the client we cannot transparently switch accounts.
                    if emitted or not self._should_retry(exc, attempt, tried):
                        raise
                    log.warning("chat failed on %s (%s), failing over", lease.account.id, exc)

    async def chat_complete(self, req: ChatRequest) -> str:
        return await self._run(
            lambda acc: self.driver.chat_complete(acc, req), req.conversation_hint
        )

    async def _run(
        self,
        fn: Callable[[Account], Awaitable[T]],
        hint: str | None = None,
        queue_timeout: float | None = None,
        on_account: Callable[[Account], None] | None = None,
        owner: str | None = None,
        kind: str = "chat",
        prompt: str = "",
    ) -> T:
        tried: list[str] = []
        for attempt in range(self.max_failover + 1):
            async with self._lease(tried, hint, queue_timeout, owner, kind, prompt) as lease:
                if on_account:
                    on_account(lease.account)
                try:
                    return await fn(lease.account)
                except UpstreamError as exc:
                    lease.fail(exc)
                    tried.append(lease.account.id)
                    if not self._should_retry(exc, attempt, tried):
                        raise
                    log.warning("call failed on %s (%s), failing over", lease.account.id, exc)
        raise AssertionError("unreachable")

    async def generate_image(self, req: ImageRequest) -> list[MediaResult]:
        return await self._run(
            lambda acc: self.driver.generate_image(acc, req), queue_timeout=self.media_queue_timeout,
            kind="image", prompt=req.prompt,
        )

    async def generate_video(
        self, req: VideoRequest, on_account: Callable[[Account], None] | None = None,
        owner: str | None = None,
    ) -> MediaResult:
        return await self._run(
            lambda acc: self.driver.generate_video(acc, req),
            queue_timeout=self.media_queue_timeout,
            on_account=on_account,
            owner=owner,
            kind="video",
            prompt=req.prompt,
        )
