#!/usr/bin/env bash
# P6 B1-RT GPU driver: RT-6, RT-7, RT-8 of spikes/B1-RT/PLAN.md §2 on xn-4090-gpu2, under Class-2 amendment C.
# PLAN sha256 b7365b4f2e382344151c64be979e5e2aff102fbaba6dc6826d8a429b3b9852a5
# AMENDMENT spikes/B1-RT/AMENDMENT-C2-rt4.json (waive RT-4, slot_rule first); its sha256 is passed in B1RT_AMENDMENT_SHA.
#
# Runner usage (launched by orch/jobs/p6-b1-rt/run.sh):
#   B1RT_TGZ=<tarball> B1RT_TARBALL_SHA=<hex> B1RT_AMENDMENT_SHA=<hex> bash b1rt_driver.sh
# The runner chooses nothing. Every step runs once; the machine verdict is computed on the box by verdict_rt.py
# from the deposited bundle (OVERLAY-001 rule 6). Bundle: $OUT/b1rt-<UTC>.tgz (no *.pt, *.npz, *.csv; PLAN §5).
#
# CPU mock (box only, never for scoring): B1RT_MOCK=1 with B1RT_J, B1RT_U, B1RT_OUT_DIR, B1RT_PY, B1RT_CFG,
# B1RT_MOCK_NPZ (dir of *.npz) and B1RT_MOCK_CKPT_ROOT; skips clone, uv, nvidia-smi and the data download.
set -uo pipefail

J=${B1RT_J:-/content/b1rt/junior}
U=${B1RT_U:-/content/SuperMimic-Reproduced-b1}
OUT=${B1RT_OUT_DIR:-/content}
MOCK=${B1RT_MOCK:-0}
PIN=d9be385b3eeb13a638fb33fb200d3bfd9be9839f
DATA_REV=ce1572906efe6157840e8474d5a0d7aa87481e74     # dataset revision recorded by the box RT-4 run
ATT_SHA=5fb48347dd957b91de4b6780c53bd43d9f1777f56aabc3396aa7351181474a1d   # P4 b0_attention_s0 ckpt_0001600.pt (P5-verified)
MLP_SHA=9ae05d74b9813e4858904a196cffe718d95d1237b41fdd7620aa3c842001913e   # P4 b0_mlp_matched_s0 ckpt_0001600.pt (P5-verified)
SPEND_CAP_H=2.0      # PLAN §4: hard cap per attempt
TRAIN_GUARD=50m      # guard only; the upstream max-hours 0.5 self-stop ends each RT-7 run
TRAIN_RESERVE_H=0.8  # a training starts only if elapsed + reserve <= cap
ARMS="attention mlp_matched"
SELF=$(readlink -f "$0")
T0=$(date +%s)

utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { echo "[b1rt_driver $(utc)] $*"; }
dev() { echo "- [driver] $(utc) $*" >> "$U/deviations.md"; }
blocked() { echo "BLOCKED_REASON=$1 detail=$2" >> "$U/BLOCKED.md"; log "BLOCKED $1: $2"; }
hours() { awk -v s="$T0" -v n="$(date +%s)" 'BEGIN{printf "%.4f", (n - s) / 3600}'; }
fits() { awk -v h="$(hours)" -v r="$1" -v c="$SPEND_CAP_H" 'BEGIN{exit !(h + r <= c)}'; }
dflag() { [ "$MOCK" = 1 ] && echo "--device cpu"; }

