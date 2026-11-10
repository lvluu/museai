#!/usr/bin/env python3
"""Channel kit: from an idea to names, style, art, bios and a launch plan for a new social channel.

  kit.py new SLUG "IDEA"                 scaffold channels/SLUG/kit.json
  kit.py handles SLUG [--probe]          check every name option's handle against each platform's rules,
                                         print the profile URLs to open (--probe: ask YouTube if @handle exists)
  kit.py art SLUG avatar|banner [--n 2] [--ref IMG ...]
                                         render takes through museai /v1/images/generations -> channels/SLUG/takes/
  kit.py keep SLUG avatar|banner TAKE    crop to every platform size, write name + banner_line in the safe zone,
                                         save art/*.jpg and art/*_safezone.png
  kit.py check SLUG                      limits, handle rules, AI disclosure, hashtags, pillars, art -> FAIL/WARN/ok
  kit.py render SLUG                     channels/SLUG/KIT.md (copy-ready kit + setup + first 30 days)

Numbers match references/platform-specs.md; change both together. The API key is read, never printed.
"""
import base64
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
CHANNELS = HERE / "channels"
API_BASE = os.environ.get("MUSEAI_BASE", "http://127.0.0.1:18610")
PLATFORMS = ["youtube", "instagram", "tiktok", "facebook", "x", "threads"]

# name, bio (description for YouTube, intro for Facebook) limits
LIMITS = {
    "youtube": {"name": 100, "bio": 1000},
    "instagram": {"name": 30, "bio": 150},
    "tiktok": {"name": 30, "bio": 80},
    "facebook": {"name": 75, "bio": 101},
    "x": {"name": 50, "bio": 160},
    "threads": {"name": 30, "bio": 150},
}
HANDLE = {
    "youtube": (r"^[A-Za-z0-9_.-]{3,30}$", "3-30 letters, digits, _ - ."),
    "instagram": (r"^(?!.*\.\.)(?!.*\.$)[A-Za-z0-9_.]{1,30}$", "1-30 letters, digits, _ . (no .. or trailing .)"),
    "tiktok": (r"^(?!.*\.$)[A-Za-z0-9_.]{2,24}$", "2-24 letters, digits, _ . (no trailing .)"),
    "facebook": (r"^[A-Za-z0-9.]{5,50}$", "5-50 letters, digits, ."),
    "x": (r"^[A-Za-z0-9_]{4,15}$", "4-15 letters, digits, _"),
    "threads": (r"^(?!.*\.\.)(?!.*\.$)[A-Za-z0-9_.]{1,30}$", "= Instagram handle"),
}
URL = {
    "youtube": "https://www.youtube.com/@{}", "instagram": "https://www.instagram.com/{}/",
    "tiktok": "https://www.tiktok.com/@{}", "facebook": "https://www.facebook.com/{}",
    "x": "https://x.com/{}", "threads": "https://www.threads.net/@{}",
}
# output file: (width, height, safe box w, h centred, text box w, h centred)
ART = {
    "youtube_banner": (2560, 1440, 1546, 423),
    "facebook_cover": (1640, 624, 1200, 624),
    "x_header": (1500, 500, 1200, 300),
}
RENDER = {
    "avatar": ("1024x1024",
               "Square 1:1 profile picture. ONE clear subject: {subject}, centred, filling the middle of the frame "
               "with a little space around it so it survives a circle crop and still reads at 110 pixels. Simple, "
               "calm background in the palette, strong silhouette, high contrast between subject and background."),
    "banner": ("1920x1080",
               "Wide 16:9 channel banner artwork: {scene}. Everything important sits in a horizontal band through "
               "the exact centre (the middle 60 % of the width, the middle 30 % of the height); the top, bottom and "
               "side edges are calm continuation of the scene (sky, meadow, wall) that can be cropped away. Leave "
               "a quiet, uncluttered area in the very centre where a title will be written later."),
}
NO_TEXT = "Absolutely no text, letters, logos, watermarks or signatures anywhere in the image."
AI_WORDS = re.compile(r"\bAI\b|AI-|A\.I\.|人工智能|AI生成|trí tuệ nhân tạo", re.I)
URL_RX = re.compile(r"https?://|www\.|\.(com|net|space|io|ai)\b", re.I)


def kit_path(slug: str) -> Path:
    return CHANNELS / slug / "kit.json"


