# ASK — P6d `p6-b1-arms` READY blocked on unbuilt prerequisites (Provisional)

**Stamp:** 2026-10-26 21:22 EDT. **From:** Orchestrator (claude-opus-5-5), P6 a2 score wake. **To:** Manager / owner relay.

## Facts
- `p6-b1-rt` attempt 2/2 is SCORED **PASS** (RT-4 waived under C2 `32143be4…`). Report: `orch/reports/VERDICT-P6-b1-rt-attempt2-20261026.md`. Arms gate (1) is met.
- `orch/jobs/p6-b1-arms.json` (`9f71dd1e…`, sealed DRAFT) says not to flip to READY until **every** `ready_prereqs` item is done and sealed. Items 2–4 are not built:
  2. `packets/P6/b1arms_driver.sh` (B1 PLAN §3–§8, CPU-mocked, sealed). Absent.
  3. `spikes/B1/verdict_b1.py` (PLAN §5–§6, fixture-tested, sealed before the arms deposit is opened). Absent.
  4. Arms tarball, manifest and `orch/jobs/p6-b1-arms/run.sh`. Absent; upload shas "TBD".
- Item 5 (gpu0 mutex free) is met.

## Decision taken (within existing authority)
The arms job stays **DRAFT** and its bytes are unchanged. If it were set READY now, the relay would get a job with no uploadable payload, and the job's own sealed gate would be broken.

## Ask (one line answer)
- **(1, recommended):** The next Orchestrator wake builds prereqs 2–4 against sealed `spikes/B1/PLAN.md` (`1088752b…`): driver, CPU mock, verdict tool on fixtures, tarball, manifest and run.sh, each sealed. It then sets `p6-b1-arms` READY with no new Manager START (934b3c9b item 4; 1855 item 2).
- (2) Other instruction.

Unchanged: no P4/P5 reopen, D-001 Provisional, P5 NO_GAIN / u_deficit caveat, venue xn-4090-gpu2.
