# P4-prep — UPSTREAM_FACTS (CR-B0-1 (c))

**Packet:** P4-prep (CPU / research box only). **Written by:** Orchestrator (Claude Code, `claude-opus`), 2026-10-26 EDT (America/Toronto); UTC/epoch in `logs/seal.log`.
**Binding PLAN:** `spikes/B0/PLAN.md`, sha256 `ed6b6a54a860bbfc67d7c822b5394804b8d408f6aae57fbeb118d2ea63c52557` (§2.2 (c)).
**Method:** v1.1 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0` + `method/local/OVERLAY-001-owner-colab-runner.md`. **Status:** Provisional.

**Source read.** `https://github.com/CuboiLeo/SuperMimic-Reproduced` at `d9be385b3eeb13a638fb33fb200d3bfd9be9839f` (commit date 2026-10-21 22:13:13 -0700), cloned read-only into `packets/P4/upstream-ro/SuperMimic-Reproduced/` (`git rev-parse HEAD` = the pin). Nothing from it was vendored into `code/`. The P1 context copy `packets/P1/ddesc/context/upstream-d9be385/` does not contain the training loop, schedule or policy trainer, so the clone was needed. Paths below are relative to the upstream repo root. Line numbers are 1-based at the pin.

---

## F-1 — iteration-cap flag

| Item | Value |
|---|---|
| Flag | `--schedule.total-iterations` (tyro name of `ScheduleCfg.total_iterations`, `src/supermimic/config.py:40`; default `320_000`, commented "env steps") |
| Unit | **Training iterations** (one vectorised env step each), not policy updates. The loop condition is `while self.iteration < sch.total_iterations` (`src/supermimic/training/loop.py:159`), and `self.iteration += 1` runs once per env step (`loop.py:161-163`, `loop.py:177`). Updates are counted separately in `self.num_updates` (`loop.py:196`) |
| Endpoint | **Inclusive** of iteration N: the body for `iteration == N` runs (log at `loop.py:205`, checkpoint at `loop.py:258-260`), then the `while` test fails and the loop exits. With `checkpoint_interval` dividing N, `ckpt_{N:07d}.pt` is written **before** the stop. After the loop: `ckpt_latest.pt`, writer flush, `finalize()` (`loop.py:269-272`) and a normal return |
| **Side effect** | `total_iterations` is also the **horizon of the cosine LR schedule**. Every update calls `cosine_lr(self.iteration, sch.total_iterations, cfg.wm_trainer.lr, sch.lr_final_ratio, sch.lr_decay_fraction)` (`loop.py:184`), and that LR is applied to the WM, policy and critic optimizers (`loop.py:185-186`; `src/supermimic/imagination/policy_trainer.py:49-53`). `decay_steps = int(total_steps * decay_fraction)` (`src/supermimic/training/schedule.py:9`), with `decay_fraction` = 250 000 / 320 000 (`config.py:45`). The LR decays to `final_ratio` = 0.03 (`config.py:44`) at `decay_steps` and stays there (`schedule.py:10-11`) |
| Effect of `--schedule.total-iterations 1600` | `decay_steps` becomes 1250. The LR falls from ≈ base at it 40 to 0.03 × base at it 1250, then stays at 0.03 × base for it 1250–1600. With the frozen value (default 320 000; `decay_steps` 250 000) the cosine factor at it 1600 is 0.5·(1 + cos(π·1600/250 000)) ≈ 0.9999, so the LR stays ≈ base for the whole 1600-iteration budget. That is the trajectory every P2 run had |

**Classification for CR-B0-1 (a): F-1 = unsuitable → harness stop (PLAN §4.3).**

