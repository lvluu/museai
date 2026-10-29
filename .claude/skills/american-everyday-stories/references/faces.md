# Original, beautiful, consistent faces

The user wants every character attractive and unique, and never a lookalike of a real person
(copyright, likeness rights and the "AI actor" look). Reference films like the one this skill was
built from tend to land on famous 1980s faces; these rules steer away from that.

## Designing a face (one per new character, recorded in cast.json `identity`)
1. Start from age, origin and build, then pick **one shape** (oval, heart, long, round, square,
   diamond) and **one dominant feature** (eyes, brows, jaw, smile, freckles).
2. Add **two or three asymmetric marks** with a side named: a beauty mark above the RIGHT lip
   corner, a crescent scar through the LEFT eyebrow, a dimple in one cheek only, a nose bent a
   little to one side, a gap in the teeth. These anchor identity across shots and make the face
   nobody else's.
3. Name **exact colours**: eye colour, hair colour and cut for the year, skin tone in plain words.
4. Beautiful = healthy skin with texture, clear eyes, good bone structure, kind or alive
   expression; never "flawless", "model", "doll-like", "perfect symmetry", "porcelain".
5. Never write "looks like", "resembles", a real actor's or model's name, a film role, or a
   decade's star ("a young Michelle Pfeiffer type"). The look block also says nobody resembles a
   real person.
6. Vary the cast: ages, builds, ethnicities and class plausible for the place and year, each an
   individual with their own job and wants, not a type.

## Reference stills (made 2026-10-30, in `series/refs/`; reuse for every shot)
`series/refs/<KEY>.png` (16:9 1920x1080 waist-up) and `<KEY>_face.png` (1024 square portrait) exist
for all six characters. A new character or a changed face gets new ones:
```bash
scripts/refs.sh NORA ~/Movies/museai/aes-refs      # two candidates; run every key in parallel
```
Pick the take whose face is most distinctive and least like anyone famous, then check by eye:
- **Age**: the image model ages people 10-20 years (first pass: Walt 63 looked 80, Grace 46 looked
  60, Danny 27 looked 40). `still` already says "looks exactly N"; if a take is still older, remove
  the ageing words from cast.json (weathered, deep lines, thinning, stooped, heavy lids, white
  brows, "silver hair" that turns the whole head grey) and say what the age looks like instead.
- **Sides**: LEFT/RIGHT mean the person's own side, the viewer's opposite. Muse still flips them
  often. A face with one sided mark may be mirrored (`ffmpeg -vf hflip`, Danny); otherwise retake.
- **Extra marks**: a mark repeated on both sides (Nora's beauty mark) is removed with a small
  `delogo` on the wrong one.
- Crop with the face a third from the top for the 16:9 still, and a square around the face.
When a still looks like a known person, change one mark or the face shape in cast.json and render
again; do not just re-roll.
Every shot with a recurring character then renders with `IMAGE=` a first-frame still built from
these refs (see SKILL.md "Shot stills"). Never pretend a reference exists: `episode.py build`
names the missing refs.
