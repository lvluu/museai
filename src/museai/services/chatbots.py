"""AI models Muse Hands can answer chat messages with: ChatGPT, Claude, and muse.ai itself.

A provider is listed only when it can run: Codex needs the ``codex`` CLI signed in (``codex login``), no key; ChatGPT needs ``MUSE2API_OPENAI_API_KEY``, Claude needs
``MUSE2API_ANTHROPIC_API_KEY``; ``muse`` goes through the local museai gateway and needs no key.
The chosen provider is kept in ``data/hands.json``.
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
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


# Work for the Codex agent: media jobs, code, files, the repo. Edit to taste.
AGENT_WORDS = re.compile(
    r"\b(videos?|clips?|reels?|images?|pictures?|photos?|thumbnails?|render|generate|draw|"
    r"code|script|bug|fix|refactor|repo|file|folder|commit|test|run|install|deploy|server|log|"
    r"video|ảnh|hình|tạo|vẽ|视频|图片|生成)\b", re.I)


@dataclass(frozen=True)
class Provider:
    id: str
    label: str
    model: str


def available(s: Settings) -> list[Provider]:
    found = []
    if shutil.which(s.codex_bin):
        found.append(Provider("auto", "Auto", "router"))
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

    def resolve(self, text: str) -> Provider:
        """The provider that answers ``text``: the chosen one, or in Auto mode the best fit.

        Auto: media / code / file work -> Codex (it can delegate to museai); everything else -> Claude,
        then ChatGPT, then Muse, whichever is available."""
        provider = self.current()
        if provider.id != "auto":
            return provider
        by_id = {p.id: p for p in self.providers()}
        if AGENT_WORDS.search(text) and "codex" in by_id:
            return by_id["codex"]
        return next(by_id[i] for i in ("claude", "chatgpt", "codex", "muse") if i in by_id)

    async def reply(self, history: list[Turn]) -> tuple[Provider, str]:
        """Answer the last user turn of ``history`` with the chosen provider."""
        provider = self.resolve(history[-1][1])
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
        """Run the message as a thread of the local Codex app-server, the one the Codex app uses.

        The thread is a normal app thread named "Muse Hands · Telegram" (visible in the ChatGPT / Codex app and
        `codex resume`); later messages continue it. Codex works as an agent in the repo (workspace-write,
        network on) so it can delegate video / image jobs to museai; only allow-listed chats reach it."""
        cwd = self.settings.agent_cwd or str(REPO)
        model = {"model": self.settings.codex_model} if self.settings.codex_model else {}
        proc = await asyncio.create_subprocess_exec(
            self.settings.codex_bin, "app-server", stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, limit=2**24)
        ids = iter(range(1, 10**6))

        async def send(method: str, params: dict) -> int:
            i = next(ids)
            proc.stdin.write((json.dumps({"jsonrpc": "2.0", "id": i, "method": method, "params": params}) + "\n").encode())
            await proc.stdin.drain()
            return i

        async def messages():
            while line := await proc.stdout.readline():
                yield json.loads(line)

        async def call(method: str, params: dict) -> dict:
            i = await send(method, params)
            async for m in messages():
                if m.get("id") == i and "method" not in m:
                    if "error" in m:
                        raise InvalidRequest(f"Codex: {m['error'].get('message', m['error'])}")
                    return m["result"]
            raise InvalidRequest("Codex app-server closed")

        async def run() -> str:
            await call("initialize", {"clientInfo": {"name": "Codex Desktop", "title": "Muse Hands", "version": "1"}})
            proc.stdin.write(b'{"jsonrpc":"2.0","method":"initialized"}\n')
            thread = self._read().get("codex_session")
            fresh = {"cwd": cwd, "approvalPolicy": "never", "sandbox": "workspace-write", **model}
            if thread:
                await call("thread/resume", {"threadId": thread, **fresh})
            else:
                thread = (await call("thread/start", {**fresh, "serviceName": "Muse Hands", "threadSource": "user", "developerInstructions": AGENT}))["thread"]["id"]
                self.file.write_text(json.dumps({**self._read(), "codex_session": thread}))
                await call("thread/name/set", {"threadId": thread, "name": "Muse Hands · Telegram"})
            await call("turn/start", {"threadId": thread, "input": [{"type": "text", "text": history[-1][1]}],
                                      "sandboxPolicy": {"type": "workspaceWrite", "networkAccess": True}, **model})
            answer = ""
            async for m in messages():
                if "id" in m and "method" in m:  # an approval or tool request: we run with approvals off
                    proc.stdin.write((json.dumps({"jsonrpc": "2.0", "id": m["id"], "error": {
                        "code": -32601, "message": "not supported"}}) + "\n").encode())
                    continue
                if m.get("method") == "item/completed" and m["params"]["item"].get("type") == "agentMessage":
                    answer = m["params"]["item"]["text"]
                if m.get("method") == "turn/completed":
                    turn = m["params"]["turn"]
                    if turn.get("status") == "failed":
                        raise InvalidRequest(f"Codex failed: {str(turn.get('error'))[:200]}")
                    return answer
            raise InvalidRequest("Codex app-server closed")

        try:
            return await asyncio.wait_for(run(), timeout=self.settings.agent_timeout)
        except asyncio.TimeoutError:
            raise InvalidRequest("Codex timed out") from None
        finally:
            if proc.returncode is None:
                proc.kill()
            await proc.wait()

    def new_session(self) -> None:
        """/new: the next Codex message starts a fresh session."""
        self.file.write_text(json.dumps({k: v for k, v in self._read().items() if k != "codex_session"}))

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
