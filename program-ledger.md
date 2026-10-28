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

## D-003 — D-DESC: morphology descriptor v2 + action-scale handling (two-author contest)
- Recorded: 2026-10-25 ~15:40 EDT, run-003-p1-freeze, by Orchestrator (did not author or adjudicate)
- Status: **Provisional** (cap). Spike: **PASS** (`spikes/D-DESC/runs.log`, CPU, 1/3 executions)
- Method: v1.1, sha256 9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0
- Decision file: `packets/P1/ddesc/decision.md` (sha256 in `logs/seal.log`, with spike Amendment v1.1)
- Outcome: Recommend candidate Y (Author A, Claude family), Alternate X (Author B, Codex family). Adjudicator agy/Gemini 4 Argon High, 35 vs 30 in both presentation orders (tie margin 4.5)
- Asserts: 16-d descriptor (hip-centred, L-normalised anchors at qpos0; axis; env default angle; range/π; limb-local depth/8; side; limb; ln σ/0.25; ln τ/(MgL)/0.5); action scale applied only by the env (σ = 0.25·τmax/kp); no second scaling layer
- depends_on: [D-001, D-002, X-001, X-003] (each depth 1)
- Confounds: Claude slots ran as Agent-tool subagents (ISSUE-002); winner shares the brief writer's family; isolation by sequencing + mode 000 + audit; close margin

## D-004 — P1 scaffold freeze
- Recorded: 2026-10-25 ~15:40 EDT, run-003-p1-freeze
- Status: **Provisional** (sealed freeze of provisional scaffolding)
- Manifest: `packets/P1/FREEZE_MANIFEST.md` (digest cd504ca289016c2a42c2e9a90cbe92723cdb8a95bc5e030ddedc9b16563d5ff0); tarball sha256 f69dd11eb532c10411bfd77e3f1f2c5edd36275f4a0b9c737624bb8cac341636
- Contains: descriptor v2 (D-003), FX-1..FX-5, S5; cross-family review REVIEW-1 BLOCK → round 2 → REVIEW-2 FREEZE-OK
- Evidence: `logs/smoke-cpu-attempt3-20261025-1537-EDT.log` (CPU, all PASS)
- depends_on: [D-001, D-002, D-003]
- Spike status: CPU smoke only. Upstream/Colab path unverified (P2 pending)

## P-B0S — Packet planned: P2 B0 Colab smoke (owner-run)
- Recorded: 2026-10-25 EDT, run-003-p1-freeze · State: PLAN SEALED, NOT RUN
- Plan: `spikes/B0-smoke/PLAN.md` (sha256 in `logs/seal.log`); input: tarball of D-004
- depends_on: [D-004]

## D-005 — B0 microbench (P4): attention vs mlp_matched, 29-DoF reference humanoid
- Recorded: 2026-10-26 ~19:00 EDT, P6 boot (back-filled by Orchestrator so B1 can cite B0 by ID; method §13.3). Verdict itself was emitted 2026-10-26 06:22 EDT
- Status: **Provisional**. Spike: **PASS / NONINFERIOR** (machine, `verdict_b0.py` 9caa744a…)
- Method: v1.1, sha256 9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0 (+ OVERLAY-001)
- Decision files: `orch/reports/VERDICT-P4-b0-attempt1-relaunch3-20261026.md` (2bb0de08f91c2514d4b76504683ccada1c5008ecfd8feba589d14a9420bd9cb4), results `orch/reports/VERDICT-P4-b0-attempt1-relaunch3-results.json` (76507d8a9488cd295add444d9e9463da1bf7ab62c2216733043c535f3c6f8d3d); PLAN `spikes/B0/PLAN.md` (356c389f…)
- Venue: xn-4090-gpu2 GPU0. Checkpoints (ckpt_0001600.pt × 6) stay on that host only
- depends_on: [D-001, D-003, D-004]

