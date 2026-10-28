# spikes/B0/PLAN.md — P4 B0 microbench (attention decoder vs mlp_matched, single 29-DoF body), pre-registered

**Written by:** Orchestrator (Claude Code, `claude-opus`, medium effort), P3 wake, 2026-10-26 EDT (America/Toronto). **Method:** v1.1, sha256 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0` (re-verified at boot) + `method/local/README.md` specials + `method/local/OVERLAY-001-owner-colab-runner.md`. No new overlay was needed for this packet (§11).
**Revision:** draft 4. Drafts 1, 2 and 3 were revised after three cross-family red-team rounds (§10 item 8). **Status:** sealed when its sha256 is appended to `logs/seal.log` (event `SEAL spikes/B0/PLAN.md`). After sealing, changes are appended `Amendment vN` blocks only. A change to a scoring input (metric, threshold, seeds, attempt cap, pass rule) is Class 2: the human lead signs it before P4 attempt 1 starts, otherwise it waits for the next packet (method §10.4).
**Decision cap:** Provisional. **Nothing in this file has been executed.** No P4 training, eval or GPU spend has happened. The paid-compute envelope (BLK-12) is authorized as a draft. Spending starts only when a later runner packet cites this sealed PLAN (§9).
**Wording:** "home humanoid" / "plant" for the second body (not used in B0). The B0 body is "the upstream 29-DoF humanoid". No commercial product brands appear in this file.
**Structure reference:** `spikes/B0-smoke/PLAN.md` (sealed P2, sha256 `512a3eb40b45cc4e5fabc30836e8b21cb9b2fe15739cd74a693a188ea4ce1987`). That file is **not modified** by this packet (§12).

---

## 0. Authority and inheritance (by ledger ID, method §13.3)

| Item | Binds this packet as | Source |
|---|---|---|
| D-001 Junior-(B) decoder on the unchanged WM loop | Explicit assumption (Provisional) | `program-ledger.md` |
| D-003 descriptor v2 + action-scale handling | Explicit assumption (Provisional), frozen in code | `packets/P1/ddesc/decision.md` |
| D-004 P1 scaffold freeze | Explicit assumption (Provisional). It supplies the frozen inputs (§2) | `packets/P1/FREEZE_MANIFEST.md` |
| P2 close under A1: pipeline objective met at Provisional; machine verdict stays **FAIL failing_ids=[P-4]** | Context and disclosure only, not a gate input | `orch/reports/DECISION-A1-P2-close-20261026.md` |
| P-4 root cause (per-step `norm_return` metric artifact) | Design input for §5 and §6 | `orch/reports/P4-RCA-20261026.md` |
| Operational accepts RV-1, RV-2, RV-8, BLK-11, BLK-12. RV-7/BLK-10 deferred | Signed (owner delegated to Manager, 2026-10-26 00:36 EDT) | `orch/reports/DECISION-RV-BLK-20261026.md` |

**Depth disclosure (§13.3).** EVAL_REVIEW §3.3 counts B0 → D-001 as depth 1. D-004 is a Provisional freeze of artifacts that itself `depends_on` D-001. Read strictly, the B0 decision chain B0 → D-004 → D-001 is Provisional-on-Provisional. This PLAN does not resolve that question. It flags it for the human lead. The B0 outcome is capped at Provisional either way. RV-7/BLK-10 stays deferred to the B1 brief, as ruled.

---

## 1. Mechanism under test

On the single upstream 29-DoF humanoid, the frozen P1 code runs the unchanged upstream WM/BPTT loop at the pinned commit. Only the policy **decoder** differs between arms.

The question: does the shared per-joint **attention decoder** (Junior-(B), `id_mode=morph`, descriptor v2 from the P1 freeze, 464 001 params) reach tracking performance that is **non-inferior** to a **parameter-matched MLP decoder** (`mlp_matched`, 468 317 params, +0.93%) under an **equal env-step and equal policy-update budget**?

This is the "cost of generality" test from EVAL_REVIEW V3 and RV-1. It is not a superiority test. Superiority is reported only. `mlp_upstream` (about 4.7 M params) is a compute-heavier reference and not a gate (SCHEME_PLAN §2).

Motion encoder, world model, critic, env config, reward and reference clips are identical across arms, and none of them is under test.

---

## 2. Inputs (frozen) and P4-prep preconditions

### 2.1 Frozen inputs

| Input | Identity |
|---|---|
| Code tarball (P1 freeze) | `packets/P2/junior_b_colab-P1freeze.tgz`, sha256 `f69dd11eb532c10411bfd77e3f1f2c5edd36275f4a0b9c737624bb8cac341636` (`packets/P1/FREEZE_MANIFEST.md` §3) |
| Freeze manifest | `packets/P1/FREEZE_MANIFEST.md`, sealed `e1d0eae27bd13170b752005eba9dedd65a0daa6bda6f3885a5d01335bf14007a`, manifest digest `cd504ca289016c2a42c2e9a90cbe92723cdb8a95bc5e030ddedc9b16563d5ff0` |
| Frozen code used unchanged | `code/train_entry.py` `fe585ffe935af132728bc69d4f7ccf044e8fc77b013566b9895af0f3d2e19431`, `code/eval_entry.py` `4406a0385e0156034b423f575f8bce2e5433474898b7b50e1ae048af5a4431e3`, `code/attention_policy.py` `2f7c5431787073566de89a711b2988b1050369c395e992ec602578aa50d5de64`, `code/mlp_baseline.py` `d70c0fa1bf5885088d458383a091134d4573ea485f5aa7d2fc35c51c7700caa1`, `code/descriptor_v2.py` `f313bddf8e5468e513868a95658814105c5463870ab4306e8ffbcec6af848f00`, `code/vendor/NOTES.md` `5f18b09c0b6208a955bd18a27706b46a8a0192bc1b92e85b78e9ae90354226fe` (sha256, from the manifest) |
| Base config | `configs/colab_smoke.yaml` `70cee6244d39ce861d9e318f354bc1473a179a55fddbbd0d91c036911317bfc7`. P4 does **not** run it directly. CR-B0-1 (§2.2) derives the P4 config from it |
| Runbook / notebook | `docs/COLAB_RUNBOOK.md` `302c27409e836d044659ff98af216a61865acec602951686bee377045c330e6d`, `notebooks/colab_smoke.ipynb` `5b59be6a8f5467f6f6f2b60f11a42207293436278e07f3f25a3c7de35735f6e8`, inside the tarball. §4 below lists the P4 substitutions |
| Upstream | `https://github.com/CuboiLeo/SuperMimic-Reproduced` @ `d9be385b3eeb13a638fb33fb200d3bfd9be9839f` (`code/vendor/NOTES.md`) |
| Motion data | The 4 clips in the frozen config (`walk1_subject1`, `run1_subject2`, `dance1_subject1`, `jumps1_subject1`; FX-3 verified). Downloaded only on the runtime and never copied back (X-002). BLK-11 accepted |
| Runner discipline | OVERLAY-001 rules 1–6. They apply on either venue (§2.3) |

### 2.2 P4-prep change request (must be sealed before P4 attempt 1; not done in this packet)

The frozen config caps training by wall clock (`--schedule.max-hours 0.5`) and checkpoints every 1000 iterations. That cannot give equal updates per arm: in P2, attention got 524 updates in 1350 it and mlp_matched got 544 in 1400 it. It also produces no 25/50/75% checkpoints for M-5. The P4-prep packet therefore files one change request against the D-004 freeze. **CR-B0-1** consists of **new files only**. The 12 frozen files stay byte-identical.

