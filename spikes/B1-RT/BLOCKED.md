# B1-RT BLOCKED — RT-4 (retarget QA) failed; RT-b trigger per PLAN §3 / AS-4

**Stamp:** 2026-10-26 ~19:45 EDT (UTC in `logs/seal.log`). **PLAN:** `spikes/B1-RT/PLAN.md` sha256 `b7365b4f2e382344151c64be979e5e2aff102fbaba6dc6826d8a429b3b9852a5`.
**Machine line:** `B1RT_VERDICT verdict=FAIL failing_ids=[RT-4] not_run=[RT-6,RT-7,RT-8] waived=[] rt5_recorded=True` (`results.json`, tool `verdict_rt.py` 2341a93d…).

## What failed
CPU attempt 1 (`results-cpu-attempt1.json`, 197b6c65…): RT-1, RT-2, RT-3 pass; RT-5 recorded (reference-PD replay falls after 1.0–4.8 s on every clip, finite). **RT-4: 0 of 4 slots pass** (both the first clip and the replacement of every slot fail):

| Clip | clip frac (≤0.10) | penetration p95 m (≤0.01) | skate p95 m/s (≤0.10) | root-height band |
|---|---|---|---|---|
| walk1_subject1 | 0.197 | 0.0173 | 1.316 | ok |
| walk1_subject2 | 0.086 | 0.0138 | 1.664 | ok |
| run1_subject2 | 0.439 | 0.0188 | 1.300 | ok |
| run1_subject5 | 0.588 | 0.0191 | 1.912 | ok |
| dance1_subject1 | 0.281 | 0.0202 | 1.142 | ok |
| dance1_subject2 | 0.455 | 0.0172 | 0.685 | ok |
| jumps1_subject1 | 0.206 | 0.0150 | 1.297 | ok |
| jumps1_subject2 | 0.285 | 0.0302 | 1.240 | p5 0.23 (fail) |

## Diagnostic (not an RT attempt): the same metrics on the source body
`diag-source-baseline-attempt1.json` (8f511559…): measured with the identical definitions on the 29-DoF reference body's own motion, **skate p95 = 0.88–2.74 m/s on all 8 clips** and penetration p95 = 0.0071–0.0108 m. The sealed skate operationalisation (planar speed of the stance ankle-roll link, stance = lower sole < 0.02 m) cannot be met by the source motion itself, so RT-4 as sealed cannot tell a good retarget from a bad one. Penetration on the home humanoid is about 2× the source's, and elbow clipping (the reference elbow flexes past the home range after the −φ offset) drives most clip-fraction failures.

## Consequence (pre-registered)
- No GPU spend on B1 arms. The RT GPU job `p6-b1-rt` stays **DRAFT** (its data step would select 0 slots and stop).
- RT-b is not implemented in P6. A Class-2 decision is required: `orch/reports/ASK-P6-RT4-class2-20261026.md`.
