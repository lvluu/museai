#!/usr/bin/env python3
"""chinese-podcast: a 16:9 Mandarin "emotional radio" story video with pinyin + Vietnamese captions.

  podcast.py bank                       (re)write bank/scripts.json: 1000 seeds = 50 themes x 20 story frames
  podcast.py next [--n 3] [--seed ID]   pick unused seeds + a random look / voice / music mix (prints JSON)
  podcast.py new DIR [--seed ID] [--date YYYY-MM-DD]
                                        next pick -> DIR/episode.json skeleton dated tomorrow (episodes go out
                                        the next day); write the lines, then go on
  podcast.py voice DIR                  edge-tts narration per line -> DIR/vo/lNN.wav + vo/durations.json
  podcast.py captions DIR               caption / date card / word card / outro PNGs -> DIR/cap/
  podcast.py stills DIR [-j 3]          one muse still per line -> DIR/stills/sNN.png (first frame for clips)
  podcast.py clips DIR [-j 3]           one muse video clip per line -> DIR/stills/sNN.mp4 (wins over the png)
  podcast.py music DIR                  ACE music bed from the episode's music id -> DIR/music.m4a (Colab)
  podcast.py compose DIR [--out F]      film -> DIR/<slug>.mp4 on the Colab render queue (PODCAST_REMOTE=0 here)
  podcast.py deliver DIR [--time 18h30] thumbnails + Desktop folder "Chinese NN · Day DD-MM HHhMM · slug" of the
                                        posting day (mp4, thumbnails, captions.txt, .museai-post), work folder to
                                        the Trash, this episode's render-queue folders deleted: run it at once
                                        after QA, never wait to be asked
  podcast.py record DIR --video F       append to ~/.config/museai/chinese-podcast-history.json

voice / captions need: uv run --no-project --python 3.12 --with edge-tts --with pypinyin --with pillow
--with lunardate python podcast.py ...   compose needs only python3 + ffmpeg (it runs on the render runtime).
"""

import argparse
import json
import os
import random
import re
import shlex
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
BANK = SKILL / "bank"
HIST = Path.home() / ".config/museai/chinese-podcast-history.json"
W, H, FPS = 1920, 1080, 30
LEAD = 3.2  # date card alone before the first line
OFF = 0.5  # voice starts this long after a shot's dissolve begins
XF = 0.9  # dissolve between shots
OUTRO = 7.0  # word recap at the end
NO_TEXT = "16:9 horizontal frame. No text, letters, subtitles, captions, logos or watermarks anywhere in the image."


def load(name):
    return json.loads((BANK / name).read_text())


def byid(items):
    return {x["id"]: x for x in items}


def history():
    try:
        return json.loads(HIST.read_text())
    except (OSError, ValueError):
        return []


def ep_load(d):
    return json.loads((Path(d) / "episode.json").read_text())


def run(cmd, **kw):
    r = subprocess.run(cmd, **kw)
    if r.returncode:
        sys.exit(f"failed ({r.returncode}): {shlex.join(map(str, cmd))[:300]}")
    return r


