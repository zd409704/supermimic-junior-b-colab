# spikes/B1/PLAN.md — B1 transfer arms on the home humanoid (pre-registered)

**Packet:** P6c (sealed) for P6d execution. **Written:** 2026-10-26 ~19:50 EDT by the Orchestrator (`claude-opus`), before any B1 arm has run and before the B1-RT GPU job has started. **Status:** Provisional, **single-candidate** (brief Amendment v1.1 A1.1-6). The decision this spike feeds may not be built on without a further signature (depth 2, A1.1-1).
**Method:** v1.1 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0` + `method/local/OVERLAY-001` (relay in place of owner, A1.1-5).
**Authority:** P6 START `3a0254de…`; xn-4090 amend `1408aeef…`; brief `briefs/B1-home-humanoid-cross-embodiment.md` (Amendment v1.1, sha256 `787b2980…`); Class-2 option C `orch/owner-decisions/20261026-1931-EDT-p6-rt4-class2-c-waive.md` sha256 `934b3c9b85231ecedc2704b06e9abd9ccf41b92a871fcc09f8e622b4d294c262`.
**Inputs:** B1-RT PLAN `spikes/B1-RT/PLAN.md` sha256 `b7365b4f2e382344151c64be979e5e2aff102fbaba6dc6826d8a429b3b9852a5`; amendment `spikes/B1-RT/AMENDMENT-C2-rt4.json` sha256 `32143be4687ca6de270165a848eaf4aa8292a21a40e8255c142c32f9f048c591`; `docs/SCHEME_PLAN.md` §4 (arms and draft criteria; this file freezes them); brief §7.

---

## 0. Mandatory disclosures (copied into every B1 write-up)

1. **P5 caveat (A1.1-4).** "The B0+B2 gate to B1 is **Go** because B0 was non-inferior. B2 returned **NO_GAIN** with **u_deficit = true**: Δρ_U(0.2) = −0.557 (the attention decoder retained *less* return than mlp_matched under untrained 20 % token masking). B1 therefore does not inherit any robustness advantage claim for the attention decoder."
2. **RT-4 waived (Class-2 option C).** RT-4 (retarget QA) failed on CPU attempt 1: 0/4 slots. On the four clips used here (first clip of each slot): walk1_subject1 clip-frac 0.197 / penetration p95 0.0173 m / skate p95 1.316 m/s; run1_subject2 0.439 / 0.0188 / 1.300; dance1_subject1 0.281 / 0.0202 / 1.142; jumps1_subject1 0.206 / 0.0150 / 1.297 (thresholds 0.10 / 0.01 / 0.10). Source baseline with identical definitions on the 29-DoF reference body: skate p95 0.88–2.74 m/s on all 8 clips, penetration p95 0.0071–0.0108 m. RT-4 is waived; RT-6..RT-8 stay binding.
3. **Claim scope (A1.1-8 + amendment C).** "Decoder-weight transfer between two rigid humanoids, with per-body motion encoder, world model and critic; references produced by route RT-a, which failed retarget QA (RT-4, waived under Class-2 option C; the sealed RT-4 skate measure is not attainable on the 29-DoF source itself)." Results are within-plant arm comparisons on shared references. Absolute home-humanoid returns are not comparable to the reference body's. Whole-policy zero-shot transfer is out of scope by construction.

## 1. Mechanism under test

Initialising the J = 22 home-humanoid decoder from the P4 29-DoF attention checkpoint (full fine-tune; per-body encoder, WM and critic new) makes tracking learn faster over a fixed env-step budget than (a) the same architecture from scratch, and at least as well as (b) the P4 mlp_matched checkpoint transferred by joint-semantic row mapping.

## 2. Gate (stage 1): B1-RT

No arm runs unless the B1-RT machine verdict (`spikes/B1-RT/verdict_rt.py`, sealed `2341a93d…`, run with `--amendment spikes/B1-RT/AMENDMENT-C2-rt4.json`) on the scored `p6-b1-rt` deposit shows: **RT-1, RT-2, RT-3 pass; RT-4 waived; RT-5 recorded finite; RT-6, RT-7, RT-8 pass** (machine `verdict=PASS waived=[RT-4]`). Anything else → `spikes/B1/BLOCKED.md`, no arm runs, return to the Manager.

## 3. Venue, data and fixed settings

- **Venue:** **xn-4090-gpu2**, GPU0, mutex `gpu0`, `HF_ENDPOINT=https://hf-mirror.com`, launched by the Manager relay from `orch/jobs/p6-b1-arms.json` in state READY (A1.1-5). Colab only through a further amendment.
- **Data:** the RT job's data step, unchanged: `prepare_b1_data.py --rev ce1572906efe6157840e8474d5a0d7aa87481e74 --slot-rule first --expect spikes/B1-RT/results-cpu-attempt1.json`. Clips walk1_subject1, run1_subject2, dance1_subject1, jumps1_subject1; CSV sha256 must equal the box values; npz on the GPU host only (X-002).
- **Upstream:** CuboiLeo/SuperMimic-Reproduced at `d9be385b3eeb13a638fb33fb200d3bfd9be9839f` + `packets/P6/upstream-b1.patch` (body parametrisation, `SM_BODY_MODULE=sm_body_home`), in a fresh clone `/content/SuperMimic-Reproduced-b1`. The P4 tree is read only.
- **Training config:** `packets/P6/configs/b1_home.yaml` (P4 decoder settings; 512 envs, batch 512, horizon 16, compile None, `--env.anchor-obs`, checkpoint interval 160, log interval 50, max-hours 1.5 as a safety cap only). H-A-xfer-noscale uses `packets/P6/configs/b1_home_noscale.yaml` (only `descriptor_scale_norm: false` differs).
- **Budget (equal env steps):** **1600 training iterations per run** (1.0× the P4 per-arm budget; 512 env steps per iteration). Endpoint = `ckpt_0001600.pt`, harness stop exactly as `spikes/B0/PLAN.md` §4.3 (no upstream iteration cap; F-1 unsuitable). Equal policy updates are checked (§6 B1-V-2).
- **Entry:** `packets/P6/b1/p6_entry.py train --config <cfg> --policy <arm> --seed <s> --init <scratch|xfer|frozen> [--src-ckpt <P4 ckpt>] --run-tag <arm-tag>`.

