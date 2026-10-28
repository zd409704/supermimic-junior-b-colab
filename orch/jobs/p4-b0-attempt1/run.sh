#!/usr/bin/env bash
# P4 B0 attempt-1 venue bootstrap for xn-4090-gpu2 (PLAN §2.3 + §4).
# Ensures uv on PATH (driver setup calls `uv sync`).
# Fix #1 (Manager 2026-10-26): HF_ENDPOINT mirror — DIAG b818a714421f3a36ce32e77d8ad72ed8ac67fac2ab1338cf1e2475baff5ed5f7
# plan_base=ed6b6a54a860bbfc67d7c822b5394804b8d408f6aae57fbeb118d2ea63c52557
# plan_full_with_amendment_v1=356c389f4c2efd47249f741b23f69bde19043a0ed8dc6e2c637abe397b9e145a
# tarball=763867682e3cfa05ca8eb6382ffc9124be2347b898531c60b904061776c33bff
set -euo pipefail
export TZ=America/Toronto LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
export PATH="${HOME}/.local/bin:/data/muchuan/.local/bin:${PATH}"
# huggingface.co unreachable on xn-4090; mirror keeps X-002 runtime download
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export HF_HUB_ENABLE_HF_TRANSFER=0
TGZ_SHA=763867682e3cfa05ca8eb6382ffc9124be2347b898531c60b904061776c33bff
UPLOAD_TGZ=${UPLOAD_TGZ:-$PWD/junior_b_colab-CR-B0-1.tgz}
B0_TGZ=/content/junior_b_colab-CR-B0-1.tgz

# Ensure uv exists before driver (driver's `pip install -q uv` may not put uv on PATH)
if ! command -v uv >/dev/null 2>&1; then
  pip3 install -q uv || curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:/data/muchuan/.local/bin:${PATH}"
fi
command -v uv
uv --version
echo "HF_ENDPOINT=${HF_ENDPOINT}"

mkdir -p /content
echo "$TGZ_SHA  $UPLOAD_TGZ" | sha256sum -c -
cp -f "$UPLOAD_TGZ" "$B0_TGZ"
echo "$TGZ_SHA  $B0_TGZ" | sha256sum -c -

tar -xOf "$B0_TGZ" packets/P4/b0_driver.sh > /content/b0_driver.sh
chmod +x /content/b0_driver.sh

export B0_TGZ B0_TARBALL_SHA="$TGZ_SHA" B0_VENUE=xn4090 B0_OUT_DIR=/content
cd /content
bash /content/b0_driver.sh
echo "RUN_SH_DONE utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
