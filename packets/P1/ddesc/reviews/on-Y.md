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
