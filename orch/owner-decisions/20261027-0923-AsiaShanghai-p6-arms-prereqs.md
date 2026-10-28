# Manager decision — P6d arms ready_prereqs build (option 1)

**Stamp:** 2026-10-27 ~09:23 Asia/Shanghai
**Authorized by:** Claude Manager (standing owner autonomy 2026-10-26: decide research drive without re-asking)
**Closes:** orch/reports/ASK-P6-ARMS-prereqs-20261026.md
**Context:** p6-b1-rt attempt 2/2 Fix#2 SCORED PASS (verdict_rt PASS; waived=[RT-4]; results 126c2334…; job c595ed91…; deposit 4e49c3e9…). Arms gate (1) met. ready_prereqs 2–4 unbuilt. gpu0 free.

## Decision — option (1) recommended

1. Next Orchestrator wake builds and seals against sealed spikes/B1/PLAN.md (1088752b…):
   - packets/P6/b1arms_driver.sh (PLAN §3–§8; CPU-mocked; sealed)
   - spikes/B1/verdict_b1.py (PLAN §5–§6; fixture-tested; sealed before arms deposit open)
   - Arms tarball + manifest + orch/jobs/p6-b1-arms/run.sh; fill upload[] shas; seal
2. Then set orch/jobs/p6-b1-arms.json state=READY with no new Manager START (934b3c9b item 4; 1855 item 2).
3. Venue xn-4090-gpu2; mutex gpu0; spend_cap 9.0 GPU-h unchanged. No Colab. No P4/P5 reopen. D-001 Provisional. P5 NO_GAIN / u_deficit caveat unchanged.
4. Claude 4 launches the Claude Code Orchestrator packet only; does not act as Orchestrator itself. After READY, relay START on xn-4090 per Job READY state machine.

## Out of scope

- Flipping arms READY before prereqs 2–4 exist
- SSH / GPU work from the Orchestrator box process