def load(slug: str) -> dict:
    p = kit_path(slug)
    if not p.exists():
        sys.exit(f"no kit {slug} (run: kit.py new {slug} \"IDEA\")")
    return json.loads(p.read_text())


def save(slug: str, kit: dict) -> None:
    kit_path(slug).write_text(json.dumps(kit, indent=1, ensure_ascii=False) + "\n")


def blank(v):
    if isinstance(v, dict):
        return {k: blank(x) for k, x in v.items()}
    if isinstance(v, list):
        return [blank(v[0])] if v and isinstance(v[0], dict) else []
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return 0
    return ""


def weighted_len(s: str) -> int:
    """Instagram and X count emoji as 2; count every symbol / astral char as 2 (the safe side)."""
    return sum(2 if ord(c) > 0xFFFF or unicodedata.category(c) == "So" else 1 for c in s)


def chosen(kit: dict) -> dict:
    names = kit.get("names") or []
    return names[kit.get("chosen", 0)] if names else {}


# ---------- new ----------
def cmd_new(slug: str, idea: str) -> None:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,40}", slug):
        sys.exit("slug: lowercase letters, digits and dashes")
    p = kit_path(slug)
    if p.exists():
        sys.exit(f"{p} exists; edit it instead")
    ex = json.loads((HERE / "templates/kit.example.json").read_text())
    kit = blank(ex)
    kit.update(slug=slug, idea=idea, ai_made=True, chosen=0)
    kit["names"] = [{"display": "", "handle": "", "why": ""} for _ in range(3)]
    kit["platforms"] = {k: {"name": "", "handle": "", "bio": ""} for k in ("youtube", "instagram", "tiktok", "facebook")}
    kit["platforms"]["youtube"].update(description="", keywords=[], category="")
    kit["platforms"]["youtube"].pop("bio")
    (p.parent / "art").mkdir(parents=True, exist_ok=True)
    (p.parent / "takes").mkdir(exist_ok=True)
    save(slug, kit)
    print(p)


# ---------- handles ----------
def youtube_exists(h: str) -> str:
    req = urllib.request.Request(URL["youtube"].format(h), method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15):
            return "taken"
    except urllib.error.HTTPError as e:
        return "looks free" if e.code == 404 else f"unknown ({e.code})"
    except Exception as e:  # network
        return f"unknown ({type(e).__name__})"


def cmd_handles(slug: str, probe: bool) -> None:
    kit = load(slug)
    platforms = PLATFORMS  # all: the handle should fit even platforms opened later
    for i, n in enumerate(kit.get("names", [])):
        h = n.get("handle", "").lstrip("@")
        if not h:
            continue
        mark = " (chosen)" if i == kit.get("chosen", 0) else ""
        print(f"\n{i}: {n.get('display', '')}  @{h}{mark}")
        for p in platforms:
            rx, rule = HANDLE[p]
            ok = re.fullmatch(rx, h) is not None
            extra = f"  youtube: {youtube_exists(h)}" if probe and p == "youtube" and ok else ""
            print(f"  {'ok  ' if ok else 'FAIL'} {p:9} {URL[p].format(h)}{'' if ok else '  rule: ' + rule}{extra}")
    print("\nAvailability: open each URL signed in (a 'page not found' = free) or try it in the app's sign-up.")


# ---------- art ----------
def data_url(path: Path) -> str:
    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def cmd_art(slug: str, view: str, n: int, refs: list[str]) -> None:
    if view not in RENDER:
        sys.exit("view: avatar or banner")
    kit = load(slug)
    st = kit.get("style", {})
    need = "avatar_subject" if view == "avatar" else "banner_scene"
    if not st.get(need) or not st.get("look"):
        sys.exit(f"fill style.look and style.{need} in {kit_path(slug)} first")
    size, frame = RENDER[view]
    parts = []
    if refs:
        parts.append("The person or character in image 1 is the channel's recurring subject: keep exactly the same "
                     "face, age, skin tone, hair and features; take pose, clothes, place and light from this text.")
    parts += [frame.format(subject=st.get("avatar_subject", ""), scene=st.get("banner_scene", "")),
              "LOOK: " + st["look"]]
    if st.get("palette"):
        parts.append("Colour palette: " + ", ".join(st["palette"]) + ".")
    parts.append(NO_TEXT)
    body = {"prompt": " ".join(parts), "n": n, "size": size, "response_format": "b64_json"}
    if refs:
        body["image"] = [data_url(Path(r)) for r in refs]
    key = (Path(os.environ.get("MUSEAI_HOME", Path.home() / "Work/museai")) / "data/api_key").read_text().strip()
    req = urllib.request.Request(
        f"{API_BASE}/v1/images/generations", data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "X-Muse-Session": os.environ.get("MUSE_SESSION", os.environ.get("CLAUDE_CODE_SESSION_ID", "new-channel"))})
    try:
        with urllib.request.urlopen(req, timeout=float(os.environ.get("STILL_TIMEOUT", 7200))) as r:
            data = json.load(r)["data"]
    except urllib.error.URLError as e:
        sys.exit(f"museai server at {API_BASE} not reachable ({e}); start it: python -m museai")
    out = CHANNELS / slug / "takes"
    out.mkdir(parents=True, exist_ok=True)
    start = len(list(out.glob(f"{view}_*.png")))
    for i, x in enumerate(data, start + 1):
        p = out / f"{view}_{i}.png"
        p.write_bytes(base64.b64decode(x["b64_json"]))
        print(p)


