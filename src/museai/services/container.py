"""Service container wired once at startup and stored on ``app.state.services``."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..accounts.pool import AccountPool
from ..accounts.store import JsonAccountStore
from ..config import Settings
from ..core.media import MediaStore
from ..drivers.base import MuseDriver
from ..drivers.registry import create_driver
from .gateway import Gateway
from .push import Push
from .tasks import TaskManager


@dataclass
class Services:
    settings: Settings
    driver: MuseDriver
    pool: AccountPool
    gateway: Gateway
    tasks: TaskManager
    media: MediaStore
    push: Push

    @classmethod
    def build(cls, settings: Settings, driver: MuseDriver | None = None) -> Services:
        settings.ensure_dirs()
        driver = driver or create_driver(settings)
        pool = AccountPool(
            JsonAccountStore(settings.accounts_file),
            strategy=settings.pool_strategy,
            max_concurrency=settings.account_max_concurrency,
            cooldown=settings.account_cooldown,
            acquire_timeout=settings.pool_acquire_timeout,
        )
        return cls(
            settings=settings,
            driver=driver,
            pool=pool,
            gateway=Gateway(
                pool,
                driver,
                max_failover=settings.max_failover,
                media_queue_timeout=settings.media_queue_timeout or math.inf,
            ),
            tasks=TaskManager(settings.tasks_file),
            media=MediaStore(settings.media_dir),
            push=Push(settings.data_dir, settings.post_dir),
        )
