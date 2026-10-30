"""Platform drivers for auto-posting (see base.py)."""

from __future__ import annotations

from pathlib import Path

from .base import Job, Publisher, PublishError, Result
from .meta import FacebookPublisher, InstagramPublisher
from .mock import MockPublisher
from .tiktok import TikTokPublisher
from .youtube import YouTubePublisher

# Platforms auto-posting supports, in dashboard order. X and Threads stay manual.
AUTO_PLATFORMS = ("tiktok", "youtube", "facebook", "instagram")


def build(mock: bool, data_dir: Path) -> dict[str, Publisher]:
    """One driver per platform; ``mock`` posts nowhere (dry run, tests)."""
    if mock:
        return {p: MockPublisher(p, data_dir / "autopost-mock.json") for p in AUTO_PLATFORMS}
    return {"youtube": YouTubePublisher(), "tiktok": TikTokPublisher(),
            "facebook": FacebookPublisher(), "instagram": InstagramPublisher()}


__all__ = ["AUTO_PLATFORMS", "Job", "PublishError", "Publisher", "Result", "build"]