# ------------------------------------------------------------------ setup
setup() {
  if [ "$MOCK" != 1 ]; then
    if [ -e "$U" ]; then mv "$U" "$U.prev-$(date -u +%Y%m%d-%H%M%S)"; fi   # never reuse a previous attempt's tree
    git clone https://github.com/CuboiLeo/SuperMimic-Reproduced "$U" || { mkdir -p "$U"; blocked setup_failed "git clone"; return 3; }
    git -C "$U" checkout -q "$PIN" && [ "$(git -C "$U" rev-parse HEAD)" = "$PIN" ] || { blocked setup_failed "upstream HEAD != $PIN"; return 3; }
  else
    mkdir -p "$U"
  fi
  cd "$U" || return 3
  mkdir -p meta logs; : > deviations.md
  exec > >(tee -a meta/driver.log) 2>&1
  log "start mock=$MOCK J=$J U=$U"
  echo "driver_sha256=$(sha256sum "$SELF" | cut -c1-64)" > meta/driver_identity.txt

  # tarball identity before unpacking; driver must equal the tarball copy
  [ -n "${B1RT_TARBALL_SHA:-}" ] && [ -f "${B1RT_TGZ:-/nonexistent}" ] || { blocked tarball_sha_mismatch "B1RT_TARBALL_SHA or B1RT_TGZ unset/missing"; return 4; }
  sha256sum "$B1RT_TGZ" > meta/tarball_sha256.txt
  [ "$(cut -c1-64 meta/tarball_sha256.txt)" = "$B1RT_TARBALL_SHA" ] || { blocked tarball_sha_mismatch "$(cat meta/tarball_sha256.txt)"; return 4; }
  rm -rf "$J" && mkdir -p "$J" && tar xzf "$B1RT_TGZ" -C "$J"
  cmp -s "$SELF" "$J/packets/P6/b1rt_driver.sh" || { blocked plan_gap "running driver differs from the tarball copy"; return 4; }
  (cd "$J" && sha256sum -c packets/P6/MANIFEST-b1rt.sha256 > "$U/meta/manifest_check.txt" 2>&1) || { blocked tarball_sha_mismatch "manifest check"; return 4; }

  # Class-2 amendment C must be present with the sealed hash before slot rule `first` is used
  AM=$J/spikes/B1-RT/AMENDMENT-C2-rt4.json
  [ "$(sha256sum "$AM" | cut -c1-64)" = "${B1RT_AMENDMENT_SHA:-}" ] || { blocked plan_gap "AMENDMENT-C2-rt4.json sha != B1RT_AMENDMENT_SHA"; return 4; }
  grep -q '"slot_rule": "first"' "$AM" && grep -q '"RT-4"' "$AM" || { blocked plan_gap "amendment lacks slot_rule first / waive RT-4"; return 4; }
  echo "amendment_sha256=$B1RT_AMENDMENT_SHA slot_rule=first waive=RT-4" > meta/amendment_check.txt

  if [ "$MOCK" != 1 ]; then
    patch -p1 --dry-run < "$J/packets/P6/upstream-b1.patch" > meta/patch_dryrun.txt 2>&1 || { blocked setup_failed "upstream-b1.patch dry run"; return 5; }
    patch -s -p1 < "$J/packets/P6/upstream-b1.patch" || { blocked setup_failed "upstream-b1.patch apply"; return 5; }
    unset PYTHONPATH
    uv sync && uv pip install --python .venv/bin/python pyyaml huggingface_hub || { blocked setup_failed "uv sync"; return 5; }
    PY=$U/.venv/bin/python
    if ! $PY -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)"; then   # R1 fallback, as P4 runbook §2
      TV=$($PY -c "import torch;print(torch.__version__.split('+')[0])")
      uv pip install --python "$PY" "torch==$TV" --index-url https://download.pytorch.org/whl/cu128 --reinstall
      uv pip install --python "$PY" warp-lang --reinstall
      dev "R1 wheel substitution (P4 runbook §2): torch==$TV from cu128 index, PyPI warp-lang"
      $PY -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)" || { blocked R1_unresolved "cuda unavailable after fallback"; return 6; }
    fi
    nvidia-smi > meta/nvidia-smi.txt 2>&1
    nvidia-smi -i "${CUDA_VISIBLE_DEVICES:-0}" --query-gpu=index,uuid,name --format=csv > meta/gpu_used.csv 2>&1
    uv pip freeze --python "$PY" > meta/pip-freeze.txt
  else
    PY=${B1RT_PY:?}
  fi
  $PY -c "import torch, mujoco; print('cuda', torch.cuda.is_available(), torch.__version__, 'mujoco', mujoco.__version__)" > meta/torch_cuda.txt
  CFG=${B1RT_CFG:-$J/packets/P6/configs/b1_rt7.yaml}
  B1=$J/packets/P6/b1
  export SM_BODY_MODULE=sm_body_home
  return 0
}

