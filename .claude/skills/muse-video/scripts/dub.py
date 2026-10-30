"""Usage: dub.py video.mp4 cues.json SPEAKERS out.mp4
  uv run --no-project --python 3.12 --with edge-tts --with librosa --with soundfile \\
      python scripts/dub.py video.mp4 cues.json WMWMWMWMWMWW dubbed.mp4

Replaces the dialogue with one fixed voice per person, timed to the original lips.
Every muse render picks its own voices, so a multi-clip video changes voice at each seam
(EP08: the woman went 258 -> 183 -> 229 Hz across 4 clips, the clerk 101-142 Hz, with a
different timbre and accent each time). Dubbing every line with the same voice fixes that.
  voices  cloned from the voice bank by default (voicebank.py, F5-TTS in clone_tts.py): each
          of W / M gets a natural muse voice, least recently used first, kept per output path so
          a re-dub keeps it. The edge-tts pair on every episode sounded like AI and like the same
          two people every day (user, 2026-10-29). VOICE_W / VOICE_M take a bank id (W-mid-01) or a
          glob (M-low-*), never an edge-tts name: EP46 dubbed the man with zh-CN-YunxiNeural and the
          user heard an AI voice, not a normal human one (2026-10-30). One exception: when no bank
          woman's voice sounds beautiful and natural, VOICE_W=zh-CN-XiaoxiaoNeural, the woman's voice
          of every episode before the bank (user, 2026-10-30).
          SPEAKERS has one letter per cue; any other letter X needs VOICE_X, an edge-tts name or a
          bank id (e.g. VOICE_N=en-US-AvaNeural).
  timing  each cue's speech span comes from the original audio (loud frames inside the cue).
          A line whose commas match the original's pauses (> 0.15 s) is synthesised per
          comma part and each part is placed on its own span; otherwise the whole line
          is placed on the whole span. Each part starts on the lips and plays at the voice's
          own speed; it may run on into the silence after, up to the next part or speaker.
          Only when it would not fit there does the voice speak faster itself (edge-tts rate,
          up to MAX_PCT, default +20 %). Never time-stretched or slowed: EP08 v4/v5 used
          +40 % and a phase-vocoder stretch, and the user heard a pitched, unnatural voice.
          Cloned voices speak at SPEED (default 0.8) of the reference's pace: at 1.0 F5 copied
          muse's hurried delivery (EP46: 5.4-7.4 syl/s, the user heard an unnatural speed); 0.8
          gave 4.4-5.1 syl/s. OVERRUN marks a part that still runs into the next one. MAX_PCT can be lowered, never
          raised above 20. The voice is never pitch-shifted, slowed or time-stretched (no
          librosa time_stretch / pitch_shift here): EP08 v4-v5 used them and sounded pitched.
  music   muse's music bed is kept: demucs (htdemucs, run in its own uv env on Python 3.11)
          splits the original audio, the voices are dropped and the music stem goes under the
          new voice at MUSIC_DB (default -11 dB), ducked further while anyone speaks. Replacing
          the whole track dropped the music the brief asks for (EP12). MUSIC=0 skips it.
  out     dubbed.mp4 and dubbed.cues.json: the cues retimed to the new voice. Burn captions
          and run qa.py / speakers.py with them; the old cues end with the lips, so captions
          vanish early and qa reads the voice as too fast (EP08: 5.6-5.7 syl/s on the lips'
          spans for lines the voice says at a normal pace)."""
import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile

import edge_tts
import librosa
import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voicebank  # noqa: E402

video, cues_path, who, out = sys.argv[1], sys.argv[2], sys.argv[3].upper(), sys.argv[4]
cues = json.load(open(cues_path))
if len(who) != len(cues):
    sys.exit(f"SPEAKERS has {len(who)} letters for {len(cues)} cues")
