#!/usr/bin/env bash
# P6 B1-RT (RT-6..RT-8) venue bootstrap for xn-4090-gpu2 (spikes/B1-RT/PLAN.md §2, §4, §5; Class-2 amendment C).
# plan=b7365b4f2e382344151c64be979e5e2aff102fbaba6dc6826d8a429b3b9852a5
# amendment(AMENDMENT-C2-rt4.json)=32143be4687ca6de270165a848eaf4aa8292a21a40e8255c142c32f9f048c591
# tarball(junior_b_colab-P6-B1RT.tgz)=85d2cc87aaa906e5c0fe4a81973150bcece57f263a3d2909c6d24a77d5291db1
# Attempt 2 (Fix #2, decision 768d6a0a0e62a7f193e29620316dfdf90bfadba2614bbd047e398925fa036f22; spikes/B1-RT/AMENDMENT-FIX2-fetch.md):
# attempt-1 tarball was 3cbb7726...; rt_cpu.py fetch_clip now reads $LAFAN1_G1_DIR first (sha256-pinned), then hf_hub, then urllib.
# Same bootstrap as P5 run.sh (2ae9af24...): uv on PATH, HF mirror, tarball sha check before use.
# Upstream clone goes to /content/SuperMimic-Reproduced-b1. The P4 tree /content/SuperMimic-Reproduced and
# /content/p5_p4ckpts are read only (two P4 s0 checkpoints for RT-8 (b)); nothing there is written, moved or deleted.
# LAFAN1_G1_DIR is inside that read-only P4 tree: the four CSVs are read into memory only (X-002); never clean it.
set -euo pipefail
RUN_SH=$(readlink -f "$0"); JOB_DIR=$PWD
mkdir -p /content/p6_b1rt
exec > >(tee -a /content/p6_b1rt/runner_stdout.log) 2>&1
export TZ=America/Toronto LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
export PATH="${HOME}/.local/bin:/data/muchuan/.local/bin:${PATH}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export HF_HUB_ENABLE_HF_TRANSFER=0
export LAFAN1_G1_DIR="${LAFAN1_G1_DIR:-/content/SuperMimic-Reproduced/data/raw/lafan1/g1}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
TGZ_SHA=85d2cc87aaa906e5c0fe4a81973150bcece57f263a3d2909c6d24a77d5291db1
AMEND_SHA=32143be4687ca6de270165a848eaf4aa8292a21a40e8255c142c32f9f048c591
UPLOAD_TGZ=${UPLOAD_TGZ:-$PWD/junior_b_colab-P6-B1RT.tgz}
B1RT_TGZ=/content/p6_b1rt/junior_b_colab-P6-B1RT.tgz

if ! command -v uv >/dev/null 2>&1; then
  pip3 install -q uv || curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:/data/muchuan/.local/bin:${PATH}"
fi
command -v uv
uv --version
echo "HF_ENDPOINT=${HF_ENDPOINT} CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES}"
echo "LAFAN1_G1_DIR=${LAFAN1_G1_DIR}"
# preflight (decision 768d6a0a item 2): the slot_rule=first CSVs in the read-only P4 tree. Informational only;
# fetch_clip enforces the same pins on whatever source it uses and data_step BLOCKs on a mismatch.
( cd "$LAFAN1_G1_DIR" 2>/dev/null && sha256sum -c - <<'PINS' ) || echo "LAFAN1_LOCAL_PREFLIGHT=FAIL (fetch_clip falls back to hf_hub/urllib)"
68c7887438e94f1f3d9ebacd3a8ce59251a22c7b05129a0f5d7cacaedc48c28d  walk1_subject1.csv
ec02af4447a62214a6fec6afff60c75d0ecc8f80f8fb45e3cd4119fed9ceac8d  run1_subject2.csv
e2a369e92e5ad076c5acffff7bce53157a0e6cd9e7e9f6a08dadfb1eb2928d8f  dance1_subject1.csv
3f55c1a0f87564044a71817d62dc2a40aa76332aa1cab3f1c817333a197c78c2  jumps1_subject1.csv
PINS

echo "$TGZ_SHA  $UPLOAD_TGZ" | sha256sum -c -
cp -f "$UPLOAD_TGZ" "$B1RT_TGZ"
echo "$TGZ_SHA  $B1RT_TGZ" | sha256sum -c -

# the driver from the sha-checked tarball (the driver cmp's itself against the unpacked copy)
tar -xzOf "$B1RT_TGZ" packets/P6/b1rt_driver.sh > /content/p6_b1rt/b1rt_driver.sh
chmod +x /content/p6_b1rt/b1rt_driver.sh

B1RT_EXTRA_FILES="$RUN_SH /content/p6_b1rt/runner_stdout.log"
for j in "$JOB_DIR"/job.json "$JOB_DIR"/p6-b1-rt.json; do [ -f "$j" ] && B1RT_EXTRA_FILES="$B1RT_EXTRA_FILES $j"; done
export B1RT_TGZ B1RT_TARBALL_SHA="$TGZ_SHA" B1RT_AMENDMENT_SHA="$AMEND_SHA" B1RT_OUT_DIR=/content B1RT_EXTRA_FILES
cd /content
bash /content/p6_b1rt/b1rt_driver.sh
echo "RUN_SH_DONE utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
