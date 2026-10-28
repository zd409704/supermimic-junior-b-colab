# P6b B1-RT (`p6-b1-rt`) attempt 1 — machine verdict

**Stamp:** 2026-10-26 EDT (UTC in `logs/seal.log`)
**Decision cap:** Provisional
**Venue:** xn-4090-gpu2 (GPU0, CUDA_VISIBLE_DEVICES=0), relay-launched driver (OVERLAY-001 rules 2–6)
**Tool:** `spikes/B1-RT/verdict_rt.py` (VERDICT-TOOL-B1RT) sha256 `2341a93d4acb857dae3933d38e5dedb49e03841533abdd9cb71482909616443a`, sealed 2026-10-26T23:30:16Z before any GPU deposit. Byte-identical at scoring.
**PLAN:** `spikes/B1-RT/PLAN.md` sha256 `b7365b4f2e382344151c64be979e5e2aff102fbaba6dc6826d8a429b3b9852a5` (unchanged)
**Amendment:** `spikes/B1-RT/AMENDMENT-C2-rt4.json` sha256 `32143be4687ca6de270165a848eaf4aa8292a21a40e8255c142c32f9f048c591` (Class-2 option C, decision `934b3c9b…`; waive=[RT-4], slot_rule=first)
**Method:** v1.1 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0` + `method/local/OVERLAY-001` (no new overlay; in-flight packet keeps its method hash)
**CPU input:** `spikes/B1-RT/results-cpu-attempt1.json` `197b6c6556551ee9994f54126767192175d3aa9a75c5011d6f573cfa4947eeab`
**Deposit:** `logs/xn4090/2026-10-26/b1rt-20261026-2350.tgz` sha256 `36cc77dc8710dbaa09abb05584e2ccd1a01b8d9f476f99067c18f870143a0893`
**Seal:** `DEPOSIT xn4090` @ `2026-10-26T23:50:59Z` (remote DONE_DRIVER `2026-10-26T23:50:09Z`). Seal line and tgz hash verified before opening. The .tgz was not rewritten.
**Open tree:** `logs/xn4090/2026-10-26/open-b1rt-20261026-2350/` (read-only; 16 regular files; listing showed relative paths only, no `..`, no links).

## Machine line

```
B1RT_VERDICT verdict=BLOCKED failing_ids=[] not_run=[RT-6,RT-7,RT-8] waived=[RT-4] rt5_recorded=True
```

Results JSON: `orch/reports/VERDICT-P6-b1-rt-attempt1-results.json` (copied byte-identical to `spikes/B1-RT/results.json` per PLAN §2 outputs; the prior CPU-only INCOMPLETE bytes `ff129d51…` are kept as `spikes/B1-RT/results-verdict-incomplete-c2-cpuonly.json`).

| Check | Result | Source |
|---|---|---|
| RT-1 | pass | CPU attempt 1 |
| RT-2 | pass | CPU attempt 1 |
| RT-3 | pass | CPU attempt 1 |
| RT-4 | fail, **waived** (Class-2 C) | CPU attempt 1 |
| RT-5 | recorded, finite | CPU attempt 1 |
| RT-6 | **not_run** | GPU: `meta/rt6.json` absent |
| RT-7 | **not_run** | GPU: `meta/rt7_{attention,mlp_matched}.json` absent |
| RT-8 | **not_run** | GPU: `meta/rt8_xferload.json`, `meta/rt8_eval_*.json` absent |

**Verdict: BLOCKED** (PLAN §2: a GPU check could not execute). Not PASS, not FAIL. No performance statement of any kind follows from this deposit.

## Deposit inventory (what the driver did)

| Step | Evidence | Outcome |
|---|---|---|
| Tarball identity | `meta/tarball_sha256.txt` | `3cbb7726…` = sealed P6B-TARBALL ✔ |
| Driver identity | `meta/driver_identity.txt` | `90bad7a3…` = sealed P6B-DRIVER ✔ |
| Amendment check | `meta/amendment_check.txt` | `32143be4…` slot_rule=first waive=RT-4 ✔ |
| Manifest | `meta/manifest_check.txt` | all entries OK (0 FAIL) ✔ |
| Upstream patch dry-run | `meta/patch_dryrun.txt` | applies (12 files) ✔ |
| Env | `meta/torch_cuda.txt`, `nvidia-smi.txt`, `pip-freeze.txt` | cuda True, torch 2.14.1+cu130, mujoco 3.16.0 |
| **Data step** | `logs/data_step.log`, `meta/driver.log` | `prepare_b1_data.py` → `rt_cpu.fetch_clip` → `urllib` HTTP 302 then **HTTP 403 Forbidden**; exit 1 |
| Stop | `BLOCKED.md`, `meta/steps.txt` | `BLOCKED_REASON=data_step`; spent_hours=0.0050; end 2026-10-26T23:50:09Z |
| Driver deviations | `deviations.md` | empty |

`BLOCKED.md` refers to `meta/b1_data_qa.json`, which is absent from the bundle. `prepare_b1_data.py` raised before it wrote the QA file. This is a pointer defect in the driver message, not missing evidence: the traceback is in `logs/data_step.log`. Recorded in `spikes/B1-RT/deviations.md`.

## Classification and budget (PLAN §4)

- Failure class: **INFRA (download)**. No RT check executed on GPU, so nothing is scored against the thresholds.
- GPU attempts used: 1 of 2. Spend: ≈0.005 of the 2.0 GPU-h per-attempt cap.
- Attempt 2 is allowed under PLAN §4 only with **byte-identical inputs** (tarball `3cbb7726…`, driver, verdict tool, amendment). Whether a venue-side fetch fix keeps those inputs byte-identical is for the Manager to decide. Examples of such fixes: a different `HF_ENDPOINT` in the job env, or a pre-staged mirror served at the same resolve path. PLAN §3 still requires each clip's CSV sha256 to equal the box values, whatever the source. A fix that changes `rt_cpu.py`, `prepare_b1_data.py` or the tarball is not byte-identical and needs a sealed amendment first.
- Orchestrator observation, a hypothesis that was not tested and is not part of the verdict: P4's successful mirror fetch used `huggingface_hub` (`DIAG-P4-motion-fetch-20261026.md`), whereas B1's `fetch_clip` uses bare `urllib` (default `Python-urllib` User-Agent) and follows the mirror's 302 to a target that answered 403.

## Consequences

- `orch/jobs/p6-b1-rt.json` → state **SCORED** (verdict BLOCKED).
- `p6-b1-arms` **stays DRAFT**. Its gate requires SCORED PASS with RT-6, RT-7 and RT-8 passing, and none of them ran.
- Class-2 option C (RT-4 waive, slot_rule first) stays in force unchanged. No new owner decision beyond C is needed to score. The next decision is the Manager's: the relay fix and whether to start attempt 2.
- P4 and P5 were not reopened. No GPU relaunch.

## Required disclosure (AMENDMENT-C2-rt4)

B1 references were produced by retarget route RT-a, which failed retarget QA (RT-4, waived under Class-2 option C); the sealed RT-4 skate measure is not attainable on the 29-DoF source itself. B1 results are within-plant arm comparisons on these shared references; absolute returns on the home humanoid are not comparable to the reference body's. (No B1 results exist yet; this deposit produced none.)
