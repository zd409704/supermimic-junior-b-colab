#!/usr/bin/env bash
# P5 B2 driver (CR-B2-1 (e)). Implements spikes/B2/PLAN.md §4 and writes the §9.1 bundle.
# PLAN sha256 5d1f26f776a3ea56c2becd3ec2fa2cf8e88bd62c43a20f79415a96e82a3da11d. Bundle detail: packets/P5/BUNDLE_CONTRACT.md.
# Reuses launch_signal_restored + harness_stop from the CR-B0-1 driver (packets/P4/b0_driver.sh, sourced; its main does
# not run when sourced). setup checks that the sourced copy is byte-identical to the tarball's.
#
# Runner usage (XN-4090-GPU2, via orch/jobs/p5-b2-attempt1/run.sh, which extracts both drivers from the tarball):
#   B2_TGZ=/content/junior_b_colab-CR-B2-1.tgz B2_TARBALL_SHA=<sealed hash> B2_P4_DRIVER=/content/p5_b2/b0_driver.sh \
#     bash /content/p5_b2/b2_driver.sh
# Optional: B2_STATE_IN=<previous meta/driver_state.txt> (new session part), B2_OUT_DIR=/content, B2_EXTRA_FILES.
# The runner chooses nothing: order, attempts and retries come from b2_driver_helper.py `next`.
#
# Write scope (PLAN §9.3): in the P4 upstream tree only logs/b2*, logs/eval/b2*, logs/attempts/b2* (plus the venv /
# motion-data setup of B0 PLAN §4.1, as P4 did); the staged copies under /content/p5_p4ckpts/; driver bookkeeping under
# /content/p5_b2/. Nothing under logs/b0_* is written, moved or deleted.

B2_P4_DRIVER=${B2_P4_DRIVER:-/content/p5_b2/b0_driver.sh}
# shellcheck source=../P4/b0_driver.sh
source "$B2_P4_DRIVER" || { echo "[b2_driver] cannot source $B2_P4_DRIVER"; exit 3; }

J=/content/junior
U=/content/SuperMimic-Reproduced
W=/content/p5_b2
STAGE=/content/p5_p4ckpts
P4_ROOTS=(/content/SuperMimic-Reproduced /data/muchuan/p4-b0-attempt1/workdir/SuperMimic-Reproduced)  # PLAN §2.2, in order
HELPER=$J/packets/P5/b2_driver_helper.py
SPEND_CAP_H=6        # PLAN §10
EXPECT_GPU=NVIDIA_GeForce_RTX_4090
# PLAN §2.2: <P4 AID> <ckpt_0001600.pt bytes> <sidecar sha256>
P4_EXPECT=(
  "b0_attention_s0_a1 164415878 cc9cac5864d7845578975e2dd3883b53ea8705201ae7a9de55ac0abdadaa2767"
  "b0_attention_s1_a1 164415878 9085130f54e0ff9d568f075b7b2439d53c02a9437c8352a66fea64fcb2b30d09"
  "b0_attention_s2_a1 164415878 b84b39c174c1a18895b7f66118976039fdaec8c7304c788453c3f951f752edae"
  "b0_mlp_matched_s0_a1 164427663 e08618782fbf5ca107a74bd81494194055fbd50edb43b8eb528b134bbdca370a"
  "b0_mlp_matched_s1_a1 164427663 9a8a0e443aae59ab55ca82621892804c0ad5f1807302231df6c3a89b4dee83d0"
  "b0_mlp_matched_s2_a1 164427663 365096f41c67c789a7d9efc94c630ee259dc10ca5a2070a12cfc3c3098dd1641"
)

utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { echo "[b2_driver $(utc)] $*"; }
dev() { echo "- [driver] $(utc) $*" >> "$W/deviations.md"; }
blocked() { echo "BLOCKED_REASON=$1 detail=$2" >> "$W/BLOCKED.md"; log "BLOCKED $1: $2"; }
state() { echo "$*" >> "$W/meta/driver_state.txt"; }

