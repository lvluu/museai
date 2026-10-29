# Posting times per platform (researched 2026-10-29)

The dashboard's "Ready to post" schedule (`src/museai/api/routes/posting.py` `TIMES`) gives each video a
slot (day + slot 1 or 2, two a day) and each platform its own time for that slot, in the audience's local
time (Buffer's studies report times that way). Vietnamese sources are blog guides, not large studies;
they agree with each other and with Buffer's evening peaks.

Audience per video (user rule 2026-10-29), set on the dashboard card, default from the caption language:
- **Vietnam** (Chinese lessons, Vietnamese captions): the table below in GMT+7.
- **Everyone** (travel reels, any other language): no single clock, so both slots use the table's evening
  column: slot 1 in London time (Europe's evening peak, US lunch), slot 2 in New York time (US evening
  peak, Asia's next morning).

The dashboard shows every time in the device's own clock, with the audience's clock beside it.

| Audience-local | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|---|
| YouTube Shorts | 12:00 · 20:00 | 12:00 · 20:00 | 12:00 · 19:00 | 12:00 · 19:00 | 12:00 · 17:00 | 11:00 · 19:00 | 11:00 · 19:00 |
| TikTok | 11:00 · 20:00 | 12:00 · 21:30 | 12:00 · 21:30 | 13:00 · 21:30 | 12:00 · 19:00 | 11:30 · 17:00 | 09:00 · 19:00 |
| Facebook Reels | 12:00 · 21:00 | 08:00 · 20:00 | 08:00 · 20:30 | 09:00 · 20:30 | 08:00 · 20:30 | 11:30 · 22:00 | 10:00 · 20:30 |
| Instagram Reels | 12:00 · 19:00 | 15:00 · 19:00 | 12:00 · 18:00 | 09:00 · 20:00 | 12:00 · 21:00 | 12:00 · 21:00 | 12:00 · 21:00 |
| X | 09:00 · 14:00 | 09:00 · 13:00 | 10:00 · 14:00 | 09:00 · 13:00 | 09:00 · 13:00 | 10:00 · 13:00 | 10:00 · 13:00 |
| Threads | 09:00 · 12:00 | 09:00 · 12:00 | 09:00 · 12:00 | 09:00 · 12:00 | 09:00 · 12:00 | 10:00 · 13:00 | 11:00 · 14:00 |

The slot's day and its "free / taken / passed" state follow YouTube's time. The other platforms may post
the same video earlier the same day (X and Threads peak in the morning, Facebook on weekday mornings).

## Why each row
- **YouTube Shorts** (Buffer, 1.8M videos, Jul 2026): evenings 18-21h dominate (Wed/Thu 19-20h, Mon/Tue
  20-21h); Friday 16-18h is the best day; Saturday 11h is the second window. Shorts keep resurfacing for
  days, so the hour matters less than on other platforms. Slot 1 sits in the Vietnamese lunch break.
- **TikTok** (Buffer, 7.1M posts, Sep 2026): evenings 18-23h strong, 12-17h weakest; Sunday 9h is the
  week's peak, Monday 11-13h, Thursday 13h, Friday 18h, Saturday 16-17h. Vietnamese guides: 11-13h and
  19-22h, strongest 19-22h. Sprout's Tue-Fri 14-18h conflicts with both, so it is not used.
- **Facebook Reels** (Buffer, 14M posts, Oct 2026, all post types): weekday mornings 7-9h (Thursday 9h is
  the peak), Monday 21-22h, Saturday 22h, Sunday 9-10h; afternoons are worst. Vietnamese guides for Reels:
  20-22h, 11:30-13h and 7-8:30h. Slot 1 takes the morning, slot 2 the Vietnamese evening peak.
- **Instagram Reels** (Buffer, 9.6M posts, Sep 2026): 18-23h, Wednesday 12h and 18h, Thursday 8-9h,
  Tuesday 15h and 19h, Friday-Sunday 21-22h. Slot 1 on days without a daytime peak uses lunch.
- **X** (Buffer, 8.7M posts: Tuesday 9h peak, Wednesday 9-10h, weekday 9-11h best; Sprout: Tue-Thu
  12-18h; both: evenings 18-23h and Saturday weakest): slot 1 in the morning, slot 2 early afternoon.
  Early replies, reposts and bookmarks drive reach, so post when people are scrolling.
- **Threads** (Buffer, 2.5M posts, Feb 2026): weekday mornings 6-11h strongest (Thursday 9h peak,
  Wednesday 12h), Saturday 10-11h, Sunday 11h; evenings weakest. Monday and Friday were not reported, so
  they use the weekday pattern.

Check each platform's own analytics after two or three weeks and adjust `TIMES` to when the account's
followers are online; content (hook, relevance) still matters more than the hour.

## Sources
- Buffer, YouTube: https://buffer.com/resources/best-time-to-post-on-youtube/
- Buffer, TikTok: https://buffer.com/resources/best-time-to-post-on-tiktok/
- Buffer, Facebook: https://buffer.com/resources/best-time-to-post-on-facebook/
- Buffer, Instagram: https://buffer.com/resources/when-is-the-best-time-to-post-on-instagram/
- Buffer, Threads: https://buffer.com/resources/the-best-time-to-post-on-threads/
- Buffer, X (8.7M posts) and Sprout Social, X: summarized by the user 2026-10-29
- Sprout Social: https://sproutsocial.com/insights/best-times-to-post-on-social-media/
- Seongon, TikTok (VN): https://seongon.com/blog/tiktok/khung-gio-dang-tiktok.html
- Seongon, Facebook (VN): https://seongon.com/blog/facebook/khung-gio-vang-dang-bai-facebook.html
- GHN, TikTok (VN): https://ghn.vn/blogs/tip-ban-hang/cac-khung-gio-dang-tiktok-len-xu-huong-nhieu-tuong-tac
- dangbaitudong.vn, Facebook Reels (VN): https://dangbaitudong.vn/blog/khung-gio-dang-reels-facebook-hieu-qua-2026/
- SocialBoost, Facebook (VN): https://socialboost.asia/vi-vn/blog/gio-vang-dang-bai-facebook-khung-gio-tuong-tac-cao-nhat
