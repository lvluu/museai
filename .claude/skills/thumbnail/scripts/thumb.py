"""Usage: thumb.py video.mp4 out_dir --title "MUA HOA SINH NHẬT" [--zh 你喜欢什么花？] [--sub "Nǐ xǐhuan shénme huā?"]
                 [--badge "TẬP 33"] [--at 12.4] [--skip 17.2-20.2,30-31] [--name ep33]
  uv run --no-project --python 3.12 --with mediapipe==0.10.14 --with opencv-python-headless==4.10.0.84 \\
      --with pillow==11.0.0 python scripts/thumb.py video.mp4 out --title "..."

Writes, from one frame of the video:
  <name>_9x16.jpg   1080x1920  TikTok cover, YouTube Shorts, Facebook / Instagram Reels
  <name>_16x9.jpg   1920x1080  YouTube long-form, Facebook feed video
  <name>_picks.jpg  the 6 best-scoring frames with their times (choose another with --at)
Frame pick (without --at): sampled at 4 fps, every face open-eyed, not mid-word, smiling, sharp, toward
the lens; all faces of the video in frame. No faces at all (travel): the most vivid, sharp frame.
--skip drops time ranges (vocab cards, cuts, burned-in text).
Pass the video BEFORE captions are burned in when there is one; on a captioned final pass --cut (where the
caption band starts, e.g. 0.6): the picture below it is replaced by a blurred mirror of the scene.
Text stays inside the 9:16 safe box x80-960 / y300-1560, which also survives the 3:4 profile-grid,
4:5 feed and 1:1 square crops (centre crops) and the TikTok / Reels UI (right column, bottom 20 %).
"""
import argparse
import os
import subprocess
import sys
import tempfile

import cv2
import mediapipe as mp
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ZH_FONT = ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb"
           ".asset/AssetData/PingFang.ttc", 11)  # PingFang SC Semibold
TITLE_FONT = ("/System/Library/Fonts/HelveticaNeue.ttc", 9)  # Condensed Black, has Vietnamese
SUB_FONT = ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 0)
YELLOW, RED, WHITE, BLACK = (255, 214, 10), (232, 23, 58), (255, 255, 255), (0, 0, 0)
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


def pick(video, skip, mesh):
    dur = ffprobe_duration(video)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", "fps=4,scale=540:-2", f"{tmp}/%05d.png"], check=True)
        names = sorted(os.listdir(tmp))
        cands, prev = [], None
        for i, n in enumerate(names):
            t = (i + 0.5) / 4
            img = cv2.imread(f"{tmp}/{n}")
            if not (t < 0.5 or t > dur - 0.5 or any(a <= t <= b for a, b in skip)):
                cands.append((t, faces(img, mesh), scenery(img, prev)))
            prev = img  # the motion measure compares with the frame before
    want = max((len(fs) for _, fs, _ in cands), default=0)
    ranked = sorted(((score(fs, want, sc), t) for t, fs, sc in cands), reverse=True)
    if not ranked or ranked[0][0] < 0:
        sys.exit("no frame with every face visible: pass --at")
    picks = []
    for s, t in ranked:  # 6 picks at least 1 s apart
        if all(abs(t - p) >= 1 for _, p in picks):
            picks.append((s, t))
        if len(picks) == 6:
            break
    views = [(sc, t) for t, fs, sc in cands if not fs]
    return picks, max(views)[1] if views else None


def grade(im):
    im = ImageEnhance.Color(im).enhance(1.15)
    im = ImageEnhance.Contrast(im).enhance(1.08)
    return im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))


def shade(im, y0, y1, top_alpha, bottom_alpha):
    """vertical black gradient over rows y0..y1, alpha top_alpha -> bottom_alpha"""
    g = Image.new("L", (1, y1 - y0))
    for y in range(y1 - y0):
        g.putpixel((0, y), int(top_alpha + (bottom_alpha - top_alpha) * y / max(y1 - y0 - 1, 1)))
    layer = Image.new("RGB", (im.width, y1 - y0), BLACK)
    im.paste(layer, (0, y0), g.resize((im.width, y1 - y0)))


def block(args, width, scale=1.0):
    """The text stack as an RGBA image: zh (yellow), title (white on red), sub (white)."""
    rows = []
    if args.zh:
        f = fit(ZH_FONT, args.zh, int(160 * scale), width)
        rows.append(("zh", args.zh, f, int(f.size * 0.09)))
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


