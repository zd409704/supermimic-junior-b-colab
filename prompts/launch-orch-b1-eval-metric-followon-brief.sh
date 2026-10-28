#!/usr/bin/env bash
set -euo pipefail
export TZ=America/Toronto LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
PROG=/srv/claude/research/supermimic-junior-b-colab
LOGDIR="$PROG/orch/logs"
mkdir -p "$LOGDIR" "$PROG/orch/reports" "$PROG/prompts"
STAMP=$(TZ=America/Toronto date +%Y%m%d-%H%M-EDT)
LOG="$LOGDIR/orch-b1-eval-metric-followon-brief-$STAMP.log"
PIDF="$LOGDIR/orch-b1-eval-metric-followon-brief.pid"
PROMPT="$PROG/prompts/ORCH_P6_B1_EVAL_METRIC_FOLLOWON_BRIEF.txt"
cd "$PROG"
nohup /home/box/.local/bin/claude -p --model opus --effort medium \
  --dangerously-skip-permissions --permission-mode bypassPermissions \
  --add-dir "$PROG" \
  --add-dir /srv/claude/research/METHOD \
  < "$PROMPT" > "$LOG" 2>&1 &
echo $! > "$PIDF"
echo "launched orch b1-eval-metric-followon-brief pid=$(cat "$PIDF") log=$LOG"
