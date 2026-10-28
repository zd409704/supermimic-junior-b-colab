# D-DESC proposal — candidate X

1. **Feature table**

Adopt a 19-dimensional descriptor, computed once per body. D-001 and D-002 remain explicit Provisional assumptions. Let $q^*$ be the supplied full env-default qpos vector. Forward kinematics at $q^*$ gives anchors $p_j$, axes $u_j$, and floating-root position/rotation $p_r,R_r$. Identify the root through the unique free joint, never a body index.

Define $L$ as the bilateral mean of hip-roll–knee distance plus knee–ankle-pitch distance, measured between joint anchors at $q^*$. Resolve knee/calf aliases. Require both complete leg chains and $L>10^{-6}$ m. Let $M$ be summed mass in the root subtree, $g_*=9.81$ m/s², $T=Mg_*L$, and $t=\sqrt{L/g_*}$. These reference units require no motor-inertia estimate. Angles below are numerical radians.

| Feature | Dims | Formula and inputs | Normalization | Addresses |
|---|---:|---|---|---|
| Anchor | 3 | $R_r^T(p_j-p_r)/L$; model, default pose | Body length $L$ | GAP-3 |
| Signed axis | 3 | $R_r^Tu_j$; model, default pose | Unit length; preserve sign | Existing geometric identity, RV-4 |
| Default angle | 1 | $q^*_j/\pi$; supplied default | Fixed π rad | GAP-1 |
| Hinge depth | 1 | Number of hinges on root-to-joint path, including joint | Divide by fixed 8; no clipping | GAP-2 |
| Side | 1 | left/l_ = +1; right/r_ = −1; central = 0 | Fixed name semantics | Existing identity |
| Limb | 3 | One-hot leg, central, arm; joint name | Fixed vocabulary below | Existing identity |
| Limit offsets | 2 | $(q_{min}-q^*)/\pi,(q_{max}-q^*)/\pi$; compiled hard limits | Fixed π rad; zeros if unlimited | GAP-4 |
| Limited flag | 1 | Compiled `jnt_limited` | Boolean | GAP-4; disambiguates zeros |
| Effort authority | 1 | `log1p(effort/T)`; supplied joint effort | Body torque unit | GAP-4, RV-4 |
| Stiffness | 1 | `log1p(kp/T)`; supplied joint gain | Torque per radian | GAP-4, RV-4 |
| Damping | 1 | `log1p(kd/(T*t))`; supplied joint gain | Torque-time per radian | GAP-4, RV-4 |
| Action scale | 1 | $s_j/\pi$; supplied resolved env scale | Fixed π rad/action-unit | GAP-5, RV-5 |

Leg vocabulary: hip, thigh, knee, calf, ankle; central: waist, torso, head, neck; arm: shoulder, upper_arm, elbow, wrist, hand. Reject unknown or ambiguous classifications. No fitted statistics, row-index features, or silent clipping. Positive effort/kp/scale and nonnegative kd are mandatory. Inputs are joint-space quantities after transmission resolution, not motor-shaft values.

2. **Action contract**

The unchanged decoder emits an unbounded, dimensionless normalized offset $a_j$. The existing env alone computes $q^{target}_j=q^*_j+s_j(a_j+\epsilon_j)$, followed by its configured target clipping and encoder-bias correction. Preserve clean previous-action observations and executed noisy actions for replay, as in the pinned action implementation. No new tanh, limit clamp, output multiplier, or observation rescaling.

Pinned constants give $s=0.25E/kp$, with these radians/unit values on the 29-DoF reference humanoid:

| Joints | Scale |
|---|---:|
| Wrist pitch/yaw | 0.074501 |
| Hip roll, knee | 0.350661 |
| Shoulder pitch/roll/yaw, elbow, wrist roll | 0.438577 |
| Ankle pitch/roll, waist pitch/roll | 0.438577 |
| Hip pitch/yaw, waist yaw | 0.547546 |

Paired linkage actuators double effort and stiffness together, preserving their ratio. Thus the range is **0.074501–0.547546**. These values were recomputed on CPU from the pinned inertia/gain formulas; actual runtime resolution still needs verification.

