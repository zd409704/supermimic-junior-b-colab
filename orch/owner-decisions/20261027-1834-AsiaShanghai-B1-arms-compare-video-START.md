# Owner decision — 2026-10-27 ~18:34 Asia/Shanghai — SuperMimic P6 B1 arms compare-video START

**Decision:** START a **visual-only** xn-4090-gpu2 job to render side-by-side / per-arm MP4 rollouts for sealed P6 B1 arms attempt-1 policies. Does **not** reopen scoring, amend PLAN.md, supersede arms CLOSE `5d8cf393…`, or change M1 CLOSEOUT `48cd6bd2…` (INCONCLUSIVE of-record + M1 KILL cite).

**AuthorizedBy:** owner chat ask 2026-10-27 ~18:33 Asia/Shanghai (render P6 arms compare videos) plus Manager standing autonomy / xn-4090 prefer.

**Program:** /srv/claude/research/supermimic-junior-b-colab/

## Intent

Claude 4 schedules Claude Code as Orchestrator to:
1. Adapt `packets/P4/render_compare_b0.py` into a B1 arms compare renderer under `packets/P6/` (or spikes/B1/); same headless OffscreenRenderer pattern.
2. Target arms at least: **H-A-scratch**, **H-A-xfer**, **H-M-xfer** (seed s0, ckpt 1600). Optionally include H-M-scratch if remote ckpt present. Clips: **walk1_subject1** and **dance1_subject1** (mask 0). Prefer one side-by-side walk1 and one side-by-side dance1 when frame lengths allow; otherwise labeled per-arm MP4s.
3. Locate attempt-1 trained ckpts on xn-4090 host (p6-b1-arms workdir / SuperMimic logs). Sealed deposit `f95155af…` has eval JSON only — do not claim ckpts are in the tarball. If ckpts are gone, write ASK and stop (no retrain).
4. Write `orch/jobs/p6-b1-arms-compare-video.json` + `run.sh`; seal uploads; set state **READY** when mutex-ready. Do not SSH from the box.
5. Update STATUS. Notify Manager when READY (or ASK if blocked). Relay (Claude 4 / Manager via Mac mini) starts only READY jobs.

## Constraints

- Visual artifact only. No scoring reopen. No seeds. No attempt 2. No PLAN in-place edit.
- Home-humanoid / plant-class wording; Provisional.
- Stay under program root for writes.
- Timeout ~1–2 GPU hours; mutex gpu0.

## Success

READY job + sealed render script; after relay DEPOSIT: MP4s under logs/xn4090/… and /workspace/uploads for owner view. Then HOLD.
