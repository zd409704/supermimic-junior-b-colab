#!/usr/bin/env bash
# P5-prep driver integration mock (CPU, research box). Usage: run_driver_mock.sh <attempt N> [abort_after_s [restart]]
# abort: SIGTERM to the driver after that many seconds; restart: then session part 2 from the saved driver_state.
# Runs the real packets/P5/b2_driver.sh functions (relocated copy: /content -> <mock>/content, second P4 root ->
# <mock>/data_root, POLL_S=1 in the sourced CR-B0-1 driver) against: a mock P4 tree whose six ckpt_0001600.pt have
# the PLAN §2.2 byte sizes (sparse) and whose sidecars are the real P4 deposit sidecars (PLAN §2.2 sha256); a fake
# trainer and a fake PERM script; the REAL p5_eval_entry.py + frozen eval_entry.py over a fake upstream package.
# Only b2_setup is replaced (no uv / clone / motion data / GPU). Then runs verdict_b2.py on the mock deposit.
# Expected verdict: BLOCKED [U-ID, U-REPRO] only (mock root is not a PLAN root; fake evals do not reproduce P4).
set -u
R=/srv/claude/research/supermimic-junior-b-colab
N=$1
ABORT_S=${2:-}
RESTART=${3:-}
M=$R/logs/p5prep/driver-mock-attempt$N
[ -e "$M" ] && { echo "refusing: $M exists"; exit 2; }
C=$M/content; mkdir -p "$C" "$M/bin" "$M/data_root"
MK=$R/packets/P5/mock
REALPY=$R/.venv/bin/python
OPEN=$R/logs/xn4090/2026-10-26/open-b0-20261026-0919
bash $R/packets/P5/make_cr_b2_1.sh tar "$C/junior_b_colab-CR-B2-1.tgz"
TGZ_SHA=$(sha256sum "$C/junior_b_colab-CR-B2-1.tgz" | cut -c1-64)
sed -e "s#/content#$C#g" -e "s#/data/muchuan/p4-b0-attempt1/workdir#$M/data_root#g" $R/packets/P5/b2_driver.sh > $M/b2_driver_mock.sh
sed -e "s#/content#$C#g" -e 's#^POLL_S=30 #POLL_S=1 #' $R/packets/P4/b0_driver.sh > $M/b0_driver_mock.sh
# mock P4 tree
U=$C/SuperMimic-Reproduced
for aid in b0_attention_s0_a1 b0_attention_s1_a1 b0_attention_s2_a1 b0_mlp_matched_s0_a1 b0_mlp_matched_s1_a1 b0_mlp_matched_s2_a1; do
  run=${aid%_a1}; mkdir -p $U/logs/$run
  case $aid in *attention*) sz=164415878;; *) sz=164427663;; esac
  truncate -s $sz $U/logs/$run/ckpt_0001600.pt
  cp $OPEN/logs/attempts/$aid/junior_policy.json $U/logs/$run/
done
mkdir -p $U/scripts && cp $MK/fake_eval_benchmark.py $U/scripts/eval_benchmark.py
# fake tools
cat > $M/bin/nvidia-smi <<'X'
#!/bin/bash
if [[ "$*" == *query-gpu* ]]; then echo "timestamp, memory.used [MiB], memory.total [MiB]"; while :; do echo "2026/10/27 01:00:00.000, 5000 MiB, 24564 MiB"; sleep 5; done
else echo "|   0  NVIDIA GeForce RTX 4090        Off |   00000000:16:00.0 Off |                  Off |"; fi
X
cat > $M/bin/py <<X
#!/bin/bash
case "\$1" in
  */p5_train_entry.py) shift; MOCK_J=$C/junior MOCK_M=$M exec $REALPY $MK/fake_trainer.py "\$@" ;;
  */perm_check.py) shift; exec $REALPY $MK/fake_perm.py "\$@" ;;
  */p5_eval_entry.py) PYTHONPATH=$MK/fake_site exec $REALPY "\$@" ;;
  *) exec $REALPY "\$@" ;;