# ------------------------------------------------------------------ driver work dir and session part
b2_init() {
  mkdir -p "$W"
  local stamp state_in=""; stamp=$(date -u +%Y%m%d-%H%M%S)
  if [ -n "${B2_STATE_IN:-}" ]; then   # copied before the directories rotate (the file may live in $W/meta)
    state_in=$(mktemp "$W/state_in.XXXX") && cp "$B2_STATE_IN" "$state_in" \
      || { echo "[b2_driver] cannot read B2_STATE_IN=$B2_STATE_IN"; exit 3; }
  fi
  [ -d "$W/meta" ] && mv "$W/meta" "$W/meta.prev-$stamp"
  [ -d "$W/logs" ] && mv "$W/logs" "$W/logs.prev-$stamp"
  [ -f "$W/deviations.md" ] && mv "$W/deviations.md" "$W/deviations.prev-$stamp.md"
  [ -f "$W/BLOCKED.md" ] && mv "$W/BLOCKED.md" "$W/BLOCKED.prev-$stamp.md"
  mkdir -p "$W/meta" "$W/logs"; : > "$W/deviations.md"
  exec > >(tee -a "$W/meta/driver.log") 2>&1
  exec 3>&1   # the driver log; the termination trap writes here even when it fires inside a redirected function
  [ -n "$state_in" ] && mv "$state_in" "$W/meta/driver_state.txt"
  touch "$W/meta/driver_state.txt"
  PART=$(( $(grep -c '^PART ' "$W/meta/driver_state.txt") + 1 ))
  PRIOR_H=$(awk '$1=="SPENT"{h=$2} END{printf "%.4f", h+0}' "$W/meta/driver_state.txt")
  state "PART $PART $(utc)"
  [ "$PART" -ge 2 ] && dev "session restart: part $PART continues from driver_state (prior_hours=$PRIOR_H)"
  return 0
}

# ------------------------------------------------------------------ step 0: P4 checkpoint staging (PLAN §4.1 step 0)
b2_stage() {
  local f=$W/meta/p4_ckpt_identity.txt root="" r ok det row aid size sha run s h
  echo "# P4 checkpoint identity (PLAN §2.2 / §4.1 step 0), $(utc)" > "$f"
  for r in "${P4_ROOTS[@]}"; do
    ok=true; det=""
    for row in "${P4_EXPECT[@]}"; do
      read -r aid size sha <<< "$row"; run=${aid%_a1}
      s=$(stat -c %s "$r/logs/$run/ckpt_0001600.pt" 2>/dev/null || echo none)
      h=$(sha256sum "$r/logs/$run/junior_policy.json" 2>/dev/null | cut -c1-64); h=${h:-none}
      if [ "$s" != "$size" ] || [ "$h" != "$sha" ]; then ok=false; det="$det $aid:size=$s,sidecar=$h"; fi
    done
    echo "candidate_root=$r match=$ok${det:+ mismatch:$det}" >> "$f"
    if $ok; then root=$r; break; fi
  done
  if [ -z "$root" ]; then
    echo "root=none" >> "$f"; blocked p4_ckpts_unavailable "no PLAN §2.2 candidate root holds all six checkpoints"; return 1
  fi
  echo "root=$root" >> "$f"
  rm -rf "$STAGE"
  local src=() dst=()
  for row in "${P4_EXPECT[@]}"; do
    read -r aid size sha <<< "$row"; run=${aid%_a1}
    mkdir -p "$STAGE/logs/$run"
    cp -p "$root/logs/$run/ckpt_0001600.pt" "$root/logs/$run/junior_policy.json" "$STAGE/logs/$run/"
    src+=("$root/logs/$run/ckpt_0001600.pt" "$root/logs/$run/junior_policy.json")
    dst+=("$STAGE/logs/$run/ckpt_0001600.pt" "$STAGE/logs/$run/junior_policy.json")
  done
  { echo "## ls -l source"; ls -l "${src[@]}"; echo "## ls -l copy"; ls -l "${dst[@]}"
    echo "## sha256 source"; sha256sum "${src[@]}"; echo "## sha256 copy"; sha256sum "${dst[@]}"; } >> "$f"
  local eq=true
  [ "$(sha256sum "${src[@]}" | cut -c1-64)" = "$(sha256sum "${dst[@]}" | cut -c1-64)" ] || eq=false
  echo "copy_equals_source=$eq" >> "$f"
  $eq || { blocked p4_ckpts_unavailable "staged copy sha256 != source sha256"; return 1; }
  return 0
}