- **(a) New config file `configs/b0_microbench.yaml`.** It is a byte copy of `configs/colab_smoke.yaml` with **only** these values changed:
  - `run_name: b0`
  - `--schedule.max-hours: 1.5`. This is a safety cap only, never the budget.
  - `--schedule.checkpoint-interval: 400`
  - the upstream cap flag, set to stop at iteration 1600, **only** if F-1 (below) shows that the flag exists, counts **training iterations** (not policy updates), and writes `ckpt` at iteration 1600 before it stops. Otherwise no cap flag is added and the harness stop applies.

  Everything else keeps the frozen values:
  - `--env.num-envs 512`, `--policy-trainer.batch-size 512`, `--policy-trainer.horizon 16`
  - `--policy-trainer.compile None`, `--schedule.log-interval 50`, `--env.anchor-obs true`
  - `upstream.repo_dir`, the clips, descriptor v2, `id_mode: morph`
  - `b2.mask_fracs [0.1, 0.2]`, `train_mask_frac 0.0`, `eval.num_envs 64`
- **(b) New config file `configs/b0_microbench_lr05.yaml`.** It equals (a) with `run_name: b0lr05` and the upstream policy learning-rate flag (F-2) set to 0.5 × its pinned default. It is used **only** by the divergence rule (§6.3).
- **(c) `packets/P4/UPSTREAM_FACTS.md`.** It records five facts, read from the upstream source at the pin, each with file and line:
  - **F-1** the iteration-cap flag: its name, its unit (iterations or updates), and its endpoint semantics (inclusive or exclusive, and whether a checkpoint is written at the cap). Or "none".
  - **F-2** the policy learning-rate flag and its default value. Or "none".
  - **F-3** the policy grad-norm clip threshold (`max_grad_norm` or equivalent). Or "none".
  - **F-4** what tb `policy/policy_grad_norm` logs: pre-clip or post-clip, and per update or aggregated per log window (mean, last, or max). Also whether any per-update clip indicator is logged.
  - **F-5** env steps per training iteration as a function of the config. Or "not determinable".
- **(d) A P4 driver script** under `packets/P4/` that runs exactly §4 and writes exactly §8. It is new code outside `code/`.
- **(e) A new tarball**, deterministic as in P1, plus a manifest addendum. The addendum lists the old 12 files with unchanged hashes, and the new files. Both hashes go into `logs/seal.log` before any P4 execution.

**Pre-registered handling of each fact:**
- **F-1 = none, or unsuitable.** The driver performs the **harness stop** (§4.3). It is not a deviation. In every case the budget endpoint is the iteration-1600 checkpoint.
- **F-2 = none.** The divergence retry (§6.3) cannot run, and a divergence makes the verdict BLOCKED (§6.4).
- **F-3 = none, or F-4 shows no per-update pre-clip norm and no per-update clip indicator.** The SCHEME_PLAN stability criterion ("clipped on > 50% of updates") cannot be evaluated. No logged-point proxy is substituted. **P4 does not start (PS-3 below)** until the human lead signs one of two rulings:
  - **(i) omit the clip clause.** The decision then carries a stability-evidence confound.
  - **(ii) add per-update clip logging.** This goes through a separate observation-only change request. Under (ii), PS-3 holds only when all three are true: the logging change request is **implemented and sealed** (new tarball and manifest addendum); a CPU or short-venue check log shows the per-update clip numerator and denominator being written; and the harness can compute M-6 from those fields. M-6 is then not `null`, and the clip clause in §6.3 is evaluated. A signature without that implementation does not satisfy PS-3.
- **F-5 = not determinable, or arm-dependent.** P4 does not start (PS-4 below) until RV-8 env-step parity is established. That needs either source-backed proof that env steps per iteration depend only on config, not on arm or policy behaviour, or a direct env-step counter.
- **(f) Launcher check (CPU, on the box).**
  - The driver starts the trainer through the signal-restoring launcher in §4.2.
  - P4-prep runs a CPU test: a dummy Python script with a `finally:` block that writes a file is started by the same driver code path (a non-interactive bash background job) and sent SIGINT. The test passes if the `finally` file is written and the exit is non-zero, not a kill.
  - The test log is sealed (`logs/p4prep/sigint-check-attempt<N>.log`).

**Pre-start gates (all must hold, as recorded in sealed P4-prep files, before P4 attempt 1 spends GPU time):**
- **PS-1.** CR-B0-1 (a)–(e) is sealed.
- **PS-2.** F-1, F-2, F-3, F-4 and F-5 are recorded.
- **PS-3.** One of three conditions holds: the clip clause is evaluable from F-3/F-4; ruling (ii) is signed **and** its logging is implemented, sealed and validated as stated above; or ruling (i), explicit omission, is signed.
- **PS-4.** Env-step parity is established (F-5), or the human lead has signed a ruling accepting the gap.
- **PS-5.** The SIGINT launcher check (f) has passed.

A failed pre-start gate is not a P4 attempt and spends nothing. Any human-lead ruling under PS-3 or PS-4 is an appended Class-2 amendment to this PLAN, signed before attempt 1.

Observation-only logging (RCA C1 to C3) would edit frozen wrappers. It is **not part of CR-B0-1**. If wanted, it needs its own change request and manifest treatment. No gate in this PLAN may depend on it. The one exception is per-update clip logging added under PS-3 ruling (ii), which feeds M-6. The harness uses only tags and fields that the P2 bundles already contain (§8).

### 2.3 Venue

| Venue | Runner | Status in this PLAN |
|---|---|---|
| **XN-4090-GPU2** (shared host, job contract `/srv/claude/research/METHOD/venues/xn-4090-gpu2.md`) | Remote job runner, via the owner's jump host. Job JSON `orch/jobs/<job_id>.json` set to `READY` only after the upload bytes and job JSON are sealed | **Intended P4 venue** (BLK-12 preference) |
| **Colab L4** | Owner (human) under OVERLAY-001 | Pre-registered alternate, and the venue for short work (env sanity, re-checks) |

- The P4 runner packet records the venue choice in its job JSON (XN-4090) or its runner note (Colab) **before attempt 1**. Choosing between these two pre-registered venues is not a PLAN change.
- **All required runs and all evals of P4 run on one GPU model.** The `nvidia-smi` header must match across the bundle set. Mixing venues or GPU models makes the run set BLOCKED (cost metrics and wall-clock stop being comparable). T4 is not allowed for P4.
- OVERLAY-001 rules 2, 3, 4 and 6 (runner input set, deposit-before-open, deviations, verdict by a non-adjudicator) apply on XN-4090 as well, with `logs/xn4090/<date>/` as the deposit path.
- **Paths on XN-4090.** The job's `run.sh` must provide the same absolute layout as Colab: `/content/junior` holds the unpacked CR-B0-1 tarball, and `/content/SuperMimic-Reproduced` holds the upstream clone at the pin. Real directories or symlinks are both fine. `upstream.repo_dir` stays unchanged, and so do the §4 commands. No other path substitution is authorized. Any other layout is a plan gap and requires `BLOCKED.md`.

---

## 3. Arms, seeds, budget, attempts

| Arm | Decoder | Seeds | Role |
|---|---|---|---|
| `attention` | Junior-(B), `id_mode=morph`, descriptor v2 (P1 freeze) | 0, 1, 2 | Arm under test (**gate arm**) |
| `mlp_matched` | MLP, params within ±5% (+0.93%) | 0, 1, 2 | Comparator (**gate arm**) |
| `mlp_upstream` | Upstream-width MLP | 0 | Compute-heavier **reference**. Its results never change the verdict or the outcome (§6.1 REF rows) |

