# VERDICT — P6d B1 arms — **post-hoc re-score (M1)** (Provisional, single-candidate)

**Label: post-hoc re-score (M1).** This report is not the packet verdict and does not supersede it. The **outcome of record stays attempt-1 INCONCLUSIVE**, and the arms CLOSE `5d8cf393…` stands. Read the M1 outcome only next to that line.

```
OF RECORD  B1_VERDICT verdict=PASS outcome=INCONCLUSIVE failing=[] aulc_HA_xfer=0.5361342107547861 aulc_HA_scratch=0.5023742432955027 aulc_HM_xfer=0.519483948911739 se=0.014513165235814461 partial_outcome=null plan=1088752b tool=62c3ae20
POST-HOC   B1_M1_VERDICT label=post-hoc-M1 verdict=PASS outcome=KILL robust=true failing=[] aulc_full_HA_xfer=0.3598740704583323 aulc_full_HA_scratch=0.41869187142511705 aulc_full_HM_xfer=0.47689527088062883 diff_xs=-0.05881780096678474 margin_xs=0.13216770557700344 se_xm=0.054676367568006694 S-excl=KILL S-full=KILL S-d10=KILL S-ratio=KILL partial_outcome=null v10_outcome=INCONCLUSIVE plan=1088752b amendment=d04aca27 tool=cd32a0ac
```

**Written:** 2026-10-27 EDT by the Orchestrator (Claude · claude-opus-5-5, Claude Code). CPU only. No GPU, Colab or SSH. No new seeds and no attempt 2.
**Authority:** `orch/owner-decisions/20261027-1810-AsiaShanghai-B1-M1-eval-metric-START.md` `73ea581b…` (Manager Class-2 signature). Brief `01ecb8c1…`.
**Method:** global v1.1 `9bdc872e…afc0` (verified at boot) + `method/local/` specials 1–6, OVERLAY-001 and **OVERLAY-002** (`f28c558f…`, added this packet: post-hoc labelled re-score).

## 1. Artifacts

| Artifact | sha256 |
|---|---|
| Amendment `spikes/B1/AMENDMENT-M1-eval-metric.md` (sealed, a-w; appended under PLAN §5, PLAN not edited) | `d04aca276c6042d7bc56c63bb6a328d62fef451290047d310b64d065475abdfe` |
| Tool `spikes/B1/verdict_b1.py` v1.1 (sealed before M1 deposit open; v1.0 logic is the default) | `cd32a0ac2340b5b2e4db6ce969914870305ef38c4694652c0c3d3bb2465f8993` |
| CPU mock log `spikes/B1/m1/cpu-mock-v1.1.log` (M1 23 OK, v1.0 34 OK + 1 skip) | `d636cabe…` |
| M1 results `orch/reports/VERDICT-P6-b1-arms-M1-posthoc-results.json` (= `spikes/B1/results-M1.json`) | `b3a995e83b379ac49c0576088814c37741ad0a53deb2da61a34a400d95e87373` |
| M1 stdout / runs log | `8545d162…` / `9e6cbc27…` |
| Red-team dispositions `spikes/B1/m1/REDTEAM-DISPOSITION.md` | `a29a5c51…` |
| Deposit (read only, unchanged) | `f95155af47357026d69f7c06f01c3d20ca806aa3378fce125322001d1094126d` |
| Attempt-1 record (unchanged; verified by the tool and copied verbatim as `v10_record`) | `64644e3c594de07a6819b685b1d0f956849eaafbff56b3ad87eab0cbb70c1403` |
| `spikes/B1/results.json` / `runs.log` (unchanged) | `64644e3c…` / `c09eacca…` |

**Sequence (UTC, `logs/seal.log`):**

1. Amendment draft1 → codex-astra high r1 → draft2 r2 → draft3 r3 → draft4 r4 (final).
2. SEAL amendment at 10:28:38Z.
3. SEAL tool v1.1 and CPU mock at 10:29:22Z.
4. M1-DEPOSIT-OPEN, then the run.

The tool's v1.0 recomputation in M1 mode reproduces the attempt-1 record with **zero discrepancies**: deposit check, B1-V-1..V-5 all pass, and every per-run R/AULC/R25/R100 and per-arm AULC matches.

## 2. Red team (cross-family; OVERLAY-002 rule 4)

`codex-astra` (gpt-6-astra, high, read-only), 4 rounds. Every round ended **SEAL-AFTER-FIXES**. There were 2 BLOCKERs in r1: δ justification, and sensitivity validity / blocked-case semantics. Both were accepted and fixed.

Main text changes from the red team:

- δ = 0.03 and the dance1 cutoff W = 5336 are labelled **exploratory, data-informed**, and W is conditional on unverified H2;
- an algebraic bar comparison states that M1 is generally the *lower* bar;
- a validity matrix (I1–I3 / C1–C2), with branches evaluated independently;
- `robust` is defined over all four sensitivities.

Tool changes: single pinned deposit, a hash-verified original record, the output alias guard and C2 guards.

At r4 **no objection against the amendment text remained open**. One tool MAJOR (the arm-level C2 writer path) was fixed after r4 and covered by test m21. That fix was **not re-reviewed by codex** (disclosed). Every round's audit of the reviewer's event log found **no access** to the deposit, the open tree, `evals.json` or `quantify.out`, and no arm-level computation. The author ruled on objections to its own draft (disclosed).

## 3. Results (post-hoc; primary = R_full with dance1 cut at W = 5336, δ = 0.03)

