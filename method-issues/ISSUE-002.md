# ISSUE-002: catalog CLI for Claude-family slots not usable from an Orchestrator subprocess

**Filed:** 2026-10-25 EDT, run-003-p1-freeze, by the Orchestrator (Claude Code, claude-opus). **Class:** 0 (infrastructure) for this run; catalog/invocation question for the method maintainer.

**Observed defect.** Catalog A.6 binds `claude-opus` / `claude-sonnet` to `claude --model …`. Launched from the Orchestrator's own shell, that CLI exits with `Not logged in · Please run /login` (`logs/p1/probe/sonnet-probe-attempt1-20261025-1443.log`). The Orchestrator itself runs authenticated because the relay launches it with credentials that child shells do not inherit. The Orchestrator did not copy credentials out of other processes to work around this.

**Run-level handling.** Claude-family slots (Author A, reviewer of X, spike runner, fixes author) ran as Claude Code Agent-tool subagents of the Orchestrator session: fresh context, same model IDs. Recorded in `roster.md` and under Confounds in `packets/P1/ddesc/decision.md`. Subagent transcripts were copied to `logs/p1/ddesc/transcripts/` for the §11.6 audit.

**Proposed amendment.** Either (a) list "Claude Code Agent-tool subagent (model=opus|sonnet)" as an accepted invocation of the Claude catalog rows, with the audit path stated; or (b) have the relay launcher export the credentials Claude-family children need, so that the catalog CLI works from Orchestrator subprocesses.

**Observation that would show the fix failed.** A later P-packet probe again logs `Not logged in` for the catalog CLI, and no accepted alternative invocation is on record.

**Contest impact.** None on scores (same model family and IDs). Disclosed as Confound 1 in the D-DESC decision.

**Disposition:** applied-in-run (Class 0 substitution, disclosed); catalog question deferred to the method maintainer.