## 4. Arms and seeds

| Arm | Policy · init | Transfer source (P4 `ckpt_0001600.pt`, P5-verified sha256) | Seeds | Role |
|---|---|---|---|---|
| **H-A-scratch** | attention · scratch | — | 0, 1, 2 | Primary: from-scratch baseline |
| **H-A-xfer** | attention · xfer (full fine-tune; all decoder parameters loaded strict-shape; `morphology`/`scale` buffers are the home body's) | seed k ← `b0_attention_s{k}`: s0 `5fb48347dd957b91de4b6780c53bd43d9f1777f56aabc3396aa7351181474a1d`, s1 `44971f21d0f9bd3dc2abbbba4775c0597efa09c64da0db376c55eb09a7d61d68`, s2 `c09d6b8ae4ecc9c7ced48a587869087bf8bc4803da08694bcd2c15dc233d28e5` | 0, 1, 2 | **Primary: arm under test** |
| **H-M-xfer** | mlp_matched · xfer (row map: 20/22 joints mapped, head yaw/pitch rows fresh, hidden layers copied; P4 hidden widths kept) | seed k ← `b0_mlp_matched_s{k}`: s0 `9ae05d74b9813e4858904a196cffe718d95d1237b41fdd7620aa3c842001913e`, s1 `5eb302ed06aad69fe9793cc0b0f085536423c30c53e1c6ef46653fce77211da9`, s2 `88a396ce00333b4e72b43fafefd2e62f8b83604cf185115e1f9e0a8a32fa73e1` | 0, 1, 2 | **Primary: strongest fair transfer baseline** |
| H-M-scratch | mlp_matched · scratch (sized to the J = 22 attention) | — | 0, 1, 2 | Secondary (B0 replication on body 2). No role in §5 |
| H-A-frozen | attention · frozen decoder | `b0_attention_s0` | 0 | Diagnostic. No pass/fail |
| H-A-xfer-noscale | attention · xfer, scale-normalisation off | `b0_attention_s0` | 0 | Ablation for R7. No pass/fail |

**Order (fixed):** primary seed-major — (H-A-scratch s0, H-A-xfer s0, H-M-xfer s0), then s1, then s2 — then H-M-scratch s0..s2, H-A-frozen s0, H-A-xfer-noscale s0. Secondary runs start only if the spend cap (§7) leaves room for a whole run plus its evals. The source checkpoint sha256 is checked before each xfer/frozen run; a mismatch blocks that run.

## 5. Metric and pre-registered criteria (frozen from brief §7 / SCHEME_PLAN §4)

- **Evaluation points:** `ckpt_0000160 … ckpt_0001600` (10 equally spaced points, 10 %…100 % of budget). Each is evaluated once with `p6_entry.py eval --masks 0.0` (upstream whole-clip benchmark, 64 envs, the 4 clips). R_k = `summary.mean_norm_return` at point k. One re-execution is allowed only if the eval process exits non-zero or writes no JSON.
- **AULC** per run = (1/9) · Σ_{k=1}^{9} (R_k + R_{k+1}) / 2 (trapezoid over [10 %, 100 %] divided by the interval length). Secondary: R at 25 % (linear interpolation between it 320 and it 480) and R at 100 % (it 1600).
- **Statistics:** per arm, mean AULC over its 3 seeds. For arms X, Y: SE(X, Y) = sqrt(s_X²/3 + s_Y²/3), sample s.d. with ddof = 1 (this is the "pooled SE" of the brief).
- **Outcome (machine):**
  - **KILL** if mean(H-A-xfer) ≤ mean(H-A-scratch) **or** mean(H-A-xfer) < mean(H-M-xfer) − 2·SE(H-A-xfer, H-M-xfer).
  - else **SIGNAL_STRONG** if mean(H-A-xfer) ≥ 1.2 × mean(H-A-scratch) **and** mean(H-A-xfer) − mean(H-M-xfer) ≥ 2·SE(H-A-xfer, H-M-xfer).
  - else **SIGNAL** if mean(H-A-xfer) ≥ 1.2 × mean(H-A-scratch) **and** mean(H-A-xfer) ≥ mean(H-M-xfer) − 2·SE(H-A-xfer, H-M-xfer).
  - else **INCONCLUSIVE**. No seeds are added without a sealed amendment.
  - If mean(H-A-scratch) ≤ 0, the 1.2× test reads mean(H-A-xfer) − mean(H-A-scratch) ≥ 0.2 · |mean(H-A-scratch)|.
- Secondary/diagnostic arms are reported (AULC, R25, R100) with no effect on the outcome.

## 6. Validity checks (any failure → verdict BLOCKED with the failing IDs; outcome not reported as a pass)

| ID | Check |
|---|---|
| B1-V-1 | Every primary run (9) completed: `ckpt_0001600.pt` stable, it-1600 line printed, sidecar present, seams S1/S2/S5 true, all 10 eval JSONs present with finite R_k. A missing primary run after its attempt cap → BLOCKED; partial seeds are reported as INCONCLUSIVE at best, never as a pass (brief §10) |
| B1-V-2 | Equal env steps and policy updates: every primary run stopped at iteration 1600 and `time/updates` at it 1600 is equal across all primary runs |
| B1-V-3 | Transfer identity: for every xfer/frozen run, sidecar `transfer_src.sha256` = the §4 identity; attention report = all decoder parameters loaded; mlp report = 20 rows mapped, fresh joints = head yaw/pitch |
| B1-V-4 | Data identity: data-step `pass` true, `used_clips` = the 4 first clips, `csv_sha_mismatch` empty, `slot_rule` = `first` |
| B1-V-5 | GPU: the **used** device line captured by the driver (`nvidia-smi -i $CUDA_VISIBLE_DEVICES --query-gpu=index,uuid,name --format=csv`, CUDA_VISIBLE_DEVICES = 0) names exactly `NVIDIA GeForce RTX 4090`. Other rows of the host table are reported, not checked (avoids the P5 multi-row defect, `orch/reports/CR-verdict-b2-gpu-name-parse.md`) |

## 7. Attempts and budgets

- Per run at most 2 attempts; attempt 2 only after an INFRA failure (exception, OOM, relay/session loss) before the endpoint, with byte-identical inputs and a fresh run directory (the attempt-1 directory is archived without `*.pt`). A run that becomes non-finite is a result, not an infra failure; it is reported and counts as not completed for B1-V-1.
- **Spend cap:** 9.0 GPU wall-hours for the arms job (SCHEME_PLAN §8 envelope ≈ 8–9 GPU-h), enforced by the driver; on hitting it the driver writes `BLOCKED.md` (`spend_cap`) and deposits what exists.
- Job attempts: at most 2 job launches; launch 2 only after an INFRA failure of the whole job, resuming from the driver state with completed runs kept.

## 8. Deposit and verdict

Bundle `b1arms-*.tgz` (meta, train logs, tb, sidecars, eval JSONs, data QA JSON, deviations; **no `.pt`, `.npz`, `.csv`**) deposited unmodified to `logs/xn4090/<UTC date>/` and sealed (`DEPOSIT xn4090`) in `logs/seal.log` before any agent opens it. The machine verdict is computed by `spikes/B1/verdict_b1.py`, which implements §5–§6 literally and is sealed before the deposit is opened. Output `spikes/B1/results.json` and one line `B1_VERDICT verdict=<PASS|BLOCKED> outcome=<SIGNAL_STRONG|SIGNAL|INCONCLUSIVE|KILL|null> …`. Prose never overrides it.

## 9. Roles (A1.1-6; non-contest packet)

| Slot | Binding |
|---|---|
| Orchestrator (PLAN, job JSON, deposit seal) | Claude · claude-opus-5-5 (Claude Code), medium |
| Infra code (driver, verdict tool) | Orchestrator session (Claude · claude-opus-5-5); CPU mock run before READY |
| GPU runner | xn-4090 relay-launched driver (OVERLAY-001 rules 2–6, relay in place of owner) |
| Verdict | `verdict_b1.py` output (machine), run by an agent process that is not an adjudicator |
| Cross-family red team on this PLAN | `codex-astra` high: **not run at seal** (P6 C2 wake scope). Disclosed here; if run later, objections are handled only by a sealed amendment before the arms job is READY |

## 10. Confounds disclosed up front

1. References fail retarget QA (§0 item 2). All arms share them, so arm comparisons stay internally fair; transfer may look different on better references (RT-b, a possible later packet).
2. Single candidate design (A1.1-6): no Step 2 contest, no adjudication; decision capped at Provisional, labelled single-candidate.
3. The P4 transfer sources were trained on the 29-DoF body with the P4 config; H-A-xfer and H-M-xfer seeds pair with the P4 seed of the same index.
4. AS-1 leg inertia 0.015 (calibrated on the RT-3 stand; `spikes/B1-RT/ASSUMPTIONS.md`).
5. The P5 caveat (§0 item 1) applies to any robustness reading.
