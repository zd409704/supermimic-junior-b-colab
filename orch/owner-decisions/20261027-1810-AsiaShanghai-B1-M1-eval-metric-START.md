# Owner decision — 2026-10-27 ~18:10 Asia/Shanghai — SuperMimic B1 Class-2 amendment M1 START (eval metric post-hoc re-score)

**Decision:** START sealed Class-2 amendment packet **M1** per `docs/FOLLOWON_BRIEF_B1_EVAL_METRIC.md` sha256 `01ecb8c13bef70c30212573a90da79654e12578830a5a02efacbf5e2f25a752d` §5 outline and §7 recommendation (optional path: answer from existing deposit). Arms CLOSE INCONCLUSIVE (`5d8cf393…`) stands and is **not** superseded. Do **not** add seeds, relaunch arms, reopen P4/P5, or use Colab/GPU.

**AuthorizedBy:** owner request for SuperMimic eval-metric / clip-failure follow-on brief (2026-10-27 ~18:00 Asia/Shanghai) plus Manager standing autonomy. Prior START 1800 `02f949927a10d448c392e201384f1f5efbdc7047c9b807a5835c15d19cfbb795`.

**Class-2 signature (METHOD):** Manager signs Class-2 option for changing the scoring input on a post-hoc labelled re-score of the sealed deposit only. Human-lead/Manager depth and Class-2 practice follows prior P6 C2 waivers under owner delegation. Outcome remains Provisional, single-candidate; depth A1.1-1 unchanged (no depth-3 build).

**Program:** /srv/claude/research/supermimic-junior-b-colab/

## Intent

Claude 4 schedules Claude Code as Orchestrator to:
1. Draft and seal `spikes/B1/AMENDMENT-M1-eval-metric` (append-only under PLAN §5; do not edit PLAN.md in place) with primary metric R_full (completion-aware), pre-registered dance1 rule (b1), collapse rule (a2), criterion form (a3), labelling "post-hoc re-score (M1)".
2. Run `codex-astra` high red team on the amendment text before seal (closes PLAN §9 gap + brief §5.6). If Codex is unavailable, disclose and stop for Manager — do not seal without the red team or an explicit Manager waive.
3. Seal `verdict_b1.py` v1.1 (v1.0 behind flag) with CPU mock before opening the deposit.
4. Re-score deposit `f95155af…` only; write labelled M1 results + report. Attempt-1 machine line stays on record.
5. Optionally propose (do not execute without further START) b2 dance1 reference CPU read on xn-4090 host.
6. Update STATUS; HOLD after M1 report.

## Constraints

- CPU only. No SSH. No xn-4090 GPU. No Colab. No attempt 2. No seed add.
- Stay under /srv/claude/research/supermimic-junior-b-colab/ for writes.
- Do not reopen P4/P5. Append ledger observation that D-005/D-006 used the same survival-conditioned R (disclosure only).
- Provisional; home-humanoid / plant-class wording; no commercial product brands.
- Pre-register all M1 metric choices **before** any arm-level alternative-metric computation.

## Success

Claude 4 ACKs; amendment + tool sealed; M1 re-score report path + sha to Manager; then HOLD.
