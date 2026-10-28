#!/usr/bin/env bash
set -euo pipefail
export TZ=America/Toronto LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
PROG=/srv/claude/research/supermimic-junior-b-colab
LOGDIR="$PROG/orch/logs"
mkdir -p "$LOGDIR" "$PROG/orch/reports" "$PROG/spikes/B0-smoke"
STAMP=$(date +%Y%m%d-%H%M-EDT)
LOG="$LOGDIR/orch-p2-deposit-verdict-$STAMP.log"
PIDF="$LOGDIR/orch-p2-deposit-verdict.pid"
PROMPT="$PROG/prompts/ORCH_P2_DEPOSIT_VERDICT.txt"
cd "$PROG"
nohup /home/box/.local/bin/claude -p --model opus --effort medium \
  --dangerously-skip-permissions --permission-mode bypassPermissions \
  --add-dir "$PROG" \
  < "$PROMPT" > "$LOG" 2>&1 &
echo $! > "$PIDF"
echo "launched orch p2-deposit-verdict pid=$(cat "$PIDF") log=$LOG"

