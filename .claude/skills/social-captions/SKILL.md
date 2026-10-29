---
name: social-captions
description: Write one caption per social platform (YouTube Shorts title + description, TikTok, Facebook Reels, Instagram Reels, X, Threads) for a finished museai video, each to that platform's own rules (length, fold, hook, hashtags, keywords, CTA) so the post can spread, check them with scripts/captions.py, and hand them to deliver.sh so the dashboard's "Ready to post" queue copies the right one per platform. Use for every delivered video (muse-video, scenic-drop-reel, teaching-video, zoominview) and for "write captions", "caption for TikTok/YouTube/X", "per-platform captions", "viết caption".
---

# Social captions

Paths are relative to this folder (`.claude/skills/social-captions/`). Rules and sources:
`references/platforms.md` (researched 2026-10-29). Platform ids match the dashboard
(`src/museai/api/routes/posting.py` `PLATFORMS`): `youtube`, `tiktok`, `facebook`, `instagram`, `x`, `threads`.

## Output
`captions.json` in the video's work folder (trashed with it after delivery):
```json
{"youtube": "<title>\n\n<description>", "tiktok": "...", "facebook": "...",
 "instagram": "...", "x": "...", "threads": "..."}
```
`python3 scripts/captions.py template > captions.json` prints the empty shape. Then
`python3 scripts/captions.py check captions.json` must print PASS (errors = hard limits; fix every
WARN too unless you have a reason). Deliver with `CAPTIONS_FILE=captions.json` (see muse-video
`scripts/deliver.sh`): it re-runs the check, then saves all six to the dashboard, where each platform
button copies its own caption and every caption can be edited in its tab.

## Write
Start from the video itself: its topic, the situation or place, the one thing a viewer gets (a phrase,
a grammar point, a view), and the language of the audience. Then write each platform separately;
never paste one caption six times with different hashtags.

1. **Hook (first line, every platform)**: a question, a promise or a surprise the viewer wants
   answered, with the search keyword in the first 5-8 words. Fits the fold: ≤ 55 characters for
   Instagram, ≤ ~90 for TikTok, ≤ ~120 for Facebook. Never open with a hashtag, the video length or
   "X in N seconds".
2. **Body**: one or two short lines naming what the viewer learns or sees, using the words people
   search (Vietnamese search terms for Vietnamese learners, plus the Chinese phrase itself; the
   place name and region for travel).
3. **CTA**: one short ask the platform rewards (below).
4. **Hashtags**: topic tags only (never `#fyp`, `#viral`, `#foryou`), at the end, per-platform count.

| id | Shape | CTA | Hashtags |
|---|---|---|---|
| `youtube` | title line (≤ 100, keyword in first ~60, 0-2 emoji), blank line, description: 1-2 keyword sentences, CTA, hashtags | subscribe / comment / next episode | 3-5 in the description, `#Shorts` last |
| `tiktok` | hook line, 1-2 lines with long-tail search phrases | comment, save, share | 3-5 |
| `facebook` | hook ≤ 120, 1-2 lines, conversational | comment, send to a friend | 0-3 |
| `instagram` | hook ≤ 55, 1-2 lines, line breaks | save, send to a friend | ≤ 5 (hard) |
| `x` | one or two short lines, ≤ 280 weighted (hanzi, emoji and Vietnamese letters like ế/ạ count 2) | a real question to reply to | 0-2 |
| `threads` | conversational, 1-3 short lines, ≤ 500 | open question inviting replies | exactly 1 topic tag |

## Series conventions
- **EVERYDAY CHINESE** (Vietnamese learners, user rule 2026-10-27/28): every caption in Vietnamese.
  YouTube title is `Tập NN | <hook>` under ~60 characters with the emoji, naming the everyday
  situation as a question or promise (e.g. `Tập 18 | Quán hết chỗ? Nói câu này là được ngồi chung bàn ☕`),
  never a long "muốn … thì nói tiếng Trung thế nào?" sentence. Hooks on other platforms drop the
  `Tập NN |` prefix. The hook names an urgent everyday dilemma (ordering food, Wi-Fi, a charger,
  haggling, a seat) or a wrong habit (`Đừng nói "Nǐ hǎo" khi vào quán ăn!`), never the grammar or a word list.
  Put the key Chinese phrase (hanzi + pinyin + Vietnamese) in the body. The CTA is the episode's quiz:
  "Comment câu trả lời của bạn bên dưới xem đúng không nhé!" (comments are what every platform rewards).
  Tags from `#hoctiengtrung #tiengtrung #tiengtrunggiaotiep #learnchinese`.
- **Grammar lessons (teaching-video)**: Vietnamese; hook names the mistake or the pattern
  (`Bạn vẫn nói sai 了?`), body gives the pattern, CTA is the challenge as a comment quiz (as above);
  tags like `#nguphaptiengtrung #hoctiengtrung`.
  One `captions.json` per export (9:16 and 16:9 can share the text; YouTube title may differ).
- **Travel reels (scenic-drop-reel, zoominview)**: English unless asked; hook is curiosity or surprise
  ("This beach looks fake… but it's real", "POV: you finally made it to …"); body names the place and
  the spots shown; tags: place, country, `#travel` style topics. YouTube title: a scannable curiosity
  question or claim under 50 characters that is true of the place ("Is this the bluest ice on Earth? 🧊",
  "The most surreal beach on Earth"), never a format label ("Golden Hour reel", "Iceland in 15 seconds").

## Maintaining this skill
When a platform changes a limit or the user corrects a caption, update `scripts/captions.py` (`RULES`),
`references/platforms.md` and the dashboard limit in `posting.py` `PLATFORMS` together, then follow
muse-video's "Maintaining this skill" flow (branch, PR).
