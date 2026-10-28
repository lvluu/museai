"""Web push to the dashboard installed as a phone app (PWA).

The phone subscribes once from the dashboard; the server keeps the subscription and a VAPID
key pair in ``data_dir``. A watcher pushes "ready to post" when a new final video lands in
``post_dir``, so the user can post from the phone without watching the desktop.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from pathlib import Path

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from py_vapid import Vapid02
from pywebpush import WebPushException, webpush

log = logging.getLogger(__name__)

VIDEO_EXT = {".mp4", ".mov", ".m4v"}
# Apple rejects pushes whose VAPID subject is not a mailto: or https: URL.
SUBJECT = "https://github.com/lvluu/museai"
# A file younger than this may still be copying in.
SETTLE = 10.0


class Push:
    def __init__(self, data_dir: Path, post_dir: Path) -> None:
        self.key_file = data_dir / "vapid.pem"
        self.state_file = data_dir / "push.json"
        self.post_dir = post_dir
        self._vapid: Vapid02 | None = None

    # --- keys and subscriptions ---

    @property
    def vapid(self) -> Vapid02:
        if self._vapid is None:
            if self.key_file.exists():
                self._vapid = Vapid02.from_pem(self.key_file.read_bytes())
            else:
                self._vapid = Vapid02()
                self._vapid.generate_keys()
                self.key_file.parent.mkdir(parents=True, exist_ok=True)
                self.key_file.write_bytes(self._vapid.private_pem())
                self.key_file.chmod(0o600)
        return self._vapid

    @property
    def public_key(self) -> str:
        raw = self.vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    def _load(self) -> dict:
        try:
            return json.loads(self.state_file.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save(self, state: dict) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False))
        tmp.replace(self.state_file)

    def subscribe(self, sub: dict) -> int:
        state = self._load()
        subs = [s for s in state.get("subscriptions", []) if s["endpoint"] != sub["endpoint"]]
        subs.append({"endpoint": sub["endpoint"], "keys": sub["keys"]})
        state["subscriptions"] = subs
        self._save(state)
        return len(subs)

    def unsubscribe(self, endpoint: str) -> None:
        state = self._load()
        state["subscriptions"] = [s for s in state.get("subscriptions", [])
                                  if s["endpoint"] != endpoint]
        self._save(state)

    @property
    def subscriptions(self) -> list[dict]:
        return self._load().get("subscriptions", [])

    # --- sending ---

    async def notify(self, title: str, body: str, url: str = "/dashboard#post") -> int:
        """Push to every subscribed device; drop subscriptions the push service says are gone."""
        data = json.dumps({"title": title, "body": body, "url": url})
        sent, gone = 0, []
        for sub in self.subscriptions:
            try:
                await asyncio.to_thread(
                    webpush, sub, data, vapid_private_key=self.vapid,
                    vapid_claims={"sub": SUBJECT}, ttl=24 * 3600, timeout=15)
                sent += 1
            except WebPushException as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status in (404, 410):
                    gone.append(sub["endpoint"])
                else:
                    log.warning("push to %s failed: %s", sub["endpoint"][:40], exc)
            except Exception as exc:  # noqa: BLE001 - a dead network must not stop the watcher
                log.warning("push to %s failed: %s", sub["endpoint"][:40], exc)
        for endpoint in gone:
            self.unsubscribe(endpoint)
        return sent

    # --- watching the posting folder ---

    def _videos(self) -> dict[str, float]:
        if not self.post_dir.is_dir():
            return {}
        return {p.name: p.stat().st_mtime for p in self.post_dir.iterdir()
                if p.is_file() and p.suffix.lower() in VIDEO_EXT and not p.name.startswith(".")}

    async def check_new_videos(self, captions: dict[str, str] | None = None) -> list[str]:
        """Push once for each video that appeared since the last check; returns their names.

        The first check only records what is already there, so a restart never re-announces
        old videos.
        """
        state = self._load()
        videos = self._videos()
        if "seen" not in state:
            state["seen"] = sorted(videos)
            self._save(state)
            return []
        seen = set(state["seen"])
        now = time.time()
        new = [n for n, mtime in videos.items() if n not in seen and now - mtime > SETTLE]
        if new or seen - set(videos):
            # Forget trashed videos so the list stays small; keep ones still settling unseen.
            state["seen"] = sorted((seen & set(videos)) | set(new))
            self._save(state)
        for name in new:
            caption = (captions or {}).get(name, "")
            first = caption.strip().splitlines()[0] if caption.strip() else "Tap to post it."
            await self.notify(f"Ready to post: {Path(name).stem}", first)
        return new


async def watch_loop(push: Push, captions, interval: float = 15.0) -> None:
    """``captions()`` returns the posting queue's captions by file name."""
    while True:
        try:
            await push.check_new_videos(captions())
        except Exception:  # noqa: BLE001
            log.exception("push watcher failed")
        await asyncio.sleep(interval)
