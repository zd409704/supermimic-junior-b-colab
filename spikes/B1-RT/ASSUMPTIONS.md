# B1-RT / B1-P0 assumptions (home humanoid as a second plant)

**Packet:** P6a (B1-P0 asset readiness, CPU). **Written:** 2026-10-26 ~19:30 EDT by the Orchestrator (`claude-opus`).
**Status:** Provisional. **Method:** v1.1 `9bdc872e…590afc0` + OVERLAY-001. **Scheme:** `docs/SCHEME_PLAN.md` §5.
**Code:** every value below lives in `spikes/B1-RT/home_humanoid.py` (single source; this file explains it).
**Owner asset:** `assets/home_humanoid_mjcf/` (single `*.xml` by glob, sha256 `856ce7021f0adda213b598c6db8b6efe3d298360931a7e7612aba21787076d82`; 27 meshes per `mesh_manifest.json`). Read-only. All changes below are made at load time on an `MjSpec`.

If the owner supplies motor data, a pose, or a motion route, it replaces the matching assumption through a sealed amendment.

---

## AS-1 Actuator gains (BLK-1, BLK-2)

- One position actuator per hinge (22), in MJCF hinge order, force range = the hinge `actuatorfrcrange`: legs ±21, arms ±10, head ±3.7 N·m.
- The MJCF armature is 0 and no motor data exists. Assumed reflected inertia per joint group, with the upstream recipe ω_n = 2π·10 rad/s, ζ = 2: kp = I·ω_n², kd = 2ζ·I·ω_n. The same armature is written into the joint (as mjlab `BuiltinPositionActuatorCfg` does).

| Group | Joints | I (kg·m²) | kp (N·m/rad) | kd (N·m·s/rad) | effort (N·m) | action scale σ = 0.25·effort/kp (rad) |
|---|---|---|---|---|---|---|
| leg | hip pitch/roll, thigh (yaw), calf (knee), ankle pitch/roll | **0.015** | 59.22 | 3.770 | 21 | 0.0887 |
| arm | shoulder pitch/roll, upper arm (yaw), elbow | 0.005 | 19.74 | 1.257 | 10 | 0.1267 |
| head | head yaw/pitch | 0.002 | 7.896 | 0.503 | 3.7 | 0.1172 |

- **Calibration (disclosed).** Arm and head inertias are the D-DESC spike's values. The D-DESC leg value 0.01 gave a zero-action stand that leaned back 0.196 rad in 2 s (nominal RT-3 would fail: the stance is an inverted pendulum with m·g·l ≈ 51 N·m/rad against 2 × 39.5 N·m/rad of ankle stiffness). The leg value was then chosen by a rule written before the grid ran: the smallest of {0.01, 0.015, 0.02, 0.03} whose zero-action stand has |pitch|, |roll| < 0.05 rad and drop < 0.015 m. Result 0.015 (pitch −0.047). Every grid point is in `logs/p6/as1-calibration-attempt1.log`. At kp × 0.5 this plant falls (RT-3 only requires no NaN there). This is a plant assumption, not a tuning of any B1 arm; it applies identically to every arm.
- The descriptor (D-003) reads kp, effort and σ from the same mjlab entity config, so the descriptor and the env cannot disagree (seam S5).

## AS-2 Default pose (BLK-4, BLK-6)

- Hip pitch −0.2, calf (knee) +0.4, ankle pitch −0.2 (feet flat: the three sum to 0), shoulder roll +0.2 left / −0.2 right (abducted), all other joints 0. These are the D-DESC placeholder values (`code/descriptor_v2.py: home_default_qpos`), kept unchanged.
- Root height for the pose: the base height at which the lowest sole point is at z = 0 (0.3703 m); mjlab init state adds 5 mm clearance.
- Checked: 0 self-contacts at this pose (BLK-4 cleared without contact excludes); only sole-floor contacts.

## AS-3 Tracked, anchor, root, termination and foot bodies (BLK-8)