| Arm | AULC_full mean (sd; seeds) | R25 | R100 | mean survival S | collapse evals | multi-fail evals | v1.0 AULC (record) |
|---|---|---|---|---|---|---|---|
| **H-A-xfer** | **0.3599** (0.087; .339 .285 .455) | 0.330 | 0.474 | **0.706** | **11/30** | 9/30 | 0.5361 |
| **H-A-scratch** | **0.4187** (0.074; .447 .475 .334) | 0.417 | 0.514 | 0.867 | 5/30 | 4/30 | 0.5024 |
| **H-M-xfer** | **0.4769** (0.037; .502 .495 .434) | 0.493 | 0.519 | 0.927 | 3/30 | 2/30 | 0.5195 |
| H-M-scratch (secondary) | 0.4768 (0.034) | 0.519 | 0.473 | 0.924 | 3/30 | 2/30 | — |
| H-A-frozen (diag., 1 seed) | 0.2658 | 0.005 | 0.518 | 0.510 | 6/10 | 6/10 | — |
| H-A-xfer-noscale (diag., 1 seed) | 0.4752 | 0.477 | 0.527 | 0.942 | 1/10 | 1/10 | — |

Comparison (primary):

| Quantity | Value |
|---|---|
| mean(x) − mean(s) | −0.0588 |
| SE(x, s) | 0.0661 |
| margin_xs = max(0.03, 2·SE(x, s)) | 0.1322 |
| mean(x) − mean(m) | −0.1170 |
| 2·SE(x, m) | 0.1094 |
| bound mean(m) − 2·SE(x, m) | 0.3675 |

**Rule 1 KILL fires on both legs:** mean(x) ≤ mean(s) is true, and mean(x) = 0.3599 < 0.3675 is true.

| Branch | x / s / m AULC_full | outcome |
|---|---|---|
| primary (W = 5336, δ 0.03) | 0.360 / 0.419 / 0.477 | **KILL** |
| S-excl (no dance1) | 0.360 / 0.421 / 0.483 | KILL |
| S-full (dance1 uncut) | 0.343 / 0.399 / 0.455 | KILL |
| S-d10 (δ 0.10) | as primary | KILL |
| S-ratio (PLAN §5 verbatim on AULC_full) | as primary; 1.2 × s = 0.502 | KILL |

`robust=true`: all four one-factor sensitivities agree with the primary.

## 4. Reading (Provisional)

1. **Ranking reversal.** Under the survival-conditioned v1.0 R, H-A-xfer ranked first (0.536 > 0.520 > 0.502). Under the completion-aware R_full, it ranks **last** of the three primary arms (0.360 < 0.419 < 0.477). The reversal comes from survival: H-A-xfer survives 71 % of clip frames on average, against 87 % for scratch and 93 % for H-M-xfer, and has 11/30 collapse evals. This is the hypothesis H6 interaction that brief §4 flagged. Under v1.0 those collapses *raised* H-A-xfer's score.
2. **Strength of the KILL.** It is a KILL by the pre-registered rule, which is the PLAN §5 KILL form. **It is not strong evidence that transfer hurts.**
   - The xfer−scratch leg has no margin in the PLAN form: −0.059 is **under 1 SE(x, s)** (0.066), with 3 seeds and a large spread (H-A-xfer seed AULCs 0.285–0.455).
   - The xfer < mlp − 2SE leg clears its bound by only **0.008**.
   - The robust reading is narrower: under a completion-aware metric, **there is no evidence for the B1 mechanism (attention-decoder transfer learns faster)**, the point estimates go the other way, and the mlp_matched row-mapped transfer (H-M-xfer) is the best primary arm.
3. **Foreknowledge (amendment M1.0).** The author knew before pre-registration that H-A-xfer had more collapses, so the *direction* was foreseeable. Every choice was sealed before computation, and all pre-registered sensitivities agree. W and δ are exploratory (the red team's r1 BLOCKERs), but neither drives the result: S-full has no W, and the KILL rule uses no δ.
4. **What this does not show.** H2 (whether the dance1 frame ~5336 is attainable) is unverified. All arms share RT-a references that failed retarget QA (RT-4 waived). Each R_k is one deterministic rollout per clip (H5 single-draw variance). Mask 0.0 only.
5. **Status.** INCONCLUSIVE (attempt 1) stays the outcome of record. M1 KILL is a **post-hoc, labelled, Provisional** re-reading. It changes no decision, ledger state or CLOSE by itself. Whether to act on it (for example, retire the B1 transfer claim, or gate any B1 citation on it) is a Manager decision.

## 5. Mandatory disclosures (PLAN §0, carried over)

1. **P5 caveat (A1.1-4):** B2 NO_GAIN, u_deficit true, Δρ_U(0.2) = −0.557. B1 inherits no robustness advantage claim for the attention decoder.
2. **RT-4 waived (Class-2 option C, `934b3c9b…`):** references fail retarget QA. RT-6..RT-8 binding.
3. **Claim scope:** decoder-weight transfer between two rigid humanoids (home-humanoid plant class); within-plant arm comparisons on shared RT-a references; whole-policy zero-shot transfer out of scope. Single candidate; Provisional; depth A1.1-1 unchanged.
4. **D-005/D-006 (P4/P5) were scored on the same survival-conditioned R** (P4 112/112, P5 168/168 clip evals failed, median fail step ~60). This is disclosed in the ledger and is **not reopened**.

## 6. Not done (non-goals respected)

No GPU, attempt 2, seeds, Colab or SSH. No P4/P5 reopen. PLAN.md not edited. No depth-3 build. No b2 dance1 reference read. **Optional proposal (not executed; needs a further START):** a CPU-only, no-GPU read on the xn-4090 host of the home-body dance1 reference root height/tilt around frames 5200–5400 (brief b2), to settle H2 and so the S-full vs primary reading. It would not change the M1 outcome class, because S-full is also KILL.
