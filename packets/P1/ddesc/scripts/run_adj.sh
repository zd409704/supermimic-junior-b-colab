#!/usr/bin/env bash
set -uo pipefail
PROG=/srv/claude/research/supermimic-junior-b-colab; cd "$PROG/logs/p1/ddesc/adj-scratch"; P=$1; N=${2:-1}; L=$PROG/logs/p1/ddesc
IN=$PROG/packets/P1/ddesc/prompts/adjudicator-pass$P.md
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $(date +%s) START adjudicator-pass$P(agy gemini-4-argon-high) attempt$N input=$(sha256sum $IN|cut -c1-64)" >> $L/runs.log
timeout 1300 agy --model gemini-4-argon-high --effort high --print-timeout 1200s --log-file $L/adj-pass$P-attempt$N.toollog -p="$(cat $IN)" > $L/adj-pass$P-attempt$N.out 2> $L/adj-pass$P-attempt$N.err
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $(date +%s) END adjudicator-pass$P attempt$N rc=$?" >> $L/runs.log
