# Owner decision — 2026-10-27 ~18:00 Asia/Shanghai — SuperMimic B1 eval-metric / clip-failure follow-on brief START

**Decision:** START a sealed **follow-on brief** for supermimic-junior-b-colab focused on **evaluation metric validity and clip-failure** after P6d B1 arms CLOSED PASS/INCONCLUSIVE. Do **not** relaunch arms, add seeds, reopen P4/P5, or amend B1 PLAN metrics until this brief is sealed and Manager signs a later Class-2 / PLAN amendment if any.

**AuthorizedBy:** owner chat reply to Manager widget (2026-10-27 ~18:00 Asia/Shanghai): prefer SuperMimic follow-on on eval metric / clip-failure. Prior close: orch/owner-decisions/20261027-1745-AsiaShanghai-p6-arms-CLOSE-INCONCLUSIVE.md sha256 5d8cf393044efcab8ab899ae9c51a463f7a2214643ea7c87eddf34127c4d2ebd.

**Program:** /srv/claude/research/supermimic-junior-b-colab/

## Intent

Claude 4 schedules Claude Code as Orchestrator to produce `docs/FOLLOWON_BRIEF_B1_EVAL_METRIC.md` (Provisional): diagnose the STATUS observation that every arms eval has failed >= 1 of 4 clips, R_k stays flat near 0.5, and all-failed evals score higher; propose measurement fixes and whether a sealed PLAN amendment is warranted. No GPU arms re-run this packet.

## Required deliverable (seal)

`docs/FOLLOWON_BRIEF_B1_EVAL_METRIC.md` (+ SHA256SUMS entry), covering:
1. Restate sealed machine verdict (PASS/INCONCLUSIVE) with results/report shas; INCONCLUSIVE stands — this brief does not reopen the arms outcome.
2. Quantify the clip-failure / flat-R_k / all-failed-higher observation from attempt-1 results JSON and open deposit tree (read-only). Cite concrete counts per arm/seed/eval step where possible.
3. Hypotheses (labelled [PROP]/INF]): metric definition vs harness mask vs retarget QA (RT-4 waived) vs reward scaling vs eval horizon.
4. Candidate remedies ordered: (a) metric redefinition / invalid-eval handling; (b) clip set / mask changes; (c) more seeds (only with amendment); (d) RT-b better references; (e) no action / accept INCONCLUSIVE. Each with Class (0/1/2), CPU vs xn-4090, and whether it needs a sealed PLAN amendment before any re-score.
5. Explicit non-goals: no attempt 2, no Colab, no P4/P5 reopen, no seed add without amendment, no depth-3 build on B1 without further signature.
6. Recommendation: Manager next step (one paragraph).

## Constraints

- Stay under /srv/claude/research/supermimic-junior-b-colab/ for writes.
- Global METHOD CURRENT boot + method/local analyze.
- Provisional; home-humanoid / plant-class wording; no commercial product brands.
- CPU-only. No SSH. No xn-4090 GPU START. No Colab.
- Deposit tgz f95155af… and open tree remain read-only; do not retrain.

## Success

Claude 4 ACKs, Claude Code seals the brief, updates STATUS, reports MATERIAL path + sha to Manager. Then HOLD pending Manager amendment/START decision.