Seeds = 3 per gate arm (SCHEME_PLAN §2). Seeds may not be added without a sealed amendment.

### 3.1 Budget (RV-8)

- **Primary budget: 1600 training iterations per run.** The scored checkpoint is the one written at iteration 1600.
- All runs use identical `num_envs` (512), batch (512), horizon (16), compile (None) and `--env.anchor-obs`. Env steps per run are therefore equal, given equal iterations. F-5 records the per-iteration count if it can be read from source.
- Policy updates are expected to be a deterministic function of the iteration count. P2 fits (it − 40) × 0.4: (1350 − 40) × 0.4 = 524 and (1400 − 40) × 0.4 = 544. That extrapolates to about 624 updates at it 1600, but **the PLAN does not rely on the formula**: V-2 checks `time/updates` at it 1600 directly, for equality across scored gate runs.
- The secondary equal-wall-clock comparison (M-9) is reported only.

### 3.2 Cells, attempt IDs and run order

- A **cell** is one (config tag, arm, seed). The config tag ∈ {`b0`, `b0lr05`}.
- The **attempt ID** is `<tag>_<arm>_s<seed>_a<N>` (for example `b0_attention_s1_a2`).
- Run order on one venue and one GPU model:
  1. env sanity (V-0)
  2. `b0_attention_s0`, `b0_mlp_matched_s0`, `b0_attention_s1`, `b0_mlp_matched_s1`, `b0_attention_s2`, `b0_mlp_matched_s2`
  3. `b0_mlp_upstream_s0`
- Any divergence retry pair (§6.3) runs immediately after the pair whose run diverged.
- All scheduled cells run, even after a terminal outcome is known. No run is skipped or chosen.

### 3.3 Attempt rules (closed list; the runner chooses nothing)

An attempt is any execution that starts the trainer for a cell.

**Completed attempt.** An attempt is completed when §4.3's completion condition holds: `ckpt_0001600.pt` is stable on disk, the it-1600 log line is printed, and `junior_policy.json` exists after exit.

**The first completed attempt of a cell is its scored attempt.** No further attempt of that cell is started, whatever its learning (L-1/L-2), divergence or eval result.

**Scoring endpoint and classification boundary.** The **scoring endpoint** is the moment the trainer log prints the line starting `it 1600 |`. Shutdown completion (§4.3) comes later.

Classification uses only two kinds of evidence:
- **(a)** tb values at steps ≤ 1600.
- **(b)** exceptions or failures whose log output appears **before** the scoring endpoint line.

Anything between the scoring endpoint and the trainer's exit is recorded as `post_endpoint_anomaly` and reported only. That includes non-finite values at steps > 1600 and exceptions (non-finite or not) during continued training or during the harness stop.

After the endpoint, the attempt's class is decided by the completion condition alone:
- **Completed:** checkpoint stable and sidecar present.
- **INFRA:** checkpoint not stable, or sidecar missing. This holds whatever exception occurred after the endpoint.

An attempt that is not completed is classified by the first matching row:

| Class | Condition | Consequence |
|---|---|---|
| **DIV** | NaN or inf in any tb scalar at a step ≤ 1600, **or** the final exception line of the traceback (the `ExceptionType: message` line) matches **R-DIV** (defined below the table). Source lines and identifiers inside the traceback body are not searched | Not retried as an ordinary attempt. It goes to the divergence rule (§6.3) for this seed index |
| **OOM** | CUDA out-of-memory at the frozen size | No retry. In a gate-arm cell: verdict BLOCKED (§6.4). In the reference cell: reported only |
| **SEAM** | Any seam prints `unverified` or `false` | No retry. In a gate-arm cell: BLOCKED, then a change request against D-004 and a new PLAN amendment for the cell count. In the reference cell: reported only |
| **INFRA** | Disconnect, preemption, host or runtime kill, CUDA or driver init failure, data download failure, the safety cap reached before it 1600, sidecar missing after the harness stop, or any other traceback before completion | **Retry-eligible.** At most 2 attempts per cell. A second INFRA in a gate-arm cell gives BLOCKED. In the reference cell it is reported only |

**R-DIV** (Python `re`, applied to the final exception line only):

```
(?i)\b(nan|inf)\b|non-?finite|not finite
```

`\binf\b` also matches `-inf`.

- The divergence retry pair forms new cells (tag `b0lr05`) with the same attempt rules.
- **Archive every attempt.**
  - When any attempt ends, whatever its class, the driver copies that run directory **without `*.pt` files** to `logs/attempts/<AID>/`. This happens after the attempt's evals if it completed. The harness reads the tb and sidecar of **every** attempt (scored, replaced, terminal or failed) from `logs/attempts/<AID>/`.
  - Before attempt N ≥ 2 of the same cell starts, the driver moves the live directory aside to `logs/attempts/<previous AID>.live/`. The frozen wrapper reuses `logs/<tag>_<arm>_s<seed>/` for every attempt, so this keeps the next attempt's directory fresh.
  - Train stdout and GPU-memory files are always named by attempt ID (§4).
  - Every attempt, used or not, is in the bundle and in `runs.log`.
- Resume is **not used** in P4: the frozen wrapper has no resume path, and a resume would break update parity.

### 3.4 Allowed without amendment (record each in `deviations.md`)

- the R1 wheel substitution per runbook §2
- a session restart between attempts or cells
- the harness stop (§4.3)
- the XN-4090 path layout in §2.3

Halving `num_envs` or batch is **not** pre-allowed in P4, because it changes the budget. **Anything else** is a plan gap: stop and write `BLOCKED.md` (method §12.2). That includes other config values, code edits, clip changes and venue mixing.

---

## 4. Exact commands (the CR-B0-1 driver implements exactly this)

### 4.1 Setup

1. Runbook §1–§4 as frozen, except that the CR-B0-1 tarball is uploaded instead of re-packing.
2. `sha256sum` of that tarball on the venue must equal the sealed hash before unpacking. Write the output to `meta/tarball_sha256.txt`.
3. Expect 14 PASS lines in the CPU test, 3 of them preceded by SKIP, as in P2. Write the test output to `meta/cpu_test_smoke.log`.
4. Write `nvidia-smi` to `meta/nvidia-smi.txt` and `uv pip freeze` to `meta/pip-freeze.txt`.

```bash
# V-0 env sanity, once per venue (runbook §5 as frozen: unmodified decoder, max-hours 0.1)
env -u PYTHONPATH $PY -m supermimic.scripts.train --run-name up_sanity --data.npz-dir data/npz/lafan1_smoke \
  --env.num-envs 256 --policy-trainer.batch-size 256 --policy-trainer.horizon 16 \
  --policy-trainer.compile None --schedule.max-hours 0.1 2>&1 | tee logs/train_up_sanity.log
```

### 4.2 Training one attempt (run from `/content/SuperMimic-Reproduced`)

