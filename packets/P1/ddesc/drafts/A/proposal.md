# D-DESC proposal

**Summary.** Descriptor v2 is 16-d; every feature is scale-free or divided by one stated body length L (hip-to-ankle vertical extent at `qpos0`). The decoder output keeps upstream semantics: the env maps it as `q* = q_def + σ·u` with its own `σ = 0.25·τmax/kp`. **No second scaling layer.** The descriptor carries `log σ` and a body-normalised effort limit. Since `kp·σ = 0.25·τmax`, one action unit means the same on every body: a set-point offset commanding 25% of that joint's effort limit at zero tracking error.

## 1. Feature table

Notation: `p_j`, `a_j` = joint anchor and axis in the root-body frame at `qpos0` (structural zero pose, so AS-2 cannot move geometry). `leg` = joints in limb class 0. `L = max_leg p_z − min_leg p_z`. `c` = mean anchor of leg joints with chain depth 1 (hip centre). `M` = total compiled mass. `g = 9.81`.

| # | Name | Dims | Formula | Inputs | Normalisation | GAP |
|---|---|---|---|---|---|---|
| 1 | anchor_hat | 3 | `(p_j − c) / L` | model | L, hip-centred origin | GAP-3 |
| 2 | axis | 3 | `a_j` | model | unit, scale-free | (v1) |
| 3 | q_def | 1 | env default joint angle (rad) | default_qpos | none | GAP-1 |
| 4 | q_lo, q_hi | 2 | `jnt_range / π` | model | π | GAP-4 |
| 5 | chain_depth | 1 | hinge ancestors (inclusive) **in the same limb class** / 8 | model tree, limb | constant 8 | GAP-2 |
| 6 | side | 1 | name prefix, else `sign(round(p_y,3))` | names, model | ±1/0 | (v1) |
| 7 | limb one-hot | 3 | leg / trunk+head / arm from names; fallback on anchor_hat: `z ≤ 0.1` leg, `abs(y) < 0.15` trunk, else arm | names, model | none | (v1) |
| 8 | log_sigma | 1 | `ln(σ_j / 0.25)` | action_scale | σ0 = 0.25 rad | GAP-4, GAP-5 |
| 9 | log_tau | 1 | `ln(τmax_j / (M·g·L) / 0.5)` | effort_limit, model | M·g·L, τ̂0 = 0.5 | GAP-4, GAP-3 |

`morph_dim = 16`. Each row depends only on the joint's own properties plus three set-symmetric statistics (L, c, M), never on array index (H2). kp is omitted (redundant given τ, σ); kd is omitted because `kd/kp = 2ζ/ω_n` is constant across joints and bodies under the upstream recipe (decorative). Limb-local depth removes the 3-hinge waist offset that would otherwise shift every arm joint between the bodies.

## 2. Action contract

- **Decoder output:** dimensionless `u_j`, no tanh, `last_gain = 0.01`; decoder unchanged.
- **Scaling happens only in the env** `JointPositionAction`: `q*_j = u_j·σ_j + default_joint_pos_j`. Execution noise (0.1), the action-rate penalty, the `last_action` observation and the WM action input all stay in `u` units, as upstream.
- **Descriptor carries** σ (log_sigma) and τmax (log_tau). One `actuator_params` object feeds both the env action config and `morphology_v2`; a startup assert compares env action-manager `scale`/`offset` per joint name with the sidecar (rel. tol. 1e-6).
- **29-DoF reference (pinned code, `0.25·e/s`, `s = armature·(20π)²`):**

| Group | Joints | τmax | kp | σ (rad/unit) |
|---|---|---|---|---|
| 4010 | wrist pitch/yaw ×4 | 5 | 16.78 | **0.0745** |
| 7520-22 | hip roll, knee ×4 | 139 | 99.10 | 0.3507 |
| 5020 (×2 for waist p/r, ankles) | shoulders, elbows, wrist roll ×10; waist p/r ×2; ankles ×4 | 25 / 50 | 14.25 / 28.50 | 0.4386 |
| 7520-14 | hip pitch/yaw ×4, waist yaw | 88 | 40.18 | **0.5475** |

  So log_sigma ∈ [−1.21, 0.78]. The env default pose is `KNEES_BENT_KEYFRAME` (knee 0.669), not `HOME_KEYFRAME`; q_def must come from `init_state`.
