---
name: stroke-order
description: Make a ~22 s vertical (9:16) "Cách viết từ <hanzi>" stroke-order Short - the word and its meaning on frame 0, every stroke drawn in order with a tick (current stroke highlighted), slow + natural Mandarin read, Vietnamese meaning, an example sentence and a CTA to the full lesson. No muse clips, no credits; rendered from stroke data. The daily 12:00 slot of the Chinese channel (dashboard kind "stroke"). Use for "stroke order video", "cách viết từ", "viết chữ Hán", "daily stroke short", "Chinese character writing video".
---

# stroke-order

Paths relative to `.claude/skills/stroke-order/`. Output file name MUST start with `stroke-` (the dashboard
books it in the Chinese 12:00 slot by that prefix).

## Make one
1. Pick a searched word (HSK1-3, 1-3 characters; the channel's stroke Shorts get their views from search).
2. Copy `words/xiexie.json` to `words/<slug>.json`: `word`, `pinyin` (tone-marked syllables), `tones` (1-4, 0 neutral),
   `vi` (meaning), `example` {zh, py, vi}, optional `cta`.
3. Render (downloads each character's stroke data once, from cdn.jsdelivr.net, into `scripts/.cache/hanzi/`):
```bash
uv run --no-project --python 3.12 --with pillow --with numpy --with soundfile --with edge-tts \
  python scripts/stroke.py words/<slug>.json ~/Desktop/stroke-<slug>.mp4
```
4. Captions: `social-captions` skill. Hook = the hanzi + what it means; pinned comment on YouTube links the
   "Trọn bộ" lesson of the same theme.

## Format
- 0-2.2 s: "Cách viết từ", the hanzi huge, tone-coloured pinyin, Vietnamese meaning (visible on frame 0), Mandarin read.
- Writing: 田字格 box per character, strokes in order (0.55 s each), counter "Nét i/n".
- Reveal: slow Mandarin read, "Nghĩa là: ...", example card read aloud. Outro CTA, last 0.35 s fades into frame 0 (loop).
- Safe zones: nothing above y 200, below y 1480, right of x 960 between y 900-1480.
- Length = 0.55 s x strokes + ~8 s: keep words under ~35 strokes total so the Short stays under 30 s.