```bash
# TAG in {b0, b0lr05}; CFG=/content/junior/configs/b0_microbench.yaml  (b0)
#                      CFG=/content/junior/configs/b0_microbench_lr05.yaml (b0lr05)
train_attempt() { TAG=$1; CFG=$2; ARM=$3; SEED=$4; N=$5; AID=${TAG}_${ARM}_s${SEED}_a${N}
  RUN=${TAG}_${ARM}_s${SEED}
  [ $N -ge 2 ] && mkdir -p logs/attempts && mv logs/${RUN} logs/attempts/${TAG}_${ARM}_s${SEED}_a$((N-1)).live
  nvidia-smi --query-gpu=timestamp,memory.used,memory.total --format=csv -l 5 > meta/gpumem_${AID}.csv & SMI=$!
  # signal-restoring launcher: a non-interactive bash '&' job starts with SIGINT ignored, and Python keeps SIG_IGN.
  # Setting SIG_DFL and then exec gives the trainer the normal KeyboardInterrupt handler, so the wrapper's finally runs.
  env -u PYTHONPATH $PY -c 'import os,signal,sys; signal.signal(signal.SIGINT, signal.SIG_DFL); os.execv(sys.argv[1], sys.argv[1:])' \
      $PY /content/junior/code/train_entry.py --mode upstream --policy $ARM \
      --config $CFG --seed $SEED > logs/train_${AID}.log 2>&1 & TR=$!
  # harness stop (section 4.3) runs here when F-1 = none/unsuitable; otherwise: wait $TR
  kill $SMI
  # after evals (if completed), for every attempt:
  #   mkdir -p logs/attempts/${AID} && tar -C logs/${RUN} --exclude='*.pt' -cf - . | tar -C logs/attempts/${AID} -xf -
}
```

### 4.3 Completion condition and harness stop

**Completion condition.** All three must hold:
- the trainer log contains a line that starts with `it 1600 |`
- `logs/<RUN>/ckpt_0001600.pt` exists, and its size is unchanged across two polls 30 s apart, taken after that log line
- after the trainer exits, `logs/<RUN>/junior_policy.json` exists

**Harness stop** (used when F-1 = none or unsuitable):
1. Once the first two conditions hold, the driver sends **SIGINT** to the trainer PID. It never sends SIGTERM or SIGKILL. SIGINT lets the frozen wrapper's `finally` block write `junior_policy.json`.
2. The driver waits up to 300 s for exit.
3. If the process is still alive, the driver records `harness_stop_timeout`, classifies the attempt INFRA, and only then sends SIGKILL.

The driver writes `meta/harness_stop_<AID>.txt`, recording the time of the log line, the two checkpoint sizes, the signal, the exit code and the sidecar check.

### 4.4 Eval of a completed attempt

```bash
eval_attempt() { AID=$1; RUN=$2; CFG=$3
  for IT in 0000400 0000800 0001200 0001600; do
    for K in 1 2; do
      D=logs/eval/${AID}/it${IT}/exec${K}; mkdir -p $D
      env -u PYTHONPATH $PY /content/junior/code/eval_entry.py --mode upstream --config $CFG \
          --ckpt logs/${RUN}/ckpt_${IT}.pt > $D/eval.log 2>&1; echo "exit=$?" >> $D/eval.log
      mv logs/eval/${RUN}_*_mask*.json $D/ 2>/dev/null
      [ "$(ls $D/*_mask*.json 2>/dev/null | wc -l)" -eq 3 ] && grep -q '^exit=0$' $D/eval.log && break
    done
  done; }
# after all training and eval:
ls -lR logs/b0_* logs/b0lr05_* logs/attempts 2>/dev/null > meta/ckpt_dirs_ls.txt
```

- **Eval executions.** An eval execution is one `eval_entry` call for one (attempt, checkpoint).
  - A second execution (`exec2`) runs **only** if `exec1` exited non-zero or did not produce all three mask JSONs.
  - There is never a third execution, and a successful execution is never repeated.
  - **The scored execution is the first one that passes V-4's content checks** (§6.1). All executions stay in the bundle.
- The `[eval_entry]` argv line in each `eval.log` names the checkpoint path. That line is the checkpoint-identity record.
- If the trainer names checkpoints differently from `ckpt_%07d.pt`, the driver maps the 400/800/1200/1600 checkpoints by iteration number and prints the mapping into `meta/ckpt_map.txt`. That is a bug fix under §12.2, because this PLAN specifies the iterations.
- The run directory names come from the frozen `train_entry.tyro_argv`, which builds `{run_name}_{arm}_s{seed}`.

---

## 5. Metrics (definitions frozen here)

**Eval source.** Each scored eval execution has three JSONs, one per mask. Each has per-clip records `clips[].{name, frames, steps, norm_return, failed, fail_step}` and `summary.{mean_norm_return, step_weighted_norm_return, failed, terms}`. These fields exist in the P2 bundles.

**Why the primary metric changed.** Upstream `norm_return` is a **per-step** mean reward divided by the max per-step reward (0.1). Episode length does not enter it (RCA §1.1, verified to 4 decimals in all 12 P2 eval JSONs). A policy that falls early but tracks well while standing therefore scores high. On P2 attempt 2 at mask 0, mlp_matched has per-step `mean_norm_return` 0.42 against 0.33 for attention, yet survives 196 total steps over 4 clips against 720. On that run the per-step metric and the survival/cumulative metrics rank the arms in **opposite** orders (RCA §2), so a per-step mean cannot be the sole ranking metric (decision note "carry into P3"; RCA B3). On the same data R_H (T = 500) is 0.041 for mlp_matched and 0.112 for attention.

| ID | Name | Definition | Role |
|---|---|---|---|
| **M-1** | **R_H(run)**: horizon-normalised cumulative return | R_H = Σ_c norm_return_c · min(steps_c, T) / (4 · T), with **T = 500 env steps** (10 s at 0.02 s per step). The sum runs over the 4 registered clips, at mask 0.00, on checkpoint 1600. Range [0, 1]. It equals the per-step mean when every clip survives T steps, and it scales down linearly with early termination. Arm value R̄_H = mean over the 3 scored seeds | **Primary gate metric** (§6.2) |
| M-1s | R_step(run) | `summary.mean_norm_return` at mask 0.00, checkpoint 1600. This is SCHEME_PLAN M-1 read literally | Reported, plus a **non-binding shadow verdict** (§6.2) |
| M-1c | Cum(run) | Σ_c norm_return_c · steps_c. Uncapped cumulative normalised return, in units of (max per-step reward × steps) | Reported |
| M-2 | Fail(run), Surv(run) | `summary.failed` (clips terminated early). Surv = Σ_c steps_c. Also per-clip `steps` and `fail_step` | Reported (survival is mandatory, §7) |
| M-3 | Cost | ms per policy update = 1000 × 3600 × (hours at it 1600 − hours at it 400) / (updates at it 1600 − updates at it 400), from tb `time/hours` and `time/updates`. Also tb `time/{sim,wm,policy}_s_per_iter` (mean over it 400–1600), and it/s = 1200 / (seconds from it 400 to it 1600). Peak GPU memory = max `memory.used` in `meta/gpumem_<AID>.csv`. env-steps/s = it/s × F-5 count, or "not derivable" | Reported (RV-1: "slower" is a cost, not a kill term) |
| M-4 | WM loss curve | tb `wm/loss` per logged point | Gate L-2, and reported |
| M-5 | Eval learning curve | M-1, M-1s, M-1c and M-2 at checkpoints k = 400/800/1200/1600 (25/50/75/100% of budget). **AULC_H** = (1/3) · Σ_{k=1}^{3} (R_H,k + R_H,k+1)/2: the trapezoid area over [25%, 100%] of budget, divided by the interval length | Reported (feeds later AULC comparisons) |
| M-6 | Policy grad-norm and clip fraction | Series: tb `policy/policy_grad_norm`. Clip fraction, **only if F-3 exists and F-4 gives per-update pre-clip norms or a per-update clip indicator**: (number of updates in iterations (1200, 1600] that were clipped) / (number of updates in that range). Otherwise `null` ("not evaluable") | Divergence rule (§6.3), and reported |
| **M-7** | **C_train(i)**: train cumulative return proxy | C_train(i) = `train/episode_len`(i) × `train/episode_norm_return`(i) at each logged point i. It is a product of window means, not a mean of per-episode products, so it is an approximation (RCA §1.3). It is the "episode_len × norm_return" quantity from RCA option B1, without the RCA's 0.1 factor. **It replaces per-step `train/episode_norm_return` in every train-return gate** | Gate L-1, and reported |
| M-7s | Train per-step return | tb `train/episode_norm_return` | Reported only, **no threshold**. P2 P-4 failed on exactly this quantity |
| M-8 | Action smoothness and penalty terms | All eval `summary.terms` (including `action_rate_l2` and `joint_limit`) per mask and checkpoint. tb `policy/action_abs_mean` | Reported (RCA C3 behaviour difference) |
| M-9 | Equal-wall-clock comparison (RV-8 secondary) | W = min over the 6 scored gate runs of tb `time/hours` at it 1600, so W never exceeds any run's last checkpoint. For each scored gate run, R_H(W) is interpolated linearly in hours between its two bracketing checkpoints (checkpoint hours from tb `time/hours` at that iteration). If W is below that run's it-400 hours, R_H(W) = `null`. Arm value = mean over seeds of the per-run R_H(W), or `null` if any is null | Reported only |
| M-10 | Mask evals and retention | M-1, M-1s, M-1c and M-2 at masks 0.10 and 0.20, at every checkpoint. Retention ρ_H(f) = R_H(mask f)/R_H(mask 0) and ρ_step(f) likewise. ρ = `null` if the denominator is 0 | Reported only. **B2 thresholds are frozen in the P5 PLAN, not here** (SCHEME_PLAN §3). P5 reuses these files |