asked = {w: os.environ[f"VOICE_{w}"] for w in set(who) if os.environ.get(f"VOICE_{w}")}
FALLBACK_W = "zh-CN-XiaoxiaoNeural"  # the woman's voice of every episode before the bank; the user's fallback
if ai := sorted(w for w, v in asked.items() if w in "WM" and "Neural" in v and (w, v) != ("W", FALLBACK_W)):
    sys.exit(f"VOICE_{ai[0]}={asked[ai[0]]}: W and M are cloned bank voices (only VOICE_W={FALLBACK_W} as fallback), "
             "never another edge-tts voice (AI-sounding, user 2026-10-30)")
voices = {w: v for w, v in asked.items() if "Neural" in v}
# any other speaker letter X takes its voice from VOICE_X (American Everyday Stories: one letter per character)
voices |= {w: voicebank.voice(v) for w, v in asked.items() if w not in "WM" and w not in voices}
if missing := set(who) - set(voices) - {"W", "M"}:
    sys.exit(f"no voice for speaker letter(s) {sorted(missing)}: set VOICE_<letter>")
banked = voicebank.pick(sorted(set(who) - set(voices)), out, asked)
voices |= {w: voicebank.voice(i) for w, i in banked.items()}
print("voices:", ", ".join(f"{w} {v if isinstance(v, str) else v['id']}" for w, v in sorted(voices.items())))
clone = None
if any(isinstance(v, dict) for v in voices.values()):
    clone = subprocess.Popen(["uv", "run", "-q", "--no-project", "--python", "3.11", "--with", "f5-tts",
                              "--with", "faster-whisper", "--with", "pypinyin", "python",
                              os.path.join(os.path.dirname(os.path.abspath(__file__)), "clone_tts.py")],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
SR, HOP = 24000, 120  # 5 ms frames
SPEED = float(os.environ.get("SPEED", 0.8))  # clone pace: F5 at 1.0 copies muse's hurried 5.4-7.4 syl/s (EP46)
MAX_PCT = min(20, int(os.environ.get("MAX_PCT", 20)))  # faster sounds hurried and pitched; hard cap
tmp = tempfile.mkdtemp()

subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-ac", "1", "-ar", str(SR), f"{tmp}/orig.wav"], check=True)
orig, _ = librosa.load(f"{tmp}/orig.wav", sr=SR)
db = librosa.amplitude_to_db(librosa.feature.rms(y=orig, frame_length=4 * HOP, hop_length=HOP)[0], ref=np.max)


def loud_runs(a, b, gap=0.15):
    """Speech runs inside [a, b] of the original, split at silences longer than gap."""
    i0, i1 = max(0, int(a * SR / HOP)), int(b * SR / HOP)
    on = db[i0:i1] > -35
    runs, start, last, quiet = [], None, 0, 0
    for k, v in enumerate(on):
        if v:
            if start is None:
                start = k
            elif quiet * HOP / SR > gap:
                runs.append([start, last + 1])
                start = k
            last, quiet = k, 0
        elif start is not None:
            quiet += 1
    if start is not None:
        runs.append([start, last + 1])
    return [((i0 + s) * HOP / SR, (i0 + e) * HOP / SR) for s, e in runs]


async def say(text, voice, path, pct):
    await edge_tts.Communicate(text, voice, rate=f"{pct:+d}%").save(path)


def tts(text, voice, n, pct=0):
    if isinstance(voice, str):
        asyncio.run(say(text, voice, f"{tmp}/{n}.mp3", pct))
        path = f"{tmp}/{n}.mp3"
    else:  # cloned: speed 1.2 says the line in 1/1.2 of the time, like edge-tts rate +20 %
        path = f"{tmp}/{n}.wav"
        clone.stdin.write(json.dumps({"ref": voice["ref"], "ref_text": voice["text"], "text": text, "out": path,
                                      "speed": SPEED * (1 + pct / 100)}, ensure_ascii=False) + "\n")
        clone.stdin.flush()
        got = clone.stdout.readline()
        if not got:
            sys.exit("clone_tts.py stopped (run it by hand to see why)")
        if not json.loads(got)["ok"]:
            print(f"  CLONE MISHEARD {text}: heard {json.loads(got)['heard']} (VOICE_{voice['gender']}=<edge name>)")
    y, _ = librosa.load(path, sr=SR)
    y, _ = librosa.effects.trim(y, top_db=35)
    return y


track = np.zeros(len(orig) + SR)
voice_cues = []  # the same cues, timed to the new voice: captions and the pace check use these
for i, (c, s) in enumerate(zip(cues, who, strict=True)):
    text = c[2]
    lo = max(c[0] - 0.05, cues[i - 1][1] if i else 0)
    hi = min(c[1] + 0.05, cues[i + 1][0] if i + 1 < len(cues) else c[1] + 0.05)
    nxt = cues[i + 1][0] if i + 1 < len(cues) else len(orig) / SR
    runs = [r for r in loud_runs(lo, hi) if r[1] - r[0] > 0.06]
    if not runs:
        sys.exit(f"cue {i + 1}: no speech found in the original between {c[0]} and {c[1]}")
    parts = [p for p in re.split(r"(?<=[，,、])", text) if p.strip()]
    if len(parts) == len(runs) > 1:
        spans = runs
    else:
        parts, spans = [text], [(runs[0][0], runs[-1][1])]
    for k, (p, (a, b)) in enumerate(zip(parts, spans, strict=True)):
        # room: up to the next part, or the next speaker; never slowed, never time-stretched
        room = (spans[k + 1][0] - 0.05 if k + 1 < len(spans) else nxt - 0.12) - a
        y = tts(p, voices[s], f"{i}_{k}")
        pct = int(np.clip(np.ceil((len(y) / SR / room - 1) * 100), 0, MAX_PCT))
        if pct >= 3:
            y = tts(p, voices[s], f"{i}_{k}", pct)
        dur = len(y) / SR
        flag = "  OVERRUN" if dur > room else ""
        print(f"{i + 1:2d}.{k} {s} lips {a:6.2f}-{b:6.2f} voice {dur:4.2f}s ({dur / (b - a):4.2f}x) tts {pct:+3d}%  {p}{flag}")
        y = y / (np.sqrt(np.mean(y**2)) + 1e-9) * 0.08  # same loudness for every line
        fade = np.minimum(1, np.minimum(np.arange(len(y)), np.arange(len(y))[::-1]) / (0.01 * SR))
        o = int(a * SR)
        track[o : o + len(y)] += y * fade
        end = a + len(y) / SR
    voice_cues.append([round(spans[0][0], 2), round(end, 2), *c[2:]])
if clone:
    clone.stdin.close()
track = track[: len(orig)] / max(1.0, np.abs(track).max() / 0.85)
sf.write(f"{tmp}/dub.wav", track, SR)
if os.environ.get("MUSIC", "1") == "0":
    audio = ["-i", f"{tmp}/dub.wav", "-map", "0:v", "-map", "1:a"]
else:
    # EP12: music stem at -11 dB plus the duck kept every line clear (pron + voice checks passed)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vn", "-ac", "2", "-ar", "44100", f"{tmp}/mix.wav"],
                   check=True)
    subprocess.run(["uv", "run", "-q", "--no-project", "--python", "3.11", "--with", "demucs", "--with", "soundfile",
                    "python", "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs", "-o", tmp, f"{tmp}/mix.wav"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    db_ = float(os.environ.get("MUSIC_DB", -11))
    audio = ["-i", f"{tmp}/dub.wav", "-i", f"{tmp}/htdemucs/mix/no_vocals.wav", "-filter_complex",
             f"[1:a]aformat=channel_layouts=stereo,asplit=2[d][k];[2:a]volume={db_}dB,aformat=channel_layouts=stereo[m];"
             "[m][k]sidechaincompress=threshold=0.02:ratio=4:attack=20:release=300[md];"
             "[d][md]amix=inputs=2:normalize=0,alimiter=limit=0.9[a]",
             "-map", "0:v", "-map", "[a]"]
    print(f"music: muse's music bed kept at {db_:+.0f} dB, ducked under the voice")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, *audio,
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out], check=True)
json.dump(voice_cues, open(out.rsplit(".", 1)[0] + ".cues.json", "w"), ensure_ascii=False, indent=1)
print(f"dubbed: {out}  cues timed to the voice: {out.rsplit('.', 1)[0]}.cues.json (caption and QA with these)")