# ------------------------------------------------------------------ step 1: setup (PLAN §4.1 step 1 = B0 PLAN §4.1 without V-0)
b2_setup() {
  [ -n "${B2_TARBALL_SHA:-}" ] || { blocked tarball_sha_mismatch "B2_TARBALL_SHA not set"; return 4; }
  [ -f "$B2_TGZ" ] || { blocked tarball_sha_mismatch "missing $B2_TGZ"; return 4; }
  sha256sum "$B2_TGZ" > "$W/meta/tarball_sha256.txt"
  [ "$(cut -c1-64 "$W/meta/tarball_sha256.txt")" = "$B2_TARBALL_SHA" ] || { blocked tarball_sha_mismatch "$(cat "$W/meta/tarball_sha256.txt")"; return 4; }
  rm -rf "$J" && mkdir -p "$J" && tar xzf "$B2_TGZ" -C "$J"
  cmp -s "$SELF" "$J/packets/P5/b2_driver.sh" || { blocked plan_gap "running driver differs from the tarball copy"; return 4; }
  cmp -s "$B2_P4_DRIVER" "$J/packets/P4/b0_driver.sh" || { blocked plan_gap "sourced CR-B0-1 driver differs from the tarball copy"; return 4; }

  pip install -q uv
  if [ -d "$U/.git" ]; then
    [ "$(git -C "$U" rev-parse HEAD)" = "$PIN" ] || { blocked plan_gap "existing $U HEAD != pin $PIN (not modified)"; return 3; }
    dev "reuse of the existing upstream clone at the pin ($U, HEAD=$PIN; PLAN §9.3)"
  elif [ -e "$U" ]; then
    blocked plan_gap "$U exists but is not a git clone (not modified)"; return 3
  else
    git clone https://github.com/CuboiLeo/SuperMimic-Reproduced "$U" && git -C "$U" checkout "$PIN" || { blocked setup_failed "clone"; return 3; }
    [ "$(git -C "$U" rev-parse HEAD)" = "$PIN" ] || { blocked setup_failed "upstream HEAD != pin"; return 3; }
  fi
  cd "$U" || return 3
  uv sync && uv pip install --python .venv/bin/python pyyaml huggingface_hub || { blocked setup_failed "uv sync"; return 5; }
  PY=$U/.venv/bin/python
  if ! $PY -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)"; then   # R1 fallback, runbook §2
    TV=$($PY -c "import torch;print(torch.__version__.split('+')[0])")
    uv pip install --python "$PY" "torch==$TV" --index-url https://download.pytorch.org/whl/cu128 --reinstall
    uv pip install --python "$PY" warp-lang --reinstall
    dev "R1 wheel substitution (runbook §2): torch==$TV from cu128 index, PyPI warp-lang"
    $PY -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)" || { blocked R1_unresolved "cuda unavailable after fallback"; return 6; }
  fi
  $PY -c "import torch; print('cuda', torch.cuda.is_available(), torch.__version__)" > "$W/meta/torch_cuda.txt"

  # CPU tests (runbook §3, frozen 14-test smoke; gate as in P4). The P5 prep tests are run and recorded, not gated.
  (cd "$J" && $PY code/tests/test_smoke.py) > "$W/meta/cpu_test_smoke.log" 2>&1
  (cd "$J" && $PY packets/P5/tests/test_p5_prep.py) > "$W/meta/cpu_test_p5.log" 2>&1; echo "exit=$?" >> "$W/meta/cpu_test_p5.log"
  $PY -I "$HELPER" cputest --log "$W/meta/cpu_test_smoke.log" --out "$W/meta/cpu_test_check.txt" \
      || { blocked cpu_test_mismatch "$(cat "$W/meta/cpu_test_check.txt")"; return 7; }

  # motion data on the runtime only (runbook §4), HF mirror (PLAN §9.3)
  echo "HF_ENDPOINT=${HF_ENDPOINT:-unset} HF_HUB_ENABLE_HF_TRANSFER=${HF_HUB_ENABLE_HF_TRANSFER:-unset}"
  [ -n "${HF_ENDPOINT:-}" ] && dev "HF_ENDPOINT=$HF_ENDPOINT for the motion download (PLAN §9.3)"
  SUB=$($PY -c "import yaml;print(yaml.safe_load(open('$J/configs/colab_smoke.yaml'))['upstream']['dataset_subdir'])")
  $PY - <<EOF || { blocked setup_failed "motion data download"; return 8; }
