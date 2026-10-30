"""Dry-run publisher: posts nowhere, keeps its "remote" posts in a JSON file so it behaves like a
platform across restarts (a resumed post finds the earlier upload instead of posting again)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from .base import Checkpoint, Job, Publisher, PublishError, Result, Save


class MockCrash(BaseException):
    """The process died mid-post (a BaseException, so the publisher's error handling does not catch it)."""


class MockPublisher(Publisher):
    def __init__(self, platform: str, remote_file: Path, fail: int = 0, crash_after_publish: bool = False) -> None:
        self.platform = platform
        self.remote_file = remote_file
        self.fail = fail  # fail this many calls first (retry tests)
        self.crash_after_publish = crash_after_publish  # die after the post went up, before returning
        self.calls = 0

    def _remote(self) -> dict:
        try:
            return json.loads(self.remote_file.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _store(self, remote: dict) -> None:
        self.remote_file.parent.mkdir(parents=True, exist_ok=True)
        self.remote_file.write_text(json.dumps(remote, indent=2, ensure_ascii=False))

    @property
    def posts(self) -> list[dict]:
        return [p for p in self._remote().values() if p["platform"] == self.platform and p["published"]]

    async def publish(self, job: Job, checkpoint: Checkpoint, save: Save) -> Result:
        self.calls += 1
        if self.fail:
            self.fail -= 1
            raise PublishError("mock: platform unavailable")
        remote = self._remote()
        upload = checkpoint.get("upload")
        if not upload or upload not in remote:
            upload = uuid.uuid4().hex[:12]
            remote[upload] = {"platform": self.platform, "video": job.video.name, "caption": job.caption,
                              "published": False}
            self._store(remote)
            await save({"upload": upload})
        if not remote[upload]["published"]:  # the step that must never run twice
            remote[upload]["published"] = True
            self._store(remote)
            if self.crash_after_publish:
                self.crash_after_publish = False
                raise MockCrash("mock: crashed after publishing")
        return Result(id=upload, url=f"mock://{self.platform}/{upload}")
