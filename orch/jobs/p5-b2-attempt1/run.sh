#!/usr/bin/env bash
# P5 B2 attempt-1 venue bootstrap for xn-4090-gpu2 (spikes/B2/PLAN.md §4, §9.3).
# plan=5d1f26f776a3ea56c2becd3ec2fa2cf8e88bd62c43a20f79415a96e82a3da11d
# tarball(CR-B2-1)=53a898e9b635d1317bebabe884f1450e52be2980165811859445c1b9b53ce851
# base_tarball(CR-B0-1)=763867682e3cfa05ca8eb6382ffc9124be2347b898531c60b904061776c33bff
# HF mirror: huggingface.co unreachable on xn-4090 (DIAG b818a714421f3a36ce32e77d8ad72ed8ac67fac2ab1338cf1e2475baff5ed5f7).
# Same bootstrap as P4 relaunch 3 (run.sh da9c19ce...): uv on PATH, HF_ENDPOINT, tarball sha check before use.
set -euo pipefail
RUN_SH=$(readlink -f "$0"); JOB_DIR=$PWD
mkdir -p /content/p5_b2
# runner stdout snapshot for the bundle (PLAN §9.1); the relay's own stdout log stays the authoritative copy
exec > >(tee -a /content/p5_b2/runner_stdout.log) 2>&1
export TZ=America/Toronto LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
export PATH="${HOME}/.local/bin:/data/muchuan/.local/bin:${PATH}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export HF_HUB_ENABLE_HF_TRANSFER=0
TGZ_SHA=53a898e9b635d1317bebabe884f1450e52be2980165811859445c1b9b53ce851
UPLOAD_TGZ=${UPLOAD_TGZ:-$PWD/junior_b_colab-CR-B2-1.tgz}
B2_TGZ=/content/junior_b_colab-CR-B2-1.tgz

if ! command -v uv >/dev/null 2>&1; then
  pip3 install -q uv || curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:/data/muchuan/.local/bin:${PATH}"
fi
command -v uv
uv --version
echo "HF_ENDPOINT=${HF_ENDPOINT}"

echo "$TGZ_SHA  $UPLOAD_TGZ" | sha256sum -c -
cp -f "$UPLOAD_TGZ" "$B2_TGZ"
echo "$TGZ_SHA  $B2_TGZ" | sha256sum -c -

# the P5 driver and the CR-B0-1 driver it sources, both from the sha-checked tarball (the driver cmp's both copies)
tar -xOf "$B2_TGZ" packets/P5/b2_driver.sh > /content/p5_b2/b2_driver.sh
tar -xOf "$B2_TGZ" packets/P4/b0_driver.sh > /content/p5_b2/b0_driver.sh
chmod +x /content/p5_b2/b2_driver.sh

# bundle extras (PLAN §9.1): run.sh, the runner-stdout snapshot, and the job JSON if the runner placed one in its workdir
B2_EXTRA_FILES="$RUN_SH /content/p5_b2/runner_stdout.log"
for j in "$JOB_DIR"/job.json "$JOB_DIR"/p5-b2-attempt1.json; do [ -f "$j" ] && B2_EXTRA_FILES="$B2_EXTRA_FILES $j"; done
export B2_TGZ B2_TARBALL_SHA="$TGZ_SHA" B2_P4_DRIVER=/content/p5_b2/b0_driver.sh B2_OUT_DIR=/content B2_EXTRA_FILES
cd /content
bash /content/p5_b2/b2_driver.sh
echo "RUN_SH_DONE utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
