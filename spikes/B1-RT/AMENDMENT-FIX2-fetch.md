# AMENDMENT-FIX2-fetch — LAFAN1 clip-fetch fix for `p6-b1-rt` attempt 2 (Provisional)

**Stamp:** 2026-10-26 EDT (Orchestrator, claude-opus-5-5). **Method:** pin v1.1 `9bdc872e…afc0` + `method/local/` (OVERLAY-001). No new overlay.
**Authority:** Manager decision `orch/owner-decisions/20261027-0752-AsiaShanghai-p6-lafan1-fetch-fix.md`, sha256 `768d6a0a0e62a7f193e29620316dfdf90bfadba2614bbd047e398925fa036f22` (Fix path #2).
**Prior score (not re-scored):** `p6-b1-rt` attempt 1/2 SCORED BLOCKED (INFRA download), job `eb7db827…`, results `c3a55e25…`, deposit `36cc77dc…`.

## Disclosure: attempt 2 is NOT byte-identical to attempt 1

PLAN §4 says attempt 2 runs with byte-identical inputs. This attempt does not. The upload tarball changes from `3cbb7726…` to `85d2cc87…`. Both `run.sh` and the job JSON also change. The decision `768d6a0a…` authorizes these changes. The full set of changes:

| Input | Attempt 1 | Attempt 2 |
|---|---|---|
| `spikes/B1-RT/rt_cpu.py` | `e228f724…` | `907022c2…` (`fetch_clip`: local dir → `huggingface_hub` → urllib; pin check) |
| `packets/P6/MANIFEST-b1rt.sha256` | `76d375c0…` | `91795dcf…` (only the rt_cpu.py line differs) |
| `packets/P6/junior_b_colab-P6-B1RT.tgz` | `3cbb7726…` (kept at `packets/P6/attempt1/`) | `85d2cc87…` |
| `orch/jobs/p6-b1-rt/run.sh` | `3763a3a7…` | see seal.log `P6-FIX2-RUNSH` (adds `LAFAN1_G1_DIR`, CSV preflight, new tarball sha) |

The following are unchanged: PLAN `b7365b4f…`, `AMENDMENT-C2-rt4.json` `32143be4…` (RT-4 waived, slot_rule=first), `verdict_rt.py` `2341a93d…`, `b1rt_driver.sh` `90bad7a3…`, `prepare_b1_data.py` `16855c68…`, `results-cpu-attempt1.json` `197b6c65…`, dataset rev `ce157290…`, the upstream pin and patch, the thresholds and the attempt cap. This is still attempt 2 of 2.

## Class

The change affects only the fetch mechanism, which is Class 0 under §10.4 and §10.5. The clip bytes must equal the box pins whatever the source, so no scoring input changes:

| clip | sha256 |
|---|---|
| walk1_subject1 | 68c7887438e94f1f3d9ebacd3a8ce59251a22c7b05129a0f5d7cacaedc48c28d |
| run1_subject2 | ec02af4447a62214a6fec6afff60c75d0ecc8f80f8fb45e3cd4119fed9ceac8d |
| dance1_subject1 | e2a369e92e5ad076c5acffff7bce53157a0e6cd9e7e9f6a08dadfb1eb2928d8f |
| jumps1_subject1 | 3f55c1a0f87564044a71817d62dc2a40aa76332aa1cab3f1c817333a197c78c2 |

Running attempt 2 on non-identical inputs departs from the literal PLAN §4. That departure rests on decision `768d6a0a…` and is disclosed here. The decision cap stays Provisional.

## X-002

Motion stays in process memory only. `fetch_clip` reads local CSVs read-only, and the `hf_hub_download` fallback writes to a temporary directory that is deleted on exit. The tarball contains no `.csv` (checked: 0 of 63 entries). The driver bundle already excludes `*.csv`, `*.npz` and `*.pt`. The P4 tree `/content/SuperMimic-Reproduced` is read-only and is never cleaned.

## Box smoke (not an RT attempt)

`logs/p6/b1rt-fix2-fetch-smoke-attempt1.log`: `prepare_b1_data.py --slot-rule first` with `LAFAN1_G1_DIR` pointing at a read-only box seed copy and an unreachable `HF_ENDPOINT`. Result: 4/4 clips came from local with sha256 equal to the pins, and the run printed `B1DATA pass=True csv_sha_mismatch=[]`. A corrupted copy raised `ValueError`. With no local copy, both `hf_hub` and urllib were tried and a `RuntimeError` was raised. Outputs went to /tmp and were deleted.

## What would show this did not fix it

On attempt 2, any of these means the fix failed: `data_step.log` has no `FETCH_CLIP … src=local:` lines, the job still BLOCKs at `data_step`, or any `csv_sha_mismatch` is non-empty.
