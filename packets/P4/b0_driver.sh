#!/usr/bin/env bash
# P4 B0 microbench driver (CR-B0-1 (d)). Implements spikes/B0/PLAN.md §4 and writes the §8.1 bundle.
# PLAN sha256 ed6b6a54a860bbfc67d7c822b5394804b8d408f6aae57fbeb118d2ea63c52557. Bundle detail: packets/P4/BUNDLE_CONTRACT.md.
# F-1 = unsuitable (packets/P4/UPSTREAM_FACTS.md): no cap flag; the harness stop (PLAN §4.3) ends every attempt.
#
# Runner usage (Colab L4, or XN-4090 with the /content layout of PLAN §2.3):
#   upload the CR-B0-1 tarball to $B0_TGZ and this script (byte-identical to the copy inside the tarball), then
#   B0_TARBALL_SHA=<sealed hash from the runner note> bash b0_driver.sh
# Optional: B0_STATE_IN=<previous meta/driver_state.txt> (new session part), B0_VENUE=colab|xn4090, B0_OUT_DIR=/content.
# The runner chooses nothing: schedule, retries and divergence pairs come from b0_driver_helper.py `next`.
#
# Sourcing this file (`source b0_driver.sh`) defines the functions without running main; the P4-prep SIGINT check
# (PLAN §2.2 (f)) uses launch_signal_restored + harness_stop from here.

J=/content/junior
U=/content/SuperMimic-Reproduced
PIN=d9be385b3eeb13a638fb33fb200d3bfd9be9839f
HELPER=$J/packets/P4/b0_driver_helper.py
POLL_S=30            # PLAN §4.3: two checkpoint-size polls 30 s apart
STOP_WAIT_S=300      # PLAN §4.3: wait up to 300 s after SIGINT
SPEND_CAP_H=7        # PLAN §9
ENDPOINT_RE='^it 1600 |'

utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { echo "[b0_driver $(utc)] $*"; }
dev() { echo "- [driver] $(utc) $*" >> "$U/deviations.md"; }
blocked() { echo "BLOCKED_REASON=$1 detail=$2" >> "$U/BLOCKED.md"; log "BLOCKED $1: $2"; }

# ------------------------------------------------------------------ launcher (PLAN §4.2)
# A non-interactive bash '&' job starts with SIGINT ignored, and Python keeps SIG_IGN. Setting SIG_DFL and then
# exec gives the trainer the normal KeyboardInterrupt handler, so the wrapper's finally runs.
# Usage: launch_signal_restored <logfile> <python> <script> [args...]; sets TR to the trainer PID.
launch_signal_restored() {
  local logf=$1; shift
  env -u PYTHONPATH "$PY" -c 'import os,signal,sys; signal.signal(signal.SIGINT, signal.SIG_DFL); os.execv(sys.argv[1], sys.argv[1:])' \
      "$@" > "$logf" 2>&1 &
  TR=$!
}

