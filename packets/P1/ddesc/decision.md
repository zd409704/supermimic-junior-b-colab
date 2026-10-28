# D-DESC decision — descriptor v2 and action-scale handling

**Packet:** P1 / D-DESC. **Method:** v1.1, sha256 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0`. **Brief:** `briefs/D-DESC.md` (sha256 `f2458a0e…`). **Roster:** `roster.md` (sha256 `5be8a85d…`).
**Status:** **Provisional** (decision cap; no Lock authorization). Spike: see §5 (filled after the spike runs).
**Formatting:** the Orchestrator formatted this file. The scores and outcomes below are copied from the bound adjudicator's raw outputs, which are reproduced verbatim at the cited paths and sealed in `logs/seal.log`. The Orchestrator did not alter any score.

## 1. Candidates

| Label | Author slot | Sealed draft sha256 | Published copy |
|---|---|---|---|
| X | Author B (OpenAI Codex, gpt-6-astra, high) | `b7d3b1b6…95fd84` | `proposals/X.md` |
| Y | Author A (Claude, claude-opus-5-5, medium; Agent-tool subagent) | `f1df6b40…65dd6bf` | `proposals/Y.md` |

Labels were assigned by the pre-declared rule (lower sha256 → X). The label map (`label-map.md`) was mode 000 during adjudication.

## 2. Adjudication (bound adjudicator: `agy`, resolved model "Gemini 4 Argon (High)", third family)

Raw outputs: `logs/p1/ddesc/adj-pass1-attempt1.out` (order X→Y), `logs/p1/ddesc/adj-pass2-attempt1.out` (order Y→X).

| Row | Pass 1 X | Pass 1 Y | Pass 2 X | Pass 2 Y |
|---|---|---|---|---|
| Constraint fit | 5 | 3 | 5 | 3 |
| Falsifiability | 2 | 3 | 2 | 3 |
| Evidence demand | 2 | 4 | 3 | 4 |
| Failure modes | 3 | 4 | 3 | 4 |
| Integrability | 4 | 4 | 4 | 3 |
| Latency / criticality class | 5 | 5 | 5 | 5 |
| Complexity cost | 2 | 5 | 2 | 5 |
| Reversibility | 5 | 3 | 4 | 3 |
| Transfer-readiness (≈2× scale gap) | 2 | 4 | 2 | 5 |
| **Total (max 45)** | **30** | **35** | **30** | **35** |

**Gates:** both candidates eligible in both passes (H1–H6 pass). The review of Y argued that Y's synthetic fallback breaks H2; the adjudicator ruled in both passes that H2 binds the production builder and decoder equivariance, and it scored the synthetic-fallback order dependence under Constraint fit instead.

**Tie test (brief §6, method §4 Step 4):** (a) margin 5.0 in both passes > tie margin 4.5; (b) no change of recommendation under order reversal; (c) single adjudicator, so no disagreement. **Not a tie.**

## 3. Outcome

- **Recommend: Y.** Descriptor v2 at 16 dims: hip-centred anchors normalised by leg extent L at `qpos0`, axis, env default angle, joint range/π, **limb-local** chain depth/8, side, limb one-hot, `ln(σ/0.25)`, `ln(τmax/(M·g·L)/0.5)`. Action scaling stays in the env only (`q* = q_def + σ·u`, `σ = 0.25·τmax/kp`). No second scaling layer.
- **Alternate: X** (19-d, whole-path depth, geometry at the default pose, kp/kd/limited columns).
- **Reject:** none.

**Rationale (adjudicator's, condensed; full text in the raw outputs).** Y handles the cross-body pitfalls better. It uses limb-local depth, so the 29-DoF body's 3 waist hinges do not shift every arm joint by 3/8. Its geometry is taken at `qpos0`, so AS-2 pose choices cannot leak into anchors or limits. Its anchors are hip-centred and L-normalised. It also uses fewer columns, none of them redundant. X adds redundant or constant columns (kp, kd, limited), has a falsifier that needs `mjlab` (not on the box), and its synthetic 29-DoF rows zero 8 of 19 columns. Y has specification defects that the adjudicator calls boundary fixes. The pass-2 rationale lists four tightenings for the spike PLAN, carried into `spikes/D-DESC/PLAN.md` §3.

**Framed agreement (no weight):** env-only action scaling and the four reference σ values; unchanged signature and state_dict keys; L-normalised anchors, depth/8 and M·g·L torque normalisation; AS-1/AS-2 passed as arguments. These were already implied by the brief and the pinned context.

## 4. Confounds

1. **Claude-family invocation gap.** Standalone `claude --model …` processes could not authenticate from the Orchestrator's shell. Author A and the reviewer of X ran as Claude Code Agent-tool subagents (fresh contexts, same model) instead of standalone CLI processes (`roster.md`).
2. **Same family as the brief writer.** The winning candidate Y comes from the Claude family, which is also the Orchestrator's family, and the Orchestrator wrote the brief and fetched the upstream context. The adjudicator was third-family and blind to labels, but a framing advantage for the brief writer's family cannot be ruled out.
3. **Isolation by sequencing + mode 000 + audit, not a read-allowlist.** Author A drafted before any Author-B output existed. While B drafted, A's directory and A's transcript directory were mode 000. Audits of both authors' tool logs found zero sibling-path hits and zero web calls (`logs/seal.log` AUDIT-A, AUDIT-B). Neither author was OS-restricted to the brief §9 read set.
4. **Declared handicaps.** Author A's harness exposed web tools (not used); Author B's sandbox had no network. B's wall clock started about 5 min later. Effort labels differ by vendor (catalog defaults).
5. **Reviewer framing.** The adjudicator noted that the reviews read as adversarial briefs (cross-family red team), and it discounted severity labels.
6. **Local evidence asymmetry.** The 29-DoF reference MJCF and `mjlab` are not on the box. Y's 29-DoF anchor table was recalled ("indicative until checked on Colab"), not measured.
7. **Close margin.** 5.0 vs a 4.5 tie margin. A single-point swing on any row would have produced a tie.
8. **Amendments:** none to the brief. Class-0: agy flag order (`logs/p1/amendments.log`).

## 5. Spike (Step 5)

Pre-registered plan: `spikes/D-DESC/PLAN.md` (hash in `logs/seal.log`). Result: see Amendment blocks below (appended after the run).

---

## Amendment v1.1 — spike result (appended 2026-10-25 ~15:21 EDT; Class 1, observation only)

- **Harness verdict** (`spikes/D-DESC/runs.log`, 1 of 3 allowed executions, seed 0): `SPIKE_VERDICT {"S-1": true, "S-2": true, "S-3": true, "S-4": true, "F1": true, "F2": true, "F3": true, "F4": true, "T-1": true, "T-2": true, "pass": true}`. **PASS** on every binding check of `spikes/D-DESC/PLAN.md`.
- Runner deviations: `spikes/D-DESC/deviations.md`. Orchestrator check of deviation 1 ("armature formula reconstructed"): the runner's `_armature` is `r0·(g0·g1·g2)² + r1·g2² + r2`. The pinned mjlab function `reflected_inertia_from_two_stage_planetary` (`context/upstream-d9be385/mjlab_utils_actuator.py` lines 25–34) asserts g0 = 1 and computes `r0·(g1·g2)² + r1·g2² + r2`. The two are **identical** for these inputs, so F1 is not circular. Deviations 2–7 fill points that the PLAN left open: the synthetic reference mass of 35 kg comes from Y §5, plus stage indexing and the mirror-map details. They affect only report/fixture values and F3/F4 fixtures. Under §12.2 they are plan gaps the runner resolved instead of writing `BLOCKED.md`. This is a process deviation and is recorded here; it does not change any binding threshold.
- **Outcome:** Y is adopted as descriptor v2 for the P1 freeze, Provisional. The 29-DoF reference rows on the box are synthetic. Real 29-DoF reference geometry and actuator parameters are verified only on Colab (seam checks S4/S5 in the frozen runbook).
