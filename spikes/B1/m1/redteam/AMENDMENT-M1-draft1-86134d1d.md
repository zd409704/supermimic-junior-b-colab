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
- the dance1 fixed failure at step 5336 (116/140 evals).

The author has **not** computed AULC, R_k or any arm-level statistic under R_full, under any dance1 rule, or under any criterion in this amendment. Because collapses are known to be more frequent in H-A-xfer, and R_full penalises collapse, the author could foresee the **direction** of some effects. This is a post-hoc analysis. The mitigations are: (i) every choice below follows the brief §5 outline, which was sealed before this packet, or is fixed by a stated non-arm rationale; (ii) a cross-family red team reviews the text before seal; (iii) the sensitivity analyses are pre-registered and reported in full whichever way they fall.

## M1.1 Scope

- Re-score **only** the sealed deposit `logs/xn4090/2026-10-27/b1arms-20261027-0935.tgz` (sha256 `f95155af47357026d69f7c06f01c3d20ca806aa3378fce125322001d1094126d`), using the eval JSONs already in it. No training, no new evals, no GPU, no Colab, no new seeds, no attempt 2.
- The scored attempt of every run and the scored execution of every eval point are chosen exactly as in v1.0 (PLAN §5, §7; IMPLEMENTATION_NOTES items 4–7). M1 changes only how one scored eval JSON becomes one number.
- P4/P5 (D-005/D-006) are not re-scored.

## M1.2 Primary metric: R_full,k (completion-aware; brief remedy a1)

The data come from each scored eval JSON (`…_mask0.00.json`). For each of the 4 clips c it gives `norm_return_c` = Σ_t r_t / (max_r · steps_c), plus `steps_c` (steps survived) and `frames_c` (clip length).

Define the per-clip completion-aware return with an effective length F_c:

  **R_full,c = norm_return_c · min(steps_c, F_c) / F_c**

This equals Σ_t r_t / (max_r · F_c): frames the policy did not survive score zero. Then **R_full,k = mean over the 4 clips of R_full,c** (unweighted, as in v1.0).

Pinned clip lengths (frames @ 50 fps, from the sealed data step; each eval JSON must match them, M1.6):

| clip | frames_c | F_c (primary) |
|---|---|---|
| walk1_subject1 | 13066 | 13066 |
| run1_subject2 | 11891 | 11891 |
| jumps1_subject1 | 12222 | 12222 |
| dance1_subject1 | 6574 | **W = 5336** (M1.3) |

The 0.1 constant `max_r` cancels: R_full uses only `norm_return`, `steps` and F_c.

**AULC, R25, R100:** the PLAN §5 formulas, unchanged, applied to R_full,k. That is, AULC = (1/9) Σ_{k=1}^{9} (R_k + R_{k+1})/2 over the 10 points it 160 … it 1600; R25 is linear between it 320 and it 480; R100 = R at it 1600.

**Reported beside R_full (descriptive, no role in the outcome):**

- per eval: survival fraction S_k = Σ_c min(steps_c, F_c) / Σ_c F_c; the multi-fail flag (M1.4 failed count ≥ 2); the collapse flag (M1.4);
- per run and arm: mean S, the number of multi-fail evals and the number of collapse evals;
- the v1.0 R_k, AULC and outcome, copied from the original computation for side-by-side reading.

**Root-term (tracking-only) variant: omitted.** The per-clip `terms` are per-step means, and there is no pre-sealed ceiling for a subset of terms. Re-normalising a subset would add a free choice, so no tracking-only variant is computed in M1.

## M1.3 dance1 rule (brief remedy b1)

**Primary: window at the reference-defect frame, W = 5336.** For dance1_subject1, F = 5336 instead of 6574. A dance1 rollout with steps ≥ 5336 counts as complete and is not a failure. A dance1 rollout with steps < 5336 is a failure and is scored on [0, 5336).

