You are a red-team reviewer (objections only) for a pre-registered experiment PLAN. Do not rewrite the plan; do not propose new science. Read-only.

Program root: /srv/claude/research/supermimic-junior-b-colab
PLAN under review (draft 2, not yet sealed): spikes/B2/PLAN.md

You may read these context files:
- docs/SCHEME_PLAN.md (§1 P5, §3 B2 and combined gate, §7, §8)
- spikes/B0/PLAN.md (sealed B0 PLAN incl. Amendment v1; definitions the B2 PLAN references by ID)
- orch/reports/DECISION-RV-BLK-20261026.md
- orch/reports/VERDICT-P4-b0-attempt1-relaunch3-20261026.md and orch/reports/VERDICT-P4-b0-attempt1-relaunch3-results.json (P4 machine verdict and per-attempt M-10 numbers)
- logs/xn4090/2026-10-26/open-b0-20261026-0919/ (opened P4 deposit tree; eval JSONs, sidecars, meta)
- code/eval_entry.py, code/attention_policy.py, code/mlp_baseline.py, code/train_entry.py, configs/b0_microbench.yaml
- packets/P4/upstream-ro/SuperMimic-Reproduced/src/supermimic/eval/benchmark.py
- orch/jobs/p4-b0-attempt1.json, orch/jobs/p4-b0-attempt1/run.sh
- method/local/OVERLAY-001-owner-colab-runner.md, /srv/claude/research/METHOD/venues/xn-4090-gpu2.md

Constraints the PLAN must respect (given by the human-lead side; do not object to these themselves):
- P4 is closed PASS/NONINFERIOR and must not be re-scored; spikes/B0/PLAN.md must not be modified.
- B2 thresholds are to be frozen in this PLAN using P4 M-10 data (data-informed is required; disclosure of that is required).
- Mask-seed fairness (RV-2) must be settled, not assumed.
- Equal env steps / updates (RV-8) for new trainings; R_H (cumulative) preferred for retention to match B0.

Check for:
1. Contradictions with SCHEME_PLAN §3, RV-1/RV-2/RV-8, or the sealed B0 PLAN definitions it references.
2. Gaps that would force the runner or the verdict script to make a design choice, or that make the machine verdict non-deterministic / not computable from the named fields.
3. Ways the runner or the verdict script could select runs or cherry-pick.
4. Internal inconsistencies (numbers, names, paths, keys, commands that would not work with the frozen code as written), including whether the mask-fairness finding in §3 is correct against the code.
5. Mis-statement of P4 evidence (check the numbers in §5.4/§5.5 against the results JSON).
6. Whether the threshold freeze (§5.4) is honest and defensible given the data were seen.

Output: a numbered list of objections. Each: severity (BLOCKER / MAJOR / MINOR), PLAN section, the problem in 1-3 sentences, and the smallest fix. End with one line: `REDTEAM-RESULT: SEAL-OK` (no BLOCKER and no MAJOR), or `REDTEAM-RESULT: REVISE`.

Round 2. Your round-1 objections are in spikes/B2/redteam/redteam-r1-last-message.txt and the Orchestrator's dispositions in spikes/B2/redteam/REDTEAM-DISPOSITION.md; draft 1 is spikes/B2/redteam/PLAN-draft1-65cae1df.md. For each round-1 objection state RESOLVED or NOT RESOLVED (one line each), then list any NEW objections in the same format. End with the same REDTEAM-RESULT line.
