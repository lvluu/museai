#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=2"]
# ///
"""MCP stdio bridge for the local museai gateway.

Lets Claude Code (the "leader") delegate self-contained prompts to the muse.ai
model through this machine's OpenAI-compatible gateway.

Register once:

    claude mcp add --scope user museai \
      --env MUSE2API_API_KEY=sk-museai-local-key \
      -- uv run /path/to/museai/scripts/muse_mcp.py
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from mcp.server.mcpserver import MCPServer

BASE_URL = os.environ.get("MUSE2API_BASE_URL", "http://127.0.0.1:18610").rstrip("/")
API_KEY = os.environ.get("MUSE2API_API_KEY", "")

# Never route localhost through an HTTP proxy inherited from the shell.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

mcp = MCPServer("museai")


def _request(method: str, path: str, payload: dict | None = None, timeout: float = 330.0) -> dict:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with _opener.open(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:800]
        raise RuntimeError(f"museai returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(
            f"museai gateway is not reachable at {BASE_URL} ({exc}). "
            "Start it with `just up` in the museai repo."
        ) from exc


@mcp.tool()
def muse_chat(
    prompt: str,
    system: str = "",
    model: str = "muse-chat",
    timeout_seconds: int = 300,
) -> str:
    """Delegate a self-contained prompt to the muse.ai model and return its text reply.

    muse.ai is stateless per call: include every bit of context the task needs.
    It has no tool access, so delegate text work only — analysis, drafts, code,
    reviews, brainstorming, translation.

    Args:
        prompt: The full task and context.
        system: Optional system instructions.
        model: Gateway model id; muse-chat is primary. Aliases such as gpt-4o,
            claude-sonnet-4, deepseek-chat map to the same upstream model.
        timeout_seconds: Upstream generation budget.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    data = _request(
        "POST",
        "/v1/chat/completions",
        {"model": model, "messages": messages, "stream": False},
        timeout=timeout_seconds + 30,
    )
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"museai returned no choices: {json.dumps(data)[:500]}")
    return choices[0]["message"].get("content") or ""


@mcp.tool()
def muse_models() -> str:
    """List the model ids exposed by the local museai gateway."""
    data = _request("GET", "/v1/models", timeout=30)
    return "\n".join(m["id"] for m in data.get("data", []))


@mcp.tool()
def muse_status() -> str:
    """Report gateway health, driver readiness, and account-pool stats."""
    health = _request("GET", "/healthz", timeout=10)
    ready = _request("GET", "/readyz", timeout=10)
    return json.dumps({"health": health, "ready": ready}, indent=2)


if __name__ == "__main__":
    mcp.run()
