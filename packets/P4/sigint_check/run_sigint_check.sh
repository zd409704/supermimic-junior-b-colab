#!/usr/bin/env bash
# P4-prep SIGINT launcher check, PLAN §2.2 (f). Usage: run_sigint_check.sh <attempt N>
# attempt 2+: the summary line reports the SIGINT test exit (attempt 1 printed the later natural-exit test code).
# Runs on the research box (CPU). Sources packets/P4/b0_driver.sh and uses the same functions train_attempt uses:
# launch_signal_restored (non-interactive bash '&' job + SIG_DFL/execv launcher) and harness_stop (SIGINT only).
set -u
ROOT=/srv/claude/research/supermimic-junior-b-colab
N=$1
LOG=$ROOT/logs/p4prep/sigint-check-attempt$N.log
WORK=$ROOT/logs/p4prep/sigint-work-attempt$N
[ -e "$LOG" ] || [ -e "$WORK" ] && { echo "refusing: attempt $N exists"; exit 2; }
mkdir -p "$WORK"
source "$ROOT/packets/P4/b0_driver.sh"
PY=$ROOT/.venv/bin/python
DUMMY=$ROOT/packets/P4/sigint_check/dummy_trainer.py
{
echo "# P4-prep SIGINT launcher check attempt$N, research box, $(utc) (epoch $(date +%s))"
echo "# bash $BASH_VERSION; $($PY -c 'import sys;print("python",sys.version.split()[0])'); shell interactive flags: $-"
echo "# driver sha256 $(sha256sum $ROOT/packets/P4/b0_driver.sh | cut -c1-64); dummy sha256 $(sha256sum $DUMMY | cut -c1-64); POLL_S=$POLL_S STOP_WAIT_S=$STOP_WAIT_S"
cd "$WORK"
echo "## test: driver path (launch_signal_restored + harness_stop)"
RUN=logs/sigtest_run; mkdir -p meta
launch_signal_restored "train_sigtest.log" "$PY" "$DUMMY" "$RUN"
echo "trainer pid=$TR; SigIgn of the pid (hex mask, bit 2 = SIGINT): $(sleep 1; grep SigIgn /proc/$TR/status)"
harness_stop "$TR" train_sigtest.log "$RUN/ckpt_0001600.pt" "$RUN/junior_policy.json" meta/harness_stop_sigtest.txt
echo "--- meta/harness_stop_sigtest.txt"; cat meta/harness_stop_sigtest.txt
echo "--- train_sigtest.log"; grep -v '^it [0-9]* |' train_sigtest.log; echo "(it lines: $(grep -c '^it [0-9]* |' train_sigtest.log), endpoint lines: $(grep -c "$ENDPOINT_RE" train_sigtest.log))"
echo "--- sidecar: $(cat $RUN/junior_policy.json 2>/dev/null || echo MISSING)"
SIG_EXIT=$HS_EXIT
SENT=$(grep '^harness_stop=' meta/harness_stop_sigtest.txt | cut -d= -f2)
TO=$(grep '^harness_stop_timeout=' meta/harness_stop_sigtest.txt | cut -d= -f2)
OK=false
[ "$SENT" = true ] && [ "$TO" = false ] && [ -f "$RUN/junior_policy.json" ] && [ "$SIG_EXIT" -ne 0 ] && [ "$SIG_EXIT" -ne 137 ] && OK=true
echo "## control (no launcher): plain non-interactive '&' job, same dummy, SIGINT expected to be ignored"
RUN2=logs/control_run
env -u PYTHONPATH "$PY" "$DUMMY" "$RUN2" > train_control.log 2>&1 & C=$!
sleep 3; kill -INT $C; sleep 3
if kill -0 $C 2>/dev/null; then echo "control: alive 3 s after SIGINT (SIGINT ignored, as PLAN §4.2 expects); $(grep SigIgn /proc/$C/status)"; CTRL=ignored
else echo "control: exited after SIGINT"; CTRL=exited; fi
kill -TERM $C 2>/dev/null; wait $C; echo "control exit after SIGTERM cleanup=$?; control sidecar: $([ -f $RUN2/junior_policy.json ] && echo present || echo absent)"
echo "## natural exit check (trainer ends before the harness signals)"
RUN3=logs/natural_run
launch_signal_restored "train_natural.log" "$PY" -c "import time,sys; print('it 50 |', flush=True); time.sleep(2); sys.exit(3)"
harness_stop "$TR" train_natural.log "$RUN3/ckpt_0001600.pt" "$RUN3/junior_policy.json" meta/harness_stop_natural.txt
echo "natural: exit=$HS_EXIT $(grep -E '^(harness_stop|trainer_exited_before_signal|endpoint_line_seen)=' meta/harness_stop_natural.txt | tr '\n' ' ')"
NAT=false; [ "$HS_EXIT" -eq 3 ] && grep -q '^harness_stop=false' meta/harness_stop_natural.txt && NAT=true
echo "SIGINT_CHECK attempt=$N result=$($OK && echo PASS || echo FAIL) exit_code=$SIG_EXIT harness_stop=$SENT timeout=$TO sidecar=$([ -f $RUN/junior_policy.json ] && echo present || echo missing) control=$CTRL natural_exit_ok=$NAT"
} > "$LOG" 2>&1
tail -1 "$LOG"