*Rationale (non-arm):* 116/140 evals fail dance1 at exactly step 5336, across both architectures, all inits and all seeds (brief §3.4, H2). This is treated as a reference-side defect on the home body. The brief proposed the window [0, 5300). That window is **not computable** from the deposit: the eval JSON stores only Σ over the survived steps, not per-step rewards, so the last 36 steps of a 5336-step rollout cannot be removed. W = 5336 is the earliest window that is exact on the stored data. For a rollout with steps ≤ 5336, its whole return lies inside the window.

*Non-computable case (pre-registered):* if a dance1 rollout has steps > 5336, its stored sum includes frames beyond W and cannot be truncated. That eval point is then **invalid** (M1.6). Nothing is imputed.

**Sensitivity S-excl (pre-registered; reported, not binding):** exclude dance1. R_full,k = mean of R_full,c over the 3 other clips.
**Sensitivity S-full (pre-registered; reported, not binding):** plain remedy a1 with no dance1 special case. F_dance1 = 6574 = frames, and the dance1 failure counts.

H2 itself (that the reference is unattainable at frame ~5336) is **not verified** here; that is remedy b2, which is out of scope. If b2 later shows the frame is attainable, then the primary rule has excused real policy failures. In that case S-full is the better reading.

## M1.4 Failure, multi-fail and collapse (brief remedy a2)

- A clip **fails** if steps_c < F_c, so under the primary rule dance1 fails only if steps < 5336. The failed count of an eval is the number of failed clips, from 0 to 4.
- **Collapse:** an eval is a collapse if at least one clip has steps_c < 0.10 · F_c, that is, it fails within the first 10 % of its effective length.
- **Handling: score, do not invalidate.** Collapse evals are scored by R_full like any other eval. Their unsurvived frames contribute zero, which is the a1 correction. They are not dropped, imputed or capped. *Rationale:* invalidating collapses would remove exactly the events whose mis-scoring motivated M1. Scoring them through R_full is the only handling of a2 that needs no imputation choice. Collapse and multi-fail counts are reported per arm (M1.2) and have no role in the outcome.

## M1.5 Criterion (brief remedy a3) and outcome

Notation: x = H-A-xfer, s = H-A-scratch, m = H-M-xfer. mean = arm mean of the run AULC_full over its seeds. SE(X, Y) = sqrt(s_X²/n_X + s_Y²/n_Y), sample s.d. with ddof = 1 (n = 3 when the verdict is PASS).

Practical margin **δ = 0.03** on the R_full scale.

*Rationale for δ (fixed before any R_full computation; non-arm):* the PLAN's 1.2 × scratch was meant to detect a 20 % faster-learning gain. On the v1.0 scale, about 0.35 of the nominal R ≈ 0.508 is a near-constant offset from two saturated, non-discriminating terms: body_pos 0.0193 + body_lin_vel 0.0157 per step, divided by 0.1, pooled over all 111 failed=1 evals (brief §3.5, H4). The remaining part is about 0.158, and 20 % of that is 0.032. This gives δ = 0.03. The 1.2× ratio is kept as a sensitivity (below).

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
| S-δ10 | δ = 0.10 (the v1.0 1.2× bar expressed in absolute terms at R ≈ 0.5), primary metric | margin choice |
| S-ratio | v1.0 criterion text verbatim (1.2 × mean(s); KILL and SIGNAL_STRONG as PLAN §5) on AULC_full, primary metric | criterion form |

**Interpretation rule (pre-registered).** M1 reports a primary post-hoc outcome. It is described as **robust** only if S-excl, S-full and S-δ10 all give the same outcome class as the primary. Otherwise the report gives every outcome and calls the primary **fragile**. In either case the attempt-1 outcome (INCONCLUSIVE) remains the packet outcome of record.

## M1.6 Validity and M1 kill criterion

Every v1.0 check stays binding unchanged: deposit seal and members, tarball sha, B1-V-1..B1-V-5, scored-attempt and scored-exec selection. A v1.0 failure makes M1 BLOCKED as well.

M1 adds one per-eval check. A scored eval JSON is **M1-valid** only if all of the following hold:

