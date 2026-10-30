"""Usage: thumb.py <style> out_dir video.mp4 [video.mp4 ...] [style options] [--name ep33]
  uv run --no-project --python 3.12 --with mediapipe==0.10.14 --with opencv-python-headless==4.10.0.84 \\
      --with pillow==11.0.0 --with fonttools python scripts/thumb.py chinese out video.mp4 --title "..."
  thumb.py <style> -h   lists that style's options

Writes, from one frame:
  <name>_9x16.jpg   1080x1920  TikTok cover, YouTube Shorts, Facebook / Instagram Reels
  <name>_16x9.jpg   1920x1080  YouTube long-form, Facebook feed video (only with --wide: a horizontal video)
  <name>_picks.jpg  the 6 best-scoring frames (when the style picked one itself; choose another with --at)
Each style is scripts/styles/<style>.py with add_args(parser) and make(args) -> (9x16 image,
16x9 image, picks sheet or None, info line); the shared toolkit is scripts/core.py.
"""
import argparse
import importlib
import os
import sys

from core import save

STYLES = sorted(f[:-3] for f in os.listdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles"))
                if f.endswith(".py") and not f.startswith("_"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="style", required=True)
    mods = {}
    for name in STYLES:
        mods[name] = importlib.import_module(f"styles.{name}")
        p = sub.add_parser(name, help=(mods[name].__doc__ or "").strip().splitlines()[0])
        p.add_argument("out_dir")
        p.add_argument("videos", nargs="+")
        p.add_argument("--name", default="", help="file prefix (default: the first video's name)")
        p.add_argument("--wide", action="store_true",
                       help="also write the 16x9 thumbnail (only for a horizontal final video)")
        mods[name].add_args(p)
    args = ap.parse_args()
    name = args.name or os.path.splitext(os.path.basename(args.videos[0]))[0]
    os.makedirs(args.out_dir, exist_ok=True)
    v, h, sheet, info = mods[args.style].make(args)
    if sheet is not None:
        save(sheet, f"{args.out_dir}/{name}_picks.jpg")
    save(v, f"{args.out_dir}/{name}_9x16.jpg")
    kinds = ["9x16"]
    if args.wide:
        save(h, f"{args.out_dir}/{name}_16x9.jpg")
        kinds.append("16x9")
    print(info)
    for k in kinds:
        p = f"{args.out_dir}/{name}_{k}.jpg"
        print(f"THUMB {p} {os.path.getsize(p) // 1024} KB")


if __name__ == "__main__":
    sys.exit(main())