import yaml; from huggingface_hub import snapshot_download
c = yaml.safe_load(open('$J/configs/colab_smoke.yaml'))['upstream']
snapshot_download(c['dataset_repo'], repo_type='dataset', local_dir='data/raw/lafan1',
                  allow_patterns=[f"{c['dataset_subdir']}/{n}.csv" for n in c['clips']])
EOF
  env -u PYTHONPATH $PY scripts/data/csv_to_npz_batch.py --input-dir data/raw/lafan1/$SUB \
      --output-dir data/npz/lafan1_smoke --input-fps 30 --workers 2 || { blocked setup_failed "csv_to_npz"; return 8; }
  [ "$(ls data/npz/lafan1_smoke/*.npz 2>/dev/null | wc -l)" -eq 4 ] || { blocked setup_failed "expected 4 npz"; return 8; }

  nvidia-smi > "$W/meta/nvidia-smi.txt"
  uv pip freeze --python "$PY" > "$W/meta/pip-freeze.txt"
  diff -u "$J/packets/P5/p4_pip_freeze_ref.txt" "$W/meta/pip-freeze.txt" > "$W/meta/env_drift.txt"
  [ -s "$W/meta/env_drift.txt" ] && log "env_drift: pip freeze differs from the P4 deposit's (meta/env_drift.txt)"
  GPU=$($PY -I "$HELPER" gpuname --smi "$W/meta/nvidia-smi.txt")
  [ "$GPU" = "$EXPECT_GPU" ] || { blocked plan_gap "GPU $GPU is not $EXPECT_GPU (PLAN §9.3, B2-V-2(c))"; return 9; }
  return 0
}

# Eval / PERM children run in the background and are waited for, so a termination trap fires at once (b2_abort).
b2_child() { "$@" & CHILD=$!; wait "$CHILD"; local rc=$?; CHILD=""; return $rc; }

# ------------------------------------------------------------------ one eval of one checkpoint (PLAN §4.2 eval cells, §4.3)
# Usage: b2_eval <ID> <IT> <ckpt> <cfg> <full|mask0> <run> <arm>. exec2 only if exec1 failed; never a third.
b2_eval() { local ID=$1 IT=$2 CKPT=$3 CFG=$4 MODE=$5 RUN=$6 ARM=$7 K D extra=""
  [ "$MODE" = mask0 ] && extra=--mask0-only
  local rc
  for K in 1 2; do
    D=logs/eval/$ID/it$IT/exec$K
    if [ ! -e "$D" ]; then
      mkdir -p "$D"; CUR_EVAL_LOG=$D/eval.log
      b2_child env -u PYTHONPATH $PY $J/packets/P5/p5_eval_entry.py --config "$CFG" --ckpt "$CKPT" --out-dir "$D" $extra \
          > "$D/eval.log" 2>&1; echo "exit=$?" >> "$D/eval.log"; CUR_EVAL_LOG=""
    fi   # else: session restart, an existing exec is never rerun
    $PY -I "$HELPER" evalcheck --dir "$D" --run "$RUN" --arm "$ARM" --mode "$MODE"; rc=$?
    [ "$rc" -eq 0 ] && { EVAL_K=$K; return 0; }
    [ "$rc" -eq 1 ] || break   # 2: a next exec is not authorized (PLAN §4.2)
  done
  EVAL_K=none; return 1
}

