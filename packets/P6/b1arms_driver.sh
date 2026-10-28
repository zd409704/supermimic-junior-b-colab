#!/usr/bin/env bash
# P6d B1 arms GPU driver: spikes/B1/PLAN.md §3-§8 on xn-4090-gpu2 (GPU0, mutex gpu0).
# PLAN sha256 1088752ba26a8798d721aa93d6e10d1b7bdb7fb924d9d72879acc78d8c2304c8
# Harness stop at it 1600 = spikes/B0/PLAN.md §4.3 (F-1 unsuitable, packets/P4/UPSTREAM_FACTS.md); launcher = B0 §4.2.
# Bundle layout: packets/P6/BUNDLE_CONTRACT-b1arms.md. Machine verdict: spikes/B1/verdict_b1.py on the box (OVERLAY-001 rule 6).
#
# Runner usage (launched by orch/jobs/p6-b1-arms/run.sh):
#   B1ARMS_TGZ=<tarball> B1ARMS_TARBALL_SHA=<hex> bash b1arms_driver.sh
#   Job launch 2 (PLAN §7, only after an INFRA failure of the whole job): add B1ARMS_RESUME=1; the tree, meta/ and
#   completed runs of launch 1 are kept and the spend clock continues from the last SPENT record.
# The runner chooses nothing: arm order, attempts, evals and the spend cap are fixed below.
#
# CPU mock (box only, never for scoring): B1ARMS_MOCK=1 with B1ARMS_J, B1ARMS_U, B1ARMS_OUT_DIR, B1ARMS_PY,
# B1ARMS_MOCK_ENTRY (stands in for p6_entry.py and b1_checks.py tbdump), B1ARMS_MOCK_NPZ, B1ARMS_MOCK_CKPT_ROOT,
# B1ARMS_MOCK_SRC_SHAS (file "<policy>_s<k> <sha256>" replacing the §4 identities); optional B1ARMS_MOCK_CAP_H,
# B1ARMS_MOCK_POLL_S. Skips clone, patch, uv, nvidia-smi and the data download. All B1ARMS_MOCK_* are ignored unless
# B1ARMS_MOCK=1.
set -uo pipefail

J=${B1ARMS_J:-/content/b1arms/junior}
U=${B1ARMS_U:-/content/SuperMimic-Reproduced-b1}
OUT=${B1ARMS_OUT_DIR:-/content}
MOCK=${B1ARMS_MOCK:-0}
RESUME=${B1ARMS_RESUME:-0}
PIN=d9be385b3eeb13a638fb33fb200d3bfd9be9839f
DATA_REV=ce1572906efe6157840e8474d5a0d7aa87481e74     # PLAN §3 data step, unchanged from the RT job
SPEND_CAP_H=9.0       # PLAN §7
POLL_S=30             # B0 PLAN §4.3: two checkpoint-size polls 30 s apart
STOP_WAIT_S=300       # B0 PLAN §4.3: wait up to 300 s after SIGINT
ENDPOINT_RE='^it 1600 |'
EVAL_ITS="0000160 0000320 0000480 0000640 0000800 0000960 0001120 0001280 0001440 0001600"   # PLAN §5
if [ "$MOCK" = 1 ]; then SPEND_CAP_H=${B1ARMS_MOCK_CAP_H:-$SPEND_CAP_H}; POLL_S=${B1ARMS_MOCK_POLL_S:-$POLL_S}; fi
SELF=$(readlink -f "$0")
T0=$(date +%s)
PRIOR_H=0
CAP_HIT=false

