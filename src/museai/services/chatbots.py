"""AI models Muse Hands can answer chat messages with: ChatGPT, Claude, and muse.ai itself.

A provider is listed only when it can run: Codex needs the ``codex`` CLI signed in (``codex login``), no key; ChatGPT needs ``MUSE2API_OPENAI_API_KEY``, Claude needs
``MUSE2API_ANTHROPIC_API_KEY``; ``muse`` goes through the local museai gateway and needs no key.
The chosen provider is kept in ``data/hands.json``.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import httpx

from ..config import Settings
from ..drivers.base import ChatRequest
from ..errors import InvalidRequest
from .gateway import Gateway

Turn = tuple[str, str]  # ("user" | "assistant", text)
SYSTEM = "You are Muse Hands, a concise assistant answering in a Telegram chat on a phone."
REPO = Path(__file__).resolve().parents[3]
AGENT = (
    SYSTEM + """ You run inside the museai repo (your working directory) and can use its tools.
- Plain questions: just answer, briefly.
- Video or image requests: delegate to museai (muse.ai) - never invent files. For a video read and follow
  .claude/skills/muse-video/SKILL.md (use its scripts, one render at a time); for an image POST
  /v1/images/generations on the local server http://127.0.0.1:18610 (key in data/api_key; never print that file
  or data/accounts.json). If the server is down, start it as the skill says.
- When a finished video or image exists, end your answer with one line per file: MEDIA: <absolute path>.
- Reply in the user's language, plain text, no markdown tables.""")


@dataclass(frozen=True)
class Provider:
    id: str
    label: str
    model: str


def available(s: Settings) -> list[Provider]:
    found = []
    if s.openai_api_key:
        found.append(Provider("chatgpt", "ChatGPT", s.openai_model))
    if s.anthropic_api_key:
        found.append(Provider("claude", "Claude", s.anthropic_model))
    if shutil.which(s.codex_bin):
        found.append(Provider("codex", "Codex", s.codex_model or "default"))
    found.append(Provider("muse", "Muse", "muse-chat"))
    return found


class ChatBots:
    def __init__(self, settings: Settings, gateway: Gateway, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.gateway = gateway
        self.http = client or httpx.AsyncClient(timeout=120)
        self.file: Path = settings.data_dir / "hands.json"

    def providers(self) -> list[Provider]:
        return available(self.settings)

    def current(self) -> Provider:
        chosen = self._read().get("model")
        options = self.providers()
        return next((p for p in options if p.id == chosen), options[0])

    def choose(self, provider_id: str) -> Provider:
        provider = next((p for p in self.providers() if p.id == provider_id), None)
        if provider is None:
            raise InvalidRequest(f"model '{provider_id}' is not available (missing API key?)")
        self.file.write_text(json.dumps({**self._read(), "model": provider.id}))
        return provider

    def _read(self) -> dict:
        try:
            return json.loads(self.file.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    async def reply(self, history: list[Turn]) -> tuple[Provider, str]:
        """Answer the last user turn of ``history`` with the chosen provider."""
        provider = self.current()
        if provider.id == "chatgpt":
            text = await self._openai(provider, history)
        elif provider.id == "codex":
            text = await self._codex(provider, history)
        elif provider.id == "claude":
            text = await self._anthropic(provider, history)
        else:
            transcript = "\n".join(f"{'User' if r == 'user' else 'Assistant'}: {t}" for r, t in history)
            text = await self.gateway.chat_complete(ChatRequest(
                prompt=f"{SYSTEM}\n\n{transcript}\nAssistant:", model=provider.model, turns=list(history)))
        return provider, text.strip() or "(empty answer)"

    async def _openai(self, p: Provider, history: list[Turn]) -> str:
        r = await self.http.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
            json={"model": p.model, "messages": [{"role": "system", "content": SYSTEM},
                                                 *({"role": r, "content": t} for r, t in history)]})
        _raise(r, "ChatGPT")
        return r.json()["choices"][0]["message"]["content"] or ""

    async def _codex(self, p: Provider, history: list[Turn]) -> str:
        """Ask the local Codex CLI (signed in with your ChatGPT account, no API key) as an agent in the repo.

        It may write inside the repo and reach the local museai server (workspace-write + network), so it
        can delegate video and image jobs; only allow-listed Telegram chats ever reach it."""
        transcript = "\n".join(f"{'User' if r == 'user' else 'Assistant'}: {t}" for r, t in history)
        with tempfile.TemporaryDirectory() as work:
            out = Path(work) / "answer.txt"
            cmd = [self.settings.codex_bin, "exec", "--sandbox", "workspace-write",
                   "-c", "sandbox_workspace_write.network_access=true", "--skip-git-repo-check",
                   "--ephemeral", "--ignore-user-config", "-C", self.settings.codex_cwd or str(REPO),
                   "-o", str(out)]
            if self.settings.codex_model:
                cmd += ["-m", self.settings.codex_model]
            proc = await asyncio.create_subprocess_exec(
                *cmd, "-", stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
            try:
                _, err = await asyncio.wait_for(
                    proc.communicate(f"{AGENT}\n\n{transcript}\nAssistant:".encode()),
                    timeout=self.settings.codex_timeout)
            except asyncio.TimeoutError:
                proc.kill()
                raise InvalidRequest("Codex timed out") from None
            if proc.returncode or not out.exists():
                raise InvalidRequest(f"Codex failed: {err.decode()[-200:]}")
            return out.read_text()

    async def _anthropic(self, p: Provider, history: list[Turn]) -> str:
        r = await self.http.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": self.settings.anthropic_api_key, "anthropic-version": "2023-06-01"},
            json={"model": p.model, "max_tokens": 1024, "system": SYSTEM,
                  "messages": [{"role": r, "content": t} for r, t in history]})
        _raise(r, "Claude")
        return "".join(b.get("text", "") for b in r.json()["content"])


def _raise(r: httpx.Response, name: str) -> None:
    if r.is_success:
        return
    try:
        detail = r.json()["error"]["message"]
    except (ValueError, KeyError, TypeError):
        detail = r.text[:200]
    raise InvalidRequest(f"{name} {r.status_code}: {detail}")
