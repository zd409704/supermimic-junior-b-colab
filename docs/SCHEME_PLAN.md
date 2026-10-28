# SCHEME_PLAN: packets, arms, criteria and the B1 home-humanoid runnable test

**Packet that wrote this:** run-002-eval-scheme. **Written:** 2026-10-25 EDT (America/Toronto). **Decision cap:** Provisional.
**Method:** v1.1, sha256 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0`. Overlays: `method/local/README.md`, `method/local/OVERLAY-001-owner-colab-runner.md`.
**Reads with:** `docs/EVAL_REVIEW.md`, whose revisions are cited as RV-n, risks as R-n, blockers as BLK-n and gaps as GAP-n.

This is a **plan**. No multi-agent implementation has started. Every packet below from P1 onward is executed by a **later Claude Code orchestration wake**, which schedules Authors and runners under the method. Thresholds marked *draft* become binding only when the packet's `PLAN.md` is written and hashed into the seal log (method §12.2).

---

## 1. Packet sequence

```
P0 eval+scheme (DONE, this packet)
 └─ P1 scaffold freeze  (+ pre-freeze fixes FX-1..FX-4, descriptor-v2 design contest D-DESC)
     └─ P2 B0 Colab smoke             (owner-run, 1 seed)
         └─ P3 B0 PLAN seal            (thresholds frozen; human signs RV-1/RV-2/RV-8; paid-compute gate)
             └─ P4 B0 microbench       (3 seeds/arm)
                 └─ P5 B2 mask/ablation (reuses P4 ckpts + small ablation trainings)
                     └─ P6 B1 home-humanoid cross-embodiment
                          P6a B1-P0 asset readiness (CPU, box)   ← may run in parallel from P1 if Human lead approves
                          P6b B1-RT runnable test (Colab)
                          P6c B1 PLAN seal
                          P6d B1 transfer arms (Colab)
