# Script format (library/batch_NN.json = JSON array of these)

Measurements of the three reference reels: `reference-study.md`. A script is a short rom-com movie with a
meaning of its own, never a lesson: a situation, 2-6 short natural lines, the comedy in the picture and
the timing, and a payoff that says something about the two people (she says no and leaves a lipstick
kiss; the crash victim is the ski teacher). Write the story first; English is just the language they
speak. `phrase`, `words`, `hook_vi` and `cta_vi` are optional social-caption metadata; nothing of them
appears in the video, and the "new words" card is added only when `words` is present (the default is no
card: the reel ends on its last frame like the references).

```json
{
  "id": "ME-0001",
  "title_en": "Rain Check",
  "title_vi": "Hẹn dịp khác nhé",
  "genre": "romcom",
  "level": "B1",
  "cast": ["VIV", "JAMIE"],
  "wardrobe": {"VIV": "coat", "JAMIE": "city"},
  "setting": "Rain-soaked West Village street at dusk, late 1990s, outside a small cafe with a striped awning, yellow cabs, wet cobblestones reflecting warm shop lights",
  "phrase": {
    "en": "take a rain check",
    "vi": "hẹn dịp khác",
    "type": "idiom",
    "explain_vi": "Lịch sự từ chối lời mời bây giờ nhưng ngầm hứa sẽ nhận vào dịp khác.",
    "example_en": "I'm busy tonight. Can I take a rain check?",
    "example_vi": "Tối nay mình bận. Hẹn bạn dịp khác nhé?"
  },
  "hook_vi": "Từ chối crush kiểu sang chảnh 😏",
  "shots": [
    {"id": "S1", "sec": 4, "framing": "wide", "cast": ["VIV", "JAMIE"], "action": "Viv shelters under a narrow cafe awning in pouring rain, arms crossed, no umbrella; Jamie walks up holding a big black umbrella and stops beside her.", "line": null},
    {"id": "S2", "sec": 4, "framing": "close", "cast": ["JAMIE"], "action": "Jamie under his umbrella, rain behind him, looks at her with a lopsided grin.", "line": {"who": "JAMIE", "en": "Need an umbrella?", "vi": "Cần ô không?"}},
    {"id": "S3", "sec": 4, "framing": "close", "cast": ["VIV"], "action": "Viv raises one brow, unimpressed.", "line": {"who": "VIV", "en": "Is that a pickup line?", "vi": "Đang tán tỉnh tôi đấy à?"}},
    {"id": "S4", "sec": 4, "framing": "close", "cast": ["JAMIE"], "action": "Jamie shrugs innocently.", "line": {"who": "JAMIE", "en": "It's an umbrella.", "vi": "Đây là cái ô mà."}},
    {"id": "S5", "sec": 4, "framing": "close", "cast": ["VIV"], "action": "Viv gives a sweet fake smile and turns to leave.", "line": {"who": "VIV", "en": "I'll take a rain check.", "vi": "Để dịp khác nhé."}},
    {"id": "S6", "sec": 4, "framing": "wide", "cast": ["VIV"], "action": "Viv steps proudly off the curb; a yellow cab drives through a puddle and drenches her head to toe; she freezes, mouth open.", "line": null},
    {"id": "S7", "sec": 4, "framing": "two-shot", "cast": ["VIV", "JAMIE"], "action": "Jamie calmly steps in and holds the umbrella over the soaked Viv, grinning.", "line": {"who": "JAMIE", "en": "Rain check's here.", "vi": "Dịp khác tới rồi đây."}},
    {"id": "S8", "sec": 4, "framing": "close", "cast": ["VIV"], "action": "Viv, dripping wet under his umbrella, glares, then a small smile breaks.", "line": {"who": "VIV", "en": "You're buying coffee.", "vi": "Anh mời cà phê đấy."}}
  ],
  "twist": "Her elegant brush-off is undone by a cab splash a second later; the 'rain check' arrives instantly.",
  "cta_vi": "Bạn sẽ nói gì nếu là Viv? Comment bằng tiếng Anh nhé 👇"
}
```

## Rules (check.py enforces the countable ones)
- 4-12 shots, `sec` 0.5-9 each (mix 1.5-2.5 s reactions with 4-7 s takes), 14-32 s total; 2-6 spoken lines, each ≤ 8 words, one line per shot, one speaker per shot.
- With a `phrase`, it (any inflection) appears in one spoken line, word for word; without one the lines
  are whatever the story needs. Never bend a line to teach a word.
- A speaker is never filmed from behind; a line shot is `ots`, `two-shot`, `close`, `medium` or `ecu` with the speaker's face visible.
- Cover a conversation like the reference reels: each line is a single `close` or `medium` of the speaker alone, eyes on the other person just outside the frame beside the camera; a `wide` shows both people and the place when something physical happens; `two-shot` only for a physical beat with both in frame. `ots` exists but reads cramped and unnatural: avoid it. Payoffs are small and visual (a dollar on the counter, a lipstick kiss on a napkin, a look back at the door).
- Line 1 within the first 5 s; the hook is a situation, never a greeting or a lesson.
- The last shot is the payoff: a twist, a callback to the phrase, or a romantic beat. No moral, no teacher voice.
- Every shot is one simple filmable action in one place; physical comedy is simple (a splash, a slip, a door, a reveal).
- Cast keys and wardrobe keys come from series/cast.json; extras are described in `action` (a waiter, a cab driver), never named recurring people.
- Natural, idiomatic modern English; no slang that dates fast, nothing crude, no brand names, no real people.
- `vi`: natural spoken Vietnamese with the same tone and humour (anh/em/tôi/cậu chosen by relationship), not word-by-word.
- `words` (optional): 2-3 items `{en, vi}` for an end card; leave it out for a pure story reel. `hook_vi` ≤ 8 words; `cta_vi` invites a comment in English.
- No two scripts share a `phrase` across the whole library.
- Optional shot fields: `state` (a string, or `{"VIV": "soaked"}` for one person), `hold` (seconds kept after the line), `still` (share a named still), `still_pose`, and `first` (an absolute path to a frame you supply, used as the first frame instead of a generated still; muse keeps that face only in that frame's own scene).