**Notes on T and clip length.**
- **T = 500 is fixed now, after the P2 data were seen.** P2 survival was 42–379 steps per clip, and T covers that range with headroom. A smaller T would saturate for the better arm. A larger T would compress both arms toward 0, where the δ floor of 0.05 becomes lenient. This is disclosed under Confounds.
- **Approximation for steps_c > T.** For such a clip, the formula uses the whole-episode per-step mean × T, which approximates the return over the first T steps. The harness reports how many clip records hit this case (`rh_clips_over_T`).
- **No frame conversion.** Clip `frames` are not converted to env steps, because the mapping from frame rate to env step is unverified.

**TB extraction rules.**
- Each `logs/attempts/<AID>/` must contain exactly one tb event file. The live directory is moved aside before every new attempt of a cell (§3.3), so a second file means contamination. For a scored gate run, that fails V-1.
- Within that file, if a tag has more than one value at the same step, the value with the latest wall time is used.
- The **logged points** for M-7 and L-1/L-2 are the steps at which `train/episode_len`, `train/episode_norm_return`, `wm/loss` and `time/updates` all have a value.
- A missing it-1600 point fails V-1.

---

## 6. Gates and verdict (machine-computed; prose never overrides)

The harness verdict is computed from the deposited bundles by an agent process that is not an adjudicator (OVERLAY-001 rule 6). The write-up is by `claude-sonnet` (SCHEME_PLAN §7). The Orchestrator that wrote this PLAN does not adjudicate it.

**Scored run set.** For each of the 6 gate-arm seed slots, the scored run set holds the scored attempt (§3.3). Where §6.3 applied, the slot holds the `b0lr05` replacement pair instead.

### 6.1 Validity and learning gates

| ID | Criterion | Applies to | Source |
|---|---|---|---|
| V-0 | Env sanity ran to its 0.1 h cap with no exception, once on the chosen venue | venue | `train_up_sanity.log` |
| V-1 | All of the following hold:<br>• The scored attempt meets the completion condition (§4.3).<br>• No NaN/inf in any tb scalar at steps ≤ 1600.<br>• Exactly one tb event file in `logs/attempts/<AID>/`.<br>• A logged point exists at it 1600.<br>• tb `time/hours` and `time/updates` exist at each of it 400/800/1200/1600.<br>• **Window coverage:** at least 10 logged points (§5 TB rules) at it ≤ 1600 with `time/updates` ≥ 20, so the first-5 and last-5 windows of L-1/L-2 do not overlap | scored gate runs | logs, tb, `meta/ckpt_dirs_ls.txt`, `meta/harness_stop_*` |
| V-2 | **Budget parity (RV-8)** — all three must hold: (a) tb `time/updates` at it 1600 is identical across all scored gate runs. (b) The `[train_entry] upstream argv` line is identical across scored gate runs, except for `--run-name` and `--seed` and, for `b0lr05` runs only, the F-2 LR flag at exactly 0.5 × default. (c) The GPU name in every bundle's `nvidia-smi` header is identical | scored gate runs; (c) all bundles | tb, logs, `meta/nvidia-smi.txt` |
| V-3 | Seams: S1 and S2 true; S3 recorded and identical; S4 = `env_init_state`; S5 true; no `unverified` seam line. The descriptor sha256 in `junior_policy.json` is identical across the scored attention runs | scored gate runs (S4, S5 and descriptor: attention runs) | train logs, sidecars |
| V-4 | Each of the 4 checkpoints has a scored eval execution containing three mask JSONs (0.00/0.10/0.20). Each JSON contains **exactly** the 4 registered clip names, each once. Every clip has integer `steps` ≥ 1, finite `norm_return`, boolean `failed`, and a `fail_step` when `failed`. `summary.mean_norm_return` and `summary.step_weighted_norm_return` are finite. `summary.failed` is an integer. `summary.terms` is a non-empty object with finite values. `eval.log` names the matching checkpoint path | scored gate runs | `logs/eval/<AID>/it*/exec*/` |
| **L-1** | **Train cumulative return rises.** Mean C_train (M-7) over the **last 5 logged points with it ≤ 1600** is greater than mean C_train over the **first 5 logged points with `time/updates` ≥ 20** | must hold for **≥ 2 of 3 scored seeds in each gate arm** | tb |
| L-2 | WM loss falls. Mean `wm/loss` over the same last-5 window is less than the mean over the same first-5 window | every scored gate run | tb |
| REF-1..REF-4 | The same checks as V-1, V-3 (seams S1–S3), V-4 and L-1/L-2, computed for `mlp_upstream`. Divergence of `mlp_upstream` is reported here as well | reference run | as above |

**REF rows are reported only.** They never enter §6.2–§6.4.

**Why L-1 uses cumulative return.** Sealed P2 gate P-4 used per-step `train/episode_norm_return`, comparing the end with the first post-warmup point. It FAILED on attempts 1 and 2 in both arms, while survival rose 27–125% and the cumulative proxy rose 18–78% (RCA §1.3).
- The RCA classifies that failure as a metric artifact. Learning lengthens episodes, which lowers a per-step average, and the warmup anchor is a near-zero-action policy (RCA §1.2).
- The A1 ruling accepted P2 at Provisional with the FAIL disclosed (`DECISION-A1-P2-close-20261026.md`).
- The decision note requires cumulative return for any train-return gate (`DECISION-RV-BLK-20261026.md`).

**P2 cross-check (RCA §4 B1).** The RCA computed this window rule (`time/updates` ≥ 20, first 5 vs last 5) as a raw-return proxy, which includes the 0.1 factor. All 4 P2 arm-runs pass L-1:

