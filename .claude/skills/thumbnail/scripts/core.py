"""Shared toolkit for the thumbnail styles (styles/*.py): fonts, frame grabbing, face and scenery
scoring, grade, shading, the red-box title block, badge, emoji, picks sheet and the 2 MB JPEG writer.

Layout constants are for the 1080x1920 cover: text stays inside SAFE x80-960 / y300-1560, which survives
the 3:4 profile-grid, 4:5 feed and 1:1 square centre crops and the TikTok / Reels UI (right column,
bottom 20 %). CENTRE is the text block's x span, symmetric on the frame's centre line.
"""
import io
import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ZH_FONT = ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb"
           ".asset/AssetData/PingFang.ttc", 11)  # PingFang SC Semibold
TITLE_FONT = ("/System/Library/Fonts/HelveticaNeue.ttc", 9)  # Condensed Black, has Vietnamese
SUB_FONT = ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 0)
EMOJI_FONT = "/System/Library/Fonts/Apple Color Emoji.ttc"
YELLOW, RED, WHITE, BLACK = (255, 214, 10), (232, 23, 58), (255, 255, 255), (0, 0, 0)
PANEL = (18, 20, 28)  # text panel beside or under the picture: near-black, the red title and yellow hanzi pop on it
SAFE = (80, 300, 960, 1560)  # 9:16 text box
CENTRE = (1080 - SAFE[2], SAFE[2])  # the text block's x span: symmetric on the frame's centre line, clear of the buttons
MAX_BYTES = 2_000_000  # YouTube mobile upload limit for video thumbnails


def font(spec, size):
    return ImageFont.truetype(spec[0], size, index=spec[1])


def fit(spec, text, size, width, min_size=40):
    while size > min_size and font(spec, size).getlength(text) > width:
        size -= 4
    return font(spec, size)


def ffprobe_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def grab(video, t):
    out = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1",
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
    return cv2.imdecode(np.frombuffer(out, np.uint8), cv2.IMREAD_COLOR)


def to_pil(img):
    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))


def frames(video, fps=4, width=540):
    """(t, small BGR frame) sampled at `fps`, t at the middle of each sample interval."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", f"fps={fps},scale={width}:-2", f"{tmp}/%05d.png"],
                       check=True)
        for i, n in enumerate(sorted(os.listdir(tmp))):
            yield (i + 0.5) / fps, cv2.imread(f"{tmp}/{n}")


# ---------- faces ----------
def face_mesh():
    import mediapipe as mp  # only the styles that look at people pay for loading it

    return mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=4, refine_landmarks=False)


def ratio(lm, a, b, c, d):
    """distance a-b over distance c-d (landmark indices)"""
    def dist(i, j):
        return np.linalg.norm(np.array([lm[i].x - lm[j].x, lm[i].y - lm[j].y]))

    return dist(a, b) / max(dist(c, d), 1e-6)


def faces(img, mesh):
    h, w = img.shape[:2]
    r = mesh.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    out = []
    for f in r.multi_face_landmarks or []:
        lm = f.landmark
        xs, ys = [p.x * w for p in lm], [p.y * h for p in lm]
        box = (min(xs), min(ys), max(xs), max(ys))
        eyes = min(ratio(lm, 159, 145, 33, 133), ratio(lm, 386, 374, 362, 263))  # ~0.3 open, <0.18 blink
        mouth = ratio(lm, 13, 14, 10, 152)  # lip gap / face height: >0.06 is mid-word
        smile = ratio(lm, 61, 291, 234, 454)  # mouth width / face width: wider is a smile
        yaw = abs(lm[1].x - (lm[234].x + lm[454].x) / 2) / max(abs(lm[454].x - lm[234].x), 1e-6)  # 0 = faces the lens
        x0, y0, x1, y1 = (int(v) for v in box)
        crop = cv2.cvtColor(img[max(y0, 0):y1, max(x0, 0):x1], cv2.COLOR_BGR2GRAY)
        sharp = cv2.Laplacian(crop, cv2.CV_64F).var() if crop.size else 0
        out.append(dict(box=box, eyes=eyes, mouth=mouth, smile=smile, yaw=yaw, sharp=sharp))
    return out


def scenery(img, prev):
    """No people (travel reels): vivid, sharp, still frames win (a whip pan is colourful but smeared)."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    sharp = cv2.Laplacian(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
    motion = cv2.absdiff(img, prev).mean() if prev is not None else 0
    return hsv[..., 1].mean() / 64 + min(sharp / 400, 1) + hsv[..., 2].mean() / 255 - motion / 4


