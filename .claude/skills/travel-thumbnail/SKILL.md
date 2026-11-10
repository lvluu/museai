---
name: travel-thumbnail
description: Make the cover image (thumbnail) for every finished travel / place video made through museai (scenic-drop-reel, zoominview, muse-video travel mode) - picks the sharpest, most colourful frame of the shots, grades it a little punchier and adds a short yellow hook line, the place name in big letters and country + flag in the upper band, clear of TikTok/Reels UI. Runs automatically after the video is composed, before the preview; deliver.sh carries it to the Desktop. Use also for "thumbnail", "cover image", "ảnh bìa", "make a cover for this video".
---

# travel-thumbnail

Paths are relative to this folder (`.claude/skills/travel-thumbnail/`). Fonts and emoji come from `../scenic-drop-reel/scripts/compose.py`.

## When
Automatically, right after a travel video is composed (scenic-drop-reel step 7, zoominview step 6, muse-video travel mode after the render), before showing the preview. No need to ask.

## Run
```bash
uv run --no-project --python 3.12 --with pillow --with fonttools python scripts/thumbnail.py \
  --place "Geirangerfjord" --flag 🇳🇴 --country Norway --hook "7 waterfalls. 1 fjord." \
  --out ~/Movies/museai/reel-<slug>/reel-<slug>.thumb.jpg s1.mp4 s2.mp4 …
```
- **Clips**: the raw shots in plan order (hook shot first, it gets a small bonus), never the composed reel: its frames carry intro text, dips to black and transitions. zoominview / single-shot travel: pass the one clip and `--at clip.mp4@<s>` on the view, not the selfie.
- **Name**: `<video name without .mp4>.thumb.jpg` next to the video. `deliver.sh` copies it to the Desktop beside the video, and the dashboard trashes it with the video once every platform is posted.
- **Hook** (2-5 words, upper-case on the image): the same promise as the caption's first line, and true for the frame shown. "7 waterfalls. 1 fjord." over a frame without the falls reads as bait; pick another frame (`--at`) or another hook. Optional: leave it out for a calm documentary.
- `--country` + `--flag` go under the name; leave out `--country` when the place name already is the country.
- The frame is chosen by sharpness x colourfulness x exposure on 4 frames/s, skipping 0.5 s at each clip end (~50 s for 9 six-second shots). `--at clip.mp4@2.5` overrides it.
- Output keeps the source size: 9:16 shots → 1080x1920, 16:9 → 1920x1080 (type scales with the short side).

## Check
Open the jpg and look before the preview: text readable on the sky band, nothing important of the subject under the text, flag drawn (not a box), no muse watermark in the frame. Show it with the video preview.
