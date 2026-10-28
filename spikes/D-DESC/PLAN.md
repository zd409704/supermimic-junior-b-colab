# spikes/D-DESC/PLAN.md — CPU spike for the recommended descriptor v2 (candidate Y)

**Written by:** Orchestrator, P1 wake, 2026-10-25 EDT, before execution. **Method:** v1.1 §4 Step 5, §12.2. **Sealed** when its sha256 is appended to `logs/seal.log` (event `SEAL-PLAN spikes/D-DESC`).
**Runner:** `claude-sonnet` (roster). It writes **only** under `spikes/D-DESC/`. It receives this PLAN and the published proposal `packets/P1/ddesc/proposals/Y.md`, not the adjudication reasoning.

## 1. Mechanism under test

Candidate Y's descriptor v2 (`packets/P1/ddesc/proposals/Y.md` §1–§3), implemented as written, plus the specification points in §3 below. The runner implements it in `spikes/D-DESC/descriptor_v2.py` (a standalone module that imports `AttentionDecoder`, `AttentionDecoderCfg`, `count_params`, `permute_obs_history` from `code/attention_policy.py` and `build_matched_mlp`/`MLPDecoderCfg` from `code/mlp_baseline.py`, read-only). Nothing under `code/` is edited by the runner.

## 2. Fixed inputs

- **Home humanoid:** the single `*.xml` under `assets/home_humanoid_mjcf/` (glob; exactly one match), read-only. Joint order = compiled hinge order.
- **Home AS-1 placeholder** (Y §2): reflected inertia I = 0.01 (leg: hip/thigh/calf/ankle), 0.005 (arm: shoulder/upper_arm/elbow), 0.002 (head); ω_n = 2π·10; ζ = 2; τmax from the compiled `jnt_actfrcrange` upper bound per hinge; kp = I·ω_n², kd = 2ζ·I·ω_n, σ = 0.25·τmax/kp.
- **Home AS-2 placeholder default pose** (enters only `q_def`): hip_pitch −0.2, calf (knee) +0.4, ankle_pitch −0.2, l_shoulder_roll +0.2, r_shoulder_roll −0.2, all others 0 (rad).
- **29-DoF reference:** `DEFAULT_JOINT_NAMES` from `code/attention_policy.py`, through the synthetic fallback (the reference MJCF is not on the box), with actuator parameters from `ref29_actuator_params` built from `packets/P1/ddesc/context/upstream-d9be385/mjlab_ref29_constants.py` (Y §2 table; the armature formula in that file, ω_n = 2π·10, ζ = 2; waist pitch/roll and ankles use the doubled 5020 group) and the knees-bent default pose from the same file.
- Decoder config: `AttentionDecoderCfg` defaults with `morph_dim = 16`. torch seed 0 for all random tensors; batch N = 8.

## 3. Specification points the runner implements (from the adjudication; they apply to Y only)

1. `synthetic_morphology_v2` must be order-invariant: depth and synthetic anchors derive from a fixed semantic stage table keyed by joint name, never from position in the input list.
2. The `meta` dict records `scale_norm`, `ablate` and the built descriptor matrix (plus its sha256).
3. With `scale_norm=False`, only `(L, c)` in `anchor_hat` are replaced (L=1, c=0); `log_tau` keeps the measured L. The |x| ≤ 3.5 build bound stays on.

## 4. Checks, thresholds, verdict

The harness `spikes/D-DESC/run_spike.py` computes every check and prints one final line `SPIKE_VERDICT {json}` with one boolean per ID and `"pass": <all binding true>`. Prose never overrides it.

| ID | Binding? | Check | Threshold |
|---|---|---|---|
| S-1 | yes | v2 rows finite and J distinct (rounded 1e-5) on the home humanoid (J=22) and the 29-DoF synthetic reference (J=29) | all finite; distinct == J |
| S-2 | yes | permutation-equivariance relative error `‖b − a[:,perm]‖/(‖a‖+1e-12)`, decoder in eval mode, 8 random perms, both bodies, descriptor rows permuted with the obs slices | max < 1e-4 |
| S-3 | yes | attention params at morph_dim 16 vs v1 (463 489); `mlp_matched` re-solved to the new count | change ≤ 5%; match within ±5% |
| S-4 | yes | sha256 of the owner XML and all 27 meshes in `mesh_manifest.json`, before and after the run | unchanged |
| F1 | yes | `ref29_actuator_params(DEFAULT_JOINT_NAMES)`: each of 29 names matched exactly once; σ values {0.0745, 0.3507, 0.4386, 0.5475} (±1e-3) with counts 4/4/16/5 | exact counts |
| F2 | yes | home model scaled in memory by s ∈ {0.5, 2} (body/joint positions and geom sizes ×s, masses ×s³, τ ×s⁴, σ fixed): v2 rows vs unscaled | max \|Δ\| < 1e-5 |
| F3 | yes | home mirror consistency: each `l_` row vs its `r_` counterpart under the mirror map in Y §6 | 1e-4 on geometric/categorical columns; **1e-3 on the two range columns** (the owner XML's calf limits differ left/right by 2e-3 rad; known before execution, see `packets/P1/ddesc/reviews/on-Y.md`) |
| F4 | yes | every home `log_sigma` and `log_tau` lies in [min_ref − ln2, max_ref + ln2] of the 29-DoF reference values | all inside |
| T-1 | yes | `synthetic_morphology_v2` built from a permuted name list equals the permuted rows of the original | max \|Δ\| = 0 |
| T-2 | yes | `scale_norm=False` builds without tripping the 3.5 bound on both bodies, and `meta` contains `scale_norm`, `ablate`, the matrix and its sha256 | true |
| R-1 | report | v1 vs v2 left-knee rows on the home humanoid; v2 per-column min/max on both bodies; decoder forward+backward time per call at N=512 for v1 and v2 | no threshold |

## 5. Attempts, command, outputs

- **Exact command (program root):** `.venv/bin/python -B spikes/D-DESC/run_spike.py`
- **Attempt cap:** 3 executions of that command. Every execution is appended to `spikes/D-DESC/runs.log` (UTC time, command, sha256 of `descriptor_v2.py` and `run_spike.py`, seed, the full `SPIKE_VERDICT` line). Bug fixes between attempts are allowed only where this PLAN or Y §1–§3 already specifies the behaviour (§12.2). Anything else is a plan gap: stop and write `spikes/D-DESC/BLOCKED.md`.
- **Outputs:** `spikes/D-DESC/results.json` (the verdict dict plus R-1 data), `spikes/D-DESC/runs.log`, `spikes/D-DESC/deviations.md` (may be empty). The runner does not edit this PLAN, the brief, the decision or any claim record.