# PLAN §4 order (fixed): primary seed-major, then secondaries. Fields: arm policy init seed config src role
SCHEDULE="
H-A-scratch      attention   scratch 0 b1_home.yaml         -               primary
H-A-xfer         attention   xfer    0 b1_home.yaml         attention_s0    primary
H-M-xfer         mlp_matched xfer    0 b1_home.yaml         mlp_matched_s0  primary
H-A-scratch      attention   scratch 1 b1_home.yaml         -               primary
H-A-xfer         attention   xfer    1 b1_home.yaml         attention_s1    primary
H-M-xfer         mlp_matched xfer    1 b1_home.yaml         mlp_matched_s1  primary
H-A-scratch      attention   scratch 2 b1_home.yaml         -               primary
H-A-xfer         attention   xfer    2 b1_home.yaml         attention_s2    primary
H-M-xfer         mlp_matched xfer    2 b1_home.yaml         mlp_matched_s2  primary
H-M-scratch      mlp_matched scratch 0 b1_home.yaml         -               secondary
H-M-scratch      mlp_matched scratch 1 b1_home.yaml         -               secondary
H-M-scratch      mlp_matched scratch 2 b1_home.yaml         -               secondary
H-A-frozen       attention   frozen  0 b1_home.yaml         attention_s0    diagnostic
H-A-xfer-noscale attention   xfer    0 b1_home_noscale.yaml attention_s0    diagnostic
"

# PLAN §4 transfer identities (P4 ckpt_0001600.pt, P5-verified sha256)
src_expect() {
  if [ "$MOCK" = 1 ] && [ -n "${B1ARMS_MOCK_SRC_SHAS:-}" ]; then awk -v k="$1" '$1==k{print $2}' "$B1ARMS_MOCK_SRC_SHAS"; return; fi
  case $1 in
    attention_s0)   echo 5fb48347dd957b91de4b6780c53bd43d9f1777f56aabc3396aa7351181474a1d ;;
    attention_s1)   echo 44971f21d0f9bd3dc2abbbba4775c0597efa09c64da0db376c55eb09a7d61d68 ;;
    attention_s2)   echo c09d6b8ae4ecc9c7ced48a587869087bf8bc4803da08694bcd2c15dc233d28e5 ;;
    mlp_matched_s0) echo 9ae05d74b9813e4858904a196cffe718d95d1237b41fdd7620aa3c842001913e ;;
    mlp_matched_s1) echo 5eb302ed06aad69fe9793cc0b0f085536423c30c53e1c6ef46653fce77211da9 ;;
    mlp_matched_s2) echo 88a396ce00333b4e72b43fafefd2e62f8b83604cf185115e1f9e0a8a32fa73e1 ;;
  esac
}
src_roots() {  # read-only P4 checkpoint roots, in order (as the RT job)
  if [ "$MOCK" = 1 ]; then echo "$B1ARMS_MOCK_CKPT_ROOT"; else
    echo "/content/p5_p4ckpts /content/SuperMimic-Reproduced /data/muchuan/p4-b0-attempt1/workdir/SuperMimic-Reproduced"; fi
}

utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { echo "[b1arms_driver $(utc)] $*"; }
dev() { echo "- [driver] $(utc) $*" >> "$U/deviations.md"; }
blocked() { echo "BLOCKED_REASON=$1 detail=$2" >> "$U/BLOCKED.md"; log "BLOCKED $1: $2"; }
state() { echo "$*" >> "$U/meta/driver_state.txt"; }
hours() { awk -v s="$T0" -v p="$PRIOR_H" -v n="$(date +%s)" 'BEGIN{printf "%.4f", p + (n - s) / 3600}'; }
over_cap() { awk -v h="$(hours)" -v c="$SPEND_CAP_H" 'BEGIN{exit !(h >= c)}'; }
left_s() { awk -v h="$(hours)" -v c="$SPEND_CAP_H" 'BEGIN{s = int((c - h) * 3600); print (s > 1 ? s : 1)}'; }
dflag() { [ "$MOCK" = 1 ] && echo "--device cpu"; }
spent() { state "SPENT $(hours) $(utc)"; }