def score(fs, want, scene):
    if want == 0:
        return scene
    if len(fs) < want:
        return -1
    s = 0
    for f in fs:
        s += 2 * min(f["eyes"] / 0.28, 1) - (3 if f["eyes"] < 0.18 else 0)
        s += -6 * max(f["mouth"] - 0.04, 0) / 0.04  # mid-word mouths look odd
        s += 4 * f["smile"]
        s += min(f["sharp"] / 300, 1)
        s += 1.5 * max(1 - f["yaw"] / 0.25, 0)  # eye contact with the viewer stops the scroll
    return s / len(fs)


def spread(ranked, n=6, gap=1.0):
    """The n best of ranked [(score, key)] (best first): key t, at least gap s apart, or key (clip, t),
    one per clip (the sheet then offers other shots, not the winner's neighbours)."""
    def near(a, b):
        return a[0] == b[0] if isinstance(a, tuple) else abs(a - b) < gap

    picks = []
    for s, k in ranked:
        if not any(near(k, p) for _, p in picks):
            picks.append((s, k))
        if len(picks) == n:
            break
    return picks


def pick(video, skip, mesh):
    """6 best frames (score, t) with every face of the video in frame, plus the best frame without faces."""
    dur = ffprobe_duration(video)
    cands, prev = [], None
    for t, img in frames(video):
        if not (t < 0.5 or t > dur - 0.5 or any(a <= t <= b for a, b in skip)):
            cands.append((t, faces(img, mesh), scenery(img, prev)))
        prev = img  # the motion measure compares with the frame before
    want = max((len(fs) for _, fs, _ in cands), default=0)
    ranked = sorted(((score(fs, want, sc), t) for t, fs, sc in cands), reverse=True)
    if not ranked or ranked[0][0] < 0:
        sys.exit("no frame with every face visible: pass --at")
    views = [(sc, t) for t, fs, sc in cands if not fs]
    return spread(ranked), max(views)[1] if views else None


# ---------- drawing ----------
def grade(im):
    im = ImageEnhance.Color(im).enhance(1.15)
    im = ImageEnhance.Contrast(im).enhance(1.08)
    return im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))


def cover(im, w, h, cx=0.5, cy=0.5):
    """Scale + crop to fill w x h, the crop centred on (cx, cy) (fractions of im) as far as the edges allow."""
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x = round(min(max(cx * im.width - w / 2, 0), im.width - w))
    y = round(min(max(cy * im.height - h / 2, 0), im.height - h))
    return im.crop((x, y, x + w, y + h))


def shade(im, y0, y1, top_alpha, bottom_alpha):
    """vertical black gradient over rows y0..y1, alpha top_alpha -> bottom_alpha"""
    g = Image.new("L", (1, y1 - y0))
    for y in range(y1 - y0):
        g.putpixel((0, y), int(top_alpha + (bottom_alpha - top_alpha) * y / max(y1 - y0 - 1, 1)))
    layer = Image.new("RGB", (im.width, y1 - y0), BLACK)
    im.paste(layer, (0, y0), g.resize((im.width, y1 - y0)))


def block_fit(args, width, height):
    """block() at the largest scale (1.0 down to 0.55) whose height fits, or None."""
    for i in range(10):
        blk = block(args, width, 1.0 - 0.05 * i)
        if blk.height <= height:
            return blk
    return None


