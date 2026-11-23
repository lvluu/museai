---
name: fb-weekly
description: Keep every Facebook Page (Slow Sunlit Days, Dream Jobs, Blue Eyes Wander, Chinese Everyday For Everyone) on track with Meta's creator weekly tasks ("Create 16 new public posts, 14 reels, 7 stories, reply to 5 comments, comment on 5 public posts"): read each Page's Creator Dashboard status, plan today's share, make the content from what the channel already produced (backlog reels published live, frames of published reels as photo posts and stories, replies and comments in the Page's voice), publish it from the Page, log it. Runs daily on its own without asking the user. Use for "weekly tasks", "weekly progress", "Facebook weekly status", "finish the page's weekly task", "what should the page post this week", or the daily fb-weekly run.
---

# fb-weekly

Paths are relative to this folder. Script: `scripts/fbweekly.py` (stdlib, state in `~/.config/museai/fb-weekly/`).
Pages, ids and voice: `pages.json`. The user said (2026-11-23): never ask what to do; do the week's tasks every
day until each Page is at 100 %. Ask only if a login is gone (then say so in one line and stop).

## Facts (measured 2026-11-23)
- Weekly tasks live at `https://www.facebook.com/professional_dashboard/status` after switching into the Page.
  The week runs Sunday to Saturday. Targets differ per Page and week; always read them, never assume.
- One reel counts as 1 reel + 1 public post + 1 story (Page reels share to story by default).
- Reels scheduled ahead in Business Suite (postq, 2 per day per Page) did **not** count: 3 published, 0 and 1
  counted. So everything this skill publishes is **published now** from the Page, never scheduled.
  `pages.json` `scheduled_counts` holds this; `fbweekly.py learn` re-checks it each Monday.
- The built-in browser (and the user's Chrome) is signed in as the user, who manages the Pages. Switch
  profile: avatar top right → the Page name (or `profile.php?id=<id>` → "Switch Now").

## Daily run (once a day, ~09:00 GMT+7)
For each page in `pages.json` with an `id`:
1. **Read status.** Switch into the Page, open the status URL, read the five `done/target` lines, then
   `python3 scripts/fbweekly.py record "<Page>" --posts 3/16 --reels 2/14 --stories 1/7 --replies 0/5 --comments 0/5 --focus "<focus>"`.
2. **Plan.** `python3 scripts/fbweekly.py plan --page "<Page>"` → today's `reel / photo / story / reply / comment` counts.
3. **Reels** (`reel N`): `python3 scripts/fbweekly.py backlog "<Page>" --n N` lists booked reels beyond the
   Business Suite window with their Facebook caption. Publish each now: `business.facebook.com/latest/reels_composer?asset_id=<asset_id>&business_id=<business_id>`,
   upload the `video`, paste the caption, Facebook only (untick Instagram), "Share to Facebook story" on, **Share**
   (not Schedule). Then `fbweekly.py mark-posted "<name>"` (postq will not schedule it again) and
   `fbweekly.py log "<Page>" reel --ref "<name>"`. Backlog empty → make the reel with the channel's skill
   (healing-video, dream-life, scenic-drop-reel, chinese skills) and note it in the run report.
4. **Photo posts** (`photo N`): `fbweekly.py assets "<Page>" --n N` gives fresh frames of already-published
   reels. Write a new caption in the Page's `voice` (2-3 short lines, a question to the reader, 2-3 hashtags; not
   the reel caption copied). Post from the Page now: Business Suite **Create post** (Facebook only) with the
   image → **Publish**. `fbweekly.py log "<Page>" photo --ref "<ref>" --text "<caption>"`.
5. **Stories** (`story N`): another `assets` frame → Business Suite **Create story** → Facebook → **Share**.
   `fbweekly.py log "<Page>" story --ref "<ref>"`.
6. **Replies** (`reply N`): Business Suite Inbox → Facebook comments (or the Page's newest posts). Reply as the
   Page to real comments not yet answered, in the Page's voice, 1-2 sentences, answer what they said. Skip spam
   and comments that need a human decision (complaints, collaboration offers): leave those for the user.
   `fbweekly.py log "<Page>" reply --ref "<comment id or post+author>" --text "<reply>"`.
7. **Comments** (`comment N`): as the Page, comment on its own newest public posts with a question that starts
   a conversation ("Which filling would you pick: red bean or pork?"). Never comment on other people's posts
   or pages. `fbweekly.py log "<Page>" comment --ref "<post url>" --text "<comment>"`.
8. Re-read the status (step 1) and `record` again so tomorrow's plan starts from Meta's own numbers.

Monday only: `fbweekly.py learn`. If counted ≈ live + scheduled for two weeks in a row, set `scheduled_counts` to
`true` (the plan then credits postq's scheduled reels and publishes fewer live reels), commit, PR.

## Rules
- Content quality is the channel's: captions follow `../social-captions/SKILL.md`; nothing repeats (`log --ref`
  makes `assets`/`backlog` skip what was used). No AI-looking text: no "Dive into", no emoji walls.
- Never delete, unschedule or edit posts the pipeline made. Never post on Instagram from here (postq does it).
- A Page without `id` in `pages.json` is skipped; fill the id when its login is available.
- End with one line per Page: `<Page> posts a/b reels a/b stories a/b replies a/b comments a/b, today: …`.
