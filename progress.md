# progress.md — run-001-scaffold (method v1.1 sha256 9bdc872e…590afc0)

State table (method §13.5). States: PENDING / RUNNING (attempt, start) / DONE (hash) / SKIPPED (reason) / ABORTED (reason).
Times America/Toronto. Hashes = first 16 hex of sha256.

| Step | Description | State | Evidence |
|---|---|---|---|
| S0 | Method boot: pin verified, overlays read, fit analysis | DONE (2026-10-25 14:06 EDT) | `orch/STATUS.md` §1 |
| S1 | Design review read; amendment note appended | DONE (f0590bdf180e36af) | `docs/DESIGN_REVIEW.md` |
| S2 | Scaffold: attention decoder, matched MLP, entrypoints, config, notebook, runbook, vendor notes | DONE | hashes in `orch/STATUS.md` §3 |
| S3 | CPU import + smoke on research box | DONE (attempt2 018c0a40de08da74) | `logs/smoke-cpu-attempt2-20261025-1417-EDT.log` (attempt1 kept: `logs/smoke-cpu-attempt1-20261025-1415-EDT.log`, superseded by code change for B1 morphology) |
| B0-smoke | Colab GPU: upstream sanity + 1-seed attention vs mlp_matched smoke train + eval | PENDING (owner, Colab) | runbook §5–§7 |
| B0-plan | Seal `spikes/B0/PLAN.md` (arms, seeds=3, budget, thresholds from runbook §8) | PENDING (Orchestrator, after B0-smoke passes) | — |
| B0 | Colab microbench, 3 seeds/arm, matched budget | PENDING (blocked on B0-smoke, B0-plan) | — |
| B2 | Token-mask retention ρ(0.1), ρ(0.2) + id_mode=index ablation, on B0 checkpoints | PENDING (blocked on B0) | — |
| B1 | Second embodiment / masked DoF | PENDING (gated: only if B0 or B2 shows signal). Prereqs open: actuators (MJCF nu=0), retargets, per-body WM/critic | `assets/home_humanoid_mjcf/`, `code/vendor/NOTES.md` |

---

# progress.md — run-002-eval-scheme (method v1.1 sha256 9bdc872e…590afc0 + OVERLAY-001)

| Step | Description | State | Evidence |
|---|---|---|---|
| E0 | Method boot: pin sha verified, overlays read, fit analysis (OVERLAY-001 added) | DONE (2026-10-25 14:22 EDT) | `orch/STATUS.md` |
| E1 | Context read + asset inventory (CPU mujoco 3.17) | DONE | `docs/EVAL_REVIEW.md` §4.1 |
| E2 | EVAL_REVIEW written | DONE (hash in STATUS) | `docs/EVAL_REVIEW.md` |
| E3 | SCHEME_PLAN written | DONE (hash in STATUS) | `docs/SCHEME_PLAN.md` |
| E4 | B1 brief (draft, unfrozen) | DONE (hash in STATUS) | `briefs/B1-home-humanoid-cross-embodiment.md` |
| E5 | DESIGN_REVIEW note, ledger D-002/P-B1, ISSUE-001 | DONE | appended files |
| P1 | Scaffold freeze (+FX-1..4, D-DESC contest) | PENDING (later Claude Code orchestration wake) | `docs/SCHEME_PLAN.md` §1 |
| P2–P6 | B0 smoke → B0 seal → B0 → B2 → B1 | PENDING | `docs/SCHEME_PLAN.md` |

---

# progress.md — run-003-p1-freeze (method v1.1 sha256 9bdc872e…590afc0 + OVERLAY-001; roster `roster.md`)

Times America/Toronto; epoch/UTC in `logs/seal.log`. Rows are appended as states change (latest row per step wins).

| Step | Description | State | Evidence |
|---|---|---|---|
| M0 | Method boot: pin sha verified, overlays read, fit analysis (no new overlay needed) | DONE (2026-10-25 14:43 EDT) | `logs/seal.log` METHOD-PIN |
| M1 | CLI availability probe (codex OK, agy OK after flag fix, standalone claude CLI not logged in → Agent-tool subagents) | DONE | `logs/p1/probe/` |
| D0 | `briefs/D-DESC.md` + `roster.md` + author prompts frozen | DONE (brief f2458a0ee77d936f, roster 5be8a85d97746e09) | `logs/seal.log` |
| D1-A | Author A draft (claude-opus subagent) | RUNNING (attempt1, 2026-10-25 14:49 EDT) | `logs/p1/ddesc/runs.log` |
| D1-B | Author B draft (codex-astra high) | PENDING (after D1-A sealed) | — |
