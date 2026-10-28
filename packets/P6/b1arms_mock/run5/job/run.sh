#!/usr/bin/env bash
# P6d B1 arms venue bootstrap for xn-4090-gpu2 (spikes/B1/PLAN.md §3-§8; GPU0, mutex gpu0, spend cap 9.0 GPU-h in the driver).
# plan=1088752ba26a8798d721aa93d6e10d1b7bdb7fb924d9d72879acc78d8c2304c8
# tarball(junior_b_colab-P6-B1ARMS.tgz)=0f18b8bbca7f7ef13fffb0bcf51b2370e997580a5b5f8f6ed2cffc4dd1eb8d87
# Same bootstrap as the scored p6-b1-rt attempt-2 run.sh (Fix #2): uv on PATH, HF mirror, LAFAN1_G1_DIR read-only
# local CSVs first (PLAN §3: the RT job's data step, unchanged), tarball sha check before use, driver extracted from
# the sha-checked tarball (the driver cmp's itself against the unpacked copy).
# Upstream clone goes to /home/box/.srv-claude/research/supermimic-junior-b-colab/packets/P6/b1arms_mock/run5/content/SuperMimic-Reproduced-b1 (the driver moves an older tree aside on a fresh launch).
# Read only, never cleaned: /home/box/.srv-claude/research/supermimic-junior-b-colab/packets/P6/b1arms_mock/run5/content/SuperMimic-Reproduced (P4 tree, LAFAN1 CSVs) and /home/box/.srv-claude/research/supermimic-junior-b-colab/packets/P6/b1arms_mock/run5/content/p5_p4ckpts (the six
# P4 ckpt_0001600.pt transfer sources, PLAN §4 identities checked by the driver before each xfer/frozen run).
# Job launch 2 (PLAN §7, only after an INFRA failure of the whole job): B1ARMS_RESUME=1 bash ./run.sh
set -euo pipefail
RUN_SH=$(readlink -f "$0"); JOB_DIR=$PWD
mkdir -p /home/box/.srv-claude/research/supermimic-junior-b-colab/packets/P6/b1arms_mock/run5/content/p6_b1arms
exec > >(tee -a /home/box/.srv-claude/research/supermimic-junior-b-colab/packets/P6/b1arms_mock/run5/content/p6_b1arms/runner_stdout.log) 2>&1
export TZ=America/Toronto LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
export PATH="${HOME}/.local/bin:/data/muchuan/.local/bin:${PATH}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export HF_HUB_ENABLE_HF_TRANSFER=0
export LAFAN1_G1_DIR="${LAFAN1_G1_DIR:-/home/box/.srv-claude/research/supermimic-junior-b-colab/packets/P6/b1arms_mock/run5/content/SuperMimic-Reproduced/data/raw/lafan1/g1}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export B1ARMS_RESUME="${B1ARMS_RESUME:-0}"
TGZ_SHA=0f18b8bbca7f7ef13fffb0bcf51b2370e997580a5b5f8f6ed2cffc4dd1eb8d87
UPLOAD_TGZ=${UPLOAD_TGZ:-$PWD/junior_b_colab-P6-B1ARMS.tgz}
B1ARMS_TGZ=/home/box/.srv-claude/research/supermimic-junior-b-colab/packets/P6/b1arms_mock/run5/content/p6_b1arms/junior_b_colab-P6-B1ARMS.tgz

if ! command -v uv >/dev/null 2>&1; then
  pip3 install -q uv || curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:/data/muchuan/.local/bin:${PATH}"
fi
command -v uv
uv --version
echo "HF_ENDPOINT=${HF_ENDPOINT} CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES} B1ARMS_RESUME=${B1ARMS_RESUME}"
echo "LAFAN1_G1_DIR=${LAFAN1_G1_DIR}"
# preflight: the slot_rule=first CSVs in the read-only P4 tree. Informational only; fetch_clip enforces the same pins
# on whatever source it uses and the driver's data step BLOCKs on a mismatch.
( cd "$LAFAN1_G1_DIR" 2>/dev/null && sha256sum -c - <<'PINS' ) || echo "LAFAN1_LOCAL_PREFLIGHT=FAIL (fetch_clip falls back to hf_hub/urllib)"
68c7887438e94f1f3d9ebacd3a8ce59251a22c7b05129a0f5d7cacaedc48c28d  walk1_subject1.csv
ec02af4447a62214a6fec6afff60c75d0ecc8f80f8fb45e3cd4119fed9ceac8d  run1_subject2.csv
e2a369e92e5ad076c5acffff7bce53157a0e6cd9e7e9f6a08dadfb1eb2928d8f  dance1_subject1.csv
3f55c1a0f87564044a71817d62dc2a40aa76332aa1cab3f1c817333a197c78c2  jumps1_subject1.csv
PINS
# preflight: P4 transfer sources present (informational; the driver checks sha256 before each xfer/frozen run)
ls -l /home/box/.srv-claude/research/supermimic-junior-b-colab/packets/P6/b1arms_mock/run5/content/p5_p4ckpts/logs/b0_*_s[012]/ckpt_0001600.pt 2>/dev/null || echo "P4_CKPT_PREFLIGHT=missing under /home/box/.srv-claude/research/supermimic-junior-b-colab/packets/P6/b1arms_mock/run5/content/p5_p4ckpts (driver tries the other read-only roots)"

echo "$TGZ_SHA  $UPLOAD_TGZ" | sha256sum -c -
cp -f "$UPLOAD_TGZ" "$B1ARMS_TGZ"
echo "$TGZ_SHA  $B1ARMS_TGZ" | sha256sum -c -

tar -xzOf "$B1ARMS_TGZ" packets/P6/b1arms_driver.sh > /home/box/.srv-claude/research/supermimic-junior-b-colab/packets/P6/b1arms_mock/run5/content/p6_b1arms/b1arms_driver.sh
chmod +x /home/box/.srv-claude/research/supermimic-junior-b-colab/packets/P6/b1arms_mock/run5/content/p6_b1arms/b1arms_driver.sh

B1ARMS_EXTRA_FILES="$RUN_SH /home/box/.srv-claude/research/supermimic-junior-b-colab/packets/P6/b1arms_mock/run5/content/p6_b1arms/runner_stdout.log"
for j in "$JOB_DIR"/job.json "$JOB_DIR"/p6-b1-arms.json; do [ -f "$j" ] && B1ARMS_EXTRA_FILES="$B1ARMS_EXTRA_FILES $j"; done
export B1ARMS_TGZ B1ARMS_TARBALL_SHA="$TGZ_SHA" B1ARMS_OUT_DIR=/home/box/.srv-claude/research/supermimic-junior-b-colab/packets/P6/b1arms_mock/run5/content B1ARMS_EXTRA_FILES
cd /home/box/.srv-claude/research/supermimic-junior-b-colab/packets/P6/b1arms_mock/run5/content
bash /home/box/.srv-claude/research/supermimic-junior-b-colab/packets/P6/b1arms_mock/run5/content/p6_b1arms/b1arms_driver.sh
echo "RUN_SH_DONE utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
