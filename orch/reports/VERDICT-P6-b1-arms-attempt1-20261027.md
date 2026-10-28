# P6d B1 arms (`p6-b1-arms`) attempt 1/2 — machine verdict

**Stamp:** 2026-10-27 05:40 EDT (UTC in `logs/seal.log`)
**Decision cap:** Provisional, single-candidate (A1.1-6). Depth 2 (A1.1-1): nothing may be built on this without a further signature.
**Venue:** xn-4090-gpu2 (GPU0, CUDA_VISIBLE_DEVICES=0, `NVIDIA GeForce RTX 4090`, uuid `GPU-fb0522c7…`). Relay-launched driver (OVERLAY-001 rules 2–6, with the relay in place of the owner).
**Tool:** `spikes/B1/verdict_b1.py` sha256 `62c3ae20151345950e44541569c45599860bf5c996c4b98f0243eada0f3b6ed6` v1.0. Sealed before the deposit was opened; byte-identical at scoring. B0 helpers `9caa744a…`.
**PLAN:** `spikes/B1/PLAN.md` `1088752ba26a8798d721aa93d6e10d1b7bdb7fb924d9d72879acc78d8c2304c8` (unchanged).
**Method:** v1.1 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0` + `method/local/OVERLAY-001`. This is an in-flight packet, so no new overlay was added.
**Gate:** `p6-b1-rt` SCORED PASS a2, waived=[RT-4], results `126c23349ef6770ce7a8c5e3d9d7b60c66dceb7803ae27824f8d2651cc07be2d`.
**Deposit:** `logs/xn4090/2026-10-27/b1arms-20261027-0935.tgz` sha256 `f95155af47357026d69f7c06f01c3d20ca806aa3378fce125322001d1094126d` (743903 B).
**Seal:** `DEPOSIT xn4090` at `2026-10-27T09:38:14Z` (seal.log line 367; DONE_DRIVER `2026-10-27T09:35:50Z`, state=DONE). The seal line and the tgz hash were verified before the archive was opened, and the tgz was not rewritten.
**Open tree:** `logs/xn4090/2026-10-27/open-b1arms-20261027-0935/`, read-only (a-w). It holds 435 regular files, 327 dirs and 0 links. Member paths are all relative, none contains `..`, and there are no `.pt`/`.npz`/`.csv` files. The verdict tool extracted the tgz separately into its own tempdir (`member_problems=[]`).

## Machine line

```
B1_VERDICT verdict=PASS outcome=INCONCLUSIVE failing=[] aulc_HA_xfer=0.5361342107547861 aulc_HA_scratch=0.5023742432955027 aulc_HM_xfer=0.519483948911739 se=0.014513165235814461 partial_outcome=null plan=1088752b tool=62c3ae20
```

| Artifact | Path | sha256 |
|---|---|---|
| Results JSON | `orch/reports/VERDICT-P6-b1-arms-attempt1-results.json` (= `spikes/B1/results.json`, byte-identical) | `64644e3c594de07a6819b685b1d0f956849eaafbff56b3ad87eab0cbb70c1403` |
| Stdout | `orch/reports/VERDICT-P6-b1-arms-attempt1.stdout` | `ddcd77ed4803858f65374c9af2a565180476969348dce438bf622bfb67806a92` |
| runs.log (tool block) | `spikes/B1/runs.log` (copy `orch/reports/VERDICT-P6-b1-arms-attempt1.runs.log`) | `99b157a7…` at tool write |

Command (exit 0, empty stderr):
`python3 -I spikes/B1/verdict_b1.py --deposit logs/xn4090/2026-10-27/b1arms-20261027-0935.tgz --tarball-sha 0f18b8bbca7f7ef13fffb0bcf51b2370e997580a5b5f8f6ed2cffc4dd1eb8d87 --seal-log logs/seal.log` (default `--out` / `--runs-log`, per PLAN §8).

## Validity (PLAN §6), all pass

| ID | Result | Key evidence |
|---|---|---|
| Deposit check | pass | tarball sha recorded `0f18b8bb…` = expected; driver `10bfc76b…`; no BLOCKED.md; spend 7.5047 h / 9.0 cap, cap_hit=false |
| B1-V-1 | pass | 9/9 primary runs completed on attempt 1: ckpt_0001600 stable, it-1600 line, sidecar, seams true, 10/10 eval JSONs finite |
| B1-V-2 | pass | all 9 primary runs stopped at it 1600; `time/updates`=624 for every run |
| B1-V-3 | pass | the source ckpt sha for every xfer/frozen run matches §4; attention: full decoder load; mlp: 20 rows mapped, head yaw/pitch fresh |
| B1-V-4 | pass | data QA pass; used_clips walk1_subject1, run1_subject2, dance1_subject1, jumps1_subject1; csv_sha_mismatch=[]; slot_rule=first; rev `ce157290…` |
| B1-V-5 | pass | used device `0, GPU-fb0522c7-d42b-41f1-f24b-4729e2c2174c, NVIDIA GeForce RTX 4090` |

## Arms (AULC over the 10 %–100 % budget; R at mask 0.0)

| Arm | Role | n | AULC per seed (s0, s1, s2) | mean AULC | sd | R25 mean | R100 mean |
|---|---|---|---|---|---|---|---|
| **H-A-xfer** | primary, under test | 3 | 0.5488, 0.5463, 0.5133 | **0.5361** | 0.0198 | 0.5238 | 0.5209 |
| **H-A-scratch** | primary | 3 | 0.5138, 0.4746, 0.5187 | **0.5024** | 0.0241 | 0.4441 | 0.5138 |
| **H-M-xfer** | primary | 3 | 0.5076, 0.5138, 0.5370 | **0.5195** | 0.0155 | 0.5215 | 0.5191 |
| H-M-scratch | secondary | 3 | 0.5161, 0.4918, 0.5244 | 0.5108 | 0.0170 | 0.5188 | 0.5252 |
| H-A-frozen | diagnostic | 1 | 0.5701 | 0.5701 | — | 0.6342 | 0.5178 |
| H-A-xfer-noscale | ablation | 1 | 0.5123 | 0.5123 | — | 0.4768 | 0.5266 |

## Outcome logic (PLAN §5)

- KILL test: xfer ≤ scratch? 0.5361 ≤ 0.5024, **no**. xfer < H-M-xfer − 2·SE? 0.5361 < 0.5195 − 0.0290, **no**. → not KILL.
- The 1.2× test: xfer / scratch = **1.067** (needs ≥ 1.2, i.e. xfer ≥ 0.6028). **Fails**, so neither SIGNAL nor SIGNAL_STRONG.
- xfer − H-M-xfer = +0.0167, against 2·SE = 0.0290 (SE = 0.01451, ddof=1).
- → **INCONCLUSIVE**. PLAN §5 says: "No seeds are added without a sealed amendment."

The Orchestrator recomputed these figures from the per-seed AULCs in results.json with independent arithmetic. They match the tool to full precision. This was a check only; the machine line governs.

## Observations (not part of the verdict; prose never overrides it)

1. **The return metric is nearly flat across training.** In every arm, R_k sits around 0.50–0.53 from it 160 to it 1600. Arm differences in AULC come mostly from scattered high-R points, not from distinct learning curves.
2. **Clip-failure pattern.** Every eval JSON (140/140 at mask 0.0) reports `summary.failed` ≥ 1 of 4 clips. RT-8(a) showed the same `failed: 1` pattern. 20/140 report `failed: 4`, and those evals tend to show *higher* `mean_norm_return` (e.g. 0.60–0.67) than the `failed: 1` evals (≈0.50–0.52). Of the 20 all-failed evals, 8 fall in H-A-xfer, 4 in H-A-scratch, 4 in H-A-frozen, 2 in H-M-scratch and 2 in H-M-xfer. R_k as frozen by PLAN §5 is therefore partly driven by early-termination behaviour, not by tracking quality alone. This does not change the verdict or the outcome. It weakens any reading of the +0.034 xfer–scratch AULC gap as a learning-speed effect, and any follow-up packet should review it as a measurement-validity question before adding seeds or arms.
3. H-A-frozen has the highest diagnostic AULC (0.570, n=1). Its first four eval points all have `failed: 4`, so observation 2 applies directly.

## Mandatory disclosures (PLAN §0)

1. **P5 caveat (A1.1-4).** "The B0+B2 gate to B1 is **Go** because B0 was non-inferior. B2 returned **NO_GAIN** with **u_deficit = true**: Δρ_U(0.2) = −0.557 (the attention decoder retained *less* return than mlp_matched under untrained 20 % token masking). B1 therefore does not inherit any robustness advantage claim for the attention decoder."
2. **RT-4 waived (Class-2 option C).** References from route RT-a fail retarget QA (RT-4, 0/4 slots). RT-4 is waived; RT-6..RT-8 stay binding.
3. **Claim scope (A1.1-8 + C).** "Decoder-weight transfer between two rigid humanoids, with per-body motion encoder, world model and critic; references produced by route RT-a, which failed retarget QA (RT-4, waived under Class-2 option C; the sealed RT-4 skate measure is not attainable on the 29-DoF source itself)." The results are within-plant arm comparisons on shared references. Whole-policy zero-shot transfer is out of scope.
4. PLAN §9: the `codex-astra` cross-family red team on PLAN/driver was **not run** (disclosed at seal).

## Deposit integrity (driver-reported)

- `deviations.md` lists only the 14 harness stops (B0 PLAN §4.3, SIGINT, exit 130), one per run. These are the expected endpoint mechanism, not deviations from PLAN.
- All 14 runs used attempt 1. No INFRA retries.

## Consequences

- `orch/jobs/p6-b1-arms.json` → **SCORED** (verdict PASS, outcome INCONCLUSIVE, attempt 1/2). The whole job did not fail on INFRA, so job launch 2 is **not** authorised by PLAN §7 and is not launched.
- B1 outcome INCONCLUSIVE at Provisional, single-candidate. Adding seeds requires a sealed amendment (PLAN §5), which is a Manager / human-lead decision. No attempt 2, no Colab, and no P4/P5 reopen from this wake.
- No SSH and no GPU START from the Orchestrator. The verdict was computed by an Orchestrator process that is not an adjudicator (OVERLAY-001 rule 6; no adjudication slot exists in this single-candidate packet).
