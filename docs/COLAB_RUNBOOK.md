# Colab runbook: Junior-(B) attention decoder vs matched MLP (B0 / B2)

**Written:** 2026-10-25 (America/Toronto) · **Status:** Provisional. No Colab run has happened yet. Every GPU step below is **unverified** until the owner runs it and files logs.
**Notebook:** `notebooks/colab_smoke.ipynb`, which runs the same steps as cells.

## 0. What runs where

| Venue | What | Verified? |
|---|---|---|
| Research box (CPU, no NVIDIA GPU) | `code/tests/test_smoke.py`, `train_entry.py --mode smoke`, `eval_entry.py --mode smoke` | Yes, 2026-10-25 (see `orch/STATUS.md`) |
| Colab L4 (preferred) / T4 | Upstream mjlab SuperMimic-style loop with our decoder (`--mode upstream`) | **No** |

## 1. Runtime

1. Colab → *Runtime → Change runtime type* → **L4 GPU** (preferred: Ada, 24 GB). T4 (Turing, 16 GB) is the fallback and may hit risk R2.
2. First cell: `!nvidia-smi`. Note the **driver version** and the GPU. Copy both into the run log.

## 2. Get the code

On the research box, pack the program code. It contains no data or binaries:

```bash
cd /srv/claude/research/supermimic-junior-b-colab
tar czf /tmp/junior_b_colab.tgz code configs notebooks docs/COLAB_RUNBOOK.md
```

Upload `junior_b_colab.tgz` to Colab (files pane or Drive), then:

```bash
mkdir -p /content/junior && tar xzf /content/junior_b_colab.tgz -C /content/junior
```

Clone the upstream reproduction at its pin (see `code/vendor/NOTES.md`):

```bash
pip install -q uv
git clone https://github.com/CuboiLeo/SuperMimic-Reproduced /content/SuperMimic-Reproduced
git -C /content/SuperMimic-Reproduced checkout d9be385b3eeb13a638fb33fb200d3bfd9be9839f
cd /content/SuperMimic-Reproduced && uv sync            # Python 3.12 venv in .venv (uv fetches 3.12 if needed)
uv pip install --python .venv/bin/python pyyaml
export PY=/content/SuperMimic-Reproduced/.venv/bin/python
```

**R1, driver vs. CUDA 13 wheels.** Upstream pins torch from the `cu130` index and warp from the NVIDIA index. If `$PY -c "import torch; print(torch.cuda.is_available())"` prints `False`, or warp fails to initialise, the Colab driver is probably too old for CUDA 13. Fallback (unverified): reinstall torch from a CUDA 12.x index that has the same torch version, e.g. `uv pip install --python $PY torch --index-url https://download.pytorch.org/whl/cu128 --reinstall`, and the PyPI `warp-lang` wheel. Record any substitution in the run log, because it is a deviation from the upstream pin.

## 3. CPU-level import smoke (on Colab, before the GPU run)

```bash
cd /content/junior
$PY code/tests/test_smoke.py              # expect 6x PASS (b1 test prints SKIP: asset not in the tarball)
$PY code/train_entry.py --policy attention
$PY code/eval_entry.py                    # B2 smoke: attention perm_rel_err ~1e-6; MLP arms O(1)
```

## 4. Motion data (small LAFAN1-style subset; never commit)

LAFAN1 motion is **CC BY-NC-ND 4.0**. Download only on the Colab runtime, only the clips in `configs/colab_smoke.yaml`:

```bash
cd /content/SuperMimic-Reproduced
SUB=$($PY -c "import yaml;print(yaml.safe_load(open('/content/junior/configs/colab_smoke.yaml'))['upstream']['dataset_subdir'])")
$PY - <<EOF
import yaml; from huggingface_hub import snapshot_download
c = yaml.safe_load(open('/content/junior/configs/colab_smoke.yaml'))['upstream']
snapshot_download(c['dataset_repo'], repo_type='dataset', local_dir='data/raw/lafan1',
                  allow_patterns=[f"{c['dataset_subdir']}/{n}.csv" for n in c['clips']])
EOF
env -u PYTHONPATH $PY scripts/data/csv_to_npz_batch.py --input-dir data/raw/lafan1/$SUB \
    --output-dir data/npz/lafan1_smoke --input-fps 30 --workers 2
ls data/npz/lafan1_smoke      # 4 npz + manifest.csv
```

## 5. Upstream sanity (optional, about 10 min)

Before swapping the decoder, check that the unmodified upstream loop runs at reduced size:

```bash
env -u PYTHONPATH $PY -m supermimic.scripts.train --run-name up_sanity --data.npz-dir data/npz/lafan1_smoke \
  --env.num-envs 256 --policy-trainer.batch-size 256 --policy-trainer.horizon 16 \
  --policy-trainer.compile None --schedule.max-hours 0.1
```

If this fails, the problem is the environment (R1/R2), not our decoder. Stop and file the error.

## 6. Smoke train: both B0 arms (GPU)

