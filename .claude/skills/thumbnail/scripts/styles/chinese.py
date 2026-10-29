"""chinese: people on camera (EVERYDAY CHINESE, teaching-video, product-ad with a presenter).

The best face frame (open eyes, not mid-word, smiling, sharp, toward the lens; every face of the video
in frame), the hook phrase in yellow hanzi, the title white on a red box, a sub line and an episode
badge. No faces at all: the most vivid, sharp frame.
"""
import sys

from core import (
    CENTRE,
    SAFE,
    badge,
    block,
    face_mesh,
    faces,
    grab,
    grade,
    horizontal,
    pick,
    picks_sheet,
    shade,
    to_pil,
)
from PIL import Image, ImageEnhance, ImageFilter


def add_args(p):
    p.add_argument("--title", required=True, help="2-5 words, the viewer's language, uppercase reads best")
    p.add_argument("--zh", default="", help="the big hook phrase in the taught language (optional)")
    p.add_argument("--sub", default="", help="small line under the title (pinyin, a question)")
    p.add_argument("--badge", default="", help='e.g. "TẬP 33"')
    p.add_argument("--at", type=float, help="frame time in seconds (skips the automatic pick)")
    p.add_argument("--skip", default="", help="time ranges to never pick, e.g. 17.2-20.2,30-31")
    p.add_argument("--cut", type=float, default=0,
                   help="burned-in captions start at this fraction of the height (e.g. 0.6): never shown")


def vertical(frame, boxes, args):
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
    badge(im, args.badge, 540, SAFE[1] - 20)
    return im


def make(args):
    if len(args.videos) > 1:
        sys.exit("chinese takes one video")
    video = args.videos[0]
    skip = [tuple(float(v) for v in r.split("-")) for r in args.skip.split(",") if r]
    mesh = face_mesh()
    sheet = None
    if args.at is None:
        picks, _ = pick(video, skip, mesh)
        sheet = picks_sheet([(grab(video, t), f"{t:.2f}s  {sc:.2f}") for sc, t in picks])
        t = picks[0][1]
    else:
        t = args.at
    img = grab(video, t)
    boxes = [f["box"] for f in faces(img, mesh)]
    frame = to_pil(img)
    return vertical(frame, boxes, args), horizontal(frame, boxes, args), sheet, f"frame {t:.2f}s, {len(boxes)} face(s)"