def dur(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


# ---------------------------------------------------------------- bank / pick


def cmd_bank(_a):
    themes, frames = load("themes.json"), load("frames.json")
    try:  # seeds already in the bank keep their ids (history and episodes point at them); new pairs append
        old = json.loads((BANK / "scripts.json").read_text())
    except (OSError, ValueError):
        old = []
    have = {(s["theme"], s["frame"]) for s in old}
    pairs = [(t, f) for t in themes for f in frames if (t["id"], f["id"]) not in have]
    random.Random(7 + len(old)).shuffle(pairs)  # a fixed order: neighbours differ in theme and frame
    tb, fb = byid(themes), byid(frames)
    seeds = [{"id": s["id"], "theme": s["theme"], "frame": s["frame"]} for s in old]
    seeds += [{"id": f"cp-{i:04d}", "theme": t["id"], "frame": f["id"]} for i, (t, f) in enumerate(pairs, len(old) + 1)]
    seeds = [{**s, "theme_zh": tb[s["theme"]]["zh"], "theme_vi": tb[s["theme"]]["vi"], "truth": tb[s["theme"]]["truth"],
              "frame_zh": fb[s["frame"]]["name"], "shape": fb[s["frame"]]["shape"], "looks": fb[s["frame"]]["looks"]}
             for s in seeds]
    (BANK / "scripts.json").write_text(json.dumps(seeds, ensure_ascii=False, indent=1) + "\n")
    print(f"wrote {BANK / 'scripts.json'}: {len(seeds)} seeds")


def pick(n=1, seed=None):
    seeds, hist = load("scripts.json"), history()
    used = {h.get("seed") for h in hist}
    last = hist[-15:]
    looks, voices, music = byid(load("looks.json")), load("voices.json"), byid(load("music.json"))
    rng = random.Random(time.time_ns())
    if seed:
        cands = [s for s in seeds if s["id"] == seed] or sys.exit(f"no seed {seed}")
    else:
        recent_t = {h.get("theme") for h in last}
        recent_f = {h.get("frame") for h in hist[-5:]}
        cands = [s for s in seeds if s["id"] not in used and s["theme"] not in recent_t and s["frame"] not in recent_f]
        cands = cands or [s for s in seeds if s["id"] not in used]
    out, prev = [], (hist[-1] if hist else {})
    for s in cands[:n]:
        look = rng.choice([x for x in s["looks"] if x != prev.get("look")] or s["looks"])
        voice = rng.choice([v for v in voices if v["id"] != prev.get("voice")] or voices)
        mus = rng.choice([m for m in looks[look]["music"] if m != prev.get("music")] or looks[look]["music"])
        out.append({**s, "look": look, "voice": voice["id"], "voice_feel": voice["feel"], "music": mus,
                    "music_style": music[mus]["style"]})
    return out


def cmd_next(a):
    print(json.dumps(pick(a.n, a.seed), ensure_ascii=False, indent=1))


def cmd_new(a):
    p = pick(1, a.seed)[0]
    d = Path(a.dir).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    f = d / "episode.json"
    if f.exists():
        sys.exit(f"{f} exists")
    ep = {"seed": p["id"], "theme": p["theme"], "frame": p["frame"], "look": p["look"], "voice": p["voice"],
          "music": p["music"], "date": a.date or (date.today() + timedelta(days=1)).isoformat(), "slug": d.name, "title": "", "title_vi": "",
          "brief": {"truth": p["truth"], "shape": p["shape"], "theme": f"{p['theme_zh']} ({p['theme_vi']})"},
          "lines": [{"zh": "", "vi": "", "shot": "", "word": None}]}
    f.write_text(json.dumps(ep, ensure_ascii=False, indent=1) + "\n")
    print(f"wrote {f}\n{json.dumps(p, ensure_ascii=False, indent=1)}")


# ---------------------------------------------------------------- voice


def cmd_voice(a):
    import asyncio

    import edge_tts

    d = Path(a.dir)
    ep = ep_load(d)
    v = byid(load("voices.json"))[ep["voice"]]
    if not (v["voice"].startswith("zh-CN-") and v["voice"].count("-") == 2):
        sys.exit(f"voice {v['voice']}: only Standard Mandarin zh-CN-<Name>Neural")
    vo = d / "vo"
    vo.mkdir(exist_ok=True)
    durs = {}
    for i, ln in enumerate(ep["lines"]):
        wav = vo / f"l{i:02d}.wav"
        text = ln.get("say") or ln["zh"]
        if not wav.exists() or a.fresh:
            mp3 = vo / f"l{i:02d}.mp3"
            for k in range(4):
                try:
                    asyncio.run(edge_tts.Communicate(text, v["voice"], rate=ln.get("rate", v["rate"]),
                                                     pitch=v["pitch"]).save(str(mp3)))
                    break
                except Exception as e:  # network hiccup: edge-tts is a web service
                    print(f"l{i:02d}: {e}; retry", file=sys.stderr)
                    time.sleep(3 * (k + 1))
            else:
                sys.exit(f"l{i:02d}: edge-tts failed")
            # trim the service's leading/trailing silence, warm close-mic tone (no room, no echo)
            trim = "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05"
            run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-af",
                 f"{trim},areverse,{trim},areverse,highpass=f=70,lowpass=f=11000,"
                 "equalizer=f=180:t=q:w=1:g=2,acompressor=threshold=-22dB:ratio=2.5:attack=8:release=220",
                 "-ar", "48000", "-ac", "1", wav])
            mp3.unlink()
        durs[f"l{i:02d}"] = round(dur(wav), 3)
        print(f"l{i:02d} {durs[f'l{i:02d}']:.2f}s {text}")
    (vo / "durations.json").write_text(json.dumps(durs, indent=1) + "\n")
    print(f"voice: {len(durs)} lines, {sum(durs.values()):.1f}s of speech")


# ---------------------------------------------------------------- captions

FONT_HZ = "/System/Library/Fonts/Hiragino Sans GB.ttc"
FONT_SERIF_HZ = "/System/Library/Fonts/Supplemental/Songti.ttc"
FONT_LAT = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
FONT_IT = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"
CREAM = (246, 238, 222)
INK = (34, 30, 26)
# neutral tones pypinyin's dictionary gives a full tone (learners hear them neutral from the narrator)
NEUTRAL = {"妈妈": "mā ma", "爸爸": "bà ba", "奶奶": "nǎi nai", "爷爷": "yé ye", "姐姐": "jiě jie", "哥哥": "gē ge",
           "时候": "shí hou", "头发": "tóu fa", "告诉": "gào su", "晚上": "wǎn shang", "早上": "zǎo shang",
           "看看": "kàn kan", "打个": "dǎ ge", "认不出来": "rèn bu chū lái", "东西": "dōng xi", "衣服": "yī fu",
           "朋友": "péng you", "知道": "zhī dao", "喜欢": "xǐ huan", "觉得": "jué de", "事情": "shì qing",
           "地方": "dì fang", "外婆": "wài pó", "窗户": "chuāng hu", "舒服": "shū fu", "收拾": "shōu shi"}
PUNCT = set("，。！？、；：,.!?;:…“”‘’「」（）() ")


