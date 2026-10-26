"""Usage: cutedit.py plan.json out.mp4  -> joins trimmed segments of rendered clips with hard cuts.
Use it to put a cut muse would not render (to-camera intro, ending close-up) and to drop a
pause at that cut. Trimming never retimes a segment, so lip sync is kept.

plan.json:
  {"inputs": ["a.mp4", "b.mp4", "c.mp4"],
   "segments": [[input, start, end, crop or null, gain_db], ...]}
crop is an ffmpeg crop "w:h:x:y" in source pixels, 9:16, scaled back to 1080x1920 (punch-in).
Keep the speaker's chin above 57 % of the frame so captions (y57-75 %) never cover the face.
Each segment gets 20 ms audio fades; the last one fades out over 0.25 s."""
import json
import subprocess
import sys

plan = json.load(open(sys.argv[1]))
segs = plan["segments"]
fc, cat = [], ""
for i, (src, a, b, crop, gain) in enumerate(segs):
    d = b - a
    v = f"crop={crop},scale=1080:1920:flags=lanczos,setsar=1" if crop else "scale=1080:1920,setsar=1"
    out = 0.25 if i == len(segs) - 1 else 0.02
    vol = f"volume={gain}dB," if gain else ""
    fc.append(f"[{src}:v]trim={a}:{b},setpts=PTS-STARTPTS,{v}[v{i}]")
    fc.append(f"[{src}:a]atrim={a}:{b},asetpts=PTS-STARTPTS,{vol}afade=t=in:d=0.02,"
              f"afade=t=out:st={d - out:.3f}:d={out}[a{i}]")
    cat += f"[v{i}][a{i}]"
fc.append(f"{cat}concat=n={len(segs)}:v=1:a=1[v][a]")
cmd = ["ffmpeg", "-v", "error", "-y"]
for f in plan["inputs"]:
    cmd += ["-i", f]
cmd += ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]", "-r", "24", "-c:v", "libx264",
        "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", sys.argv[2]]
subprocess.run(cmd, check=True)
print("WROTE", sys.argv[2])