```

Default order is strictly sequential. **One optional parallelism:** P6a uses CPU only, consumes no motion data or GPU and touches only B1 infrastructure. The Human lead may approve starting it after P1. Without that approval it waits for the P5 gate.

### P0: Evaluation + written scheme. **DONE**
Artifacts: `docs/EVAL_REVIEW.md`, `docs/SCHEME_PLAN.md`, `briefs/B1-home-humanoid-cross-embodiment.md`, `orch/STATUS.md` (+ dated report), `method/local/OVERLAY-001-…`, `method-issues/ISSUE-001.md`, a DESIGN_REVIEW note, and a ledger entry D-002.

### P1: Scaffold freeze
- **Goal.** Turn the existing scaffold into a hashed, frozen baseline that B0 runs against. Fix only what B0 or a later B1 transfer would otherwise inherit as a defect.
- **Pre-freeze fixes** (single Author, `claude-sonnet`; one reviewer from a different family, `codex-astra` high, objections only):
  - FX-1 (GAP-1): the descriptor's default-angle column comes from the env default pose, not `qpos0`.
  - FX-2 (GAP-2): depth normalisation uses a fixed constant (for example, 8), not the per-body max.
  - FX-3: verify that the 4 clip names exist in the dataset listing. Replace any that do not, and record the replacements.
  - FX-4 (GAP-7): wording only. The `test_b1_*` docstring says "J-agnostic shape test".
- **D-DESC (two-author design contest, method §4 Steps 1–4).** Descriptor v2 (RV-4) and action-scale handling (RV-5). These must be decided **before B0**: if the descriptor changes after B0, the B0 attention checkpoints cannot serve as the transfer source for B1, and a 29-DoF source model would have to be retrained (+3 seeds of Colab). Brief: `briefs/D-DESC.md`, written by the Orchestrator in P1 before drafting. Roster: Author A `claude-opus`, Author B `codex-astra` high, adjudicator `agy` (third family), spike runner `claude-sonnet` (CPU spike: descriptor finite and distinct on both bodies, permutation-equivariance error < 1e-4 on both, param count change ≤ 5%). The rubric rows are §5 of the method, plus "transfer-readiness across a ≈2× scale gap".
  - *Note on RV-5:* if the upstream env already applies a per-joint action scale (expected), RV-5 reduces to "verify this, and put the scale in the descriptor". The contest should not invent a second scaling layer.
- **Freeze.** Write `packets/P1/FREEZE_MANIFEST.md` with the sha256 of every file under `code/`, `configs/`, `notebooks/` plus the runbook, and append it to `logs/seal.log`. After the freeze, any code change needs a change request (method §4 Step 6).
- **Done predicate.** Manifest exists, all CPU smoke tests pass (new log attempt file), D-DESC `decision.md` filled by the adjudicator.
- **Degraded outcome.** If D-DESC cannot run (no second family available), freeze with descriptor v1 plus FX-1..FX-4, and record that B1 transfer arms will need a retrained 29-DoF source. Decision stays Provisional.
- **Budget.** About 1 wake.

### P2: B0 Colab smoke (owner-run)
- **Runner.** The owner on Colab L4, under `OVERLAY-001`. The Orchestrator prepares `spikes/B0-smoke/PLAN.md` (pipeline-level criteria only) and the tarball.
- **Steps.** Runbook §1–§7 at 1 seed: upstream sanity, then `attention` and `mlp_matched`, then eval masks 0/0.1/0.2. Optionally 1 seed of `mlp_upstream`.
- **Must also capture.** Seam checks S1 (joint order assertion output), S2 (obs dim and layout), S3 (compile setting). Cost per update. Peak memory. Policy grad-norm series (M-6). `nvidia-smi` header. Every deviation (for example an R1 wheel substitution).
- **Accept (pipeline).** Runbook §8 "Smoke success" for both arms, plus S1/S2 asserted true.
- **Blocked.** R1 unresolved after the fallback, which means `BLOCKED.md` and a venue decision for the Human lead (owner GPU or a different runtime). S1 false is a bug: fix it under a change request and re-run the smoke as a new attempt.
- **No performance claim** comes from P2.

### P3: B0 PLAN seal
- The Orchestrator writes `spikes/B0/PLAN.md` from §2 below, with the thresholds filled in from P2 cost data. It is red-teamed by `codex-astra` high (objections only), then hashed into `logs/seal.log`.
- **Human lead signs:** RV-1 (non-inferiority gate), RV-2 (mask-fairness arms in B2), RV-8 (budget rule), and the **paid-compute gate** for P4/P5.
- `roster.md` is written under A.7 if P4 is treated as high-stakes. Recommended: runner = owner (Colab), adjudicator of the verdict = harness (machine-computed) plus `claude-sonnet` for the write-up. The Orchestrator does not adjudicate a spike it planned and another agent is not competing on; the harness verdict is binding.

### P4: B0 microbench. See §2
### P5: B2 mask/ablation. See §3
### P6: B1 home-humanoid cross-embodiment. See §4 and §5, and the brief `briefs/B1-home-humanoid-cross-embodiment.md`

---

## 2. B0: attention decoder vs matched MLP, single 29-DoF body

| Arm | Decoder | Seeds | Role |
|---|---|---|---|
| `attention` | Junior-(B), `id_mode=morph`, descriptor from P1 freeze | 3 | Arm under test |
| `mlp_matched` | MLP, params within ±5% | 3 | Comparator (gate) |
| `mlp_upstream` | Upstream-width MLP (~4.7 M) | 1 | Compute-heavier reference. Not a gate |

**Budget (RV-8).** Primary: equal env steps **and** equal policy updates per arm. Secondary: also report each arm's return at an equal wall-clock cap. Same compile setting, same `num_envs`, batch, H and `--env.anchor-obs` for all arms.

**Metrics.**
- M-1 R(arm): mean upstream normalised return over the clip subset, unmasked, at the end of the budget.
- M-2 Fail(arm): number of clips whose termination fires in eval.
- M-3 Cost: ms per policy update, peak GPU memory, env-steps/s.
- M-4 WM loss curve per arm (A5).
- M-5 Learning curve: R evaluated at 25/50/75/100% of the budget (needed later for AULC comparisons).
- M-6 Policy grad-norm per update, and clip fraction (A4/R13).

**Draft criteria (frozen in P3):**
- **Non-inferior (proceed):** R(att) ≥ R(mlp_matched) − δ, with δ = max(0.05, 2 × pooled seed SE), **and** no seed of the attention arm diverges (NaN, or grad-norm clipped on more than 50% of updates over the last 25% of training).
- **Superior (bonus, reported only):** R(att) − R(mlp_matched) ≥ max(0.02, 2 × pooled SE).
- **Inferior (kill candidate):** R(att) < R(mlp_matched) − δ. Combined with the B2 result in §3.
- **Divergence rule:** one pre-registered retry per diverging seed, with a lower LR (×0.5) applied to *both* arms in a re-run. The PLAN states this. A second divergence counts as inferior.
- **Inconclusive:** pooled-SE overlap with neither condition met, so the B2 result decides (§3). Seeds may not be added without a sealed amendment.

---

## 3. B2: robustness to missing tokens, on B0 checkpoints

| Arm | Source | Seeds | Note |
|---|---|---|---|
| `attention` ρ(f) | P4 checkpoints | 3 | Eval only |
| `mlp_matched` ρ(f), zero-fill | P4 checkpoints | 3 | Eval only |
| `attention_idx` | New training, `id_mode=index` | 1 (draft; 3 if budget allows) | Ablation: does the morphology keying matter? |
| `attention_mtrain` | New training, `train_mask_frac=0.1` | 1 | Trained-mask condition |
| `mlp_mind_mtrain` | New training, MLP with a per-joint mask-indicator input, `train_mask_frac=0.1` | 1 | Mask-fairness control (RV-2) |

- Metric: retention ρ(f) = R(mask f)/R(mask 0), at f ∈ {0.1, 0.2}. The same random masks (fixed seed list) are used for every arm. The root is never masked.
- Report **untrained-mask** (P4 checkpoints) and **trained-mask** (new trainings) separately.
- *Draft B2 gain:* ρ_att(0.2) − ρ_mlp(0.2) ≥ 0.05 in the untrained-mask condition, **and** the gap is not removed by the trained-mask control (`attention_mtrain` vs `mlp_mind_mtrain` differ by ≥ 0.03). If only the untrained gap exists, record it as "absence-representation advantage, not robustness under equal training".
- Permutation: the CPU architectural check is repeated on GPU checkpoints (rel err < 1e-4, else bug).

**Combined B0+B2 gate to B1 (RV-1):**
- **Go** if B0 is non-inferior (or superior).
- **Go-with-caveat** if B0 is inconclusive and there is a B2 gain.
- **Kill** if B0 is inferior **and** there is no B2 gain. Then stop: no B1, no library scale-up. Write a negative-result note.
- Otherwise the Human lead decides.

---

## 4. B1: home-humanoid cross-embodiment arms (after B1-RT passes)

Scope (RV-3): the shared decoder transfers. Encoder, WM, critic, env config and reference motion are per body. Zero-shot whole-policy transfer is out of scope by construction.

| Arm | Decoder init on home humanoid | Encoder / WM / critic | Seeds | Role |
|---|---|---|---|---|
| H-A-scratch | Random (attention) | New | 3 | From-scratch baseline for the architecture |
| H-M-scratch | Random (mlp_matched sized for J=22) | New | 3 | Replicates B0 on body 2 |
| **H-A-xfer** | **P4 attention checkpoint (29-DoF)**, full fine-tune | New | 3 | **Arm under test** |
| H-M-xfer | P4 mlp_matched checkpoint. Input/output rows mapped by joint semantics (20 of 22 joints have a counterpart). Unmapped rows (head) start fresh. Hidden layers copied | New | 3 | **Strongest fair transfer baseline** |
| H-A-frozen | P4 attention checkpoint, decoder **frozen** | New | 1 | Diagnostic: how body-general is the decoder? No pass/fail |
| H-A-xfer-noscale | As H-A-xfer, with descriptor scale-normalisation off | New | 1 | Ablation for R7. Only if descriptor v2 has scale normalisation |

**Budget.** Equal env steps per arm. Draft: 1.0× the P4 per-arm budget. The 0.5× and 0.25× points come from the learning curve (M-5).

**Primary metric.** AULC: area under the normalised-return learning curve over the shared budget, evaluated at 10 equally spaced points. Secondary: R at 25% budget (early transfer) and R at 100%.

**Draft criteria (frozen in P6c):**
- **Cross-embodiment signal:** AULC(H-A-xfer) ≥ 1.2 × AULC(H-A-scratch) **and** AULC(H-A-xfer) ≥ AULC(H-M-xfer) − (2 × pooled SE). Positive transfer is required, and attention transfer must be at least as good as mapped-MLP transfer.
- **Architecture-specific transfer advantage (stronger claim):** additionally, AULC(H-A-xfer) − AULC(H-M-xfer) ≥ 2 × pooled SE.
- **Kill (cross-embodiment claim):** AULC(H-A-xfer) ≤ AULC(H-A-scratch) (no positive transfer) **or** AULC(H-A-xfer) < AULC(H-M-xfer) − 2 × pooled SE. Then stop the cross-embodiment line. B0/B2 findings stand on their own.
- **Claim scope language (mandatory in every write-up):** "decoder-weight transfer between two rigid humanoids, with per-body motion encoder, world model and critic; references produced by route RT-a/RT-b".

---

## 5. B1 runnable test (B1-RT): concrete definition

**Purpose.** Prove that the home humanoid is a working second plant in this stack before any B1 arm spends GPU money. B1-RT is infrastructure acceptance. It produces **no performance claim**.

**Asset contract.**
- Load path: the single `*.xml` under `assets/home_humanoid_mjcf/`, found by glob (exactly one match is required). Meshes resolve through the XML's `meshdir="meshes"` to `assets/home_humanoid_mjcf/meshes/` alongside it.
- The owner files are **read-only**. All modifications (actuators, default pose, removing the floors, contact excludes) are applied **at load time** through a `mujoco.MjSpec` edit, or the mjlab entity config, in code under `code/` or `spikes/B1-RT/`. The owner XML sha256 (`856ce7021f0adda213b598c6db8b6efe3d298360931a7e7612aba21787076d82`) and the 27 mesh sha256s in `mesh_manifest.json` are checked before and after every run.
- Prose and new identifiers use "home humanoid" (for example `home_humanoid_cfg`). Exported filenames are referenced only through the glob and the directory path.

**Assumptions B1-P0 must document** (each one is a named line in `spikes/B1-RT/ASSUMPTIONS.md`):
- AS-1 actuator gains: armature is 0 in the MJCF (BLK-2). Choose kp/kd from an assumed reflected inertia per joint group (arm, head, leg) and natural frequency/damping ratio following the upstream recipe. Effort limits come from the MJCF `actuatorfrcrange` (±10 / ±3.7 / ±21 N·m). If the owner supplies motor data, it replaces the assumption.
- AS-2 default pose: knees and hips slightly flexed. Shoulder roll abducted enough to clear the wrist–hip/thigh contacts (BLK-4).
- AS-3 tracked/termination bodies: base, torso, both wrists, both ankle-roll links, head pitch link. Ankle sites are foot keypoints.
- AS-4 retarget route: RT-a by default (EVAL_REVIEW §4.3), with the joint correspondence table and axis-sign checks written out explicitly.

**Checks.** RT-1..RT-5 run on CPU on the research box; RT-6..RT-8 on Colab.

| ID | Check | Pass criterion | Venue |
|---|---|---|---|
| RT-1 | Load + integrity | Compiles. 1 free + 22 hinge joints. 28 bodies. XML and all 27 mesh hashes match. Owner files unchanged after the run | CPU |
| RT-2 | Load-time overlay | After the spec edit: `nu = 22`, one position actuator per hinge with force range = `actuatorfrcrange`. No embedded floor geoms (scene floor only). Self-contacts at the default pose = 0. Actuator order == hinge order == descriptor row order (S1 for body 2) | CPU |
| RT-3 | PD stand | Zero action (targets = default pose) for 2.0 s from a settled start: base-height drop < 0.03 m, \|roll\|, \|pitch\| < 0.10 rad, both feet in contact at the end. Repeat at kp × 0.5 and × 1.5 (R11): record them, and they must not NaN. Nominal must pass | CPU |
| RT-4 | Retarget QA, per smoke clip, route RT-a | Joint-limit clipping: ≤ 10% of frames have any joint clipped by > 0.05 rad. Foot penetration p95 ≤ 0.01 m. Stance-foot skate speed p95 ≤ 0.10 m/s. Root height within [0.6, 1.1] × the default standing height. A clip that fails is replaced or routed to RT-b. **≥ 3 of 4 clips must pass**, else switch to RT-b and re-run | CPU (Colab if the data cannot be on the box) |
| RT-5 | Reference-PD replay probe | Drive PD to the reference joint targets with the root free. Record time-to-fall per clip. **No pass/fail** (a difficulty baseline). Must finish without NaN | CPU |
| RT-6 | MuJoCo Warp parity | The same overlaid model in the mjlab env on GPU: S1 assertion true. A 1-s zero-action rollout keeps base height within 0.01 m of CPU MuJoCo | Colab |
| RT-7 | Train smoke | Per-body encoder/WM/critic, 1 seed each of `attention` and `mlp_matched` (J=22), 0.5 h. No NaN or exception. WM loss decreases. Final train return > post-warmup return. Checkpoint and sidecar written | Colab |
| RT-8 | Eval smoke | Whole-clip benchmark JSON for both arms at masks 0/0.1/0.2. The **transfer-load check** also passes: the P4 attention checkpoint loads into the J=22 decoder with no shape errors, and the P4 MLP checkpoint loads through the row mapping | Colab |

**B1-RT passes** when RT-1..RT-4 and RT-6..RT-8 pass and RT-5 is recorded. Outputs go to `spikes/B1-RT/` (`runs.log`, `results.json` with one key per RT-id and a boolean `pass`, `ASSUMPTIONS.md`, `deviations.md`). There are no motion files and no checkpoints in the tree.

---

## 6. Blockers (status at 2026-10-25 14:2x EDT, verified on CPU)

| ID | Blocker | Status | Cleared by |
|---|---|---|---|
| BLK-0 | GPU venue: the box has no NVIDIA GPU | Open | Owner runs Colab (P2) |
| BLK-1 | Home-humanoid MJCF has **zero actuators** (`nu = 0`) | **Open (still true)** | RT-2 overlay (P6a) |
| BLK-2 | Armature = 0 on all DoFs. No motor data | Open | AS-1 assumption or owner motor data |
| BLK-3 | No reference motion for the home humanoid | Open | RT-a retarget + RT-4 QA |
| BLK-4 | Self-contact at qpos0 (wrists vs hip/thigh, up to 8.6 mm penetration) | Open | AS-2 default pose / contact excludes |
| BLK-5 | Two embedded floor planes in the MJCF | Open | RT-2 spec edit |
| BLK-6 | No keyframe/default pose | Open | AS-2 |
| BLK-7 | Encoder/WM/critic sized to 29-DoF (goal 680/689, state 71) | Open | Per-body configs (P6a/P6b). Expected state 57 to be verified |
| BLK-8 | The tracking env config names 29-DoF bodies | Open | AS-3, per-body env config |
| BLK-9 | B0+B2 gate (§3) | Open | P4/P5 |
| BLK-10 | Provisional depth-2 chain (B1 → B0 → D-001), method §13.3 | Open | Human lead signs the raise in the B1 brief, or Locks D-001 (RV-7) |
| BLK-11 | LAFAN1 ND licence: private runtime adaptations | Open (confirmation) | Human lead confirmation (R10) |
| BLK-12 | Paid Colab compute | Open | Human gate before P4, P5 and P6d |

---

## 7. Roles and orchestration guidance for the later wake

| Packet | Orchestrator | Authors | Reviewer / red team | Adjudicator | Runner |
|---|---|---|---|---|---|
| P1 fixes | Claude Code (`claude-opus`) | `claude-sonnet` | `codex-astra` high | — (no contest) | `claude-sonnet`, CPU tests |
| P1 D-DESC | `claude-opus` (does not author) | A: `claude-opus` (separate process, §11.3 firewall), B: `codex-astra` high | cross red team | `agy` | `claude-sonnet` (CPU spike) |
| P2 / P4 / P5 / P6b / P6d | `claude-opus` | — | `codex-astra` high on each PLAN | harness verdict, write-up by `claude-sonnet` | **owner on Colab** (OVERLAY-001) |
| P6a B1-P0 | `claude-opus` | `claude-sonnet` (infra code) | `codex-astra` high | — | `claude-sonnet` CPU |

Rules the later wake must keep:
- Isolation for D-DESC: separate draft directories with no cross-read permission, a seal log, and publish-after-all (§11). If isolation cannot be enforced, the decision stays Provisional and the gap goes under Confounds.
- Every Colab result is deposited as an owner-provided raw bundle in `logs/colab/<date>/`, with its sha256 in `logs/seal.log` *before* any analysis.
- The harness prints a machine-readable verdict against the sealed thresholds. Prose never overrides it.
- No code edits after the P1 freeze without a change request. Runners stay inside `spikes/<id>/`.

## 8. Cost sketch (Colab L4 GPU-hours, draft)

| Packet | Runs | Approx. GPU-h |
|---|---|---|
| P2 | sanity 0.1 + 2–3 arms × 0.5 + eval | ≈ 1.5–2 |
| P4 | 7 runs × 0.5 + eval | ≈ 4–5 |
| P5 | 3 trainings × 0.5 + eval sweeps | ≈ 2–2.5 |
| P6b | 2 × 0.5 + parity/eval | ≈ 1.5 |
| P6d | 14 runs × 0.5 + eval | ≈ 8–9 |
| **Total** | | **≈ 17–20 GPU-h**, spread over many sessions (R6) |
