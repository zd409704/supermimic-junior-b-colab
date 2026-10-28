# Program STATUS - supermimic-junior-b-colab

**Stamp:** 2026-10-26 09:02 EDT
**Decision cap:** Provisional

## Headline

**P5 B2 job READY (Provisional).** Manager closed engineering-review MINOR r1 #8 as option (i) and issued START citing PLAN and CR-B2-1 tarball shas. Job `p5-b2-attempt1` is **READY** (not RUNNING). No GPU start from the research box.

| Item | Path | sha256 |
|---|---|---|
| PLAN (binding, unchanged) | `spikes/B2/PLAN.md` | `5d1f26f776a3ea56c2becd3ec2fa2cf8e88bd62c43a20f79415a96e82a3da11d` |
| **CR-B2-1 tarball** (30 files) | `packets/P5/junior_b_colab-CR-B2-1.tgz` | `53a898e9b635d1317bebabe884f1450e52be2980165811859445c1b9b53ce851` |
| Manifest addendum | `packets/P5/MANIFEST_ADDENDUM.md` | `96a61859a0f37bbbddb6422b6e13530477d542ab8f6141ecd0b4186f58767db9` |
| CPU test log (g), all sections PASS | `logs/p5prep/cpu-tests-attempt1.log` | `cac574632072b1a96634f6327d1cfe9140df170dc62610ad88351f7891a88aab` |
| VERDICT-TOOL-B2 (71/71) | `spikes/B2/verdict/verdict_b2.py` | `cd2ac741d2ffad7353c7cf62ca5f325a5402ec4d7e6a6c6f5887ecff511c994c` |
| Job run.sh | `orch/jobs/p5-b2-attempt1/run.sh` | `2ae9af24b03ce83b346a3331a568cd3b4a1cd882e03f3ac3431475d71ee32717` |
| Job JSON (**state READY**) | `orch/jobs/p5-b2-attempt1.json` | `3e81b0b9530bae56dc202bda8ff54c695ffea38526f1d298218856528425d167` |
| Manager decision (r1 #8 + START) | `orch/reports/DECISION-r1-8-P5-START-20261026.md` | `ac82694f03734b51e5d64632b24b696040d5ecb09885880715642391271de67d` |
| PRESTART (prep-time seal, unchanged 0444) | `packets/P5/PRESTART.md` | `97b8942ee87dbe4ec475f31ed38e4be5ee33fe4093b0ce8cad976270e157a5b9` |

- **r1 #8 (MINOR) closed — option (i):** job JSON stays under `orch/jobs/`; uploads = tarball + run.sh per PS-B2-3; authoritative JSON + relay stdout sealed beside the archive (`RELAY-LOG`), as in P4. No upload-list amendment.
- **PS-B2-1 / PS-B2-2:** held (prep). **PS-B2-3:** READY flip. **PS-B2-4:** Manager START in the decision note above.
- **Mutex:** `gpu0`. No other job is RUNNING. Prior: p4-b0-attempt1 SCORED; p4-b0-compare-video DEPOSITED.
- **P4 checkpoints:** must remain on xn-4090 until this run (PLAN §2.2). Not verified from the box (no SSH).

## Deposits (sealed before open)

No P5 deposits exist. P4 deposits are unchanged (latest scored: `logs/xn4090/2026-10-26/b0-20261026-0919.tgz` `1f491182…`, PASS/NONINFERIOR).

## Jobs

| job_id | state | venue | mutex | artifact | note |
|---|---|---|---|---|---|
| p4-b0-attempt1 | SCORED | xn-4090-gpu2 | gpu0 | results `76507d8a…` | PASS/NONINFERIOR |
| p4-b0-compare-video | DEPOSITED | xn-4090-gpu2 | gpu0 | compare mp4s `a0d77524…` | sealed; gpu0 free |
| p5-b2-attempt1 | READY | xn-4090-gpu2 | gpu0 | tarball `53a898e9…` | awaiting Mac mini relay start; not RUNNING |

## Next

1. **Mac mini relay:** pick up READY job `p5-b2-attempt1`, verify upload sha256s, rsync to remote workdir, `ssh xn-4090-gpu2` with job command, set RUNNING only when starting, deposit `b2-*.tgz` + RELAY-LOG, seal before open.
2. Confirm six P4 `ckpt_0001600.pt` still exist on xn-4090 under PLAN §2.2 roots before/at start (driver BLOCKs if missing).
3. Est. 3.5–4 GPU-h; cap 6 h (`timeout_hours` 8). Venue XN-4090-GPU2 only.

No Colab. P6 has not started.

---

## Previous status (P5-prep DONE 09:00 EDT), kept for reference

**P5-prep DONE (Provisional).** CR-B2-1 sealed; CPU 14/14; verdict 71/71; job was DRAFT awaiting Manager START. See `orch/reports/STATUS-20261026-0900-EDT.md`.

