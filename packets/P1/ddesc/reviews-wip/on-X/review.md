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
