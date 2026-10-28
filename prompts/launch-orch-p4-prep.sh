#!/usr/bin/env bash
set -euo pipefail
export TZ=America/Toronto LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
PROG=/srv/claude/research/supermimic-junior-b-colab
LOGDIR="$PROG/orch/logs"
mkdir -p "$LOGDIR" "$PROG/packets/P4" "$PROG/logs/p4prep" "$PROG/spikes/B0/verdict"
STAMP=$(date +%Y%m%d-%H%M-EDT)
LOG="$LOGDIR/orch-p4-prep-$STAMP.log"
PIDF="$LOGDIR/orch-p4-prep.pid"
PROMPT="$PROG/prompts/ORCH_P4_PREP.txt"
cd "$PROG"
nohup /home/box/.local/bin/claude -p --model opus --effort medium \
  --dangerously-skip-permissions --permission-mode bypassPermissions \
  --add-dir "$PROG" \
  < "$PROMPT" > "$LOG" 2>&1 &
echo $! > "$PIDF"
echo "launched orch p4-prep pid=$(cat "$PIDF") log=$LOG"

