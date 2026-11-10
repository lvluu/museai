# Auto-posting

When a finished video lands in the posting folder (`MUSE2API_POST_DIR`, the Desktop), museai can
post it to TikTok, YouTube Shorts, Facebook Reels and Instagram Reels by itself, at the time of the
video's slot. X and Threads stay manual.

Everything is managed on `/dashboard` → **Auto-post**:

- **Plan**: each planned video with one tile per platform: time, caption, state, link once posted.
  Change a time, **Post now**, **Pause** a video, **Post by hand** (take it out of auto-posting),
  or **Pause all**.
- **Connected accounts**: per channel, a **Connect** button per provider. Facebook and Instagram
  pick the Page / IG account when the login gives several.
- **Rules**: which videos get planned, and how.

## How a video is planned

The posting queue (`data/posts.json`, the "Ready to post" cards) stays the single source of truth;
auto-posting adds an `auto` block to a card's entry.

1. A new video appears in the posting folder. The first enabled rule whose match fits plans it:
   - **source**: the skill that made it, by file name (`reel-*` scenic-drop-reel, `zoom-*`
     zoominview, `scenic-*` scenery-director, `travel-*`, `ad-*` product-ad, `lesson-*`
     teaching-video, `Tiếng Trung mỗi ngày*` everyday-chinese);
   - **pattern**: a file-name glob, such as `*Hà Nội*`;
   - **channel**: the card's channel.
   Empty fields match anything. Videos no rule matches stay manual and are listed under
   "Not auto-posted", where "Plan with rule…" plans one by hand.
2. The rule sets the channel (or keeps the card's), the platforms, the thumbnail (9x16 / 16x9 /
   none), the privacy and a caption template per platform. Templates take `{caption}` (the card's
   caption for that platform), `{title}` (its first line), `{name}` (file name) and `{channel}`.
3. Time per platform, first that applies: a time set on the plan tile → the rule's fixed times
   (`schedule: fixed`, next free HH:MM) → the card's slot with each platform's own offset (the
   times the "Ready to post" tiles show).

## How a video is posted

A loop in the server (`MUSE2API_AUTOPOST_INTERVAL`, 60 s) posts each due job. Job states:

| state | meaning |
|---|---|
| `scheduled` | waiting for its time |
| `waiting` | due, but the caption is still empty (auto captions retry, or type one) |
| `needs_account` | due, but the channel has no account connected for that platform |
| `posting` | uploading now |
| `retry` | failed; tries again after 1 min, 5 min, 15 min, 1 h, 3 h |
| `posted` | done; the platform is ticked on the card, the link shows on the tile |
| `error` | gave up (6 tries, or an error retrying will not fix, such as a rejected token) |
| `missed` | its time passed more than 2 h ago without starting (server off, paused, no account): it waits for **Post now** instead of posting a backlog at once |

When every platform of a card is ticked, the card goes to the Trash, the same as by hand.

**No double posts.** Each job (video × platform) keeps a checkpoint in `posts.json` that the driver
writes *before* each step that cannot be undone (TikTok `init`, YouTube upload session, Facebook
`finish`, Instagram `media_publish`). After a crash or restart the driver asks the platform where
that upload stands and finishes it, instead of starting a second one.

A video is picked up only 30 s after its file last changed, so a render still being written is
never uploaded.

## Going live: YouTube first

YouTube Shorts goes live first; the other platforms follow once it runs cleanly. New rules start
with YouTube Shorts only; tick more platforms on a rule when their accounts are connected.

