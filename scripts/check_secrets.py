#!/usr/bin/env python3
"""Block credentials and private files from being committed or pushed.

This repository is public. The check runs from the git hooks in `.githooks/`
(enable them once with `just hooks`) and in CI.

    python scripts/check_secrets.py --staged          # pre-commit: the index
    python scripts/check_secrets.py --push < refs     # pre-push: outgoing commits
    python scripts/check_secrets.py --all             # CI: every tracked file

Besides generic token patterns, it looks for the exact values of this machine's
live secrets (data/api_key, the cookies in data/accounts.json, .env keys), so a
leaked muse.ai session is caught even when it matches no pattern.

A line ending in `secret-scan: allow` is skipped.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZERO = "0" * 40
MAX_BYTES = 5 * 1024 * 1024
ALLOW_MARK = "secret-scan: allow"

BLOCKED_PATHS = (
    "data/*",
    ".env",
    ".env.*",
    "*.key",
    "*.pem",
    "*.p12",
    "*.har",
    "*cookie*.txt",
    "*cookies*.json",
    "accounts.json",
    "*/accounts.json",
    "api_key",
    "*/api_key",
    ".claude/settings.local.json",
)
ALLOWED_PATHS = (".env.example",)

PATTERNS = {
    "private key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "GitHub token": r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{40,}",
    "AWS access key": r"\bAKIA[0-9A-Z]{16}\b",
    "Anthropic/OpenAI key": r"\bsk-(ant|proj)-[A-Za-z0-9_-]{20,}",
    "Slack token": r"\bxox[abprs]-[A-Za-z0-9-]{10,}",
    "Google API key": r"\bAIza[0-9A-Za-z_-]{35}\b",
    "museai generated key": r"\bm2a-[A-Za-z0-9_-]{30,}",
    "muse.ai session cookie": r"\b(hatch_sess|hatch_native_auth_device|hatch_vml|datr)\b[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9%:._-]{16,}",
    "Bearer token": r"\bBearer\s+[A-Za-z0-9._~+/-]{24,}",
    "home directory path": r"(/Users|/home)/[A-Za-z0-9._-]+/",
}
COMPILED = {name: re.compile(rx) for name, rx in PATTERNS.items()}


def git(*args: str, input: str | None = None) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, input=input, capture_output=True, text=True, check=True
    ).stdout


def live_secrets() -> list[str]:
    """Exact values of the secrets on this machine (empty in CI)."""
    found: set[str] = set()
    key_file = ROOT / "data" / "api_key"
    if key_file.is_file():
        found.add(key_file.read_text().strip())
    accounts = ROOT / "data" / "accounts.json"
    if accounts.is_file():
        try:
            data = json.loads(accounts.read_text())
        except ValueError:
            data = {}
        items = data if isinstance(data, list) else data.get("accounts", data)
        for acc in items if isinstance(items, list) else items.values():
            if isinstance(acc, dict):
                found.update(str(v) for v in (acc.get("cookies") or {}).values())
    env = ROOT / ".env"
    if env.is_file():
        for line in env.read_text().splitlines():
            name, _, value = line.partition("=")
            if re.search(r"KEY|TOKEN|SECRET|PASS|COOKIE", name, re.I):
                found.add(value.strip().strip("\"'"))
    return [s for s in found if len(s) >= 12]


def path_problem(path: str, size: int) -> str | None:
    if path in ALLOWED_PATHS:
        return None
    name = path.rsplit("/", 1)[-1]
    if any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(name, p) for p in BLOCKED_PATHS):
        return "private file (credentials / local state)"
    if size > MAX_BYTES:
        return f"file larger than {MAX_BYTES // 1024 // 1024} MB (media/render output?)"
    return None


def text_problems(text: str, secrets: list[str]) -> list[tuple[int, str]]:
    hits = []
    for no, line in enumerate(text.splitlines(), 1):
        if ALLOW_MARK in line:
            continue
        if any(s in line for s in secrets):
            hits.append((no, "live secret from data/ or .env"))
            continue
        for name, rx in COMPILED.items():
            if rx.search(line):
                hits.append((no, name))
                break
    return hits


def scan(files: dict[str, bytes], secrets: list[str]) -> list[str]:
    """`files` maps "path" or "path @ commit" to the file content."""
    errors = []
    for label, blob in sorted(files.items()):
        path = label.split(" @ ")[0]
        problem = path_problem(path, len(blob))
        if problem:
            errors.append(f"{label}: {problem}")
            continue
        if b"\0" in blob[:8000]:
            continue
        for no, what in text_problems(blob.decode("utf-8", "replace"), secrets):
            errors.append(f"{label}:{no}: {what}")
    return errors


def staged_files() -> dict[str, bytes]:
    names = git("diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR").split("\0")
    return {n: subprocess.run(["git", "show", f":{n}"], cwd=ROOT, capture_output=True).stdout
            for n in names if n}


def tracked_files() -> dict[str, bytes]:
    return {n: (ROOT / n).read_bytes() for n in git("ls-files", "-z").split("\0")
            if n and (ROOT / n).is_file()}


def pushed_files(refs: str) -> dict[str, bytes]:
    """Every file version added or changed by the commits about to be pushed."""
    files: dict[str, bytes] = {}
    for line in refs.splitlines():
        parts = line.split()
        if len(parts) != 4 or parts[1] == ZERO:
            continue
        local, remote = parts[1], parts[3]
        rng = [f"{remote}..{local}"] if remote != ZERO else [local, "--not", "--remotes"]
        for commit in git("rev-list", *rng).split():
            changed = git("diff-tree", "--no-commit-id", "-r", "--root", "--name-only", "-z",
                          "--diff-filter=ACMR", commit).split("\0")
            for n in filter(None, changed):
                blob = subprocess.run(["git", "show", f"{commit}:{n}"], cwd=ROOT,
                                      capture_output=True).stdout
                files[f"{n} @ {commit[:8]}"] = blob
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--push", action="store_true")
    mode.add_argument("--all", action="store_true")
    args = ap.parse_args()

    if args.staged:
        files = staged_files()
    elif args.push:
        files = pushed_files(sys.stdin.read())
    else:
        files = tracked_files()

    errors = scan(files, live_secrets())
    if not errors:
        return 0
    print("[secret-scan] blocked: this repo is public.", file=sys.stderr)
    for e in errors:
        print(f"  {e}", file=sys.stderr)
    print(f"Remove it, or end the line with '{ALLOW_MARK}' if it is a placeholder.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
