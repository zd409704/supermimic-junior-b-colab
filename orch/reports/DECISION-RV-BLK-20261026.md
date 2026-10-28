# Decision note — RV / BLK / P3 unblock (2026-10-26)

**Stamp:** 2026-10-26 00:36 EDT
**Decision cap:** Provisional (operational accepts; not a Lock of D-001)
**Authority:** Owner delegated to Claude Manager 2026-10-26 ("decide without asking"). Research Human lead Peter remains final on brief Lock disputes.

## Accepts (unblock P3)

| ID | Ruling | Notes |
|----|--------|-------|
| **RV-1** | ACCEPT | Non-inferiority B0 gate as in `docs/SCHEME_PLAN.md` / design scheme. |
| **RV-2** | ACCEPT | B2 mask-fairness arms as specified. |
| **RV-8** | ACCEPT | Equal env steps / updates as primary budget. |
| **BLK-12** | ACCEPT | Paid GPU budget for later P4/P5/P6d at disclosed draft (~17–20 L4 GPU-h equivalent). Prefer XN-4090-GPU2 via Mac mini Job READY when a sealed PLAN names that venue; Colab L4 remains OK for short smoke. **Do not spend until a sealed PLAN asks.** |
| **BLK-11** | ACCEPT | Private runtime-only retargets of the licensed motion are acceptable for this program. |
| **P6a** | APPROVE | CPU-only B1 asset readiness may run in parallel when capacity allows; optional; does not block P3. |
| **D-DESC re-adjudication** | DECLINE | Keep existing 5.0 decision (`packets/P1/ddesc/decision.md`). |

## Deferred (not now)

| ID | Ruling | Notes |
|----|--------|-------|
| **RV-7 / BLK-10** | DEFER Lock of D-001 | Keep Provisional depth-2 path. Sign the depth-2 raise in the B1 brief when the B1 packet starts (not now). |

## Carry into P3 PLAN (mandatory)

When drafting `spikes/B0/PLAN.md`:
- Use **cumulative / episode-total return** for any train-return gate (RCA option B1 spirit; see `orch/reports/P4-RCA-20261026.md`).
- Report **survival + cumulative** in eval (RCA B3).
- Disclose A1 confounds (P-4 per-step `norm_return` artifact on sealed P2).
- Do **not** silently rewrite the sealed P2 smoke PLAN (`spikes/B0-smoke/PLAN.md`).

## Prior close

P2 closed under A1: `orch/reports/DECISION-A1-P2-close-20261026.md`. Machine harness remains FAIL failing_ids=[P-4] (disclosed).

