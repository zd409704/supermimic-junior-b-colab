#!/usr/bin/env bash
# P1 CPU smoke, new attempt log; JSON outputs go to a fresh per-attempt dir (never overwrite logs/smoke/).
set -uo pipefail
cd /srv/claude/research/supermimic-junior-b-colab
N=$1; STAMP=$(date +%Y%m%d-%H%M)-EDT; LOG=logs/smoke-cpu-attempt$N-$STAMP.log; OUT=logs/smoke-attempt$N
[ -e "$OUT" ] && { echo "refusing: $OUT exists"; exit 2; }
mkdir -p "$OUT"; export PYTHONDONTWRITEBYTECODE=1; PY=.venv/bin/python
{
echo "# CPU smoke attempt$N (P1 freeze candidate), research box, $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "# $($PY -c 'import sys,torch,mujoco;print("python",sys.version.split()[0],"torch",torch.__version__,"mujoco",mujoco.__version__,"cuda_available",torch.cuda.is_available())')"
echo "# code manifest sha256 (make_manifest.sh | sha256sum): $(packets/P1/scripts/make_manifest.sh | sha256sum | cut -c1-64)"
run(){ echo "\$ $*"; "$@"; echo "exit=$?"; }
run $PY code/attention_policy.py
run $PY code/mlp_baseline.py
run $PY code/tests/test_smoke.py
for a in attention mlp_matched mlp_upstream; do run $PY code/train_entry.py --policy $a --out $OUT; done
run $PY code/eval_entry.py --out $OUT
echo "\$ python code/train_entry.py --mode upstream (expected: refuse, no CUDA)"; $PY code/train_entry.py --mode upstream; echo "exit=$?"
echo "\$ notebook validate"; $PY -c "import nbformat;nbformat.validate(nbformat.read('notebooks/colab_smoke.ipynb',4));print('notebook valid')"; echo "exit=$?"
} > "$LOG" 2>&1
echo "$LOG"