For the home humanoid, AS-1 supplies $kp_j,kd_j,E_j$; $s_j=0.25E_j/kp_j$. With AS-1's assumed inertia $I_j$, $kp_j=I_j\omega_j^2$, $kd_j=2\zeta_jI_j\omega_j$. Effort groups give arm $s=2.5/kp$, head $0.925/kp$, leg $5.25/kp$. This proposal chooses no production gains. The builder consumes these arguments and AS-2's pose; it never infers them from owner XML defaults, damping, or missing actuators.

At nominal pose and zero velocity, one unit requests an incremental proportional torque of $E/4$, before saturation. This does not imply equivalent acceleration or tracking performance. Verify the actual env scale and offset against supplied values before B0; descriptor limits describe mechanics and do not introduce control clipping.

3. **CPU implementation and integration**

```python
def morphology_v2(model, joint_names, default_qpos, actuator_params):
    # actuator_params: name -> {effort, kp, kd, scale}; SI units
    require_unique_names_and_exact_parameter_coverage()
    # joint_names is the env obs/action order; preserve it verbatim.
    require_full_finite_qpos_and_valid_root_quaternion()
    root = body_of_unique_free_joint(model)
    ids = resolve_names_to_hinges(model, joint_names)  # fail on missing
    require_one_hinge_per_joint_body_and_root_ancestry(ids)
    data = MjData(model)
    data.qpos[:] = default_qpos
    mj_forward(model, data)
    # Semantic lookup uses all model hinges, independent of row ordering.
    L = mean(leg_lengths(data, aliases={"calf": "knee"}))
    M = sum_mass_of_root_subtree(model, root)
    require(M > 0 and L > 1e-6 and finite(M, L))
    T, t = M * 9.81 * L, sqrt(L / 9.81)
    rows = []
    for name, j in zip(joint_names, ids):
        E, kp, kd, s = validated_params(actuator_params[name])
        require_close(s, 0.25 * E / kp, rtol=1e-6)
        q = default_qpos[model.jnt_qposadr[j]]
        limited = bool(model.jnt_limited[j])
        lo, hi = model.jnt_range[j] if limited else (q, q)
        if limited: require(lo < hi and lo <= q <= hi)
        rows.append(concatenate(
            root_anchor(j)/L, root_unit_axis(j), [q/pi],
            [hinges_on_ancestral_path(j)/8, side(name)], limb(name),
            [(lo-q)/pi, (hi-q)/pi, float(limited)],
            log1p([E/T, kp/T, kd/(T*t)]), [s/pi]))
    return checked_finite_distinct_float32_tensor(rows, width=19)

def synthetic_v2(joint_names):
    # Fixed semantic stages, never enumerate input rows for features.
    # leg: hip pitch/roll/yaw, knee, ankle pitch/roll -> 0..5
    # arm: shoulder pitch/roll/yaw, elbow, wrist roll/pitch/yaw -> 0..6
    # central: waist yaw/roll/pitch, head yaw/pitch -> 0..4
    # aliases: thigh=hip_yaw, calf=knee, upper_arm=shoulder_yaw
    rows = []
    for name in joint_names:
        side, limb, stage, axis = parse_fixed_semantic_table(name)
        row = zeros(19)
        row[:3] = [stage/8, side/4, (-1, 0, 1)[limb]]
        row[3:6] = axis  # roll=x, pitch/elbow/knee=y, yaw=z
        row[7:9] = [(stage+1)/8, side]
        row[9+limb] = 1
        rows.append(row)
    return checked_finite_distinct_float32_tensor(rows, width=19)
```

These helpers require only tree walking, name parsing and array arithmetic; the builder plus fallback fits within 150 implementation lines. Synthetic rows are explicit smoke fixtures, prohibited for production. Record their source flag.

Keep `forward(z, obs_hist, token_mask=None, morphology=None)`, H=10 term-major layout, and all `policy` state_dict key names. Change only morphology construction/configuration and the first morphology-layer width. Sidecar JSON stores version, feature order/formulas/constants, alias table, resolved joint order, full default qpos, per-joint parameters/limits, measured M/L, descriptor matrix, and decoder config. Eval rebuilds from this sidecar and checks the stored morphology buffer agrees. Missing metadata is an error.

