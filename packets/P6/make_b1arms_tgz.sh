#!/usr/bin/env bash
# Build the P6d B1 arms upload tarball packets/P6/junior_b_colab-P6-B1ARMS.tgz (deterministic: sorted names, fixed
# mtime, numeric owner 0, gzip -n). Writes packets/P6/MANIFEST-b1arms.sha256 (sha256 of every file in the tarball but
# itself). Same pattern as make_b1rt_tgz.sh; adds the arms driver + helper and spikes/B1/PLAN.md, drops b1rt_driver.sh
# and verdict_rt.py (box-side tools, not needed on the GPU host).
set -euo pipefail
ROOT=/srv/claude/research/supermimic-junior-b-colab
cd "$ROOT"
OUT=packets/P6/junior_b_colab-P6-B1ARMS.tgz
MAN=packets/P6/MANIFEST-b1arms.sha256
LIST=$(mktemp -p "$ROOT/packets/P6" .b1arms-list.XXXX)
trap 'rm -f "$LIST"' EXIT
{
  find code -type f ! -path '*/__pycache__/*' ! -name '*.pyc'
  find assets/home_humanoid_mjcf -type f
  ls packets/P6/b1/*.py packets/P6/configs/*.yaml
  echo packets/P6/b1arms_driver.sh; echo packets/P6/upstream-b1.patch
  echo spikes/B1/PLAN.md
  for f in PLAN.md AMENDMENT-C2-rt4.json ASSUMPTIONS.md home_humanoid.py retarget_rta.py rt_cpu.py supermimic_compat.py \
           results-cpu-attempt1.json; do echo "spikes/B1-RT/$f"; done
} | LC_ALL=C sort > "$LIST"
xargs -a "$LIST" -d '\n' sha256sum > "$MAN"
echo "$MAN" >> "$LIST"
tar --sort=name --mtime='2026-10-27 00:00:00Z' --owner=0 --group=0 --numeric-owner -cf - -T "$LIST" | gzip -n -9 > "$OUT"
echo "files=$(wc -l < "$MAN") manifest_sha256=$(sha256sum "$MAN" | cut -c1-64)"
echo "tarball_sha256=$(sha256sum "$OUT" | cut -c1-64) $OUT"
