#!/usr/bin/env bash
# Run the arms driver in CPU mock mode against the built tarball. Usage: run_mock.sh <dir> [extra env assignments...]
set -uo pipefail
ROOT=/srv/claude/research/supermimic-junior-b-colab
D=$(readlink -f "$1"); shift
TGZ=$ROOT/packets/P6/junior_b_colab-P6-B1ARMS.tgz
env "$@" B1ARMS_MOCK=1 B1ARMS_J="$D/junior" B1ARMS_U="$D/up" B1ARMS_OUT_DIR="$D/out" B1ARMS_PY=python3 \
  B1ARMS_MOCK_ENTRY="$ROOT/packets/P6/b1arms_mock/mock_entry.py" B1ARMS_MOCK_NPZ="$D/npz" B1ARMS_MOCK_CKPT_ROOT="$D/ckroot" \
  B1ARMS_MOCK_SRC_SHAS="$D/src_shas.txt" B1ARMS_MOCK_POLL_S=1 B1ARMS_MOCK_STATE="$D/mockstate" \
  B1ARMS_MOCK_BEHAVIOUR="$D/behaviour.json" B1ARMS_TGZ="$TGZ" B1ARMS_TARBALL_SHA="$(sha256sum "$TGZ" | cut -c1-64)" \
  bash "$ROOT/packets/P6/b1arms_driver.sh"
