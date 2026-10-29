"""Render a sung song with ACE-Step. Runs inside the ACE-Step venv (music.py calls it):
  ~/.local/share/ace-step/venv/bin/python scripts/ace_song.py --tags "..." --lyrics-file l.txt \
      --duration 40 --seed 7 --out song.wav
Weights (ACE-Step/ACE-Step-v1-3.5B, ~7.7 GB) download to ~/.cache/ace-step on first use.
"""
import argparse
from pathlib import Path

import soundfile
import torch
import torchaudio
from acestep.pipeline_ace_step import ACEStepPipeline


def _save(path, wav, sample_rate, format=None, backend=None, **_):
    # torchaudio >= 2.9 saves only through torchcodec, which the venv lacks (Iceland reel, 2026-10-28:
    # the song rendered, then the save raised ImportError). ACE-Step asks for soundfile anyway.
    soundfile.write(str(path), wav.detach().cpu().float().numpy().T, sample_rate)


torchaudio.save = _save


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", required=True)
    ap.add_argument("--lyrics-file", required=True)
    ap.add_argument("--duration", type=float, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--steps", type=int, default=100)
    ap.add_argument("--guidance", type=float, default=10.0)  # 15 gave a strained, artefacted voice
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    mps = torch.backends.mps.is_available()
    pipe = ACEStepPipeline(checkpoint_dir=str(Path.home() / ".cache/ace-step/checkpoints"),
                           dtype="float32" if mps else "bfloat16", torch_compile=False, cpu_offload=False)
    pipe(audio_duration=a.duration, prompt=a.tags, lyrics=Path(a.lyrics_file).read_text(), infer_step=a.steps,
         guidance_scale=a.guidance, scheduler_type="euler", cfg_type="apg", omega_scale=10.0, manual_seeds=str(a.seed),
         guidance_interval=0.5, guidance_interval_decay=0.0, min_guidance_scale=3.0, use_erg_tag=True,
         use_erg_lyric=True, use_erg_diffusion=True, oss_steps="", guidance_scale_text=0.0,
         guidance_scale_lyric=0.0, save_path=str(Path(a.out).resolve()), format="wav")
    # resolve(): ACE-Step makedirs(dirname(save_path)) and a bare file name gives makedirs('') -> crash
    # after the whole render (Vatnajökull reel, 2026-10-28, --out track.m4a run from the reel folder).


if __name__ == "__main__":
    main()
