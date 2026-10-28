#!/usr/bin/env bash
# Build one CPU mock environment for the B1 arms driver: fake P4 source ckpts, sha file, npz, behaviour file.
# Usage: setup_mock.sh <dir> <behaviour-json> [bad_src_key]
set -euo pipefail
D=$1; mkdir -p "$D"/ckroot "$D"/npz "$D"/out
for pol in attention mlp_matched; do for k in 0 1 2; do
  mkdir -p "$D/ckroot/logs/b0_${pol}_s$k"; echo "fake P4 $pol s$k" > "$D/ckroot/logs/b0_${pol}_s$k/ckpt_0001600.pt"
  echo "${pol}_s$k $(sha256sum "$D/ckroot/logs/b0_${pol}_s$k/ckpt_0001600.pt" | cut -c1-64)" >> "$D/src_shas.txt"
done; done
[ -n "${3:-}" ] && sed -i "s/^$3 .*/$3 $(printf 0%.0s {1..64})/" "$D/src_shas.txt"
for c in a b c d; do echo "$c" > "$D/npz/$c.npz"; done
echo "$2" > "$D/behaviour.json"
