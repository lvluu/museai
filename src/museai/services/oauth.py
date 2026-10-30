"""Connected social accounts: OAuth sign-in per channel and platform, and the token store.

The user signs in on the dashboard ("Connect" per channel and provider); the provider redirects back
to ``/dashboard/autopost/oauth/callback``, which trades the code for tokens. Tokens live in
``data/oauth.json`` (mode 600) and never leave the server: the dashboard only sees account names.

The developer apps (client id / secret) come from settings (``MUSE2API_GOOGLE_CLIENT_ID`` …), see
docs/auto-post.md for which apps to create, their scopes and audits.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from ..config import Settings
from .publishers.http import using
from .publishers.meta import GRAPH, VERSION

STATE_TTL = 900.0  # a sign-in must come back within 15 min
REFRESH_AHEAD = 300.0


@dataclass(frozen=True)
class Provider:
    name: str
    platforms: tuple[str, ...]
    auth_url: str
    scopes: tuple[str, ...]
    setting: str  # settings prefix of the app's id / secret


PROVIDERS = {
    "google": Provider("Google (YouTube)", ("youtube",), "https://accounts.google.com/o/oauth2/v2/auth",
                       ("https://www.googleapis.com/auth/youtube.upload",
                        "https://www.googleapis.com/auth/youtube.readonly"), "google"),
    "meta": Provider("Meta (Facebook + Instagram)", ("facebook", "instagram"),
                     f"https://www.facebook.com/{VERSION}/dialog/oauth",
                     ("pages_show_list", "pages_read_engagement", "pages_manage_posts", "business_management",
                      "instagram_basic", "instagram_content_publish"), "meta"),
    "tiktok": Provider("TikTok", ("tiktok",), "https://www.tiktok.com/v2/auth/authorize/",
                       ("user.info.basic", "user.info.profile", "video.publish"), "tiktok"),
}
PROVIDER_OF = {p: k for k, prov in PROVIDERS.items() for p in prov.platforms}
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
TIKTOK_TOKEN = "https://open.tiktokapis.com/v2/oauth/token/"


class OAuthError(Exception):
    pass


class OAuth:
    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.file = settings.data_dir / "oauth.json"
        self.http = http
        self._pending: dict[str, tuple[str, str, str, float]] = {}  # state -> provider, channel, redirect, at
        self._lock = threading.Lock()

    # --- storage ---

    def _load(self) -> dict:
        try:
            return json.loads(self.file.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save(self, data: dict) -> None:
        self.file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.file.with_suffix(".tmp")
        tmp.touch(mode=0o600)
        tmp.chmod(0o600)
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        tmp.replace(self.file)

    def _set(self, channel: str, platform: str, account: dict | None) -> None:
        with self._lock:
            data = self._load()
            accounts = data.setdefault("accounts", {}).setdefault(channel, {})
            if account is None:
                accounts.pop(platform, None)
            else:
                accounts[platform] = account
            self._save(data)

    def app(self, provider: str) -> tuple[str, str]:
        p = PROVIDERS[provider].setting
        s = self.settings
        return {"google": (s.google_client_id, s.google_client_secret),
                "meta": (s.meta_app_id, s.meta_app_secret),
                "tiktok": (s.tiktok_client_key, s.tiktok_client_secret)}[p]

    def view(self) -> dict:
        """What the dashboard may see: per channel and platform the account's name, never a token."""
        data = self._load()
        out: dict[str, dict] = {}
        for channel, accounts in data.get("accounts", {}).items():
            out[channel] = {p: {"name": a.get("name", ""), "connected": a.get("connected", 0),
                                "choices": [{"id": c["id"], "name": c["name"]} for c in a.get("choices", [])]}
                            for p, a in accounts.items()}
        return {"accounts": out,
                "providers": [{"id": k, "name": p.name, "platforms": list(p.platforms),
                               "configured": all(self.app(k))} for k, p in PROVIDERS.items()]}

    # --- sign-in ---

    def start(self, provider: str, channel: str, redirect: str) -> str:
        if provider not in PROVIDERS:
            raise OAuthError(f"unknown provider '{provider}'")
        client_id, secret = self.app(provider)
        if not client_id or not secret:
            raise OAuthError(f"{PROVIDERS[provider].name}: set the developer app's id and secret first "
                             "(docs/auto-post.md)")
        now = time.time()
        self._pending = {s: v for s, v in self._pending.items() if now - v[3] < STATE_TTL}
        state = secrets.token_urlsafe(24)
        self._pending[state] = (provider, channel, redirect, now)
        scopes = PROVIDERS[provider].scopes
        params = {"redirect_uri": redirect, "state": state, "response_type": "code"}
        if provider == "google":
            params |= {"client_id": client_id, "scope": " ".join(scopes), "access_type": "offline",
                       "prompt": "consent select_account", "include_granted_scopes": "true"}
        elif provider == "meta":
            params |= {"client_id": client_id, "scope": ",".join(scopes)}
        else:
            params |= {"client_key": client_id, "scope": ",".join(scopes)}
        return f"{PROVIDERS[provider].auth_url}?{urlencode(params)}"

    async def finish(self, state: str, code: str) -> tuple[str, str]:
        """Trade the callback's code for tokens and store the account; returns (provider, channel)."""
        pending = self._pending.pop(state, None)
        if not pending or time.time() - pending[3] > STATE_TTL:
            raise OAuthError("sign-in expired or not started here; press Connect again")
        provider, channel, redirect, _ = pending
        async with using(self.http) as http:
            if provider == "google":
                await self._google(http, channel, code, redirect)
            elif provider == "meta":
                await self._meta(http, channel, code, redirect)
            else:
                await self._tiktok(http, channel, code, redirect)
        return provider, channel

    async def _google(self, http: httpx.AsyncClient, channel: str, code: str, redirect: str) -> None:
        cid, secret = self.app("google")
        tok = _ok(await http.post(GOOGLE_TOKEN, data={"code": code, "client_id": cid, "client_secret": secret,
                                                      "redirect_uri": redirect, "grant_type": "authorization_code"}))
        res = await http.get("https://www.googleapis.com/youtube/v3/channels", params={"part": "snippet", "mine": "true"},
                             headers={"Authorization": f"Bearer {tok['access_token']}"})
        items = res.json().get("items", []) if res.is_success else []
        name = items[0]["snippet"]["title"] if items else "YouTube channel"
        self._set(channel, "youtube", {"name": name, "connected": time.time(),
                                       "access_token": tok["access_token"], "refresh_token": tok.get("refresh_token", ""),
                                       "expires_at": time.time() + tok.get("expires_in", 3600)})

    async def _meta(self, http: httpx.AsyncClient, channel: str, code: str, redirect: str) -> None:
        cid, secret = self.app("meta")
        short = _ok(await http.get(f"{GRAPH}/oauth/access_token", params={
            "client_id": cid, "client_secret": secret, "redirect_uri": redirect, "code": code}))
        long = _ok(await http.get(f"{GRAPH}/oauth/access_token", params={
            "grant_type": "fb_exchange_token", "client_id": cid, "client_secret": secret,
            "fb_exchange_token": short["access_token"]}))
        # Page tokens from a long-lived user token do not expire.
        pages = _ok(await http.get(f"{GRAPH}/me/accounts", params={
            "fields": "id,name,access_token,instagram_business_account{id,username}",
            "access_token": long["access_token"]})).get("data", [])
        if not pages:
            raise OAuthError("this Facebook login manages no Page; Reels post to a Page")
        fb = [{"id": p["id"], "name": p["name"], "page_id": p["id"], "access_token": p["access_token"]}
              for p in pages]
        ig = [{"id": p["instagram_business_account"]["id"],
               "name": "@" + p["instagram_business_account"].get("username", ""),
               "ig_user_id": p["instagram_business_account"]["id"], "access_token": p["access_token"],
               "profile_url": f"https://www.instagram.com/{p['instagram_business_account'].get('username', '')}/"}
              for p in pages if p.get("instagram_business_account")]
        now = time.time()
        self._set(channel, "facebook", {**fb[0], "connected": now, "choices": fb})
        if ig:
            self._set(channel, "instagram", {**ig[0], "connected": now, "choices": ig})

    async def _tiktok(self, http: httpx.AsyncClient, channel: str, code: str, redirect: str) -> None:
        key, secret = self.app("tiktok")
        tok = _ok(await http.post(TIKTOK_TOKEN, data={"client_key": key, "client_secret": secret, "code": code,
                                                      "grant_type": "authorization_code", "redirect_uri": redirect}))
        res = await http.get("https://open.tiktokapis.com/v2/user/info/",
                             params={"fields": "open_id,display_name,username"},
                             headers={"Authorization": f"Bearer {tok['access_token']}"})
        user = (res.json().get("data") or {}).get("user", {}) if res.is_success else {}
        self._set(channel, "tiktok", {"name": user.get("display_name") or "TikTok account",
                                      "username": user.get("username", ""), "connected": time.time(),
                                      "access_token": tok["access_token"], "refresh_token": tok.get("refresh_token", ""),
                                      "expires_at": time.time() + tok.get("expires_in", 86400)})

    def choose(self, channel: str, platform: str, choice: str) -> None:
        """Pick another Page / Instagram account from the ones the Meta login manages."""
        with self._lock:
            data = self._load()
            acc = data.get("accounts", {}).get(channel, {}).get(platform)
            pick = next((c for c in (acc or {}).get("choices", []) if c["id"] == choice), None)
            if not pick:
                raise OAuthError(f"no {platform} account '{choice}' on this login")
            acc.update(pick)
            self._save(data)

    def disconnect(self, channel: str, platform: str) -> None:
        self._set(channel, platform, None)

    # --- tokens for posting ---

    async def token(self, channel: str, platform: str) -> dict | None:
        """The channel's account for ``platform``, its access token refreshed when about to expire."""
        acc = self._load().get("accounts", {}).get(channel, {}).get(platform)
        if not acc:
            return None
        if acc.get("expires_at") and acc["expires_at"] - time.time() < REFRESH_AHEAD and acc.get("refresh_token"):
            provider = PROVIDER_OF[platform]
            cid, secret = self.app(provider)
            async with using(self.http) as http:
                if provider == "google":
                    tok = _ok(await http.post(GOOGLE_TOKEN, data={
                        "client_id": cid, "client_secret": secret, "refresh_token": acc["refresh_token"],
                        "grant_type": "refresh_token"}))
                else:
                    tok = _ok(await http.post(TIKTOK_TOKEN, data={
                        "client_key": cid, "client_secret": secret, "refresh_token": acc["refresh_token"],
                        "grant_type": "refresh_token"}))
            acc |= {"access_token": tok["access_token"], "expires_at": time.time() + tok.get("expires_in", 3600),
                    "refresh_token": tok.get("refresh_token") or acc["refresh_token"]}
            self._set(channel, platform, acc)
        return acc


def _ok(res: httpx.Response) -> dict:
    """The JSON of a token response; the error names only the status and the provider's error code."""
    try:
        body = res.json()
    except ValueError:
        body = {}
    if not res.is_success or "error" in body and not body.get("access_token") and not body.get("data"):
        err = body.get("error")
        code = err.get("code") or err.get("message") if isinstance(err, dict) else err
        raise OAuthError(f"sign-in failed: HTTP {res.status_code} {code or ''}".strip())
    return body

