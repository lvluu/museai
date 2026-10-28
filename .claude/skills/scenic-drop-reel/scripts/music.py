# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["torch", "transformers>=4.40", "librosa", "soundfile", "numpy", "scipy"]
# ///
"""Generate an AI music track shaped like the reference reel's: filtered riser under the countdown,
beat drop at --intro, steady 100 BPM body for --shots cuts of 2 beats.

Usage:
  uv run --no-project scripts/music.py "uplifting summer tropical house, bright plucks, warm bass" \
      --out assets/music-<slug>.m4a [--seed 7] [--model facebook/musicgen-medium]

Steps: MusicGen renders ~20 s from the style + "100 bpm" → librosa finds its tempo and beats →
time-stretched to exactly 100 BPM → body = the loudest, cleanest beat-aligned stretch, starting
on a beat → intro = the 3.233 s before it, low-passed with a 300→7000 Hz sweep, quieter, plus a
rising white-noise whoosh that stops dead on the drop → body fades over its last 0.3 s → tanh drive to the reference's loudness.
The MusicGen weights are CC-BY-NC 4.0: fine for personal reels, not for paid/commercial posts.
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
import torch
from transformers import AutoProcessor, MusicgenForConditionalGeneration

BPM = 100.0


def generate(style, seconds, model_id, seed):
    proc = AutoProcessor.from_pretrained(model_id)
    model = MusicgenForConditionalGeneration.from_pretrained(model_id)
    text = [f"{style}, {BPM:.0f} bpm, steady four-on-the-floor beat, instrumental, no vocals"]
    for dev in (["mps"] if torch.backends.mps.is_available() else []) + ["cpu"]:
        torch.manual_seed(seed)
        try:
            inputs = proc(text=text, padding=True, return_tensors="pt").to(dev)
            out = model.to(dev).generate(**inputs, do_sample=True, guidance_scale=3.0,
                                         max_new_tokens=int(seconds * 50))
            return out[0, 0].float().cpu().numpy(), model.config.audio_encoder.sampling_rate
        except (RuntimeError, NotImplementedError) as e:  # MPS lacks some ops on older torch
            if dev == "cpu":
                raise
            print(f"{dev} failed ({e}); retrying on cpu", file=sys.stderr)


def sweep_lowpass(y, sr, f0, f1, n_fft=2048, hop=256):
    """Low-pass whose cutoff rises exponentially from f0 to f1 over the clip (STFT mask)."""
    S = librosa.stft(y, n_fft=n_fft, hop_length=hop)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)[:, None]
    cut = f0 * (f1 / f0) ** np.linspace(0, 1, S.shape[1])[None, :]
    mask = 1 / (1 + (freqs / cut) ** 8)
    return librosa.istft(S * mask, hop_length=hop, length=len(y))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("style", help="genre/instruments/mood, e.g. 'uplifting tropical house, marimba, warm bass'")
    ap.add_argument("--out", required=True)
    ap.add_argument("--intro", type=float, default=3.233)
    ap.add_argument("--shots", type=int, default=7)
    ap.add_argument("--shot", type=float, default=1.2)
    ap.add_argument("--seconds", type=float, default=22)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--model", default="facebook/musicgen-medium")
    ap.add_argument("--raw", help="reuse an already generated wav instead of running MusicGen")
    a = ap.parse_args()

    if a.raw:
        y, sr = librosa.load(a.raw, sr=None, mono=True)
    else:
        y, sr = generate(a.style, a.seconds, a.model, a.seed)
        sf.write(Path(a.out).with_suffix(".raw.wav"), y, sr)

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.atleast_1d(tempo)[0])
    tempo = min((tempo * m for m in (0.5, 1, 2)), key=lambda t: abs(t - BPM))  # half/double-time guesses
    y = librosa.effects.time_stretch(y, rate=BPM / tempo)
    _, beats = librosa.beat.beat_track(y=y, sr=sr, start_bpm=BPM, tightness=400, units="samples")

    body_len = int((a.shots * a.shot + 0.3) * sr)
    intro_len = int(a.intro * sr)
    hop = 512
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    flat = librosa.feature.spectral_flatness(y=y, hop_length=hop)[0]
    valid = [b for b in beats if b >= max(intro_len, 2 * sr) and b + body_len <= len(y)]
    if not valid:
        sys.exit(f"generated track too short for intro {a.intro}s + body; raise --seconds")

    def body_score(b):  # loud, even groove; MusicGen's noisy swells (high flatness) read as hiss on a phone
        i, j = b // hop, (b + body_len) // hop
        k = i + sr // hop  # the first second after the drop must be clean groove, not the tail of a swell
        return rms[i:j].mean() - 0.5 * rms[i:j].std() - flat[i:j].mean() - flat[i:k].mean()

    b0 = max(valid, key=body_score)

    body = y[b0:b0 + body_len].copy()
    fade = int(0.3 * sr)
    body[-fade:] *= np.linspace(1, 0, fade)

    intro = sweep_lowpass(y[b0 - intro_len:b0], sr, 300, 7000)
    t = np.linspace(0, 1, intro_len)
    intro *= 10 ** ((-14 + 10 * t) / 20)  # -14 dB → -4 dB swell
    noise = np.random.default_rng(a.seed).standard_normal(intro_len)
    noise = sweep_lowpass(noise, sr, 500, 12000) * 0.08 * t ** 3  # whoosh up to the drop
    intro = intro + noise
    intro[-int(0.02 * sr):] *= np.linspace(1, 0.2, int(0.02 * sr))  # tiny gap so the drop hits

    track = np.concatenate([intro, body])
    track = np.tanh(3 * track / np.abs(track).max()) / np.tanh(3)  # drive: phone-loud like the reference (-13 dB mean)
    track *= 10 ** (-1 / 20)

    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "t.wav"
        sf.write(wav, track, sr)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-ar", "44100", "-ac", "2",
                        "-c:a", "aac", "-b:a", "192k", a.out], check=True)
    print(f"{a.out}: body from {b0 / sr:.2f}s of the raw track, tempo {tempo:.1f}→{BPM:.0f} BPM, drop {a.intro}s, length {len(track) / sr:.2f}s")


if __name__ == "__main__":
    main()
