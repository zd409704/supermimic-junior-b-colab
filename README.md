# Program: supermimic-junior-b-colab

## Intent

Scaffold and Colab microbench for **Junior-(B) morphology-adaptive shared attention action policy** on top of a **SuperMimic-style** learned differentiable world model (or lighter joint-critic path). Policy architecture change only; do **not** replace the world model with energy-based soft-body simulation (algovivo).

## Venue

- Research box: scaffolding, docs, CPU smoke only (no NVIDIA GPU).
- Training smoke / microbench: **Google Colab** (T4/L4 class), reduced `num_envs`.
- Preferred stack: mjlab / MuJoCo Warp SuperMimic reproduction path (Colab-feasible). Isaac Lab Docker reproductions are reference-only for parity, not the Colab default.

## Method

Inherits global `/srv/claude/research/METHOD/`. See `method/README.md` and `method/local/` for Colab-venue specials.

## Key docs

| Path | Role |
|---|---|
| `docs/DESIGN_REVIEW.md` | Scheme critique, accept/revise, experiment map |
| `docs/COLAB_RUNBOOK.md` | Exact Colab steps (filled by scaffold) |
| `notebooks/` | Colab notebooks |
| `code/` | Attention policy module + train/eval entrypoints |
| `configs/` | Reduced-env Colab configs |
| `code/vendor/NOTES.md` | Upstream mjlab reproduction pin, integration seam, data licensing |
| `progress.md` / `program-ledger.md` | Run state table / append-only program ledger |
| `orch/STATUS.md` | Current Orchestrator status and asks |

## Decision cap

Provisional. Human lead on research briefs: Peter.