1. Set up the Google app ([YouTube](#youtube-google-cloud) below), restart the server.
2. **Auto-post → Connected accounts → Connect** on each channel, sign in with that channel's
   Google account.
3. Add a rule per source you want posted (YouTube Shorts ticked, schedule = slot) and **Save rules**.
4. Watch the first video post: its tile turns `posted` with a youtube.com/shorts link. Uploads stay
   private until the API audit passes; send the audit once a few have gone through.

## Muse Hands (post from your phone)

`/dashboard/hands` lists every queued video with its state per platform and a **Post now** button
(phone-sized; from outside the laptop open `/dashboard/hands#key=<admin key>`).
The Telegram bot **Muse Hands** does the same from chat: `/posts` lists the videos, one button per
platform presses **Post now**; the auto-post loop then posts it within `MUSE2API_AUTOPOST_INTERVAL`.

1. Telegram → @BotFather → `/newbot` → copy the token.
2. `.env`: `MUSE2API_TELEGRAM_BOT_TOKEN=…`, restart, message the bot once: it replies with your chat id (the bot starts with no ids listed and serves nobody until you add yours).
3. `.env`: `MUSE2API_TELEGRAM_CHAT_IDS=<id>` (comma-separated for more), restart.

The bot also messages you by itself after every auto-post pass: ✅ posted (with link), and for a failure
(🔁 retrying, ❌ gave up, ⚠️ missed, 🔌 no account) two buttons instead of a question:
**Retry** and **Delete post** (to the Trash). A tap answers in the same message.

**Chat with an AI.** Any plain message to the bot is answered by the chosen model, with the last 20
turns as context. `/model` shows buttons (✅ marks the current one) for **ChatGPT**, **Claude** and
**Muse** (muse.ai through this gateway, no key); the choice is saved in `data/hands.json`. `/new`
starts a fresh conversation. ChatGPT and Claude appear once `MUSE2API_OPENAI_API_KEY` /
`MUSE2API_ANTHROPIC_API_KEY` are set (models: `MUSE2API_OPENAI_MODEL`, `MUSE2API_ANTHROPIC_MODEL`).

The server polls Telegram outbound only (no tunnel, no open port). Only listed chats are answered.
The laptop must be awake: while the bot runs, the server holds `caffeinate` (idle + system sleep on
power; `MUSE2API_KEEP_AWAKE=false` turns it off). A closed lid on battery still sleeps.

## Developer apps (one-time, by you)

Each platform needs a developer app of your own. Put its id and secret in `.env`, restart the
server, and the **Connect** buttons appear. Register this redirect URI in every app (the dashboard
shows the exact value):

```
<MUSE2API_PUBLIC_BASE or http://localhost:18610>/dashboard/autopost/oauth/callback
```

Tokens are stored in `data/oauth.json` (mode 600). The dashboard and the API never show them.

### YouTube (Google Cloud)

1. <https://console.cloud.google.com> → new project → **APIs & Services → Library** → enable
   **YouTube Data API v3**.
2. **OAuth consent screen**: External, add the scopes below, add your Google account as a test user.
3. **Credentials → Create credentials → OAuth client ID** → Web application → add the redirect URI.
4. `.env`: `MUSE2API_GOOGLE_CLIENT_ID=…`, `MUSE2API_GOOGLE_CLIENT_SECRET=…`

Scopes: `https://www.googleapis.com/auth/youtube.upload`, `https://www.googleapis.com/auth/youtube.readonly`.

Limits:

- Until the project passes Google's **YouTube API audit** (API compliance form), every upload is
  locked to **private**. Ask for the audit once auto-posting works privately.
- While the consent screen is in "Testing", the refresh token expires after 7 days: publish the
  consent screen (it can stay unverified for your own account) to keep the connection.
- Custom thumbnails need a phone-verified channel; without it the thumbnail step is skipped.
- Default quota is 10,000 units a day and an upload costs 1,600, so about 6 uploads a day.
- Videos are marked as altered/synthetic content (`containsSyntheticMedia`).

### Facebook Reels and Instagram Reels (Meta)

1. <https://developers.facebook.com> → **Create app** → use case "Other" → type **Business**.
2. Add **Facebook Login for Business**; in its settings add the redirect URI (`localhost` works while
   the app is in development mode).
3. The Instagram account must be a **Business or Creator** account linked to the Facebook Page.
4. `.env`: `MUSE2API_META_APP_ID=…`, `MUSE2API_META_APP_SECRET=…`

Permissions: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `business_management`,
`instagram_basic`, `instagram_content_publish`.

Limits:

- In development mode the app works for people with a role on the app (admins, developers, testers)
  without review. That covers your own Pages. For anyone else: **App Review** for each permission
  plus **Business Verification**.
- The login gives a long-lived Page token; museai lists every Page and linked IG account the login
  can manage, and the dashboard lets you pick one per channel.
- Instagram allows 50 API posts per account in 24 h.

### TikTok

1. <https://developers.tiktok.com> → **Manage apps → Connect an app**.
2. Add the products **Login Kit** and **Content Posting API**; in Content Posting API turn on
   **Direct Post**.
3. Scopes: `user.info.basic`, `user.info.profile`, `video.publish`.
4. Redirect URI: TikTok accepts **HTTPS only, no localhost**. Expose the server through a tunnel
   (for example `cloudflared tunnel --url http://localhost:18610`), set
   `MUSE2API_PUBLIC_BASE=https://<tunnel host>`, and register
   `https://<tunnel host>/dashboard/autopost/oauth/callback`. The tunnel is needed only while you
   click **Connect**; posting itself goes outbound.
5. `.env`: `MUSE2API_TIKTOK_CLIENT_KEY=…`, `MUSE2API_TIKTOK_CLIENT_SECRET=…`
6. Submit the app for review, then for the **Content Posting API audit**.

Limits:

- Until the audit passes, TikTok makes every post **private (SELF_ONLY)**, and at most 5 users may
  post through the app in 24 h. museai asks TikTok which privacy levels the account may use and
  picks the most public one.
- Posts are marked as AI-generated content (`is_aigc`).
- About 15 posts per account per day.

## Settings (`.env`)

| variable | default | meaning |
|---|---|---|
| `MUSE2API_AUTOPOST_ENABLED` | `true` | run the posting loop |
| `MUSE2API_AUTOPOST_MOCK` | `false` | dry run: every platform "posts" through the mock driver, nothing leaves the machine |
| `MUSE2API_AUTOPOST_INTERVAL` | `60` | seconds between checks |
| `MUSE2API_PUBLIC_BASE` | | public URL for the OAuth redirect (needed for TikTok) |
| `MUSE2API_GOOGLE_CLIENT_ID` / `_SECRET` | | YouTube |
| `MUSE2API_META_APP_ID` / `_SECRET` | | Facebook and Instagram |
| `MUSE2API_TIKTOK_CLIENT_KEY` / `_SECRET` | | TikTok |

Nothing is posted until an account is connected: a due job without an account waits in
`needs_account`, and after 2 h it turns `missed`.

## Files

| file | content |
|---|---|
| `data/autopost.json` | rules and the global pause |
| `data/posts.json` | each card's `auto` block: rule, platforms, time overrides, jobs with checkpoints |
| `data/oauth.json` | tokens per channel and platform (mode 600, never shown) |
| `data/autopost-mock.json` | what the mock driver "posted" |

## Code

- `src/museai/api/routes/autopost.py`: rules, planning, the posting loop, dashboard routes.
- `src/museai/services/oauth.py`: the three OAuth flows and token refresh.
- `src/museai/services/publishers/`: one driver per platform plus `mock.py`.
- `tests/test_autopost.py`: offline tests (mock driver and `httpx.MockTransport`).

### Muse Hands commands (replaces the pager bot)

Stop any other process polling the same token first (else Telegram `409 Conflict`).

| Command | Does |
|---|---|
| `/status` | Dashboard: channels × platforms left, tap a channel to drill in, tap a platform to post, ✅ Approve (asks to confirm) |
| `/approve <channel\|all> [platform]` | Post queued videos now (confirm button) |
| `/posts` | Every video, tap to post |
| `/postq` | Auto-post state counts |
| `/tasks`, `/job [id]`, `/cancel [id]` | Video renders: list, detail, cancel (latest if no id) |
| `/model`, `/new` | Pick chat AI, reset chat |

Make it yours: nothing personal is in the code. Your bot token, chat ids and AI keys live in `.env` (`MUSE2API_TELEGRAM_BOT_TOKEN`, `MUSE2API_TELEGRAM_CHAT_IDS`, ...), your look in `data/hands.json` (both untracked). Start from [hands.example.json](hands.example.json) (`cp docs/hands.example.json data/hands.json`); `channels` null = all channels in `posting.CHANNELS`.

Customize the look in `data/hands.json`:

```json
{"dashboard": {"title": "Posting", "platforms": ["youtube", "tiktok"], "channels": ["chinese"],
               "icons": {"youtube": "▶️"}, "hide_empty": true}}
```

`/task <prompt>` (Claude sessions) is not implemented.

### Chat with Codex (no API key)

`/model` lists **Codex** when the `codex` CLI is installed and signed in (`codex login`, your ChatGPT account). Each message runs `codex exec` as an agent in the museai repo (workspace-write sandbox, network on, ignoring `~/.codex/config.toml`). Video/image requests are delegated to museai through the `muse-video` skill and the local API; finished files named on a `MEDIA: <path>` line are sent back to the chat (≤50 MB). The bot stays responsive while Codex works (`MUSE2API_CODEX_TIMEOUT`, default 2400 s; `MUSE2API_CODEX_CWD` to change the working dir). Only chats in `MUSE2API_TELEGRAM_CHAT_IDS` reach it. Optional: `MUSE2API_CODEX_MODEL`, `MUSE2API_CODEX_BIN`.

### Auto mode (right model per message)

With Codex installed, `/model` also lists **Auto**: video / image / code / file requests go to Codex (which delegates to museai), everything else to Claude, then ChatGPT, then Codex, then Muse. Each answer ends with `— Auto → <model>`. Change the trigger words in `AGENT_WORDS` (`services/chatbots.py`).

Codex runs are real sessions: the first message starts one (id kept in `data/hands.json`), later messages resume it, so they appear in `codex resume` / the Codex app history and keep their context. `/new` starts a fresh session.
