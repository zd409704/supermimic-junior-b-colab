# P5 bundle contract: what `packets/P5/b2_driver.sh` writes, and what `spikes/B2/verdict/verdict_b2.py` reads

**Packet:** P5-prep (CR-B2-1 (e)). **PLAN:** `spikes/B2/PLAN.md` sha256 `5d1f26f776a3ea56c2becd3ec2fa2cf8e88bd62c43a20f79415a96e82a3da11d`. **Status:** Provisional.
This file adds machine-readable detail to PLAN §4 and §9.1. Where it and the PLAN disagree, the PLAN wins. It extends `packets/P4/BUNDLE_CONTRACT.md` (CR-B0-1) for the P5 job; every P4 record format reused here keeps its P4 definition.

## 1. Archive

- One archive per job session: `b2-<YYYYMMDD>-<HHMM>[-partN].tgz` (UTC time of packing), written to `/content` (`deposit.remote_glob /content/b2-*.tgz`).
- Member paths are relative (`./meta/...`, `./logs/...`). No absolute paths, no `..`, no `*.pt`, no motion data (`*lafan*`, `*.csv` other than `meta/gpumem_*.csv`, `*.npz` other than `logs/eval/*/maskstream_*.npz`).

## 2. Venue paths

| Path | Content | Written by |
|---|---|---|
| `/content/junior` | unpacked CR-B2-1 tarball | driver step 1 |
| `/content/SuperMimic-Reproduced` | upstream clone at `d9be385b…`, reused if present at the pin | P4 (reused) |
| `/content/p5_p4ckpts/logs/b0_<arm>_s<seed>/` | staged copies (`cp -p`) of the six P4 `ckpt_0001600.pt` + `junior_policy.json` | driver step 0 |
| `/content/p5_b2/` | driver work dir: `meta/`, `logs/train_<AID>.log`, `logs/perm_<ID>.log`, `deviations.md`, `BLOCKED.md`; also the two driver scripts extracted by `run.sh` | driver, `run.sh` |
| `<U>/logs/b2mt_*`, `<U>/logs/b2idx_*` | live run directories of new trainings (upstream trainer) | trainer |
| `<U>/logs/attempts/b2*` | archived attempt dirs (no `*.pt`) and `.live` dirs | driver |
| `<U>/logs/eval/b2*` | eval executions | eval wrapper |

The driver never writes, moves or deletes anything under `<U>/logs/b0_*`. Setup (`uv sync`, motion download, `csv_to_npz`) runs in `<U>` as in P4.

## 3. Members (paths relative to the archive root)

| Path | Content |
|---|---|
| `meta/p4_ckpt_identity.txt` | step 0: one `candidate_root=<path> match=<true|false>[ mismatch: <AID>:size=<n>,sidecar=<sha> …]` line per root tried (PLAN §2.2 order, stops at the first match); `root=<path|none>`; then `## ls -l source`, `## ls -l copy`, `## sha256 source`, `## sha256 copy` blocks (12 files each: per run `ckpt_0001600.pt`, `junior_policy.json`); `copy_equals_source=<true|false>` |
| `meta/tarball_sha256.txt` | `sha256sum` line of the uploaded CR-B2-1 tarball |
| `meta/cpu_test_smoke.log`, `meta/cpu_test_check.txt` | frozen 14-test CPU smoke and its 14/3 check (P4 format; gate) |
| `meta/cpu_test_p5.log` | P5 prep tests on the venue, last line `exit=<code>` (recorded, not gated) |
| `meta/torch_cuda.txt`, `meta/nvidia-smi.txt`, `meta/pip-freeze.txt` | as P4 |
| `meta/env_drift.txt` | `diff -u packets/P5/p4_pip_freeze_ref.txt meta/pip-freeze.txt` (empty = no drift). The reference is a byte copy of the P4 deposit's `meta/pip-freeze.txt` (`e63a57c5…`) |
| `meta/attempt_<AID>.txt`, `meta/harness_stop_<AID>.txt`, `meta/gpumem_<AID>.csv` | as P4 (`packets/P4/BUNDLE_CONTRACT.md` §3, §4) for every new attempt. `cfg=/content/junior/configs/b2_mtrain.yaml` or `b2_idx.yaml` |
| `meta/perm_<ID>.json` | `perm_check.py` output (§5 below) |
| `meta/driver_state.txt` | append-only, §4 below |
| `meta/session.txt` | `part`, `venue=xn4090`, `start_utc`, `end_utc`, `session_hours`, `prior_hours`, `total_hours`, `spend_cap_hours=6`, `spend_cap_hit`, `cells_remaining`, `p4_root_candidates`, `stage_dir` |
| `meta/ckpt_dirs_ls.txt` | `ls -lR` of `logs/b2mt_* logs/b2idx_* logs/attempts/b2*` in `<U>`, then of `/content/p5_p4ckpts` |
| `meta/driver.log` | the driver's stdout |
| `logs/train_<AID>.log` | trainer stdout+stderr (`p5_train_entry.py`), every new attempt |
| `logs/attempts/<AID>/` | run directory copy without `*.pt` (`tb/events.out.tfevents.*`, `junior_policy.json`, `config.json`); `logs/attempts/<RUN>_a<N-1>.live/` when attempt N ≥ 2 started |
| `logs/eval/<ID>/it<IT>/exec<K>/` | `eval.log` (last line `exit=<code>`), condition JSONs, mask-stream files (§6 below) |
| `logs/perm/perm_<ID>.log` | `perm_check.py` stdout+stderr, last line `exit=<code>` |
| `deviations.md`, `BLOCKED.md` | as P4; codes add `p4_ckpts_unavailable`. `plan_gap` is also used for a non-RTX-4090 GPU and for an existing clone not at the pin |
| `job.json`, `runner_stdout.log` | XN-4090 job runner (via `B2_EXTRA_FILES`), if supplied |

