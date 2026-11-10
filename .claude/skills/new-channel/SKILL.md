---
name: new-channel
description: Turn a channel idea or style into everything needed to open a new social channel on YouTube, Instagram, TikTok, Facebook, X and Threads - the brief (niche, audience, language), 3 name + handle options checked against each platform's rules, a visual style (look block for muse prompts, palette, font), avatar, YouTube banner, Facebook cover and X header rendered through museai, per-platform bios and descriptions within the character limits, keywords, hashtags, content pillars, AI disclosure, profile setup checklist and a first-30-days plan - as one kit (kit.json + KIT.md + art) that any team member can follow. Use for "new channel", "create a channel", "start an account", "channel kit", "channel name ideas", "bio for my channel", "avatar / banner / cover photo for a channel", "tạo kênh mới", or when someone gives an idea or style for a channel they want to open.
---

# new-channel

Paths are relative to this folder. Script: `scripts/kit.py`. One channel = one folder `channels/<slug>/`
(`kit.json`, `KIT.md`, `art/`, `takes/`). Platform limits and image sizes: `references/platform-specs.md`.
Launch plan, cadence, what not to do: `references/playbook.md`. Example kit: `templates/kit.example.json`
(the Dream Jobs account, the first channel we opened this way).

The member gives an idea ("calm Japanese countryside walks", "AI-graded English for CET students") or a
style (a few reference images, a mood). Everything else comes from this skill. Ask only what the idea leaves
open, in **one** message, with a proposed default for each:
1. Who watches (country / age / interest) and in which language the channel speaks.
2. One kind of video only, or several? (One. A channel that mixes lessons, travel and healing confuses the
   platforms' interest matching. A second kind = a second channel.)
3. Real person on camera, recurring AI character, or no person?
4. Which platforms (default: YouTube, Instagram, TikTok, Facebook; X and Threads optional).

## Steps
1. **Scaffold.** `python3 scripts/kit.py new <slug> "<idea in the member's words>"` → `channels/<slug>/kit.json`
   from the template. `<slug>`: short, lowercase, dashes.
2. **Brief.** Fill `idea`, `audience`, `language`, `niche`, `promise` (what a viewer gets from every video,
   one line), `ai_made` (true when images, video or voices are AI). Look up 3-5 channels already doing well in
   the niche and write in `notes` what they share (hook style, length, look) and the gap this channel takes.
3. **Names.** 3 options in `names[]`, each with `display`, `handle`, `why`. A good name:
   - says the series in 1-3 words a viewer could search (Dream Jobs, Tiny Magic Jobs), not the creator;
   - one handle that fits every platform (≤ 15 chars, letters/digits/`_` only, so X accepts it too);
     `.ai` / `ai` suffix when the channel is AI-made (says it up front);
   - no trademark, no famous person, no other channel's name; easy to spell after hearing it once.
   Then `python3 scripts/kit.py handles <slug>`: it checks each handle against every platform's format
   rules and prints the profile URLs to open. A member checks availability in each app (the apps need a
   sign-in); set `chosen` to the free one. Display name adds the keyword: `Dream Jobs ✨ AI daydreams`.
4. **Style.** Fill `style`:
   - `look`: one paragraph used verbatim in every muse prompt for this channel (medium, era, palette, light,
     lens, texture, mood), like `dream-life/looks.json`. No beauty words ("8K", "masterpiece", "flawless").
   - `palette`: 3-5 hex colours taken from the look; `font`: one font for covers and banners
     (`Avenir Next`, `Futura`, `Impact`, `SF Rounded` exist on every Mac); `mood`: 3 words.
   - `avatar_subject`: one subject that reads at 110 px in a circle - a face, a mascot, an object. No text.
     A recurring person comes from `character-bank` (attach their hero portrait, see step 5).
   - `banner_scene`: a wide scene; the subject sits in the centre band, edges are calm.
   - `banner_line`: the promise in ≤ 6 words for the banner (`a new dream job every day`).
5. **Art.** The museai server must be running (`python -m museai`, port 18610).
   ```bash
   python3 scripts/kit.py art <slug> avatar            # 2 takes → channels/<slug>/takes/
   python3 scripts/kit.py art <slug> banner             # one wide render feeds YouTube, Facebook, X
   python3 scripts/kit.py art <slug> avatar --ref ../character-bank/bank/SIENNA/hero.jpg   # recurring person
   ```
   Renders take 5-15 min; run avatar and banner in the background together. Pick takes by eye at 100 %:
   reject text or letters in the frame, a famous-looking face, plastic skin, a subject cut by the crop.
   ```bash
   python3 scripts/kit.py keep <slug> avatar takes/avatar_1.png
   python3 scripts/kit.py keep <slug> banner takes/banner_2.png    # → youtube_banner, facebook_cover, x_header
   ```
   `keep` crops to each platform's exact size, writes the name + `banner_line` in the safe zone in the kit's
   font and palette, and saves `art/*_safezone.png` with the zones drawn. Open the safezone files: nothing
   important may sit outside the green box (that part is cut on phones or TVs).
6. **Copy.** Fill `platforms.<id>` for each platform in the brief: name, handle, bio / description,
   keywords, category. Write each one for its platform, not one bio pasted 6 times:
   - first line = the promise with the search keyword; second = how often (`a new one every day`);
     last = one call to comment (`comment the dream job you want next`); AI-made channels say so in the bio;
   - Chinese platforms or TikTok: no URL in the bio text, use "search <name>".
   - YouTube description: welcome line, what every video is, how it's made (AI disclosure), how often, ask.
   `hashtags`: 3-5 topic tags shared by every post (Instagram caps a post at 5). `pillars`: 2-3 kinds of
   post with shares adding to 100 (core ≈ 80 %).
7. **Check.** `python3 scripts/kit.py check <slug>` - character limits, handle rules, the same handle
   everywhere, AI disclosure, hashtag count, pillar shares, art files. Fix every `FAIL`; a `WARN` needs a reason
   in `notes`.
8. **Kit.** `python3 scripts/kit.py render <slug>` → `channels/<slug>/KIT.md`: copy-ready blocks per platform,
   art list with sizes, setup checklist and the first-30-days plan from `references/playbook.md`. Open it
   for the member (`open channels/<slug>/KIT.md`) and show the avatar and banners.
9. **Hand over.** Accounts are made by the member in each app (sign-up, phone numbers and passwords are
   theirs; never type them). Commit `channels/<slug>/` (kit.json, KIT.md, art/; `takes/` and `*_safezone.png` are ignored) so the
   video skills can read the channel's `style.look`, and add the channel to the dashboard's posting tabs
   when its first video is ready.

## Rules learned opening channels
- One channel = one kind of video, one audience, one language. Mixing kinds lowers reach for all of them.
- Same handle on every platform; check all before picking.
- Say "AI-made" in the bio and turn on every AI label the platform has (Instagram profile label since
  2026-08-31, YouTube *altered or synthetic content*). Labelled accounts keep reach; caught ones lose it.
- Avatar = one subject, no text. Banner text only in the safe zone, ≤ 6 words.
- New account: 1 post a day while finished videos wait, never 2; 3-5 a week is the floor. Reply to every
  comment in the first hour. Details and the 30-day plan: `references/playbook.md`.
- Post the original file on each platform; never a TikTok download with its watermark elsewhere.
