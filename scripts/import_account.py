#!/usr/bin/env python3
"""
import_account.py — Add a muse.ai account to a running museai server, then check its session.

Reads a cookie export (Cookie-Editor JSON, Netscape cookies.txt or a raw "a=b; c=d" header),
keeps only the session cookies, posts them to /admin/accounts and calls /renew on the new account.
Cookie values are never printed.

Usage:
    python scripts/import_account.py muse.ai_cookies.json --label muse-2 [--base http://127.0.0.1:18610]
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_cookies import parse_cookies_file  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIRED = ("hatch_sess", "hatch_native_auth_device")


def admin_key() -> str:
    env = {}
    env_file = os.path.join(ROOT, ".env")
    if os.path.exists(env_file):
        for line in open(env_file):
            if "=" in line and not line.lstrip().startswith("#"):
                name, value = line.strip().split("=", 1)
                env[name] = value
    key = os.environ.get("MUSE2API_ADMIN_KEY") or env.get("MUSE2API_ADMIN_KEY")
    if not key:
        key_file = os.path.join(ROOT, "data", "api_key")
        key = open(key_file).read().strip() if os.path.exists(key_file) else ""
    if not key:
        sys.exit("[!] Error: no admin key (set MUSE2API_ADMIN_KEY or start the server once to create data/api_key)")
    return key


def call(base: str, key: str, method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        base + path,
        method=method,
        data=json.dumps(body or {}).encode() if method != "GET" else None,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as exc:
        sys.exit(f"[!] {method} {path} failed: HTTP {exc.code} {exc.read()[:300].decode(errors='replace')}")
    except urllib.error.URLError as exc:
        sys.exit(f"[!] museai server not reachable at {base}: {exc.reason}")


def main():
    parser = argparse.ArgumentParser(description="Add a muse.ai account to a running museai server.")
    parser.add_argument("input", help="Cookie export file")
    parser.add_argument("--label", required=True, help="Account label, e.g. muse-2")
    parser.add_argument("--base", default="http://127.0.0.1:18610", help="museai server URL")
    args = parser.parse_args()

    # Session cookies only: UI cookies (theme, wd, dpr, ps_*) don't matter upstream.
    cookies = {k: v for k, v in parse_cookies_file(args.input).items() if k.startswith(("hatch_", "datr"))}
    missing = [name for name in REQUIRED if not cookies.get(name)]
    if missing:
        sys.exit(f"[!] Error: missing {', '.join(missing)}; export the cookies from a logged-in https://muse.ai tab")

    key = admin_key()
    base = args.base.rstrip("/")
    account = call(base, key, "POST", "/admin/accounts", {"label": args.label, "cookies": cookies})["account"]
    print(f"[+] Imported {account['label']} ({account['id']}) with cookies: {', '.join(sorted(cookies))}")

    renewed = call(base, key, "POST", f"/admin/accounts/{account['id']}/renew")
    meta = renewed.get("meta") or {}
    if not renewed.get("ok"):
        sys.exit(f"[!] Session check failed for {account['id']}; log in again, re-export the cookies and re-import")
    print(f"[+] Session check: ok session={meta.get('session_status')} vm={meta.get('vm_state')}")


if __name__ == "__main__":
    main()