`<ID>` = `b2u_<P4 AID>` (U checkpoints, e.g. `b2u_b0_attention_s0_a1`) or the new attempt ID `<tag>_<arm>_s<seed>_a<N>` with `<tag>` ∈ {`b2mt`, `b2idx`}, `<arm>` ∈ {`attention`, `mlp_mind`}. `<RUN>` = `<tag>_<arm>_s<seed>`. `<IT>` ∈ {`0000400`, `0000800`, `0001200`, `0001600`}.

## 4. `meta/driver_state.txt` records

```
PART <n> <start_utc>
UEVAL <P4 AID> <ok|fail> exec<K|none>        # one per U checkpoint (PLAN §4.1 step 2)
PERM <ID> <exit code of perm_check.py>       # U checkpoints (step 3) and every completed new attempt (steps 4-5)
ATTEMPT <AID> <driver_class> <driver_diverged> <completed>
SPENT <total_hours_after_this_item>
SPEND_CAP_HIT <total_hours>
```

Schedule (`b2_driver_helper.py next`): the six `UEVAL` in PLAN §4.1 step 2 order (attention s0, mlp_matched s0, attention s1, …); then `UPERM` on the same six (attention = gate, mlp_matched = report); then the cells `b2mt_attention_s0`, `b2mt_mlp_mind_s0`, `…_s1`, `…_s2`, `b2idx_attention_s0`, `_s1`, `_s2`. A cell is finished when its last attempt is `completed`, `DIV`, `OOM` or `SEAM`, or 2 INFRA attempts have run (B0 PLAN §3.3, frozen `cell_status`). There is no retry pair. The spend cap (6 h, all parts) is checked before every new work item (U eval, U PERM, new cell); a started cell (its retries included) is finished.

Per completed new attempt: evals at it 400 / 800 / 1200 (mask 0 only), then it 1600 (7 conditions), then PERM (`role=gate` for a non-diverged `b2mt` attention attempt, else `report`).

## 5. `meta/perm_<ID>.json`

Keys: `id`, `role` (`gate`|`report`), `mode` (`upstream`), `arm`, `ckpt`, `rel_err_tf32off`, `rel_err_default`, `rel_err_masked`, `pass` (`rel_err_tf32off < 1e-4`), `threshold` (1e-4), `tf32off` / `default` / `masked` (each `{perm_max_abs_err, action_mean_abs, rel_err, per_trial_max_abs_err}`), `tf32_default_flags`, `auto_mask_frac_loaded`, `auto_mask_frac_used` (0.0), `latent_dim`, `history`, `num_joints`, `n` (32), `trials` (8), `mask_frac` (0.2), `mask_seed` (7100), `device`, `torch`, `decoder_class`, `has_morphology`, `id_mode`, `sidecar_train_mask_frac`, `sidecar_descriptor_sha256`, `rebuilt_descriptor_sha256`. The verdict tool decides gate membership from the ID, not from `role`.

## 6. Eval execution content (PLAN §4.3, §2.3 (c))

`eval.log` holds the `[p5_eval] argv …` line, one frozen `[eval_entry] eval_benchmark.py --ckpt <path> … --out <exec dir>/<RUN>_<arm>_mask<f>.json` line per condition, `[p5_eval] condition i/n …`, `[p5_eval] maskstream …`, `[p5_eval] saved …` lines, and a final `exit=<code>`.

| Checkpoint | Condition files (`<cond>` = `mask<f>_ms<seed>`) |
|---|---|
| it 1600 | `<cond>` ∈ {`mask0.00_ms0`, `mask0.10_ms7100`, `mask0.20_ms7100`, `mask0.10_ms7101`, `mask0.20_ms7101`, `mask0.10_ms7102`, `mask0.20_ms7102`} (this run order) |
| it 400 / 800 / 1200 | `mask0.00_ms0` |

Per condition: `<RUN>_<arm>_mask<f>_ms<seed>.json` (frozen benchmark JSON, renamed only), `maskstream_<cond>.npz`, `maskstream_<cond>.json`.

- `maskstream_<cond>.npz`: `numpy.savez` (uncompressed zip) with `packed` = `numpy.packbits(stream, axis=-1)` of the bool stream of shape (calls, rows, 29), i.e. uint8 shape (calls, rows, 4), C order, numpy's default bit order (big); plus scalars `seed`, `frac`. A condition with no draws (mask 0.00) has `packed` of shape (0, 0, 0).
- `maskstream_<cond>.json`: `seed`, `frac`, `k` (0 for mask 0.00), `calls`, `rows_per_call`, `num_joints`, `true_per_row` (sorted set of per-row True counts), `fracs_seen`, `devices`, `packed_shape`, `sha256` (of the packed bytes).
- `calls` counts the decoder's mask draws, one per benchmark loop step; MS (PLAN §7.1) compares it with the maximum clip `steps` of the condition's JSON.