b2_perm() { local ID=$1 CKPT=$2 CFG=$3 ROLE=$4 rc
  b2_child env -u PYTHONPATH $PY $J/packets/P5/perm_check.py --mode upstream --config "$CFG" --ckpt "$CKPT" --id "$ID" \
      --role "$ROLE" --out "$W/meta/perm_$ID.json" > "$W/logs/perm_$ID.log" 2>&1; rc=$?
  echo "exit=$rc" >> "$W/logs/perm_$ID.log"; tail -n 2 "$W/logs/perm_$ID.log"
  state "PERM $ID $rc"
}

# ------------------------------------------------------------------ steps 2-3: U evals and PERM on the staged P4 checkpoints
b2_ueval() { local AID=$1 run=${1%_a1} arm
  arm=${run#b0_}; arm=${arm%_s[0-9]}
  SESSION_EVALS+=("b2u_$AID")   # registered before launch: an aborted eval is still deposited
  b2_eval "b2u_$AID" 0001600 "$STAGE/logs/$run/ckpt_0001600.pt" "$J/configs/b0_microbench.yaml" full "$run" "$arm"
  local r=$?; state "UEVAL $AID $([ $r -eq 0 ] && echo ok || echo fail) exec$EVAL_K"
}

b2_uperm() { local AID=$1 run=${1%_a1} role=report
  case $AID in b0_attention_*) role=gate ;; esac
  b2_perm "b2u_$AID" "$STAGE/logs/$run/ckpt_0001600.pt" "$J/configs/b0_microbench.yaml" "$role"
}

# ------------------------------------------------------------------ steps 4-5: one training attempt (PLAN §4.2 = B0 §3.3)
b2_train_attempt() { TAG=$1; CFG=$2; ARM=$3; SEED=$4; N=$5; AID=${TAG}_${ARM}_s${SEED}_a${N}
  RUN=${TAG}_${ARM}_s${SEED}
  if [ "$N" -ge 2 ] && [ -d "logs/${RUN}" ]; then
    mkdir -p logs/attempts && mv "logs/${RUN}" "logs/attempts/${RUN}_a$((N-1)).live"
    SESSION_DIRS+=("logs/attempts/${RUN}_a$((N-1)).live")
  elif [ "$N" -eq 1 ] && [ -e "logs/${RUN}" ]; then
    blocked plan_gap "logs/${RUN} exists before attempt 1 (B0 PLAN §3.3 needs a fresh run directory)"; return 2
  fi
  { echo "aid=$AID"; echo "tag=$TAG"; echo "arm=$ARM"; echo "seed=$SEED"; echo "attempt=$N"; echo "cfg=$CFG"
    echo "start_utc=$(utc)"; } > "$W/meta/attempt_${AID}.txt"
  echo "aid=$AID" > "$W/meta/harness_stop_${AID}.txt"
  CUR_AID=$AID; CUR_RUN=$RUN; CUR_PHASE=train    # active attempt, for b2_abort
  nvidia-smi --query-gpu=timestamp,memory.used,memory.total --format=csv -l 5 > "$W/meta/gpumem_${AID}.csv" & SMI=$!
  launch_signal_restored "$W/logs/train_${AID}.log" "$PY" $J/packets/P5/p5_train_entry.py --mode upstream --policy "$ARM" \
      --config "$CFG" --seed "$SEED"
  log "started $AID pid=$TR"
  harness_stop "$TR" "$W/logs/train_${AID}.log" "logs/${RUN}/ckpt_0001600.pt" "logs/${RUN}/junior_policy.json" "$W/meta/harness_stop_${AID}.txt"
  kill "$SMI" 2>/dev/null; wait "$SMI" 2>/dev/null
  grep -q '^harness_stop=true' "$W/meta/harness_stop_${AID}.txt" && dev "harness stop (B0 PLAN §4.3, SIGINT) used for $AID"
  { echo "end_utc=$(utc)"; echo "exit_code=$HS_EXIT"; } >> "$W/meta/attempt_${AID}.txt"
  read -r CLASS DIVERGED COMPLETED < <("$PY" -I "$HELPER" classify --aid "$AID" --log "$W/logs/train_${AID}.log" \
      --tb-dir "logs/${RUN}/tb" --harness "$W/meta/harness_stop_${AID}.txt" --sidecar "logs/${RUN}/junior_policy.json" \
      --out "$W/meta/attempt_${AID}.txt")
  log "$AID class=$CLASS diverged=$DIVERGED completed=$COMPLETED exit=$HS_EXIT"
  state "ATTEMPT $AID $CLASS $DIVERGED $COMPLETED"   # training outcome recorded before the evals (restart-safe)
  CUR_PHASE=eval; TR=""; SMI=""
  SESSION_AIDS+=("$AID")
  b2_archive "$AID" "$RUN"
  if [ "$COMPLETED" = true ]; then   # PLAN §4.3; a diverged run that completed is still evaluated (reported only)
    b2_finish "$AID" "$TAG" "$CFG" "$ARM" "$RUN" "$DIVERGED"
  else echo "evals=skipped" >> "$W/meta/attempt_${AID}.txt"; fi
  CUR_AID=""
}