# ------------------------------------------------------------------ harness stop (PLAN §4.3)
# Usage: harness_stop <pid> <trainer log> <ckpt path> <sidecar path> <out file>. Sets HS_EXIT.
harness_stop() {
  local pid=$1 logf=$2 ckpt=$3 sidecar=$4 out=$5
  local seen=false t_line=none s1=none s2=none stable=false sent=false t_sig=none early=false waited=0 timeout=false killed=false
  _poll_pair() {  # two size polls POLL_S apart; sets s1 s2 stable
    if [ -f "$ckpt" ]; then
      s1=$(stat -c %s "$ckpt"); sleep "$POLL_S"; s2=$(stat -c %s "$ckpt" 2>/dev/null || echo none)
      [ "$s1" = "$s2" ] && stable=true
    fi
  }
  while kill -0 "$pid" 2>/dev/null; do
    if ! $seen && grep -q "$ENDPOINT_RE" "$logf" 2>/dev/null; then seen=true; t_line=$(utc); fi
    if $seen; then _poll_pair; $stable && break; fi
    sleep 5
  done
  if kill -0 "$pid" 2>/dev/null && $stable; then
    kill -INT "$pid"; sent=true; t_sig=$(utc)
    while kill -0 "$pid" 2>/dev/null && [ "$waited" -lt "$STOP_WAIT_S" ]; do sleep 1; waited=$((waited + 1)); done
    if kill -0 "$pid" 2>/dev/null; then timeout=true; kill -KILL "$pid"; killed=true; fi
  else
    early=true
  fi
  wait "$pid"; HS_EXIT=$?
  # Trainer exited on its own: the endpoint line may have appeared late; take the two polls after exit.
  if ! $seen && grep -q "$ENDPOINT_RE" "$logf" 2>/dev/null; then seen=true; t_line=$(utc); fi
  if $seen && ! $stable; then _poll_pair; fi
  {
    echo "endpoint_line_seen=$seen"; echo "endpoint_line_utc=$t_line"; echo "ckpt_path=$ckpt"
    echo "ckpt_size_poll1=$s1"; echo "ckpt_size_poll2=$s2"; echo "poll_interval_s=$POLL_S"; echo "ckpt_stable=$stable"
    echo "harness_stop=$sent"; echo "signal=$($sent && echo SIGINT || echo none)"; echo "sigint_sent_utc=$t_sig"
    echo "trainer_exited_before_signal=$early"; echo "exit_wait_s=$waited"; echo "harness_stop_timeout=$timeout"
    echo "sigkill_sent=$killed"; echo "exit_code=$HS_EXIT"
    echo "sidecar=$([ -f "$sidecar" ] && echo present || echo missing)"
  } >> "$out"
}

# ------------------------------------------------------------------ one attempt (PLAN §4.2)
train_attempt() { TAG=$1; CFG=$2; ARM=$3; SEED=$4; N=$5; AID=${TAG}_${ARM}_s${SEED}_a${N}
  RUN=${TAG}_${ARM}_s${SEED}
  if [ "$N" -ge 2 ] && [ -d "logs/${RUN}" ]; then
    mkdir -p logs/attempts && mv "logs/${RUN}" "logs/attempts/${TAG}_${ARM}_s${SEED}_a$((N-1)).live"
    SESSION_DIRS+=("logs/attempts/${TAG}_${ARM}_s${SEED}_a$((N-1)).live")
  elif [ "$N" -eq 1 ] && [ -e "logs/${RUN}" ]; then
    blocked plan_gap "logs/${RUN} exists before attempt 1 (PLAN §3.3 needs a fresh run directory)"; return 2
  fi
  { echo "aid=$AID"; echo "tag=$TAG"; echo "arm=$ARM"; echo "seed=$SEED"; echo "attempt=$N"; echo "cfg=$CFG"
    echo "start_utc=$(utc)"; } > "meta/attempt_${AID}.txt"
  echo "aid=$AID" > "meta/harness_stop_${AID}.txt"
  nvidia-smi --query-gpu=timestamp,memory.used,memory.total --format=csv -l 5 > "meta/gpumem_${AID}.csv" & SMI=$!
  launch_signal_restored "logs/train_${AID}.log" "$PY" /content/junior/code/train_entry.py --mode upstream --policy "$ARM" \
      --config "$CFG" --seed "$SEED"
  log "started $AID pid=$TR"
  harness_stop "$TR" "logs/train_${AID}.log" "logs/${RUN}/ckpt_0001600.pt" "logs/${RUN}/junior_policy.json" "meta/harness_stop_${AID}.txt"
  kill "$SMI" 2>/dev/null; wait "$SMI" 2>/dev/null
  grep -q '^harness_stop=true' "meta/harness_stop_${AID}.txt" && dev "harness stop (PLAN §4.3, SIGINT) used for $AID"
  { echo "end_utc=$(utc)"; echo "exit_code=$HS_EXIT"; } >> "meta/attempt_${AID}.txt"
  read -r CLASS DIVERGED COMPLETED < <("$PY" -I "$HELPER" classify --aid "$AID" --log "logs/train_${AID}.log" \
      --tb-dir "logs/${RUN}/tb" --harness "meta/harness_stop_${AID}.txt" --sidecar "logs/${RUN}/junior_policy.json" \
      --out "meta/attempt_${AID}.txt")
  log "$AID class=$CLASS diverged=$DIVERGED completed=$COMPLETED exit=$HS_EXIT"
  if [ "$COMPLETED" = true ]; then eval_attempt "$AID" "$RUN" "$CFG"; echo "evals=done" >> "meta/attempt_${AID}.txt"
  else echo "evals=skipped" >> "meta/attempt_${AID}.txt"; fi
  # after evals (if completed), for every attempt: archive the run directory without *.pt
  mkdir -p "logs/attempts/${AID}"
  [ -d "logs/${RUN}" ] && tar -C "logs/${RUN}" --exclude='*.pt' -cf - . | tar -C "logs/attempts/${AID}" -xf -
  SESSION_AIDS+=("$AID")
  echo "ATTEMPT $AID $CLASS $DIVERGED $COMPLETED" >> meta/driver_state.txt
}