- **Home humanoid:** AS-1 supplies group reflected inertia `I_g`, `ω_n = 2π·10`, `ζ = 2`, τmax from the overlay force range (±21 / ±10 / ±3.7 N·m). Then `kp = I_g·ω_n²`, `kd = 2ζ·I_g·ω_n`, **`σ_j = 0.25·τmax_j / (I_g·ω_n²)`**. Placeholder `I = (0.01, 0.005, 0.002)` (leg/arm/head) gives σ ≈ 0.133 / 0.127 / 0.117, inside the reference envelope. The env receives this σ dict and AS-2 offsets exactly as upstream.

## 3. Signatures and pseudocode

```python
MORPH_DIM_V2 = 16
DESC_V2 = dict(version="v2", sigma0=0.25, tau_hat0=0.5, depth_c=8.0, range_c=math.pi, g=9.81)

@dataclass(frozen=True)
class ActuatorParams:  # per joint, joint_names order
    effort_limit: float; stiffness: float; damping: float; action_scale: float

def morphology_v2(model, joint_names, default_qpos, actuator_params, *,
                  scale_norm=True, ablate=()) -> tuple[Tensor, dict]:
    d = MjData(model); mj_forward(model, d)            # qpos0 geometry
    R, p0 = xmat[1], xpos[1]
    P = R.T @ (xanchor[j] - p0); A = R.T @ xaxis[j]    # per joint j
    limb = limb_from_name(n); None -> geometric rule after L, c (iterate once)
    hinge_of_body = {jnt_bodyid[h]: h for hinges h}
    depth_j = #bodies b on path jnt_bodyid[j] -> world with b in hinge_of_body
              and limb(hinge_of_body[b]) == limb_j
    leg = limb == 0; assert leg.sum() >= 2
    L = P[leg, 2].max() - P[leg, 2].min(); c = P[leg & (depth == 1)].mean(0)
    if not scale_norm: L, c = 1.0, 0                   # H-A-xfer-noscale
    M = model.body_mass.sum()
    tau, sig, kp = (ap.effort_limit, ap.action_scale, ap.stiffness)
    warn if abs(sig - 0.25*tau/kp) > 1e-6*sig          # env sigma stays authoritative
    rows = cat[(P-c)/L, A, default_qpos, jnt_range/pi, depth/8, side, onehot(limb),
               ln(sig/0.25), ln(tau/(M*g*L)/0.5)]
    rows[:, cols(ablate)] = 0                          # ablation keeps morph_dim
    assert finite(rows) and n_unique(rows, 1e-5) == J and abs(rows).max() <= 3.5
    return tensor(rows), dict(DESC_V2, L=L, c=c, M=M, names, q_def, range,
                              tau, kp, kd, sigma, limb_source, sha256(rows))

def ref29_actuator_params(joint_names) -> (list[ActuatorParams], default_qpos)
    # regex table from the pinned constants + KNEES_BENT pose

def home_actuator_params(joint_names, effort_limits, inertia_by_group,
                         wn=20*pi, zeta=2.0) -> list[ActuatorParams]
    # AS-1 interface; limits passed in, never read from the XML

def synthetic_morphology_v2(joint_names, default_qpos=None, actuator_params=None):
    # v1 synthetic anchors/axis/side/limb; depth = order within (side, limb);
    # L, c by the same rule on synthetic anchors; ranges (-0.5, 0.5);
    # actuator_params None -> log columns 0, M := 1
```

Integration: `load_morphology` dispatches on `attention.descriptor: v1|v2`; `decoder_sidecar` stores `meta`; eval rebuilds from the sidecar's per-joint inputs and checks `sha256`. `policy` state_dict keys are unchanged (the morphology buffer and `morph_mlp.0.weight` change shape only). About 110 lines.

## 4. Parameter impact

Only `morph_mlp[0]` widens: +4·128 = +512. Measured on CPU: 463 489 → **464 001 (+0.11%)**. The existing solver re-matches `mlp_matched` to 468 317 (384, 192, 96, 48), +0.93%. Per-step cost: a 16×128 instead of 12×128 projection per token; the descriptor is computed once per body.

## 5. Transfer-readiness

Left knee. Reference geometry is recalled from the public reference asset (indicative until checked on Colab); the home row was measured on CPU from `assets/home_humanoid_mjcf/*.xml`.

