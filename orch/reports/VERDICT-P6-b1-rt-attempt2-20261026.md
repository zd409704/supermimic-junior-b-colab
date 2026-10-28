# P6b B1-RT (`p6-b1-rt`) attempt 2/2 (Fix#2) — machine verdict

**Stamp:** 2026-10-26 21:22 EDT (UTC in `logs/seal.log`)
**Decision cap:** Provisional
**Venue:** xn-4090-gpu2 (GPU0, CUDA_VISIBLE_DEVICES=0), relay-launched driver (OVERLAY-001 rules 2–6)
**Tool:** `spikes/B1-RT/verdict_rt.py` sha256 `2341a93d4acb857dae3933d38e5dedb49e03841533abdd9cb71482909616443a`. Sealed 2026-10-26T23:30:16Z. Byte-identical at scoring.
**PLAN:** `spikes/B1-RT/PLAN.md` `b7365b4f2e382344151c64be979e5e2aff102fbaba6dc6826d8a429b3b9852a5` (unchanged)
**Amendment (scoring):** `spikes/B1-RT/AMENDMENT-C2-rt4.json` `32143be4687ca6de270165a848eaf4aa8292a21a40e8255c142c32f9f048c591` (Class-2 option C, decision `934b3c9b…`; waive=[RT-4], slot_rule=first)
**Fix#2 (context, not a scoring input):** `spikes/B1-RT/AMENDMENT-FIX2-fetch.md` `4ebe829b…`, decision `768d6a0a…`. Upload tarball `85d2cc87…`. Not byte-identical to attempt 1. Disclosed.
**Method:** v1.1 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0` + `method/local/OVERLAY-001`. No new overlay: this is an in-flight packet.
**CPU input:** `spikes/B1-RT/results-cpu-attempt1.json` `197b6c6556551ee9994f54126767192175d3aa9a75c5011d6f573cfa4947eeab`
**Deposit:** `logs/xn4090/2026-10-27/b1rt-20261027-0113.tgz` sha256 `4e49c3e9efd788e6a457e7df251143cc7c6d0c688179c0c38aa667c5e5d4d8e8`
**Seal:** `DEPOSIT xn4090` @ `2026-10-27T01:18:28Z` (remote DONE_DRIVER `2026-10-27T01:13:49Z` state=DONE). The seal line and the tgz hash were verified before opening, and the .tgz was not rewritten.
**Open tree:** `logs/xn4090/2026-10-27/open-b1rt-20261027-0113/`. Read-only; 43 regular files, 0 links. The listing had relative paths only and no `..`.

## Machine line

```
B1RT_VERDICT verdict=PASS failing_ids=[] not_run=[] waived=[RT-4] rt5_recorded=True
```

Results JSON: `orch/reports/VERDICT-P6-b1-rt-attempt2-results.json` `126c2334…`. It is copied byte-identical to `spikes/B1-RT/results.json`. The prior BLOCKED bytes `c3a55e25…` are kept as `spikes/B1-RT/results-verdict-blocked-gpu-attempt1.json`.

| Check | Result | Source / key evidence |
|---|---|---|
| RT-1 | pass | CPU attempt 1 |
| RT-2 | pass | CPU attempt 1 |
| RT-3 | pass | CPU attempt 1 |
| RT-4 | fail, **waived** (Class-2 C) | CPU attempt 1 |
| RT-5 | recorded, finite | CPU attempt 1 |
| RT-6 | **pass** | parity max\|Δz\| 7.95e-8 m (tol 0.01), 4 worlds, finite; seams S1/S2/S5 true (obs 720) |
| RT-7 | **pass** | attention: it 3200, WM loss 12.21→0.090, C 17.2→57.4. mlp_matched: it 3250, WM 12.17→0.061, C 16.9→61.4. Both: no traceback, finite tb, ckpt + sidecar, seams true |
| RT-8 | **pass** | (a) eval masks 0.0/0.1/0.2 × 2 arms, 4 clips each, all finite. (b) xferload: attention full copy (41 params) and mlp row map (20/22 joints, head fresh) give finite (8,22); ckpt sha `5fb48347…`/`9ae05d74…` match |

**Verdict: PASS** (PLAN §2), with RT-4 waived under AMENDMENT-C2-rt4.

## Deposit integrity

| Step | Evidence | Outcome |
|---|---|---|
| Tarball identity | `meta/tarball_sha256.txt` | `85d2cc87…` = sealed P6-FIX2-TGZ ✔ |
| Driver identity | `meta/driver_identity.txt` | `90bad7a3…` = sealed driver ✔ |
| Amendment check | `meta/amendment_check.txt` | `32143be4…` slot_rule=first waive=RT-4 ✔ |
| Manifest | `meta/manifest_check.txt` | 0 FAIL ✔ |
| P4 ckpts | `meta/p4_ckpt_identity.txt` | root `/content/p5_p4ckpts`; both sha match ✔ |
| Data step | `logs/data_step.log`, `meta/b1_data_qa.json` | 4/4 `FETCH_CLIP … src=local:` with sha = pin; `B1DATA pass=True csv_sha_mismatch=[]` ✔ (none of the Fix#2 failure signs appeared) |
| Steps | `meta/steps.txt` | all exit 0; spent_hours=1.2258 (cap 2.0) |
| Driver deviations | `deviations.md` | empty |

## Observation (not part of the verdict)

The RT-8(a) eval summaries report `failed: 1` of 4 clips at every mask for both arms. Mean norm_return is ≈0.52 at mask 0, falling to 0.47 (attention) and 0.52 (mlp) at mask 0.2. RT-8(a) requires only finite `norm_return`, so this does not affect the verdict. It matters for interpreting the B1 arms. It is not a performance claim: these are 0.5 h smoke trainings, one seed.

## Consequences

- `orch/jobs/p6-b1-rt.json` → state **SCORED** (verdict PASS, attempt 2/2). No GPU attempts remain for this job.
- `p6-b1-arms`: **gate (1) is met** (SCORED PASS, waived=[RT-4]). The job **stays DRAFT**, bytes unchanged (`9f71dd1e…`). Its sealed `state_note` also requires every `ready_prereqs` item to be done and sealed first, and items 2–4 do not exist: `packets/P6/b1arms_driver.sh`, `spikes/B1/verdict_b1.py`, the arms tarball and manifest, and `orch/jobs/p6-b1-arms/run.sh`. Upload shas are still "TBD". Flipping to READY would hand the relay a job with no payload. See `orch/reports/ASK-P6-ARMS-prereqs-20261026.md`. The authority to READY without a new Manager START (934b3c9b item 4, 1855 item 2) is unaffected.
- P4/P5 were not reopened. No SSH and no GPU START from the Orchestrator.

## Required disclosure (AMENDMENT-C2-rt4)

B1 references were produced by retarget route RT-a, which failed retarget QA (RT-4, waived under Class-2 option C). The sealed RT-4 skate measure is not attainable on the 29-DoF source itself. B1 results are within-plant arm comparisons on these shared references. Absolute returns on the home humanoid are not comparable to the reference body's. RT-4 numbers: 0/4 slots pass. Used clips (clip frac / penetration p95 m / skate p95 m/s): walk1_subject1 0.197/0.0173/1.316, run1_subject2 0.439/0.0188/1.300, dance1_subject1 0.281/0.0202/1.142, jumps1_subject1 0.206/0.0150/1.297. Source baseline: skate p95 0.88–2.74 m/s; penetration p95 0.0071–0.0108 m.

Attempt 2 ran on inputs that were not byte-identical to attempt 1 (Fix#2 fetch path; `AMENDMENT-FIX2-fetch.md`, decision `768d6a0a…`). This departs from the literal PLAN §4 attempt-2 rule. The decision cap stays Provisional.