# ------------------------------------------------------------------ eval (PLAN §4.4, verbatim)
eval_attempt() { AID=$1; RUN=$2; CFG=$3
  for IT in 0000400 0000800 0001200 0001600; do
    for K in 1 2; do
      D=logs/eval/${AID}/it${IT}/exec${K}; mkdir -p $D
      env -u PYTHONPATH $PY /content/junior/code/eval_entry.py --mode upstream --config $CFG \
          --ckpt logs/${RUN}/ckpt_${IT}.pt > $D/eval.log 2>&1; echo "exit=$?" >> $D/eval.log
      mv logs/eval/${RUN}_*_mask*.json $D/ 2>/dev/null
      [ "$(ls $D/*_mask*.json 2>/dev/null | wc -l)" -eq 3 ] && grep -q '^exit=0$' $D/eval.log && break
    done
  done; }

hours_total() { awk -v s="$SESSION_START" -v p="$PRIOR_H" -v n="$(date +%s)" 'BEGIN{printf "%.4f", p + (n - s) / 3600}'; }

# ------------------------------------------------------------------ setup (PLAN §4.1 = runbook §1-§4 as frozen)
setup() {
  pip install -q uv
  if [ -d "$U/.git" ]; then log "reusing clone"; else rm -rf "$U"; git clone https://github.com/CuboiLeo/SuperMimic-Reproduced "$U"; fi
  git -C "$U" checkout "$PIN" || { echo "checkout failed"; return 3; }
  [ "$(git -C "$U" rev-parse HEAD)" = "$PIN" ] || { echo "upstream HEAD != pin"; return 3; }
  cd "$U" || return 3
  STAMP=$(date -u +%Y%m%d-%H%M%S)
  [ -d meta ] && mv meta "meta.prev-$STAMP"            # a persistent FS keeps the previous part's meta aside
  [ -f deviations.md ] && mv deviations.md "deviations.prev-$STAMP.md"
  [ -f BLOCKED.md ] && mv BLOCKED.md "BLOCKED.prev-$STAMP.md"
  mkdir -p meta logs; : > deviations.md
  exec > >(tee -a meta/driver.log) 2>&1
  [ -n "${B0_STATE_IN:-}" ] && cp "$B0_STATE_IN" meta/driver_state.txt
  touch meta/driver_state.txt
  PART=$(( $(grep -c '^PART ' meta/driver_state.txt) + 1 ))
  PRIOR_H=$(awk '$1=="SPENT"{h=$2} END{printf "%.4f", h+0}' meta/driver_state.txt)
  echo "PART $PART $(utc)" >> meta/driver_state.txt
  [ "$PART" -ge 2 ] && dev "session restart: part $PART continues from driver_state (prior_hours=$PRIOR_H; PLAN §3.4)"

  # §4.1 step 2: tarball hash before unpacking
  [ -n "${B0_TARBALL_SHA:-}" ] || { blocked tarball_sha_mismatch "B0_TARBALL_SHA not set"; return 4; }
  [ -f "$B0_TGZ" ] || { blocked tarball_sha_mismatch "missing $B0_TGZ"; return 4; }
  sha256sum "$B0_TGZ" > meta/tarball_sha256.txt
  [ "$(cut -c1-64 meta/tarball_sha256.txt)" = "$B0_TARBALL_SHA" ] || { blocked tarball_sha_mismatch "$(cat meta/tarball_sha256.txt)"; return 4; }
  rm -rf "$J" && mkdir -p "$J" && tar xzf "$B0_TGZ" -C "$J"
  cmp -s "$SELF" "$J/packets/P4/b0_driver.sh" || { blocked plan_gap "running driver differs from the tarball copy"; return 4; }

  uv sync && uv pip install --python .venv/bin/python pyyaml huggingface_hub || { blocked setup_failed "uv sync"; return 5; }
  PY=$U/.venv/bin/python
  if ! $PY -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)"; then   # R1 fallback, runbook §2
    TV=$($PY -c "import torch;print(torch.__version__.split('+')[0])")
    uv pip install --python "$PY" "torch==$TV" --index-url https://download.pytorch.org/whl/cu128 --reinstall
    uv pip install --python "$PY" warp-lang --reinstall
    dev "R1 wheel substitution (runbook §2): torch==$TV from cu128 index, PyPI warp-lang"
    $PY -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)" || { blocked R1_unresolved "cuda unavailable after fallback"; return 6; }
  fi
  $PY -c "import torch; print('cuda', torch.cuda.is_available(), torch.__version__)" > meta/torch_cuda.txt

  # §4.1 step 3: CPU test (runbook §3)
  (cd "$J" && $PY code/tests/test_smoke.py) > meta/cpu_test_smoke.log 2>&1
  (cd "$J" && $PY code/train_entry.py --policy attention) > meta/cpu_train_smoke.log 2>&1
  (cd "$J" && $PY code/eval_entry.py) > meta/cpu_eval_smoke.log 2>&1
  $PY -I "$HELPER" cputest --log meta/cpu_test_smoke.log --out meta/cpu_test_check.txt \
      || { blocked cpu_test_mismatch "$(cat meta/cpu_test_check.txt)"; return 7; }

  # runbook §4: motion data on the runtime only
  SUB=$($PY -c "import yaml;print(yaml.safe_load(open('/content/junior/configs/colab_smoke.yaml'))['upstream']['dataset_subdir'])")
  $PY - <<'EOF' || { blocked setup_failed "motion data download"; return 8; }