def badge(im, text, x, y, scale=1.0):
    if not text:
        return
    f = font(TITLE_FONT, int(64 * scale))
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = f.getbbox(text)
    p = int(18 * scale)
    d.rounded_rectangle((x, y, x + x1 - x0 + 2 * p, y + y1 - y0 + 2 * p), int(16 * scale), fill=YELLOW,
                        outline=BLACK, width=max(int(4 * scale), 2))
    d.text((x + p - x0, y + p - y0), text, font=f, fill=BLACK)


def save(im, path):
    for q in (92, 88, 84, 80):
        im.save(path, "JPEG", quality=q, optimize=True)
        if os.path.getsize(path) <= MAX_BYTES:
            return
    print(f"warning: {path} is over 2 MB", file=sys.stderr)


def window(frame, cy, h):
    """1080 x h band of the frame (scaled to 1080x1920) centred on row cy."""
    y0 = int(min(max(cy - h / 2, 0), 1920 - h))
    return grade(frame.resize((1080, 1920), Image.LANCZOS).crop((0, y0, 1080, y0 + h)))


def vertical(frame, boxes, args, view=None):
    if view is not None:  # reaction on top, the view below, title on the seam
        s = frame.width / 1080
        cy = np.mean([(b[1] + b[3]) / 2 for b in boxes]) / s if boxes else 700
        im = Image.new("RGB", (1080, 1920))
        im.paste(window(frame, cy, 880), (0, 0))
        im.paste(window(view, 1060, 1040), (0, 880))
        ImageDraw.Draw(im).rectangle((0, 872, 1080, 888), fill=YELLOW)
        blk = block(args, CENTRE[1] - CENTRE[0])
        im.paste(blk, (CENTRE[0], min(880 - blk.height // 3, SAFE[3] - blk.height)), blk)
        badge(im, args.badge, SAFE[0], SAFE[1] - 20)
        return im
    im = grade(frame.resize((1080, 1920), Image.LANCZOS))
    if args.cut:  # burned-in text below: replace it with a blurred mirror of the picture above it
        c = int(args.cut * 1920)
        fill = im.crop((0, 2 * c - 1920 if 2 * c > 1920 else 0, 1080, c)).transpose(Image.FLIP_TOP_BOTTOM)
        fill = ImageEnhance.Brightness(fill.resize((1080, 1920 - c)).filter(ImageFilter.GaussianBlur(30))).enhance(0.6)
        blur = im.filter(ImageFilter.GaussianBlur(30))
        im.paste(fill, (0, c))
        seam = Image.linear_gradient("L").resize((1080, 200))  # feather the cut over 200 px
        im.paste(ImageEnhance.Brightness(blur.crop((0, c - 200, 1080, c))).enhance(0.8), (0, c - 200), seam)
    s = frame.width / 1080
    face_bottom = max(b[3] / s for b in boxes) if boxes else 1000
    face_top = min(b[1] / s for b in boxes) if boxes else 600
    blk = block(args, CENTRE[1] - CENTRE[0])
    below = SAFE[3] - max(face_bottom + 40, SAFE[1])
    if below >= blk.height:  # under the chins, bottom-anchored in the safe box
        y = SAFE[3] - blk.height
        shade(im, max(y - 260, 0), 1920, 0, 200)
    else:  # above the heads
        y = max(SAFE[1] + 110, int(face_top) - 40 - blk.height)
        shade(im, 0, y + blk.height + 200, 190, 0)
    im.paste(blk, (CENTRE[0], y), blk)
    badge(im, args.badge, SAFE[0], SAFE[1] - 20)
    return im


def horizontal(frame, boxes, args, view=None):
    W, H = 1920, 1080
    s = frame.width / 1080
    cy = (np.mean([(b[1] + b[3]) / 2 for b in boxes]) / s) if boxes else 700
    if view is not None:  # the view itself behind the title, darkened toward the text side
        bg = grade(view.resize((W, int(W * view.height / view.width)), Image.LANCZOS))
        top = (bg.height - H) // 2
        bg = bg.crop((0, top, W, top + H))
        g = Image.linear_gradient("L").rotate(90, expand=True).resize((W, H))  # 255 left -> 0 right
        bg.paste(Image.new("RGB", (W, H), BLACK), (0, 0), g.point(lambda v: int(v * 0.7)))
    else:
        bg = frame.resize((W, int(W * frame.height / frame.width)), Image.LANCZOS)
        top = int(min(max(cy * W / 1080 - H / 2, 0), bg.height - H))
        bg = bg.crop((0, top, W, top + H)).filter(ImageFilter.GaussianBlur(28))
        bg = ImageEnhance.Brightness(bg).enhance(0.55)
    # the people: a 1080x1215 window around the faces, sharp, on the right
    limit = int(args.cut * 1920) if args.cut else 1920
    win = min(950, limit)  # tight on the faces: big faces read at thumbnail size
    y0 = int(min(max(cy - win * 0.45, 0), limit - win))
    fw = min(int(1080 * H / win), 1100)
    cx = (np.mean([(b[0] + b[2]) / 2 for b in boxes]) / s) if boxes else 540
    ww = int(fw * win / H)
    x0 = int(min(max(cx - ww / 2, 0), 1080 - ww))
    fg = grade(frame.resize((1080, 1920), Image.LANCZOS).crop((x0, y0, x0 + ww, y0 + win)).resize((fw, H), Image.LANCZOS))
    mask = Image.new("L", fg.size, 255)
    for x in range(120):  # soft left edge
        ImageDraw.Draw(mask).line((x, 0, x, H), fill=int(255 * x / 120))
    bg.paste(fg, (W - fw, 0), mask)
    blk = block(args, W - fw - 40, scale=1.0)
    bg.paste(blk, (60, max((H - blk.height) // 2 + 40, 150)), blk)
    badge(bg, args.badge, 60, 50)
    return bg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out_dir")
    ap.add_argument("--title", required=True, help="2-5 words, the viewer's language, uppercase reads best")
    ap.add_argument("--zh", default="", help="the big hook phrase in the taught language (optional)")
    ap.add_argument("--sub", default="", help="small line under the title (pinyin, a question)")
    ap.add_argument("--badge", default="", help='e.g. "TẬP 33"')
    ap.add_argument("--at", type=float, help="frame time in seconds (skips the automatic pick)")
    ap.add_argument("--skip", default="", help="time ranges to never pick, e.g. 17.2-20.2,30-31")
    ap.add_argument("--cut", type=float, default=0,
                    help="burned-in captions start at this fraction of the height (e.g. 0.6): never shown")
    ap.add_argument("--split", action="store_true",
                    help="reaction + view (zoominview, travel with a person): face on top, the view below")
    ap.add_argument("--view", type=float, help="time of the view frame for --split (default: best frame without faces)")
    ap.add_argument("--name", default="", help="file prefix (default: the video's name)")
    args = ap.parse_args()
    skip = [tuple(float(v) for v in r.split("-")) for r in args.skip.split(",") if r]
    name = args.name or os.path.splitext(os.path.basename(args.video))[0]
    os.makedirs(args.out_dir, exist_ok=True)
    mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=4, refine_landmarks=False)

    view_t = args.view
    if args.at is None:
        picks, auto_view = pick(args.video, skip, mesh)
        view_t = view_t if view_t is not None else auto_view
        sheet = Image.new("RGB", (6 * 270, 480 + 40), WHITE)
        for i, (sc, t) in enumerate(picks):
            sheet.paste(Image.fromarray(cv2.cvtColor(grab(args.video, t), cv2.COLOR_BGR2RGB)).resize((270, 480)), (i * 270, 40))
            ImageDraw.Draw(sheet).text((i * 270 + 8, 6), f"{t:.2f}s  {sc:.2f}", font=font(SUB_FONT, 26), fill=BLACK)
        save(sheet, f"{args.out_dir}/{name}_picks.jpg")
        t = picks[0][1]
    else:
        t = args.at
    img = grab(args.video, t)
    boxes = [f["box"] for f in faces(img, mesh)]
    frame = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    view = None
    if args.split:
        if view_t is None:
            sys.exit("--split needs a frame without faces: pass --view")
        view = Image.fromarray(cv2.cvtColor(grab(args.video, view_t), cv2.COLOR_BGR2RGB))
    save(vertical(frame, boxes, args, view), f"{args.out_dir}/{name}_9x16.jpg")
    save(horizontal(frame, boxes, args, view), f"{args.out_dir}/{name}_16x9.jpg")
    print(f"frame {t:.2f}s, {len(boxes)} face(s)" + (f", view {view_t:.2f}s" if view else ""))
    for k in ("9x16", "16x9"):
        p = f"{args.out_dir}/{name}_{k}.jpg"
        print(f"THUMB {p} {os.path.getsize(p) // 1024} KB")


if __name__ == "__main__":
    main()
