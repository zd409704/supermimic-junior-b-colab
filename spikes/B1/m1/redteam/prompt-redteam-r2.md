You are a cross-family red-team reviewer (objections only) for a pre-registered evaluation amendment in a robotics research program. You do not write files. Your deliverable is your final message.

Working directory: the program root (read-only sandbox).

## Document under review
`spikes/B1/m1/redteam/AMENDMENT-M1-draft2-fa900397.md` (sha256 fa900397e7515fe2bc449a6453574fd1f0132598380b34379ca341287cbe9b98). It is a Class-2 amendment that pre-registers a completion-aware metric (R_full), a dance1 clip rule, a collapse rule, a criterion and sensitivities for a POST-HOC re-score of an already-scored, sealed deposit. The original verdict (PASS/INCONCLUSIVE) stays on record.

## Context you may read
- `spikes/B1/PLAN.md` (original pre-registered plan; §5 metric/criteria)
- `docs/FOLLOWON_BRIEF_B1_EVAL_METRIC.md` (diagnostic brief that motivates the amendment; §2-§5)
- `spikes/B1/verdict_b1.py` (v1.0 scoring tool) and `spikes/B1/IMPLEMENTATION_NOTES.md`
- `method/local/OVERLAY-002-posthoc-rescore.md`
- `packets/P6/upstream-b1/SuperMimic-Reproduced/src/supermimic/eval/benchmark.py` (how norm_return/steps/frames are produced)

## Hard restrictions (audited)
- Do NOT open, list or extract `logs/xn4090/` (the deposit tgz or any `open-*` tree), and do NOT open `orch/analysis/b1-eval-metric/evals.json` or `quantify.out`.
- Do NOT compute AULC, R_k, or any arm-level or run-level number under R_full or any alternative metric. The point of pre-registration is that no one sees the effect of the candidate metric before it is sealed.

## What to do
Find defects that would make the amendment invalid, biased, ambiguous, or non-implementable, before it is sealed. In particular check:
1. Is R_full = norm_return · min(steps,F)/F correct given benchmark.py, and exactly computable from the stored fields?
2. Is the dance1 window rule (W = 5336, chosen from an observed pooled failure frame) defensible, exact, and non-arm-dependent? Is the non-computable case handled?
3. Is the collapse rule (score, not invalidate) and the M1 kill criterion sound?
4. Is the criterion (difference margin delta = 0.03 with a 2·SE(x,s) floor) justified independently of arm results? Is it lower or higher a bar than the PLAN's 1.2x ratio? Is there garden-of-forking-paths or author-foreknowledge bias (see M1.0)? Are the sensitivities and the "robust" rule adequate?
5. Labelling/governance: does anything let the post-hoc outcome supersede or be confused with the original verdict?
6. Ambiguities an implementer could resolve two ways (ordering, float comparisons, n, ddof, missing data).

## Output format
A numbered list of objections. For each: severity (BLOCKER / MAJOR / MINOR), the section (M1.x), the defect, and a concrete fix. End with one line: `OVERALL: SEAL-OK` or `OVERALL: SEAL-AFTER-FIXES` or `OVERALL: DO-NOT-SEAL`.

## Round 2
This is round 2. Your round-1 objections are in `spikes/B1/m1/redteam/redteam-r1-last-message.txt`. The author's dispositions are in `spikes/B1/m1/REDTEAM-DISPOSITION.md`. For each round-1 objection, state whether draft2 resolves it (RESOLVED / PARTIAL / NOT RESOLVED), then list any NEW objections in the same format. The same hard restrictions apply. You may also read the draft tool `spikes/B1/verdict_b1.py` (functions `m1_*`) to check that it implements M1.2–M1.6 as written, but do not run it on any deposit.
