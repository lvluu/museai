"""podcast: chinese-podcast episodes (no faces to camera): the brightest, most colourful sharp still, big text.

Candidates are the episode's 1920x1080 stills (`stills/sNN.png`, the first frame of each clip): sharper than
any frame of the 1248x704 clips or the captioned final. Each is scored on light (mean luminance near 0.55),
colour (Hasler-Suesstrunk colourfulness) and detail; the winner is lifted (exposure, saturation, warmth) so
the cover reads bright, never dark. The text never shrinks: the hanzi hook is huge, a long title wraps to
two lines on the red box instead of getting smaller.
"""
import cv2
import numpy as np
from core import (
    BLACK,
    RED,
    SAFE,
    SUB_FONT,
    TITLE_FONT,
    WHITE,
    YELLOW,
    ZH_FONT,
    font,
    picks_sheet,
)
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


def add_args(p):
    p.add_argument("--title", required=True, help="2-5 words in Vietnamese, uppercase (wraps, never shrinks)")
    p.add_argument("--zh", default="", help="the episode title in hanzi, the big yellow hook")
    p.add_argument("--sub", default="", help="one short line under the title")
    p.add_argument("--badge", default="", help='series tag at the top, e.g. "TRUYỆN TIẾNG TRUNG"')
    p.add_argument("--at", default="", help="force this candidate (file name, e.g. s07.png)")
    p.add_argument("--focus", type=float, default=None, help="x of the 9:16 crop centre, 0-1 (default: auto)")
    p.add_argument("--place", choices=["center", "bottom", "top"], default="center",
                   help="9:16 text block in the middle of the frame (default, owner's pick), the bottom of the safe "
                        "box, or under the badge")


def load(path):
    if path.lower().endswith((".png", ".jpg", ".jpeg")):
        return cv2.imread(path)
    cap = cv2.VideoCapture(path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 12)
    ok, img = cap.read()
    return img if ok else None


def score(img):
    small = cv2.resize(img, (480, 270), interpolation=cv2.INTER_AREA).astype(np.float32)
    b, g, r = small[..., 0], small[..., 1], small[..., 2]
    lum = (0.299 * r + 0.587 * g + 0.114 * b).mean() / 255
    rg, yb = r - g, 0.5 * (r + g) - b
    colour = (np.hypot(rg.std(), yb.std()) + 0.3 * np.hypot(rg.mean(), yb.mean())) / 100
    detail = min(cv2.Laplacian(cv2.cvtColor(small.astype(np.uint8), cv2.COLOR_BGR2GRAY), cv2.CV_64F).var() / 400, 1)
    light = 1 - min(abs(lum - 0.55) / 0.35, 1)
    return 0.45 * light + 0.35 * min(colour, 1) + 0.2 * detail, lum


def lift(im, lum):
    """Bright and warm: exposure toward mean 0.55, more saturation, a touch of warmth, crisp."""
    if lum < 0.5:
        g = np.log(0.55) / np.log(max(lum, 0.08))  # gamma that maps the mean to 0.55
        a = np.asarray(im).astype(np.float32) / 255
        im = Image.fromarray((np.clip(a ** g, 0, 1) * 255).astype(np.uint8))
    im = ImageEnhance.Color(im).enhance(1.3)
    im = ImageEnhance.Contrast(im).enhance(1.06)
    r, g, b = im.split()
    im = Image.merge("RGB", (r.point(lambda v: min(255, int(v * 1.04))), g, b.point(lambda v: int(v * 0.96))))
    return im.filter(ImageFilter.UnsharpMask(radius=2, percent=80, threshold=2))


def focus_x(img):
    """x (0-1) of the most detailed, brightest column band: where the subject is."""
    gray = cv2.cvtColor(cv2.resize(img, (480, 270)), cv2.COLOR_BGR2GRAY).astype(np.float32)
    energy = np.abs(cv2.Laplacian(gray, cv2.CV_32F)).mean(0) + gray.mean(0) / 8
    win = 152  # 9:16 window width at 270 high
    sums = np.convolve(energy, np.ones(win), "valid")
    return (int(sums.argmax()) + win / 2) / 480


def wrap(text, f, width):
    words, lines = text.split(), [""]
    for w in words:
        t = (lines[-1] + " " + w).strip()
        if f.getlength(t) <= width or not lines[-1]:
            lines[-1] = t
        else:
            lines.append(w)
    if len(lines) == 2:  # balance: the split that minimises the longer line, never an orphan word
        best = min(range(1, len(words)), key=lambda i: max(f.getlength(" ".join(words[:i])),
                                                           f.getlength(" ".join(words[i:]))))
        lines = [" ".join(words[:best]), " ".join(words[best:])]
    return lines