def font(path, size, index=0):
    from PIL import ImageFont

    return ImageFont.truetype(path, size, index=index)


def tone(syl):
    for t, marks in enumerate(("āēīōūǖ", "áéíóúǘ", "ǎěǐǒǔǚ", "àèìòùǜ"), 1):
        if any(m in syl for m in marks):
            return t
    return 5


def sandhi(hz, py):
    """Spoken tones of 一 and 不 (一阵 yí zhèn, 一些 yì xiē, 不是 bú shì); ordinal 一 (第一, 十一, 一月) stays yī."""
    out = list(py)
    for i, c in enumerate(hz):
        nxt = tone(py[i + 1]) if i + 1 < len(hz) else 0
        if c == "一" and nxt and not (i and hz[i - 1] in "第十") and hz[i + 1] not in "月号日":
            out[i] = "yí" if nxt == 4 else "yì"
        elif c == "不" and nxt == 4 and py[i] in ("bù", "bú"):
            out[i] = "bú"
    return out


def syllables(zh, override=None):
    """[(char, pinyin or '')] one per character; OVERRIDE = space-separated syllables for the hanzi only."""
    from pypinyin import Style, load_phrases_dict, pinyin

    load_phrases_dict({k: [[s] for s in v.split()] for k, v in NEUTRAL.items()})
    chars = list(zh)
    hz = [c for c in chars if "一" <= c <= "鿿"]
    if override:
        py = override.split()
        if len(py) != len(hz):
            sys.exit(f"py override has {len(py)} syllables for {len(hz)} hanzi: {zh}")
    else:
        py = sandhi(hz, [p[0] for p in pinyin("".join(hz), style=Style.TONE)])  # phrase-aware: 还车 huán
    it = iter(py)
    return [(c, next(it) if "一" <= c <= "鿿" else "") for c in chars]


def tw(f, s):
    if not s:
        return 0
    b = f.getbbox(s)
    return b[2] - b[0]


def ruby_rows(pairs, fh, fp, maxw):
    cells = [(c, p, max(tw(fh, c), tw(fp, p) + 18 if p else 0)) for c, p in pairs]
    total = sum(w for *_, w in cells)
    if total <= maxw:
        return [cells]
    # break at the punctuation nearest the middle, else the middle
    acc, mid, best = 0, total / 2, None
    for i, (c, _, w) in enumerate(cells):
        acc += w
        if c in PUNCT and 0 < i < len(cells) - 1:
            if best is None or abs(acc - mid) < abs(best[1] - mid):
                best = (i + 1, acc)
    cut = best[0] if best else next(i for i, x in enumerate(cells) if sum(w for *_, w in cells[: i + 1]) >= mid)
    return [cells[:cut], cells[cut:]]