# ------------------------------------------------------------------ P4 transfer sources (read only; PLAN RT-8 (b))
find_p4() {  # sets ATT MLP; roots in order, first root holding both s0 checkpoints is used
  local roots
  if [ "$MOCK" = 1 ]; then roots="$B1RT_MOCK_CKPT_ROOT"; else
    roots="/content/p5_p4ckpts /content/SuperMimic-Reproduced /data/muchuan/p4-b0-attempt1/workdir/SuperMimic-Reproduced"; fi
  ATT=""; MLP=""
  { echo "# P4 s0 checkpoints for RT-8 (b), $(utc)"; echo "expected attention=$ATT_SHA mlp_matched=$MLP_SHA"; } > meta/p4_ckpt_identity.txt
  for r in $roots; do
    local a=$r/logs/b0_attention_s0/ckpt_0001600.pt m=$r/logs/b0_mlp_matched_s0/ckpt_0001600.pt
    if [ -f "$a" ] && [ -f "$m" ]; then ATT=$a; MLP=$m; echo "root=$r" >> meta/p4_ckpt_identity.txt; break; fi
    echo "candidate_root=$r missing" >> meta/p4_ckpt_identity.txt
  done
  [ -n "$ATT" ] && sha256sum "$ATT" "$MLP" >> meta/p4_ckpt_identity.txt
}