# ------------------------------------------------------------------ launcher (B0 PLAN §4.2, as packets/P4/b0_driver.sh)
# A non-interactive bash '&' job starts with SIGINT ignored, and Python keeps SIG_IGN. Setting SIG_DFL and then
# exec gives the trainer the normal KeyboardInterrupt handler, so the wrapper's finally writes the sidecar.
launch_signal_restored() {
  local logf=$1; shift
  env -u PYTHONPATH "$PY" -c 'import os,signal,sys; signal.signal(signal.SIGINT, signal.SIG_DFL); os.execv(sys.argv[1], sys.argv[1:])' \
      "$@" > "$logf" 2>&1 &
  TR=$!
}

# ------------------------------------------------------------------ harness stop (B0 PLAN §4.3) + spend-cap stop (PLAN §7)
# Usage: harness_stop <pid> <trainer log> <ckpt path> <sidecar path> <out file>. Sets HS_EXIT and CAP_STOP.
harness_stop() {
  local pid=$1 logf=$2 ckpt=$3 sidecar=$4 out=$5
  local seen=false t_line=none s1=none s2=none stable=false sent=false t_sig=none early=false waited=0 timeout=false killed=false
  CAP_STOP=false
  _poll_pair() {  # two size polls POLL_S apart; sets s1 s2 stable
    if [ -f "$ckpt" ]; then
      s1=$(stat -c %s "$ckpt"); sleep "$POLL_S"; s2=$(stat -c %s "$ckpt" 2>/dev/null || echo none)
      [ "$s1" = "$s2" ] && stable=true
    fi
  }
  while kill -0 "$pid" 2>/dev/null; do
    if ! $seen && grep -q "$ENDPOINT_RE" "$logf" 2>/dev/null; then seen=true; t_line=$(utc); fi
    if $seen; then _poll_pair; $stable && break; fi
    if ! $seen && over_cap; then CAP_STOP=true; break; fi
    sleep 5
  done
  if kill -0 "$pid" 2>/dev/null && { $stable || $CAP_STOP; }; then
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
    echo "spend_cap_stop=$CAP_STOP"
    echo "trainer_exited_before_signal=$early"; echo "exit_wait_s=$waited"; echo "harness_stop_timeout=$timeout"
    echo "sigkill_sent=$killed"; echo "exit_code=$HS_EXIT"
    echo "sidecar=$([ -f "$sidecar" ] && echo present || echo missing)"
  } >> "$out"
}

