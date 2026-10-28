# P4 PRESTART update — PS-3 cleared by Amendment v1

**Stamp:** 2026-10-26 02:25 EDT (America/Toronto); owner authority Asia/Shanghai 2026-10-26 ~14:25.
**Binding:** `spikes/B0/PLAN.md` base sha256 `ed6b6a54a860bbfc67d7c822b5394804b8d408f6aae57fbeb118d2ea63c52557` + Amendment v1; full-file sha256 after append `356c389f4c2efd47249f741b23f69bde19043a0ed8dc6e2c637abe397b9e145a`.
**Prior record:** `packets/P4/PRESTART.md` (PS-3 was BLOCKED_ON_SIGNATURE) remains historical and byte-identical.

## Gate table (supersedes PS-3 row only)

| Gate | State | Evidence |
|---|---|---|
| PS-1 | true | unchanged — see PRESTART.md |
| PS-2 | true | unchanged |
| **PS-3** | **true** | Amendment v1 Option **(i)** omit clip clause; M-6=null; stability confound disclosed. No CR-B0-2. |
| PS-4 | true | unchanged (F-5) |
| PS-5 | true | unchanged |

**F-1:** confirmed unsuitable; harness stop; CR-B0-1 **not** rebuilt (tarball `763867682e3cfa05ca8eb6382ffc9124be2347b898531c60b904061776c33bff`).

**Result:** all PS-1…PS-5 hold. P4 attempt 1 still requires a sealed runner packet at READY **and** an explicit Manager/owner run order. No GPU spend in this wake.