def draw_shadow_text(img, xy, text, f, fill, shadow=150, r=3):
    from PIL import Image, ImageDraw, ImageFilter

    # blur only a box around the text: a full-frame blur per glyph takes minutes per caption
    b = f.getbbox(text)
    pad = 4 * r + 4
    x0, y0 = int(xy[0] + b[0]) - pad, int(xy[1] + b[1]) - pad
    sh = Image.new("RGBA", (b[2] - b[0] + 2 * pad + 4, b[3] - b[1] + 2 * pad + 4), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((xy[0] - x0 + 2, xy[1] - y0 + 3), text, font=f, fill=(0, 0, 0, shadow))
    sh = sh.filter(ImageFilter.GaussianBlur(r))
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    layer.paste(sh, (x0, y0))
    img.alpha_composite(layer)
    ImageDraw.Draw(img).text(xy, text, font=f, fill=fill)


def draw_ruby(img, pairs, y, hz_size=60, py_size=28, color=(255, 255, 255, 255), pycolor=(*CREAM, 235)):
    fh, fp = font(FONT_HZ, hz_size), font(FONT_LAT, py_size)
    rows = ruby_rows(pairs, fh, fp, W - 220)
    row_h = py_size + hz_size + 22
    for r, cells in enumerate(rows):
        x = (W - sum(w for *_, w in cells)) / 2
        yy = y + r * row_h
        for c, p, w in cells:
            if p:
                draw_shadow_text(img, (x + (w - tw(fp, p)) / 2, yy), p, fp, pycolor, shadow=170, r=2)
            draw_shadow_text(img, (x + (w - tw(fh, c)) / 2, yy + py_size + 10), c, fh, color)
            x += w
    return y + len(rows) * row_h


def pill(img, cx, y, text, f, fg=INK, bg=(250, 247, 240, 228), padx=22, pady=10):
    from PIL import Image, ImageDraw

    w = tw(f, text)
    asc, desc = f.getmetrics()
    box = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(box)
    dr.rounded_rectangle((cx - w / 2 - padx, y, cx + w / 2 + padx, y + asc + desc + 2 * pady), radius=10, fill=bg)
    dr.text((cx - w / 2, y + pady), text, font=f, fill=fg)
    img.alpha_composite(box)
    return y + asc + desc + 2 * pady


def gradient(img, top, alpha):
    from PIL import Image, ImageDraw

    g = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(g)
    for y in range(top, H):
        dr.line([(0, y), (W, y)], fill=(0, 0, 0, int(alpha * ((y - top) / (H - top)) ** 1.4)))
    img.alpha_composite(g)


def caption_png(ln, out):
    from PIL import Image

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pairs = syllables(ln["zh"], ln.get("py"))
    fh, fp = font(FONT_HZ, 60), font(FONT_LAT, 28)
    rows = len(ruby_rows(pairs, fh, fp, W - 220))
    block = rows * (28 + 60 + 22) + 70
    y0 = H - 70 - block
    gradient(img, max(0, y0 - 160), 175)
    y = draw_ruby(img, pairs, y0)
    pill(img, W / 2, y + 6, ln["vi"], font(FONT_LAT, 31))
    img.save(out)


def lunar_line(d):
    from lunardate import LunarDate

    months = "正二三四五六七八九十冬腊"
    ld = LunarDate.from_solar_date(d.year, d.month, d.day)
    n = ld.day
    day = {10: "初十", 20: "二十", 30: "三十"}.get(n) or (["初", "十", "廿"][(n - 1) // 10] + "一二三四五六七八九"[(n - 1) % 10])
    week = "一二三四五六日"[d.weekday()]
    return f"农历{'闰' if ld.isLeapMonth else ''}{months[ld.month - 1]}月{day} · 星期{week}"


def card_png(ep, out):
    """Opening date card (reel 1460615008861785): a big translucent date, the lunar date, the title."""
    from PIL import Image, ImageDraw

    d = date.fromisoformat(ep["date"])
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    veil = Image.new("RGBA", (W, H), (0, 0, 0, 70))
    img.alpha_composite(veil)
    big = font(FONT_IT, 150)
    s = f"{d.strftime('%b')}. {d.day}"
    draw_shadow_text(img, ((W - tw(big, s)) / 2, 150), s, big, (255, 255, 255, 205), shadow=90, r=6)
    lf = font(FONT_SERIF_HZ, 40)
    ll = lunar_line(d)
    draw_shadow_text(img, ((W - tw(lf, ll)) / 2, 345), ll, lf, (*CREAM, 240))
    ImageDraw.Draw(img).line([(W / 2 - 60, 420), (W / 2 + 60, 420)], fill=(*CREAM, 200), width=2)
    pairs = syllables(ep["title"], ep.get("title_py"))
    y = draw_ruby(img, pairs, 470, hz_size=92, py_size=34)
    vf = font(FONT_IT, 40)
    draw_shadow_text(img, ((W - tw(vf, ep["title_vi"])) / 2, y + 12), ep["title_vi"], vf, (*CREAM, 235))
    img.save(out)


def word_png(wd, out):
    """New-word card, top right, while its line plays."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fh, fp, fv, fl = font(FONT_HZ, 58), font(FONT_LAT, 28), font(FONT_IT, 28), font(FONT_LAT, 20)
    w = max(tw(fh, wd["zh"]), tw(fp, wd["py"]), tw(fv, wd["vi"]), tw(fl, "生词 · từ mới")) + 56
    x0, y0 = W - 70 - w, 60
    box = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(box).rounded_rectangle((x0, y0, x0 + w, y0 + 224), radius=16, fill=(20, 18, 16, 150))
    img.alpha_composite(box)
    dr = ImageDraw.Draw(img)
    dr.text((x0 + 28, y0 + 18), "生词 · từ mới", font=fl, fill=(*CREAM, 190))
    dr.text((x0 + 28, y0 + 48), wd["py"], font=fp, fill=(*CREAM, 255))
    dr.text((x0 + 28, y0 + 94), wd["zh"], font=fh, fill=(255, 255, 255, 255))
    dr.text((x0 + 28, y0 + 170), wd["vi"], font=fv, fill=(*CREAM, 230))
    img.save(out)


def outro_png(ep, out):
    from PIL import Image, ImageDraw

    words = [ln["word"] for ln in ep["lines"] if ln.get("word")]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 120)))
    dr = ImageDraw.Draw(img)
    hf = font(FONT_SERIF_HZ, 50)
    head = "今天的词 · Từ hôm nay"
    draw_shadow_text(img, ((W - tw(hf, head)) / 2, 150), head, hf, (*CREAM, 255))
    fh, fp, fv = font(FONT_HZ, 54), font(FONT_LAT, 32), font(FONT_IT, 34)
    y = 270
    for wd in words:
        dr.text((560, y), wd["zh"], font=fh, fill=(255, 255, 255, 255))
        dr.text((860, y + 14), wd["py"], font=fp, fill=(*CREAM, 240))
        dr.text((1160, y + 12), wd["vi"], font=fv, fill=(*CREAM, 220))
        y += 100
    img.save(out)


def cmd_captions(a):
    d = Path(a.dir)
    ep = ep_load(d)
    cap = d / "cap"
    cap.mkdir(exist_ok=True)
    for i, ln in enumerate(ep["lines"]):
        caption_png(ln, cap / f"l{i:02d}.png")
        if ln.get("word"):
            word_png(ln["word"], cap / f"w{i:02d}.png")
        print(f"l{i:02d} " + " ".join(p for _, p in syllables(ln["zh"], ln.get("py")) if p))
    card_png(ep, cap / "card.png")
    outro_png(ep, cap / "outro.png")
    print(f"captions: {cap}")


# ---------------------------------------------------------------- stills / music


def muse_key():
    for home in (SKILL.parents[2], Path(os.environ.get("MUSEAI_HOME", "~/dev/museai-work")).expanduser()):
        if (home / "data/api_key").is_file():
            return (home / "data/api_key").read_text().strip()
    sys.exit("no data/api_key (MUSEAI_HOME)")


def still(prompt, out, key):
    import base64
    import urllib.request

    body = json.dumps({"prompt": prompt, "n": 1, "size": "1920x1080", "response_format": "b64_json"}).encode()
    base = os.environ.get("MUSEAI_BASE", "http://127.0.0.1:18610")
    for k in range(6):
        try:
            req = urllib.request.Request(f"{base}/v1/images/generations", data=body, headers={
                "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                data = json.loads(r.read())["data"][0]["b64_json"]
            out.write_bytes(base64.b64decode(data))
            return True
        except Exception as e:  # account busy / upstream hiccup: muse-video retries the same way
            print(f"{out.name}: {e}; retry {k + 1}", file=sys.stderr, flush=True)
            time.sleep(20 * (k + 1))
    return False


def cmd_stills(a):
    from concurrent.futures import ThreadPoolExecutor

    d = Path(a.dir)
    ep = ep_load(d)
    look = byid(load("looks.json"))[ep["look"]]
    st = d / "stills"
    st.mkdir(exist_ok=True)
    key = muse_key()
    jobs = []
    for i, ln in enumerate(ep["lines"]):
        out = st / f"s{i:02d}.png"
        if not out.exists() or (a.only and i in a.only):
            jobs.append((f"{look['block']} {ln['shot']} {NO_TEXT}", out))
    with ThreadPoolExecutor(a.j) as ex:
        res = list(ex.map(lambda j: (j[1].name, still(j[0], j[1], key)), jobs))
    bad = [n for n, ok in res if not ok]
    print(f"stills: {len(jobs) - len(bad)}/{len(jobs)} new in {st}" + (f"; FAILED {bad}" if bad else ""))
    sys.exit(1 if bad else 0)


def cmd_music(a):
    d = Path(a.dir)
    ep = ep_load(d)
    m = byid(load("music.json"))[ep["music"]]
    secs = int(plan(d, ep)[-1]["end"] + 8)
    script = SKILL.parent / "healing-video/scripts/music"
    # healing, never dramatic: the soft preset and its calm gate (no BUSY_OK); exit 3 = take refused, next seed
    env = {k: v for k, v in os.environ.items() if k not in ("BUSY_OK", "SUNNY_OK")} | {"MOOD": "soft", "TAGS": m["tags"]}
    for seed in range(a.seed, a.seed + a.tries):
        r = subprocess.run([str(script), m["style"], str(d / "music.m4a"), str(secs), str(seed)], env=env)
        if r.returncode != 3:
            sys.exit(r.returncode)
        print(f"music: seed {seed} not calm enough, next seed", file=sys.stderr)
    sys.exit(f"music: no calm take in seeds {a.seed}..{a.seed + a.tries - 1}")


# ---------------------------------------------------------------- clips

# a locked camera: qa.py --travel fails a drift above 3 % of the width per second as time-lapse, and a muse
# "slow push-in" drifts 3-17 %/s (ep005); only the scene moves
CLIP_MOTION = ("One continuous real video shot from a locked camera on a tripod: the camera does not pan, zoom, push "
               "in or drift. Only small living movement in the scene (steam, leaves, light, a hand, a passer-by far "
               "away). Calm and unhurried. No cuts, no speech, no one talking to camera, faces never close.")


def cmd_clips(a):
    """Real muse video per line (the user wants video, not a moving still): muse-video, 16:9, the line's still as
    first frame when there is one so the look matches the date card and the other shots."""
    from concurrent.futures import ThreadPoolExecutor

    d = Path(a.dir)
    ep = ep_load(d)
    look = byid(load("looks.json"))[ep["look"]]
    st = d / "stills"
    st.mkdir(exist_ok=True)
    segs = {p["i"]: p["seg"] for p in plan(d, ep)} if (d / "vo/durations.json").exists() else {}
    mv = SKILL.parent / "muse-video/scripts/muse-video"
    jobs = [i for i in range(len(ep["lines"])) if not (st / f"s{i:02d}.mp4").exists() or (a.only and i in a.only)]

    def one(i):
        ln, out = ep["lines"][i], st / f"s{i:02d}.mp4"
        env = {**os.environ, "SIZE": "16:9", "NO_OPEN": "1", "OUT_NAME": out.name, "RETAKE": "1",
               "DURATION": str(min(10, max(6, int(segs.get(i, 8)) + 1)))}
        first = st / f"s{i:02d}.png"
        if first.exists():
            head = first.read_bytes()[:12]
            ext = ".webp" if head[8:12] == b"WEBP" else ".jpg" if head[:2] == b"\xff\xd8" else ".png"
            img = st / f".first{i:02d}{ext}"
            img.write_bytes(first.read_bytes())
            env["IMAGE"] = str(img)
        prompt = f"{look['block']} {ln['shot']} {CLIP_MOTION} {NO_TEXT}"
        with open(d / "clips.log", "a") as log:
            r = subprocess.run([str(mv), prompt, str(st)], env=env, stdout=log, stderr=subprocess.STDOUT)
        if "IMAGE" in env:
            Path(env["IMAGE"]).unlink(missing_ok=True)
        return out.name, r.returncode == 0 and out.exists()

    with ThreadPoolExecutor(a.j) as ex:
        res = list(ex.map(one, jobs))
    bad = [n for n, ok in res if not ok]
    print(f"clips: {len(jobs) - len(bad)}/{len(jobs)} new in {st}" + (f"; FAILED {bad}" if bad else ""))
    sys.exit(1 if bad else 0)


# ---------------------------------------------------------------- compose


def plan(d, ep):
    durs = json.loads((d / "vo/durations.json").read_text())
    t, out = 0.0, []
    n = len(ep["lines"])
    for i, ln in enumerate(ep["lines"]):
        off = LEAD if i == 0 else OFF
        vo = durs[f"l{i:02d}"]
        pause = ln.get("pause", 1.3 if ln["zh"].rstrip().endswith(("。", "？", "！", "…")) else 0.8)
        slot = off + vo + pause
        seg = slot + XF + (OUTRO if i == n - 1 else 0)
        out.append({"i": i, "start": t, "off": off, "vo": vo, "slot": slot, "seg": seg, "end": t + seg})
        t += slot
    return out


def seg_video(d, p, ln, build, enc):
    i = p["i"]
    src = d / "stills" / f"s{i:02d}.mp4"
    if not src.exists():
        src = d / "stills" / f"s{i:02d}.png"
    frames = int(round(p["seg"] * FPS))
    if src.suffix == ".png":
        # slow push-in or pull-out from a 4K copy (zoompan at 1080 jitters); alternate direction per shot
        z0, z1 = (1.0, 1.07) if i % 2 == 0 else (1.07, 1.0)
        dx = [0.5, 0.45, 0.55][i % 3]
        z = f"{z0}+({z1 - z0})*on/{frames}"
        inp = ["-loop", "1", "-framerate", str(FPS), "-t", f"{p['seg']:.3f}", "-i", str(src)]
        base = (f"[0:v]scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2},"
                f"zoompan=z='{z}':x='(iw-iw/zoom)*{dx}':y='(ih-ih/zoom)/2':d=1:s={W}x{H}:fps={FPS}")
    else:
        slow = max(1.0, p["seg"] / max(dur(src), 0.1))  # a short clip plays slower, never loops (a loop jumps)
        inp = ["-t", f"{p['seg']:.3f}", "-i", str(src)] if slow == 1.0 else ["-i", str(src)]
        base = (f"[0:v]setpts={slow:.4f}*(PTS-STARTPTS),scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H},fps={FPS},trim=0:{p['seg']:.3f},setpts=PTS-STARTPTS")
    grade = "eq=contrast=0.97:saturation=0.9:gamma=1.02,noise=alls=5:allf=t,vignette=PI/5"
    fc = [f"{base},{grade},format=rgba[v0]"]
    ov = []  # (png, t0, t1)
    a0, a1 = max(0.0, p["off"] - 0.25), p["off"] + p["vo"] + 0.45
    ov.append((d / "cap" / f"l{i:02d}.png", a0, a1))
    if (d / "cap" / f"w{i:02d}.png").exists():
        ov.append((d / "cap" / f"w{i:02d}.png", a0 + 0.3, min(p["seg"] - 0.2, a1 + 1.2)))
    if i == 0:
        ov.insert(0, (d / "cap" / "card.png", 0.2, a1 + 0.2))
    if p["seg"] > p["slot"] + XF + 1:  # last shot: the word recap after the final line
        ov.append((d / "cap" / "outro.png", p["slot"], p["seg"]))
    last = "v0"
    for k, (png, t0, t1) in enumerate(ov, 1):
        inp += ["-loop", "1", "-framerate", str(FPS), "-t", f"{p['seg']:.3f}", "-i", str(png)]
        fc.append(f"[{k}:v]format=rgba,fade=t=in:st={t0:.2f}:d=0.35:alpha=1,"
                  f"fade=t=out:st={max(t0 + 0.4, t1 - 0.35):.2f}:d=0.35:alpha=1[o{k}]")
        fc.append(f"[{last}][o{k}]overlay=0:0:format=auto[v{k}]")
        last = f"v{k}"
    fc.append(f"[{last}]format=yuv420p[out]")
    out = build / f"seg{i:02d}.mp4"
    run(["ffmpeg", "-v", "error", "-y", *inp, "-filter_complex", ";".join(fc), "-map", "[out]",
         "-frames:v", str(frames), *enc, "-an", str(out)])
    return out


def cmd_compose(a):
    d = Path(a.dir).resolve()
    ep = ep_load(d)
    out = Path(a.out or d / f"{ep['slug']}.mp4").resolve()
    pl = plan(d, ep)
    music = Path(a.music).resolve() if a.music else d / "music.m4a"
    if os.environ.get("PODCAST_REMOTE", "1") != "0" and os.environ.get("RENDER_LOCAL") != "1":
        sys.path.insert(0, str(SKILL.parent / "muse-video" / "scripts"))
        import remote

        files = [d / "episode.json", *sorted((d / "vo").glob("l*.wav")), d / "vo/durations.json",
                 *sorted((d / "cap").glob("*.png")),
                 *[f for f in sorted((d / "stills").glob("s*.*")) if f.suffix in (".png", ".mp4")]]
        assets = {"music" + music.suffix: str(music)} if music.exists() else {}
        cmd = ("PODCAST_REMOTE=0 HV_NVENC=1 python3 \"$MUSEAI/.claude/skills/chinese-podcast/scripts/podcast.py\" "
               "compose w --out out.mp4" + (f" --music w/_assets/music{music.suffix}" if assets else ""))
        remote.compose_here_or_exit("compose", d, files, assets, cmd, str(out), name=f"{ep['slug']}-compose")
        print(f"wrote {out} ({dur(out):.1f} s)")
        return
    build = d / "build"
    build.mkdir(exist_ok=True)
    nv = os.environ.get("HV_NVENC") == "1"
    enc = (["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "20", "-b:v", "0"] if nv
           else ["-c:v", "libx264", "-preset", "medium", "-crf", "19"]) + ["-pix_fmt", "yuv420p", "-r", str(FPS)]
    segs = [seg_video(d, p, ep["lines"][p["i"]], build, enc) for p in pl]  # no zip(strict=): Mac python3 is 3.9
    print(f"compose: {len(segs)} shots", flush=True)
    total = pl[-1]["end"]
    # video: dissolve chain
    inp, fc, last = [], [], "0:v"
    for s in segs:
        inp += ["-i", str(s)]
    for k in range(1, len(segs)):
        fc.append(f"[{last}][{k}:v]xfade=transition=fade:duration={XF}:offset={pl[k]['start']:.3f}[x{k}]")
        last = f"x{k}"
    fc.append(f"[{last}]fade=t=in:st=0:d=1.2,fade=t=out:st={total - 2.5:.2f}:d=2.5,format=yuv420p[v]")
    # voice: each line at its shot's start + offset
    nvid = len(segs)
    vo_labels = []
    for p in pl:
        inp += ["-i", str(d / "vo" / f"l{p['i']:02d}.wav")]
        ms = int((p["start"] + p["off"]) * 1000)
        fc.append(f"[{nvid + p['i']}:a]aresample=48000,adelay={ms}|{ms},apad[a{p['i']}]")
        vo_labels.append(f"[a{p['i']}]")
    fc.append(f"{''.join(vo_labels)}amix=inputs={len(vo_labels)}:normalize=0:duration=longest,"
              f"atrim=0:{total:.3f},asplit=2[voice][key]")
    if music.exists():
        inp += ["-stream_loop", "-1", "-i", str(music)]
        mi = nvid + len(pl)
        fc.append(f"[{mi}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total:.3f},lowpass=f=5500,volume=-6dB,"
                  f"afade=t=in:st=0:d=2,afade=t=out:st={total - 4:.2f}:d=4[mus]")
        fc.append("[mus][key]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=600[duck]")
        fc.append("[voice]pan=stereo|c0=c0|c1=c0[vs];[vs][duck]amix=inputs=2:normalize=0,"
                  "loudnorm=I=-16:TP=-1.5:LRA=9,aresample=48000,alimiter=limit=0.84:level=false[aout]")
    else:
        fc.append("[key]anullsink;[voice]pan=stereo|c0=c0|c1=c0,loudnorm=I=-16:TP=-1.5:LRA=9,aresample=48000,alimiter=limit=0.84:level=false[aout]")
    run(["ffmpeg", "-v", "error", "-y", *inp, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[aout]",
         *enc, "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{total:.3f}", "-movflags", "+faststart",
         str(out)])
    print(f"wrote {out} ({dur(out):.1f} s)")


# ---------------------------------------------------------------- record


def cmd_record(a):
    d = Path(a.dir)
    ep = ep_load(d)
    h = history()
    h.append({"seed": ep["seed"], "theme": ep["theme"], "frame": ep["frame"], "look": ep["look"],
              "voice": ep["voice"], "music": ep["music"], "title": ep["title"], "video": str(Path(a.video).resolve()),
              "date": date.today().isoformat()})
    HIST.parent.mkdir(parents=True, exist_ok=True)
    HIST.write_text(json.dumps(h, ensure_ascii=False, indent=1) + "\n")
    print(f"recorded {ep['seed']} ({len(h)} in {HIST})")


# ---------------------------------------------------------------- deliver

HEADS = {"youtube": "YouTube", "tiktok": "TikTok", "facebook": "Facebook", "instagram": "Instagram",
         "x": "X", "threads": "Threads"}


def desktop_slot(dest, slug, day, hhmm):
    """Desktop folder of this episode: "Chinese NN · Fri 27-11 18h30 · <slug>". The posting day is episode.json's
    date; the folder of the same slug is reused, a different episode on that day is an error (one post a day),
    else NN = the next free number."""
    rows = []
    for p in dest.glob("Chinese [0-9]* · *"):
        m = re.match(r"Chinese (\d+) · (\w+ \d\d-\d\d) (\d\dh\d\d) · (.+)$", p.name)
        if m:
            rows.append((int(m.group(1)), m.group(2), p, m.group(4)))
    stamp = f"{day:%a %d-%m}"
    for _n, _st, p, sl in rows:
        if sl == slug:
            return p
    for _n, st, p, _sl in rows:
        if st == stamp:
            sys.exit(f"deliver: {stamp} is taken by {p.name}: change this episode's date in episode.json "
                     "(one post a day) and compose again")
    return dest / f"Chinese {max([n for n, *_ in rows], default=0) + 1:02d} · {stamp} {hhmm} · {slug}"


def cmd_deliver(a):
    """The finished episode, with no ask: thumbnails, then the Desktop folder of its posting day (mp4, both
    thumbnails, captions.txt, .museai-post), work folder to the Trash, the render queue's folders of this episode
    deleted, history recorded."""
    d = Path(a.dir).resolve()
    ep = ep_load(d)
    slug = ep["slug"]
    video = d / f"{slug}.mp4"
    if not video.is_file() or dur(video) < 30:
        sys.exit(f"deliver: {video} missing or unreadable: compose it first")
    cj = d / "captions.json"
    if not cj.is_file():
        sys.exit(f"deliver: write {cj} first (social-captions skill: one caption per platform)")
    caps = json.loads(cj.read_text())
    day = date.fromisoformat(ep["date"])
    hhmm = a.time.replace(":", "h")
    folder = desktop_slot(Path(os.environ.get("DEST", Path.home() / "Desktop")), slug, day, hhmm)
    thumbs = d / "thumbs"
    if not (list(thumbs.glob("*_9x16.jpg")) and list(thumbs.glob("*_16x9.jpg"))):
        stills = sorted((d / "stills").glob("s*.png"))
        tool = SKILL.parent / "thumbnail" / "scripts" / "thumb.py"
        run(["uv", "run", "--no-project", "--python", "3.12", "--with", "mediapipe==0.10.14", "--with",
             "opencv-python-headless==4.10.0.84", "--with", "pillow==11.0.0", "--with", "fonttools", "python",
             str(tool), "podcast", str(thumbs), *map(str, stills), "--name", slug, "--wide",
             "--title", ep["title_vi"], "--zh", ep["title"], "--badge", "TRUYỆN TIẾNG TRUNG"])
    folder.mkdir(parents=True, exist_ok=True)
    when = f"{day:%a %d-%m} {a.time.replace('h', ':')}"
    (folder / "captions.txt").write_text("\n\n".join(
        f"=== {HEADS[k]}{'  ' + when if k not in ('x', 'threads') else ''} ===\n{caps[k]}"
        for k in HEADS if k in caps) + "\n")
    cmd_record(argparse.Namespace(dir=str(d), video=str(video)))
    env = {**os.environ, "FINAL": "1", "CAPTIONS_FILE": str(cj), "THUMB_DIR": str(thumbs), "DEST": str(folder)}
    run(["bash", str(SKILL.parent / "muse-video/scripts/deliver.sh"), str(video), str(d), slug], env=env)
    sys.path.insert(0, str(SKILL.parent / "muse-video" / "scripts"))
    import remote

    try:
        print(f"render queue: {remote.sweep(f'{slug}-compose')} folder(s) of {slug} deleted")
    except SystemExit as e:
        print(f"render queue not swept: {e}")
    print(f"DELIVERED {folder}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("bank")
    p = sp.add_parser("next")
    p.add_argument("--n", type=int, default=3)
    p.add_argument("--seed")
    p = sp.add_parser("new")
    p.add_argument("dir")
    p.add_argument("--seed")
    p.add_argument("--date", help="episode date (default tomorrow: episodes go out the next day)")
    p = sp.add_parser("voice")
    p.add_argument("dir")
    p.add_argument("--fresh", action="store_true")
    sp.add_parser("captions").add_argument("dir")
    p = sp.add_parser("stills")
    p.add_argument("dir")
    p.add_argument("-j", type=int, default=3)
    p.add_argument("--only", type=int, nargs="*", help="re-render these line numbers")
    p = sp.add_parser("clips")
    p.add_argument("dir")
    p.add_argument("-j", type=int, default=3)
    p.add_argument("--only", type=int, nargs="*", help="re-render these line numbers")
    p = sp.add_parser("music")
    p.add_argument("dir")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--tries", type=int, default=6, help="seeds to try before giving up on a calm take")
    p = sp.add_parser("compose")
    p.add_argument("dir")
    p.add_argument("--out")
    p.add_argument("--music")
    p = sp.add_parser("record")
    p.add_argument("dir")
    p.add_argument("--video", required=True)
    p = sp.add_parser("deliver")
    p.add_argument("dir")
    p.add_argument("--time", default="18h30", help="posting time in the folder name (default 18h30)")
    a = ap.parse_args()
    globals()[f"cmd_{a.cmd}"](a)


if __name__ == "__main__":
    main()