1. `clips` has exactly 4 entries whose `name` set equals the 4 pinned clips;
2. each clip has a finite `norm_return` and an integer `steps` with 1 ≤ steps ≤ frames;
3. `frames` equals the pinned value (M1.2);
4. |mean of the clip `norm_return` − `summary.mean_norm_return`| ≤ 1e-9, so the stored summary is the v1.0 R_k built from these clips;
5. under the primary rule, dance1 steps ≤ 5336 (M1.3). Under S-full this condition is not applied. Under S-excl dance1 is ignored.

A run is M1-valid if all 10 of its scored eval points are M1-valid. **M1 kill criterion (BLOCKED):** M1 reports `verdict=BLOCKED`, outcome null, if any primary run (9) is not M1-valid. In that case `partial_outcome` follows the v1.0 rule: it is computed only when every primary arm has at least 2 M1-valid runs, and SIGNAL/SIGNAL_STRONG are capped to INCONCLUSIVE. This is stricter than the brief §5 item 7 rule ("fewer than 2 of 3 primary arms"), which it contains. Secondary and diagnostic arms are reported where valid and never gate.

## M1.7 Tool

- `spikes/B1/verdict_b1.py` **v1.1**. The default mode is v1.0, byte-for-byte in logic, so the attempt-1 line is reproducible. M1 runs only with `--amendment-m1 <this file>`, and the tool checks this file's sha256 against a pinned constant before computing anything.
- In M1 mode it writes **new** files: `spikes/B1/results-M1.json` and `spikes/B1/runs-M1.log`. It never writes `spikes/B1/results.json` or `spikes/B1/runs.log`. It prints exactly one line:
  `B1_M1_VERDICT label=post-hoc-M1 verdict=<PASS|BLOCKED> outcome=<SIGNAL_STRONG|SIGNAL|INCONCLUSIVE|KILL|null> robust=<true|false|null> failing=[…] aulc_full_HA_xfer=… aulc_full_HA_scratch=… aulc_full_HM_xfer=… diff_xs=… margin_xs=… se_xm=… S-excl=… S-full=… S-d10=… S-ratio=… v10_outcome=INCONCLUSIVE plan=1088752b amendment=<8> tool=<8>`
- Order: v1.1 is CPU-mock tested on synthetic fixtures only, including that default mode reproduces the v1.0 outcomes. Its sha256 is sealed in `logs/seal.log` **before** it opens the deposit. It is run by an agent process that is not an adjudicator (OVERLAY-001 rule 6; single-candidate packet, no adjudicator exists).

## M1.8 Red team and roles

| Slot | Binding |
|---|---|
| Amendment author, tool author, Orchestrator | Claude · claude-opus-5-5 (Claude Code) |
| Cross-family red team (amendment text, before seal) | `codex-astra` (OpenAI Codex · `gpt-6-astra`, codex-cli 0.163.0), effort **high**, `-s read-only -C <program root>`, objections only. It is told not to open the deposit or open tree and not to compute arm-level quantities under any candidate metric; its event log is audited for this. Dispositions are written by the Orchestrator in `spikes/B1/m1/REDTEAM-DISPOSITION.md`, and the Orchestrator rules on objections to its own draft (disclosed) |
| Verdict | `verdict_b1.py` v1.1 machine output (CPU), run by the Orchestrator's shell; no model judgment |

This red team also closes, for M1, the PLAN §9 gap (no red team on PLAN at seal). It does **not** retroactively red-team PLAN.md.

## M1.9 Labelling and reporting

- Every M1 artifact carries "post-hoc re-score (M1)". The report places the M1 outcome next to the attempt-1 INCONCLUSIVE. It never stands alone, and it is not a packet verdict or a decision change.
- All PLAN §0 disclosures carry over: the P5 caveat, the RT-4 waiver and the claim scope.
- A ledger observation is added (disclosure only, no reopen): D-005/D-006 were scored on the same survival-conditioned R.
- Any further action (b2 dance1 reference read, seeds, RT-b, eval-protocol changes) needs a further START.