## D-006 — B2 mask/ablation (P5), Class-2 amended
- Recorded: 2026-10-26 ~19:00 EDT, P6 boot (back-filled; see D-005)
- Status: **Provisional**. Spike: **PASS / NO_GAIN** (u_deficit true), `gate_b1 = Go` (Class-2 decision 9985fc8f…; machine line BLOCKED kept on record)
- Decision files: `orch/reports/VERDICT-P5-b2-attempt1-class2-results.json` (d62dc0b7e565d372558fbaf3a5f9b9b4b0440ae69aa5586751460145183d7798), report `orch/reports/VERDICT-P5-b2-attempt1-class2-20261026.md` (67f0424e…); PLAN `spikes/B2/PLAN.md` (5d1f26f7…)
- Mandatory caveat for any citation of the gate: Δρ_U(0.2) = −0.557 (attention retains less than mlp_matched under untrained masking); NO_GAIN; u_deficit true
- depends_on: [D-005]

## P-B1 (update) — Packet P6 opened: home-humanoid cross-embodiment (B1)
- Recorded: 2026-10-26 ~19:00 EDT, P6 · supersedes: P-B1 state PLANNED
- Authority: `orch/owner-decisions/20261026-1852-EDT-p6-start.md` (3a0254de…), amended by `…-1855-EDT-xn4090-free-p6d-proceed.md` (1408aeef…)
- State: OPEN (P6a → P6b → P6c → P6d). Venue xn-4090-gpu2 (amendment to SCHEME_PLAN Colab text, see brief Amendment v1.1 and `spikes/B1/PLAN.md`)
- depends_on: [D-001, D-002, D-003, D-004, D-005, D-006] — Provisional depth 2 (B1 → D-005/D-006 → D-001), raise signed in brief Amendment v1.1

## OBS-001 — Observation (disclosure only): D-005 / D-006 scored on a survival-conditioned R
- Recorded: 2026-10-27 EDT, packet B1-M1 (authority `orch/owner-decisions/20261027-1810-AsiaShanghai-B1-M1-eval-metric-START.md` 73ea581b…). **Not a decision. Reopens nothing.**
- Observation: the upstream benchmark `norm_return` divides by the steps actually survived, so early termination is not penalised and can raise R (brief `docs/FOLLOWON_BRIEF_B1_EVAL_METRIC.md` 01ecb8c1… §2, §3.7). D-005 (P4 B0 non-inferiority, results 76507d8a…) and D-006 (P5 B2 retention ratios, results c184bb88… / class-2 d62dc0b7…) were scored on this same R. P4: 112/112 mask-0 clip evals failed. P5: 168/168. Median fail step ~60 (`orch/analysis/b1-eval-metric/p4p5_failstats.out` 4d677eec…).
- Consequence: D-005/D-006 stay Provisional as recorded. Any citation of them carries this caveat, and it is weighed before any packet builds on them. Re-scoring them would need its own sealed amendment and START.

## OBS-002 — B1 arms post-hoc re-score (M1), labelled; outcome of record unchanged
- Recorded: 2026-10-27 EDT, packet B1-M1. **Outcome of record stays B1 attempt-1 INCONCLUSIVE** (results 64644e3c…; CLOSE 5d8cf393…).
- Post-hoc (M1) line: `B1_M1_VERDICT label=post-hoc-M1 verdict=PASS outcome=KILL robust=true` (AULC_full x/s/m = 0.360 / 0.419 / 0.477; all 4 sensitivities KILL). Amendment d04aca27…, tool v1.1 cd32a0ac…, results b3a995e8…, report `orch/reports/VERDICT-P6-b1-arms-M1-posthoc-20261027.md` e1d9d11a….
- Reading: no evidence for the B1 transfer mechanism under a completion-aware metric. The KILL fires on the PLAN §5 no-margin leg (x−s = −0.059, under 1 SE) and on the x < m − 2SE leg by a 0.008 margin. Provisional, single-candidate; depth A1.1-1 unchanged. Any action on it is a Manager decision.