Run from the upstream repo dir so `logs/` and `data/` resolve there:

```bash
cd /content/SuperMimic-Reproduced
for ARM in attention mlp_matched; do
  env -u PYTHONPATH $PY /content/junior/code/train_entry.py --mode upstream --policy $ARM \
      --config /content/junior/configs/colab_smoke.yaml --seed 0 2>&1 | tee logs/train_${ARM}_s0.log
done
```

Optional compute-heavier reference arm (1 seed; DESIGN_REVIEW note 2026-10-25): repeat with `--policy mlp_upstream`.

Reduced defaults (`configs/colab_smoke.yaml`): `num_envs 512`, `batch 512`, `H=16` (paper 32), compile off, `max-hours 0.5` per arm, `--env.anchor-obs` (upstream deviation, applied the same way to both arms). Per GPU: T4 use 256–512 envs, L4 512–1024. If you get CUDA OOM, halve `num-envs` and `batch-size` together, for both arms.

On the first run, check seams S1–S3 (`code/vendor/NOTES.md`). The trainer prints `params: world model …, policy …`. Policy params differ between arms only by the decoder: attention decoder about 0.46 M vs mlp_matched about 0.47 M.

## 7. Eval (Appendix-F style whole-clip benchmark + B2 mask)

```bash
for ARM in attention mlp_matched; do
  env -u PYTHONPATH $PY /content/junior/code/eval_entry.py --mode upstream \
      --config /content/junior/configs/colab_smoke.yaml --ckpt logs/b0_smoke_${ARM}_s0/ckpt_latest.pt
done
ls logs/eval   # <run>_<arm>_mask{0.00,0.10,0.20}.json
```

Copy `logs/*/junior_policy.json`, `logs/*/tb`, `logs/train_*.log` and `logs/eval/*.json` back to the program tree under `logs/colab/<date>/`. These are metrics only. No motion data and no checkpoints.

## 8. Success and kill metrics

**Smoke success (pipeline level, one seed):** for both arms, training reaches the time cap with no NaN or exception. World-model loss goes down. Training return at the end is above its value after warmup. A checkpoint and `junior_policy.json` are written. Eval JSON exists for masks 0.0, 0.1 and 0.2.

**B0 microbench (after smoke; seal `spikes/B0/PLAN.md` first, per method §12.2):**

| Quantity | Definition |
|---|---|
| R(arm) | mean upstream normalised return over the clip subset (1.0 = perfect), unmasked |
| Fail(arm) | count of clips where the training termination fired during eval |
| Cost(arm) | wall-clock per policy update and peak GPU memory, same compile setting for both arms |
| Seeds | 3 per arm (attention, mlp_matched). mlp_upstream gets 1 seed, as a reference only |
| Budget | equal env steps **and** equal wall-clock cap per arm |

**B2:** retention ρ(f) = R(mask f) / R(mask 0) at f ∈ {0.1, 0.2}. Permutation equivariance of the attention arm (id_mode=morph) is architectural: it is checked in CPU smoke, and an error above 1e-4 is a bug, not a finding. Its empirical content is ρ, plus any later id_mode=index ablation.

**Draft thresholds (Provisional; to be frozen in `spikes/B0/PLAN.md`):**

- *Signal:* R(attention) − R(mlp_matched) ≥ max(0.02, 2 × pooled seed SE), **or** ρ_att(0.2) − ρ_mlp(0.2) ≥ 0.05 with R(attention) ≥ R(mlp_matched) − 0.02.
- *Kill (design review §3):* attention ≤ mlp_matched on R **and** no B2 retention gain **and** attention is slower per update → stop. Do not scale to B1 or a larger library.
- Without a signal, B1 (second embodiment or masked DoF) does not start.

## 9. Known risks

| ID | Risk | Mitigation |
|---|---|---|
| R1 | Upstream CUDA 13 wheels need a newer driver than Colab provides | Fallback torch/warp index (§2). Record as deviation |
| R2 | MuJoCo Warp or warp kernels not supported or slow on T4 (sm_75) | Prefer L4. Drop `num_envs` |
| R3 | 0.5 h per arm on Colab is far below upstream's ~1.7 h on a much larger GPU at 4096 envs, so absolute returns will be low | B0 compares arms at matched budget. Absolute return is not a claim |
| R4 | Matched **params** do not mean matched **compute**. The shared weights are applied once per token (31 tokens), so attention costs about 25.7 MFLOP/sample forward vs 0.94 for mlp_matched (27×) and 9.5 for mlp_upstream. CPU fwd+bwd at N=512 measured 302 vs 3.0 vs 16 ms | Report GPU cost per update for every arm. Treat mlp_upstream as the compute-heavier reference. See DESIGN_REVIEW note 2026-10-25 |
| R5 | Joint-order mismatch between morphology rows and obs (S1) | Assert on first run |
| R6 | Colab session limits / disconnects | `--schedule.max-hours`, upstream `--resume <ckpt>`. Copy logs out after each arm |