The flag meets the three properties PLAN §2.2 (a) lists: it exists, it counts iterations, and it writes `ckpt_0001600.pt` before it stops (with `--schedule.checkpoint-interval 400`). It does **not** act as a cap only. Setting it to 1600 would change the learning rate of every policy, critic and WM update in the budget, and the last ≈ 22% of the budget would run at 3% of base LR. PLAN §2.2 (a) says "Everything else keeps the frozen values", and §1 says only the decoder differs from the unchanged upstream loop. The Orchestrator therefore reads the dual-purpose flag as **unsuitable** and applies the pre-registered fallback: no cap flag, harness stop. PLAN §2.2 says the harness stop "is not a deviation". The budget endpoint is the iteration-1600 checkpoint either way.

This is an Orchestrator reading of a PLAN term ("unsuitable") that the PLAN does not define beyond the three properties. It is disclosed, and the human lead is asked to confirm it in `packets/P4/PRESTART.md` (ruling R-F1). If the human lead rules the literal reading instead (cap flag added, compressed LR schedule accepted), CR-B0-1 (a)/(b), the tarball and the manifest addendum must be regenerated and re-sealed before attempt 1.

## F-2 — policy learning-rate flag

| Item | Value |
|---|---|
| Flag | `--policy-trainer.lr` (`PolicyTrainerCfg.lr`, `src/supermimic/imagination/policy_trainer.py:26`) |
| Pinned default | `2e-4` (`policy_trainer.py:26`). The WM default is also `2e-4` (`src/supermimic/world_model/wm_trainer.py:21`) |
| How it is applied | At every update, policy LR = `cosine_lr(...) * cfg.policy_trainer.lr / cfg.wm_trainer.lr` (`loop.py:184-186`). Halving the flag halves the policy LR at every update and leaves the WM LR unchanged |
| **Side effect** | `PolicyTrainer.set_lr` writes the same value to the **critic** optimizer (`policy_trainer.py:49-53`). `set_lr` runs before every update (`loop.py:186` precedes `loop.py:193`), so `--policy-trainer.critic-lr` (`policy_trainer.py:30`) only matters before the first update. Halving `--policy-trainer.lr` therefore also halves the critic LR. No upstream flag halves the policy LR alone |
| No world-size scaling | `cfg.policy_trainer.lr *= self.world**0.5` runs only when `world > 1` (`loop.py:35-40`). Single-process runs have `world == 1` (`src/supermimic/training/distributed.py:20-27`) |

**CR-B0-1 (b):** `configs/b0_microbench_lr05.yaml` adds `--policy-trainer.lr: 0.0001` (= 0.5 × 2e-4). The divergence retry (PLAN §6.3) **can run**. The critic-LR coupling is disclosed here and in that file's added line.

## F-3 — policy grad-norm clip threshold

| Item | Value |
|---|---|
| Norm clip | `grad_clip_norm: float = 1.0` (`policy_trainer.py:28`), applied as `gn = torch.nn.utils.clip_grad_norm_(self.policy.parameters(), cfg.grad_clip_norm)` (`policy_trainer.py:79`) once per policy update |
| Also applied | element-wise value clip `grad_clip_value: float = 0.1` (`policy_trainer.py:29`), `torch.nn.utils.clip_grad_value_(...)` (`policy_trainer.py:80`), after the norm clip. Critic norm clip 1.0 (`policy_trainer.py:31`, `:122`). WM norm clip `wm_trainer.py:60` |
| Flag names | `--policy-trainer.grad-clip-norm` (not changed by CR-B0-1) |

**F-3 = 1.0 (policy, L2 norm over all policy parameters).**

## F-4 — what tb `policy/policy_grad_norm` logs

| Item | Value |
|---|---|
| Pre- or post-clip | **Pre-clip.** `policy_grad_norm = float(gn)` (`policy_trainer.py:91`). `gn` is the return value of `clip_grad_norm_`, which is the total norm of the gradients before clipping. Torch docstring "Total norm of the parameter gradients (viewed as a single vector)" (torch 2.14.1 `torch/nn/utils/clip_grad.py:216`, return at `:232`). Checked on the research box: grads of norm 6.0 with max_norm 1.0 return 6.0 and leave a post-clip norm of 1.0 |
| Per update or aggregated | **Aggregated: mean over the updates in each log window.** Each update adds the metric into a running sum, `agg[f"policy/{k}"] = agg.get(...) + v` (`loop.py:199-200`), and `agg_n += 1` (`loop.py:202`). Every `log_interval` (50) iterations the tb value written is `v / agg_n` (`loop.py:220-222`), and the sums reset (`loop.py:255`). At UTD 0.4 (`config.py:41`) a 50-iteration window holds 20 updates (the first window after warmup holds fewer) |
| Per-update clip indicator | **None.** No per-update norm, max or clipped count is written to tb or stdout. The stdout line (`loop.py:247-253`) does not print the grad norm |

