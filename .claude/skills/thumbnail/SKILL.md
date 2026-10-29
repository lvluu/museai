---
name: thumbnail
description: Make the thumbnails for a finished museai video - one 9:16 cover (YouTube Shorts, TikTok, Facebook / Instagram Reels) and one 16:9 thumbnail (YouTube video, Facebook feed) from the video's best frame, with a big readable hook title placed clear of faces and the platform UI - and hand them to deliver.sh, which puts them next to the video on the Desktop and the dashboard. Use after every video (muse-video, EVERYDAY CHINESE, scenic-drop-reel, zoominview, product-ad, teaching-video) before the final delivery, and for "thumbnail", "cover", "ảnh bìa", "ảnh thumbnail", "make a cover for this video".
---

# thumbnail

Every video posted from museai gets thumbnails (user rule, 2026-10-29). `deliver.sh` refuses a final
without `THUMB_DIR=` (or `NO_THUMB=1` for a video that will not be posted).

## Which sizes (researched 2026-10)

| Where | Shape | Size we make | Notes |
|---|---|---|---|
| YouTube Shorts | 9:16 | 1080x1920 | custom Shorts thumbnail: upload in YouTube Studio on a computer (verified channel); 9:16 recommended, min 640 high |
| YouTube video | 16:9 | 1920x1080 | JPG/PNG; Google recommends large (3840x2160 max), 2 MB limit from mobile, 50 MB desktop; a 16:9 thumbnail on a vertical video is replaced |
| TikTok | 9:16 | 1080x1920 | cover = a frame or an uploaded image; the profile grid crops the centre to 3:4 |
| Facebook / Instagram Reels | 9:16 | 1080x1920 | custom cover upload; grid and feed crop the centre to 3:4 / 4:5 / 1:1 |
| Facebook feed video | 16:9 | 1920x1080 | |

So two files cover everything: `<name>_9x16.jpg` and `<name>_16x9.jpg`. One 9:16 image cannot serve
YouTube long-form, and one 16:9 image is cropped badly on every vertical platform. Both stay under 2 MB.

**9:16 safe box**: all text inside x80-960 / y300-1560. That survives the centre crops to 3:4 (y240-1680),
4:5 (y285-1635) and 1:1 (y420-1500, keep the title low in the box), the right-hand button column
and the bottom 20 % (caption, username) on TikTok / Reels / Shorts. The 16:9 layout leaves the
bottom-right corner free of text (YouTube's duration badge).

**Alignment**: every line is centred, the series badge too (top of the safe box on 9:16, above the
text column on 16:9). On 9:16 the block is centred on the frame's centre line (x120-960,
symmetric, still clear of the button column); on 16:9 it is centred in the text column beside the faces
(centring on the whole frame would cover them).

## What makes it get clicked
- A real face with a clear emotion (smile, surprise) and eye contact; big enough to read at phone size.
- 2-5 words of title, huge, high contrast; it adds to the video title instead of repeating it.
- One focal point, bright saturated colour, no clutter; the same layout every episode so a series is recognisable.
- Never misleading: the picture is a real frame from the video.

## Make them
```
uv run --no-project --python 3.12 --with mediapipe==0.10.14 --with opencv-python-headless==4.10.0.84 \
    --with pillow==11.0.0 python scripts/thumb.py VIDEO OUT_DIR --title "..." [options]
```
- `--title` (required): 2-5 words in the viewer's language, uppercase, white on a red box.
- `--zh`: the big hook phrase in the taught language (yellow, above the title), e.g. the ending question.
- `--sub`: one small line under the title (a question or promise).
- `--badge`: series tag, centred at the top, e.g. `TẬP 33`.
- `--at T`: use this frame; without it, frames sampled at 4 fps are scored (all faces, eyes open, not
  mid-word, smiling, toward the lens, sharp) and `<name>_picks.jpg` shows the 6 best with times.
- `--skip 17.2-20.2,...`: never pick these spans (vocab cards, cuts, text cards).
- `--cut 0.6`: the video has burned-in captions from 60 % of the height down; that part is replaced by a
  blurred mirror of the scene. Better: run on the cut **before** captions are burned in, then no `--cut`.
- `--split [--view T]`: reaction on top, the view below (zoominview, any reel with a person reacting to a
  place); the view is the sharpest, most vivid frame without faces unless `--view` names one.
- `--name`: file prefix.
Prints `THUMB <file> <KB>`. Look at both images (and `_picks.jpg`) before delivering: face not
covered, text readable, frame not mid-blink. Re-run with `--at` from the picks sheet if needed.

Per kind of video:
- **EVERYDAY CHINESE**: `--zh "<ending question or key phrase>" --title "<topic in Vietnamese, uppercase>"
  --sub "Nói sao bằng tiếng Trung?" --badge "TẬP NN"`, skip the vocab-card span; frame of both people
  smiling at each other or at the lens.
- **zoominview**: `--split --title "<PLACE>" --sub "<wow line in the caption language>"`.
- **scenic-drop-reel / travel**: no faces → the most vivid sharp frame; `--title "<PLACE>"`, `--sub` the hook.
- **product-ad**: `--at` the hero product shot, `--title` the offer (3-4 words).
- **teaching-video**: run on each format's video; `--zh` the pattern, `--title` the lesson in Vietnamese.

## Deliver
Write them into the work folder (e.g. `WORK/thumbs`), then pass `THUMB_DIR=WORK/thumbs` to
`../muse-video/scripts/deliver.sh`. It copies them next to the video as
`<video name> - thumbnail 9x16.jpg` / `16x9.jpg` before it trashes the work folder; the dashboard's
"Ready to post" card shows both (click to download, drag into the upload page) and trashes them with
the video once it is posted everywhere.
