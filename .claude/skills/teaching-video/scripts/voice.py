"""Usage:
  voice.py synth lesson.json work/voice            -> phrase wavs, master.wav, timeline.json
  voice.py dub video.mp4 work/voice/timeline.json out.mp4   -> same phrases placed on the teacher's lips
Run: uv run --no-project --python 3.12 --with edge-tts --with numpy --with soundfile python scripts/voice.py ...

One voice for the whole lesson, made once and reused by both formats, so the narration is identical.
  voices   VOICE_VI (default vi-VN-HoaiMyNeural, Northern standard) for Vietnamese, VOICE_ZH (default
           zh-CN-XiaoxiaoNeural, standard Putonghua) for Mandarin. Male teacher: vi-VN-NamMinhNeural +
           zh-CN-YunjianNeural. Only zh-CN-<Name>Neural voices are accepted for Mandarin: regional ones
           (zh-CN-liaoning-*, zh-CN-shaanxi-*, zh-TW, zh-HK) are not the standard accent the lesson needs.
           muse's own voice reads Chinese inside Vietnamese as Hán-Việt or with wrong tones (muse-video
           skill, hientang 2026-10-28), so every word is dubbed.
  natural  what keeps it from sounding like TTS: whole phrases, never word-by-word; rate left near the
           voice's own, at an everyday talking pace (RATE_VI +25 %: HoaiMy at +0 % measured 3.8 syl/s and +10 % still
           sounded slow to the user, 2026-10-28; RATE_ZH_SLOW -15 % for the learner read of an example, clearly slower
           but not dragged (-30 % was heard as too slow); RATE_ZH +5 % for natural reads and a word
           inside a Vietnamese sentence), never pitch-shifted or time-stretched (muse-video EP08: the user
           heard it as pitched and fake); "!" read as "." (the voice shouts it); gaps between phrases vary
           like speech (shorter inside a sentence, longer between ideas, +-12 % jitter, never one fixed gap);
           a soft breath before a phrase that follows >= 0.4 s of silence (BREATH=0 to drop); every phrase
           through one EQ/de-ess chain and the same loudness, so the Vietnamese and Mandarin voices sit in one
           room; a quiet room tone under everything (digital silence between phrases sounds synthetic);
           a short early-reflection room and loudnorm -16 LUFS on the mix.
  dub      muse moves the teacher's lips to its own speech. Each phrase that starts a breath group (>= 0.4 s
           of silence before it in the master) starts on the nearest lip onset (speech span of the render's
           own audio) within 1.5 s of where it is expected; phrases inside a group follow the previous one
           with the master's gap, so a sentence is never torn apart to chase the lips. Repeat and challenge
           pauses keep their planned length at least. LATE marks a breath group pushed past its lip onset
           because the phrase before it was still sounding (re-render that clip, or ONSETS). ONSETS=file.json ({"id": seconds}) forces starts. The render's audio is
           dropped entirely; out.timeline.json holds the placed times (captions, cards and QA use it).
"""
import asyncio
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 48000
VOICE_VI = os.environ.get("VOICE_VI", "vi-VN-HoaiMyNeural")
VOICE_ZH = os.environ.get("VOICE_ZH", "zh-CN-XiaoxiaoNeural")
RATE_VI = os.environ.get("RATE_VI", "+25%")
RATE_ZH_SLOW = os.environ.get("RATE_ZH_SLOW", "-15%")
RATE_ZH = os.environ.get("RATE_ZH", "+5%")
BREATH = os.environ.get("BREATH", "1") != "0"
TARGETS = {"hook": 8, "explain": 30, "demo": 80, "fix": 100, "challenge": 113, "reinforce": 120}  # section ends
PHRASE_CHAIN = ("highpass=f=70,equalizer=f=180:t=q:w=1:g=1.5,equalizer=f=3000:t=q:w=1.5:g=-1.5,"
                "equalizer=f=7500:t=q:w=1:g=-2,deesser=i=0.3")
MIX_CHAIN = ("acompressor=threshold=0.1:ratio=2:attack=10:release=150,"
             "aecho=0.9:0.9:17|29|43:0.07|0.05|0.03")
LOUDNORM = "loudnorm=I=-16:TP=-1.5:LRA=20"


