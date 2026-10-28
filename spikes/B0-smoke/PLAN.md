# spikes/B0-smoke/PLAN.md — P2 B0 Colab smoke (owner-run), pre-registered

**Written by:** Orchestrator (Claude Code, `claude-opus`), P1 wake, 2026-10-25 EDT (America/Toronto). **Method:** v1.1, sha256 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0` + `method/local/OVERLAY-001-owner-colab-runner.md`.
**Status:** sealed when its sha256 is appended to `logs/seal.log` (event `SEAL-PLAN spikes/B0-smoke`). After sealing, changes are appended `Amendment` blocks only.
**Runner:** owner (human), venue Colab (L4 preferred, T4 fallback), per OVERLAY-001 rule 1. The runner receives this PLAN, the frozen tarball and the notebook/runbook only.
**Decision cap:** Provisional. **No performance claim comes from P2** (SCHEME_PLAN §1 P2).
**Nothing in this file has been executed on Colab.** (Only the tarball's CPU tests were run on the box from a clean unpack, 2026-10-25 15:4x EDT.) As of writing, no Colab or GPU run has happened in this program.

## 1. Mechanism under test

The pipeline, not the architecture: the frozen P1 code (tarball below) runs the upstream SuperMimic-style WM/BPTT loop at the pinned commit on Colab with (a) the attention decoder and (b) the matched MLP decoder, end to end (train → checkpoint → sidecar → eval at masks 0/0.1/0.2), and the seam assumptions S1–S5 hold on the real upstream objects.

## 2. Inputs (frozen)

| Input | Identity |
|---|---|
| Code tarball | `packets/P2/junior_b_colab-P1freeze.tgz`, sha256 `f69dd11eb532c10411bfd77e3f1f2c5edd36275f4a0b9c737624bb8cac341636` (listed in `packets/P1/FREEZE_MANIFEST.md`) |
| Config | `configs/colab_smoke.yaml` inside the tarball (hash in the manifest) |
| Runbook / notebook | `docs/COLAB_RUNBOOK.md`, `notebooks/colab_smoke.ipynb` inside the tarball |
| Upstream | `https://github.com/CuboiLeo/SuperMimic-Reproduced` @ `d9be385b3eeb13a638fb33fb200d3bfd9be9839f` |
| Motion data | the 4 clips in the frozen config (FX-3 verified), downloaded on the Colab runtime only; never copied back (X-002) |

## 3. Arms, seeds, attempts

| Arm | Seed | Required? |
|---|---|---|
| upstream sanity (runbook §5, unmodified decoder, `max-hours 0.1`) | 0 | Required first; if it fails, stop: environment problem, not decoder |
| `attention` (descriptor as frozen in P1) | 0 | Required |
| `mlp_matched` | 0 | Required (control) |
| `mlp_upstream` | 0 | Optional |

- **Attempt cap:** 3 attempts per required arm. An attempt is any execution that starts the trainer, including crashes and disconnects. Every attempt is returned in the bundle (OVERLAY-001 rule 3).
- **Allowed without amendment** (record each in `deviations.md`): R1 wheel substitution per runbook §2; halving `num_envs` and `batch-size` **together for all arms** on OOM or T4; session restart with upstream `--resume`.
- **Anything else** (changing config values other than the above, editing code in the tarball, switching clips) is a plan gap: stop and write `BLOCKED.md` (method §12.2).

## 4. Exact commands

Runbook §1–§7 as frozen in the tarball, in order, **with one substitution in §2: do not re-pack on the box; upload the frozen tarball named in §2 of this PLAN and check its sha256 on Colab (`sha256sum junior_b_colab-P1freeze.tgz`) before unpacking.** Runbook §3 says "expect 10x PASS"; the frozen test file prints **14 PASS lines, 3 of them preceded by SKIP** (asset/spike module not in the tarball), as verified on the box from a clean unpack of the tarball. That count, not the runbook's, is the expectation (stale comment in the frozen runbook; not a code change). §1 `nvidia-smi`; §2 unpack + clone + `uv sync`; §3 CPU import smoke; §4 data; §5 upstream sanity; §6 train `attention` then `mlp_matched` (`--seed 0`); §7 eval both arms. The notebook cells are the same commands.

## 5. Pass rule (pipeline level; machine-checked)

The harness verdict is computed from the deposited bundle by an agent process that is not an adjudicator (OVERLAY-001 rule 6). Prose never overrides it.

| ID | Criterion | Source in bundle |
|---|---|---|
| P-1 | Upstream sanity ran to its cap with no exception | `train_up_sanity.log` |
| P-2 | For **each** of `attention`, `mlp_matched`: training reached the time cap with no NaN and no exception | `train_<arm>_s0.log` |
| P-3 | For each arm: WM loss at the end < WM loss at the first logged point after warmup | tb scalars / log |
| P-4 | For each arm: train return at the end > train return at the first logged point after warmup | tb scalars / log |
| P-5 | For each arm: a checkpoint was written and `junior_policy.json` exists (checkpoint itself stays on Colab) | `junior_policy.json`, `ls` output |
| P-6 | For each arm: eval JSON exists for masks 0.00, 0.10, 0.20 | `logs/eval/*.json` |
| S1 | Joint-order assertion printed **true**: morphology row order == robot entity joint order == action order | `train_attention_s0.log` |
| S2 | obs `policy` dim == 930 and term-major layout assertion **true** | `train_attention_s0.log` |
| S3 | Compile setting recorded and identical for both arms | both train logs |
| S4 | Descriptor default pose came from the env initial joint state (not the `qpos0` fallback) | `junior_policy.json` (`default_pose_source`) |
| S5 | `[seam] S5 env_action_scale_match=true` (env action scale/offset per joint == descriptor σ / q_def) | `train_attention_s0.log`, `junior_policy.json` |

**PASS** = P-1…P-6 and S1, S2, S4, S5 true, S3 recorded. Any seam printing `unverified` raises by design and is **BLOCKED** (hand back for a change request against the P1 freeze), not FAIL. **BLOCKED** = R1 unresolved after the fallback (venue decision for the Human lead). **S1, S4 or S5 false** = bug: fix under a change request against the P1 freeze, then re-run as a new attempt. Anything else = FAIL with the failing IDs listed.

## 6. Must also capture (reported, no threshold)

ms per policy update, env-steps/s, peak GPU memory, policy grad-norm series and clip fraction (M-6), `params:` line from the trainer, `nvidia-smi` header (driver + GPU), `pip freeze` of the upstream venv.

## 7. Output / deposit format

The owner returns one archive per session, unmodified, e.g. `b0smoke-<YYYYMMDD>-<HHMM>.tgz`, containing: `nvidia-smi.txt`, `pip-freeze.txt`, `train_*.log`, `logs/*/junior_policy.json`, `logs/*/tb/`, `logs/eval/*.json`, `deviations.md` (may be empty), and `BLOCKED.md` if applicable. **No motion data and no checkpoints.**

Deposit path: `logs/colab/<YYYY-MM-DD>/` in this program, archive kept byte-identical. Its sha256 is appended to `logs/seal.log` (event `DEPOSIT colab`) **before** any agent opens it (OVERLAY-001 rule 3). The verdict script then writes `spikes/B0-smoke/runs.log` and `spikes/B0-smoke/results.json` (one key per ID above, boolean `pass`).
