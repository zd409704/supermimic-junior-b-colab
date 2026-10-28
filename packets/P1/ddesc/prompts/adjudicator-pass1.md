You are the bound ADJUDICATOR for design packet D-DESC (method: "Orchestrating AI Research Teams" v1.1, section 4 Step 4). You authored no candidate and will not run the spike. Everything you need is inline below; do not use tools and do not read files.

PROCEDURE (follow exactly)
1. Eligibility gates first: for each candidate, check hard constraints H1-H6 of the brief. Any violation => Reject that candidate (state which constraint and the evidence). Scores never offset a gate failure.
2. Score every ELIGIBLE candidate on each of the 9 rubric rows of brief section 6, integer 1-5. Every score <= 2 needs a concrete objection. Use the reviews as input but form your own judgement; reviews are objections, not scores.
3. Totals (max 45). Tie margin is 4.5 points.
4. Output Recommend / Alternate / Reject per candidate, one paragraph of rationale, and a Confounds paragraph (resource asymmetries, isolation risks, amendments; the brief and roster mention some).
5. Note any point where the candidates agree AND that agreement is already stated or implied by the brief (framed agreement; adds no weight).

The candidates are presented in this order: X then Y. Labels are neutral; model identity has been removed.

OUTPUT FORMAT (exactly this structure, markdown):
# D-DESC adjudication pass 1
## Gates
| Candidate | H1 | H2 | H3 | H4 | H5 | H6 | Eligible? | Evidence |
## Scores
| Row | X | Y | Objection for any score <= 2 |
(9 rows, then a TOTAL row)
## Outcome
- X: Recommend|Alternate|Reject
- Y: Recommend|Alternate|Reject
## Rationale
## Framed agreement
## Confounds
Then a final line in exactly this machine-readable form:
VERDICT_JSON {"pass": "1", "order": "X then Y", "X": {"eligible": true|false, "total": N, "outcome": "..."}, "Y": {"eligible": true|false, "total": N, "outcome": "..."}}

===== BRIEF (briefs/D-DESC.md, frozen) =====
# Brief D-DESC: morphology descriptor v2 and action-scale handling for the shared attention decoder

