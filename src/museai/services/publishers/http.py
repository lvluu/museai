"""Shared HTTP handling for the platform drivers."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx

from .base import PublishError

TIMEOUT = httpx.Timeout(60.0, write=600.0, read=300.0)


@asynccontextmanager
async def using(http: httpx.AsyncClient | None) -> AsyncIterator[httpx.AsyncClient]:
    """The injected client (tests), else a fresh one closed afterwards."""
    if http is not None:
        yield http
        return
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as fresh:
        yield fresh


def check(res: httpx.Response, what: str) -> httpx.Response:
    """Raise PublishError for an error response: 429 and 5xx are worth a retry, other 4xx are not
    (a 401/403 needs the account connected again)."""
    if res.is_success:
        return res
    body = res.text[:300]
    retry = res.status_code == 429 or res.status_code >= 500
    hint = " (connect the account again on the dashboard)" if res.status_code in (401, 403) else ""
    raise PublishError(f"{what}: HTTP {res.status_code}{hint}: {body}", retry=retry)


async def read(path: Path) -> bytes:
    return await asyncio.to_thread(path.read_bytes)
