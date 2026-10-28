# BUNDLE_CONTRACT — B1 arms deposit `b1arms-<UTC>.tgz` (spikes/B1/PLAN.md §8)

Producer: `packets/P6/b1arms_driver.sh`. Consumer: `spikes/B1/verdict_b1.py`. PLAN sha256 `1088752ba26a8798d721aa93d6e10d1b7bdb7fb924d9d72879acc78d8c2304c8`.
Archive root = the upstream tree `$U` (`/content/SuperMimic-Reproduced-b1`). Excluded: `*.pt`, `*.npz`, `*.csv` (PLAN §8, X-002) and the live run dirs `logs/b1H*_s<seed>` (their non-`.pt` content is in `logs/attempts/<AID>`).

Names: `RUN = b1<arm without hyphens>_<policy>_s<seed>` (for example `b1HAxfer_attention_s0`, `b1HAxfernoscale_attention_s0`). `AID = <RUN>_a<attempt>`, attempt 1 or 2.

| Path | Content |
|---|---|
| `meta/driver_state.txt` | `PART n …`, `DATA ok`, `ATTEMPT <AID> <CLASS> <completed> [session_loss]`, `DUR <RUN> <h>`, `RUNDONE <RUN> COMPLETED\|NOT_COMPLETED\|NONFINITE\|SPEND_CAP\|SRC_MISMATCH\|SKIPPED_NO_ROOM`, `SPENT <h> <utc>` |
| `meta/schedule.txt`, `meta/schedule_skips.txt` | the fixed §4 order; secondaries not started for lack of room under the cap |
| `meta/attempt_<AID>.txt` | arm, policy, init, seed, role, config, src key/path, start/end, exit code, `class=`, evals |
| `meta/harness_stop_<AID>.txt` | B0 §4.3 record + `spend_cap_stop=` |
| `meta/src_ckpt_<AID>.txt` | every candidate P4 checkpoint with sha256 and match flag; `used=` |
| `meta/tb_<AID>.json` | all TB scalars (b1_checks tbdump), used by the driver's classification only |
| `meta/b1_data_qa.json` | data step QA (B1-V-4) |
| `meta/gpu_used.csv.txt` | byte copy of `nvidia-smi -i $CUDA_VISIBLE_DEVICES --query-gpu=index,uuid,name --format=csv` (B1-V-5; the `.csv` original is excluded by §8) |
| `meta/gpu_env.txt`, `meta/gpu_used_attempts.txt` | `CUDA_VISIBLE_DEVICES` per part; the used-device line at each attempt start |
| `meta/gpumem_<AID>.txt`, `meta/nvidia-smi_part<n>.txt`, `meta/pip-freeze_part<n>.txt`, `meta/torch_cuda.txt` | host records (not gated) |
| `meta/tarball_sha256.txt`, `meta/driver_identity.txt`, `meta/manifest_check_part<n>.txt`, `meta/patch_*.txt` | identity checks per part |
| `meta/spend.txt` | spent hours, cap, cap_hit, end state |
| `logs/train_<AID>.log` | trainer stdout/stderr |
| `logs/attempts/<AID>/` | run dir without `*.pt`: `tb/events.*`, `junior_policy.json`, `config.json` |
| `logs/eval/<AID>/it<IT>/exec<k>/` | `eval.log` (ends `exit=<rc>`) and `<RUN>_ckpt_<IT>_mask0.00.json`; IT = 0000160 … 0001600; k = 2 only if exec1 failed |
| `logs/data_step.log`, `logs/tbdump_<AID>.log` | step logs |
| `deviations.md`, `BLOCKED.md` | driver deviations; `BLOCKED_REASON=<code> detail=…` (`spend_cap`, `src_ckpt_mismatch`, `setup_failed`, `tarball_sha_mismatch`, `plan_gap`, `data_step`, `R1_unresolved`) |
| `extras/` | `run.sh`, `runner_stdout.log`, job JSON |

A job launch 2 (`B1ARMS_RESUME=1`) keeps `$U`, so its bundle is a superset of launch 1. The verdict accepts both deposits; a later deposit wins a duplicate path.
