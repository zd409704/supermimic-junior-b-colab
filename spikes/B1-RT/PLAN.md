# spikes/B1-RT/PLAN.md — B1 runnable test (home humanoid as a second plant), pre-registered

**Packet:** P6b. **Written:** 2026-10-26 ~19:35 EDT by the Orchestrator (`claude-opus`), before any RT check ran on real motion data. **Status:** Provisional. **Purpose:** infrastructure acceptance only. B1-RT makes **no performance claim**.
**Method:** v1.1 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0` + `method/local/OVERLAY-001` (relay in place of owner, brief Amendment v1.1 A1.1-5).
**Authority:** P6 START `3a0254de…`; xn-4090 amend `1408aeef…`; brief Amendment v1.1 (`briefs/B1-home-humanoid-cross-embodiment.md` sha256 `787b2980…`). **Scheme:** `docs/SCHEME_PLAN.md` §5 (this file operationalises it; thresholds are SCHEME_PLAN's unless marked *tightening*).
**Inputs (sealed P6a):** `spikes/B1-RT/home_humanoid.py` `63ef8bc6…`, `spikes/B1-RT/ASSUMPTIONS.md` `9794f3ef…`.

---

## 1. Mechanism under test

The owner home-humanoid MJCF, with the AS-1..AS-5 load-time overlay, is a working second plant in the frozen stack: it loads intact, actuates, stands under zero action, accepts RT-a reference motion of acceptable quality, simulates identically on MuJoCo Warp, trains and evaluates with per-body encoder/WM/critic at J = 22, and accepts P4 decoder weights.

## 2. Checks (operational definitions; first run of each counts)

Sim settings for every CPU dynamics check: timestep 0.005 s, Newton, iterations 10, ls_iterations 20 (the upstream env's `MujocoCfg`), control step 0.02 s (decimation 4).

| ID | Venue | Pass criterion (exact) |
|---|---|---|
| RT-1 | box CPU (`rt_cpu.py`) | Owner XML compiles; exactly 1 free + 22 hinge joints; 28 bodies (owner and overlaid); XML sha256 = `856ce702…` and all 27 manifest meshes match; the same hashes recomputed after all checks are unchanged |
| RT-2 | box CPU | (a) overlaid CPU model and the mjlab entity (`get_home_humanoid_robot_cfg`) both have nu = 22, one `<position>` actuator per hinge, force range = that hinge's `actuatorfrcrange`; (b) the compiled mjlab scene has exactly 1 plane (the scene terrain) and 0 planes inside the robot; (c) 0 non-floor contacts at the AS-2 keyframe in both the CPU model and the mjlab scene model; (d) hinge order = CPU actuator order = mjlab actuator order = mjlab entity joint order = descriptor-v2 row order, descriptor 22×16 finite |
| RT-3 | box CPU | From the `home` keyframe with targets = AS-2 pose: settle 0.5 s, then a 2.0 s window. Nominal (kp × 1.0): base-height drop over the window < 0.03 m, **max over the window** of \|roll\|, \|pitch\| < 0.10 rad (*tightening*: SCHEME_PLAN reads at the end), both feet in contact at the end. kp × 0.5 and × 1.5 are run and recorded; they pass if no NaN/inf appears |
| RT-4 | box CPU, motion in process memory only (brief A1.1-7) | Per clip, RT-a (AS-4), on the 50 fps retarget: (i) clipped-frame fraction (input frames with any joint clipped by > 0.05 rad) ≤ 0.10; (ii) sole penetration p95 ≤ 0.01 m (per frame: max(0, −lowest sole point)); (iii) stance-foot skate p95 ≤ 0.10 m/s (stance foot = foot with the lower sole point, frames where that point is < 0.02 m; speed = planar speed of its ankle-roll link); (iv) root height ratio (base z / 0.3703 m) has p5 ≥ 0.6 and p95 ≤ 1.1 (SCHEME_PLAN's range read as the 5–95 % band of frames); (v) the AS-4 axis-sign/offset check passes. **RT-4 passes if ≥ 3 of the 4 slots (§3) have a passing clip and (v) holds** |
| RT-5 | box CPU | Reference-PD replay, root free, PD targets = clipped reference joints, start at the reference first frame. Time-to-fall = first control step where \|ref root z − base z\| > 0.122 m (AS-5) or the gravity-tilt difference > 0.8. Recorded for every clip fetched. **No pass/fail**; must finish without NaN |
| RT-6 | xn-4090-gpu2 (`packets/P6/b1/rt_gpu.py rt6`) | (a) Parity: the compiled mjlab scene model (robot + terrain) stepped on MuJoCo Warp (4 identical worlds) and on C MuJoCo from the same keyframe, ctrl = AS-2 pose, 200 physics steps (1.0 s): max over steps and worlds of \|z_gpu − z_cpu\| ≤ 0.01 m, all finite. (b) Seams on the GPU tracking env (16 envs, home body): S1 = true (descriptor rows = entity joints = action joints), S2 = true (policy obs 720, term-major, upstream term names), S5 = true (env action scale/offset = descriptor σ/q_def) |
| RT-7 | xn-4090-gpu2 | Two trainings, `attention` and `mlp_matched` (J = 22, scratch, seed 0), config `packets/P6/configs/b1_home.yaml` with `--schedule.max-hours 0.5` appended (upstream self-stop). Pass per run: (i) exit without Traceback and every tb scalar finite; (ii) WM loss decreases: mean `wm/state_loss` of the last 3 logged windows < mean of the first 3 windows that have updates; (iii) cumulative train return rises: C = `train/episode_norm_return` × `train/episode_len` per logged window; mean C of the last 3 windows > mean C of the first 3 windows at it ≥ 100 (*operationalises* "final train return > post-warmup return" with the cumulative metric required by `DECISION-RV-BLK-20261026.md`); (iv) `ckpt_latest.pt` and `junior_policy.json` written, sidecar seams S1/S2/S5 true. RT-7 passes if both runs pass |
| RT-8 | xn-4090-gpu2 | (a) Eval smoke: `p6_entry.py eval` on each RT-7 `ckpt_latest.pt` at masks 0.0/0.1/0.2 → 3 benchmark JSONs per arm, every clip `norm_return` finite. (b) Transfer-load check (`rt_gpu.py xferload`): the P4 attention s0 `ckpt_0001600.pt` loads into the J = 22 attention decoder (all decoder parameters, strict shapes; buffers `morphology`/`scale` are the home body's), and the P4 mlp_matched s0 checkpoint loads through the row map (20 joints mapped, head yaw/pitch fresh, hidden layers copied); both give finite (8, 22) actions; both checkpoint sha256 equal the P5-verified identities (`5fb48347…a1d`, `9ae05d74…913e`) |

**B1-RT verdict (machine):** `PASS` iff RT-1, RT-2, RT-3, RT-4, RT-6, RT-7, RT-8 pass and RT-5 is recorded finite. `FAIL` lists the failing IDs. `BLOCKED` if a GPU check could not execute (infra, deposit integrity, spend cap). Computed by `spikes/B1-RT/verdict_rt.py` (sealed before the GPU deposit is opened) from `results-cpu-attempt<N>.json` and the deposited bundle. Prose never overrides it. Outputs: `spikes/B1-RT/results.json` (one key per RT-id with boolean `pass`), `runs.log`, `deviations.md`.

## 3. Clip slots (RT-4, RT-5, RT-7, B1 arms)

| Slot | First clip | Pre-declared replacement |
|---|---|---|
| walk | walk1_subject1 | walk1_subject2 |
| run | run1_subject2 | run1_subject5 |
| dance | dance1_subject1 | dance1_subject2 |
| jump | jumps1_subject1 | jumps1_subject2 |

First clips are the P4 clips. The replacement is tried only if the first clip fails RT-4; a slot passes if one of its two clips passes. Fewer than 3 passing slots → RT-b trigger (AS-4): `BLOCKED.md`, no GPU spend on arms, brief amendment. The dataset revision recorded by the box run is pinned for the GPU host (`prepare_b1_data.py --rev`), and the CSV sha256 per clip must equal the box values. The GPU host trains and evaluates on exactly the passing slots' clips.

## 4. Attempts and budgets

- CPU harness: at most 3 executions of `rt_cpu.py` (attempt files never overwritten). A bug fix needs the literal PLAN behaviour (method §12.2); anything else is a plan gap → `BLOCKED.md` and a sealed amendment.
- GPU job `p6-b1-rt`: at most 2 attempts; attempt 2 only after an INFRA failure (setup, download, OOM, relay) with byte-identical inputs. GPU-hour envelope ≈ 1.5 h (SCHEME_PLAN §8 P6b); hard spend cap 2.0 GPU wall-hours per attempt in the driver.

## 5. Venue and deposit

xn-4090-gpu2, GPU0, mutex `gpu0`, `HF_ENDPOINT=https://hf-mirror.com`, launched by the Manager relay from `orch/jobs/p6-b1-rt.json` (state READY). Bundle `b1rt-*.tgz` (meta, logs, tb, eval JSONs, QA JSON, deviations; **no `.pt`, `.npz`, `.csv`**) deposited unmodified to `logs/xn4090/<UTC date>/` and sealed (`DEPOSIT xn4090`) in `logs/seal.log` before any agent opens it.

## 6. Runner and roles

Non-contest infrastructure spike (brief A1.1-6). CPU harness run by the Orchestrator shell (deterministic script, no model judgment). GPU runner = relay-launched driver (OVERLAY-001 rules 2–6). Verdict = `verdict_rt.py` output.

## 7. Confounds disclosed up front

1. AS-1 leg inertia was calibrated on the zero-action stand (RT-3 nominal); RT-3 nominal therefore confirms the calibration rather than testing it independently. The rule and every grid point were logged before this PLAN.
2. RT-4's constant per-clip z offset (median lowest sole at 0) is part of RT-a; per-frame penetration and skate remain real measurements.
3. The box CPU runs mujoco 3.16 / mjlab 8bb2bc9e (same pins as the GPU host's upstream lock); the research box's older `.venv` (mujoco 3.17) is not used for RT.