# ---------- keep ----------
def font_file(name: str):
    from PIL import ImageFont
    want = name.lower().replace(" ", "")
    want = {"sfrounded": "sfnsrounded", "sfprorounded": "sfnsrounded", "sanfrancisco": "sfns"}.get(want, want)
    dirs = [Path("/System/Library/Fonts"), Path("/System/Library/Fonts/Supplemental"), Path("/Library/Fonts"),
            Path.home() / "Library/Fonts", Path("/usr/share/fonts")]
    cands = [f for d in dirs if d.exists() for f in d.rglob("*") if f.suffix.lower() in (".ttf", ".ttc", ".otf")
             and f.stem.lower().replace(" ", "") == want]
    cands += [f for d in dirs if d.exists() for f in d.rglob("*") if f.suffix.lower() in (".ttf", ".ttc", ".otf")
              and want in f.stem.lower().replace(" ", "")]
    for f in cands:
        best = None
        for idx in range(0, 40):
            try:
                fo = ImageFont.truetype(str(f), 40, index=idx)
            except OSError:
                break
            style = fo.getname()[1].lower()
            if "italic" in style or "oblique" in style:
                continue
            if style in ("bold", "demi bold", "demibold", "heavy"):
                return str(f), idx
            best = best if best is not None else idx
        if best is not None:
            return str(f), best
    return "/System/Library/Fonts/Helvetica.ttc", 1


def load_font(path: str, idx: int, size: int):
    """Variable fonts (SF Rounded) hold every weight in one face: pick Bold when it is there."""
    from PIL import ImageFont
    f = ImageFont.truetype(path, size, index=idx)
    try:
        f.set_variation_by_name("Bold")
    except (OSError, ValueError, AttributeError):
        pass
    return f


def channel_title(display: str) -> str:
    """'Pocket Paws 🐾 tiny AI pets' -> 'Pocket Paws': the name ends at the first emoji or separator."""
    m = re.split(r"[|·•—]|\s[-–]\s", display)[0]
    cut = next((i for i, c in enumerate(m) if ord(c) > 0xFFFF or unicodedata.category(c) == "So"), len(m))
    return strip_emoji(m[:cut])


def strip_emoji(s: str) -> str:
    return re.sub(r"\s+", " ", "".join(c for c in s if ord(c) <= 0xFFFF and unicodedata.category(c) != "So")).strip()


