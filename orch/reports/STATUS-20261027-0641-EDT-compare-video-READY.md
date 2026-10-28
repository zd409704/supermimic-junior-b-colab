# Program STATUS - supermimic-junior-b-colab

**Stamp:** 20261027-0641-EDT
**Decision cap:** Provisional

## Headline

**P6 B1 arms compare-video: COMPARE_VIDEO_JOB_READY, HOLD for relay.** Job `orch/jobs/p6-b1-arms-compare-video.json` sha256=`e4367c5bd7cf951d4fbb7097a99b36a904f98c49a4a205f58de11e04af44ecd5` (READY, xn-4090-gpu2, gpu0 free). The renderer `packets/P6/render_compare_b1_arms.py` (`51df5575…`) and run.sh (`50ba9b02…`) are sealed. Arms: H-A-scratch / H-A-xfer / H-M-xfer, plus H-M-scratch if its ckpt is present, s0@1600, walk1+dance1, mask 0. Output: labelled per-arm MP4s plus one side-by-side per clip. The ckpt paths come from the sealed driver meta (`/content/SuperMimic-Reproduced-b1/logs/b1H*_s0/ckpt_0001600.pt`). Presence on the host is checked by the run.sh preflight: if a ckpt is missing, the job produces a BLOCKED tgz and exits 4, then COMPARE_VIDEO_ASK follows (no retrain). Report: `orch/reports/READY-P6-b1-arms-compare-video-20261027.md` (`eb023a9f…`). **M1 CLOSEOUT `48cd6bd2…` and arms CLOSE `5d8cf393…` stand. No scoring reopen, no seeds, no attempt 2.**

| Item | Path | sha256 |
|---|---|---|
| **Compare-video START** | `orch/owner-decisions/20261027-1834-AsiaShanghai-B1-arms-compare-video-START.md` | `90f6dd004b5c2a78ee049af4f7d19b62397d0e3cb2cb55516b6391eb2f12de28` |
| Compare-video prompt | `prompts/ORCH_P6_B1_ARMS_COMPARE_VIDEO.txt` | `80e132d35394d198bde8fc5540f1b1f77ce9443ca18da4e25bb7dddf9f954d75` |
| M1 CLOSEOUT (stands) | `orch/owner-decisions/20261027-1832-AsiaShanghai-B1-M1-CLOSEOUT.md` | `48cd6bd25e986ab616d58a15df33cf05d86e4a87d4e4b2bd56cd7d5626dc9768` |
| Arms CLOSE (stands) | `orch/owner-decisions/20261027-1745-AsiaShanghai-p6-arms-CLOSE-INCONCLUSIVE.md` | `5d8cf393044efcab8ab899ae9c51a463f7a2214643ea7c87eddf34127c4d2ebd` |
| **Compare-video job (READY)** | `orch/jobs/p6-b1-arms-compare-video.json` | `e4367c5bd7cf951d4fbb7097a99b36a904f98c49a4a205f58de11e04af44ecd5` |
| Compare-video READY report | `orch/reports/READY-P6-b1-arms-compare-video-20261027.md` | `eb023a9f7eff75bc12a5de9f5bca6bb23c26a81f06d095fb04cdf003cd439a11` |
| Deposit archive (RO; no .pt) | `logs/xn4090/2026-10-27/b1arms-20261027-0935.tgz` | `f95155af47357026d69f7c06f01c3d20ca806aa3378fce125322001d1094126d` |

## Jobs

| job_id | state | venue | mutex | artifact | note |
|---|---|---|---|---|---|
| p6-b1-arms | SCORED/CLOSED | xn-4090-gpu2 | (released) | results `64644e3c…` | PASS/INCONCLUSIVE a1 of record |
| b1-m1-eval-metric | DONE / CLOSEOUT HOLD | CPU | — | report `e1d9d11a…` | post-hoc KILL alongside |
| p6-b1-arms-compare-video | **READY** | xn-4090-gpu2 | gpu0 | job `e4367c5b…` | visual-only; deposit `/content/b1-arms-compare-videos*.tgz` → `logs/xn4090/<date>/`; HOLD for relay |

## Hard non-touch

No scoring reopen, no M1 reopen, no attempt 2, no seeds, no PLAN.md in-place edit. Scoring HOLD from M1 CLOSEOUT stands.
