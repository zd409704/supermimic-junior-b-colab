# ISSUE-001: implementation sprint ran before brief, rubric and scheme

**Filed:** 2026-10-25 EDT, run-002-eval-scheme, by Claude Code (Orchestrator role). **Class:** process defect (not an in-run amendment; no contest was active).

**Observed defect.** run-001-scaffold built the attention decoder, baselines, entrypoints, notebook and runbook (orch/reports/STATUS-20261025-1419-EDT.md §3) before any brief with a rubric existed (method §4 Step 1: "No drafting of solutions begins until the brief exists"; §5 rubric before solutions). The design choices (descriptor features, d_model, one self-attention layer) were made and accepted by a single author, with no competing draft.

**Evidence.** `orch/reports/STATUS-20261025-1419-EDT.md`; `orch/reports/STATUS-20261025-1420-EDT.md` (owner process correction); `progress.md` rows S2–S3; no `brief.md` or `briefs/*` before 2026-10-25 14:2x EDT.

**Proposed amendment / disposition.** No change to the global text: the rule already exists. Program-level remedy: (1) freeze the scaffold as provisional scaffolding (SCHEME_PLAN P1); (2) open the B1-critical design choices as a two-author contest (D-DESC) before B0; (3) relay prompts launch evaluation packets before implementation packets.

**Observation that would show the remedy failed.** A later wake changes code before the P1 manifest is sealed, or B0 runs against a descriptor that no brief or decision covers.

**Contest impact.** None (no contest active). D-001 stays Provisional.

**Disposition:** applied at program level (deferred-to-next-packet for P1).
