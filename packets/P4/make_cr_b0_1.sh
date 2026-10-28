#!/usr/bin/env bash
# CR-B0-1 (e): deterministic tarball + manifest listing (same recipe as the P1 freeze tarball f69dd11e...:
# GNU tar, sorted names, mtime 2026-10-25 00:00:00 UTC, uid/gid 0, mode 644, gzip -n).
# Usage: make_cr_b0_1.sh list | make_cr_b0_1.sh tar <out.tgz>
set -euo pipefail
cd /srv/claude/research/supermimic-junior-b-colab
NEW="configs/b0_microbench.yaml configs/b0_microbench_lr05.yaml packets/P4/BUNDLE_CONTRACT.md packets/P4/UPSTREAM_FACTS.md packets/P4/b0_driver.sh packets/P4/b0_driver_helper.py"
FROZEN=$(sed -n '/^```$/,/^```$/p' packets/P1/FREEZE_MANIFEST.md | grep -v '```' | awk '{print $2}')   # the 12 sealed D-004 files
FILES=$(printf '%s\n' $FROZEN $NEW | LC_ALL=C sort)
case "${1:-}" in
  list) sha256sum $FILES ;;
  tar)  tar --format=gnu --sort=name --mtime="2026-10-25 00:00:00 UTC" --owner=0 --group=0 --numeric-owner --mode=644 \
            -cf - $FILES | gzip -n > "$2" ;;
  *) echo "usage: $0 list|tar <out>"; exit 2 ;;
esac
