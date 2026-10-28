# M1 amendment — red-team dispositions (Orchestrator; author rules on objections to its own draft, disclosed)

Reviewer: codex-astra (gpt-6-astra, high), read-only, binding `spikes/B1/m1/redteam/BINDING.md`.

## Round 1 — draft1 `86134d1d…` → `OVERALL: SEAL-AFTER-FIXES` (last message `redteam-r1-last-message.txt`)

**Audit (OVERLAY-002 rule 4):** the r1 event log has 12 command executions: reads of the draft, brief, PLAN, verdict_b1.py, IMPLEMENTATION_NOTES, OVERLAY-002 and benchmark.py, an `rg --files` that **excludes** `logs/**` and `orch/analysis/b1-eval-metric/**`, and one `sha256sum`. There was no command on `logs/xn4090`, the open tree, `evals.json` or `quantify.out`, and no computation of arm-level values. **PASS.** Note: during r1 the `verdict_b1.py` working copy was being edited toward v1.1. The reviewer may have read either version. This does not affect the amendment review.

| # | Sev | Disposition | Change in draft2 `fa900397` |
|---|---|---|---|
| 1 | BLOCKER | **Accepted.** No external grounding exists for δ | δ is relabelled an **exploratory, data-informed** threshold with no "20 % faster" reading. The heuristic and its limits (outcome-selected subset; the offset is not constant under R_full) are disclosed (M1.0, M1.5) |
| 2 | MAJOR | **Accepted** | M1.5 adds the algebraic bar comparison: M1 is generally the *lower* bar at R ≈ 0.5. S-δ10 is described as a fixed-margin sensitivity, and only S-ratio speaks to equivalence with the PLAN |
| 3 | MAJOR | **Accepted** | M1.2: R_full is defined only for steps ≤ F, with no clipping. The estimand is "first F benchmark transitions incl. the terminal one", subject to binary64 precision. M1.3: steps = W complete, < W fail, > W non-computable. Tool: `min()` removed |
| 4 | MAJOR | **Accepted** | "reference-defect frame" is removed. W is called an observed, outcome-derived common-failure cutoff, exploratory and conditional on H2 |
| 5 | BLOCKER | **Accepted** | M1.6: validity matrix (integrity I1–I3 on all 4 clips in every branch; computability C1–C2 per branch), frozen v1.0 selection with no fallback, each branch evaluated independently, v1.0 failure nulls all branch outcomes. Tool: implemented (`m1_branch` independent verdict/partial) |
| 6 | MAJOR | **Accepted** | robust = true/false/null over **all four** sensitivities, S-ratio included. Null if the primary is BLOCKED or any sensitivity is null. SIGNAL ≠ SIGNAL_STRONG. Wording narrowed to "agreement across the four one-factor sensitivities"; interactions are stated as not registered |
| 7 | MAJOR | **Accepted** | M1.6: v1.0 checks keep their scope, including B1-V-3 on diagnostics. Only the new M1 checks gate solely through the 9 primary runs |
| 8 | MINOR | **Accepted** | M1.6 Numerics: binary64, sorted clip order, bools rejected, malformed means invalid, collapse `10·steps < F` (integer), S-excl counts and S on 3 clips, denominators and retained seeds reported. Tool: implemented |
| 9 | MINOR | **Accepted** | M1.8: the review satisfies only M1's requirement, and the PLAN §9 timing gap stays on record. M1.6: partial outcome is informational, on the listed retained seeds, with no decision authority |

## Round 2 — draft2 `fa900397…` → `OVERALL: SEAL-AFTER-FIXES` (`redteam-r2-last-message.txt`)

**Audit:** the r2 event log has 9 command executions. They read the draft, the r1 message, the disposition, PLAN, IMPLEMENTATION_NOTES, OVERLAY-002, the brief, benchmark.py and `verdict_b1.py`, plus an `rg --files` excluding `logs/**`, `orch/**` and others. There was no access to `logs/xn4090`, the open tree, `evals.json` or `quantify.out`, and no arm-level computation. **PASS.**

r1 items 1–7 and 9: RESOLVED. Item 8: PARTIAL.

