"""AI models Muse Hands can answer chat messages with: ChatGPT, Claude, and muse.ai itself.

A provider is listed only when it can run: ChatGPT needs ``MUSE2API_OPENAI_API_KEY``, Claude needs
``MUSE2API_ANTHROPIC_API_KEY``; ``muse`` goes through the local museai gateway and needs no key.
The chosen provider is kept in ``data/hands.json``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import httpx

from ..config import Settings
from ..drivers.base import ChatRequest
from ..errors import InvalidRequest
from .gateway import Gateway

Turn = tuple[str, str]  # ("user" | "assistant", text)
SYSTEM = "You are Muse Hands, a concise assistant answering in a Telegram chat on a phone."


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