**Consequence (PLAN §2.2, pre-registered).** F-4 shows no per-update pre-clip norm and no per-update clip indicator. M-6 clip fraction is `null` (not evaluable), divergence clause §6.3 (b) is skipped, and **PS-3 does not hold until the human lead signs ruling (i) or ruling (ii)** (`packets/P4/PRESTART.md`). A window mean above 1.0 shows that at least one update in the window was clipped. It does not give the fraction, and the PLAN forbids substituting a logged-point proxy.

## F-5 — env steps per training iteration

| Item | Value |
|---|---|
| Per iteration | **`num_envs` env steps** (one control step for each of the `num_envs` parallel envs). Each loop iteration makes exactly one `env.step(action)` call on the vectorised env (`loop.py:161-163`) and increments `iteration` once (`loop.py:177`). No branch in the collect step depends on the policy arm or on policy behaviour. Episode ends are handled by resetting episode statistics (`loop.py:166-174`). They add no extra steps and skip none. Policy updates (`loop.py:180-202`) do not touch the env |
| Config dependence | `num_envs` comes from `--env.num-envs` (`config.py:25`, passed at `loop.py:59`). The control step is `decimation = 4` physics steps of `timestep = 0.005` s, so 0.02 s (`src/supermimic/envs/tracking_env_cfg.py:237-238`). Both are fixed in source, not set by any arm |
| Single process | `world == 1` (`distributed.py:20-27`), so there is one simulator with `num_envs` envs |
| B0 value | `--env.num-envs 512` (frozen config, unchanged by CR-B0-1) → **512 env steps per iteration**, 819 200 env steps per 1600-iteration run, identical for every arm |
| Not read at the pin | the internals of mjlab `ManagerBasedRlEnv.step` (separate pin, mjlab `8bb2bc9e…`). "One `step` call = one control step per env" is the mjlab/Isaac-Lab manager-env convention that the upstream loop assumes (`time/updates` and UTD are counted per `step` call). Auto-reset inside `step` does not change the count of transitions |

**F-5 = 512 env steps per iteration, a function of config only (`num_envs`). PS-4 holds on source-backed proof.** Updates per iteration are also arm-independent: `_utd_acc` grows by 0.4 per iteration from it 40 (`loop.py:180-183`), so `num_updates` is a deterministic function of `iteration`. PLAN V-2 (a) still checks `time/updates` at it 1600 directly.

---

## Summary for `results.json` `upstream_facts`

```json
{
  "F-1": {"flag": "--schedule.total-iterations", "unit": "iterations", "endpoint": "inclusive; ckpt at N written before stop when checkpoint_interval divides N", "side_effect": "cosine LR horizon (loop.py:184)", "classification": "unsuitable", "cap_flag_in_config": false, "stop": "harness_stop"},
  "F-2": {"flag": "--policy-trainer.lr", "default": 0.0002, "lr05_value": 0.0001, "side_effect": "critic LR follows (policy_trainer.py:49-53)"},
  "F-3": {"flag": "--policy-trainer.grad-clip-norm", "value": 1.0, "also": "clip_grad_value 0.1"},
  "F-4": {"pre_or_post_clip": "pre", "aggregation": "mean per log window (50 it)", "per_update_clip_indicator": false, "m6_evaluable": false},
  "F-5": {"env_steps_per_iter": 512, "formula": "num_envs", "arm_dependent": false}
}
```