esac
X
chmod +x $M/bin/*
export PATH=$M/bin:$PATH MOCK_b2mt_mlp_mind_s1=infra MOCK_b2idx_attention_s2=div
export B2_P4_DRIVER=$M/b0_driver_mock.sh B2_TGZ=$C/junior_b_colab-CR-B2-1.tgz B2_TARBALL_SHA=$TGZ_SHA B2_OUT_DIR=$C
source $M/b2_driver_mock.sh
b2_setup() {   # mock: tarball check + unpack as the real setup; no uv/clone/motion/GPU
  sha256sum "$B2_TGZ" > "$W/meta/tarball_sha256.txt"
  [ "$(cut -c1-64 "$W/meta/tarball_sha256.txt")" = "$B2_TARBALL_SHA" ] || { blocked tarball_sha_mismatch x; return 4; }
  rm -rf "$J" && mkdir -p "$J" && tar xzf "$B2_TGZ" -C "$J"
  sed -i "s#/content#$C#g" "$J/packets/P5/b2_driver_helper.py"                       # mock-only relocation
  sed -i "s#repo_dir: /content/SuperMimic-Reproduced#repo_dir: $U#" "$J"/configs/*.yaml
  cd "$U" || return 3
  PY=$M/bin/py
  echo "cuda True mock" > "$W/meta/torch_cuda.txt"
  (cd "$J" && $REALPY code/tests/test_smoke.py) > "$W/meta/cpu_test_smoke.log" 2>&1
  $PY -I "$HELPER" cputest --log "$W/meta/cpu_test_smoke.log" --out "$W/meta/cpu_test_check.txt" || { blocked cpu_test_mismatch x; return 7; }
  nvidia-smi > "$W/meta/nvidia-smi.txt"
  cp "$J/packets/P5/p4_pip_freeze_ref.txt" "$W/meta/pip-freeze.txt"
  diff -u "$J/packets/P5/p4_pip_freeze_ref.txt" "$W/meta/pip-freeze.txt" > "$W/meta/env_drift.txt"
  GPU=$($PY -I "$HELPER" gpuname --smi "$W/meta/nvidia-smi.txt")
  [ "$GPU" = "$EXPECT_GPU" ] || { blocked plan_gap "GPU $GPU"; return 9; }
  return 0
}
SELF=$M/b2_driver_mock.sh
if [ -n "$ABORT_S" ]; then
  ( b2_main ) > $M/mock.out 2>&1 & DRV=$!
  sleep "$ABORT_S"; echo "MOCK: SIGTERM to driver pid $DRV at $(date -u +%H:%M:%S)" >> $M/abort.txt; kill -TERM $DRV
  wait $DRV; echo "driver exit=$?" >> $M/mock.out
  if [ "$RESTART" = restart ]; then
    cp $C/p5_b2/meta/driver_state.txt $M/state_part1.txt
    sleep 61   # distinct archive name (minute stamp)
    ( B2_STATE_IN=$M/state_part1.txt b2_main ) > $M/mock-part2.out 2>&1
    echo "driver part2 exit=$?" >> $M/mock-part2.out
  fi
else
  ( b2_main ) > $M/mock.out 2>&1
  echo "driver exit=$?" >> $M/mock.out
fi
: > $M/mock-seal.log; DEPARGS=""
for DEP in $(ls $C/b2-*.tgz); do
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) 0 DEPOSIT xn4090 $(sha256sum $DEP | cut -c1-64) $DEP mock" >> $M/mock-seal.log
  DEPARGS="$DEPARGS --deposit $DEP"
done
$REALPY -I $R/spikes/B2/verdict/verdict_b2.py $DEPARGS --seal-log $M/mock-seal.log --plan $R/spikes/B2/PLAN.md \
  --method-sha 9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0 --tarball-sha $TGZ_SHA \
  --facts $R/packets/P4/UPSTREAM_FACTS.md --p4-open-tree $OPEN \
  --p4-results $R/orch/reports/VERDICT-P4-b0-attempt1-relaunch3-results.json --venue xn4090 \
  --out $M/mock-results.json --runs-log $M/mock-runs.log --work $M/vwork > $M/verdict.out 2> $M/verdict.err
cat $M/verdict.out
