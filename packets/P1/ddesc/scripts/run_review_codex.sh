#!/usr/bin/env bash
set -uo pipefail
PROG=/srv/claude/research/supermimic-junior-b-colab; cd "$PROG"; N=${1:-1}; L=logs/p1/ddesc
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $(date +%s) START review-on-Y(codex) attempt$N input=$(sha256sum packets/P1/ddesc/prompts/review-on-Y.md|cut -c1-64)" >> $L/runs.log
timeout 1200 codex exec -m gpt-6-astra -c model_reasoning_effort=high -s workspace-write -C "$PROG/packets/P1/ddesc/reviews-wip/on-Y" \
  --skip-git-repo-check --json -o "$L/review-on-Y-attempt$N-last-message.txt" - \
  < packets/P1/ddesc/prompts/review-on-Y.md > "$L/review-on-Y-attempt$N-events.jsonl" 2> "$L/review-on-Y-attempt$N-stderr.log"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $(date +%s) END review-on-Y(codex) attempt$N rc=$?" >> $L/runs.log
