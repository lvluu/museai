#!/usr/bin/env python3
"""PreToolUse guard: museai lives only in lvluu/museai. d4ncboz/museai is someone else's repo (the fork's parent):
never push, open PRs or post there. gh picks the fork parent when no repo is given, so `gh pr create` must name it."""
import json
import re
import sys

cmd = (json.load(sys.stdin).get("tool_input") or {}).get("command") or ""
why = None
if re.search(r"d4ncboz", cmd, re.I) and not re.match(r"\s*(gh\s+\S+\s+(view|list|diff|checks|status)|git\s+(log|show|fetch))\b", cmd):
    why = "d4ncboz/museai is not our repo: push, PRs and comments go to lvluu/museai only"
elif re.search(r"\bgh\s+pr\s+create\b", cmd) and not re.search(r"(--repo|-R)[\s=]+lvluu/museai\b", cmd):
    why = "gh pr create needs --repo lvluu/museai (without it gh may open the PR on the fork parent d4ncboz/museai)"
elif re.search(r"\bgit\s+(remote\s+(add|set-url)\b.*d4ncboz|push\s+upstream\b)", cmd):
    why = "no remote or push to d4ncboz/museai: origin (lvluu/museai) only"
if why:
    print(f"blocked: {why}", file=sys.stderr)
    sys.exit(2)