b2_archive() {   # run directory -> logs/attempts/<AID>/ without *.pt (repeatable)
  mkdir -p "logs/attempts/$1"
  [ -d "logs/$2" ] && tar -C "logs/$2" --exclude='*.pt' -cf - . | tar -C "logs/attempts/$1" -xf -
}

# Evals (400/800/1200 mask 0, 1600 full) and PERM of a completed attempt, then `EVALDONE`. Also run by a later
# session part (`FINISH` from the helper) when an abort interrupted them; existing execs and PERM records are reused.
b2_finish() { local AID=$1 TAG=$2 CFG=$3 ARM=$4 RUN=$5 DIVERGED=$6 IT role=report
  for IT in 0000400 0000800 0001200; do b2_eval "$AID" "$IT" "logs/${RUN}/ckpt_${IT}.pt" "$CFG" mask0 "$RUN" "$ARM"; done
  b2_eval "$AID" 0001600 "logs/${RUN}/ckpt_0001600.pt" "$CFG" full "$RUN" "$ARM"
  echo "evals=done" >> "$W/meta/attempt_${AID}.txt"
  [ "$TAG" = b2mt ] && [ "$ARM" = attention ] && [ "$DIVERGED" = false ] && role=gate
  grep -q "^PERM $AID " "$W/meta/driver_state.txt" || b2_perm "$AID" "logs/${RUN}/ckpt_0001600.pt" "$CFG" "$role"
  b2_archive "$AID" "$RUN"
  state "EVALDONE $AID"
}

