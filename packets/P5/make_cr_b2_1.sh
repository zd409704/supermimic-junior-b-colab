#!/usr/bin/env bash
# CR-B2-1 (f): deterministic tarball + manifest listing (same recipe as P1 f69dd11e... and CR-B0-1 763867682e3c...:
# GNU tar, sorted names, mtime 2026-10-25 00:00:00 UTC, uid/gid 0, mode 644, gzip -n).
# Contents = the 12 D-004 files + the 6 CR-B0-1 files (both byte-identical, hashes in packets/P5/MANIFEST_ADDENDUM.md)
# + the 12 CR-B2-1 new files below. Usage: make_cr_b2_1.sh list | make_cr_b2_1.sh tar <out.tgz>
set -euo pipefail
cd /srv/claude/research/supermimic-junior-b-colab
FROZEN=$(sed -n '/^```$/,/^```$/p' packets/P1/FREEZE_MANIFEST.md | grep -v '```' | awk '{print $2}')   # 12 sealed D-004 files
CRB01="configs/b0_microbench.yaml configs/b0_microbench_lr05.yaml packets/P4/BUNDLE_CONTRACT.md packets/P4/UPSTREAM_FACTS.md packets/P4/b0_driver.sh packets/P4/b0_driver_helper.py"
NEW="configs/b2_idx.yaml configs/b2_mtrain.yaml packets/P5/BUNDLE_CONTRACT.md packets/P5/b2_driver.sh packets/P5/b2_driver_helper.py packets/P5/maskstream.py packets/P5/mlp_mind.py packets/P5/p4_pip_freeze_ref.txt packets/P5/p5_eval_entry.py packets/P5/p5_train_entry.py packets/P5/perm_check.py packets/P5/tests/test_p5_prep.py"
FILES=$(printf '%s\n' $FROZEN $CRB01 $NEW | LC_ALL=C sort)
case "${1:-}" in
  list) sha256sum $FILES ;;
  frozen) printf '%s\n' $FROZEN $CRB01 | LC_ALL=C sort ;;
  new) printf '%s\n' $NEW | LC_ALL=C sort ;;
  tar)  tar --format=gnu --sort=name --mtime="2026-10-25 00:00:00 UTC" --owner=0 --group=0 --numeric-owner --mode=644 \
            -cf - $FILES | gzip -n > "$2" ;;
  *) echo "usage: $0 list|frozen|new|tar <out>"; exit 2 ;;
esac