| Feature | 29-DoF ref (L ≈ 0.65 m) | Home (L = 0.282 m) |
|---|---|---|
| anchor_hat | ≈ (−0.08, 0.18, −0.51) | (0.00, 0.29, −0.50) |
| axis | (0, 1, 0) | (0, 1, 0) |
| q_def | 0.669 | AS-2 (placeholder 0.4) |
| q_lo, q_hi | ≈ (−0.03, 0.92) | (−0.69, 0.69) |
| chain_depth | 4/8 | 4/8 |
| side, limb | +1, leg | +1, leg ("calf") |
| log_sigma | 0.34 | placeholder −0.63 |
| log_tau | ≈ 0.22 (M ≈ 35 kg) | −0.05 |

v1 absolute knee z is about −0.43 m vs −0.19 m; v2 z_hat is −0.51 vs −0.50 (ankle pitch −0.97 vs −1.00). **Scale-free:** axis, q_def, ranges, chain_depth, side, limb, log_sigma. **L-normalised:** anchor_hat, log_tau. Remaining differences (hip width, knee range) are real morphology, not scale. CPU check: scaling the home model ×2 in memory (positions ×2, masses ×8, τ ×16, σ fixed) leaves v2 rows identical (max |Δ| = 0); unnormalised rows shift by up to 0.69. Home rows: 22 distinct, finite; permutation error 2.3e-7.

## 6. Falsifiers (CPU)

- **F1 env-scale reproduction:** `ref29_actuator_params(DEFAULT_JOINT_NAMES)` matches each of the 29 names exactly once and yields exactly the four σ values above with counts 4/4/16/5. Otherwise "carry the env scale" is mis-specified.
- **F2 scale invariance:** home rows vs the same model scaled ×s (s ∈ {0.5, 2}; positions ×s, masses ×s³, τ ×s⁴, σ fixed) agree to max |Δ| < 1e-5. Otherwise the normalisation leaks scale.
- **F3 mirror consistency:** each home left row equals its right counterpart under the mirror map (y_hat, side negated; for x/z-axis joints (q_lo, q_hi) → (−q_hi, −q_lo), axis reflected) within 1e-4.
- **F4 envelope:** under the documented AS-1 placeholder, every home log_sigma and log_tau lies inside the reference interval widened by ln 2 each side. Otherwise home rows are out of distribution for a 29-DoF-trained morph MLP; revisit AS-1 or the feature before B1.

## 7. Rejected alternative: decoder-side (second) scale layer

The decoder emits radians or normalised torque and multiplies by a per-joint scale buffer; env scale set to 1. Rejected: (1) it duplicates the env's `0.25·τ/kp`; either identical (pure complexity) or different (silently changed semantics). (2) Upstream noise, action-rate penalty, `last_action` observation and WM action input are defined in raw-`u` units; rescaling in the attention arm alone changes them for one B0 arm (fairness). (3) Checkpoint outputs would no longer be interchangeable with `mlp_matched` at eval.

Also rejected: **raw actuator features** (τ in N·m, kp). Torque scales roughly with L⁴, a 10–25× shift between bodies — GAP-3 again on actuator columns.

## 8. Failure modes

| Risk | Mechanism | Signature |
|---|---|---|
| R7 scale shift | L picks the wrong extent (leg joints mis-classed) | F2 fails; `meta.L` outside [0.2, 0.9] m; RT-a-paired anchor_hat distance > 0.15; H-A-xfer ≈ H-A-xfer-noscale |
| R8 action semantics | Env σ ≠ descriptor σ (AS-1 changed after build); or knee flexion sign opposite between bodies (home calf range is symmetric, so it cannot reveal this) | Startup scale/offset assert fails; sha mismatch at eval; FK check: +0.1 rad knee must move the ankle the same root-frame x direction on both bodies |
| B0 fairness (S1 order) | Descriptor rows in MuJoCo hinge order, env actuators in regex-group order: σ/τ attach to wrong joints, attention arm only | Per-name assert `robot.joint_names == meta.names` and per-name σ equality |
| B0 fairness (capacity) | v2 adds parameters to attention only | `mlp_matched` re-solved from the v2 count; sidecar logs both; ≤ 5% |
| R13 BPTT stability | Large descriptor magnitudes saturate the morph MLP | Build assert abs(x) ≤ 3.5 (extremes: ref wrist log_tau ≈ −3.1, home shoulder q_lo −1.33); policy grad-norm (M-6) vs a v1 control smoke; same clip for both arms |
| Name heuristics | Unfamiliar names push limb/side to geometry | `meta.limb_source` per joint; spike lists fallbacks |

**Reversibility:** `attention.descriptor: v1` restores the old path; `ablate=[...]` zeroes columns without changing morph_dim; `scale_norm=False` is the R7 ablation. Nothing touches the owner asset or B2 artifacts.