# ------------------------------------------------------------------ termination (SIGTERM/SIGHUP/SIGINT to the driver)
# Every long child (trainer, eval, PERM) is waited for with `wait`, so the trap fires at once. Stops the child and the
# GPU-memory logger, keeps the evidence of the active attempt (classified and archived without *.pt, ATTEMPT
# record written so a later part starts attempt N+1), records the spend, writes BLOCKED.md `aborted`, and packs.
b2_abort() {
  trap - TERM HUP INT
  log "ABORT: driver received a termination signal (phase=${CUR_PHASE:-none} attempt=${CUR_AID:-none})"
  local p w rc
  # eval/PERM child: SIGTERM (a non-interactive '&' job ignores SIGINT); trainer: SIGINT (restored by the CR-B0-1
  # launcher, so the frozen finally writes the sidecar). 60 s grace each, then SIGKILL.
  for p in "TERM:${CHILD:-}" "INT:${TR:-}"; do
    [ -n "${p#*:}" ] && kill -0 "${p#*:}" 2>/dev/null || continue
    kill -"${p%%:*}" "${p#*:}" 2>/dev/null; w=0
    while kill -0 "${p#*:}" 2>/dev/null && [ "$w" -lt 60 ]; do sleep 1; w=$((w + 1)); done
    kill -KILL "${p#*:}" 2>/dev/null; wait "${p#*:}" 2>/dev/null; rc=$?
    if [ "${p%%:*}" = TERM ] && [ -n "${CUR_EVAL_LOG:-}" ]; then   # interrupted eval: record its exit status
      echo "exit=$rc" >> "$CUR_EVAL_LOG"
    fi
  done
  [ -n "${SMI:-}" ] && kill "$SMI" 2>/dev/null
  if [ -n "${CUR_AID:-}" ]; then
    echo "aborted=true phase=$CUR_PHASE" >> "$W/meta/attempt_${CUR_AID}.txt"
    if [ "$CUR_PHASE" = train ]; then   # training interrupted: classify from the evidence, record the attempt
      local c d k
      read -r c d k < <("$PY" -I "$HELPER" classify --aid "$CUR_AID" --log "$W/logs/train_${CUR_AID}.log" \
          --tb-dir "logs/${CUR_RUN}/tb" --harness "$W/meta/harness_stop_${CUR_AID}.txt" \
          --sidecar "logs/${CUR_RUN}/junior_policy.json" --out "$W/meta/attempt_${CUR_AID}.txt")
      state "ATTEMPT $CUR_AID ${c:-INFRA} ${d:-false} ${k:-false}"
      SESSION_AIDS+=("$CUR_AID")
    fi
    b2_archive "$CUR_AID" "$CUR_RUN"   # phase=eval: ATTEMPT is on record, no EVALDONE -> a later part runs FINISH
    dev "abort during $CUR_AID (phase $CUR_PHASE)"
  fi
  state "SPENT $(hours_total)"
  blocked aborted "driver terminated by signal at $(utc)"
  b2_pack false aborted
  exit 143
}

hours_total() { awk -v s="$SESSION_START" -v p="$PRIOR_H" -v n="$(date +%s)" 'BEGIN{printf "%.4f", p + (n - s) / 3600}'; }

# ------------------------------------------------------------------ pack (PLAN §9.1)
b2_pack() {
  local cap_hit=$1 remaining=$2 tot suffix="" stage name a d f
  tot=$(hours_total)
  [ -d "$U" ] && (cd "$U" && ls -lR logs/b2mt_* logs/b2idx_* logs/attempts/b2* 2>/dev/null) > "$W/meta/ckpt_dirs_ls.txt"
  ls -lR "$STAGE" >> "$W/meta/ckpt_dirs_ls.txt" 2>/dev/null
  { echo "part=$PART"; echo "venue=$VENUE"; echo "start_utc=$SESSION_START_UTC"; echo "end_utc=$(utc)"
    echo "session_hours=$(awk -v t="$tot" -v p="$PRIOR_H" 'BEGIN{printf "%.4f", t-p}')"; echo "prior_hours=$PRIOR_H"
    echo "total_hours=$tot"; echo "spend_cap_hours=$SPEND_CAP_H"; echo "spend_cap_hit=$cap_hit"
    echo "cells_remaining=$remaining"; echo "p4_root_candidates=${P4_ROOTS[*]}"; echo "stage_dir=$STAGE"; } > "$W/meta/session.txt"
  [ "$PART" -ge 2 ] && suffix="-part$PART"
  name=b2-$(date -u +%Y%m%d-%H%M)${suffix}.tgz
  stage=$(mktemp -d "$B2_OUT_DIR/b2_stage.XXXX")
  mkdir -p "$stage/logs/attempts" "$stage/logs/eval"
  cp -a "$W/meta" "$stage/"
  for a in "${SESSION_AIDS[@]}"; do
    cp -a "$W/logs/train_${a}.log" "$stage/logs/" 2>/dev/null
    cp -a "$U/logs/attempts/${a}" "$stage/logs/attempts/" 2>/dev/null
    [ -d "$U/logs/eval/${a}" ] && cp -a "$U/logs/eval/${a}" "$stage/logs/eval/"
  done
  for a in "${SESSION_EVALS[@]}"; do [ -d "$U/logs/eval/${a}" ] && cp -a "$U/logs/eval/${a}" "$stage/logs/eval/"; done
  for d in "${SESSION_DIRS[@]}"; do cp -a "$U/$d" "$stage/logs/attempts/"; done
  mkdir -p "$stage/logs/perm"; cp -a "$W"/logs/perm_*.log "$stage/logs/perm/" 2>/dev/null
  find "$stage" -name '*.pt' -delete
  cp -a "$W/deviations.md" "$stage/"; [ -f "$W/BLOCKED.md" ] && cp -a "$W/BLOCKED.md" "$stage/"
  for f in ${B2_EXTRA_FILES:-}; do                                      # run.sh passes itself; relay-side records stay outside
    cp -a "$f" "$stage/" || dev "extra file $f missing from the bundle"; done
  if find "$stage" \( \( -name '*.npz' ! -path '*/logs/eval/*/maskstream_*.npz' \) -o -path '*lafan*' \
       -o \( -name '*.csv' ! -path '*/meta/gpumem_*.csv' \) \) | grep -q .; then
    echo "REFUSE: motion data in stage"; return 4; fi
  tar czf "$B2_OUT_DIR/$name" -C "$stage" .
  sha256sum "$B2_OUT_DIR/$name"
  log "DONE_DRIVER deposit=$B2_OUT_DIR/$name (deposit unmodified; seal before open, PLAN §9.2)"
}

