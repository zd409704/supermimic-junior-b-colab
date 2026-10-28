# READY — P6 B1 arms compare-video (visual artifact only) — 2026-10-27 06:40 EDT

**Provisional.** Visual artifact only. It does not reopen B1 scoring or M1, and it involves no attempt 2, no seeds, no retrain and no PLAN edit. Arms CLOSE `5d8cf393…` and M1 CLOSEOUT `48cd6bd2…` stand.
**Authority:** `orch/owner-decisions/20261027-1834-AsiaShanghai-B1-arms-compare-video-START.md` sha256 `90f6dd004b5c2a78ee049af4f7d19b62397d0e3cb2cb55516b6391eb2f12de28` (verified), with 1832 `48cd6bd2…` and 1745 `5d8cf393…` (verified).
**Method:** global pin v1.1 `9bdc872e…afc0` (sha verified) plus OVERLAY-001 (mechanical deposit, seal before analysis). OVERLAY-002 does not apply because nothing is scored. No new overlay: there is no contest and no Step 2, so no A.7 roster allocation is needed. This is a single-Claude orchestrator job.

## Job
| Item | Path | sha256 |
|---|---|---|
| Job JSON (READY) | `orch/jobs/p6-b1-arms-compare-video.json` | `e4367c5bd7cf951d4fbb7097a99b36a904f98c49a4a205f58de11e04af44ecd5` |
| Renderer | `packets/P6/render_compare_b1_arms.py` | `51df5575bb6f0644faf0a46748efd0174163ba160acf22352d8c85f6061742c7` |
| run.sh | `orch/jobs/p6-b1-arms-compare-video/run.sh` | `50ba9b02789b76eff961baa3f433e2de9bf2addae3b922e46f82edee42ec568a` |
| Junior tarball (sealed attempt-1, unchanged) | `packets/P6/junior_b_colab-P6-B1ARMS.tgz` | `0f18b8bbca7f7ef13fffb0bcf51b2370e997580a5b5f8f6ed2cffc4dd1eb8d87` |
| CPU test log | `logs/p6/render-compare-b1-cpu-attempt1.log` | `017ccfa888d845ec0a39706672f17d6d3500a52d9ed66a3d56c113367fb0ad36` |
| run.sh mock log | `logs/p6/run-compare-b1-mock-attempt1.log` | `ca6afbeab7ce94d0b16b908b1b73939a7115bea6905858e4f7528c921f734930` |

Venue xn-4090-gpu2, GPU0, mutex gpu0. The mutex is free: every other job is SCORED or DEPOSITED. Timeout 1.5 h. Command `bash ./run.sh`.
Deposit: `remote_glob=/content/b1-arms-compare-videos*.tgz` to `logs/xn4090/<UTC date>/`, seal event `DEPOSIT xn4090`.

## Design (adapted from packets/P4/render_compare_b0.py)
- **Arms.** H-A-scratch, H-A-xfer and H-M-xfer are required. H-M-scratch is optional and rendered only if its ckpt passes the checks. All are seed 0 at `ckpt_0001600.pt`, on clips walk1_subject1 and dance1_subject1, mask 0.0.
- **Policy load.** Identical to the sealed B1 eval path (`packets/P6/b1/p6_entry.py` cmd_eval): `install(init="scratch", probe=False, mlp_hidden from sidecar)`, then the attention descriptor sha check, then `supermimic.eval.benchmark.load_policy_from_checkpoint`. It runs on the home humanoid (`SM_BODY_MODULE=sm_body_home`) with the attempt-1 patched upstream tree and its `.venv`, both read-only.
- **Junior code.** A fresh unpack of the sealed tarball into `/content/p6_b1arms_compare/junior`, sha- and manifest-checked. `/content/b1arms/junior` is not reused.
- **Render.** One env, deterministic, starting from frame 0 of the clip, using OffscreenRenderer 640×480. Frames are streamed to an ffmpeg pipe, not held in RAM. Each frame carries a two-line label: arm/seed/it, and clip with time (or FELL AT / CLIP END). The rollout stops at termination or at `MAX_STEPS=3600` (about 72 s; the clips are ~13k frames, so long survivors are capped).
- **Side-by-side.** One per clip, using ffmpeg `hstack`. An arm that ends early holds its last labelled frame (`tpad clone`) so the panels stay time-aligned.
- **Outputs.** `<arm>_s0_it0001600_<clip>.mp4`, `compare_s0_it0001600_<clip>_sidebyside.mp4`, `preflight.json` and `summary.json`. Step counts in the summary describe video length only; nothing is scored.
- **ffmpeg.** The system binary, or else `imageio-ffmpeg --no-deps` installed into a side dir. The attempt-1 venv is not modified.

## Remote ckpt paths (identified; presence on host not verifiable from box)
These come from the sealed meta of deposit `f95155af…`, `meta/harness_stop_<aid>_a1.txt` (`ckpt_stable=true`). The `*.pt` files were excluded from the bundle by PLAN §8.

| Arm | Path on xn-4090 | Sealed bytes |
|---|---|---|
| H-A-scratch | `/content/SuperMimic-Reproduced-b1/logs/b1HAscratch_attention_s0/ckpt_0001600.pt` | 159445702 |
| H-A-xfer | `/content/SuperMimic-Reproduced-b1/logs/b1HAxfer_attention_s0/ckpt_0001600.pt` | 159445702 |
| H-M-xfer | `/content/SuperMimic-Reproduced-b1/logs/b1HMxfer_mlp_matched_s0/ckpt_0001600.pt` | 158486223 |
| H-M-scratch (opt.) | `/content/SuperMimic-Reproduced-b1/logs/b1HMscratch_mlp_matched_s0/ckpt_0001600.pt` | 159357327 |

The job also needs these on the host:
- `junior_policy.json` beside each ckpt
- `/content/SuperMimic-Reproduced-b1/.venv/bin/python`
- `/content/SuperMimic-Reproduced-b1/data/npz/b1_home/{walk1_subject1,dance1_subject1}.npz`
- the tarball, either uploaded or present at `/content/p6_b1arms/` with the same sha

No ckpt sha256 was recorded at train time, so identity is checked by the sealed byte size plus the sidecar policy. `preflight.json` records the sha256 seen on the host.

**Fail-safe instead of a pre-emptive ASK.** The paths are fully identified, so the job is READY. Presence on the host cannot be checked without SSH. The run.sh preflight therefore runs before any GPU work. If a required ckpt or npz is missing, or a size is wrong, it packs `b1-arms-compare-videos-<stamp>-BLOCKED.tgz` (preflight.json + log), prints `COMPARE_VIDEO_BLOCKED` and exits 4. The relay deposits that tgz like any other, and the Orchestrator then writes COMPARE_VIDEO_ASK. There is no retrain.

## Not tested on the box
Policy load and `env.render()` were not tested, because mjlab and supermimic are not on the box. They use the same calls as the sealed B1 eval path and the deposited P4 B0 compare job. These paths were tested:
- preflight (OK / size mismatch / missing)
- label, ffmpeg writer and hstack with unequal lengths (60/90/45 → 90 frames, 1920×480)
- run.sh end to end with `/content` remapped: the BLOCKED tgz path, and preflight-OK reaching the render import

## Relay (after DEPOSIT)
1. Seal the tgz under `logs/xn4090/<date>/`.
2. Copy the MP4s to `/workspace/uploads` for the owner to view.
3. HOLD.