import yaml; from huggingface_hub import snapshot_download
c = yaml.safe_load(open('/content/junior/configs/colab_smoke.yaml'))['upstream']
snapshot_download(c['dataset_repo'], repo_type='dataset', local_dir='data/raw/lafan1',
                  allow_patterns=[f"{c['dataset_subdir']}/{n}.csv" for n in c['clips']])
EOF
  env -u PYTHONPATH $PY scripts/data/csv_to_npz_batch.py --input-dir data/raw/lafan1/$SUB \
      --output-dir data/npz/lafan1_smoke --input-fps 30 --workers 2 || { blocked setup_failed "csv_to_npz"; return 8; }
  [ "$(ls data/npz/lafan1_smoke/*.npz 2>/dev/null | wc -l)" -eq 4 ] || { blocked setup_failed "expected 4 npz"; return 8; }

  # §4.1 step 4
  nvidia-smi > meta/nvidia-smi.txt
  uv pip freeze --python "$PY" > meta/pip-freeze.txt
  GPU=$($PY -I "$HELPER" gpuname --smi meta/nvidia-smi.txt)
  case "$GPU" in *T4*) blocked plan_gap "T4 is not allowed for P4 (PLAN §2.3)"; return 9;; esac
  return 0
}

v0_sanity() {
  if grep -q '^V0 ' meta/driver_state.txt; then log "V-0 already on record for this venue"; return 0; fi
  # V-0 env sanity, once per venue (runbook §5 as frozen: unmodified decoder, max-hours 0.1)
  env -u PYTHONPATH $PY -m supermimic.scripts.train --run-name up_sanity --data.npz-dir data/npz/lafan1_smoke \
    --env.num-envs 256 --policy-trainer.batch-size 256 --policy-trainer.horizon 16 \
    --policy-trainer.compile None --schedule.max-hours 0.1 2>&1 | tee logs/train_up_sanity.log
  local r=fail
  grep -q '^\[INFO\] max_hours reached, stopping' logs/train_up_sanity.log && ! grep -q '^Traceback' logs/train_up_sanity.log && r=pass
  echo "V0 $r $VENUE $GPU" >> meta/driver_state.txt
  V0_THIS_SESSION=1
}

