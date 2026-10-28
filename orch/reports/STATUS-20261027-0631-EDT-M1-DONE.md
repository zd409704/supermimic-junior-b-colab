# Program STATUS - supermimic-junior-b-colab

**Stamp:** 20261027-0631-EDT
**Decision cap:** Provisional

## Headline

**M1_REScore_DONE — HOLD.** Class-2 amendment M1 (post-hoc re-score of the sealed B1 arms deposit, CPU only) is complete. The **post-hoc (M1) outcome is KILL, robust=true**: under the completion-aware R_full, H-A-xfer AULC 0.360 < H-A-scratch 0.419 < H-M-xfer 0.477, and all 4 pre-registered sensitivities give KILL. **The outcome of record stays attempt-1 INCONCLUSIVE.** The arms CLOSE `5d8cf393…` stands and is not superseded.

Caveat: the KILL fires on the PLAN §5 no-margin leg (x − s = −0.059, under 1 SE) and on the x < m − 2SE leg by 0.008. Read it as "no evidence for the B1 transfer mechanism under a completion-aware metric", not as strong evidence of harm. Report: `orch/reports/VERDICT-P6-b1-arms-M1-posthoc-20261027.md`.

| Item | Path | sha256 |
|---|---|---|
| **M1 report** | `orch/reports/VERDICT-P6-b1-arms-M1-posthoc-20261027.md` | `e1d9d11a0bab58a78f57db4761de2d0238a84ac5554b6abcad2ed88a6d4ebf04` |
| M1 results (post-hoc) | `orch/reports/VERDICT-P6-b1-arms-M1-posthoc-results.json` | `b3a995e83b379ac49c0576088814c37741ad0a53deb2da61a34a400d95e87373` |
| Amendment M1 (sealed, a-w) | `spikes/B1/AMENDMENT-M1-eval-metric.md` | `d04aca276c6042d7bc56c63bb6a328d62fef451290047d310b64d065475abdfe` |
| Tool v1.1 (sealed before open) | `spikes/B1/verdict_b1.py` | `cd32a0ac2340b5b2e4db6ce969914870305ef38c4694652c0c3d3bb2465f8993` |
| Red-team dispositions (codex-astra high r1–r4) | `spikes/B1/m1/REDTEAM-DISPOSITION.md` | `a29a5c51c668a02c1dc5609633e39f0df8befe4ea0995b30ca70b9a8a44137f2` |
| Overlay (new, append-only) | `method/local/OVERLAY-002-posthoc-rescore.md` | `f28c558fd18a9894977bcf5c6c422f1098a3b4297c5838a6b55996f603415ab9` |
| Ledger (OBS-001 D-005/D-006 disclosure; OBS-002 M1) | `program-ledger.md` | `406871ae59083d35056140ce5de81d787e7e0d0372f2018fd3f00fb19c82dec2` |
| Attempt-1 record (unchanged) | `orch/reports/VERDICT-P6-b1-arms-attempt1-results.json` | `64644e3c594de07a6819b685b1d0f956849eaafbff56b3ad87eab0cbb70c1403` |
| Deposit (RO, unchanged) | `logs/xn4090/2026-10-27/b1arms-20261027-0935.tgz` | `f95155af47357026d69f7c06f01c3d20ca806aa3378fce125322001d1094126d` |
| PLAN (not edited) | `spikes/B1/PLAN.md` | `1088752ba26a8798d721aa93d6e10d1b7bdb7fb924d9d72879acc78d8c2304c8` |
| M1 START | `orch/owner-decisions/20261027-1810-AsiaShanghai-B1-M1-eval-metric-START.md` | `73ea581bb89e3025304994c200394d2621e64a02407fa8ae6f525d67caffc9b6` |

## Jobs

| job_id | state | venue | mutex | artifact | note |
|---|---|---|---|---|---|
| p6-b1-arms | SCORED/CLOSED | xn-4090-gpu2 | (released) | results `64644e3c…` | PASS/INCONCLUSIVE a1 **of record**; CLOSE stands |
| p6-b1-rt | SCORED | xn-4090-gpu2 | (released) | results `126c2334…` | PASS a2/2 (RT-4 waived C2) |
| b1-eval-metric-followon-brief | SEALED | CPU Claude Code | — | `01ecb8c1…` | ack |
| b1-m1-eval-metric | **DONE / HOLD** | CPU Claude Code | — | results-M1 `b3a995e8…`, report `e1d9d11a…` | post-hoc KILL robust; Provisional |

## Disclosures

- The red team (codex-astra high, read-only) ran 4 rounds, each ending SEAL-AFTER-FIXES. No text objection was open at r4. One tool MAJOR was fixed after r4 and not re-reviewed (covered by CPU test m21). The author ruled on objections to its own draft. The audit of every round found no deposit or open-tree access.
- The author knew the collapse-direction descriptive results before pre-registration (amendment M1.0). W = 5336 and δ = 0.03 are exploratory, but neither drives the KILL (S-full has no W; the KILL rule uses no δ).
- H2 (dance1 frame ~5336 attainable?) is unverified. Optional b2 CPU-only reference read on the xn-4090 host is proposed, **not executed** (needs a START).

## Next (Manager)

HOLD. Possible decisions, none taken here:
1. how to cite B1 (the attempt-1 INCONCLUSIVE of record with the M1 post-hoc KILL beside it);
2. whether to retire the B1 attention-transfer claim;
3. whether to START b2 (H2 check);
4. whether a sealed amendment should re-score D-005/D-006 (disclosed in OBS-001; not reopened).

## Hard non-touch (unchanged)

No xn-4090 GPU START, no Colab, no attempt 2, no seed add, no P4/P5 reopen, no PLAN.md in-place edit, no depth-3 build on B1.
