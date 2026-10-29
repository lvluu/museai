"""travel: scenery reels (scenic-drop-reel, muse-video travel mode); --split for zoominview reactions.

Pass the raw shots in plan order, not the finished reel (its intro text, dips to black and transitions
would be picked). The most vivid, sharp, still frame wins; the first shot is the hook shot and gets a
small bonus. The cover is the frame full bleed, graded a little punchier, with a dark band at the top
behind a yellow hook line, the place name big in Futura (two balanced lines when long) and a sub line
that may end in a flag emoji ("Norway 🇳🇴"). A frame of the other aspect sits sharp on a blurred
copy of itself, the text beside or above it.
--split (zoominview): one reel with a person, the reaction on top and the view below, the title on the
seam, as the old thumbnail did.
"""
import sys

from core import (
    CENTRE,
    SAFE,
    YELLOW,
    cover,
    emoji,
    face_mesh,
    faces,
    ffprobe_duration,
    frames,
    grab,
    grade,
    horizontal,
    pick,
    picks_sheet,
    scenery,
    split,
    split_emoji,
    spread,
    to_pil,
)
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

FONTS = {  # (file, face index)
    "futura": ("/System/Library/Fonts/Supplemental/Futura.ttc", 4),  # Condensed ExtraBold
    "heavy": ("/System/Library/Fonts/Avenir Next.ttc", 8),
    "demi": ("/System/Library/Fonts/Avenir Next.ttc", 2),
}
HOOK_BONUS = 1.15
EDGE = 0.5  # s skipped at both ends of a shot (muse settles in / fades out there)


def add_args(p):
    p.add_argument("--title", required=True, help="the place name, e.g. GEIRANGERFJORD")
    p.add_argument("--hook", default="", help="2-5 words above it, the caption's promise: \"7 waterfalls. 1 fjord.\"")
    p.add_argument("--sub", default="", help='line under it, may end in a flag: "Norway 🇳🇴"')
    p.add_argument("--at", default="", help="force the frame: shot.mp4@2.5, or seconds in the first video")
    p.add_argument("--split", action="store_true", help="reaction + view (zoominview): face on top, the view below")
    p.add_argument("--view", type=float, help="time of the view frame for --split (default: best frame without faces)")


# ---------- text ----------
def font(kind, size):
    return ImageFont.truetype(FONTS[kind][0], size, index=FONTS[kind][1])


def fit(d, text, kind, start, maxw, spacing_ratio=0.0):
    words, emo = split_emoji(text)
    size = start
    while size > 20:
        width = d.textlength(words, font=font(kind, size)) + size * spacing_ratio * max(len(words) - 1, 0)
        if width + (size if emo else 0) <= maxw:  # the emoji is drawn 0.8*size wide after a 0.2*size gap
            break
        size -= 4
    return font(kind, size), round(size * spacing_ratio)


def chars(d, xy, text, f, fill, spacing, stroke):
    x = xy[0]
    for c in text if spacing else [text]:
        d.text((x, xy[1]), c, font=f, fill=fill, anchor="ls", stroke_width=stroke, stroke_fill=(0, 0, 0, 200))
        x += d.textlength(c, font=f) + spacing


def line(img, cx, y, text, f, fill=(255, 255, 255), stroke=0, spacing=0):
    """text (+ trailing emoji) centred on cx, baseline y, with a soft shadow"""
    d = ImageDraw.Draw(img)
    words, emo = split_emoji(text)
    tw = d.textlength(words, font=f) + spacing * max(len(words) - 1, 0)
    em = emoji(emo, round(f.size * 0.8)) if emo else None
    x0 = cx - (tw + (em.width + f.size * 0.2 if em else 0)) / 2
    sh = Image.new("RGBA", img.size)
    chars(ImageDraw.Draw(sh), (x0 + 3, y + 4), words, f, (0, 0, 0, 150), spacing, stroke)
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(f.size / 10)))
    chars(d, (x0, y), words, f, fill, spacing, stroke)
    if em:
        img.alpha_composite(em, (round(x0 + tw + f.size * 0.2), round(y - em.height)))


