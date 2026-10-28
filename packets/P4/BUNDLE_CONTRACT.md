# P4 bundle contract: what `packets/P4/b0_driver.sh` writes, and what `spikes/B0/verdict/verdict_b0.py` reads

**Packet:** P4-prep. **PLAN:** `spikes/B0/PLAN.md` sha256 `ed6b6a54a860bbfc67d7c822b5394804b8d408f6aae57fbeb118d2ea63c52557`. **Status:** Provisional.
This file adds machine-readable detail to PLAN §4 and §8.1. Where it and the PLAN disagree, the PLAN wins. Every file name the PLAN lists keeps its PLAN name.

## 1. Archive

- One archive per session (Colab) or job (XN-4090): `b0-<YYYYMMDD>-<HHMM>[-partN].tgz` (UTC time of packing; `-partN` for N ≥ 2).
- Member paths are relative (`./meta/...`, `./logs/...`). No absolute paths, no `..`, no `*.pt`, no `*.npz`, no `*.csv` motion files.

## 2. Members (paths relative to the archive root)

| Path | Written by | Content |
|---|---|---|
| `meta/tarball_sha256.txt` | driver §4.1 step 2 | `sha256sum` output line for the uploaded CR-B0-1 tarball |
| `meta/cpu_test_smoke.log` | driver §4.1 step 3 | stdout+stderr of `code/tests/test_smoke.py` |
| `meta/cpu_test_check.txt` | driver | `pass_lines=<n> skip_before_pass=<n> expected=14/3 ok=<true|false>` |
| `meta/nvidia-smi.txt` | driver §4.1 step 4 | plain `nvidia-smi` output (header has the GPU name) |
| `meta/pip-freeze.txt` | driver §4.1 step 4 | `uv pip freeze --python $PY` |
| `meta/torch_cuda.txt` | driver | `cuda <True|False> <torch version>` (after the R1 fallback, if used) |
| `meta/ckpt_dirs_ls.txt` | driver §4.4 | `ls -lR logs/b0_* logs/b0lr05_* logs/attempts` |
| `meta/ckpt_map.txt` | driver §4.4 (only if needed) | `<AID> it<IT> <path>` lines |
| `meta/gpumem_<AID>.csv` | driver §4.2 | `nvidia-smi --query-gpu=timestamp,memory.used,memory.total --format=csv -l 5` |
| `meta/harness_stop_<AID>.txt` | driver §4.3 | `key=value` lines, §3 below. Written for every attempt whose trainer was started (`harness_stop=false` when no SIGINT was sent) |
| `meta/attempt_<AID>.txt` | driver | `key=value` lines, §4 below. The driver's own classification, used for scheduling only. The verdict tool recomputes the class from the evidence and reports any disagreement |
| `meta/driver_state.txt` | driver | append-only history carried across sessions, §5 below |
| `meta/session.txt` | driver | `key=value`: `part`, `venue`, `start_utc`, `end_utc`, `session_hours`, `prior_hours`, `total_hours`, `spend_cap_hours=7`, `spend_cap_hit=<true|false>`, `gate_set_complete=<true|false>`, `cells_remaining=<comma list>` |
| `meta/driver.log` | driver | the driver's own stdout |
| `train_up_sanity.log` | driver §4.1 V-0 | V-0 log (first session on a venue only; later parts record `V0` in `driver_state.txt`) |
| `logs/train_<AID>.log` | trainer | stdout+stderr of each attempt |
| `logs/attempts/<AID>/` | driver §3.3 | the run directory copied **without `*.pt`**: `tb/events.out.tfevents.*`, `junior_policy.json`, `config.json` |
| `logs/attempts/<AID>.live/` | driver §3.3 | the moved-aside live directory of attempt N−1 when attempt N ≥ 2 starts (`*.pt` removed at packing) |
| `logs/eval/<AID>/it<IT>/exec<K>/eval.log` | driver §4.4 | eval stdout+stderr, then a final `exit=<code>` line |
| `logs/eval/<AID>/it<IT>/exec<K>/<RUN>_<arm>_mask<f>.json` | eval_entry | `f` ∈ {0.00, 0.10, 0.20} |
| `deviations.md` | driver + runner | may be empty. Driver entries are lines starting `- [driver]` |
| `BLOCKED.md` | driver or runner | only if applicable. One machine line per reason: `BLOCKED_REASON=<code> detail=<text>`. Codes: `R1_unresolved`, `cpu_test_mismatch`, `tarball_sha_mismatch`, `setup_failed`, `spend_cap`, `plan_gap` |
| `job.json`, `runner_stdout.log` | XN-4090 job runner | XN-4090 only |

