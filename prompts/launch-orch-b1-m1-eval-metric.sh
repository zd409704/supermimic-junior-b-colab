#!/usr/bin/env bash
set -euo pipefail
export TZ=America/Toronto LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
PROG=/srv/claude/research/supermimic-junior-b-colab
LOGDIR="$PROG/orch/logs"
mkdir -p "$LOGDIR" "$PROG/orch/reports"
STAMP=$(TZ=America/Toronto date +%Y%m%d-%H%M-EDT)
LOG="$LOGDIR/orch-b1-m1-eval-metric-$STAMP.log"
PIDF="$LOGDIR/orch-b1-m1-eval-metric.pid"
PROMPT="$PROG/prompts/ORCH_P6_B1_M1_EVAL_METRIC.txt"
cd "$PROG"
nohup /home/box/.local/bin/claude -p --model opus --effort medium \
  --dangerously-skip-permissions --permission-mode bypassPermissions \
  --add-dir "$PROG" \
  --add-dir /srv/claude/research/METHOD \
  < "$PROMPT" > "$LOG" 2>&1 &
echo $! > "$PIDF"
echo "launched orch b1-m1-eval-metric pid=$(cat "$PIDF") log=$LOG"
