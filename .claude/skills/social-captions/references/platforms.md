# Platform caption rules (researched 2026-10-29)

Hard limits are enforced by `scripts/captions.py check`. Numbers marked *(unverified)* come from
secondary sources only; the checker uses the safer value. Instagram Help, TikTok Support, Meta and
Threads Help pages render only with JavaScript, so their rules come from sources that quote them.

| id | Hard limit | Fold ("… more") | Hashtags | Rewards |
|---|---|---|---|---|
| `youtube` | title 100, description 5,000 | ~70 chars of title in search; ~157 of description | 3-5 in the description, `#Shorts` last; > 60 → all ignored | viewed vs swiped away, retention, replays |
| `tiktok` | 4,000 (app; 2,200 via API) | ~70-100 chars (one line) | 1-5 topic tags (5 cap reported Aug 2025, unverified); no `#fyp` | watch time, completion, shares, comments, saves |
| `facebook` | 2,200 used (Reels cap unverified; posts allow 63,206) | ~125 chars | 0-3 (excess hurts) | originality, freshness, comments, shares, sends |
| `instagram` | 2,200 | ~125 in feed, ~55 on the Reels view | max 5 (since Dec 2025), topic labels | sends/shares, saves, watch time |
| `x` | 280 weighted (non-Premium) | none (post is short) | 0-2 | predicted replies, reposts, quotes, dwell, follows |
| `threads` | 500 | first 1-2 lines (unverified) | exactly 1 topic tag | replies, likes, profile taps, time spent |

## YouTube Shorts
- The title is the search and browse hook: primary keyword in the first ~60 characters, 0-2 emoji.
- The description is indexed: 1-2 natural sentences with the keywords people search, a short CTA
  (subscribe, comment, watch the next episode), then 3-5 hashtags ending with `#Shorts`.
- YouTube shows up to 3 hashtags above the title; hashtags must be relevant or the video risks removal.
- Tags field (500 chars combined) matters little for Shorts.

## TikTok
- TikTok reads the caption, on-screen text and speech for search: put the keyword phrase and hook in
  the first 5-8 words; never open with hashtags (they push the hook past the fold).
- Long-tail search phrases ("cách nói … bằng tiếng Trung", "how to …") beat generic tags; skip `#fyp`,
  `#viral`. The For You feed drives most views; search only ~4 %.
- CTA for comments, shares or saves; a few emoji and line breaks are fine, most readers see one line.

## Facebook Reels
- Meta's 2026 guidance puts originality first: no re-uploads, borders or cosmetic edits; same-day Reels
  surface more. A caption unrelated to the Reel is a recommendation risk.
- Hook in the first 80-120 characters; CTA that invites comments or "send to a friend".

## Instagram Reels
- Hashtags are topic labels, not a reach lever (Mosseri, Apr 2025); max 5 per post, none in comments.
- The first line is the whole caption for most viewers: keep it ≤ ~55 characters so it shows on the
  Reels view; put the search keyword in it and in on-screen text.
- Emoji count as 2 characters. Line breaks are fine. CTA for saves and sends.

## X
- 280 weighted characters for non-Premium accounts: Latin letters, digits and punctuation count 1;
  emoji, CJK (hanzi) and letters outside U+0000-10FF count 2 (Vietnamese letters with stacked marks
  such as ế, ạ, ộ live in U+1E00-1EFF, so they count 2); each URL counts 23; attached media counts 0.
- Lead with the hook, invite a reply with a real question; forced engagement bait can backfire.
- 0-2 hashtags; X ranks by predicted engagement per viewer, not hashtags.

## Threads
- 500 characters. One topic tag per post (only the first counts); it may contain spaces.
- All post text is searchable. Conversational, short paragraphs; end with a question that invites
  replies (replies are the strongest signal). Video beats plain text.

## Sources
- YouTube Help, *Find playlists & videos using hashtags*: https://support.google.com/youtube/answer/6390658 (3 hashtags above title, 60-hashtag rule)
- howmanywords.app, *YouTube Character Limits 2026*: https://howmanywords.app/blog/youtube-character-limits (title/description limits and folds)
- hashtagtools.io, *YouTube Shorts Hashtags: title vs description 2026*: https://hashtagtools.io/blog/youtube-shorts-hashtags-title-vs-description-2026
- Metricool, *TikTok SEO Guide 2026*: https://metricool.com/tiktok-seo/ (keyword placement, hashtag count, ranking signals)
- Postlia, *TikTok Caption Length*: https://postlia.com/blog/tiktok-caption-length (4,000 limit, ~70-char fold)
- omnisocials, *TikTok Character Limits*: https://omnisocials.com/tiktok-character-limits (app vs API, 5-hashtag report)
- dohoo, *Facebook Reels Best Practices 2026*: https://blog.dohoo.ai/blog/facebook-reels-best-practices/ (originality, freshness)
- Kompozy, *Facebook Reels caption character limit*: https://kompozy.io/specs/facebook-reels-caption-character-limit
- SocialKit, *Social Media Character Limits 2026*: https://socialk.it/en/tools/social-media-character-limits (folds, X Premium)
- StoryCut, *Instagram Hashtag Limit*: https://www.storycut.com/blog/instagram-hashtag-limit (5-hashtag cap, Mosseri quotes)
- lettercounter, *Instagram Reels Caption Length*: https://lettercounter.org/blog/instagram-reels-caption-length/
- clipspeed, *Instagram Reels Captions 2026*: https://www.clipspeed.ai/blog/instagram-reels-captions.html
- X developer docs, *Counting characters*: https://docs.x.com/fundamentals/counting-characters (weights, URL 23, NFC)
- Sprout Social, *Twitter algorithm 2026*: https://sproutsocial.com/insights/twitter-algorithm/
- pilotmyx, *What the X algorithm rewards*: https://pilotmyx.com/blog/what-x-twitter-algorithm-rewards
- PostEverywhere, *How the Threads algorithm works*: https://posteverywhere.ai/blog/how-the-threads-algorithm-works
- hashtagtools.io, *Threads tags vs hashtags*: https://hashtagtools.io/blog/threads-tags-vs-hashtags-one-topic-tag-2026
- SendCove, *Threads character limits*: https://www.sendcove.app/integrations/threads/character-limits
