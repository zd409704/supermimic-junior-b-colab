#!/usr/bin/env bash
# P6 seal helper: append "<UTC> <epoch> <EVENT> <sha256> <path> <note>" to logs/seal.log (append-only).
set -euo pipefail
ROOT=/srv/claude/research/supermimic-junior-b-colab
ev=$1; p=$2; shift 2
sha=$(sha256sum "$ROOT/$p" | cut -d' ' -f1)
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $(date +%s) $ev $sha $p $*" >> "$ROOT/logs/seal.log"
echo "$sha"
