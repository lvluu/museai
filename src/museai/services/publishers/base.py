"""Publisher interface: one driver per platform posts a queued video through the platform's own API.

A post runs in steps (create an upload session, send the bytes, publish). Before each step that
cannot be repeated safely, the driver stores where it got to with ``save(checkpoint)``; the
publisher keeps that checkpoint in ``posts.json``. After a crash or restart the driver is called
again with the stored checkpoint and asks the platform where the post stands instead of starting
over, so a video is never posted twice.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

Checkpoint = dict
Save = Callable[[Checkpoint], Awaitable[None]]


@dataclass
class Job:
    """One video to post on one platform."""

    video: Path
    platform: str
    caption: str  # YouTube: "title\n\ndescription"
    token: dict  # the channel's connected account for this platform (see services/oauth.py)
    thumbnail: Path | None = None
    privacy: str = "public"  # public | private (TikTok: SELF_ONLY until the app passes the audit)
    extra: dict = field(default_factory=dict)


@dataclass
class Result:
    id: str
    url: str = ""


class PublishError(Exception):
    """A failed post. ``retry`` False means trying again cannot help (bad token, rejected file)."""

    def __init__(self, message: str, retry: bool = True) -> None:
        super().__init__(message)
        self.retry = retry


class Publisher(ABC):
    platform: str

    @abstractmethod
    async def publish(self, job: Job, checkpoint: Checkpoint, save: Save) -> Result:
        """Post ``job``, continuing from ``checkpoint`` (empty on the first try)."""


def title_and_description(caption: str) -> tuple[str, str]:
    """YouTube captions are "title\\n\\ndescription"; the title is at most 100 characters."""
    title, _, rest = caption.strip().partition("\n")
    return title.strip()[:100] or "Video", rest.strip()
