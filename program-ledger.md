# Program ledger — supermimic-junior-b-colab

Append-only (method §13.2). Entries are never edited; changes are new entries with `supersedes`. Times America/Toronto.

## X-001 — External: public mjlab SuperMimic-style reproduction as dependency base
- Recorded: 2026-10-25 14:16 EDT, run-001-scaffold, by Orchestrator
- Source: `https://github.com/CuboiLeo/SuperMimic-Reproduced` @ `d9be385b3eeb13a638fb33fb200d3bfd9be9839f` (MIT), base mjlab @ `8bb2bc9e…`
- Asserts (upstream's own claims, not verified here): LAFAN1 40-clip tracking normalised return 0.82–0.90 on one large consumer GPU at 4096 envs; policy = MotionEncoder(goal→z32) + MLP decoder(z, 930-d obs history → 29 actions)
- Adopted as: integration base for B0/B2 (code/vendor/NOTES.md). Return claims are context only.

## X-002 — External: motion data licensing
- Recorded: 2026-10-25 14:16 EDT, run-001-scaffold
- Source: HF dataset `lvhaidong/LAFAN1_Retargeting_Dataset` (retarget code BSD-3; underlying LAFAN1 motion CC BY-NC-ND 4.0)
- Asserts: non-commercial, no-derivatives motion license → download at Colab runtime only; never stored in this tree.

## D-001 — Scheme: Junior-(B) shared attention decoder on unchanged SuperMimic-style WM loop
- Status: **Provisional** (no Lock authorization on disk)
- Method: v1.1, sha256 9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0
- Run: run-001-scaffold · Decision file: `docs/DESIGN_REVIEW.md` sha256 prefix f0590bdf180e36af (incl. amendment note 2026-10-25 14:14 EDT)
- depends_on: [X-001]
- Spike status: none run. B0-smoke pending on Colab.

## P-B0 — Packet planned: attention vs matched-param MLP (B0)
- Recorded: 2026-10-25 14:16 EDT · State: PLANNED · depends_on: [D-001] (Provisional, depth 1)
- Arms: attention (id_mode=morph), mlp_matched (kill comparator), mlp_upstream (compute reference, 1 seed)
- Metric/thresholds: draft in `docs/COLAB_RUNBOOK.md` §8; to be frozen in `spikes/B0/PLAN.md` before execution

## P-B2 — Packet planned: permutation / token-mask (B2)
- Recorded: 2026-10-25 14:16 EDT · State: PLANNED · depends_on: [D-001] (B0 checkpoints reused; not a Provisional-on-Provisional chain)
- Permutation equivariance verified architecturally on CPU (rel err 2.2e-6); empirical metric = mask retention ρ(0.1), ρ(0.2) + id_mode=index ablation

## X-003 — External: owner-provided second home-humanoid body for B1
- Recorded: 2026-10-25 14:18 EDT, run-001-scaffold, by Orchestrator
- Source: `assets/home_humanoid_mjcf/` (appeared 14:11 EDT; provenance in its `sources.json`)
- Asserts: 22-hinge MJCF + meshes for cross-embodiment work. Verified on CPU: loads; morphology descriptors finite and distinct; decoder runs at J=22. MJCF has no actuators (nu=0).
- Adopted as: B1 second morphology (gated on B0/B2 signal per D-001).

## D-002 — Eval + written scheme packet (Claude Code)
- Recorded: 2026-10-25 EDT, run-002-eval-scheme, by Orchestrator (Claude Code, single model)
- Status: **Provisional**
- Method: v1.1, sha256 9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0 (+ method/local OVERLAY-001)
- Decision files: `docs/EVAL_REVIEW.md`, `docs/SCHEME_PLAN.md` (hashes in `orch/STATUS.md`)
- Asserts: accept D-001 scheme with revisions RV-1..RV-8 (RV-1, RV-2, RV-7, RV-8 pending Human lead signature); B1 = decoder-weight transfer with per-body encoder/WM/critic; B1 blockers BLK-0..BLK-12 (incl. MJCF nu=0 verified 2026-10-25)
- depends_on: [D-001, X-001, X-002, X-003]
- Spike status: none (written scheme only). Multi-agent implementation NOT started.

## P-B1 — Packet planned: home-humanoid cross-embodiment (B1)
- Recorded: 2026-10-25 EDT, run-002-eval-scheme · State: PLANNED (draft brief, not frozen)
- Brief: `briefs/B1-home-humanoid-cross-embodiment.md`
- depends_on: [D-001, D-002, B0/B2 decision (future)] — Provisional depth 2: requires Human lead signature or Lock of D-001 before Step 2 (method §13.3)