- **Tracked (15):** base_link; hip roll, calf and ankle roll links (both sides); torso_link; shoulder roll, elbow and wrist links (both sides); head_pitch_link. These are the semantic counterparts of the 14 bodies the upstream env tracks on the 29-DoF reference (pelvis, hip roll, knee, ankle roll, torso, shoulder roll, elbow, wrist yaw), plus the head pitch link that SCHEME_PLAN AS-3 names. SCHEME_PLAN AS-3 listed 7 bodies; the 8 extra intermediate links keep the reward structure the same as on the reference body. This is a tightening, disclosed here.
- **Anchor:** torso_link. **Root / termination body:** base_link (the free-joint body), as the pelvis is upstream.
- **Feet:** the 4 sole capsules of each ankle-roll link, renamed `l_foot1..4_collision` / `r_foot1..4_collision` (regex `^(l|r)_foot[1-4]_collision$`). condim 3, priority 1, friction 0.6 (randomised per episode in training as upstream). Other collision geoms condim 1. The two anatomical ankle sites are kept as foot keypoints for QA.
- Collision geoms are renamed `<body>_collision<k>`. The visual meshes stay visual-only.

## AS-4 Retarget route RT-a (BLK-3; EVAL_REVIEW §4.3)

Source: the upstream 29-DoF LAFAN1 retarget CSVs (`lvhaidong/LAFAN1_Retargeting_Dataset`, `g1/`, 30 fps), used at runtime only (X-002; brief Amendment v1.1 A1.1-7). Implementation: `spikes/B1-RT/retarget_rta.py`.

**Joint correspondence and axis-sign check.** The check compares world joint axes at the zero pose (dot product) and the zero-pose direction of each child segment.

| Home humanoid | 29-DoF reference | axis dot at zero pose | sign | zero offset |
|---|---|---|---|---|
| hip pitch | hip pitch | 1.000 | +1 | 0 |
| hip roll | hip roll | 0.985 (reference axis tilted 10°) | +1 | 0 |
| thigh (yaw) | hip yaw | 0.985 | +1 | 0 |
| calf (knee) | knee | 1.000 | +1 | 0 |
| ankle pitch | ankle pitch | 1.000 | +1 | 0 |
| ankle roll | ankle roll | 1.000 | +1 | 0 |
| shoulder pitch | shoulder pitch | 0.961 (reference axis tilted 16°) | +1 | 0 |
| shoulder roll | shoulder roll | 1.000 | +1 | 0 |
| upper arm (yaw) | shoulder yaw | 1.000 | +1 | 0 |
| elbow | elbow | 1.000 | +1 | **−φ**, φ = the reference elbow angle at which its forearm is parallel to its upper arm (computed from the reference MJCF by the harness; ≈ 1.4 rad). At 0 the reference forearm points forward and the home forearm hangs straight |
| head yaw, head pitch | — | — | — | held at 0 |
| — | waist yaw/roll/pitch, wrist roll/pitch/yaw ×2 | — | dropped | — |

Both left and right sides were checked. The harness re-runs this check on every execution and fails RT-4 if any sign or offset differs from the table (|dot| < 0.9 or a zero-pose child-segment angle above 15° on a pair with offset 0).

**Clip to limits.** Mapped angles are clipped to the home-humanoid MJCF range. RT-4 counts clipped frames.

**Root.** Root orientation is copied (pelvis → base; the dropped waist is not folded in). Root x, y and z are multiplied by the leg-length ratio s = 0.2824 / 0.6366 = 0.4436 (hip-pitch-to-ankle-pitch vertical at the zero pose, home / reference). Then one constant z offset per clip puts the **median over frames of the lowest sole point at z = 0**. No per-frame height correction is made, so penetration and skate remain real measurements.

**Resampling and bodies.** 30 → 50 fps and velocities exactly as upstream `supermimic.data.motion_convert.resample_motion`. Body states by CPU MuJoCo FK on the overlaid home-humanoid model (the upstream `forward_kinematics` routine on the home model). The output has the upstream npz keys, written on the GPU host only.

**RT-b fallback trigger.** RT-a fails QA on more than 1 of the 4 clip slots after one pre-declared replacement per slot (`spikes/B1-RT/PLAN.md` §3). RT-b (keypoint IK) is not implemented in P6; triggering it means `BLOCKED.md` and a brief amendment.

## AS-5 Length-dimensioned env constants (new; BLK-8)

- The upstream root-height termination threshold (0.25 m) and the torso COM-offset randomisation (±0.025/±0.05/±0.05 m) are lengths sized for the reference body. Both are multiplied by the standing-height ratio h = 0.3703 / 0.76 = 0.487 (home base height at the AS-2 pose / reference pelvis height of the upstream knees-bent keyframe): threshold 0.122 m.
- Everything else in the env (reward terms and their stds, tilt threshold 0.8, action noise, observation noise, episode length, friction range, encoder bias) is unchanged from upstream, so the home-humanoid task differs from the reference task only by the plant, the references and these two lengths.
