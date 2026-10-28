#!/usr/bin/env bash
# usage: seal_and_lock.sh <label> <file> <dir-to-lock> [extra-path-to-lock]
set -euo pipefail
cd /srv/claude/research/supermimic-junior-b-colab
L=$1; F=$2; D=$3
H=$(sha256sum "$F" | cut -d' ' -f1)
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $(date +%s) SEAL $H $F $L words=$(wc -w < "$F")" >> logs/seal.log
chmod 000 "$D"; echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $(date +%s) LOCK-000 - $D isolation" >> logs/seal.log
if [ $# -ge 4 ]; then chmod 000 "$4"; echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $(date +%s) LOCK-000 - $4 isolation" >> logs/seal.log; fi
echo "sealed $L $H"