# ------------------------------------------------------------------ setup (PLAN §3)
setup() {
  local resume=false
  if [ "$RESUME" = 1 ] && [ -f "$U/meta/driver_state.txt" ]; then resume=true; fi
  if [ "$MOCK" != 1 ] && ! $resume; then
    if [ -e "$U" ]; then mv "$U" "$U.prev-$(date -u +%Y%m%d-%H%M%S)"; fi   # never reuse a previous job's tree
    git clone https://github.com/CuboiLeo/SuperMimic-Reproduced "$U" || { mkdir -p "$U/meta"; blocked setup_failed "git clone"; return 3; }
    git -C "$U" checkout -q "$PIN" && [ "$(git -C "$U" rev-parse HEAD)" = "$PIN" ] || { mkdir -p "$U/meta"; blocked setup_failed "upstream HEAD != $PIN"; return 3; }
  fi
  if ! $resume && [ "$RESUME" = 1 ]; then echo "B1ARMS_RESUME=1 but no $U/meta/driver_state.txt; fresh start" >&2; fi
  mkdir -p "$U"; cd "$U" || return 3
  if ! $resume; then
    if [ "$MOCK" = 1 ] && [ -e meta ]; then mkdir -p meta; blocked plan_gap "mock tree $U not empty"; return 3; fi
    mkdir -p meta logs; : > deviations.md; : > meta/driver_state.txt
  fi
  exec > >(tee -a meta/driver.log) 2>&1
  PART=$(( $(grep -c '^PART ' meta/driver_state.txt) + 1 ))
  PRIOR_H=$(awk '$1=="SPENT"{h=$2} END{printf "%.4f", h+0}' meta/driver_state.txt)
  state "PART $PART $(utc) resume=$resume mock=$MOCK prior_hours=$PRIOR_H"
  log "start part=$PART resume=$resume mock=$MOCK J=$J U=$U prior_hours=$PRIOR_H cap=$SPEND_CAP_H"
  echo "part=$PART driver_sha256=$(sha256sum "$SELF" | cut -c1-64)" >> meta/driver_identity.txt

  # tarball identity before unpacking; the running driver must equal the tarball copy
  [ -n "${B1ARMS_TARBALL_SHA:-}" ] && [ -f "${B1ARMS_TGZ:-/nonexistent}" ] || { blocked tarball_sha_mismatch "B1ARMS_TARBALL_SHA or B1ARMS_TGZ unset/missing"; return 4; }
  echo "part=$PART $(sha256sum "$B1ARMS_TGZ")" >> meta/tarball_sha256.txt
  [ "$(sha256sum "$B1ARMS_TGZ" | cut -c1-64)" = "$B1ARMS_TARBALL_SHA" ] || { blocked tarball_sha_mismatch "$(tail -1 meta/tarball_sha256.txt)"; return 4; }
  rm -rf "$J" && mkdir -p "$J" && tar xzf "$B1ARMS_TGZ" -C "$J"
  cmp -s "$SELF" "$J/packets/P6/b1arms_driver.sh" || { blocked plan_gap "running driver differs from the tarball copy"; return 4; }
  (cd "$J" && sha256sum -c packets/P6/MANIFEST-b1arms.sha256 > "$U/meta/manifest_check_part$PART.txt" 2>&1) || { blocked tarball_sha_mismatch "manifest check"; return 4; }
  [ "$(sha256sum "$J/spikes/B1/PLAN.md" | cut -c1-64)" = 1088752ba26a8798d721aa93d6e10d1b7bdb7fb924d9d72879acc78d8c2304c8 ] || { blocked plan_gap "PLAN.md sha in tarball"; return 4; }

  if [ "$MOCK" != 1 ]; then
    if $resume; then
      [ "$(git -C "$U" rev-parse HEAD)" = "$PIN" ] || { blocked setup_failed "resume: upstream HEAD != $PIN"; return 5; }
      patch -R -p1 --dry-run < "$J/packets/P6/upstream-b1.patch" > "meta/patch_check_part$PART.txt" 2>&1 || { blocked setup_failed "resume: upstream-b1.patch not applied"; return 5; }
      [ -x "$U/.venv/bin/python" ] || { blocked setup_failed "resume: .venv missing"; return 5; }
    else
      patch -p1 --dry-run < "$J/packets/P6/upstream-b1.patch" > meta/patch_dryrun.txt 2>&1 || { blocked setup_failed "upstream-b1.patch dry run"; return 5; }
      patch -s -p1 < "$J/packets/P6/upstream-b1.patch" || { blocked setup_failed "upstream-b1.patch apply"; return 5; }
    fi
    unset PYTHONPATH
    PY=$U/.venv/bin/python
    if ! $resume; then
      uv sync && uv pip install --python .venv/bin/python pyyaml huggingface_hub || { blocked setup_failed "uv sync"; return 5; }
      if ! $PY -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)"; then   # R1 fallback, as P4 runbook §2
        TV=$($PY -c "import torch;print(torch.__version__.split('+')[0])")
        uv pip install --python "$PY" "torch==$TV" --index-url https://download.pytorch.org/whl/cu128 --reinstall
        uv pip install --python "$PY" warp-lang --reinstall
        dev "R1 wheel substitution (P4 runbook §2): torch==$TV from cu128 index, PyPI warp-lang"
      fi
    fi
    $PY -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)" || { blocked R1_unresolved "cuda unavailable"; return 6; }
    nvidia-smi > "meta/nvidia-smi_part$PART.txt" 2>&1
    # PLAN §6 B1-V-5: the used device. *.csv is excluded from the bundle (PLAN §8), so a byte copy is kept as .csv.txt
    nvidia-smi -i "${CUDA_VISIBLE_DEVICES:-0}" --query-gpu=index,uuid,name --format=csv > meta/gpu_used.csv 2>&1
    cp -f meta/gpu_used.csv meta/gpu_used.csv.txt
    uv pip freeze --python "$PY" > "meta/pip-freeze_part$PART.txt"
    ENTRY=("$J/packets/P6/b1/p6_entry.py"); TBDUMP=("$J/packets/P6/b1/b1_checks.py" tbdump)
  else
    PY=$(command -v "${B1ARMS_PY:?}")   # absolute: the launcher execv()s it
    printf 'index, uuid, name\n0, GPU-mock, MOCK CPU\n' > meta/gpu_used.csv; cp -f meta/gpu_used.csv meta/gpu_used.csv.txt
    ENTRY=("${B1ARMS_MOCK_ENTRY:?}"); TBDUMP=("$B1ARMS_MOCK_ENTRY" tbdump)
    dev "MOCK part $PART: trainer/eval/tbdump = $B1ARMS_MOCK_ENTRY; cap=$SPEND_CAP_H h poll=$POLL_S s"
  fi
  echo "part=$PART CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}" >> meta/gpu_env.txt
  $PY -c "import torch, mujoco; print('cuda', torch.cuda.is_available(), torch.__version__, 'mujoco', mujoco.__version__)" \
      >> meta/torch_cuda.txt 2>&1 || echo "part=$PART torch/mujoco import failed" >> meta/torch_cuda.txt
  B1=$J/packets/P6/b1
  HELPER=$B1/b1arms_helper.py
  export SM_BODY_MODULE=sm_body_home
  printf '%s\n' "$SCHEDULE" | awk 'NF' > meta/schedule.txt
  return 0
}

