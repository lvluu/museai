#!/usr/bin/env bash
# Usage: still.sh lesson.json out_dir            -> out_dir/still_1.png, still_2.png (16:9 candidates)
#        still.sh lesson.json out_dir pick.png   -> out_dir/first_16x9.png + first_9x16.png
# One teacher for both formats: muse invents a new face per render, so both chains start from the
# same still. Step 1 generates two 16:9 stills (teacher in the left third, empty right side); pick
# the one that looks most real (hands, eyes, no text on the wall). Step 2 makes the first frames:
# the 16:9 still scaled to 1920x1080, and a 9:16 crop around the teacher upscaled with Real-ESRGAN
# to 1080x1920 (a 608 px-wide crop stretched to 1080 renders soft: muse-video "Sharp first frame").
# Only this reference still is cropped; each format is still rendered as its own composition.
# Env: MUSEAI_HOME=~/Work/museai MUSEAI_BASE=http://127.0.0.1:18610 ESRGAN_DIR=~/Work/tools/realesrgan
#      FACE_X=0.25 (teacher's face centre as a fraction of the still's width)
set -euo pipefail
lesson=$1 out=$2 pick=${3:-}
mkdir -p "$out"
if [ -z "$pick" ]; then
  home=${MUSEAI_HOME:-$HOME/Work/museai}
  KEY=$(cat "$home/data/api_key")
  prompt=$(python3 - "$lesson" <<'EOF'
import json, sys
t = json.load(open(sys.argv[1]))["teacher"]
print(f"Photo, real camera, 16:9. {t['cast']} She stands in the LEFT third of the frame, face about 25 % "
      f"from the left edge, framed from the waist up, facing the lens with a warm closed-mouth smile, hands "
      f"resting loosely together at waist height. {t['set']} The right 55 % of the frame is a calm, softly "
      f"blurred bright wall with nothing on it. No text, letters, logos or signs anywhere.")
EOF
)
  body=$(python3 -c 'import json,sys; print(json.dumps({"prompt": sys.argv[1], "n": 2, "size": "1920x1080", "response_format": "b64_json"}))' "$prompt")
  curl -sf -X POST "${MUSEAI_BASE:-http://127.0.0.1:18610}/v1/images/generations" \
    -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d "$body" > "$out/still.json"
  python3 - "$out" <<'EOF'
import base64, json, sys
d = json.load(open(f"{sys.argv[1]}/still.json"))["data"]
for i, x in enumerate(d, 1):
    open(f"{sys.argv[1]}/still_{i}.png", "wb").write(base64.b64decode(x["b64_json"]))
    print(f"{sys.argv[1]}/still_{i}.png")
EOF
  rm "$out/still.json"
  exit 0
fi
ffmpeg -v error -y -i "$pick" -vf "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080" "$out/first_16x9.png"
# 9:16 window of the full still height around the face
read -r w h < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x "$pick" | tr x ' ')
cw=$(( h * 9 / 16 / 2 * 2 ))
cx=$(python3 -c "print(max(0, min($w - $cw, int($w * ${FACE_X:-0.25} - $cw / 2))))")
ffmpeg -v error -y -i "$pick" -vf "crop=$cw:$h:$cx:0" "$out/crop_9x16.png"
esr=${ESRGAN_DIR:-$HOME/Work/tools/realesrgan}
if [ -x "$esr/realesrgan-ncnn-vulkan" ]; then
  "$esr/realesrgan-ncnn-vulkan" -i "$out/crop_9x16.png" -o "$out/crop_x4.png" -n realesrgan-x4plus -m "$esr/models" >/dev/null 2>&1
  src=$out/crop_x4.png
else
  echo "WARN Real-ESRGAN not found in $esr: plain lanczos scale (softer first frame)"
  src=$out/crop_9x16.png
fi
ffmpeg -v error -y -i "$src" -vf "scale=1080:1920:flags=lanczos" "$out/first_9x16.png"
rm -f "$out/crop_9x16.png" "$out/crop_x4.png"
echo "$out/first_16x9.png $out/first_9x16.png (crop ${cw}x$h at x=$cx of ${w}x$h)"
