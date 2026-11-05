---
name: character-bank
description: Bank of real-looking recurring characters (original faces) shared by every museai video skill - one card per character (fixed identity text, build, voice, base wardrobe) plus reference portraits (front hero, three-quarter, full-length) rendered through muse with photo-realism rules learned from Seedance/Seedream practice (real skin texture, window light, 85 mm lens, no beauty words). Puts bank characters into any new scene with their portraits attached as reference images, so the same face comes back in every video. Use for "character bank", "save this character", "make a new character", "reuse <name>", "make the characters look more real", or before any video that needs a recurring person.
---

# character-bank

Paths are relative to this folder. Cards and portraits: `bank/<KEY>/` (`card.json`, `hero.jpg`,
`three_quarter.jpg`, `full.jpg`). Script: `scripts/bank.py` (`list`, `body`, `render`, `keep`, `scene`).
The realism block `prompt/real.txt` is appended to every bank prompt; change the rules there.

## Why it looks real (Seedance/Seedream practice, 2026-11 study)
- Photo language, not beauty words: camera, 85 mm f/2, window light at 45 degrees. Side light shows pores;
  flat frontal light hides them. "Flawless", "perfect skin", "model", "gorgeous", "8K" and "masterpiece"
  push toward the plastic AI face, so cards and prompts never use them.
- Texture is named: fine pores, vellus hair, uneven tone, faint redness, under-eye shadow, slight shine,
  asymmetry, flyaway strands, fabric creases.
- No grain in the portraits. Grain crawls once the still becomes a video, and the user rejected it.
- Identity is a fixed block in `card.json`, pasted the same way every time: age, origin, face shape, eyes,
  brows, nose, lips, hair, 1-2 sided marks (a dimple on the LEFT, earrings). Never "looks like" a real person.
- Consistency comes from references, not seeds. muse has no seed, so the same portraits are attached in the
  same order, with "X is the person in image 1".
- Keep the reference set small: hero + full per person (Seedance advice is 4-5 images at most, character
  first). The three-quarter view is kept in the bank for edits, not attached to scenes.

## Add or refresh a character
1. Write `bank/<KEY>/card.json`. Copy a card. `identity` = face and hair only, no style or beauty words.
   `version` goes up when the face changes.
2. `python3 scripts/bank.py render KEY hero ~/Movies/museai/bank-takes` (2 takes, 5-15 min). Several
   characters go through one `../muse-video/scripts/render-queue` job file, one at a time.
3. Pick a take by eye at 100 %. Reject:
   - plastic or airbrushed skin, razor-sharp detail;
   - a face older than the card age;
   - a famous-looking face;
   - a mark on the wrong side;
   - text in the frame.

   Then `python3 scripts/bank.py keep KEY hero <take>.png`.
4. Render `three_quarter` and `full` the same way. They attach `hero.jpg`, so the face stays. Keep them.
5. Commit the card and the portraits. They are our own renders, never someone else's footage.

## Use a character in a video
- **Still of a scene:**
  ```bash
  python3 scripts/bank.py scene OUT "SCENE TEXT" VIV JAMIE --look ../movies-english/prompt/look.txt
  ```
  It attaches each person's hero + full, binds them by name, and adds the card identity and the realism block.
  The skill's own look file can go in `--look`. Pick a take, then use it as the video's first frame
  (`IMAGE=`, muse-video).
- Video skills paste the card `identity` verbatim into shot prompts, like `cast.json` does today.
- Reference images need the museai server to accept `image` on `/v1/images/generations` (one data URL or a
  list). A server started before that change ignores the field.