| # | Sev | Disposition | Change in draft3 `9425649f` / tool |
|---|---|---|---|
| R1-8 | MAJOR (partial) | **Accepted** | Tool: a non-object `summary` no longer raises (v1.1 hardening; it now gives R = None, which fails B1-V-1). C2 is extended to run AULC/R25/R100 and to all comparison quantities; arithmetic exceptions are caught and BLOCK the branch; JSON is written with `allow_nan=False`. M1.6 C2 row and M1.7 updated. Tests m04c added |
| 10 | MAJOR | **Accepted** | M1 mode requires exactly one `--deposit` whose full sha256 equals `f95155af…`, checked before extraction (M1.7; tests m04b) |
| 11 | MAJOR | **Accepted** | The attempt-1 record is loaded from the hash-verified `64644e3c…` file and copied verbatim (`v10_record`: line, outcome, per-run R/AULC/R25/R100, per-arm AULC). The line's `v10_outcome` comes from the record. The recomputation is labelled `v10_recomputed_*` with a discrepancy list (M1.7) |
| 12 | MAJOR | **Accepted** | Both outputs are checked against all protected files by realpath and `samefile`; out ≠ runs-log; checked before scoring (M1.7; test m04 incl. cross-swap, `..` alias and symlink) |

## Round 3 — draft3 `9425649f…` → `OVERALL: SEAL-AFTER-FIXES` (`redteam-r3-last-message.txt`)

**Audit:** 10 command executions. They read the draft, the earlier messages, the disposition, OVERLAY-002, IMPLEMENTATION_NOTES, PLAN, `verdict_b1.py`, benchmark.py and the brief, plus an `rg --files` excluding `logs/**` and `orch/analysis/b1-eval-metric/**`. There was no forbidden access and no arm-level computation. **PASS.**

Round-2 #10 and #11: RESOLVED. R1-8 and #12: PARTIAL. One NEW MINOR. No objection to the amendment's scientific content remains open; all r3 items are tool robustness.

| # | Sev | Disposition | Change in draft4 `d04aca27` / tool |
|---|---|---|---|
| R1-8 | MAJOR (partial) | **Accepted in part** | Tool: arithmetic guards at point, run, arm (`m1_arm_stats_safe`) and comparison level. Every operand (incl. S-ratio thresholds and the `mean(m) − 2SE` bound) is validated before classification. Comparison-level C2 nulls both outcome and partial. Secondary-arm C2 is informational. Text: M1.6 C2 row. Tests m20 (direct). **Declined:** wrapping the v1.0 recomputation in new exception handling. That path is kept verbatim and is fail-closed: an exception gives no M1 output (M1.7). An M1-only overflow cannot occur when v1.0 does not overflow, because R_full ≤ \|norm_return\| · 1 |
| #12 | MAJOR (partial) | **Accepted** | `samefile` check between `--out` and `--runs-log`; test m19 (hard link) |
| NEW-5 | MINOR | **Accepted** | Discrepancies are now compared on every copied field, with missing entries listed; recomputed values are kept under `v10_recomputed` (M1.7) |

Round 4 is the **final** round. Any remaining MINOR objections get a disposition without a further round. Any BLOCKER or MAJOR stops the seal pending a fix or a Manager decision.

## Round 4 (final) — draft4 `d04aca27…` → `OVERALL: SEAL-AFTER-FIXES` (`redteam-r4-last-message.txt`)

**Audit:** 13 command executions. They read the draft, earlier messages, the disposition, PLAN, the brief, IMPLEMENTATION_NOTES, OVERLAY-002, benchmark.py, `verdict_b1.py` and `AGENTS.md` (absent), plus an allow-listed `rg --files`. There was no forbidden access and no arm-level computation. **PASS.**

Round-2 #10, #11, #12 and round-3 NEW-5: RESOLVED. **No open objection against the amendment text.**

| # | Sev | Disposition | Change (tool only; amendment text final = draft4 `d04aca27…`) |
|---|---|---|---|
| R1-8 | MAJOR (partial; tool) | **Accepted, fixed in the tool.** Also accepted: the r3 disposition's magnitude argument ("M1 overflow implies v1.0 overflow") was wrong, because completion scaling can increase between-seed dispersion. That argument is withdrawn | `m1_arm_stats_safe` returns the full arm schema after an aggregation error: the actual retained seeds and denominators, with statistics null. The writer serialises it (`fmt(None)` → null). Test m21 covers the end-to-end path (primary-arm OverflowError → BLOCKED artifact with outcome and partial null in every branch, no crash). This matches M1.6 as already written (primary-arm aggregate C2 → BLOCKED, outcome and partial null), so **no text change** |
| NEW-6 | MINOR (tool) | **Accepted** | Placeholder replaced by the sealed amendment sha256 at the tool seal step. Matching and mismatching amendment handling tested on synthetic fixtures (`B1_M1_AMENDMENT=<sealed file>`) before the deposit is opened |

**Disclosure:** the final tool fix for R1-8 and the sha pin were made after round 4 and were **not** re-reviewed by codex. They are covered by the CPU mock tests (m21, m03) and are within the stated stopping rule (fix, then seal). The amendment text sealed is exactly the draft4 the reviewer saw.
