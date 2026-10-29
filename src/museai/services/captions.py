"""Auto captions: write the per-platform captions a queued video is missing, through muse chat.

The rules are the social-captions skill's (SKILL.md and references/platforms.md, read at runtime so
there is one source), and its scripts/captions.py checks the result. Muse sees the file name, the
shared caption when there is one, and four frames of the video, so even a video delivered with no
caption at all gets a set.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import re
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from ..drivers.base import ChatRequest, InputImage
from .gateway import Gateway

log = logging.getLogger(__name__)

SKILL = Path(__file__).resolve().parents[3] / ".claude/skills/social-captions"
PLATFORMS = ("youtube", "tiktok", "facebook", "instagram", "x", "threads")
RETRY_AFTER = 1800.0  # a failed video is tried again after 30 min, not on every dashboard poll
JSON_BLOCK = re.compile(r"\{.*\}", re.S)


def _skill_check() -> Callable[[dict], tuple[list[str], list[str], list[str]]] | None:
    path = SKILL / "scripts/captions.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("social_captions", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.check


def _rules() -> str:
    parts = []
    for name in ("SKILL.md", "references/platforms.md"):
        try:
            parts.append((SKILL / name).read_text())
        except OSError:
            continue
    return "\n\n".join(parts)


def frames(path: Path, n: int = 4) -> bytes | None:
    """One JPEG with ``n`` frames spread over the video side by side; None without ffmpeg."""
    try:
        dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=20, check=True).stdout.strip())
        out = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(path), "-vf",
             f"fps={n / max(dur, 1):.4f},scale=360:-2,tile={n}x1", "-frames:v", "1",
             "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
            capture_output=True, timeout=60, check=True).stdout
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return out or None


def prompt(name: str, caption: str, missing: list[str], rules: str, errors: list[str]) -> str:
    lines = [
        "You write social media captions for a short vertical video. Follow these rules exactly:",
        "<rules>", rules or "(no rules file: keep each platform's length limit and topic hashtags)", "</rules>",
        f"Video file name: {name}",
        f"Its shared caption (the creator's own words, match its language and series): {caption}"
        if caption else "It has no caption yet: work out the topic, place and language from the file "
        "name and the attached frames (Vietnamese for Chinese lessons, English for travel).",
        f"Write the captions for: {', '.join(missing)}.",
        "Reply with only a JSON object mapping each of those platform ids to its caption text, "
        "no Markdown, no comments.",
    ]
    if errors:
        lines.append("Your last answer broke these limits, fix them: " + "; ".join(errors))
    return "\n".join(lines)


def parse(text: str, missing: list[str]) -> dict[str, str]:
    m = JSON_BLOCK.search(text)
    if not m:
        return {}
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {p: str(data[p]).strip() for p in missing if str(data.get(p) or "").strip()}


class CaptionWriter:
    """Writes missing captions one video at a time in the background."""

    def __init__(self, gateway: Gateway, enabled: bool = True) -> None:
        self.gateway = gateway
        self.enabled = enabled
        self._busy: set[str] = set()
        self._failed: dict[str, float] = {}
        self._tasks: set[asyncio.Task] = set()
        self._one = asyncio.Semaphore(1)  # one chat at a time: renders need the tabs more

    @staticmethod
    def missing(entry: dict) -> list[str]:
        own = entry.get("captions") or {}
        return [p for p in PLATFORMS if not own.get(p)]

    def status(self, key: str) -> str | None:
        if key in self._busy:
            return "writing"
        if key in self._failed:
            return "failed"
        return None

    def schedule(self, key: str, path: Path, entry: dict, save: Callable[[str, dict], None]) -> None:
        """Start writing ``key``'s missing captions unless it is in progress or failed recently.
        ``save(key, captions)`` stores the result (it fills only platforms still empty)."""
        missing = self.missing(entry)
        if not self.enabled or not missing or key in self._busy \
                or time.time() - self._failed.get(key, 0) < RETRY_AFTER:
            return
        self._busy.add(key)
        task = asyncio.create_task(self._run(key, path, entry.get("caption", ""), missing, save))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run(self, key: str, path: Path, caption: str, missing: list[str],
                   save: Callable[[str, dict], None]) -> None:
        try:
            async with self._one:
                captions = await self.write(path, caption, missing)
            if not captions:
                raise ValueError("muse returned no usable caption")
            await asyncio.to_thread(save, key, captions)
            self._failed.pop(key, None)
            log.info("auto captions for %s: %s", key, ", ".join(captions))
        except Exception as exc:  # noqa: BLE001 - a failed caption must not take the dashboard down
            self._failed[key] = time.time()
            log.warning("auto captions for %s failed: %s", key, exc)
        finally:
            self._busy.discard(key)

    async def write(self, path: Path, caption: str, missing: list[str]) -> dict[str, str]:
        """Captions for ``missing`` that pass the skill's hard limits (one retry with the errors)."""
        rules, check = await asyncio.to_thread(lambda: (_rules(), _skill_check()))
        image = await asyncio.to_thread(frames, path)
        images = [InputImage(image, "image/jpeg")] if image else []
        good: dict[str, str] = {}
        errors: list[str] = []
        for _ in range(2):
            todo = [p for p in missing if p not in good]
            text = await self.gateway.chat_complete(ChatRequest(
                prompt=prompt(path.name, caption, todo, rules, errors), model="muse-chat",
                # The rules are long and the frames upload first: muse often needs over a minute
                # before the first token, more while renders load the machine.
                images=images, first_token_timeout=180.0))
            got = parse(text, todo)
            if check:
                errs, _, _ = check({**dict.fromkeys(PLATFORMS, "-"), **got})
                errors = [e for e in errs if e.split(":")[0] in got]
                got = {p: t for p, t in got.items() if not any(e.startswith(f"{p}:") for e in errors)}
            good.update(got)
            if len(good) == len(missing):
                break
        return good
