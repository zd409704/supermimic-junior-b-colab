#!/usr/bin/env bash
# P4 B0 compare-video: headless rollout MP4s for attention / mlp_matched / mlp_upstream (s0).
# Venue: xn-4090-gpu2. Does not reopen scoring. Does not start P5.
set -euo pipefail
export TZ=America/Toronto LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
export MUJOCO_GL="${MUJOCO_GL:-egl}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export HF_HUB_ENABLE_HF_TRANSFER=0
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

STAMP=$(date -u +%Y%m%d-%H%M)
OUT=/content/b0-compare-videos
TGZ=/content/b0-compare-videos-${STAMP}.tgz
PY=/content/SuperMimic-Reproduced/.venv/bin/python
LOG=/content/b0-compare-videos-run-${STAMP}.log
mkdir -p "$OUT"
exec > >(tee -a "$LOG") 2>&1

echo "COMPARE_VIDEO_START utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES MUJOCO_GL=$MUJOCO_GL"

# Ensure imageio + ffmpeg plugin in the SuperMimic venv
"$PY" -c "import imageio, imageio_ffmpeg" 2>/dev/null || \
  "$PY" -m pip install -q imageio imageio-ffmpeg

# Place / refresh render script (uploaded beside run.sh)
SCRIPT_SRC="${COMPARE_SCRIPT:-$PWD/render_compare_b0.py}"
if [[ ! -f "$SCRIPT_SRC" ]]; then
  echo "FATAL missing render script: $SCRIPT_SRC" >&2
  exit 2
fi
mkdir -p /content/junior/packets/P4
cp -f "$SCRIPT_SRC" /content/junior/packets/P4/render_compare_b0.py
cp -f "$SCRIPT_SRC" /content/render_compare_b0.py

# Junior code must exist (from P4 CR-B0-1 unpack)
if [[ ! -f /content/junior/code/train_entry.py ]]; then
  echo "FATAL missing /content/junior/code/train_entry.py" >&2
  exit 3
fi
if [[ ! -f /content/SuperMimic-Reproduced/logs/b0_attention_s0/ckpt_0001600.pt ]]; then
  echo "FATAL missing attention s0 ckpt" >&2
  exit 4
fi

cd /content/SuperMimic-Reproduced
export PYTHONPATH="/content/junior/code:${PYTHONPATH:-}"

"$PY" /content/render_compare_b0.py \
  --junior-code /content/junior/code \
  --config /content/junior/configs/b0_microbench.yaml \
  --logs-root /content/SuperMimic-Reproduced/logs \
  --npz-dir /content/SuperMimic-Reproduced/data/npz/lafan1_smoke \
  --out-dir "$OUT" \
  --device cuda:0 \
  --max-steps "${MAX_STEPS:-3600}" \
  --arms attention mlp_matched mlp_upstream \
  --clips walk1_subject1 dance1_subject1 \
  --seed-tag s0

# Pack deposit
tar -C /content -czf "$TGZ" "$(basename "$OUT")" "$(basename "$LOG")"
sha256sum "$TGZ" | tee "$OUT/deposit.sha256"
ls -la "$OUT"/*.mp4 "$TGZ"
echo "COMPARE_VIDEO_DONE utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) tgz=$TGZ"
