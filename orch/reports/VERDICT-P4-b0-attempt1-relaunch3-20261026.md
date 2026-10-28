# P4 B0 attempt 1 (relaunch #3) — machine verdict

**Stamp:** 2026-10-26 06:22 EDT  
**Decision cap:** Provisional  
**Venue:** xn-4090-gpu2 (GPU0)  
**Tool:** `spikes/B0/verdict/verdict_b0.py` v1.0 sha256 `9caa744a65ef5206fd46f532c4d13529b7773d076ee725ee4cb98ec192774a3b`  
**PLAN:** `spikes/B0/PLAN.md` full (Amendment v1) sha256 `356c389f4c2efd47249f741b23f69bde19043a0ed8dc6e2c637abe397b9e145a`  
**Method:** `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0`  
**Tarball CR-B0-1:** `763867682e3cfa05ca8eb6382ffc9124be2347b898531c60b904061776c33bff`  
**Deposit:** `logs/xn4090/2026-10-26/b0-20261026-0919.tgz` sha256 `1f49118213d53538485303aa0b3f09bb5f068daeb06eb325045fd83a3118dde1`  
**Seal:** `DEPOSIT xn4090` @ `2026-10-26T10:22:04Z` (opened only after seal verified)  
**Run log:** `logs/xn4090/2026-10-26/run-20261026T065253Z.log` sha256 `255fd9446e4fd8d4b40c0633d4a8b853f4032697289e76e321f05bf2002b3e28`  
**HF fix:** `HF_ENDPOINT=https://hf-mirror.com` (DIAG `b818a714421f3a36ce32e77d8ad72ed8ac67fac2ab1338cf1e2475baff5ed5f7`)

## Machine line

```
B0_VERDICT verdict=PASS outcome=NONINFERIOR basis=margin delta=0.21324904291209681 delta_thr=0.1520180327677581 failing_ids=[] blocked=[]
```

| Field | Value |
|---|---|
| `verdict` | **PASS** |
| `b0_outcome` | **NONINFERIOR** |
| `outcome_basis` | margin |
| `superior` | true (primary R_H) |
| `noise_widened` | false (primary) |
| `decision_row` | 4 |
| `failing_ids` | [] |
| `blocked_reason` | [] |
| R̄_H attention | 0.2908716158904344 |
| R̄_H mlp_matched | 0.0776225729783376 |
| Δ / Δ_thr | 0.21325 / 0.15202 |
| SE_pooled | 0.07601 |
| shadow `r_step` outcome | NONINFERIOR (`noise_widened=true`; attention R̄_step 0.401 < mlp 0.466; `metric_disagreement=false` because both NONINFERIOR) |
| L-1 seeds passing | attention 3/3; mlp_matched 3/3 |
| Gates | V-0..V-4, L-1, L-2, DIV, REF-1..REF-4 all pass |
| F-1 | unsuitable → harness_stop (Amendment v1 confirmed) |
| PS-3 | Amendment v1 option (i) omit clip clause; M-6 null |

## Per-arm attempts (driver meta + harness class)

Exit code **130** on every arm is the **F-1 harness stop** (SIGINT after it-1600 checkpoint stable), not a crash. `diverged=false`, `completed=true`, evals done.

| AID | Arm | Seed | Class | Exit | Diverged | Scored | R_H (mask 0, ckpt 1600) |
|---|---|---|---|---|---|---|---|
| b0_attention_s0_a1 | attention | 0 | completed | 130 | false | yes | 0.41693 |
| b0_attention_s1_a1 | attention | 1 | completed | 130 | false | yes | 0.29937 |
| b0_attention_s2_a1 | attention | 2 | completed | 130 | false | yes | 0.15631 |
| b0_mlp_matched_s0_a1 | mlp_matched | 0 | completed | 130 | false | yes | 0.08560 |
| b0_mlp_matched_s1_a1 | mlp_matched | 1 | completed | 130 | false | yes | 0.05783 |
| b0_mlp_matched_s2_a1 | mlp_matched | 2 | completed | 130 | false | yes | 0.08943 |
| b0_mlp_upstream_s0_a1 | mlp_upstream | 0 | completed | 130 | false | REF only | (reference; does not change verdict) |

## Disclosure (required)

1. **Harness stop / exit=130.** All seven arms stopped via F-1 harness SIGINT after endpoint it 1600 (`max_hours` path in train log coincides with budget end). `harness_stop_timeout=false`; sidecar present.
2. **Primary vs shadow metric.** Primary cumulative R_H ranks attention above mlp_matched with superior NONINFERIOR. Shadow per-step R_step ranks mlp_matched higher on the mean but still NONINFERIOR with `noise_widened=true`. Same qualitative split as P2 RCA; primary metric is R_H per sealed PLAN.
3. **PS-3 (i).** Clip-fraction clause omitted by Amendment v1; stability-evidence confound disclosed.
4. **Provisional.** Outcome capped Provisional (PLAN depth disclosure).

## Artifacts

| Path | sha256 |
|---|---|
| `orch/reports/VERDICT-P4-b0-attempt1-relaunch3-results.json` | `76507d8a9488cd295add444d9e9463da1bf7ab62c2216733043c535f3c6f8d3d` |
| `orch/reports/VERDICT-P4-b0-attempt1-relaunch3.stdout` | `e0f812d7488b8dd32a4fdd4f3d062a90832eec3dcd96d426ef4f7a8c2770acfc` |
| `orch/reports/VERDICT-P4-b0-attempt1-relaunch3-20261026.md` | (this file; sealed below) |
| Deposit (sealed, opened for score) | `1f49118213d53538485303aa0b3f09bb5f068daeb06eb325045fd83a3118dde1` |

## Overall

**PASS / NONINFERIOR** (machine). Not FAIL. Not BLOCKED. Not INCONCLUSIVE.

No new GPU run. No Colab. Drive paused.
