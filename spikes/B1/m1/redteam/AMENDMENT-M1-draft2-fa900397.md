# AMENDMENT-M1-eval-metric: B1 post-hoc re-score with a completion-aware metric (Class 2, Provisional)

**Label: post-hoc re-score (M1).** This amendment is appended under `spikes/B1/PLAN.md` §5 (sha256 `1088752ba26a8798d721aa93d6e10d1b7bdb7fb924d9d72879acc78d8c2304c8`). PLAN.md is not edited. Both the PLAN and the attempt-1 machine line stay in force and on record:

```
B1_VERDICT verdict=PASS outcome=INCONCLUSIVE failing=[] aulc_HA_xfer=0.5361342107547861 aulc_HA_scratch=0.5023742432955027 aulc_HM_xfer=0.519483948911739 se=0.014513165235814461 partial_outcome=null plan=1088752b tool=62c3ae20
```

(results `orch/reports/VERDICT-P6-b1-arms-attempt1-results.json` `64644e3c594de07a6819b685b1d0f956849eaafbff56b3ad87eab0cbb70c1403`; CLOSE INCONCLUSIVE `5d8cf393044efcab8ab899ae9c51a463f7a2214643ea7c87eddf34127c4d2ebd`, which this amendment does not supersede.)

**Written:** 2026-10-27 EDT by the Orchestrator (Claude · claude-opus-5-5, Claude Code). CPU only.
**Authority:** Manager Class-2 signature `orch/owner-decisions/20261027-1810-AsiaShanghai-B1-M1-eval-metric-START.md` sha256 `73ea581bb89e3025304994c200394d2621e64a02407fa8ae6f525d67caffc9b6`. Outline: `docs/FOLLOWON_BRIEF_B1_EVAL_METRIC.md` `01ecb8c13bef70c30212573a90da79654e12578830a5a02efacbf5e2f25a752d` §5.
**Method:** global v1.1 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0` + `method/local/` README specials 1–6, OVERLAY-001 and **OVERLAY-002** (post-hoc labelled re-score; added for this packet).
**Decision cap:** Provisional, single-candidate. Depth rule A1.1-1 is unchanged: no depth-3 build on B1 without a further signature. Home-humanoid / plant-class wording only.

---

## M1.0 Prior knowledge of the author (disclosure)

The author of this amendment had already seen these sealed descriptive results (brief §3; `orch/analysis/b1-eval-metric/quantify.out` `9aa84c7e…`, `evals.json` `743e7db8…`):

- failed-clip counts per eval, per run and per arm, including that H-A-xfer has more multi-fail evals (11/30) than H-A-scratch (5/30) or H-M-xfer (3/30);
- per-run v1.0 R_k curves;
- coverage (survived share of frames) pooled by failed count, but **not** split by arm;
- the dance1 common failure at step 5336 (116/140 evals);
- the pooled per-term reward means by failed count (brief §3.5), which inform δ (M1.5).

The author has **not** computed AULC, R_k or any arm-level statistic under R_full, under any dance1 rule, or under any criterion in this amendment. Because collapses are known to be more frequent in H-A-xfer, and R_full penalises collapse, the author could foresee the **direction** of some effects. This is a post-hoc analysis. The mitigations are: (i) every structural choice below follows the brief §5 outline, which was sealed before this packet. Where a value is data-informed, it is labelled **exploratory**: the cutoff W (M1.3) and the margin δ (M1.5); (ii) a cross-family red team reviews the text before seal; (iii) the sensitivity analyses are pre-registered and reported in full whichever way they fall.

## M1.1 Scope

- Re-score **only** the sealed deposit `logs/xn4090/2026-10-27/b1arms-20261027-0935.tgz` (sha256 `f95155af47357026d69f7c06f01c3d20ca806aa3378fce125322001d1094126d`), using the eval JSONs already in it. No training, no new evals, no GPU, no Colab, no new seeds, no attempt 2.
- The scored attempt of every run and the scored execution of every eval point are chosen exactly as in v1.0 (PLAN §5, §7; IMPLEMENTATION_NOTES items 4–7). M1 changes only how one scored eval JSON becomes one number.
- P4/P5 (D-005/D-006) are not re-scored.

## M1.2 Primary metric: R_full,k (completion-aware; brief remedy a1)

The data come from each scored eval JSON (`…_mask0.00.json`). For each of the 4 clips c it gives `norm_return_c` = Σ_t r_t / (max_r · steps_c), plus `steps_c` (steps survived) and `frames_c` (clip length).

Define the per-clip completion-aware return with an effective length F_c:

  **R_full,c = norm_return_c · steps_c / F_c, defined only for 1 ≤ steps_c ≤ F_c**

`benchmark.py` accumulates the reward of a step, increments `steps`, and only then checks termination. So the stored sum covers the first `steps_c` benchmark transitions, including the terminating one. On the domain steps_c ≤ F_c, R_full,c equals Σ_{t < steps_c} r_t / (max_r · F_c), the per-transition return over the first F_c transitions, with transitions that were not reached scoring zero. This is reconstructed from stored binary64 values, so it is subject to their floating-point precision. A record with steps_c > F_c is **non-computable** (the stored sum includes transitions beyond F_c) and is handled by M1.6, never by clipping. Then **R_full,k = mean over the 4 clips of R_full,c** (unweighted, as in v1.0).

Pinned clip lengths (frames @ 50 fps, from the sealed data step; each eval JSON must match them, M1.6):

| clip | frames_c | F_c (primary) |
|---|---|---|
| walk1_subject1 | 13066 | 13066 |
| run1_subject2 | 11891 | 11891 |
| jumps1_subject1 | 12222 | 12222 |
| dance1_subject1 | 6574 | **W = 5336** (M1.3, primary rule only) |

The 0.1 constant `max_r` cancels: R_full uses only `norm_return`, `steps` and F_c.

**AULC, R25, R100:** the PLAN §5 formulas, unchanged, applied to R_full,k. That is, AULC = (1/9) Σ_{k=1}^{9} (R_k + R_{k+1})/2 over the 10 points it 160 … it 1600; R25 is linear between it 320 and it 480; R100 = R at it 1600.

**Reported beside R_full (descriptive, no role in the outcome):**

- per eval: survival fraction S_k = Σ_c steps_c / Σ_c F_c over the clips included by the rule; the multi-fail flag (M1.4 failed count ≥ 2); the collapse flag (M1.4);
- per run and arm: mean S, the number of multi-fail evals and the number of collapse evals;
- the v1.0 R_k, AULC and outcome, copied from the original computation for side-by-side reading.

**Root-term (tracking-only) variant: omitted.** The per-clip `terms` are per-step means, and there is no pre-sealed ceiling for a subset of terms. Re-normalising a subset would add a free choice, so no tracking-only variant is computed in M1.

## M1.3 dance1 rule (brief remedy b1)

**Primary: cutoff at the observed common-failure step, W = 5336 (exploratory, conditional on H2).** dance1_subject1 is scored on its first W = 5336 benchmark transitions (F = 5336 instead of 6574), including the terminal transition. The cases:

- steps = 5336: complete, not a failure;
- steps < 5336: a failure, scored by R_full on F = 5336;
- steps > 5336: non-computable, so the eval point is invalid under every branch that uses this rule (M1.6). Nothing is imputed.

*Rationale and status:* 116/140 evals end dance1 at exactly step 5336, across both architectures, all inits and all seeds (brief §3.4). H2 reads this as a reference-side event on the home body. H2 is **not verified**, and a common failure location across policies does not show that the frame is unattainable. W is an observed, outcome-derived cutoff, applied identically to all arms. Excusing the dance1 failure at W is valid only to the extent H2 holds. The brief proposed [0, 5300). That window is not computable from the deposit, because only the sum over survived transitions is stored. W = 5336 is used because it is computable, not because it has independent scientific grounding.

**Sensitivity S-excl (pre-registered; reported, not binding):** exclude dance1. R_full,k, S_k and the failure and collapse counts all use only the 3 other clips. dance1 records must still pass the integrity checks (M1.6).
**Sensitivity S-full (pre-registered; reported, not binding):** plain remedy a1 with no dance1 special case. F_dance1 = 6574 = frames, and the dance1 failure counts.

H2 is checked by remedy b2, which is out of scope here. If b2 shows the frame is attainable, the primary rule has excused real policy failures, and S-full is then the better reading.

## M1.4 Failure, multi-fail and collapse (brief remedy a2)

- A clip **fails** if steps_c < F_c, so under the primary rule dance1 fails only if steps < 5336. The failed count of an eval is the number of failed clips among those the rule includes (0–4, or 0–3 under S-excl).
- **Collapse:** an eval is a collapse if at least one included clip has 10 · steps_c < F_c (integer comparison), that is, it fails within the first 10 % of its effective length.
- **Handling: score, do not invalidate.** Collapse evals are scored by R_full like any other eval. Their unsurvived frames contribute zero, which is the a1 correction. They are not dropped, imputed or capped. *Rationale:* invalidating collapses would remove exactly the events whose mis-scoring motivated M1. Scoring them through R_full is the only handling of a2 that needs no imputation choice. Collapse and multi-fail counts are reported per arm (M1.2) and have no role in the outcome.

## M1.5 Criterion (brief remedy a3) and outcome

Notation: x = H-A-xfer, s = H-A-scratch, m = H-M-xfer. mean = arm mean of the run AULC_full over its seeds. SE(X, Y) = sqrt(s_X²/n_X + s_Y²/n_Y), sample s.d. with ddof = 1 (n = 3 when the verdict is PASS).

Margin **δ = 0.03** on the R_full AULC scale. **δ is an exploratory, data-informed threshold.** It has no external practical grounding and no "20 % faster learning" interpretation.

*How it was set (disclosed):* the value was fixed before any R_full computation, by this heuristic. Pooled over the 111 failed=1 evals (brief §3.5, an outcome-selected subset, all arms mixed), about 0.35 of the v1.0 nominal R ≈ 0.508 comes from two near-saturated terms (body_pos + body_lin_vel). 20 % of the remainder (≈ 0.158) is ≈ 0.03. This calibration is on the v1.0 scale. Under R_full these terms are scaled by survival, so the offset is not constant and the heuristic does not transfer exactly. It is a rough scale, not an equivalence.

*Bar comparison (algebraic; no data):* for mean(s) > 0, the PLAN rule requires mean(x) − mean(s) ≥ 0.2 · mean(s). M1 requires mean(x) − mean(s) ≥ max(0.03, 2·SE(x, s)). Either can be larger. M1 is the lower bar exactly when max(0.03, 2·SE(x, s)) < 0.2 · mean(s), which holds for mean(s) > 0.15 whenever 2·SE(x, s) < 0.2 · mean(s). At R ≈ 0.5, the M1 primary criterion is therefore expected to be **easier** to meet than the PLAN's. This is the main reason S-ratio and S-δ10 are registered.

Rules, applied in this order with exact float comparisons:

1. **KILL** if mean(x) ≤ mean(s), **or** mean(x) < mean(m) − 2·SE(x, m). (Same form as PLAN §5.)
2. else **SIGNAL_STRONG** if mean(x) − mean(s) ≥ max(δ, 2·SE(x, s)) **and** mean(x) − mean(m) ≥ 2·SE(x, m).
3. else **SIGNAL** if mean(x) − mean(s) ≥ max(δ, 2·SE(x, s)) **and** mean(x) ≥ mean(m) − 2·SE(x, m).
4. else **INCONCLUSIVE**.

Compared with PLAN §5, the only change is in rules 2–3: "mean(x) ≥ 1.2 × mean(s)" is replaced by "mean(x) − mean(s) ≥ max(δ, 2·SE(x, s))". The new form adds a precision floor that v1.0 did not have. The PLAN §5 branch for mean(s) ≤ 0 is not needed, because the rule is a difference.

**Pre-registered sensitivities (all reported; none binding):**

| ID | Change from primary | Purpose |
|---|---|---|
| S-excl | dance1 excluded (M1.3), same criterion | dance1 rule |
| S-full | dance1 with no special case (M1.3), same criterion | dance1 rule / H2 not verified |
| S-δ10 | fixed margin δ = 0.10, primary metric (a fixed-margin sensitivity; 0.10 = 0.2 × 0.5, the PLAN bar at the v1.0 reference level, but **not** equivalent to the PLAN threshold on R_full) | margin choice |
| S-ratio | v1.0 criterion text verbatim (1.2 × mean(s), with the mean(s) ≤ 0 branch; KILL and SIGNAL_STRONG as PLAN §5) on AULC_full, primary metric. **Only this sensitivity speaks to equivalence with the PLAN criterion** | criterion form |

Only these four one-factor sensitivities are registered. Clip-rule × criterion interactions are not.

**Interpretation rule (pre-registered).** Outcome classes are KILL, INCONCLUSIVE, SIGNAL and SIGNAL_STRONG. SIGNAL and SIGNAL_STRONG are **distinct** classes.

- `robust=true`: the primary verdict is PASS, all four sensitivities have a non-null outcome, and all four equal the primary class.
- `robust=false`: all are non-null and at least one differs. The report gives every outcome and calls the primary **fragile**.
- `robust=null`: the primary is BLOCKED, or any sensitivity outcome is null (comparison unavailable).

The label means only "agreement across the four specified one-factor sensitivities". In every case the attempt-1 outcome (INCONCLUSIVE) remains the packet outcome of record.

## M1.6 Validity and M1 kill criterion

Every v1.0 check stays binding unchanged and with its existing scope: deposit seal and members, tarball sha, B1-V-1..B1-V-5, scored-attempt and scored-exec selection. This includes B1-V-3 on the diagnostic transfer/frozen runs (IMPLEMENTATION_NOTES item 12). A v1.0 failure makes M1 BLOCKED and makes every branch's outcome null; branch partial outcomes are still reported.

**Frozen selection.** The scored attempt and scored execution of every run and point are fixed first by the v1.0 rules. An M1 validation failure never triggers a fallback to another attempt or execution.

**Per-eval checks.** A record fails validation if a field is missing or malformed. Booleans are not accepted as numbers or integers.

| # | Check | Kind | primary | S-excl | S-full | S-δ10 | S-ratio |
|---|---|---|---|---|---|---|---|
| I1 | `clips` is a list of exactly 4 objects whose `name` strings equal the 4 pinned clips | integrity | ✓ | ✓ | ✓ | ✓ | ✓ |
| I2 | every clip: finite `norm_return`; integer `frames` equal to the pinned value; integer `steps` with 1 ≤ steps ≤ frames | integrity | ✓ (all 4 clips) | ✓ (all 4, incl. dance1) | ✓ | ✓ | ✓ |
| I3 | finite `summary.mean_norm_return` with \|mean of the 4 clip norm_return − it\| ≤ 1e-9 | integrity | ✓ | ✓ | ✓ | ✓ | ✓ |
| C1 | dance1 steps ≤ W = 5336 | computability | ✓ | — | — | ✓ | ✓ |
| C2 | the derived R_full,k and S_k are finite | computability | ✓ | ✓ | ✓ | ✓ | ✓ |

A run is valid for a branch if all 10 of its scored points pass that branch's checks.

**Each branch is evaluated independently.** Every branch (primary and each sensitivity) computes its own run validity, the seeds it retains, its outcome and its partial outcome. A BLOCKED primary does not stop the computable sensitivities from being computed and reported.

**M1 kill criterion (BLOCKED).** A branch is BLOCKED (outcome null) if any of the 9 primary runs is invalid for that branch, or if any v1.0 check fails. M1's `verdict` is the primary branch's. This is stricter than the brief §5 item 7 rule ("fewer than 2 of 3 primary arms"), which it contains.

**Partial outcome.** It is computed only when every primary arm retains at least 2 valid runs, and SIGNAL/SIGNAL_STRONG are capped to INCONCLUSIVE. It is an **informational result on the explicitly listed retained seeds**. It supports no inference about the complete primary comparison and has no decision authority.

**Scope of the new checks.** The M1-specific checks (I1–I3, C1–C2) gate only through the 9 primary runs. Secondary and diagnostic runs are reported where valid.

**Numerics.** All arithmetic is IEEE binary64, with no intermediate rounding. Clips are processed in name-sorted order, points in iteration order and seeds in increasing order. Every aggregate reports its denominator (clips, evals, seeds) and the retained seed identities.

## M1.7 Tool

- `spikes/B1/verdict_b1.py` **v1.1**. The default mode is v1.0, byte-for-byte in logic, so the attempt-1 line is reproducible. M1 runs only with `--amendment-m1 <this file>`, and the tool checks this file's sha256 against a pinned constant before computing anything.
- `robust` is printed as `true|false|null` (M1.5). Every sensitivity outcome is printed, null included.
- In M1 mode it writes **new** files: `spikes/B1/results-M1.json` and `spikes/B1/runs-M1.log`. It never writes `spikes/B1/results.json` or `spikes/B1/runs.log`. It prints exactly one line:
  `B1_M1_VERDICT label=post-hoc-M1 verdict=<PASS|BLOCKED> outcome=<SIGNAL_STRONG|SIGNAL|INCONCLUSIVE|KILL|null> robust=<true|false|null> failing=[…] aulc_full_HA_xfer=… aulc_full_HA_scratch=… aulc_full_HM_xfer=… diff_xs=… margin_xs=… se_xm=… S-excl=… S-full=… S-d10=… S-ratio=… v10_outcome=INCONCLUSIVE plan=1088752b amendment=<8> tool=<8>`
- Order: v1.1 is CPU-mock tested on synthetic fixtures only, including that default mode reproduces the v1.0 outcomes. Its sha256 is sealed in `logs/seal.log` **before** it opens the deposit. It is run by an agent process that is not an adjudicator (OVERLAY-001 rule 6; single-candidate packet, no adjudicator exists).

## M1.8 Red team and roles

| Slot | Binding |
|---|---|
| Amendment author, tool author, Orchestrator | Claude · claude-opus-5-5 (Claude Code) |
| Cross-family red team (amendment text, before seal) | `codex-astra` (OpenAI Codex · `gpt-6-astra`, codex-cli 0.163.0), effort **high**, `-s read-only -C <program root>`, objections only. It is told not to open the deposit or open tree and not to compute arm-level quantities under any candidate metric; its event log is audited for this. Dispositions are written by the Orchestrator in `spikes/B1/m1/REDTEAM-DISPOSITION.md`, and the Orchestrator rules on objections to its own draft (disclosed) |
| Verdict | `verdict_b1.py` v1.1 machine output (CPU), run by the Orchestrator's shell; no model judgment |

This review satisfies **only** M1's own review requirement. The PLAN §9 gap (no red team on PLAN.md before its seal) stays on record. A review now cannot repair that original timing gap.

## M1.9 Labelling and reporting

- Every M1 artifact carries "post-hoc re-score (M1)". The report places the M1 outcome next to the attempt-1 INCONCLUSIVE. It never stands alone, and it is not a packet verdict or a decision change.
- All PLAN §0 disclosures carry over: the P5 caveat, the RT-4 waiver and the claim scope.
- A ledger observation is added (disclosure only, no reopen): D-005/D-006 were scored on the same survival-conditioned R.
- Any further action (b2 dance1 reference read, seeds, RT-b, eval-protocol changes) needs a further START.