**Packet:** P1 / D-DESC (two-author design contest, method §4 Steps 1–5). **Stakes:** high (it decides whether the B0 attention checkpoints can serve as the B1 transfer source; SCHEME_PLAN §1 P1).
**Written:** 2026-10-25 EDT (America/Toronto) by the Orchestrator (Claude Code, `claude-opus`, P1 wake). The Orchestrator does **not** author on this packet.
**Method:** v1.1, sha256 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0`. Overlays: `method/local/README.md`, `method/local/OVERLAY-001-owner-colab-runner.md` (not used here; the D-DESC spike is CPU, agent-run).
**Decision cap:** Provisional. **Roster:** `roster.md` (program root), frozen with this brief before Step 2.
**Freeze:** this file is frozen when its sha256 is appended to `logs/seal.log` (event `FREEZE brief D-DESC`). Afterwards only appended `Amendment vN.M` blocks are allowed (method §10.4).

## 1. Inherited items (by ledger ID; method §13.3)

Ledger snapshot: `program-ledger.md` up to and including **P-B1**.

| ID | Binds as |
|---|---|
| X-001 (upstream reproduction pin) | Context. The pinned action/actuator code excerpts are in `packets/P1/ddesc/context/upstream-d9be385/` (identifiers mechanically redacted; see its README) |
| X-003 (owner home-humanoid asset, `assets/home_humanoid_mjcf/`) | Context. Read-only |
| D-001 (Junior-(B) decoder on unchanged WM loop) | **Explicit assumption** (Provisional, depth 1) |
| D-002 (eval + scheme: RV-4, RV-5, GAP-1..GAP-7) | **Explicit assumption** (Provisional, depth 1). This packet depends on D-001 and D-002 directly, not on a chain, so the depth-1 cap holds |

## 2. Problem statement

The attention decoder (`code/attention_policy.py`) keys each joint token by a 12-d morphology descriptor (v1: root-frame anchor xyz, axis xyz, default angle from `qpos0`, depth normalised by per-body max depth, side sign, limb one-hot). The same decoder weights are meant to drive the 29-DoF reference humanoid (B0) and later the **home humanoid** (22 hinges, ≈ half scale, no actuators in the MJCF; B1). v1 has four defects for that purpose (EVAL_REVIEW §6.3): GAP-1 default angle from `qpos0`, GAP-2 per-body depth normalisation, GAP-3 absolute metric anchors (≈ 2× scale shift), GAP-4 no actuator/limit/action-scale features. Separately, the meaning of one action unit differs per body (GAP-5).

**Decide, before B0:**
1. **Descriptor v2:** the exact feature list, each feature's computation from (compiled model, env default pose, per-joint actuator parameters), normalisation constants, and `morph_dim`.
2. **Action-scale handling (RV-5):** how one decoder output unit maps to a joint set-point on each body, and whether/how the scale enters the descriptor.

The pinned upstream code shows the env already applies a per-joint action scale `0.25 · effort_limit / stiffness` plus the default-pose offset (`context/upstream-d9be385/mjlab_ref29_constants.py`, `REF29_ACTION_SCALE`; `src_supermimic_envs_actions.py`). Per SCHEME_PLAN P1 note, a candidate that adds a **second** scaling layer must justify it against that fact; the default expectation is "verify the env scale, carry it in the descriptor".

## 3. Constraints and non-goals

**Hard constraints (violation ⇒ Reject at the eligibility gate):**
- H1. Decoder call signature unchanged: `forward(z, obs_hist, token_mask=None, morphology=None) -> (N, J)`; obs layout unchanged (term-major, H=10). No change to motion encoder, WM, critic or training loop.
- H2. `id_mode=morph` stays exactly permutation-equivariant: permuting joints (obs slices + descriptor rows) permutes actions. No feature may depend on array index.
- H3. Trainable-parameter change of the attention decoder ≤ 5% versus v1 (463 489 at J=29 defaults), and `mlp_matched` re-matches to ±5% by the existing solver.
- H4. Every descriptor feature must be computable **without motion data and without GPU** from: the compiled MuJoCo model, an env default pose vector, and per-joint actuator parameters (effort limit, stiffness/kp, damping/kd, action scale). For the home humanoid these inputs come from load-time assumptions (AS-1 gains, AS-2 default pose; SCHEME_PLAN §5); the descriptor function must take them as **arguments**, never read them from the owner XML (which has `nu=0`, no keyframe). A name-only synthetic fallback must still exist for CPU smoke.
- H5. Owner asset read-only. Plant-class naming only in prose and identifiers; reference the asset by directory and glob, not basename.
- H6. Integrates with the frozen seam: checkpoint `policy` state_dict layout preserved; the descriptor config is recorded in the sidecar JSON so eval rebuilds the same decoder.

**Non-goals:** tokenised per-joint goal encoders; shared multi-body WM/critic; retargeting; home-humanoid actuator gain selection itself (only the interface that receives it); any GPU run; any B0/B1 arm.

## 4. What each candidate delivers (Step 2)

One markdown file, `proposal.md`, in the author's own draft directory, containing in order:
1. **Feature table** for descriptor v2: name, dims, formula, inputs used, normalisation, which GAP it addresses.
2. **Action contract:** decoder output semantics; where scaling happens; what the descriptor carries; how this behaves on both bodies (give the expected per-joint scale ranges on the 29-DoF body from the pinned code, and the formula for the home humanoid given AS-1 gains).
3. **Function signature(s)** and pseudocode precise enough for a runner to implement on CPU in < 150 lines, including the synthetic fallback.
4. **Parameter-count impact** (estimate) and `morph_dim`.
5. **Transfer-readiness argument:** what a descriptor row for "the same functional joint" (e.g. left knee) looks like on both bodies, and which features are scale-free.
6. **Falsifiers:** at least two CPU-checkable observations that would show the design is wrong (these may be added to the spike PLAN by the Orchestrator, identically for the recommended candidate only).
7. **At least one serious rejected alternative**, with reason (method §11.5).
8. **Failure modes** (at least R7, R8 and a B0-fairness risk), each with a detectable signature.

Drafts must **not** state the author's model, vendor or tool identity (neutral-label adjudication, §4 Step 4). Length ≤ 1 800 words.

## 5. Interfaces / contracts

| Interface | Contract |
|---|---|
| Descriptor builder | `morphology_v2(model, joint_names, default_qpos, actuator_params) -> Tensor (J, morph_dim)`; row order == actuator order == obs joint order (S1). Exact argument names may differ but inputs may not exceed H4 |
| Synthetic fallback | name-only builder returning distinct rows of the same `morph_dim` |
| Decoder | `AttentionDecoderCfg.morph_dim` set from v2; nothing else in the decoder changes unless justified under "Complexity cost" |
| Action | Decoder emits a per-joint normalised offset; the per-body env maps it to a set-point (upstream: `raw · scale + default_offset`) |
| Sidecar | records descriptor version, normalisation constants and per-joint inputs |

## 6. Rubric (fixed before drafts; method §5 rows plus one packet row)

Each row 1–5; every score ≤ 2 needs a concrete objection. **Aggregation:** unweighted sum, max 45. **Tie margin:** 4.5 points (10% of max), plus the order-reversal rule (§4 Step 4 (b)). One adjudicator (third family), two passes with presentation order reversed.

| Row | Question for this packet |
|---|---|
| Constraint fit | Obeys H1–H6 and the non-goals? |
| Falsifiability | Do its falsifiers and the spike criteria (§7) fail clearly on CPU? |
| Evidence demand | Validatable on CPU now, without new GPU runs or owner data beyond AS-1/AS-2 inputs? |
| Failure modes | R7 (scale shift), R8 (action semantics), B0 fairness and BPTT-stability (R13) risks named with signatures? |
| Integrability | Fits the existing seam, sidecar, `mlp_matched` re-matching, upstream action pipeline without a second scale layer (or justifies one)? |
| Latency / criticality class | Descriptor is computed once per body (offline tier); no per-step cost increase beyond the morph MLP input width? |
| Complexity cost | Every added feature tied to a named GAP/RV; nothing decorative? |
| Reversibility | Can it be dropped back to v1 (or a feature ablated) without touching B0/B2 artifacts or the owner asset? |
| **Transfer-readiness across a ≈2× scale gap** | Do corresponding joints on the two bodies get comparable descriptors, with scale-dependent quantities normalised by a stated body length? |

**Eligibility gates (before ranking):** any H1–H6 violation ⇒ Reject. There are no Locked claims in the ledger, so no Grade-1/Grade-2 gate applies.

## 7. Spike criteria (recommended candidate only; CPU; method §4 Step 5)

Binding (from SCHEME_PLAN P1); the PLAN may add the recommended candidate's own CPU falsifiers (§4 item 6) but may not relax these:
- **S-1** v2 descriptor finite and with J distinct rows on both bodies: the 29-DoF reference (synthetic-name fallback on the box, because the upstream model is not on the box) **and** the home humanoid (from `assets/home_humanoid_mjcf/` via glob, with documented placeholder AS-1/AS-2 inputs).
- **S-2** Permutation-equivariance relative error < 1e-4 on both bodies.
- **S-3** Attention decoder parameter-count change ≤ 5% vs v1; `mlp_matched` within ±5% of the new attention count.
- **S-4** Owner asset sha256 (XML + 27 meshes per `mesh_manifest.json`) unchanged after the run.

The runner is `claude-sonnet` (roster), working only under `spikes/D-DESC/`, under a hashed `spikes/D-DESC/PLAN.md` (method §12.2).

## 8. Isolation, timing, degraded outcomes

- Isolation and publication: `roster.md` §Isolation (sequential drafting; sibling draft directory mode 000 and sibling transcript mode 000 while the other author drafts; tool-call logs audited for sibling paths; seal then publish-after-all under neutral labels).
- Budgets (wall clock, each): Author draft 30 min; each review 20 min; each adjudication pass 20 min; spike 30 min.
- **If D-DESC cannot run** (an author family unavailable): freeze descriptor v1 + FX-1..FX-4; record that B1 transfer arms need a retrained 29-DoF source (SCHEME_PLAN P1 degraded outcome).
- **If the adjudication is a tie:** P1 freezes with descriptor v1 + FX-1..FX-4; the tie goes to the Human lead; v2 then enters by change request **before P2**, so B0 never runs on an undecided descriptor.
- **If the spike fails:** the Alternate (if any) is spiked once; otherwise the degraded freeze above applies and the decision is recorded as spike-failed.

## 9. Readable context for authors (identical set for both)

`briefs/D-DESC.md`; `docs/EVAL_REVIEW.md`; `docs/SCHEME_PLAN.md`; `code/attention_policy.py`; `code/mlp_baseline.py`; `code/train_entry.py`; `code/tests/test_smoke.py`; `configs/colab_smoke.yaml`; `code/vendor/NOTES.md`; `packets/P1/ddesc/context/upstream-d9be385/*`; `assets/home_humanoid_mjcf/` (read-only; loadable with `.venv/bin/python` + mujoco 3.17). Authors may run CPU Python from `.venv` and write only inside their own draft directory. No network.

===== CANDIDATE X (packets/P1/ddesc/proposals/X.md) =====
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


===== CANDIDATE Y (packets/P1/ddesc/proposals/Y.md) =====
# D-DESC proposal — candidate Y

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


===== REVIEW OF CANDIDATE X (packets/P1/ddesc/reviews/on-X.md) =====
# D-DESC review of candidate X

Scope: objections against `packets/P1/ddesc/proposals/X.md` only. Brief: `briefs/D-DESC.md` (H1-H6, §6 rubric, §7 spike). I read the other proposal only for reference. Verification scripts were run from `/tmp` with `.venv/bin/python` on CPU. Nothing was written to `assets/`.

**Eligibility:** I found no H1-H6 gate violation. The objections below are major or minor.

## Objections

### O1. Whole-path hinge depth gives "the same" arm joints different depths on the two bodies (Transfer-readiness, major)
**Claim:** Hinge depth = "Number of hinges on root-to-joint path, including joint", /8 (§1). §5 only shows the left knee ("hinge depth 4/8" on both bodies).
**Problem:** The knee is the one case where this works. On the 29-DoF reference the arms hang off the torso, behind three waist hinges (waist yaw/roll/pitch). X's formula therefore gives arm joints depths 4..10. The home humanoid has no waist hinges, so its arm joints get depths 1..4. Every corresponding arm joint is offset by 3/8: elbow 7/8 on the reference vs 4/8 on the home body. The head joints (1..2) also have no counterpart on the reference. This is a GAP-2-style scale/topology leak, carried into the very feature that X lists as addressing GAP-2. The transfer argument in §5 never looks at the arms, so it misses it.
**Verified (home side):** `.venv/bin/python /tmp/ddesc_x_check.py`. Loads the single `assets/home_humanoid_mjcf/*.xml` and counts hinge ancestors inclusive. Result: shoulder_pitch 1, shoulder_roll 2, upper_arm 3, elbow 4; head_yaw 1, head_pitch 2; hip_pitch 1 ... calf 4, ankle_roll 6; max depth 6. The reference-side depth (waist chain above the shoulders) comes from X's own synthetic stage table and the pinned joint list. The reference model is not on the box.

### O2. The synthetic fallback contradicts X's own production depth definition (Evidence demand / Falsifiability, major)
**Claim:** `synthetic_v2` sets depth to `(stage+1)/8`, with arm stages 0..6 (§3).
**Problem:** The synthetic rows ignore the waist hinges, so synthetic arm depth is 1..7/8. The production builder would give 4..10/8 on the reference body (O1). S-1, S-2 and S-3 on the 29-DoF body run only on synthetic rows, so the spike checks a descriptor distribution the real B0 decoder will never see. The synthetic rows also hard-zero 8 of the 19 columns: default angle, two limit offsets, limited flag, and all four actuator features. On the reference body, the spike therefore never touches the GAP-4/GAP-5 columns. X's own falsifier 4 asks for "parameter gates" on "29 synthetic" joints, and that check is vacuous when the actuator columns are zero. The pinned constants are enough to fill the reference actuator columns and the KNEES_BENT default on CPU without the model. X does not do this.

### O3. Two of the four actuator columns are exact functions of the others (Complexity cost, major)
**Claim:** Effort `log1p(E/T)`, stiffness `log1p(kp/T)`, damping `log1p(kd/(T*t))` and scale `s/pi`. The builder enforces `require_close(s, 0.25*E/kp, rtol=1e-6)`.
**Problem:**
- Because that assert is mandatory, kp is fixed by E and s (`kp = 0.25E/s`), so the stiffness column carries no independent information.
- Under the upstream recipe (and AS-1 as X writes it: `kp = I*w^2`, `kd = 2*zeta*I*w`), kd/kp = 2*zeta/w is the same constant for every joint and both bodies. Within a body, the damping column is a fixed monotone function of the stiffness column.

The brief's Complexity row requires every feature to be tied to a GAP and to be non-decorative. Adding kp and kd under the GAP-4 label does not meet that bar.
**Verified:** `.venv/bin/python /tmp/ddesc_x_check2.py` recomputes the pinned gains. kd/kp = 0.0636620 for all four actuator groups (5020, 7520-14, 7520-22, 4010).

### O4. The scale-invariance falsifier is circular (Falsifiability, major)
**Claim:** Falsifier 2: "Halve a CPU fixture's spatial coordinates; scale effort/kp with Mg*L, kd with Mg*L*t ... Descriptor mismatch above 1e-6 falsifies the claimed similarity invariance."
**Problem:** Every actuator feature is defined as a ratio to T = M*g*L or T*t, taken from the same fixture. Scaling the inputs by exactly those quantities leaves the features unchanged by construction. The test can catch an implementation bug, such as a missing /L, but it cannot falsify the design. None of X's falsifiers checks whether real cross-body rows end up comparable. There is no envelope test showing that home actuator/limit features fall inside the reference range, and no mirror test. The only check that touches real geometry is "finite, distinct". The Falsifiability row needs at least one observation that could show the design is wrong.

### O5. The action-probe falsifier cannot be run on the box (Evidence demand, major)
**Claim:** Falsifier 3: "Noise-free env action probes at 0 and +-0.01 must reproduce default offset and slope (s_j) within 1e-6". This is also the R8 signature ("failed affine probes").
**Problem:** These probes need the mjlab env action manager, which is not installed. The brief requires falsifiers to be CPU-checkable now. As written, the main R8/double-scaling detector moves to Colab, after the decision. A CPU-checkable substitute exists and X does not give it: assert per joint name that the supplied `actuator_params` match the resolved REF29_ACTION_SCALE regex table (the pinned file is readable).
**Verified:** `.venv/bin/python -c "import mjlab"` gives `ModuleNotFoundError: No module named 'mjlab'`.

### O6. Anchors and limit offsets depend on the AS-2 placeholder pose, so pose choices show up as morphology (Transfer-readiness / Failure modes, minor-to-major)
**Claim:** Anchors come from forward kinematics at the env-default q*, and limit offsets are (lo-q*)/pi and (hi-q*)/pi.
**Problem:** On the reference body q* is KNEES_BENT (knee 0.669, ankle -0.363, elbow 0.6). The home placeholder is knee 0.3, ankle -0.2, elbow 0. Every distal anchor (ankle, arm chain) and every limit-offset pair therefore moves with an arbitrary AS-2 choice, on top of the explicit default-angle column. The pose ends up encoded in roughly 6 columns rather than one. R7 lists "AS-2 poses differ" but gives no threshold or test: the signature "corresponding-joint feature shifts" has no number attached.
**Check:** L itself is pose-robust. It stays 0.2824004 m at qpos0, at the placeholder, and with thigh = 0.5 and hip_roll = +-0.15 (`/tmp/ddesc_x_check.py`). The objection applies to the anchors and offsets, not to L.

### O7. The anchor origin is the root body frame, an arbitrary modelling choice that L does not normalise (Transfer-readiness, minor)
**Claim:** Anchor = R_r^T (p_j - p_r)/L.
**Problem:** Where the pelvis-frame origin sits is an authoring choice that differs between assets. Dividing by L normalises size but not this offset. The verified home left-knee anchor/L of (0.049, 0.289, -0.656) has a non-zero x component that may be an origin artefact. Centring on a body landmark such as the hip centre would remove it. Of the two problems in the rubric's Transfer row, X handles size and leaves the origin shift.

### O8. Effort-limit provenance is unstated, and the numbers match the owner XML (Constraint fit (H4) / Integrability, minor)
**Claim:** "Effort groups give arm s=2.5/kp, head 0.925/kp, leg 5.25/kp" (so E = 10 / 3.7 / 21 N*m). The builder "never infers them from owner XML".
**Problem:** These values are exactly the XML's `actuatorfrcrange` values. The builder itself takes them as arguments, so H4 holds at the function boundary. But the proposal never says AS-1 is the source, so a runner could reasonably hard-wire an XML read.
**Verified:** `grep -o 'actuatorfrcrange="[^"]*"' assets/home_humanoid_mjcf/*.xml | sort | uniq -c` gives 12 x +-21, 8 x +-10, 2 x +-3.7.

### O9. The R13 signature has no thresholds and the builder has no magnitude gate (Failure modes, minor)
**Problem:** "nonfinite gradients, activation extremes and persistent clipping" does not say what counts as extreme. Some features exceed 1 with no gate: reference wrist-yaw depth 10/8, and the home shoulder-pitch limit offset (-4.18-0)/pi = -1.33 (range verified). The builder bounds nothing besides finiteness and distinctness.

### O10. Minor wording and decorative items (Complexity cost / Integrability, minor)
- The "limited flag" is constant 1 on the home body: all 22 hinges are limited (verified). It is very likely constant on the reference too, so it spends a column on a case that does not occur.
- "Replacing only body-specific `morphology` and `scale` buffers": in the decoder, `scale` is the observation-term scale vector, not an action scale. The sentence invites exactly the second-scale-layer misreading that the brief warns about.
- `require_close(s, 0.25E/kp)` checks that the supplied dict is consistent with itself. It does not check the env, yet §2 calls it verification of "the actual env scale". If the B1 interface ever supplies a scale that does not follow the formula, the builder hard-fails. That may be the right choice, but the proposal should say so.

## Points that survive review
- The 29-DoF action-scale table is correct: 0.074501 / 0.350661 / 0.438577 / 0.547546 rad per unit, giving a range of 0.074501-0.547546. Linkage joints double both E and kp. Verified with `/tmp/ddesc_x_check2.py` from the pinned reflected-inertia formulas.
- Parameter counts are correct. morph_dim=19 gives 464,385 (+0.193% vs 463,489). `build_matched_mlp` returns (384,192,96,48) = 468,317 (+0.847%). H3/S-3 hold. Verified in the same script.
- The home-humanoid numbers are correct: L = 0.2824004 m, M = 15.862761 kg; left-knee anchor/L (0.0491, 0.2886, -0.6559), axis (0,1,0), limit offsets (-0.79005, 0.59906). The model has exactly one free joint, 22 hinges and one hinge per body, so the free-joint root lookup and one-hinge-per-body gate pass. Verified with `/tmp/ddesc_x_check.py`.
- The action contract matches the pinned code: `executed_raw*scale + offset`, optional clip, then `- encoder_bias` (mjlab actions l.218-223). Clean actions are observed and noisy executed actions are replayed. There is no second scale layer. Also correct: kp*s = E/4 per unit.
- H1, H2, H4 (function boundary), H5 and H6 are met as described. The signature is unchanged, all statistics (L, M) are set-symmetric and name-based, the builder takes gains and pose as arguments, the asset is referenced by glob, and the sidecar records version, constants and inputs.
- The proposal is 1,539 words (limit 1,800), includes a rejected alternative, and names R7, R8, R13 and a B0-fairness risk.


===== REVIEW OF CANDIDATE Y (packets/P1/ddesc/reviews/on-Y.md) =====
# D-DESC review of candidate Y

Candidate Y has an H2 gate violation in its specified synthetic fallback. Its unchanged decoder is equivariant when already-built descriptor rows are permuted, but that does not satisfy H2's separate prohibition on index-dependent features. Several additional objections concern the proposed falsifiers and reproducibility contracts.

Only the frozen brief, published proposals, permitted decoder/baseline code, and permitted upstream excerpts were read as review sources. The home model was loaded read-only through `assets/home_humanoid_mjcf/*.xml`. No reference model was available or substituted with recalled geometry.

**CPU verification.** The reproducible probes are in [check_claims.py](check_claims.py), with results in [check_results.txt](check_results.txt). From the program root, the command is:

```bash
.venv/bin/python -B packets/P1/ddesc/reviews-wip/on-Y/check_claims.py
```

The C-numbered results below refer to this command. These are independent implementations of Y's stated formulas, not execution of an unpublished candidate implementation. Home placeholders use the proposed effort/inertia groups, calf defaults of 0.4 rad, and other hinge defaults of zero. Scaling checks modify compiled arrays only in memory.

## Objections

### 1. The name-only fallback depends on input order

- **Rubric row:** Constraint fit.
- **Severity:** **gate-violation of H2**.
- **Text objected to:** §3: “v1 synthetic anchors/axis/side/limb; depth = order within (side, limb)”; §1: “never on array index.”
- **Why:** `synthetic_morphology` in the permitted decoder code increments a counter while traversing the input names. Its anchors depend on that counter too. Reusing those anchors and defining depth by order assigns different features to the same joint after input reordering. H2 explicitly forbids features depending on array index, including within a group. S-2 can conceal this defect if it only permutes an existing tensor instead of rebuilding from reordered names.
- **Verified by code, C1:** Reversing the 29 names changes the reconstructed descriptor by a maximum of **1.0** relative to the correctly permuted rows. Left hip pitch depth changes from **0.125 to 0.75**. With fixed decoder weights and appropriately permuted observations, directly permuting rows gives relative action error **2.33e-7**, while rebuilding the fallback gives **0.03118**, exceeding 1e-4. The probe uses inclusive depth; changing the depth origin cannot remove the order dependency.

### 2. F3 rejects an actual, correctly represented home-model asymmetry

- **Rubric row:** Falsifiability.
- **Severity:** **major**.
- **Text objected to:** F3: “each home left row equals its right counterpart under the mirror map … within 1e-4.”
- **Why:** The compiled asset is not exactly symmetric at this tolerance. A descriptor that faithfully records its limits fails the proposed test. This is a false rejection condition if F3 is added to the spike plan. The failure is independent of any ambiguity about how to reflect joint axes: the calf axes are both y axes, so the stated map leaves their limit columns unchanged.
- **Verified by code, C5:** Left calf limits are **[-2.182, 2.182] rad**, right calf limits **[-2.18, 2.18] rad**. After division by π, the maximum limit-column discrepancy is **0.000636620**, more than six times F3's tolerance. This is present in the owner model, not introduced by normalization or ordering.

### 3. Gain redundancy is assumed but not enforced by the input contract

- **Rubric row:** Failure modes.
- **Severity:** **major**.
- **Text objected to:** §1: “kp is omitted (redundant given τ, σ); kd is omitted because … [the ratio] is constant across joints and bodies”; §3: `warn if abs(sig - 0.25*tau/kp) > 1e-6*sig` and “env sigma stays authoritative.”
- **Why:** The permitted reference recipe supports the constant ratio for that recipe. It does not make it a property of arbitrary supplied AS-1 parameters. The public home helper even accepts `wn` and `zeta`. Changing `zeta` changes damping while leaving effort, kp, sigma, geometry, and every descriptor column unchanged. Similarly, once the sigma/kp relation is allowed to fail with only a warning, kp is no longer recoverable from the encoded effort and scale. The scale/offset startup comparison still passes when the descriptor and env share those same scale/offset values. Thus the interface accepts bodies with different control responses under identical descriptor rows, contrary to the stated redundancy rationale and quarter-effort contract. This is particularly relevant to R8 and R13.
- **Evidence:** Algebraic inspection of the feature formulas and helper arguments. **Verified by code, C3:** the pinned reference groups do all have `kd/kp = 0.063661977` seconds. That verifies the reference premise only; it does not validate or enforce the home-input assumption.

### 4. The geometric fallback is circular and retains an absolute length threshold

- **Rubric row:** Transfer-readiness.
- **Severity:** **minor**.
- **Text objected to:** §1 limb fallback “on anchor_hat”; §3 “None -> geometric rule after L, c (iterate once)”; side fallback `sign(round(p_y,3))`; summary “every feature is scale-free or divided by … L.”
- **Why:** Computing `anchor_hat` requires L and c, but computing L and c requires leg classification and limb-local depth. When the leg names are unknown, there is no specified initial classification from which the proposed single iteration can start. Also, rounding raw `p_y` to three decimal places introduces a metric threshold into the supposedly scale-free side feature. Both issues are latent in the advertised fallback, although the inspected home names are all recognized.
- **Verified by code, C7:** An unnamed joint at `p_y = 0.0008 m` receives side **+1**; the corresponding joint after halving the geometry receives **0**. F2 on the current named model does not exercise this branch. More generally, an incorrectly selected but consistently scaled leg subset can still pass F2, so F2 is not sufficient evidence that L measures the intended anatomy.

### 5. The stated feature bound can prevent the promised scale ablation

- **Rubric row:** Reversibility.
- **Severity:** **major**.
- **Text objected to:** §3: `if not scale_norm: L, c = 1.0, 0` followed by `assert ... abs(rows).max() <= 3.5`; §8: “scale_norm=False is the R7 ablation.”
- **Why:** The replacement L also enters `log_tau`. The unconditional magnitude assertion can reject the very ablation proposed to diagnose R7. This is a build failure, before any comparison of transfer performance is possible. The supplied pseudocode specifies no ablation exception or distinct bound.
- **Verified by code, C8, conditional on Y's own reference estimate:** Using the pinned wrist effort of **5 N·m** and Y's approximate reference **M = 35 kg, L = 0.65 m**, normal `log_tau` is **−3.10538**, but `scale_norm=False` makes it **−3.53617**, violating the bound. At L=1 this failure occurs for any mass above **33.75683 kg**. The actual reference mass was not verified locally; the objection is that Y's own worked assumptions already contradict the advertised ablation path.

### 6. The sidecar does not specify how to reconstruct ablated rows

- **Rubric row:** Integrability.
- **Severity:** **major**.
- **Text objected to:** §3: `rows[:, cols(ablate)] = 0`; returned `meta` lists constants, body statistics, names and joint inputs plus `sha256(rows)`; “eval rebuilds from the sidecar's per-joint inputs and checks sha256.”
- **Why:** The listed metadata omits `ablate`, the explicit normalization-mode setting, and the resulting descriptor matrix. In particular, identical recorded per-joint inputs can generate either normal or zeroed feature columns depending on an unrecorded argument. A hash can detect that eval rebuilt the wrong rows but cannot tell it which ablation to reconstruct. Recording only `attention.descriptor: v1|v2` does not distinguish these configurations. This leaves the H6 reproducibility obligation unresolved for the advertised ablations; the proposal needs an explicit persistence/reconstruction contract before those artifacts are reviewable. This is a specification gap, not a claim that an unseen loader has been tested and failed.

### 7. “25% effort at zero tracking error” misstates the controller semantics

- **Rubric row:** Transfer-readiness.
- **Severity:** **minor**.
- **Text objected to:** Summary: “one action unit means the same on every body: a set-point offset commanding 25% of that joint's effort limit at zero tracking error.”
- **Why:** For proportional control, `τ_p = kp(q_target − q)`. At zero tracking error that term is zero. The defensible identity is an **incremental** proportional torque of `kp·σ = τmax/4` for a one-unit action change at fixed joint state, before clipping or saturation. Equivalently, from `q=q_def` and zero velocity, a unit offset initially requests that proportional torque. It does not establish equal acceleration, tracking response, or damping behavior across bodies. The underlying affine scale contract survives; the stronger wording does not.
- **Evidence:** Direct algebra using Y's equation and the pinned action implementation. No dynamic rollout was run.

## Points that survive review

- **Action-scale arithmetic:** C3 reproduces the pinned scale values **0.074500870, 0.350661466, 0.438577314, 0.547546463**, with counts **4/4/16/5**. Source inspection confirms `KNEES_BENT_KEYFRAME`, knee default **0.669 rad**, and scaling in the env. Keeping clean action observations and noisy executed actions in their existing units is compatible with the excerpts.
- **Parameter budget and matching:** C2 confirms **463,489 → 464,001** attention parameters and **468,317** matched-MLP parameters at widths **(384,192,96,48)**. Both H3 thresholds pass. The feature table sums to 16 dimensions, and the extra trainable weights are confined to the first morphology projection.
- **Named home-body construction:** C4 finds **22 finite, distinct rows**, **L=0.2824 m**, **M=15.862761 kg**, and **nu=0**. The left-knee normalized anchor is approximately **(−0.00124, 0.28860, −0.50425)**, with depth **4/8** and `log_tau ≈ −0.04528`, consistent with Y's rounded example under the documented placeholders.
- **Conditional scale invariance and decoder equivariance:** C6 gives maximum row differences below **6e-16** at spatial scales 0.5 and 2 when masses scale as s³, effort as s⁴, and sigma is fixed. This supports the stated similarity test for the recognized home names. C1 and C4 also confirm the unchanged decoder passes 1e-4 when fixed descriptor rows and observations are permuted together; this does not rescue the fallback rebuilding defect.

