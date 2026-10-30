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