B1 loads all learned decoder tensors exactly, replacing only body-specific `morphology` and `scale` buffers with target-body buffers; assert every other key and shape matches. No blanket permissive loading. Encoder, WM, critic and training loop remain unchanged by this packet.

4. **Parameter-count impact**

`morph_dim=19`: $7×128=896$ additional weights, no extra biases. CPU count: **464,385**, up **0.193%** from 463,489. Existing matching solver selects widths `(384,192,96,48)`, **468,317** parameters, **0.847%** above attention. Per-step cost increases only at the morphology MLP input; construction is offline.

5. **Transfer readiness**

Both left knees have side +1, leg one-hot, and hinge depth 4/8. Their signed axes and normalized anchors describe comparable anatomy without forcing identical rows. The pinned reference default knee is 0.669 rad; a documented smoke placeholder home pose can use 0.3 rad, hips −0.1, ankle pitch −0.2, shoulder roll ±0.2, others zero.

CPU inspection of `assets/home_humanoid_mjcf/`, loaded through its single `*.xml` glob, gives this placeholder $L=0.2824004$ m and $M=15.862761$ kg. Its left-knee anchor/L is approximately `(0.0491, 0.2886, −0.6559)`, axis `(0,1,0)`, default/π 0.09549, limit offsets `(−0.79005,0.59906)`. Placeholder leg kp=40 gives scale 0.13125; this is a plumbing example, not AS-1 acceptance. Reference geometry is unavailable locally; synthetic rows cannot establish geometric agreement.

Geometry, angles, depth and categorical features are invariant under uniform geometric rescaling at the same pose. Actuator features are dimensionless: they match only when effort/gains scale with the stated body units. Actual physical differences remain visible. This supports decoder-weight transfer, not whole-policy or guaranteed performance transfer.

6. **Falsifiers**

- Reorder names/parameter inputs before building: rows must reorder exactly. Decoder relative permutation error `norm(b-a[:,perm])/(norm(a)+1e-12)` must remain below 1e-4 on both bodies, including jointly permuted masks. Any failure rejects implementation/design.
- Halve a CPU fixture's spatial coordinates; scale effort/kp with $Mg_*L$, kd with $Mg_*Lt$, and preserve angles/scale. Descriptor mismatch above 1e-6 falsifies the claimed similarity invariance.
- Noise-free env action probes at 0 and ±0.01 must reproduce default offset and slope (s_j) within 1e-6 away from clipping. Wrong slopes expose double scaling or order errors.
- Require finite, distinct rows for 29 synthetic and 22 real joints, parameter gates, and unchanged XML plus 27 mesh hashes against the manifest. Also perturb supplied default pose: defaults and kinematics must respond rather than reuse qpos0.

7. **Rejected alternative**

Mapping outputs directly to fractions of joint range offers comparable limit utilization. It changes exploration, action penalties and WM action semantics relative to the pinned baseline; layering it onto existing scaling also multiplies scales twice. Retain upstream units and expose limits instead. Raw SI effort/gain features are simpler, but conflate body size with relative actuator authority.

8. **Failure modes**

R7: proportions or AS-2 poses differ despite size normalization; detect corresponding-joint feature shifts and L sensitivity. R8: stale gains/scale, sign or ordering mismatch; detect failed affine probes and quarter-effort checks. R13: large feature values saturate attention or destabilize BPTT; detect nonfinite gradients, activation extremes and persistent clipping in the existing toy rollout and later training logs.

B0 fairness risk: attention alone receives incorrect ordering or defaults; assert env obs/action/descriptor name equality, compare physical target probes across arms, rematch parameters, and retain equal updates, initialization gain and action processing. Synthetic metadata in a production sidecar is a hard failure.

Versioned sidecars retain v1 loading. Feature ablations zero selected v2 columns without changing shapes; scale-normalization ablation replaces L by 1 for anchors. Use separate configurations/artifacts, preserving frozen B0/B2 outputs and the read-only owner asset.