# ------------------------------------------------------------------ data (PLAN §3: the RT job's data step, unchanged; X-002)
data_step() {
  if grep -q '^DATA ok' meta/driver_state.txt && [ "$(ls data/npz/b1_home/*.npz 2>/dev/null | wc -l)" -eq 4 ]; then
    log "data step already passed in an earlier part"; return 0
  fi
  if [ "$MOCK" = 1 ]; then
    mkdir -p data/npz/b1_home && cp "$B1ARMS_MOCK_NPZ"/*.npz data/npz/b1_home/
    printf '{"mock": true, "pass": true, "slot_rule": "first", "csv_sha_mismatch": [], "used_clips": ["walk1_subject1", "run1_subject2", "dance1_subject1", "jumps1_subject1"]}\n' > meta/b1_data_qa.json
    dev "MOCK data step (synthetic npz)"; state "DATA ok"; return 0
  fi
  $PY "$B1/prepare_b1_data.py" --rev "$DATA_REV" --out-npz data/npz/b1_home --qa-out meta/b1_data_qa.json \
      --expect "$J/spikes/B1-RT/results-cpu-attempt1.json" --slot-rule first 2>&1 | tee -a logs/data_step.log
  local rc=${PIPESTATUS[0]}
  [ "$rc" -eq 0 ] || { blocked data_step "prepare_b1_data exit $rc (see meta/b1_data_qa.json)"; return 8; }
  [ "$(ls data/npz/b1_home/*.npz 2>/dev/null | wc -l)" -eq 4 ] || { blocked data_step "expected 4 npz"; return 8; }
  state "DATA ok"
}

# ------------------------------------------------------------------ eval (PLAN §5: 10 points, mask 0.0, one re-execution)
eval_run() { local aid=$1 run=$2 cfg=$3 it k d rc
  for it in $EVAL_ITS; do
    for k in 1 2; do
      d=logs/eval/$aid/it$it/exec$k
      # resumed part: a point already scored is kept; an exec dir from a lost part counts as used (no JSON = failed)
      if [ -f "$d/eval.log" ]; then
        if grep -q '^exit=0$' "$d/eval.log" && [ "$(ls "$d"/*_mask0.00.json 2>/dev/null | wc -l)" -eq 1 ]; then break; fi
        continue
      fi
      if over_cap; then CAP_HIT=true; echo "eval_it$it=spend_cap" >> "meta/attempt_${aid}.txt"; return 9; fi
      mkdir -p "$d"
      timeout --signal=INT --kill-after=60 "$(left_s)" "$PY" "${ENTRY[@]}" eval --config "$cfg" \
          --ckpt "logs/$run/ckpt_$it.pt" --out-dir "$d" --masks 0.0 $(dflag) > "$d/eval.log" 2>&1 < /dev/null
      rc=$?; echo "exit=$rc" >> "$d/eval.log"
      if [ "$rc" -eq 124 ] && over_cap; then CAP_HIT=true; echo "eval_it$it=spend_cap" >> "meta/attempt_${aid}.txt"; return 9; fi
      if [ "$rc" -eq 0 ] && [ "$(ls "$d"/*_mask0.00.json 2>/dev/null | wc -l)" -eq 1 ]; then break; fi
      [ "$k" -eq 1 ] && dev "eval $aid it$it exec1 exit=$rc or no JSON: one re-execution (PLAN §5)"
    done
  done
  return 0
}

# evals (completed only), archive without *.pt, state records. Returns 9 on the spend cap, 1 = try next attempt.
finish_attempt() { local aid=$1 run=$2 cfg=$3 cls=$4 done_=$5 t_start=$6 rc=0
  if [ "$cls" = COMPLETED ]; then
    eval_run "$aid" "$run" "$cfg"; rc=$?
    echo "evals=$([ $rc -eq 0 ] && echo done || echo spend_cap)" >> "meta/attempt_${aid}.txt"
  fi
  mkdir -p "logs/attempts/$aid"
  [ -d "logs/$run" ] && tar -C "logs/$run" --exclude='*.pt' -cf - . | tar -C "logs/attempts/$aid" -xf -
  state "ATTEMPT $aid $cls $done_"; spent
  case $cls in
    COMPLETED)
      if [ "$rc" -ne 0 ]; then blocked spend_cap "during evals of $aid at $(hours) h"; state "RUNDONE $run SPEND_CAP"; return 9; fi
      state "DUR $run $(awk -v s="$t_start" -v n="$(date +%s)" 'BEGIN{printf "%.4f", (n - s) / 3600}')"
      state "RUNDONE $run COMPLETED"; return 0 ;;
    NONFINITE) dev "$aid became non-finite: a result, not an INFRA failure (PLAN §7)"; state "RUNDONE $run NONFINITE"; return 0 ;;
    SPEND_CAP) CAP_HIT=true; blocked spend_cap "$aid stopped by the spend cap at $(hours) h"; state "RUNDONE $run SPEND_CAP"; return 9 ;;
    *) dev "$aid INFRA failure (exit ${HS_EXIT:-na}) before the endpoint"; return 1 ;;
  esac
}

# ------------------------------------------------------------------ one run, at most 2 attempts (PLAN §4, §7)
max_dur() { awk '$1=="DUR"{if ($3 > m) m = $3} END{if (m > 0) printf "%.4f", m}' meta/driver_state.txt; }

run_arm() { local arm=$1 pol=$2 init=$3 seed=$4 cfgname=$5 src=$6 role=$7
  local tag=b1${arm//-/} run cfg n aid prev t_start est srcpath rc
  run=${tag}_${pol}_s${seed}; cfg=$J/packets/P6/configs/$cfgname
  if grep -q "^RUNDONE $run " meta/driver_state.txt; then log "skip $run ($(grep "^RUNDONE $run " meta/driver_state.txt | tail -1))"; return 0; fi
  n=$(( $(grep -c "^ATTEMPT ${run}_a" meta/driver_state.txt) + 1 ))
  # a previous job part was lost inside attempt n (no ATTEMPT record; PLAN §7 session loss)
  if [ -f "meta/attempt_${run}_a${n}.txt" ]; then
    aid=${run}_a${n}
    if grep -q '^class=COMPLETED' "meta/attempt_${aid}.txt"; then   # lost during evals: the run itself is complete
      dev "$aid: previous part lost during evals; resuming the missing eval points"
      echo "resumed_evals_part=$PART" >> "meta/attempt_${aid}.txt"
      finish_attempt "$aid" "$run" "$cfg" COMPLETED true "$(date +%s)"; return $?
    fi
    echo "class=INFRA reason=session_loss_previous_part" >> "meta/attempt_${aid}.txt"
    mkdir -p "logs/attempts/$aid"; [ -d "logs/$run" ] && tar -C "logs/$run" --exclude='*.pt' -cf - . | tar -C "logs/attempts/$aid" -xf -
    state "ATTEMPT $aid INFRA false session_loss"; dev "$aid lost with the previous job part: INFRA (session loss)"
    n=$((n + 1))
  fi
  while [ "$n" -le 2 ]; do
    aid=${run}_a${n}
    if [ "$role" = primary ]; then
      if over_cap; then CAP_HIT=true; blocked spend_cap "before $aid at $(hours) h (cap $SPEND_CAP_H)"; state "RUNDONE $run SPEND_CAP"; return 9; fi
    else
      est=$(max_dur)
      if [ -z "$est" ] || awk -v h="$(hours)" -v e="$est" -v c="$SPEND_CAP_H" 'BEGIN{exit !(h + e > c)}'; then
        log "no room for $aid ($role) at $(hours) h, est ${est:-none} h, cap $SPEND_CAP_H"
        echo "$run skipped_no_room hours=$(hours) est=${est:-none} cap=$SPEND_CAP_H" >> meta/schedule_skips.txt
        state "RUNDONE $run SKIPPED_NO_ROOM"; return 0
      fi
    fi
    srcpath=""
    if [ "$init" != scratch ]; then
      local exp cands="" r
      exp=$(src_expect "$src")
      for r in $(src_roots); do cands="$cands $r/logs/b0_${src%_s*}_s${src##*_s}/ckpt_0001600.pt"; done
      echo "aid=$aid src=$src" >> "meta/src_ckpt_${aid}.txt"
      if ! srcpath=$("$PY" -I "$HELPER" srcsha --expect "${exp:-none}" --out "meta/src_ckpt_${aid}.txt" $cands); then
        blocked src_ckpt_mismatch "$aid: no candidate of $src has sha256 ${exp:-none} (meta/src_ckpt_${aid}.txt)"
        state "RUNDONE $run SRC_MISMATCH"; return 0
      fi
    fi
    if [ "$n" -ge 2 ] && [ -d "logs/$run" ]; then
      prev=${run}_a$((n - 1)); mkdir -p attempts-live && mv "logs/$run" "attempts-live/$prev"   # fresh run dir; *.pt stay off-bundle
    elif [ -e "logs/$run" ]; then
      blocked plan_gap "logs/$run exists before $aid"; state "RUNDONE $run NOT_COMPLETED"; return 0
    fi
    t_start=$(date +%s)
    { echo "aid=$aid"; echo "arm=$arm"; echo "policy=$pol"; echo "init=$init"; echo "seed=$seed"; echo "role=$role"
      echo "attempt=$n"; echo "config=$cfgname"; echo "src_key=$src"; echo "src_ckpt=${srcpath:-none}"
      echo "start_utc=$(utc)"; echo "hours_at_start=$(hours)"; } > "meta/attempt_${aid}.txt"
    echo "aid=$aid" > "meta/harness_stop_${aid}.txt"
    [ "$MOCK" != 1 ] && nvidia-smi -i "${CUDA_VISIBLE_DEVICES:-0}" --query-gpu=index,uuid,name --format=csv,noheader \
        | sed "s/^/$aid /" >> meta/gpu_used_attempts.txt 2>&1
    local SMI=""
    if [ "$MOCK" != 1 ]; then
      nvidia-smi --query-gpu=timestamp,memory.used,memory.total --format=csv -l 30 > "meta/gpumem_${aid}.txt" 2>/dev/null & SMI=$!
    fi
    local xargs_=()
    [ -n "$srcpath" ] && xargs_=(--src-ckpt "$srcpath")
    launch_signal_restored "logs/train_${aid}.log" "$PY" "${ENTRY[@]}" train --config "$cfg" --policy "$pol" --seed "$seed" \
        --init "$init" "${xargs_[@]}" --run-tag "$tag" $(dflag) < /dev/null
    log "started $aid pid=$TR ($role, $(hours) h)"
    harness_stop "$TR" "logs/train_${aid}.log" "logs/$run/ckpt_0001600.pt" "logs/$run/junior_policy.json" "meta/harness_stop_${aid}.txt"
    [ -n "$SMI" ] && { kill "$SMI" 2>/dev/null; wait "$SMI" 2>/dev/null; }
    grep -q '^harness_stop=true' "meta/harness_stop_${aid}.txt" && ! $CAP_STOP && dev "harness stop (B0 PLAN §4.3, SIGINT) used for $aid"
    { echo "end_utc=$(utc)"; echo "exit_code=$HS_EXIT"; } >> "meta/attempt_${aid}.txt"
    "$PY" "${TBDUMP[@]}" --run-dir "logs/$run" --out "meta/tb_${aid}.json" > "logs/tbdump_${aid}.log" 2>&1
    local cls done_
    read -r cls done_ < <("$PY" -I "$HELPER" classify --aid "$aid" --log "logs/train_${aid}.log" --tb-json "meta/tb_${aid}.json" \
        --harness "meta/harness_stop_${aid}.txt" --sidecar "logs/$run/junior_policy.json" $($CAP_STOP && echo --spend-cap-stop))
    echo "class=$cls completed=$done_" >> "meta/attempt_${aid}.txt"
    log "$aid class=$cls completed=$done_ exit=$HS_EXIT"
    finish_attempt "$aid" "$run" "$cfg" "$cls" "$done_" "$t_start"; rc=$?
    [ "$rc" -eq 1 ] && { n=$((n + 1)); continue; }
    return "$rc"
  done
  state "RUNDONE $run NOT_COMPLETED"; return 0
}

# ------------------------------------------------------------------ bundle (PLAN §8)
bundle() {
  cd "$U" 2>/dev/null || { mkdir -p "$U/meta" && cd "$U"; }
  mkdir -p meta extras
  [ -f meta/driver_state.txt ] && spent
  echo "spent_hours=$(hours) cap=$SPEND_CAP_H cap_hit=$CAP_HIT end_utc=$(utc) state=$1" >> meta/spend.txt
  for f in ${B1ARMS_EXTRA_FILES:-}; do [ -f "$f" ] && cp -p "$f" extras/; done
  local B="$OUT/b1arms-$(date -u +%Y%m%d-%H%M).tgz" items="meta logs deviations.md extras"
  [ -f BLOCKED.md ] && items="$items BLOCKED.md"
  # live run dirs logs/b1*_s<seed> hold the *.pt; their non-pt content is in logs/attempts/<AID>
  tar --exclude='*.pt' --exclude='*.npz' --exclude='*.csv' --exclude='logs/b1H*_s[0-9]' -czf "$B" $items 2>/dev/null
  log "BUNDLE $B sha256=$(sha256sum "$B" | cut -c1-64)"
  echo "DONE_DRIVER utc=$(utc) bundle=$B state=$1"
}

main() {
  if ! setup; then bundle BLOCKED; return 0; fi
  if ! data_step; then bundle BLOCKED; return 0; fi
  local line
  while read -r line <&3; do
    [ -z "$line" ] && continue
    # shellcheck disable=SC2086
    run_arm $line || break
  done 3< meta/schedule.txt
  bundle "$([ -f BLOCKED.md ] && echo BLOCKED || echo DONE)"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
