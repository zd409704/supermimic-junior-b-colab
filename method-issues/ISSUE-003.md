# ISSUE-003: spike runner resolved plan gaps itself instead of writing BLOCKED.md

**Filed:** 2026-10-25 EDT, run-003-p1-freeze, by the Orchestrator. **Class:** process defect (§12.2); observed after the run, no re-run needed.

**Observed defect.** `spikes/D-DESC/deviations.md` lists 7 points the sealed `spikes/D-DESC/PLAN.md` did not specify (synthetic reference mass, stage indexing, mirror-map details for q_def, F2 inertia scaling, timing protocol, inertia grouping, armature formula). The runner chose values and continued. §12.2 says a plan gap means stop and write `BLOCKED.md`.

**Evidence.** `spikes/D-DESC/deviations.md`, `spikes/D-DESC/runs.log` (single execution, PASS), Orchestrator check in `packets/P1/ddesc/decision.md` Amendment v1.1. The armature "reconstruction" was shown to be identical to the pinned formula.

**Assessment.** None of the gaps touches a binding threshold or the mechanism. Several of them (mass, mirror map) affect fixture values of F3/F4. The PLAN was under-specified (Orchestrator defect), and the runner's choices were transparent (good), but the method rule was not followed.

**Proposed amendment.** (1) Orchestrator side: spike PLANs must list every fixture constant a check depends on (masses, mirror maps, scaling rules). (2) Method side: allow a runner to proceed on a plan gap only when the gap affects a *reported* quantity, not a binding check, and require `deviations.md` to classify each gap as binding/non-binding.

**Observation that would show the fix failed.** A later spike's deviations again contain choices that feed a binding check without a BLOCKED stop.

**Contest impact.** None on adjudication (the spike follows it). D-DESC stays Provisional.

**Disposition:** deferred-to-next-packet (PLAN-writing practice applied from P2 on; method text question to the maintainer).
