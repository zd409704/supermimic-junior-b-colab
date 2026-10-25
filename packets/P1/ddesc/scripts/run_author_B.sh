#!/usr/bin/env bash
# Author B launcher (roster.md). Class-0 mechanics only; inputs fixed by sealed author-B.md.
set -uo pipefail
PROG=/srv/claude/research/supermimic-junior-b-colab
cd "$PROG"
N=${1:-1}
L=logs/p1/ddesc
OUT=packets/P1/ddesc/drafts/B
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $(date +%s) START author-B attempt$N input=$(sha256sum packets/P1/ddesc/prompts/author-B.md|cut -c1-64)" >> $L/runs.log
timeout 1800 codex exec -m gpt-6-astra -c model_reasoning_effort=high -s workspace-write -C "$PROG/$OUT" \
  --skip-git-repo-check --json -o "$L/author-B-attempt$N-last-message.txt" - \
  < packets/P1/ddesc/prompts/author-B.md > "$L/author-B-attempt$N-events.jsonl" 2> "$L/author-B-attempt$N-stderr.log"
RC=$?
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $(date +%s) END author-B attempt$N rc=$RC" >> $L/runs.log