# ------------------------------------------------------------------ data (PLAN §3 under amendment C; X-002 runtime only)
data_step() {
  if [ "$MOCK" = 1 ]; then
    mkdir -p data/npz/b1_home && cp "$B1RT_MOCK_NPZ"/*.npz data/npz/b1_home/
    echo '{"mock": true, "pass": true}' > meta/b1_data_qa.json; dev "MOCK data step (synthetic npz)"; return 0
  fi
  $PY "$B1/prepare_b1_data.py" --rev "$DATA_REV" --out-npz data/npz/b1_home --qa-out meta/b1_data_qa.json \
      --expect "$J/spikes/B1-RT/results-cpu-attempt1.json" --slot-rule first 2>&1 | tee logs/data_step.log
  local rc=${PIPESTATUS[0]}
  [ "$rc" -eq 0 ] || { blocked data_step "prepare_b1_data exit $rc (see meta/b1_data_qa.json)"; return 8; }
  [ "$(ls data/npz/b1_home/*.npz 2>/dev/null | wc -l)" -eq 4 ] || { blocked data_step "expected 4 npz"; return 8; }
}

# ------------------------------------------------------------------ RT-6, RT-8 (b), RT-7, RT-8 (a)
rt6() {
  $PY "$B1/rt_gpu.py" rt6 --out meta/rt6.json $( [ "$MOCK" = 1 ] && echo "--device cpu" ) 2>&1 | tee logs/rt6.log
  echo "rt6_exit=${PIPESTATUS[0]}" >> meta/steps.txt
}

rt8x() {
  find_p4
  if [ -z "$ATT" ]; then
    echo '{"pass": false, "error": "P4 s0 checkpoints not found at any candidate root"}' > meta/rt8_xferload.json
    dev "RT-8 (b): P4 s0 checkpoints not found"; return 0
  fi
  $PY "$B1/rt_gpu.py" xferload --att "$ATT" --mlp "$MLP" --config "$CFG" --out meta/rt8_xferload.json \
      --expect-att-sha "$ATT_SHA" --expect-mlp-sha "$MLP_SHA" 2>&1 | tee logs/rt8_xferload.log
  echo "rt8x_exit=${PIPESTATUS[0]}" >> meta/steps.txt
}

rt7_arm() { local arm=$1 run=b1rt_${1}_s0
  if ! fits "$TRAIN_RESERVE_H"; then blocked spend_cap "no room for RT-7 $arm at $(hours) h (cap $SPEND_CAP_H)"; return 9; fi
  [ -e "logs/$run" ] && { blocked plan_gap "logs/$run exists before the first run"; return 9; }
  echo "rt7_${arm}_start_utc=$(utc)" >> meta/steps.txt
  nvidia-smi --query-gpu=timestamp,memory.used,memory.total --format=csv -l 30 > "meta/gpumem_${run}.csv" 2>/dev/null & local SMI=$!
  timeout --signal=INT --kill-after=300 "$TRAIN_GUARD" $PY "$B1/p6_entry.py" train --config "$CFG" --policy "$arm" --seed 0 \
      --run-tag b1rt $(dflag) > "logs/train_${run}.log" 2>&1
  local rc=$?
  kill "$SMI" 2>/dev/null; wait "$SMI" 2>/dev/null
  echo "rt7_${arm}_exit=$rc rt7_${arm}_end_utc=$(utc)" >> meta/steps.txt
  [ "$rc" -eq 124 ] && dev "RT-7 $arm: training guard $TRAIN_GUARD fired (SIGINT)"
  $PY "$B1/b1_checks.py" rt7 --run-dir "logs/$run" --log "logs/train_${run}.log" --out "meta/rt7_${arm}.json"
  $PY "$B1/b1_checks.py" tbdump --run-dir "logs/$run" --out "meta/tb_${run}.json"
}

rt8_eval_arm() { local arm=$1 run=b1rt_${1}_s0
  if [ ! -f "logs/$run/ckpt_latest.pt" ]; then
    echo "{\"run\": \"$run\", \"pass\": false, \"error\": \"ckpt_latest.pt missing\"}" > "meta/rt8_eval_${arm}.json"; return 0
  fi
  $PY "$B1/p6_entry.py" eval --config "$CFG" --ckpt "logs/$run/ckpt_latest.pt" --out-dir logs/eval/rt8 \
      --masks 0.0 0.1 0.2 $(dflag) > "logs/eval_${run}.log" 2>&1
  echo "rt8_eval_${arm}_exit=$?" >> meta/steps.txt
  $PY "$B1/b1_checks.py" rt8eval --eval-dir logs/eval/rt8 --run "$run" --out "meta/rt8_eval_${arm}.json"
}

# ------------------------------------------------------------------ bundle (PLAN §5)
bundle() {
  cd "$U" 2>/dev/null || { mkdir -p "$U" && cd "$U"; }
  mkdir -p meta extras
  echo "spent_hours=$(hours) end_utc=$(utc)" >> meta/steps.txt
  for f in ${B1RT_EXTRA_FILES:-}; do [ -f "$f" ] && cp -p "$f" extras/; done
  local B="$OUT/b1rt-$(date -u +%Y%m%d-%H%M).tgz" items="meta logs deviations.md extras"
  [ -f BLOCKED.md ] && items="$items BLOCKED.md"
  tar --exclude='*.pt' --exclude='*.npz' --exclude='*.csv' -czf "$B" $items 2>/dev/null
  log "BUNDLE $B sha256=$(sha256sum "$B" | cut -c1-64)"
  echo "DONE_DRIVER utc=$(utc) bundle=$B state=$1"
}

main() {
  if ! setup; then bundle BLOCKED; return 0; fi
  if ! data_step; then bundle BLOCKED; return 0; fi
  rt6
  rt8x
  for arm in $ARMS; do rt7_arm "$arm" || break; done
  for arm in $ARMS; do [ -f "meta/rt7_${arm}.json" ] && rt8_eval_arm "$arm"; done
  bundle "$([ -f BLOCKED.md ] && echo BLOCKED || echo DONE)"
}

main "$@"