b2_main() {
  SELF=$(readlink -f "$0")
  B2_TGZ=${B2_TGZ:-/content/junior_b_colab-CR-B2-1.tgz}
  B2_OUT_DIR=${B2_OUT_DIR:-/content}
  VENUE=xn4090
  SESSION_START=$(date +%s); SESSION_START_UTC=$(utc)
  SESSION_AIDS=(); SESSION_DIRS=(); SESSION_EVALS=(); PART=1; PRIOR_H=0; CUR_AID=""; CUR_PHASE=""; TR=""; SMI=""; CHILD=""; CUR_EVAL_LOG=""
  b2_init
  trap 'b2_abort >&3 2>&3' TERM HUP INT
  if ! b2_stage; then b2_pack false p4_ckpts_unavailable; exit 1; fi     # step 0, before any setup
  if ! b2_setup; then cd "$U" 2>/dev/null; b2_pack false setup_failed; exit 1; fi
  local cap=false remaining=none line
  while :; do
    line=$("$PY" -I "$HELPER" next --state "$W/meta/driver_state.txt" --total-hours "$(hours_total)" --spend-cap "$SPEND_CAP_H")
    case "$line" in
      DONE) break ;;
      SPENDCAP) cap=true; state "SPEND_CAP_HIT $(hours_total)"
                blocked spend_cap "$SPEND_CAP_H GPU wall-hours reached between cells (PLAN §10)"; remaining=see_driver_state; break ;;
      UEVAL*) read -r _ A <<< "$line"; b2_ueval "$A"; state "SPENT $(hours_total)" ;;
      UPERM*) read -r _ A <<< "$line"; b2_uperm "$A"; state "SPENT $(hours_total)" ;;
      FINISH*) read -r _ A TAG CFG ARM DIV <<< "$line"; RUN=${A%_a[0-9]*}
               CUR_AID=$A; CUR_RUN=$RUN; CUR_PHASE=eval; SESSION_AIDS+=("$A")
               b2_finish "$A" "$TAG" "$CFG" "$ARM" "$RUN" "$DIV"; CUR_AID=""; state "SPENT $(hours_total)" ;;
      CELL*) read -r _ TAG CFG ARM SEED N NEW <<< "$line"
             b2_train_attempt "$TAG" "$CFG" "$ARM" "$SEED" "$N" || break
             state "SPENT $(hours_total)" ;;
      *) blocked plan_gap "helper returned: $line"; break ;;
    esac
  done
  b2_pack "$cap" "$remaining"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then b2_main "$@"; fi