def text_block(args, width, zh_size, title_size, sub_size):
    """zh (huge yellow), title (white on red, wrapped), sub (white) as one RGBA image."""
    rows = []
    if args.zh:
        f = font(ZH_FONT, zh_size)
        while f.getlength(args.zh) > width:
            f = font(ZH_FONT, f.size - 8)
        rows.append(("zh", [args.zh], f))
    f = font(TITLE_FONT, title_size)
    rows.append(("title", wrap(args.title, f, width - 70), f))
    if args.sub:
        f = font(SUB_FONT, sub_size)
        while f.getlength(args.sub) > width:
            f = font(SUB_FONT, f.size - 4)
        rows.append(("sub", [args.sub], f))
    parts = []
    for kind, lines, f in rows:
        lh = f.getbbox("ĐẶgy是")[3] - f.getbbox("ĐẶgy是")[1]
        lead = int(lh * 0.18)
        h = len(lines) * lh + (len(lines) - 1) * lead
        pad = 30 if kind == "title" else 0
        im = Image.new("RGBA", (width, h + 2 * pad + 24), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        if kind == "title":
            bw = max(f.getlength(t) for t in lines) + 2 * 34
            x0 = (width - bw) / 2
            d.rounded_rectangle((x0 + 8, 10, x0 + bw + 8, h + 2 * pad + 10), 22, fill=(0, 0, 0, 120))
            d.rounded_rectangle((x0, 0, x0 + bw, h + 2 * pad), 22, fill=RED)
        top = f.getbbox("ĐẶgy是")[1]
        for i, t in enumerate(lines):
            x, y = (width - f.getlength(t)) / 2, pad + i * (lh + lead) - top
            if kind == "title":
                d.text((x, y), t, font=f, fill=WHITE)
            else:
                stroke = max(int(f.size * (0.07 if kind == "zh" else 0.09)), 4)
                d.text((x + 6, y + 8), t, font=f, fill=(0, 0, 0, 150), stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
                d.text((x, y), t, font=f, fill=YELLOW if kind == "zh" else WHITE, stroke_width=stroke, stroke_fill=BLACK)
        parts.append(im)
    gap = 18
    out = Image.new("RGBA", (width, sum(p.height for p in parts) + gap * (len(parts) - 1)), (0, 0, 0, 0))
    y = 0
    for p in parts:
        out.paste(p, (0, y), p)
        y += p.height + gap
    return out


def badge(im, text, cx, y, size):
    if not text:
        return
    f = font(TITLE_FONT, size)
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = f.getbbox(text)
    p = int(size * 0.3)
    x = cx - (x1 - x0 + 2 * p) // 2
    d.rounded_rectangle((x, y, x + x1 - x0 + 2 * p, y + y1 - y0 + 2 * p), int(size * 0.25), fill=YELLOW,
                        outline=BLACK, width=4)
    d.text((x + p - x0, y + p - y0), text, font=f, fill=BLACK)


def soft_shade(im, box, alpha):
    """a feathered dark oval behind the text only: legible on any frame, the rest stays bright"""
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).ellipse(box, fill=alpha)
    m = m.filter(ImageFilter.GaussianBlur(90))
    im.paste(Image.new("RGB", im.size, BLACK), (0, 0), m)


def vertical(src, cx, args):
    s = 1920 / src.height
    big = src.resize((round(src.width * s), 1920), Image.LANCZOS)
    x = round(min(max(cx * big.width - 540, 0), big.width - 1080))
    im = big.crop((x, 0, x + 1080, 1920)).filter(ImageFilter.UnsharpMask(radius=3, percent=70, threshold=2))
    w = 1080 - 2 * 90
    blk = text_block(args, w, 250, 132, 66)
    y = {"center": (1920 - blk.height) // 2 + 40, "bottom": SAFE[3] - blk.height - 40, "top": SAFE[1] + 100}[args.place]
    soft_shade(im, (40, y - 60, 1040, y + blk.height + 60), 110)
    im.paste(blk, (90, y), blk)
    badge(im, args.badge, 540, y - 100 if args.place == "center" else SAFE[1] - 10, 50)
    return im


def horizontal(src, args):
    im = src.resize((1920, 1080), Image.LANCZOS)
    w = 1200
    blk = text_block(args, w, 240, 116, 58)
    x, y = (1920 - w) // 2, (1080 - blk.height) // 2 + 40
    soft_shade(im, (x - 100, y - 120, x + w + 100, y + blk.height + 120), 120)
    im.paste(blk, (x, y), blk)
    badge(im, args.badge, 960, max(y - 100, 30), 44)
    return im


def make(args):
    cands = []
    for p in args.videos:
        img = load(p)
        if img is not None:
            sc, lum = score(img)
            cands.append((sc, lum, p, img))
    cands.sort(key=lambda c: -c[0])
    sheet = picks_sheet([(c[3], f"{c[2].rsplit('/', 1)[-1]} {c[0]:.2f}") for c in cands[:6]])
    best = next((c for c in cands if c[2].endswith("/" + args.at) or c[2] == args.at), None) if args.at else cands[0]
    sc, lum, path, img = best
    cx = args.focus if args.focus is not None else focus_x(img)
    src = lift(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)), lum)
    return vertical(src, cx, args), horizontal(src, args), sheet, f"pick {path} score {sc:.2f} lum {lum:.2f} x {cx:.2f}"