def block(args, width, scale=1.0):
    """The text stack as an RGBA image: zh (yellow), title (white on red), sub (white)."""
    rows = []
    zh = getattr(args, "zh", "")
    if zh:
        f = fit(ZH_FONT, zh, int(160 * scale), width)
        rows.append(("zh", zh, f, int(f.size * 0.09)))
    f = fit(TITLE_FONT, args.title, int(150 * scale), width - int(60 * scale))
    rows.append(("title", args.title, f, 0))
    if args.sub:
        f = fit(SUB_FONT, args.sub, int(64 * scale), width)
        rows.append(("sub", args.sub, f, int(f.size * 0.1)))
    gap, pad = int(26 * scale), int(28 * scale)
    sizes = []
    for kind, text, f, stroke in rows:
        x0, y0, x1, y1 = f.getbbox(text, stroke_width=stroke)
        sizes.append((x1 - x0 + (2 * pad if kind == "title" else 0), y1 - y0 + (2 * pad if kind == "title" else 0)))
    h = sum(s[1] for s in sizes) + gap * (len(rows) - 1)
    out = Image.new("RGBA", (width, h + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    y = 0
    for (kind, text, f, stroke), (bw, bh) in zip(rows, sizes, strict=True):
        x = (width - bw) // 2
        ox, oy = f.getbbox(text, stroke_width=stroke)[:2]
        if kind == "title":
            d.rounded_rectangle((x + 8, y + 10, x + bw + 8, y + bh + 10), int(18 * scale), fill=(0, 0, 0, 140))
            d.rounded_rectangle((x, y, x + bw, y + bh), int(18 * scale), fill=RED)
            d.text((x + pad - ox, y + pad - oy), text, font=f, fill=WHITE)
        else:
            d.text((x - ox + 6, y - oy + 8), text, font=f, fill=(0, 0, 0, 160), stroke_width=stroke, stroke_fill=(0, 0, 0, 160))
            d.text((x - ox, y - oy), text, font=f, fill=YELLOW if kind == "zh" else WHITE,
                   stroke_width=stroke or int(f.size * 0.08), stroke_fill=BLACK)
        y += bh + gap
    return out


def badge(im, text, cx, y, scale=1.0):
    """Series tag, centred on column cx."""
    if not text:
        return
    f = font(TITLE_FONT, int(64 * scale))
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = f.getbbox(text)
    p = int(18 * scale)
    x = cx - (x1 - x0 + 2 * p) // 2
    d.rounded_rectangle((x, y, x + x1 - x0 + 2 * p, y + y1 - y0 + 2 * p), int(16 * scale), fill=YELLOW,
                        outline=BLACK, width=max(int(4 * scale), 2))
    d.text((x + p - x0, y + p - y0), text, font=f, fill=BLACK)


def window(frame, cy, h):
    """1080 x h band of the frame (scaled to 1080x1920) centred on row cy."""
    y0 = int(min(max(cy - h / 2, 0), 1920 - h))
    return grade(frame.resize((1080, 1920), Image.LANCZOS).crop((0, y0, 1080, y0 + h)))


def split(frame, boxes, args, view):
    """9:16 reaction + view (zoominview): the face on top, the view below, the title on the seam."""
    s = frame.width / 1080
    cy = np.mean([(b[1] + b[3]) / 2 for b in boxes]) / s if boxes else 700
    im = Image.new("RGB", (1080, 1920))
    im.paste(window(frame, cy, 880), (0, 0))
    im.paste(window(view, 1060, 1040), (0, 880))
    ImageDraw.Draw(im).rectangle((0, 872, 1080, 888), fill=YELLOW)
    blk = block(args, CENTRE[1] - CENTRE[0])
    im.paste(blk, (CENTRE[0], min(880 - blk.height // 3, SAFE[3] - blk.height)), blk)
    badge(im, getattr(args, "badge", ""), 540, SAFE[1] - 20)
    return im


def horizontal(frame, boxes, args, view=None):
    """16:9 (chinese and --split): the people sharp on the right, the text block on the left on a solid panel
    (or on the view, darkened toward the text). Nothing is blurred and no text touches a face."""
    W, H = 1920, 1080
    s = frame.width / 1080
    cy = (np.mean([(b[1] + b[3]) / 2 for b in boxes]) / s) if boxes else 700
    if view is not None:  # the view itself behind the title, darkened toward the text side
        bg = grade(view.resize((W, int(W * view.height / view.width)), Image.LANCZOS))
        top = (bg.height - H) // 2
        bg = bg.crop((0, top, W, top + H))
        g = Image.linear_gradient("L").rotate(90, expand=True).resize((W, H))  # 255 left -> 0 right
        bg.paste(Image.new("RGB", (W, H), BLACK), (0, 0), g.point(lambda v: int(v * 0.7)))
    else:  # a solid panel: never a blurred copy of the people behind the text
        bg = Image.new("RGB", (W, H), PANEL)
    # the people: a window around the faces, sharp, on the right, every face inside it
    cut = getattr(args, "cut", 0)
    limit = int(cut * 1920) if cut else 1920
    fw = 1100
    span = (max(b[2] for b in boxes) - min(b[0] for b in boxes)) / s + 240 if boxes else 0
    win = min(max(950, span * H / fw), limit)  # tight on the faces: big faces read at thumbnail size
    ww = int(fw * win / H)
    if ww > 1080:  # the faces are far apart: a wider window, less of the panel
        ww, fw = 1080, int(1080 * H / win)
    y0 = int(min(max(cy - win * 0.45, 0), limit - win))
    cx = (np.mean([(b[0] + b[2]) / 2 for b in boxes]) / s) if boxes else 540
    x0 = int(min(max(cx - ww / 2, 0), 1080 - ww))
    fg = grade(frame.resize((1080, 1920), Image.LANCZOS).crop((x0, y0, x0 + ww, y0 + int(win))).resize((fw, H), Image.LANCZOS))
    bg.paste(fg, (W - fw, 0))
    if view is None:
        ImageDraw.Draw(bg).rectangle((W - fw - 12, 0, W - fw, H), fill=YELLOW)
    blk = block(args, W - fw - 40, scale=1.0)
    bg.paste(blk, (60, max((H - blk.height) // 2 + 40, 150)), blk)
    badge(bg, getattr(args, "badge", ""), 60 + blk.width // 2, 50)
    return bg


# ---------- emoji ----------
def split_emoji(text):
    """'Norway 🇳🇴' -> ('Norway', '🇳🇴'); emoji only at the end are supported."""
    i = len(text)
    while i and (ord(text[i - 1]) > 0x2500 or ord(text[i - 1]) == 0xFE0F):
        i -= 1
    return text[:i].rstrip(), text[i:]


def emoji(text, height):
    # Pillow without raqm can't shape emoji (flags are 2-codepoint ligatures), so take the glyph's
    # 160 px PNG straight from Apple Color Emoji's sbix table (named u1F1E8_u1F1ED, u1F4CD ...)
    from fontTools.ttLib import TTCollection

    f = TTCollection(EMOJI_FONT, lazy=True).fonts[0]
    name = "_".join(f"u{ord(c):04X}" for c in text if ord(c) != 0xFE0F)
    glyph = f["sbix"].strikes[160].glyphs.get(name)
    if glyph is None or glyph.graphicType != "png ":
        sys.exit(f"no emoji bitmap for {text!r} ({name})")
    img = Image.open(io.BytesIO(glyph.imageData)).convert("RGBA")
    img = img.crop(img.getbbox())
    return img.resize((round(img.width * height / img.height), height), Image.LANCZOS)


# ---------- output ----------
def save(im, path):
    for q in (92, 88, 84, 80):
        im.save(path, "JPEG", quality=q, optimize=True)
        if os.path.getsize(path) <= MAX_BYTES:
            return
    print(f"warning: {path} is over 2 MB", file=sys.stderr)


def picks_sheet(items):
    """items: [(BGR frame, label)] -> one row of 270x480 tiles with their labels on top."""
    sheet = Image.new("RGB", (6 * 270, 480 + 40), WHITE)
    for i, (img, label) in enumerate(items):
        sheet.paste(to_pil(img).resize((270, 480)), (i * 270, 40))
        ImageDraw.Draw(sheet).text((i * 270 + 8, 6), label, font=font(SUB_FONT, 26), fill=BLACK)
    return sheet