def rows(args, w, base):
    """[(text, font, spacing, fill, stroke, space above the baseline, space below)] of hook, title, sub."""
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    out = []
    if args.hook:
        f, _ = fit(d, args.hook.upper(), "heavy", round(base * 0.075), w)
        out.append((args.hook.upper(), f, 0, YELLOW, max(2, f.size // 18), f.size, f.size * 0.35))
    title = args.title.upper()
    f, sp = fit(d, title, "futura", round(base * 0.22), w, 0.08)
    words = title.split()
    lines = [title]
    if f.size < base * 0.14 and len(words) > 1:  # two balanced lines read bigger than one long small one
        cut = min(range(1, len(words)), key=lambda k: abs(len(" ".join(words[:k])) - len(" ".join(words[k:]))))
        lines = [" ".join(words[:cut]), " ".join(words[cut:])]
        f, sp = min((fit(d, r, "futura", round(base * 0.2), w, 0.08) for r in lines), key=lambda x: x[0].size)
    for t in lines:
        out.append((t, f, sp, (255, 255, 255), max(2, f.size // 22), f.size * 0.85, f.size * 0.25))
    if args.sub:
        f, _ = fit(d, args.sub, "demi", round(base * 0.06), w * 0.8)
        out.append((args.sub, f, 0, (255, 255, 255), 0, f.size * 1.2, 0))
    return out


def text(img, box, args, middle=False):
    """Draw the stack into box (x0, y0, x1, y1): from its top, or centred in it when middle."""
    stack = rows(args, box[2] - box[0], 1080)
    h = sum(a + b for *_, a, b in stack)
    y = box[1] + (max(box[3] - box[1] - h, 0) / 2 if middle else 0)
    for t, f, sp, fill, stroke, above, below in stack:
        y += above
        line(img, (box[0] + box[2]) / 2, y, t, f, fill, stroke, sp)
        y += below


# ---------- layout ----------
def band(w, h, top, bottom):
    """Dark band behind the text at the top, a lighter one at the bottom so the cover reads on any feed."""
    g = Image.new("L", (1, h))
    for y in range(h):
        a = 0
        if y < h * top[0]:
            a = top[1] * (1 - y / (h * top[0])) ** 1.4
        elif y > h * (1 - bottom[0]):
            a = bottom[1] * ((y - h * (1 - bottom[0])) / (h * bottom[0])) ** 1.6
        g.putpixel((0, y), round(a))
    black = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    black.putalpha(g.resize((w, h)))
    return black


def backdrop(frame, w, h):
    """frame blurred and dimmed to fill w x h, for a frame of the other aspect"""
    bg = cover(frame, w, h).filter(ImageFilter.GaussianBlur(30))
    return ImageEnhance.Brightness(bg).enhance(0.55).convert("RGBA")


def vertical(frame, args):
    tall = frame.height > frame.width
    if tall:
        im = grade(cover(frame, 1080, 1920)).convert("RGBA")
    else:  # 16:9 shot: sharp across the middle, the text above it
        im = backdrop(frame, 1080, 1920)
        panel = grade(cover(frame, 1080, 608))
        im.paste(panel, (0, 1000))
    im.alpha_composite(band(1080, 1920, (0.42, 190), (0.18, 120)))
    text(im, (CENTRE[0], SAFE[1], CENTRE[1], SAFE[3]), args)
    return im.convert("RGB")


def landscape(frame, args):
    W, H = 1920, 1080
    if frame.width > frame.height:
        im = grade(cover(frame, W, H)).convert("RGBA")
        right = W
    else:  # 9:16 shot: sharp on the right, soft-edged, over a blurred copy
        im = backdrop(frame, W, H)
        pw = round(H * 9 / 16)
        panel = grade(cover(frame, pw, H))
        mask = Image.new("L", panel.size, 255)
        for x in range(60):
            ImageDraw.Draw(mask).line((x, 0, x, H), fill=int(255 * x / 60))
        im.paste(panel, (W - pw, 0), mask)
        right = W - pw
    g = Image.linear_gradient("L").rotate(90, expand=True).resize((W, H))  # 255 left -> 0 right
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    shadow.putalpha(g.point(lambda v: int(v * 0.6)))
    im.alpha_composite(shadow)
    text(im, (80, 80, min(right - 60, 1180), H - 80), args, middle=True)
    return im.convert("RGB")


# ---------- frame ----------
def best(clips):
    """[(score, (clip index, t))] the 6 best frames at least 1 s apart, any shot"""
    cands = []
    for i, clip in enumerate(clips):
        dur, prev = ffprobe_duration(clip), None
        for t, img in frames(clip):
            if EDGE <= t <= dur - EDGE:
                sc = scenery(img, prev)  # can be negative (fast drone moves): the bonus must still raise it
                cands.append((sc + abs(sc) * (HOOK_BONUS - 1) * (i == 0), (i, t)))
            prev = img  # the motion measure compares with the frame before
    if not cands:
        sys.exit("no frames: shots shorter than 1 s?")
    return spread(sorted(cands, reverse=True))


def at(args):
    clip, _, t = args.at.rpartition("@")
    return clip or args.videos[0], float(t)


def reaction(args):
    """--split: the old zoominview cover, kept pixel-identical"""
    video = args.videos[0]
    mesh = face_mesh()
    view_t, sheet = args.view, None
    if not args.at:
        picks, auto_view = pick(video, [], mesh)
        view_t = view_t if view_t is not None else auto_view
        sheet = picks_sheet([(grab(video, t), f"{t:.2f}s  {sc:.2f}") for sc, t in picks])
        t = picks[0][1]
    else:
        t = at(args)[1]
    img = grab(video, t)
    boxes = [f["box"] for f in faces(img, mesh)]
    if view_t is None:
        sys.exit("--split needs a frame without faces: pass --view")
    frame, view = to_pil(img), to_pil(grab(video, view_t))
    return (split(frame, boxes, args, view), horizontal(frame, boxes, args, view), sheet,
            f"frame {t:.2f}s, {len(boxes)} face(s), view {view_t:.2f}s")


def make(args):
    if args.split:
        return reaction(args)
    sheet = None
    if args.at:
        clip, t = at(args)
    else:
        picks = best(args.videos)
        name = [c.rsplit("/", 1)[-1] for c in args.videos]
        sheet = picks_sheet([(grab(args.videos[i], t), f"{name[i]}@{t:.2f} {sc:.1f}") for sc, (i, t) in picks])
        i, t = picks[0][1]
        clip = args.videos[i]
    frame = to_pil(grab(clip, t))
    return vertical(frame, args), landscape(frame, args), sheet, f"frame {clip}@{t:.2f}s ({frame.width}x{frame.height})"
