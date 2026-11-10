# Platform profile specs (2026-11)

`scripts/kit.py` holds the same numbers (`LIMITS`, `HANDLE`, `ART`); change both together. Values marked
*(unverified)* come from secondary sources; the checker uses the safer one.

## Text limits
| Platform | Handle rule | Name | Bio / description | Notes |
|---|---|---|---|---|
| YouTube | 3-30 chars: letters, digits, `_` `-` `.` | 100 (aim ≤ 50) | description 1,000 | keywords field 500 chars; brand channel, not a personal one |
| Instagram | 1-30 chars: letters, digits, `_` `.`; no `..`, no trailing `.` | 30 *(64 in some apps, unverified)* | bio 150 | the Name field is searchable: put the keyword there |
| TikTok | 2-24 chars: letters, digits, `_` `.`; no trailing `.` | 30 | bio 80 | links in bio need 1,000 followers (business accounts earlier) |
| Facebook Page | username 5-50: letters, digits, `.` | 75 | intro 101, about 255 *(unverified)* | category *Digital creator* fits most video channels |
| X | 4-15 chars: letters, digits, `_` | 50 | bio 160 | the strictest handle: pick a handle X accepts and it fits everywhere |
| Threads | = Instagram handle | = Instagram | bio 150 | made from the Instagram account |

Emoji count as 2 characters on Instagram and X; the checker counts them so.

## Art sizes
| File | Size | Safe zone (centre) | From |
|---|---|---|---|
| `avatar.jpg` | 800 x 800 | circle, inner 80 % | avatar render; all platforms crop it to a circle, shown at ~110 px |
| `youtube_banner.jpg` | 2560 x 1440, < 6 MB | 1546 x 423 (shows on every device) | banner render |
| `facebook_cover.jpg` | 1640 x 624 | 1200 x 624 is what phones show *(Meta's own numbers vary)* | banner render |
| `x_header.jpg` | 1500 x 500 | centre 1500 x 360; avatar covers bottom-left | banner render |

TikTok and Instagram have no banner: the avatar, bio and the first 3 pinned videos are the "cover". Plan the
first 3 posts' covers (`thumbnail` skill) as a set in the channel's palette.

## Account setup
- **YouTube:** brand channel. Upload defaults: category, language, *not made for kids*, altered or synthetic
  content = Yes when photoreal AI. One playlist per pillar. Channel trailer = the best first video.
- **Instagram:** professional account, type *Creator*. AI-made: turn on the AI-generated profile label.
  Highlights: what the channel is, how it's made, vote next. Pin the 3 strongest reels.
- **TikTok:** switch to a business or creator account for analytics; AI-generated content label on every
  AI video.
- **Facebook:** a Page, not a profile. Link Instagram in Accounts Center; still post the original file on
  each (no cross-app watermark).
- **X:** media tab works as the portfolio; pin the best video.
- **Threads:** made from Instagram; one topic tag per post.
- **Chinese platforms (小红书, 抖音, B站, 视频号):** no external URL in bio or on screen ("搜 <name>" instead);
  Douyin real-name verification for links and live; set up each in its own app, no region-hopping VPN.

## AI disclosure (checked 2026-11-02)
- Instagram / Facebook: label every photoreal AI reel (*Add AI label* / *AI info*). Profiles featuring an
  AI-generated person: AI-generated profile label since 2026-08-31.
- YouTube: *altered or synthetic content* for realistic content; tick it when in doubt. Mass-produced,
  repetitive videos are not monetized: every video needs its own idea, shots and sound.
- TikTok: AI-generated content label on realistic AI video; unlabelled ones get removed.
- Say "AI-made" in the bio as well.

## Sources
- dream-life `references/account-kit.md` (the first kit), social-captions `references/platforms.md` and
  `posting-times.md`.
- YouTube handles: https://support.google.com/youtube/answer/11585688 ; banner: https://support.google.com/youtube/answer/2972003
- Instagram AI labels: https://iimagined.ai/blog/instagram-ai-label-rules-2026
- YouTube altered content: https://support.google.com/youtube/answer/14328491
