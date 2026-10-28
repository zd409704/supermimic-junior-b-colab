# 20261027-0607-EDT — B1 eval-metric follow-on brief SEALED

**Milestone:** `FOLLOWON_BRIEF_B1_EVAL_SEALED path=docs/FOLLOWON_BRIEF_B1_EVAL_METRIC.md sha=01ecb8c13bef70c30212573a90da79654e12578830a5a02efacbf5e2f25a752d`
**Seal:** `logs/seal.log` SEAL line at 2026-10-27T10:07:18Z. `docs/SHA256SUMS` entry added. File is a-w.
**Authority:** START `02f94992…` (1800). CLOSE `5d8cf393…` (1745) stands. PLAN `1088752b…` unchanged.
**Method boot:** CURRENT → v1.1 `9bdc872e…` (sha verified). method/local README + OVERLAY-001 read. No new overlay is needed (single-author, non-contest diagnostic packet). A.7 allocation is not applicable; `roster.md` is untouched. All 11 governing input shas were verified at boot and match.
**Decision cap:** Provisional. CPU only. No GPU, Colab, SSH, attempt 2, seeds or P4/P5 reopen.

## Findings (summary; the brief governs)
- INCONCLUSIVE is restated and not reopened.
- **H1 (primary):** upstream `norm_return` divides by *survived* steps, so early collapse raises R. Of 140 evals, failed=4 gives R 0.588 at 5 % coverage, versus failed=1 at R 0.508 and 97 % coverage. r(R, coverage) = −0.56.
- **H2:** dance1 fails at the identical step 5336 in 116/140 evals across all arms. This is a reference-side floor (RT-4 waived), not verifiable on the box.
- **H4:** R is compressed by a saturated body_pos term and a drifting global-root term. The 1.2× ratio test on this offset metric is near-unattainable.
- Collapses (failed ≥ 2): H-A-xfer 11/30, H-A-scratch 5/30, H-M-xfer 3/30.
- **Disclosure:** P4 (112/112) and P5 (168/168) mask-0 clip evals all failed (median step ~60), so D-005/D-006 were scored on the same R. Not reopened.
- Arm-level alternative metrics were deliberately not computed, so a future amendment stays blind to its effect on the arm comparison.

## Recommendation
HOLD. Optionally sign the Class-2 amendment M1: a CPU post-hoc re-score with a completion-aware metric, pre-registered and red-teamed by codex-astra high before computing. Optionally authorise a CPU-only read of the dance1 reference on the xn-4090 host. Defer seeds and RT-b. Add a ledger observation for D-005/D-006.

## Artifacts
| Path | sha256 |
|---|---|
| docs/FOLLOWON_BRIEF_B1_EVAL_METRIC.md | 01ecb8c13bef70c30212573a90da79654e12578830a5a02efacbf5e2f25a752d |
| orch/analysis/b1-eval-metric/quantify.py | ebdc86d2b0f480beda73d6c8d31078773dd3b1ca480450cdec0875f83acbe74d |
| orch/analysis/b1-eval-metric/quantify.out | 9aa84c7e7966cc7fefbd917844c14ceb6ae8aad324979c5c3456b11e4909cb91 |
| orch/analysis/b1-eval-metric/evals.json | 743e7db85bb8b8f62181edc0f17cf91d3e1972dcc12844ccb0ed12898b9c2c42 |
| orch/analysis/b1-eval-metric/p4p5_failstats.out | 4d677eecba490832db9efba6c25625266f311413e1402a04e9a5384b13e20c0d |

## Notes
- The brief header says "~06:20 EDT". The actual seal was 06:07 EDT (10:07:18Z). Local-time labels are display-only (§10.3); seal.log UTC governs.
- The program ledger was not edited. The ledger entry is a Manager proposal (brief §7).
- Deposit tgz and open tree untouched (open tree still a-w).
