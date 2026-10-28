#!/usr/bin/env bash
set -euo pipefail
export TZ=America/Toronto LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
PROG=/srv/claude/research/supermimic-junior-b-colab
LOGDIR="$PROG/orch/logs"
mkdir -p "$LOGDIR" "$PROG/spikes/B1" "$PROG/spikes/B1-RT" "$PROG/packets/P6"
STAMP=$(date +%Y%m%d-%H%M-EDT)
LOG="$LOGDIR/orch-p6-b1-line-$STAMP.log"
PIDF="$LOGDIR/orch-p6-b1-line.pid"
PROMPT="$PROG/prompts/ORCH_P6_B1_LINE.txt"
cd "$PROG"
nohup /home/box/.local/bin/claude -p --model opus --effort medium \
  --dangerously-skip-permissions --permission-mode bypassPermissions \
  --add-dir "$PROG" \
  < "$PROMPT" > "$LOG" 2>&1 &
echo $! > "$PIDF"
echo "launched orch p6-b1-line pid=$(cat "$PIDF") log=$LOG"