| P2 arm-run | Raw proxy (RCA units), first 5 → last 5 | M-7 units (× 10) |
|---|---|---|
| a1 attention | 1.233 → 1.922 | 12.33 → 19.22 |
| a2 attention | 1.220 → 1.890 | 12.20 → 18.90 |
| a1 mlp_matched | 1.180 → 1.347 | 11.80 → 13.47 |
| a2 mlp_matched | 1.191 → 1.362 | 11.91 → 13.62 |

The units do not change the direction of any comparison. This result was known when the rule was written, and it is disclosed here. The justification for the rule is the metric definition (RCA §1.1), not the fact that P2 would pass it.

### 6.2 B0 comparison (primary; RV-1 as accepted)

**Inputs** (from the scored run set):
- R_H (M-1) at checkpoint 1600, mask 0.00, for the 3 scored seeds of each gate arm.
- s_att and s_mlp: sample standard deviations across seeds (ddof = 1).
- SE_pooled = √(s_att²/3 + s_mlp²/3), the standard error of the difference of arm means.
- Δ = R̄_H(attention) − R̄_H(mlp_matched).
- **δ = max(0.05, 2 · SE_pooled)** (SCHEME_PLAN §2, RV-1).

| Outcome | Rule |
|---|---|
| **NONINFERIOR** | Δ ≥ −δ, **and** no scored attention run diverged (any divergence was resolved by the §6.3 retry) |
| **SUPERIOR** (flag, reported only) | NONINFERIOR **and** Δ ≥ max(0.02, 2 · SE_pooled) |
| **INFERIOR** (kill candidate, combined with B2 per SCHEME_PLAN §3) | Δ < −δ (`outcome_basis = margin`), **or** terminal attention divergence (§6.3; `outcome_basis = divergence`) |

- **Noise-widened flag (reported).** If NONINFERIOR holds only because 2·SE_pooled > 0.05 (that is, Δ < −0.05), the harness sets `noise_widened = true`.
- **No INCONCLUSIVE band.** With δ defined as above, "Δ ≥ −δ" and "Δ < −δ" are exhaustive. SCHEME_PLAN's "pooled-SE overlap with neither condition met" therefore has no region of its own under the literal RV-1 rule. This PLAN keeps RV-1 literally and does not invent a third band; the noise-widened flag carries the information the scheme meant by overlap. A human lead who wants a separate INCONCLUSIVE band must sign a Class-2 amendment before P4 attempt 1. Until then `INCONCLUSIVE` is never emitted.
- **Shadow verdict (non-binding).** The same rules are evaluated on R_step (M-1s), the scheme's literal per-step M-1, and the result is reported as `shadow_outcome_rstep`. If it differs from the primary outcome, the harness sets `metric_disagreement = true` and the difference is disclosed. The shadow verdict never changes the verdict.

### 6.3 Divergence rule (SCHEME_PLAN §2, pre-registered; the single definition used everywhere)

A gate-arm attempt **diverges** if either of these holds:
- **(a)** NaN or inf appears in any tb scalar at a step ≤ 1600, **or** an exception whose log output appears before the scoring endpoint line (§3.3) has a final exception line that matches the §3.3 DIV regex. This applies whether or not the attempt completed. The §3.3 boundary applies. Anything after the scoring endpoint line, whether a scalar at a step > 1600 or an exception, is `post_endpoint_anomaly` and reported only.
- **(b)** The clip fraction (M-6) is above 0.5. This test is skipped when M-6 is `null`.

**Retry pair.** The **first** divergence at seed index s triggers exactly one retry pair: both `attention` and `mlp_matched` at seed s are run with `b0_microbench_lr05.yaml` (tag `b0lr05`, policy LR × 0.5), so the pair stays matched.
- The `b0lr05` pair replaces the `b0` pair for seed s in the scored run set.
- The `b0` pair stays in `runs.log` and in the results.
- There is never a second retry pair for the same seed index.

**Terminal outcomes:**
- **Terminal attention divergence.** The `b0lr05` attention run at seed s diverges. This counts as INFERIOR (scheme rule; §6.4 row 2).
- **Terminal comparator divergence.** The `b0lr05` mlp_matched run at seed s diverges. The comparator is invalid, and the verdict is BLOCKED.
- **F-2 = none.** Any divergence gives BLOCKED.

### 6.4 Spike verdict: ordered decision table (the first matching row wins)

| # | Condition | `verdict` | `b0_outcome` |
|---|---|---|---|
| 1 | Any of the following holds, all scoped to **gate-arm** cells and runs:<br>• V-0 false<br>• R1 unresolved after the fallback<br>• any gate-arm attempt classed OOM or SEAM (§3.3)<br>• the INFRA attempt cap exhausted on any gate-arm cell (this includes `harness_stop_timeout` on a second attempt)<br>• V-1, V-2, V-3 or V-4 false on the **checkable gate runs** (see below)<br>• terminal comparator divergence<br>• F-2 = none together with any gate-arm divergence<br>• the spend cap reached before the gate set is complete (predicate below)<br>• a bundle that fails the deposit/seal check (§8.2) | **BLOCKED** (`blocked_reason` lists every matching item) | `null` |
| 2 | Terminal attention divergence (§6.3), with no row-1 condition | **PASS** | **INFERIOR**, `outcome_basis = divergence`. Δ, δ and SE are `null`; `superior` and `noise_widened` are false |
| 3 | L-1 false (fewer than 2 of 3 scored seeds pass in either gate arm) or L-2 false on any scored gate run, with no row-1 or row-2 condition | **FAIL** (`failing_ids` ⊆ {L-1, L-2}) | `null` |
| 4 | All other cases. Here V-0…V-4, L-1 and L-2 are all true | **PASS** | NONINFERIOR or INFERIOR per §6.2, plus the flags |

- **The table is exhaustive.** Any failed validity check (V-0…V-4) on a checkable gate run is caught by row 1. Any failed learning check is caught by row 3. Row 4 is reached only when everything holds.
- **Checkable gate runs.**
  - These are all scored gate runs except a terminally diverged attention run (§6.3).
  - A terminally diverged attention run may have stopped before it 1600. Only its **endpoint-dependent** requirements are exempt: V-1 completion condition, the it-1600 point, the checkpoint timing tags and window coverage; V-2(a) updates at 1600; and V-4 evals.
  - Its **evidence-integrity** checks still apply and are evaluated in full:
    - `logs/attempts/<AID>/` exists and contains **exactly one** tb event file
    - its `logs/train_<AID>.log` is present
    - the divergence evidence comes from that single tb file (a value at a step ≤ 1600) or from that log (a matching exception before the scoring endpoint line)
    - V-2(b)/(c) (argv and GPU name) and the V-3 seam checks
  - If any of these integrity checks fails, row 1 applies (BLOCKED), not row 2.
  - Every other run, including its paired `b0lr05` mlp_matched run, is checked in full.
- **Gate set complete, and the spend-cap predicate (the same predicate as §9).** The gate set is complete when each of the 6 gate-arm seed slots has either a scored attempt with all its scored eval executions, or a terminal attention divergence.
  - If the spend cap is reached **before** the gate set is complete, row 1 applies (BLOCKED).
  - If the spend cap is reached **after** the gate set is complete, only the remaining reference work stops. REF rows report `incomplete`, and the verdict is unaffected.
- **PASS means the comparison was validly executed. It is not a claim that attention wins.** INFERIOR is a PASS-verdict outcome.
- REF rows never move the verdict.
- A BLOCKED verdict goes to the human lead with `BLOCKED.md`.
- The **combined B0+B2 gate to B1** follows SCHEME_PLAN §3 unchanged, after P5. P4 alone does not open or kill B1.

