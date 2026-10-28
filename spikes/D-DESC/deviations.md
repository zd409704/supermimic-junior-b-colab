# D-DESC deviations / spec gaps resolved by the runner (1 execution used of 3; no bug fixes between attempts)

1. Armature formula: the pinned constants file only imports `reflected_inertia_from_two_stage_planetary` from mjlab (not on the box). Reconstructed as `r1*(g1*g2*g3)^2 + r2*g3^2 + r3` (fitted so that the four group kp/sigma values of Y s2 are reproduced; the 4010 group is exact, others within rounding). F1 passes with it.
2. Synthetic 29-DoF reference mass: PLAN gives no mass for the synthetic reference, but log_tau needs M. Used M = 35 kg (Y s5, "M ~ 35 kg") via the optional kwarg `total_mass` of `synthetic_morphology_v2`; L is taken from the synthetic anchors (0.5 m), not the 0.65 m of Y s5. With actuator_params None, M := 1 and log columns are 0 (Y s3).
3. Synthetic chain depth: 1-based stage from a name-keyed table (hip_pitch=1 ... knee=4), so that the "depth == 1" hip-centre rule of Y s1 applies; v1's 0-based order index is not used. Synthetic anchors use the v1 formulas with stage-1 as the v1 depth.
4. F3 mirror map: axis kept unchanged (pseudovector; the owner XML uses identical axes on both sides); for x/z-axis joints q_def is negated and (q_lo,q_hi) -> (-q_hi,-q_lo); y_hat and side negated. q_def negation is needed because the AS-2 placeholder has shoulder_roll +0.2/-0.2.
5. F2 scaling also scales body_ipos, geom_pos and body_inertia (s^5); kp is set to 0.25*tau/sigma0 so sigma stays fixed and the sigma-consistency warning stays silent.
6. R-1 timing: mean of 5 forward+backward calls after one warm-up, default torch threads, N=512, J=29 reference morphology (v1: `synthetic_morphology()`, 12-d).
7. Home inertia groups: leg = hip/thigh/calf/ankle, arm = shoulder/upper_arm/elbow, head = head_*. runs.log is appended by the harness itself.
