#!/usr/bin/env bash
# P6 B1 arms compare-video (visual artifact only): H-A-scratch / H-A-xfer / H-M-xfer (+ H-M-scratch if present), s0 it 1600,
# walk1_subject1 + dance1_subject1, mask 0. Venue xn-4090-gpu2, GPU0, mutex gpu0.
# Authority: orch/owner-decisions/20261027-1834-AsiaShanghai-B1-arms-compare-video-START.md (90f6dd00...).
# Does not reopen B1 scoring or M1, no attempt 2, no seeds, no retrain, no PLAN edit. Reads the attempt-1 tree
# /content/SuperMimic-Reproduced-b1 read-only (ckpts, .venv, data/npz/b1_home); writes only under
# /content/p6_b1arms_compare, /content/b1-arms-compare-videos and /content/b1-arms-compare-videos-*.{tgz,log}.
# If a required ckpt is missing or its size differs from the sealed harness-stop size, the render does not run:
# a BLOCKED tgz (preflight.json + log) is still packed for the deposit and the script exits 4.
set -euo pipefail
export TZ=America/Toronto LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
export MUJOCO_GL="${MUJOCO_GL:-egl}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export PATH="${HOME}/.local/bin:/data/muchuan/.local/bin:${PATH}"
export SM_BODY_MODULE=sm_body_home

SCRIPT_SHA=51df5575bb6f0644faf0a46748efd0174163ba160acf22352d8c85f6061742c7
TGZ_SHA=0f18b8bbca7f7ef13fffb0bcf51b2370e997580a5b5f8f6ed2cffc4dd1eb8d87   # sealed junior_b_colab-P6-B1ARMS.tgz
U=/content/SuperMimic-Reproduced-b1
W=/content/p6_b1arms_compare
STAMP=$(date -u +%Y%m%d-%H%M)
OUT=/content/b1-arms-compare-videos
LOG=/content/b1-arms-compare-videos-run-${STAMP}.log
JOB_DIR=$PWD
mkdir -p "$W" "$OUT"
exec > >(tee -a "$LOG") 2>&1

pack() {  # $1 = DONE | BLOCKED
  local suf=""; [ "$1" = BLOCKED ] && suf="-BLOCKED"
  local tgz=/content/b1-arms-compare-videos-${STAMP}${suf}.tgz
  cp -f "$JOB_DIR/run.sh" "$OUT/run.sh.txt" 2>/dev/null || true
  for j in "$JOB_DIR"/*.json; do [ -f "$j" ] && cp -f "$j" "$OUT/"; done
  tar -C /content -czf "$tgz" "$(basename "$OUT")" "$(basename "$LOG")"
  sha256sum "$tgz"
  echo "COMPARE_VIDEO_$1 utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) tgz=$tgz"
}

echo "COMPARE_VIDEO_START utc=$(date -u +%Y-%m-%dT%H:%M:%SZ) host=$(hostname) CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES MUJOCO_GL=$MUJOCO_GL"
nvidia-smi -i "$CUDA_VISIBLE_DEVICES" --query-gpu=index,uuid,name,memory.used --format=csv || true

# 1. uploaded render script (sha-checked)
echo "$SCRIPT_SHA  $JOB_DIR/render_compare_b1_arms.py" | sha256sum -c -
cp -f "$JOB_DIR/render_compare_b1_arms.py" "$W/render_compare_b1_arms.py"

# 2. junior tree: fresh unpack of the sealed B1ARMS tarball (upload first, else the attempt-1 host copy), sha-checked
SRC_TGZ=""
for c in "$JOB_DIR/junior_b_colab-P6-B1ARMS.tgz" /content/p6_b1arms/junior_b_colab-P6-B1ARMS.tgz; do
  if [ -f "$c" ] && [ "$(sha256sum "$c" | cut -c1-64)" = "$TGZ_SHA" ]; then SRC_TGZ=$c; break; fi
done
if [ -z "$SRC_TGZ" ]; then echo "BLOCKED_REASON=tarball no copy with sha $TGZ_SHA"; pack BLOCKED; exit 3; fi
echo "junior tarball: $SRC_TGZ"
rm -rf "$W/junior" && mkdir -p "$W/junior" && tar -xzf "$SRC_TGZ" -C "$W/junior"
(cd "$W/junior" && sha256sum -c --quiet packets/P6/MANIFEST-b1arms.sha256)

# 3. attempt-1 venv (read-only use)
PY=$U/.venv/bin/python
if [ ! -x "$PY" ]; then echo "BLOCKED_REASON=venv missing $PY"; pack BLOCKED; exit 3; fi
env -u PYTHONPATH "$PY" -c "import torch,mujoco; print('cuda', torch.cuda.is_available(), torch.__version__, 'mujoco', mujoco.__version__)"

# 4. ffmpeg: system binary, else imageio-ffmpeg (--no-deps) into a side dir; the attempt-1 venv is not modified
FF=$(command -v ffmpeg || true)
if [ -z "$FF" ]; then
  if command -v uv >/dev/null 2>&1; then uv pip install -q --target "$W/pydeps" --no-deps imageio-ffmpeg
  else pip3 install -q --target "$W/pydeps" --no-deps imageio-ffmpeg; fi
  FF=$(PYTHONPATH="$W/pydeps" "$PY" -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
fi
echo "ffmpeg: $FF"; "$FF" -hide_banner -version | head -1

# 5. preflight: required ckpts present with the sealed harness-stop size, sidecar policy, npz present
cd "$U"
set +e
env -u PYTHONPATH "$PY" "$W/render_compare_b1_arms.py" --junior "$W/junior" --upstream "$U" --out-dir "$OUT" --check-only
rc=$?
set -e
if [ "$rc" -ne 0 ]; then echo "BLOCKED_REASON=preflight exit $rc (see preflight.json; no retrain)"; pack BLOCKED; exit 4; fi

# 6. render
env -u PYTHONPATH "$PY" "$W/render_compare_b1_arms.py" \
  --junior "$W/junior" \
  --upstream "$U" \
  --out-dir "$OUT" \
  --device cuda:0 \
  --max-steps "${MAX_STEPS:-3600}" \
  --arms H-A-scratch H-A-xfer H-M-xfer \
  --optional-arms H-M-scratch \
  --clips walk1_subject1 dance1_subject1 \
  --seed 0 --it 0001600 \
  --ffmpeg "$FF"

ls -la "$OUT"/*.mp4
pack DONE