---

## 7. Eval reporting requirements

For every scored run, checkpoint and mask, report:
- **survival:** per-clip `steps`, `failed` and `fail_step`; Surv = Σ steps; the Fail count
- **cumulative return:** M-1c, plus M-1 (R_H)
- **per-step mean:** `mean_norm_return` and `step_weighted_norm_return`
- **behaviour:** all `summary.terms`

A per-step mean is never reported without the survival and cumulative numbers beside it, and no single per-step metric ranks arms (RCA B3).

**Masks:**
- B0 gates use **mask 0.00 only**.
- Masks 0.10 and 0.20 are evaluated and reported (M-10) so P5 can reuse them. The root is never masked (frozen code).
- It is **unverified** whether `eval_entry`'s mask sampling uses a fixed seed list. P4 does not repeat successful evals to test this (§4.4). The P5 PLAN must settle mask-seed fairness (RV-2) before it uses these files for B2 thresholds.

---

## 8. Must capture, bundle layout, harness keys

### 8.1 Bundle

**Archive.** One archive per session (Colab) or per job (XN-4090), returned unmodified and named `b0-<YYYYMMDD>-<HHMM>[-partN].tgz`.

**Contents:**
- `meta/nvidia-smi.txt`, `meta/pip-freeze.txt`, `meta/cpu_test_smoke.log`, `meta/tarball_sha256.txt`
- `meta/ckpt_dirs_ls.txt`, plus `meta/ckpt_map.txt` if used
- `meta/gpumem_<AID>.csv` and `meta/harness_stop_<AID>.txt` (if used), one each per attempt
- `train_up_sanity.log` and `logs/train_<AID>.log` for **every** attempt
- `logs/attempts/<AID>/` (sidecar, tb and any other non-`*.pt` files) for **every** attempt: scored, replaced, terminal or failed. Also any `logs/attempts/<AID>.live/` directories, with `*.pt` files removed before packing
- `logs/eval/<AID>/it<IT>/exec<K>/{eval.log, *_mask*.json}` for every eval execution
- `deviations.md` (may be empty), and `BLOCKED.md` if applicable
- for XN-4090, also the job JSON and the remote runner's stdout

**No motion data and no checkpoint files (`*.pt`) leave the venue.** The archive keeps only `ls` listings of the checkpoints.

### 8.2 Deposit and seal-before-open

- **Deposit paths:**
  - Colab: `logs/colab/<YYYY-MM-DD>/`, seal event `DEPOSIT colab`.
  - XN-4090: `logs/xn4090/<YYYY-MM-DD>/`, the job's `deposit.local_dir`, seal event `DEPOSIT xn4090`.
- **Seal before open.** The archive is kept byte-identical (mode 0444). Its sha256 goes into `logs/seal.log` **before** any agent opens it (OVERLAY-001 rule 3; venue contract). Every archive is deposited, including those from failed or aborted sessions.
- **Verdict tool.** The verdict script (`spikes/B0/verdict/verdict_b0.py`, written in P4-prep or the verdict wake) is sealed as `VERDICT-TOOL` **before the first P4 deposit is opened**. If the script changes after any deposit has been opened, the change is logged as a new tool version and the outputs of both versions are kept.
- **Verdict outputs.** The verdict process extracts each archive read-only and checks member paths: no absolute paths and no `../`. It then writes `spikes/B0/runs.log` (append-only, one block per deposit) and `spikes/B0/results.json`.

### 8.3 `results.json` keys (machine-checkable)

**Top level:**
- **Provenance:** `plan_sha256`, `method_sha256`, `tarball_sha256`, `venue`, `gpu_name`, `deposits[]` (path, sha256, seal line).
- **Verdict:** `verdict` ∈ {PASS, FAIL, BLOCKED}, `decision_row` (1–4), `failing_ids[]`, `blocked_reason[]`.
- **Outcome:** `b0_outcome` ∈ {NONINFERIOR, INFERIOR, null}, `outcome_basis` ∈ {margin, divergence, null}, `superior`, `noise_widened`.
- **Comparison numbers:** `delta`, `delta_threshold`, `se_pooled`, `rbar_h_attention`, `rbar_h_mlp_matched`, `T` (500).
- **Shadow:** `shadow_outcome_rstep`, `metric_disagreement`.
- **Budget:** `budget` = `{iterations: 1600, updates_at_1600: {<AID>: int}, parity: bool, env_steps_per_iter: int|null}`.
- **Scored set and learning:** `scored_set` = {slot → AID}, `l1_seeds_passing` = `{attention, mlp_matched}`.
- **Upstream facts:** `upstream_facts` = `{F-1..F-5}`.
- **Counters:** `rh_clips_over_T`.

**One key per gate ID** (`V-0`, `V-1`, `V-2`, `V-3`, `V-4`, `L-1`, `L-2`, `DIV`, `REF-1`, `REF-2`, `REF-3`, `REF-4`), each with a boolean `pass` and per-attempt evidence.

**`attempts.<AID>`, for every attempt whether used or not:**
- **Identity and status:** `tag`, `arm`, `seed`, `attempt`, `class` (completed, DIV, OOM, SEAM or INFRA), `scored` (bool), `harness_stop`.
- **Training checks:** `reached_1600`, `nan`, `updates_at_1600`, `seams{S1..S5}`, `descriptor_sha256`, `params_policy`.
- **Learning windows:** `c_train_first5`, `c_train_last5`, `nret_train_first5`, `nret_train_last5`, `elen_first5`, `elen_last5`, `wm_loss_first5`, `wm_loss_last5`.
- **Stability:** `clip_fraction_last25` (or null), `grad_norm_max`.
- **Cost:** `ms_per_update`, `it_per_s`, `peak_mem_mib`, `hours_at_1600`, `hours_at_ckpt{400,800,1200,1600}`.
- **Eval**, keyed `eval.it<IT>`: `{scored_exec, mask<f>: {r_h, r_step, r_step_weighted, cum, surv_steps, fail_count, clips[{name, steps, failed, fail_step, norm_return}], terms{…}, rho_h, rho_step}}`. `rho_*` is set for f > 0 only.
- **Summary:** `aulc_h`.

**`m9_wallclock`:** `{W_hours, r_h_attention_at_W, r_h_mlp_matched_at_W, per_run{AID: r_h_at_W}}`.

**Harness output line.** The harness prints exactly one machine-readable line:

`B0_VERDICT verdict=<…> outcome=<…> basis=<…> delta=<…> delta_thr=<…> failing_ids=[…] blocked=[…]`

### 8.4 Also captured (reported, no threshold)

- the `params:` line from the trainer, for every attempt
- the compile setting
- the `nvidia-smi` header
- every deviation
- relay notes, kept outside the archive and not sealed as evidence (as in P2)

---

## 9. Cost, budget and spend gate

| Item | Estimate on Colab L4 (from P2 rates: attention 0.7 it/s, mlp_matched ≈ 0.75 it/s at 512 envs) |
|---|---|
| Env sanity | 0.1 h |
| 3 × attention to it 1600 | 3 × ≈ 0.64 h |
| 3 × mlp_matched | 3 × ≈ 0.59 h |
| 1 × mlp_upstream | ≈ 0.6–0.7 h (unmeasured) |
| Evals (7 runs × 4 checkpoints × 3 masks) | ≈ 0.5–1.0 h (eval duration was not measured in P2) |
| **Total** | **≈ 4.6–5.6 L4 GPU-h**, against the SCHEME_PLAN §8 draft of 4–5 for P4 |

