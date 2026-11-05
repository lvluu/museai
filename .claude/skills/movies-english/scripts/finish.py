#!/usr/bin/env python3
"""Cut the rendered shots into the reel the way the reference reels look, then add subtitles and new words.

  uv run --no-project --python 3.12 --with faster-whisper --with 'av<14' --with pillow --with numpy --with scikit-image --with scipy python scripts/finish.py WORK OUT.mp4

WORK holds script.json (build.py) and clips/<id>-<shot>.mp4 (render.sh). Steps:
1. Per line shot, Whisper word times -> keep 0.35 s before the first word to 0.6 s after the last
   (the reaction beat the reference reels hold; a shot's "hold": N keeps N s after it, for a payoff such as
   a laugh after the punchline); a silent shot keeps 0.3 s .. 0.3 + sec. Each heard
   line is compared with the script; under 70 % word match prints MISHEARD (re-render that shot).
2. Every segment is re-encoded as rendered at 1080x1920, the reel's size (GRADE=reel default: the reel's measured
   tone and warmth, luma roll-off only, no blur or grain; raw: as rendered, colour from the prompt; match: skin histogram-matched onto the reel's face, refgrade.py; airy; or a raw
   ffmpeg chain): an earlier 540 p pass, 720 p output and grain read as blur and as specks dancing over the frame,
   exactly N frames at 24 fps
   with its audio padded/cut to the same
   length, then joined with hard cuts (concat demuxer), so lips never drift at a join.
3. Overlays (Pillow PNGs, ffmpeg overlay with enable windows), all as in references/reference-study.md:
   each spoken line as a small white English subtitle centred at ~74 %, an optional handle watermark
   (HANDLE="@page"), and, only when the script lists `words`, a 3.5 s "new words" card over a blurred
   freeze of the last frame. Nothing else: no hook, no translation line, no highlight.
Optional MUSIC=file.m4a lays a bed at MUSIC_DB (default -26 dB) under the reel.
Writes WORK/trims.json, WORK/cues.json ([start, end, en] in reel time) and OUT."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 24  # the reel's own size (the THAT WAS HIM reel plays at 1080x1920)
PX = W / 720  # overlay sizes were drawn at 720 wide
FONTS = "/System/Library/Fonts/Supplemental/"
ROUND, SERIF, ITALIC = FONTS + "Arial Rounded Bold.ttf", FONTS + "Georgia Bold.ttf", FONTS + "Georgia Italic.ttf"
VI = FONTS + "Arial Bold.ttf"  # Arial Rounded has no Vietnamese diacritics
WHITE = (255, 255, 255)
HANDLE = os.environ.get("HANDLE", "")
CARD = 3.5


# Grade (GRADE=reel default, raw, match, airy, or a raw ffmpeg chain). Measured targets: references/reference-study.md.
# reel: the THAT WAS HIM reel measured frame by frame (scripts/reel_measure.py, reference-study.md Round 3j).
#   Its singles never go brighter than L 65 at p95 (near-white 0.5 % of the frame) while muse renders reach L 80
#   (4 %): a luma-only roll-off above Y 122 (skin and everything darker untouched; an RGB curve greyed the skin,
#   a 14 -> a 21 lost), a touch of green/blue into the shadows (the reel's are brown 17/11/9, muse's red 17/8/6)
#   and less blue in the mids and highs (the reel's background honey 118/100/88, muse's grey 128/114/110).
#   Then VINTAGE. No luma blur, no grain: sharpness stays the render's.
# raw: nothing. The muse picture as rendered at the reel's own 1080x1920: the reel's skin colour is asked for in
#   the prompt (build.py SKIN, measured from the reel) and still_check gates the still, so no post-grade is
#   needed; a 540 p round trip, a 720 p output and grain read as blur and as specks dancing over the frame, so
#   those are gone for every grade.
# match: the skin of every frame histogram-matched in CIELAB onto the reel's face-only distribution
#   (refgrade.py, the source quantiles per frame, smoothed over time), the rest untouched. A fallback for clips
#   whose still slipped past the gate.
# airy: the first three IG reels (bakery 130/108/96, sat 0.34): a slight lift, a soft haze, no warmth.
# ffmpeg traps kept for raw chains: a screen blend in yuv420p lifts U/V (magenta cast), gblur on packed rgb24
# mixes the channels (blue cast): run a halation split in planar gbrp.
# Vintage, all static so nothing dances (grain and a luma blur were rejected, Rounds 3d-3h): colour softened in
# the chroma planes only (film dye bleed, the luma and the eyes stay sharp), a warm halation glow from the
# highlights (screen, planar gbrp: in yuv420p a screen blend tints magenta), a warm print tint in the highs and
# a soft vignette (Round 3k); stronger glow + dye bleed and faded film blacks (y 22-251), less blue in the
# lifted shadows to keep shGB in band (Round 3l).
HALO = "if(gt(val,140),(val-140)*2.2,0)"
VINTAGE = ("format=yuv444p,gblur=sigma=2.4:planes=6,format=gbrp,split[a][b];"
           f"[b]lutrgb=r='{HALO}':g='{HALO}':b='{HALO}',gblur=sigma=40,colorchannelmixer=rr=1:gg=0.55:bb=0.3[g];"
           "[a][g]blend=all_mode=screen:all_opacity=0.45,colorbalance=rh=0.03:gh=0.012:bh=-0.04,format=yuv444p,"
           "lutyuv=y='22+val*0.9',format=gbrp,colorbalance=bs=-0.012,"
           "vignette=angle=0.3,format=yuv420p")
REEL_Y = "if(lt(val,122),val,if(lt(val,158),122+(val-122)*0.47,if(lt(val,204),139+(val-158)*0.6,167+(val-204)*0.6)))"
PRESETS = {
    "reel": "format=yuv444p,lutyuv=y='" + REEL_Y.replace(",", "\\,") + "',format=gbrp,"
            "colorbalance=gs=0.015:bs=0.03:rm=0.01:bm=-0.015:bh=-0.03," + VINTAGE,
    "raw": "null",
    "match": "null",
    "airy": "split[a][b];[b]gblur=sigma=24[g];[a][g]blend=all_mode=screen:all_opacity=0.08,"
            "format=gbrp,curves=all='0/0.02 0.5/0.53 1/0.97',colorbalance=rm=0.025:bm=-0.03:rh=0.01:bh=-0.01,"
            "format=yuv420p,eq=saturation=1.15,gblur=sigma=0.6,noise=alls=4:allf=t",
}
GRADE_NAME = os.environ.get("GRADE", "reel")
GRADE = PRESETS.get(GRADE_NAME, GRADE_NAME)


def transfer_clip(src, dst):
    """GRADE=match: put every frame of src onto the reference (refgrade.transfer), audio copied."""
    import av
    from refgrade import source_quantiles, transfer
    tmp = dst.with_suffix(".v.mp4")
    with av.open(str(src)) as i, av.open(str(tmp), "w") as o:
        vs = i.streams.video[0]
        out = o.add_stream("libx264", rate=vs.average_rate)
        out.width, out.height, out.pix_fmt = vs.width, vs.height, "yuv420p"
        out.options = {"crf": "16", "preset": "medium"}
        q = None
        for fr in i.decode(vs):
            rgb = fr.to_ndarray(format="rgb24")
            try:
                qf = source_quantiles(rgb)
            except ValueError:  # no face in this frame: keep the last mapping
                qf = q
            q = qf if q is None else 0.5 * q + 0.5 * qf
            img = transfer(rgb, q)
            for p in out.encode(av.VideoFrame.from_image(img)):
                o.mux(p)
        for p in out.encode():
            o.mux(p)
    run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-i", str(src), "-map", "0:v", "-map", "1:a?", "-c", "copy", str(dst)])
    tmp.unlink()


def run(a, **kw):
    return subprocess.run(a, check=True, **kw)


def dur(p):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                     capture_output=True, text=True).stdout)


def words_of(s):
    return re.findall(r"[a-z]+", s.lower().replace("'", "").replace("’", ""))


def trims(work, sc):
    from faster_whisper import WhisperModel
    model = WhisperModel(os.environ.get("WMODEL", "small.en"), device="cpu", compute_type="int8")
    out, bad = {}, []
    for sh in sc["shots"]:
        clip = work / "clips" / f"{sc['id'].lower()}-{sh['id']}.mp4"
        d = dur(clip)
        if not sh.get("line"):
            a = min(0.3, max(0, d - sh["sec"]))
            out[sh["id"]] = [a, min(d, a + sh["sec"]), None, None]
            continue
        segs, _ = model.transcribe(str(clip), language="en", word_timestamps=True, vad_filter=False)
        ws = [w for s in segs for w in s.words]
        heard = " ".join(w.word.strip() for w in ws)
        want = words_of(sh["line"]["en"])
        got = words_of(heard)
        match = sum(1 for w in want if any(g == w or g.endswith(w) for g in got)) / max(1, len(want))
        if not ws or match < 0.7:
            bad.append(sh["id"])
            print(f"MISHEARD {sh['id']}: want {sh['line']['en']!r} heard {heard!r}")
        # muse sometimes says the line twice: keep only up to the word that completes it the first time
        last, i = len(ws) - 1, 0
        for j, w in enumerate(ws):
            g = words_of(w.word)
            if i < len(want) and g and (g[0] == want[i] or g[0].endswith(want[i])):
                i += 1
                if i == len(want):
                    last = j
                    break
        s = max(0.0, (ws[0].start if ws else 0.6) - 0.35)
        said = ws[last].end if ws else sh["sec"]
        e = min(d, said + sh.get("hold", 0.6))
        out[sh["id"]] = [round(s, 3), round(e, 3), round((ws[0].start if ws else 0.6) - s, 3), round(said + 0.5 - s, 3)]
        print(f"{sh['id']} {match:.0%} heard {heard!r} keep {s:.2f}-{e:.2f}")
    (work / "trims.json").write_text(json.dumps(out, indent=1))
    return out, bad


def cut(work, sc, tr):
    segs, cues, t = [], [], 0.0
    for sh in sc["shots"]:
        clip = work / "clips" / f"{sc['id'].lower()}-{sh['id']}.mp4"
        s, e, lead, said = tr[sh["id"]]
        n = max(1, round((e - s) * FPS))
        length = n / FPS
        seg = work / "seg" / f"{sh['id']}.mp4"
        seg.parent.mkdir(exist_ok=True)
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s}", "-i", str(clip), "-frames:v", str(n),
             # no soft pass: a 540 p round trip and a 720 p output read as blurry against the 1080 p reel
             "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},fps={FPS},"
                    f"setsar=1,{GRADE}",
             "-af", f"aresample=48000,apad,atrim=0:{length:.4f}", "-ar", "48000", "-ac", "2",
             "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
             str(seg)])
        if GRADE_NAME == "match":
            raw = seg.with_name(f"{sh['id']}.raw.mp4")
            seg.rename(raw)
            transfer_clip(raw, seg)
            raw.unlink()
        if sh.get("line"):
            cues.append([round(t + lead - 0.1, 3), round(t + min(said, length), 3), sh["line"]["en"]])
        segs.append(seg)
        t += length
    lst = work / "seg" / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in segs))
    film = work / "film.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(film)])
    (work / "cues.json").write_text(json.dumps(cues, ensure_ascii=False, indent=1))
    return film, cues, t


def font(p, size):
    return ImageFont.truetype(p, round(size * PX))


def wrap(text, f, maxw, d):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + [cur]


def centred(d, y, text, f, fill, stroke=2):
    d.text(((W - d.textlength(text, font=f)) / 2, y), text, font=f, fill=fill, stroke_width=round(stroke * PX),
           stroke_fill=(20, 16, 14))


def subtitle_png(en, path):
    img = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(img)
    f = font(ROUND, 26)  # memoriescore subtitles are tiny: ~2 % of the height
    rows = wrap(en, f, W * 0.8, d)
    y = int(H * 0.735) - round(16 * PX) * (len(rows) - 1)
    for r in rows:
        centred(d, y, r, f, WHITE)
        y += round(33 * PX)
    img.save(path)


def handle_png(path):
    img = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(img)
    f = font(ITALIC, 20)
    d.text((W - 40 * PX - d.textlength(HANDLE, font=f), int(H * 0.945)), HANDLE, font=f, fill=(255, 255, 255, 140))
    img.save(path)


def words_png(frame, words, path):
    base = Image.open(frame).convert("RGB").resize((W, H)).filter(ImageFilter.GaussianBlur(14 * PX))
    base = Image.blend(base, Image.new("RGB", (W, H), (14, 11, 10)), 0.5).convert("RGBA")
    d = ImageDraw.Draw(base)
    fh, fe, fv = font(ROUND, 22), font(SERIF, 40), font(VI, 25)
    blocks = [[(r, fe, WHITE, 50 * PX) for r in wrap(w["en"], fe, W * 0.84, d)]
              + [(r, fv, (232, 224, 218), 38 * PX) for r in wrap(w["vi"], fv, W * 0.84, d)] for w in words]
    y = (H - 64 * PX - sum(sum(x[3] for x in b) + 36 * PX for b in blocks)) / 2
    centred(d, y, "NEW WORDS", fh, (255, 255, 255, 200), 1)
    y += 64 * PX
    for b in blocks:
        for r, f, c, lh in b:
            centred(d, y, r, f, c, 1)
            y += lh
        y += 36 * PX
    base.save(path)


def finish(work, out):
    work = Path(work)
    sc = json.loads((work / "script.json").read_text())
    tr, bad = trims(work, sc)
    film, cues, total = cut(work, sc, tr)
    ov = work / "ov"
    ov.mkdir(exist_ok=True)
    last = ov / "last.png"
    run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.05", "-i", str(film), "-frames:v", "1", "-update", "1", str(last)])
    for i, c in enumerate(cues):
        subtitle_png(c[2], ov / f"sub{i}.png")
    # the "new words" card exists only when the script lists `words`; a story reel ends on its last frame
    if sc.get("words"):
        words_png(last, sc["words"], ov / "card.png")
        end = total + CARD
        inputs = ["-i", str(film), "-loop", "1", "-t", f"{CARD}", "-i", str(ov / "card.png")]
        fc = [f"[1:v]fps={FPS},format=yuv420p,setsar=1[card]", "[0:v][card]concat=n=2:v=1:a=0[v0]"]
        k = 2
    else:
        end = total
        inputs = ["-i", str(film)]
        fc = ["[0:v]null[v0]"]
        k = 1
    cur = "v0"
    if HANDLE:
        handle_png(ov / "handle.png")
        inputs += ["-i", str(ov / "handle.png")]
        fc.append(f"[v0][{k}:v]overlay=enable='lt(t,{total:.3f})'[vh]")
        cur, k = "vh", k + 1
    for i, (s, e, _) in enumerate(cues):
        inputs += ["-i", str(ov / f"sub{i}.png")]
        nxt = cues[i + 1][0] if i + 1 < len(cues) else total
        fc.append(f"[{cur}][{k + i}:v]overlay=enable='between(t,{max(0, s):.3f},{min(e, nxt, total):.3f})'[c{i}]")
        cur = f"c{i}"
    fc.append(f"[0:a]apad=whole_dur={end:.3f},afade=t=out:st={total:.3f}:d=1.5[a0]")
    amap = "[a0]"
    music = os.environ.get("MUSIC")
    if music:
        inputs += ["-stream_loop", "-1", "-i", music]
        fc.append(f"[{k + len(cues)}:a]atrim=0:{end:.3f},volume={os.environ.get('MUSIC_DB', '-26')}dB,"
                  f"afade=t=in:d=1,afade=t=out:st={end - 2:.3f}:d=2[m]")
        fc.append("[a0][m]amix=inputs=2:duration=first:normalize=0[a1]")
        amap = "[a1]"
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", f"[{cur}]", "-map", amap,
         "-t", f"{end:.3f}", "-r", str(FPS), "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)])
    print(f"{out}: {end:.1f} s, {len(cues)} lines" + (f", MISHEARD {bad}" if bad else ""))
    return not bad


if __name__ == "__main__":
    sys.exit(0 if finish(*sys.argv[1:3]) else 1)
