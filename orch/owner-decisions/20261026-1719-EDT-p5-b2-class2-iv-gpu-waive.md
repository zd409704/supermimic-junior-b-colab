# Owner decision — P5 B2 Class-2 on BLOCKED (U-REPRO + gpu_mismatch)

- Decision-id: 20261026-1719-EDT
- Program: /srv/claude/research/supermimic-junior-b-colab/
- Authority: standing Manager RV/BLK for research drive; PLAN spikes/B2/PLAN.md §7.3 Class-2
- Inputs: VERDICT-P5-b2-attempt1 machine BLOCKED; results c184bb88…; report 79fda4e6…; deposit a869b8fc…

## Decisions

1. **U-REPRO — option (iv).** Accept with disclosure. U-ID passed (correct ckpt files). Per-clip |Δ| and step mismatches are disclosed in the verdict report. Score the U condition from the P5 re-evals (not legacy P4 numbers). Do not choose (v) eval-path CR as the blocking path.

2. **gpu_mismatch / B2-V-2(c) — waive as harness defect.** Host meta lists 8× identical `NVIDIA GeForce RTX 4090`; job used `CUDA_VISIBLE_DEVICES=0`. The tool joined eight names with " + " and compared to a single expected string. P4 had the same joined table without blocking. B2-V-2(a) updates=624 and (b) argv already pass. File a tool CR: parse unique GPU model names (or nvidia-smi under visible devices) instead of joining the full host table. Do not relaunch GPU for this.

3. **Re-emit score (no GPU).** With (1)+(2), recompute §7.3 row-4 outcome from existing open deposit / results. Seal an amended verdict note that records Class-2 (iv) + gpu waive, keeps Provisional, and leaves machine BLOCKED line quoted for audit. `gate_b1` remains as computed (Go). No P6 start in this decision.

## Out of scope

- xn-4090 / GPU relaunch
- Retrain B0 cells
- Drive Claude 4 routine resume (stays paused)