def loudnorm_args(src, pre=""):
    """Two-pass linear loudnorm: one gain for the whole file. Single-pass loudnorm is dynamic and lifted
    the -62 dBFS room tone in pauses to -46 dBFS (audible hiss, 2026-10-28)."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src), "-af", f"{pre}{LOUDNORM}:print_format=json",
                          "-f", "null", "-"], capture_output=True, text=True, check=True).stderr
    m = json.loads(err[err.rfind("{"):err.rfind("}") + 1])
    return (f"{pre}{LOUDNORM}:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
            f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']},"
            f"aresample={SR}")

if not re.fullmatch(r"zh-CN-[A-Z][a-z]+Neural", VOICE_ZH):
    sys.exit(f"VOICE_ZH {VOICE_ZH}: use a standard Putonghua zh-CN-<Name>Neural voice, not a regional one")


def tts_text(lang, text):
    t = text.replace("“", "").replace("”", "").replace('"', "")
    if lang == "vi":
        return t.replace("!", ".").replace(" — ", ", ")
    return t.replace("！", "。")


async def _say(text, voice, rate, path):
    import edge_tts
    # HoaiMy flakes with NoAudioReceived, and above +10 % some phrases fail at one exact rate every time
    # ("Nghe quen đúng không?" at +20 %, fine at +15 %; 2026-10-28), so after 3 tries step to a rate 1-3 % off
    r0 = int(rate.rstrip("%"))
    for r in (r0, r0 - 1, r0 + 1, r0 - 2, r0 + 2, r0 - 3, r0 + 3):
        for attempt in range(3):
            try:
                await edge_tts.Communicate(text, voice, rate=f"{r:+d}%").save(str(path))
                if path.exists() and path.stat().st_size > 1000:
                    if r != r0:
                        print(f"  note: {voice} read at {r:+d}% (edge-tts gave no audio at {rate}): {text}")
                    return
            except Exception as e:  # noqa: BLE001 - edge_tts raises several types for the same flake
                err = e
            path.unlink(missing_ok=True)
            await asyncio.sleep(1 + attempt)
    sys.exit(f"edge-tts failed at {rate} +-3 % for {voice}: {text} ({err if 'err' in dir() else 'empty audio'})")


def load(path):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.float32).copy()


def trim(y, thr_db=-50, pad=0.03):
    env = np.convolve(np.abs(y), np.ones(480) / 480, "same")
    on = np.where(env > 10 ** (thr_db / 20))[0]
    if not len(on):
        return y
    a, b = max(0, on[0] - int(pad * SR)), min(len(y), on[-1] + int(pad * SR))
    return y[a:b]


def active_rms(y):
    frames = y[: len(y) // 480 * 480].reshape(-1, 480)
    r = np.sqrt((frames ** 2).mean(1))
    r = r[r > r.max() * 0.1]
    return float(np.sqrt((r ** 2).mean())) if len(r) else 1e-6


def phrase(lang, text, slow, cache):
    voice, rate = (VOICE_VI, RATE_VI) if lang == "vi" else (VOICE_ZH, RATE_ZH_SLOW if slow else RATE_ZH)
    key = hashlib.sha1(f"{voice}|{rate}|{tts_text(lang, text)}|{PHRASE_CHAIN}".encode()).hexdigest()[:12]
    wav = cache / f"{lang}_{key}.wav"
    if not wav.exists():
        mp3 = cache / f"{lang}_{key}.mp3"
        asyncio.run(_say(tts_text(lang, text), voice, rate, mp3))
        y = trim(load(mp3))
        with tempfile.NamedTemporaryFile(suffix=".wav") as raw:
            sf.write(raw.name, y, SR)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw.name, "-af", PHRASE_CHAIN, "-ar", str(SR),
                            "-ac", "1", "-c:a", "pcm_f32le", str(wav)], check=True)
        y = load(wav)
        sf.write(wav, y * (10 ** (-20 / 20) / active_rms(y)), SR, subtype="FLOAT")  # same loudness for both voices
        mp3.unlink(missing_ok=True)
    return wav


def jitter(key, spread=0.12):
    h = int(hashlib.md5(key.encode()).hexdigest()[:6], 16) / 0xFFFFFF
    return 1 + spread * (2 * h - 1)


def gap(prev, it, new_beat, new_section):
    """Silence before item `it`, like a person: short inside a sentence, longer between ideas."""
    if prev is None:
        return 0.3
    if prev.get("repeat"):
        return prev["repeat"]
    if new_section:
        g = 0.6
    elif new_beat:
        g = 0.4
    elif prev["kind"] == "pause" or it["kind"] == "pause":
        g = 0.25
    elif it.get("inline") or prev.get("inline"):
        g = 0.12  # a Chinese word inside a Vietnamese sentence
    elif prev["text"].rstrip()[-1:] in ".?。？:：":
        g = 0.3
    else:
        g = 0.18
    return g * jitter(it["id"])


def breath(seed):
    rng = np.random.default_rng(seed)
    n = int(0.30 * SR)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec *= np.exp(-((np.log(f + 1) - math.log(1200)) ** 2) / (2 * 0.45 ** 2))  # soft band around 1.2 kHz
    y = np.fft.irfft(spec, n)
    t = np.linspace(0, 1, n)
    env = np.sin(np.pi * np.clip(t / 0.55, 0, 1) / 2) * np.clip((1 - t) / 0.45, 0, 1) ** 1.5
    y = y * env
    return y * (10 ** (-44 / 20) / (np.sqrt((y ** 2).mean()) + 1e-9))  # ~24 dB under the voice


def mix(items, total, out_wav):
    """Voice phrases + breaths + room tone -> out_wav (room + loudnorm chain)."""
    y = np.zeros(int((total + 0.5) * SR), np.float32)
    for it in items:
        if it["kind"] != "speech":
            continue
        a = int(it["start"] * SR)
        v = load(it["wav"])
        y[a:a + len(v)] += v[: len(y) - a]
        if BREATH and it.get("breath"):
            b = breath(int(it["start"] * 1000))
            s = max(0, a - len(b) - int(0.06 * SR))
            y[s:s + len(b)] += b[: len(y) - s]
    room = room_tone(len(y))
    y = y + room
    with tempfile.NamedTemporaryFile(suffix=".wav") as raw:
        sf.write(raw.name, y, SR, subtype="FLOAT")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw.name, "-af", loudnorm_args(raw.name, MIX_CHAIN + ","), "-ar", str(SR), "-ac", "1",
                        str(out_wav)], check=True)


def room_tone(n):
    """Soft brown-ish noise at -62 dBFS: a quiet room instead of digital silence between phrases."""
    spec = np.fft.rfft(np.random.default_rng(7).standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec *= 1 / np.sqrt(f + 40) * (f > 40) * np.exp(-f / 4000)
    y = np.fft.irfft(spec, n).astype(np.float32)
    return y * (10 ** (-62 / 20) / (np.sqrt((y ** 2).mean()) + 1e-12))


def synth(lesson, out):
    cache = out / "phrases"
    cache.mkdir(parents=True, exist_ok=True)
    items = []
    for bi, b in enumerate(lesson["beats"]):
        for si, x in enumerate(b["say"]):
            it = {"id": f"b{bi:02d}s{si}", "beat": bi, "section": b["section"]}
            if "pause" in x:
                it.update(kind="pause", lang=None, text="", dur=x["pause"], countdown=bool(x.get("countdown")))
            else:
                lang = "vi" if "vi" in x else "zh"
                it.update(kind="speech", lang=lang, text=x[lang], slow=bool(x.get("slow")),
                          repeat=x.get("repeat"), inline=lang == "zh" and not x.get("slow") and len(x[lang]) <= 3)
                it["wav"] = str(phrase(lang, x[lang], it["slow"], cache))
                it["dur"] = len(load(it["wav"])) / SR
            items.append(it)
    t, prev = 0.0, None
    for it in items:
        new_beat = prev is not None and prev["beat"] != it["beat"]
        g = gap(prev, it, new_beat, new_beat and prev["section"] != it["section"])
        it["start"] = round(t + g, 3)
        it["end"] = round(it["start"] + it["dur"], 3)
        it["breath"] = it["kind"] == "speech" and g >= 0.4 and not it.get("inline")
        t, prev = it["end"], it
    total = t + (prev.get("repeat") or 0) + 0.8
    mix(items, total, out / "master.wav")
    timeline = {"voice_vi": VOICE_VI, "voice_zh": VOICE_ZH, "total": round(total, 2), "items": items}
    (out / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=1))
    report(items, total)
    return timeline


def report(items, total):
    fails = []
    ends = {}
    for it in items:
        ends[it["section"]] = it["end"] + (it.get("repeat") or 0)
    print(f"{'section':10s} {'ends':>6s} {'target':>6s}")
    for s, target in TARGETS.items():
        e = ends.get(s, 0)
        flag = "" if abs(e - target) <= 6 else "  OFF (+-6 s): move a line between sections"
        if s == "hook" and e > 9.5:
            flag, _ = "  HOOK TOO LONG", fails.append("hook ends after 9.5 s")
        print(f"{s:10s} {e:6.1f} {target:6d}{flag}")
    print(f"total {total:.1f} s")
    if not 110 <= total <= 128:
        fails.append(f"total {total:.1f} s outside 110-128 s: cut or add a line (never change the rate)")
    for f in fails:
        print("FAIL ", f)
    print("RESULT", "FAIL" if fails else "ok")


def dub(video, timeline, out):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "muse-video" / "scripts"))
    from gaps import speech_spans
    items = timeline["items"]
    spans = speech_spans(str(video), float(os.environ.get("THR", -30)))
    if not spans:
        sys.exit("no speech in the render's audio: lips cannot be located")
    onsets = [a for a, _ in spans]
    forced = json.load(open(os.environ["ONSETS"])) if os.environ.get("ONSETS") else {}
    speech = [it for it in items if it["kind"] == "speech"]
    m0, m1 = speech[0]["start"], speech[-1]["end"]
    s0, s1 = spans[0][0], spans[-1][1]
    k = min(1.25, max(0.8, (s1 - s0) / (m1 - m0)))
    placed, prev, used = [], None, set()
    print(f"{'id':8s} {'lang':4s} {'master':>7s} {'placed':>7s} how")
    for it in items:
        master = it["start"]
        it = dict(it)
        exp = s0 + (it["start"] - m0) * k
        mgap = it["start"] - (prev["end"] if prev else m0 - 0.3)
        floor = (prev["end"] + max(0.1, mgap * 0.7)) if prev else 0.0
        if prev and prev.get("repeat"):
            floor = prev["end"] + prev["repeat"] * 0.9
        if prev and prev["kind"] == "pause":
            floor = max(floor, prev["end"])
        how = "chain"
        if it["id"] in forced:
            start, how = forced[it["id"]], "forced"
        elif it["kind"] == "pause":
            start = floor
        elif prev is None or mgap >= 0.4:
            cand = [o for o in onsets if o >= floor - 0.05 and abs(o - exp) <= 1.5 and o not in used]
            if cand:
                lip = min(cand, key=lambda o: abs(o - exp))
                used.add(lip)
                start, how = max(lip, floor), "lip"
                if start - lip > 0.1:
                    # the previous phrase still sounds when these lips open: the voice runs slower than muse's mouth
                    how += f"  LATE {start - lip:.2f}s after the lips open"
            else:
                start, how = max(exp, floor), "est"
        else:
            start = prev["end"] + mgap
        it["start"], it["end"] = round(start, 3), round(start + it["dur"], 3)
        print(f"{it['id']:8s} {it['lang'] or '-':4s} {master:7.2f} {it['start']:7.2f} {how}")
        placed.append(it)
        prev = it
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                               capture_output=True, text=True, check=True).stdout)
    if placed[-1]["end"] > dur - 0.2:
        print(f"WARN voice ends at {placed[-1]['end']:.1f} s, video is {dur:.1f} s: trim fewer seconds from the last clip")
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "voice.wav"
        mix(placed, max(dur, placed[-1]["end"]), wav)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(wav), "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{dur:.3f}", str(out)], check=True)
    tl = dict(timeline, items=placed, total=round(dur, 2))
    Path(out).with_suffix(".timeline.json").write_text(json.dumps(tl, ensure_ascii=False, indent=1))
    print(f"-> {out} + {Path(out).with_suffix('.timeline.json')}")


if __name__ == "__main__":
    if sys.argv[1] == "synth":
        synth(json.load(open(sys.argv[2])), Path(sys.argv[3]))
    elif sys.argv[1] == "dub":
        dub(Path(sys.argv[2]), json.load(open(sys.argv[3])), Path(sys.argv[4]))
    else:
        sys.exit(__doc__)