- The overrun comes from the 1600-iteration budget, chosen above P2's 1350 to give the M-5 curve 4 equally spaced checkpoints. It stays inside the BLK-12 envelope (≈ 17–20 L4-h for P4/P5/P6d).
- XN-4090-GPU2 hours are expected to be lower but are unmeasured. Measured wall-clock is reported, not converted.
- **Spend cap for P4: 7 GPU wall-hours on the chosen venue**, including retries. On reaching it, the runner stops after the current cell and deposits. The verdict effect uses exactly the predicate in §6.4. If the gate set is not yet complete, the verdict is BLOCKED (budget), and the human lead decides. If the gate set is already complete, only the reference work stops, and the verdict is unaffected.
- **Spend gate:** no P4 GPU time is used until (1) this PLAN is sealed, (2) CR-B0-1 is sealed, and (3) a runner packet (Colab runner note, or XN-4090 job JSON at `READY`) cites this PLAN's sha256.

---

## 10. Confounds and disclosures (carried into any B0 write-up)

1. **P2 history.** Sealed P2 (`spikes/B0-smoke/PLAN.md`) stays machine **FAIL, failing_ids=[P-4]** on attempts 1 and 2. Attempt 3 was ABORTED and counted toward the P2 cap, with no partial deposit (disclosed deviation from OVERLAY-001 rule 3). P-4 used per-step `train/episode_norm_return`, and its failure is root-caused as a metric artifact (RCA). This PLAN does not relabel P2.
2. **Post-hoc metric choices.** M-1 (R_H, T = 500) and L-1 (C_train, `time/updates` ≥ 20 window) were chosen after the P2 data were seen. Their justification is the metric definition, but the choice of T and of the windows is data-informed. SCHEME_PLAN M-1 (per-step) is kept as the shadow verdict so a reader can see both.
3. **C_train is a proxy.** It is a product of window means, and the train-side `episode_norm_return` definition is inferred, not read from source (RCA §1.1 gap; C1 would close it).
4. **R_H for steps > T** uses the whole-episode per-step mean (§5).
5. **Compute parity.** Matched params ≠ matched compute: attention forward FLOPs are about 27× those of mlp_matched (R4). The primary budget equalizes updates, not wall clock. M-9 reports the wall-clock view.
6. **Reduced scale.** 512 envs, H = 16, against the paper's 4096 envs and H = 32. Absolute returns are not a claim (R3).
7. **Venue.** P4 numbers are not comparable to P2 numbers if the venue differs. Within P4, one GPU model is enforced (V-2).
8. **Planning and review.** This PLAN was written by a Claude-family Orchestrator. A cross-family red team (`codex-astra` high, objections only, read-only) reviewed it in rounds:
   - **Round 1** reviewed draft 1 (sha256 `def49fd11a46ab0cbd3ba479350d7c45a8fed858d91c751afcf6a2d66447a27d`) and returned REVISE, with 2 BLOCKER, 13 MAJOR and 2 MINOR objections.
   - **Round 2** reviewed draft 2 (`c605c40f34ae10e601fe3a054cbfc8af62a90f2817d535a3e65a84af01598b78`). It found 9 objections resolved, 8 not resolved and 3 new, and returned REVISE.
   - All drafts are kept under `logs/p3/`, and the reviews are in `logs/p3/redteam-attempt*-last-message.txt`. Dispositions are in `packets/P3/REDTEAM-DISPOSITION.md`.
   - **Round 3** reviewed draft 3 (`2a64d475ae6abb26ecbcda1ec4b56f7dd9aeee0ebffde9a669e82edd4126d677`). It found 9 of 11 items resolved, 2 not resolved (#3, #20) and 1 new (#21), and returned REVISE.
   - Those three were applied in draft 4, the sealed text. **Draft 4 was not re-reviewed.** The Orchestrator ended review at round 3, because the remaining items were narrow edits to rules. A reviewer of the sealed PLAN may still file objections as a method issue or a proposed amendment.
9. **Depth.** See §0.
10. **Clip sub-clause.** The divergence rule's grad-clip clause may be not evaluable (F-3/F-4). In that case only NaN/inf counts as divergence, and the SCHEME_PLAN clause is not replaced by a proxy.

---

## 11. Method fit (step 4 of the boot)

- No program special beyond the existing overlays is needed. OVERLAY-001 already covers the human runner. The XN-4090 job runner is covered by the global venue contract and §2.3 here (same deposit-before-open and non-adjudicator-verdict rules).
- P3 is a single-Orchestrator PLAN packet, not a contest. A.7 roster allocation for a contest does not apply. The P1 `roster.md` (sealed `5be8a85d…`) is not edited.
- If P4 is later treated as high-stakes, its runner packet records the runner slot (`runner: owner (human), venue: Colab L4` or `runner: xn-4090-gpu2 job runner`) and the verdict-script process.

---

## 12. Explicitly not done in this packet

- `spikes/B0-smoke/PLAN.md` is **not** rewritten or amended. P2 stays historical **FAIL [P-4]**, disclosed.
- No change to any D-004 frozen file. CR-B0-1 is specified here and executed in P4-prep.
- No Colab run, no XN-4090 job, no training, no eval, no spend.
- No P4, P5 or P6 start. P6a (CPU, approved optional) is not started here.

---

## Amendment v1 (Class 2) — PS-3 ruling (i) and F-1 confirmation

**Status:** signed and appended. Does not rewrite any prior sealed section.
**Base PLAN sha256 (unchanged body above this line):** `ed6b6a54a860bbfc67d7c822b5394804b8d408f6aae57fbeb118d2ea63c52557`
**Authority:** Owner decision relayed by Claude Manager for Research Human lead Peter (Class-2 operational sign). Owner wall time Asia/Shanghai **2026-10-26 ~14:25** (CST). Box record America/Toronto below.
**Recorded:** 2026-10-26 02:25 EDT (America/Toronto); UTC 2026-10-26T06:25:57Z.

### PS-3 / F-4 — Option (i) accepted

Upstream fact F-4 (`packets/P4/UPSTREAM_FACTS.md`) shows that tb `policy/policy_grad_norm` is the pre-clip norm averaged over each 50-iteration log window, and that no per-update clip indicator is logged.

**Ruling (i) — omit the clip clause.** The divergence rule §6.3 (b) ("clip fraction (M-6) above 0.5") is **omitted** for P4. Divergence is decided by §6.3 (a) only (NaN/inf in tb at steps ≤ 1600, or an R-DIV exception before the scoring endpoint). M-6 is reported as `null`. The B0 decision carries a **stability-evidence confound**, disclosed under Confounds item 10. No logged-point proxy is used. No CR-B0-2 clip-logging code is required to start P4.

### F-1 — Orchestrator judgment confirmed

`--schedule.total-iterations` is **unsuitable** as the 1600 budget endpoint because it is also the cosine-LR horizon. P4 uses the **harness stop** (§4.3). **Do not rebuild CR-B0-1.** Configs and tarball `packets/P4/junior_b_colab-CR-B0-1.tgz` sha256 `763867682e3cfa05ca8eb6382ffc9124be2347b898531c60b904061776c33bff` stay as sealed in P4-prep.

### Effect on pre-start gates

After this amendment: **PS-3 = true** (ruling (i) signed). PS-1, PS-2, PS-4, PS-5 remain true as recorded in `packets/P4/PRESTART.md`. P4 attempt 1 may start only when a runner packet cites this PLAN (base + Amendment v1) and is ordered to run; this amendment alone does not spend GPU time.