`<IT>` ∈ {`0000400`, `0000800`, `0001200`, `0001600`}. `<AID>` = `<tag>_<arm>_s<seed>_a<N>`, `<RUN>` = `<tag>_<arm>_s<seed>`.

## 3. `meta/harness_stop_<AID>.txt`

```
aid=<AID>
endpoint_line_seen=<true|false>
endpoint_line_utc=<ISO-8601 UTC or none>
ckpt_path=logs/<RUN>/ckpt_0001600.pt
ckpt_size_poll1=<bytes or none>
ckpt_size_poll2=<bytes or none>
poll_interval_s=30
ckpt_stable=<true|false>
harness_stop=<true|false>            # true iff SIGINT was sent by the driver
signal=<SIGINT|none>
sigint_sent_utc=<ISO or none>
trainer_exited_before_signal=<true|false>
exit_wait_s=<seconds waited after SIGINT, or 0>
harness_stop_timeout=<true|false>    # still alive 300 s after SIGINT
sigkill_sent=<true|false>            # only after harness_stop_timeout
exit_code=<bash $? of wait>          # 130 = terminated by SIGINT after Python ran finally (CPython re-raises SIGINT); 137 = SIGKILL
sidecar=<present|missing>            # logs/<RUN>/junior_policy.json after exit
```

## 4. `meta/attempt_<AID>.txt`

```
aid=<AID>  tag=<b0|b0lr05>  arm=<attention|mlp_matched|mlp_upstream>  seed=<int>  attempt=<N>
cfg=/content/junior/configs/<file>.yaml
start_utc=<ISO>  end_utc=<ISO>
exit_code=<int>
completed=<true|false>               # PLAN §4.3 completion condition
driver_class=<completed|DIV|OOM|SEAM|INFRA>
driver_diverged=<true|false>         # PLAN §6.3 (a); can be true for a completed attempt
infra_cause=<none|safety_cap|harness_stop_timeout|sidecar_missing|ckpt_unstable|other_traceback|no_endpoint>
final_exception_line=<text or none>  # last pre-endpoint traceback's final line
evals=<done|skipped>
```
(One `key=value` per line in the file; shown grouped here.)

## 5. `meta/driver_state.txt`

Append-only. One record per line, space-separated:

```
PART <n> <start_utc>
V0 <pass|fail> <venue> <gpu_name>
ATTEMPT <AID> <driver_class> <driver_diverged> <completed>
SPENT <total_hours_after_this_cell>
SPEND_CAP_HIT <total_hours>
```

The driver derives its schedule (next cell, attempt numbers, divergence retry pairs) only from these records. To continue in a new session, the runner uploads the previous `meta/driver_state.txt` and starts the driver with `B0_STATE_IN=<path>`. The runner chooses nothing.

## 6. Schedule the driver implements (PLAN §3.2, §3.3, §6.3)

1. V-0 env sanity (once per venue).
2. For s in 0, 1, 2: cell `b0_attention_s<s>`, then `b0_mlp_matched_s<s>`. If either cell's counted attempt is divergent (DIV class, or completed with `driver_diverged=true`), the retry pair `b0lr05_attention_s<s>`, `b0lr05_mlp_matched_s<s>` runs immediately after (at most once per seed index; F-2 exists).
3. `b0_mlp_upstream_s0` (reference; never triggers a retry pair).
4. Per cell: attempts until one is completed, DIV, OOM or SEAM, or 2 INFRA attempts have run.
5. All scheduled cells run, whatever the outcomes. The spend cap (7 GPU wall-hours, all sessions) is checked between cells. When reached, the driver stops after the current cell, writes `SPEND_CAP_HIT`, and packs.
