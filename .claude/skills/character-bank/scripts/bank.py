#!/usr/bin/env python3
"""Character bank: real-looking reference portraits of recurring characters, reused by every video skill.

  bank.py list                                  characters, their views and who uses them
  bank.py body KEY VIEW                         the /v1/images/generations request for one view (JSON)
  bank.py render KEY VIEW OUT [N]               render N takes (default 2) -> OUT/KEY_VIEW_1.png ...
  bank.py keep KEY VIEW TAKE.png                store a picked take as bank/KEY/VIEW.jpg, record it in card.json
  bank.py scene OUT "SCENE TEXT" KEY [KEY ...]  a still of bank characters in a new scene, their views attached
        [--look FILE] [--size 1080x1920] [--n 2] [--prop "the cake=cake.jpg" ...]
        --prop attaches a picture of an object that must look the same in every scene (a cake, a car, a
        dress): the scene keeps that object exactly as in its picture.

Views: hero (front head-and-shoulders, the identity anchor), three_quarter, full (full-length).
hero renders from text alone; three_quarter, full and scene attach the stored views as reference images,
so the face stays the person in the bank. The API key is read here and never printed.
"""
import base64
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
BANK = HERE / "bank"
REAL = (HERE / "prompt/real.txt").read_text().strip()
API_BASE = os.environ.get("MUSEAI_BASE", "http://127.0.0.1:18610")
SIZES = {"hero": "1080x1350", "three_quarter": "1080x1350", "full": "1080x1920"}
FRAME = {
    "hero": "Head-and-shoulders portrait, vertical 4:5: the top of the hair just below the top edge, the frame ends "
            "at the upper chest, the face about half the frame width. {they} faces the camera straight on, eyes "
            "into the lens, a relaxed natural expression with the lips closed and the hint of a smile.",
    "three_quarter": "Head-and-shoulders portrait, vertical 4:5, the face turned three-quarters toward {their} own "
                     "LEFT, both eyes visible, eyes toward the camera, a relaxed natural expression.",
    "full": "Full-length photograph, vertical 9:16: {they} stands relaxed facing the camera, weight on one leg, arms "
            "loose at the sides, the whole body from the top of the hair to the shoes in the frame.",
}
BACKDROP = "A plain warm light-grey wall behind, softly out of focus, nothing else in the frame."


def card(key: str) -> dict:
    p = BANK / key / "card.json"
    if not p.exists():
        sys.exit(f"no character {key} (bank/{key}/card.json)")
    return json.loads(p.read_text())


def pronouns(c: dict) -> tuple[str, str]:
    return ("She", "her") if c["sex"] == "F" else ("He", "his")


def data_url(path: Path) -> str:
    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def view_body(key: str, view: str, n: int = 2) -> dict:
    c = card(key)
    if view not in FRAME:
        sys.exit(f"view must be one of {', '.join(FRAME)}")
    they, their = pronouns(c)
    first = c["name"].split()[0].strip("'")
    parts = [f"{first}, {c['identity']} Build: {c['build']}. Wearing {c['base_wardrobe']}.",
             FRAME[view].format(they=they, their=their), BACKDROP]
    images = []
    if view != "hero":
        hero = BANK / key / "hero.jpg"
        if not hero.exists():
            sys.exit(f"{key}: keep a hero view first (bank.py keep {key} hero TAKE.png)")
        images.append(data_url(hero))
        parts.insert(0, f"The person in image 1 is {first}: keep exactly the same face, age, skin tone, eyes, "
                        "brows, nose, lips, hair and jewellery as in image 1; only the pose and framing change.")
    body = {"prompt": " ".join(parts) + " " + REAL, "n": n, "size": SIZES[view], "response_format": "b64_json"}
    if images:
        body["image"] = images
    return body


def scene_body(scene: str, keys: list[str], look: str, size: str, n: int,
               props: list[tuple[str, Path]] = ()) -> dict:
    images, binds, people = [], [], []
    for k in keys:
        c = card(k)
        first = c["name"].split()[0].strip("'")
        idx = []
        for v in ("hero", "full"):
            p = BANK / k / f"{v}.jpg"
            if p.exists():
                images.append(data_url(p))
                idx.append(str(len(images)))
        if not idx:
            sys.exit(f"{k}: no stored views yet")
        binds.append(f"{first} is the person in image {' and image '.join(idx)}")
        people.append(f"{first}: {c['identity']}")
    lead = ("Reference images: " + "; ".join(binds) + ". Keep each face, age, skin tone, hair and jewellery exactly "
            "as in their reference images; the references show identity only, take the clothes, place, light and "
            "framing from this description, not from the references.")
    for name, path in props:
        images.append(data_url(path))
        lead += (f" {name[0].upper() + name[1:]} is the object in image {len(images)}: keep it exactly as in that image "
                 "(shape, size, colours, every decoration in the same place); only the angle and light follow this description.")
    prompt = " ".join([lead, scene, "People: " + " ".join(people), REAL, look]).strip()
    return {"prompt": prompt, "n": n, "size": size, "response_format": "b64_json", "image": images}


def post(body: dict, out: Path, stem: str) -> list[Path]:
    key = (Path(os.environ.get("MUSEAI_HOME", Path.home() / "Work/museai")) / "data/api_key").read_text().strip()
    req = urllib.request.Request(
        f"{API_BASE}/v1/images/generations", data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "X-Muse-Session": os.environ.get("MUSE_SESSION", os.environ.get("CLAUDE_CODE_SESSION_ID", "character-bank"))})
    with urllib.request.urlopen(req, timeout=float(os.environ.get("STILL_TIMEOUT", 7200))) as r:
        data = json.load(r)["data"]
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, x in enumerate(data, 1):
        p = out / f"{stem}_{i}.png"
        p.write_bytes(base64.b64decode(x["b64_json"]))
        paths.append(p)
        print(p)
    return paths


def keep(key: str, view: str, take: Path) -> None:
    c = card(key)
    dst = BANK / key / f"{view}.jpg"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(take), "-q:v", "2", str(dst)], check=True)
    c["views"][view] = dst.name
    (BANK / key / "card.json").write_text(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
    print(dst)


def main(a: list[str]) -> None:
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd = a[0]
    if cmd == "list":
        for d in sorted(p for p in BANK.iterdir() if (p / "card.json").exists()):
            c = card(d.name)
            print(f"{d.name:8} v{c['version']} {c['age']}{c['sex']} {c['name']:26} views: {', '.join(c['views']) or '-'}"
                  f"  used by: {', '.join(c['used_by'])}")
    elif cmd == "body":
        print(json.dumps(view_body(a[1], a[2])))
    elif cmd == "render":
        post(view_body(a[1], a[2], int(a[4]) if len(a) > 4 else 2), Path(a[3]).expanduser(), f"{a[1]}_{a[2]}")
    elif cmd == "keep":
        keep(a[1], a[2], Path(a[3]).expanduser())
    elif cmd == "scene":
        opts = {"--look": "", "--size": "1080x1920", "--n": "2"}
        rest, props = [], []
        it = iter(a[1:])
        for x in it:
            if x == "--prop":
                name, _, path = next(it).partition("=")
                props.append((name, Path(path).expanduser()))
            elif x in opts:
                opts[x] = next(it)
            else:
                rest.append(x)
        out, scene, keys = Path(rest[0]).expanduser(), rest[1], rest[2:]
        look = Path(opts["--look"]).read_text().strip() if opts["--look"] else ""
        post(scene_body(scene, keys, look, opts["--size"], int(opts["--n"]), props), out, "scene-" + "-".join(keys))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
