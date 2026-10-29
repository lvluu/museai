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

## Reference stills (make before Episode 1, reuse for every shot)
For each character, generate a front portrait and a three-quarter waist-up still through museai:
```bash
curl -s http://127.0.0.1:18610/v1/images/generations -H "Authorization: Bearer $(cat ~/Work/museai/data/api_key)" \
  -H 'Content-Type: application/json' \
  -d "$(python3 scripts/episode.py still NORA work)"   # prints the JSON body: identity + wardrobe + 1985 photo look
```
(never echo the key). Pick the take whose face is most distinctive and least like anyone famous,
check the marks are on the named side, and save it as `series/refs/<KEY>.png` (16:9 waist-up) and
`series/refs/<KEY>_face.png` (square portrait). When a still looks like a known person, change
one mark or the face shape in cast.json and render again; do not just re-roll.
Every shot with a recurring character then renders with `IMAGE=` a first-frame still built from
these refs (see SKILL.md "Shot stills"). Never pretend a reference exists: `episode.py build`
names the missing refs.