def hex_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lum(rgb) -> float:
    r, g, b = rgb[:3]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def cover_crop(img, w: int, h: int):
    from PIL import Image
    sw, sh = img.size
    scale = max(w / sw, h / sh)
    img = img.resize((round(sw * scale), round(sh * scale)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def write_title(img, kit: dict, box_w: int, box_h: int):
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat
    st = kit.get("style", {})
    title = channel_title(chosen(kit).get("display", "")) or kit.get("slug", "")
    line = strip_emoji(st.get("banner_line", ""))
    W, H = img.size
    bx, by = (W - box_w) // 2, (H - box_h) // 2
    bg = lum(ImageStat.Stat(img.crop((bx, by, bx + box_w, by + box_h)).convert("RGB")).mean)
    pal = [hex_rgb(c) for c in st.get("palette", [])] or [(255, 255, 255), (20, 20, 20)]
    fg = max(pal, key=lambda c: abs(lum(c) - bg))
    if abs(lum(fg) - bg) < 90:
        fg = (255, 255, 255)  # photos: white title on a dark glow reads on any background
    shadow = (255, 255, 255, 170) if lum(fg) < 128 else (0, 0, 0, 200)
    path, idx = font_file(st.get("font") or "Avenir Next")
    # biggest title that fits 60 % of the box width (sides stay free for the art's subjects) and 55 % of its height (line below takes the rest)
    size = int(box_h * 0.55)
    while size > 10:
        f1 = load_font(path, idx, size)
        if f1.getbbox(title)[2] <= box_w * 0.6:
            break
        size -= 4
    f2 = load_font(path, idx, max(12, int(size * 0.38)))
    while line and f2.size > 12 and f2.getbbox(line)[2] > box_w * 0.6:
        f2 = load_font(path, idx, f2.size - 2)
    h1 = f1.getbbox(title)[3]
    h2 = f2.getbbox(line)[3] if line else 0
    gap = int(size * 0.25) if line else 0
    y = by + (box_h - h1 - gap - h2) // 2
    layer = img.convert("RGBA")
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    ds = ImageDraw.Draw(sh)
    for txt, fo, yy in ((title, f1, y), (line, f2, y + h1 + gap)):
        if txt:
            ds.text((W // 2, yy), txt, font=fo, fill=shadow, anchor="ma")
    sh = sh.filter(ImageFilter.GaussianBlur(max(4, size // 8)))
    layer.alpha_composite(sh)
    layer.alpha_composite(sh)
    d = ImageDraw.Draw(layer)
    for txt, fo, yy in ((title, f1, y), (line, f2, y + h1 + gap)):
        if txt:
            d.text((W // 2, yy), txt, font=fo, fill=fg, anchor="ma")
    return layer.convert("RGB")


def safezone(img, box_w: int, box_h: int, circle: bool = False):
    from PIL import ImageDraw
    im = img.convert("RGB").copy()
    d = ImageDraw.Draw(im)
    W, H = im.size
    lw = max(3, W // 400)
    if circle:
        d.ellipse((0, 0, W - 1, H - 1), outline=(0, 255, 0), width=lw)
        m = W // 10
        d.ellipse((m, m, W - m, H - m), outline=(255, 200, 0), width=lw)
    else:
        bx, by = (W - box_w) // 2, (H - box_h) // 2
        d.rectangle((bx, by, bx + box_w, by + box_h), outline=(0, 255, 0), width=lw)
    return im


def cmd_keep(slug: str, view: str, take: str) -> None:
    from PIL import Image, ImageDraw
    kit = load(slug)
    src = Path(take)
    if not src.is_absolute() and not src.exists():
        src = CHANNELS / slug / take
    img = Image.open(src).convert("RGB")
    art = CHANNELS / slug / "art"
    art.mkdir(parents=True, exist_ok=True)
    if view == "avatar":
        a = cover_crop(img, 800, 800)
        a.save(art / "avatar.jpg", quality=92)
        safezone(a, 0, 0, circle=True).save(art / "avatar_safezone.png")
        small = a.resize((110, 110), Image.LANCZOS)
        mask = Image.new("L", (110, 110), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 109, 109), fill=255)
        prev = Image.new("RGB", (110, 110), (255, 255, 255))
        prev.paste(small, (0, 0), mask)
        prev.save(art / "avatar_110px.png")
        print(art / "avatar.jpg")
    elif view == "banner":
        for name, (w, h, sw, sh) in ART.items():
            b = cover_crop(img, w, h)
            b = write_title(b, kit, sw, sh)
            b.save(art / f"{name}.jpg", quality=90)
            safezone(b, sw, sh).save(art / f"{name}_safezone.png")
            print(art / f"{name}.jpg")
    else:
        sys.exit("view: avatar or banner")


# ---------- check ----------
def cmd_check(slug: str) -> int:
    kit = load(slug)
    out = []

    def add(level, msg):
        out.append((level, msg))

    for f in ("idea", "audience", "language", "niche", "promise"):
        if not str(kit.get(f, "")).strip():
            add("FAIL", f"{f} is empty")
    names = [n for n in kit.get("names", []) if n.get("handle")]
    if len(names) < 3:
        add("WARN", f"{len(names)} name options (aim for 3)")
    st = kit.get("style", {})
    for f in ("look", "avatar_subject", "banner_scene", "banner_line", "font"):
        if not str(st.get(f, "")).strip():
            add("FAIL", f"style.{f} is empty")
    if not 3 <= len(st.get("palette", [])) <= 5:
        add("WARN", "style.palette: 3-5 colours")
    if len(st.get("banner_line", "").split()) > 6:
        add("WARN", "style.banner_line longer than 6 words")
    if re.search(r"\b(8k|masterpiece|flawless|perfect skin|gorgeous)\b", st.get("look", ""), re.I):
        add("WARN", "style.look has beauty words (plastic AI look)")

    plats = kit.get("platforms", {})
    if not plats:
        add("FAIL", "no platforms")
    handles = set()
    for p, d in plats.items():
        if p not in LIMITS:
            add("WARN", f"{p}: unknown platform, not checked")
            continue
        h = d.get("handle", "").lstrip("@")
        handles.add(h.lower())
        if not h:
            add("FAIL", f"{p}: handle empty")
        elif not re.fullmatch(HANDLE[p][0], h):
            add("FAIL", f"{p}: handle @{h} breaks rule ({HANDLE[p][1]})")
        name = d.get("name", "")
        if not name:
            add("FAIL", f"{p}: name empty")
        elif weighted_len(name) > LIMITS[p]["name"]:
            add("FAIL", f"{p}: name {weighted_len(name)}/{LIMITS[p]['name']}")
        elif p == "youtube" and weighted_len(name) > 50:
            add("WARN", "youtube: name over 50 chars gets cut in search")
        bio = d.get("description" if p == "youtube" else "bio", "")
        label = "description" if p == "youtube" else "bio"
        if not bio:
            add("FAIL", f"{p}: {label} empty")
        else:
            n = weighted_len(bio)
            if n > LIMITS[p]["bio"]:
                add("FAIL", f"{p}: {label} {n}/{LIMITS[p]['bio']}")
            else:
                add("ok", f"{p}: {label} {n}/{LIMITS[p]['bio']}")
            if kit.get("ai_made") and not AI_WORDS.search(bio):
                add("FAIL", f"{p}: {label} does not say the channel is AI-made")
            if p == "tiktok" and URL_RX.search(bio):
                add("WARN", "tiktok: URL in bio text is throttled; use 'search <name>'")
        if p == "youtube":
            kw = d.get("keywords", [])
            if not kw:
                add("WARN", "youtube: no keywords")
            elif len(", ".join(kw)) > 500:
                add("FAIL", "youtube: keywords over 500 chars")
    if len(handles) > 1:
        add("WARN", "handles differ across platforms: " + ", ".join(sorted(handles)))
    if chosen(kit).get("handle") and chosen(kit)["handle"].lower() not in handles:
        add("WARN", "chosen name's handle is not used on the platforms")

    tags = kit.get("hashtags", [])
    if len(tags) > 5:
        add("FAIL", f"{len(tags)} hashtags (Instagram caps a post at 5)")
    elif len(tags) < 3:
        add("WARN", f"{len(tags)} hashtags (aim 3-5)")
    if any(t.lower() in ("#fyp", "#foryou", "#viral", "#foryoupage") for t in tags):
        add("WARN", "generic tags (#fyp/#viral) do nothing; use topic tags")
    pil = kit.get("pillars", [])
    total = sum(int(x.get("share", 0)) for x in pil)
    if not pil:
        add("FAIL", "no content pillars")
    elif total != 100:
        add("FAIL", f"pillar shares add to {total}, not 100")

    art = CHANNELS / slug / "art"
    for f in ["avatar.jpg", *(f"{k}.jpg" for k in ART)]:
        if not (art / f).exists():
            add("WARN", f"art/{f} missing (kit.py art + keep)")

    for level in ("FAIL", "WARN", "ok"):
        for lv, msg in out:
            if lv == level:
                print(f"{lv:4} {msg}")
    fails = sum(1 for lv, _ in out if lv == "FAIL")
    print(f"\n{fails} FAIL, {sum(1 for lv, _ in out if lv == 'WARN')} WARN")
    return 1 if fails else 0


# ---------- render ----------
def section(md: str, title: str) -> str:
    m = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", md, re.S | re.M)
    return m.group(1).strip() if m else ""


def cmd_render(slug: str) -> None:
    kit = load(slug)
    st = kit.get("style", {})
    c = chosen(kit)
    L = [f"# {c.get('display') or slug}: channel kit", "",
         f"> {kit.get('promise', '')}", "",
         "| | |", "|---|---|",
         f"| Idea | {kit.get('idea', '')} |", f"| Audience | {kit.get('audience', '')} |",
         f"| Language | {kit.get('language', '')} |", f"| Niche | {kit.get('niche', '')} |",
         f"| AI-made | {'yes: label every post, AI profile labels on' if kit.get('ai_made') else 'no'} |", ""]
    if kit.get("notes"):
        L += [f"Notes: {kit['notes']}", ""]
    L += ["## Name and handle", "", "| | Display name | Handle | Why |", "|---|---|---|---|"]
    for i, n in enumerate(kit.get("names", [])):
        star = "**chosen**" if i == kit.get("chosen", 0) else str(i)
        L.append(f"| {star} | {n.get('display', '')} | `@{n.get('handle', '')}` | {n.get('why', '')} |")
    L += ["", "## Style", "", f"- **Look** (paste in every muse prompt): {st.get('look', '')}",
          f"- **Palette:** {' '.join('`' + x + '`' for x in st.get('palette', []))}",
          f"- **Font:** {st.get('font', '')}", f"- **Mood:** {st.get('mood', '')}", "",
          "## Art", "", "| File | Size | Use |", "|---|---|---|",
          "| `art/avatar.jpg` | 800 x 800 | profile picture on every platform (`avatar_110px.png` = how it reads) |",
          "| `art/youtube_banner.jpg` | 2560 x 1440 | YouTube banner |",
          "| `art/facebook_cover.jpg` | 1640 x 624 | Facebook Page cover |",
          "| `art/x_header.jpg` | 1500 x 500 | X header |", "",
          "`*_safezone.png` show what every device keeps (green box).", "", "## Profiles", ""]
    for p, d in kit.get("platforms", {}).items():
        L += [f"### {p.capitalize() if p != 'x' else 'X'}", "",
              f"- Name: `{d.get('name', '')}`", f"- Handle: `@{d.get('handle', '')}`"]
        if d.get("category"):
            L.append(f"- Category: {d['category']}")
        text = d.get("description") if p == "youtube" else d.get("bio")
        L += ["", "```", text or "", "```"]
        if d.get("keywords"):
            L += ["", "Keywords: `" + ", ".join(d["keywords"]) + "`"]
        L.append("")
    L += ["## Hashtags", "", " ".join(kit.get("hashtags", [])), "", "## Content pillars", "",
          "| Pillar | Share | What |", "|---|---|---|"]
    for x in kit.get("pillars", []):
        L.append(f"| {x.get('name', '')} | {x.get('share', '')} % | {x.get('what', '')} |")
    if kit.get("first_posts"):
        L += ["", "First posts (pin the best 3): " + ", ".join(kit["first_posts"])]
    specs = (HERE / "references/platform-specs.md").read_text()
    play = (HERE / "references/playbook.md").read_text()
    L += ["", "## Setup checklist", "",
          "Accounts are made by you in each app (phone numbers, passwords and sign-up are yours).", "",
          section(specs, "Account setup"), "", "## AI disclosure", "", section(specs, "AI disclosure (checked 2026-11-02)"),
          "", "## Before day 0", "", section(play, "Before day 0"), "", "## How often", "", section(play, "How often"),
          "", "## First 30 days", "", section(play, "First 30 days"), "", "## What not to do", "",
          section(play, "What not to do"), ""]
    p = CHANNELS / slug / "KIT.md"
    p.write_text("\n".join(L))
    print(p)


def main(a: list[str]) -> None:
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd, rest = a[0], a[1:]

    def opt(name, default=None, many=False):
        vals = [rest[i + 1] for i, x in enumerate(rest) if x == name and i + 1 < len(rest)]
        return vals if many else (vals[0] if vals else default)

    pos = [x for i, x in enumerate(rest) if not x.startswith("--") and (i == 0 or rest[i - 1] not in ("--n", "--ref"))]
    if cmd == "new" and len(pos) == 2:
        cmd_new(*pos)
    elif cmd == "handles" and len(pos) == 1:
        cmd_handles(pos[0], "--probe" in rest)
    elif cmd == "art" and len(pos) == 2:
        cmd_art(pos[0], pos[1], int(opt("--n", 2)), opt("--ref", many=True))
    elif cmd == "keep" and len(pos) == 3:
        cmd_keep(*pos)
    elif cmd == "check" and len(pos) == 1:
        sys.exit(cmd_check(pos[0]))
    elif cmd == "render" and len(pos) == 1:
        cmd_render(pos[0])
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
