# OVERLAY-002: post-hoc labelled re-score of a sealed deposit (append-only)

**Extends:** global METHOD `pins/orchestrating-ai-research-teams.v1.1-9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0.md`, sha256 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0`.
**Added:** 2026-10-27 EDT, packet B1-M1 (Class-2 amendment M1, `orch/owner-decisions/20261027-1810-AsiaShanghai-B1-M1-eval-metric-START.md` sha256 `73ea581bb89e3025304994c200394d2621e64a02407fa8ae6f525d67caffc9b6`). **Status:** Provisional rule special. It does not replace any global rule.

**Why this is a special.** Global §10.4 allows a Class-2 change only if the affected step has not started. Otherwise the change is deferred to the next packet. B1 scoring has already run: the attempt-1 machine line is sealed. The Manager has signed a Class-2 option to change the scoring input for a **separate, post-hoc labelled** re-score of the same sealed deposit. The global text has no rule for a second scoring pass over data that was already observed, so this overlay states one. It does not make the post-hoc pass a §10.4 in-run amendment of the original scoring.

**Rules.**
1. **Original stands.** The original machine verdict line, results JSON and decision stay on record unchanged and are not superseded. The post-hoc output is written to new files. It never overwrites the original's `results.json` or `runs.log`.
2. **Label.** Every post-hoc artifact (amendment, tool output line, results JSON, report) carries the label `post-hoc re-score (<id>)`. A post-hoc outcome may be cited only next to the original outcome, never alone and never as the packet verdict.
3. **Pre-registration before computation.** The metric, every data rule (clip handling, invalid/collapse handling), the criterion and every sensitivity analysis are sealed in an amendment file (sha256 in `logs/seal.log`, `chmod a-w`) **before** any arm-level quantity is computed under the new metric. Descriptive per-eval statistics that were already sealed earlier are disclosed in the amendment as prior knowledge of its author.
4. **Cross-family red team before seal.** A different model family from the amendment author (A.6 secondary preference: `codex-astra` high) reviews the amendment text before seal, objections only. The reviewer is told not to compute arm-level quantities under any candidate metric. Its event log is audited for this before seal. Dispositions are written by the Orchestrator and disclosed. If the red team is unavailable, the amendment is not sealed without an explicit Manager waiver.
5. **Tool sealed before opening.** The scoring tool is versioned. The original logic is kept behind a flag and is the default. The tool is CPU-mock tested and its sha256 is sealed before it reads the deposit. It is run by an agent process that is not an adjudicator (OVERLAY-001 rule 6).
6. **Cap.** The decision cap stays at Provisional (single-candidate, where the original was). A post-hoc re-score cannot raise the depth or lock status of the original decision.

Do not fork a full local copy of the global method.