# ------------------------------------------------------------------ pack (PLAN §8.1)
pack() {
  local cap_hit=$1 remaining=$2 tot; tot=$(hours_total)
  ls -lR logs/b0_* logs/b0lr05_* logs/attempts 2>/dev/null > meta/ckpt_dirs_ls.txt
  { echo "part=$PART"; echo "venue=$VENUE"; echo "start_utc=$SESSION_START_UTC"; echo "end_utc=$(utc)"
    echo "session_hours=$(awk -v t="$tot" -v p="$PRIOR_H" 'BEGIN{printf "%.4f", t-p}')"; echo "prior_hours=$PRIOR_H"
    echo "total_hours=$tot"; echo "spend_cap_hours=$SPEND_CAP_H"; echo "spend_cap_hit=$cap_hit"
    echo "gate_set_complete=$([ "$remaining" = none ] && echo true || echo unknown)"; echo "cells_remaining=$remaining"; } > meta/session.txt
  local suffix="" stage name
  [ "$PART" -ge 2 ] && suffix="-part$PART"
  name=b0-$(date -u +%Y%m%d-%H%M)${suffix}.tgz
  stage=$(mktemp -d /content/b0_stage.XXXX)
  mkdir -p "$stage/logs/attempts" "$stage/logs/eval"
  cp -a meta "$stage/"
  [ -n "${V0_THIS_SESSION:-}" ] && cp -a logs/train_up_sanity.log "$stage/train_up_sanity.log"
  local a d
  for a in "${SESSION_AIDS[@]}"; do
    cp -a "logs/train_${a}.log" "$stage/logs/" 2>/dev/null
    cp -a "logs/attempts/${a}" "$stage/logs/attempts/" 2>/dev/null
    [ -d "logs/eval/${a}" ] && cp -a "logs/eval/${a}" "$stage/logs/eval/"
  done
  for d in "${SESSION_DIRS[@]}"; do cp -a "$d" "$stage/logs/attempts/"; done
  find "$stage" -name '*.pt' -delete
  cp -a deviations.md "$stage/"; [ -f BLOCKED.md ] && cp -a BLOCKED.md "$stage/"
  for f in ${B0_EXTRA_FILES:-}; do cp -a "$f" "$stage/"; done            # XN-4090: job JSON, runner stdout
  if find "$stage" \( -name '*.npz' -o -path '*lafan*' -o \( -name '*.csv' ! -path '*/meta/gpumem_*.csv' \) \) | grep -q .; then
    echo "REFUSE: motion data in stage"; return 4; fi
  tar czf "$B0_OUT_DIR/$name" -C "$stage" .
  sha256sum "$B0_OUT_DIR/$name"
  log "DONE_DRIVER deposit=$B0_OUT_DIR/$name (deposit unmodified; seal before open, PLAN §8.2)"
}

main() {
  SELF=$(readlink -f "$0")
  B0_TGZ=${B0_TGZ:-/content/junior_b_colab-CR-B0-1.tgz}
  B0_OUT_DIR=${B0_OUT_DIR:-/content}
  VENUE=${B0_VENUE:-colab}
  SESSION_START=$(date +%s); SESSION_START_UTC=$(utc)
  SESSION_AIDS=(); SESSION_DIRS=(); PART=1; PRIOR_H=0
  if ! setup; then cd "$U" 2>/dev/null && pack false setup_failed; exit 1; fi
  v0_sanity
  local cap=false remaining=none line
  while :; do
    line=$("$PY" -I "$HELPER" next --state meta/driver_state.txt --total-hours "$(hours_total)" --spend-cap "$SPEND_CAP_H")
    case "$line" in
      DONE) break ;;
      SPENDCAP) cap=true; echo "SPEND_CAP_HIT $(hours_total)" >> meta/driver_state.txt
                blocked spend_cap "7 GPU wall-hours reached between cells (PLAN §9)"; remaining=see_driver_state; break ;;
      CELL*) read -r _ TAG CFG ARM SEED N NEW <<< "$line"
             train_attempt "$TAG" "$CFG" "$ARM" "$SEED" "$N" || break
             echo "SPENT $(hours_total)" >> meta/driver_state.txt ;;
      *) blocked plan_gap "helper returned: $line"; break ;;
    esac
  done
  pack "$cap" "$remaining"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
