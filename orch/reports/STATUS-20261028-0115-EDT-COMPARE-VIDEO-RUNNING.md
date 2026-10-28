# Program STATUS - supermimic-junior-b-colab

**Stamp:** 20261028-0115-EDT
**Decision cap:** Provisional

## Headline

**P6 B1 arms compare-video — RUNNING on xn-4090-gpu2 (RE-RELAY).** Manager RE-RELAY `orch/owner-decisions/20261028-1312-AsiaShanghai-B1-arms-compare-video-RE-RELAY.md` sha256=`aae728d10a97cb351604c400df19ecd7af27ec26b9351a2da75eaeb3293916f0`. Job was READY `e4367c5b…` (sha changes on RUNNING flip). Prior RELAY-START `e4be1d9a…` stalled ~18h with no deposit. Visual-only: H-A-scratch / H-A-xfer / H-M-xfer (+optional H-M-scratch) s0@1600 walk1+dance1. Remote required ckpts+sizes pre-checked present. **M1 CLOSEOUT `48cd6bd2…` and arms CLOSE `5d8cf393…` stand — no scoring reopen.** Claude 4 will notify on DEPOSITED (or BLOCKED+ASK).

| Item | Path | sha256 |
|---|---|---|
| **RE-RELAY** | `orch/owner-decisions/20261028-1312-AsiaShanghai-B1-arms-compare-video-RE-RELAY.md` | `aae728d10a97cb351604c400df19ecd7af27ec26b9351a2da75eaeb3293916f0` |
| Compare-video START | `orch/owner-decisions/20261027-1834-AsiaShanghai-B1-arms-compare-video-START.md` | `90f6dd004b5c2a78ee049af4f7d19b62397d0e3cb2cb55516b6391eb2f12de28` |
| READY report (pre-run) | `orch/reports/READY-P6-b1-arms-compare-video-20261027.md` | `eb023a9f7eff75bc12a5de9f5bca6bb23c26a81f06d095fb04cdf003cd439a11` |
| Job JSON (RUNNING) | `orch/jobs/p6-b1-arms-compare-video.json` | (see tip after launch seal) |
| Renderer | `packets/P6/render_compare_b1_arms.py` | `51df5575bb6f0644faf0a46748efd0174163ba160acf22352d8c85f6061742c7` |
| run.sh | `orch/jobs/p6-b1-arms-compare-video/run.sh` | `50ba9b02789b76eff961baa3f433e2de9bf2addae3b922e46f82edee42ec568a` |

## Jobs

| job_id | state | venue | mutex | artifact | note |
|---|---|---|---|---|---|
| p6-b1-arms | SCORED/CLOSED | xn-4090-gpu2 | (released) | results `64644e3c…` | PASS/INCONCLUSIVE a1 of record |
| b1-m1-eval-metric | DONE / CLOSEOUT HOLD | CPU | — | report `e1d9d11a…` | post-hoc KILL alongside |
| p6-b1-arms-compare-video | **RUNNING** | xn-4090-gpu2 | gpu0 | MP4 compare | RE-RELAY launch 2026-10-28T05:15:02Z; visual-only |

## Hard non-touch

No scoring reopen, no M1 reopen, no attempt 2, no seeds, no PLAN.md in-place edit, no retrain on missing ckpt.
