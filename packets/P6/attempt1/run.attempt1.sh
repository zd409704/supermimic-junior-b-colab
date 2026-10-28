#!/usr/bin/env bash
# P6 B1-RT (RT-6..RT-8) venue bootstrap for xn-4090-gpu2 (spikes/B1-RT/PLAN.md §2, §4, §5; Class-2 amendment C).
# plan=b7365b4f2e382344151c64be979e5e2aff102fbaba6dc6826d8a429b3b9852a5
# amendment(AMENDMENT-C2-rt4.json)=32143be4687ca6de270165a848eaf4aa8292a21a40e8255c142c32f9f048c591
# tarball(junior_b_colab-P6-B1RT.tgz)=3cbb77267863145887439dad322f6b1017ba485f5c5f7b491583962596a4d956
# Same bootstrap as P5 run.sh (2ae9af24...): uv on PATH, HF mirror, tarball sha check before use.
# Upstream clone goes to /content/SuperMimic-Reproduced-b1. The P4 tree /content/SuperMimic-Reproduced and
# /content/p5_p4ckpts are read only (two P4 s0 checkpoints for RT-8 (b)); nothing there is written, moved or deleted.
set -euo pipefail
RUN_SH=$(readlink -f "$0"); JOB_DIR=$PWD
mkdir -p /content/p6_b1rt
exec > >(tee -a /content/p6_b1rt/runner_stdout.log) 2>&1
export TZ=America/Toronto LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
export PATH="${HOME}/.local/bin:/data/muchuan/.local/bin:${PATH}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export HF_HUB_ENABLE_HF_TRANSFER=0
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
TGZ_SHA=3cbb77267863145887439dad322f6b1017ba485f5c5f7b491583962596a4d956
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
