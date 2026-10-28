# P4 PRESTART — pre-start gate record PS-1…PS-5 (P4-prep)

**Packet:** P4-prep (CPU / research box only). **Written by:** Orchestrator (Claude Code, `claude-opus`), 2026-10-26 EDT (America/Toronto). UTC/epoch for every seal is in `logs/seal.log`.
**Binding PLAN:** `spikes/B0/PLAN.md` sha256 `ed6b6a54a860bbfc67d7c822b5394804b8d408f6aae57fbeb118d2ea63c52557`, re-verified before every write in this packet. The PLAN was **not edited**.
**Method:** v1.1 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0` (re-verified at boot) + `method/local/OVERLAY-001-owner-colab-runner.md`. No new overlay was needed. P4-prep is not a contest packet, so no A.7 allocation or roster change was made (PLAN §11). **Decision cap:** Provisional.
**Spend:** none. No Colab, no XN-4090 job, no GPU training, no BLK-12 budget used.

## Gate table

| Gate | State | Evidence |
|---|---|---|
| **PS-1** CR-B0-1 (a)–(e) sealed | **true** | (a) `configs/b0_microbench.yaml` `d19e9297bf90530859c25aedc5ed3834064a7fc19838933def6b653e8a4cd495`; (b) `configs/b0_microbench_lr05.yaml` `283030054d53cc5b7002d696d9b466ae669b08d2a03960cabab8060fabde4729`; (c) `packets/P4/UPSTREAM_FACTS.md` `0e9cc73a98d7f006647e98210fa9014ee05811b112df8993a6e9b77215b5583f`; (d) `packets/P4/b0_driver.sh` `e87478fd16b7b41bde302cfbf3bda5d45534e58278a35e8a09e8d102218af3be` + `packets/P4/b0_driver_helper.py` `f43d8f5db9ad45fe6850aa87a4f549be56c6265b27d2e81bbe7dc840adf34b42` (+ `packets/P4/BUNDLE_CONTRACT.md` `07e565226cc25d8c84b7a3f5701d1264d6aa8549e3808b71c9d0c817bf729634`); (e) tarball `packets/P4/junior_b_colab-CR-B0-1.tgz` `763867682e3cfa05ca8eb6382ffc9124be2347b898531c60b904061776c33bff` and `packets/P4/MANIFEST_ADDENDUM.md` `0f203ffc206fd8e8b4a48f49c4d2bd02ad40a51ae86b0b3d0e0566e20164f79a`. All sealed in `logs/seal.log` (events `CR-B0-1-*`, `TARBALL-P4`, `MANIFEST-ADDENDUM-P4`). The 12 D-004 files are byte-identical to `packets/P1/FREEZE_MANIFEST.md` §1 (manifest digest `cd504ca2…5ff0` reproduced) |
| **PS-2** F-1…F-5 recorded | **true** | `packets/P4/UPSTREAM_FACTS.md`: F-1 `--schedule.total-iterations` (iterations, inclusive, ckpt written; **also the cosine-LR horizon** → classified unsuitable → harness stop); F-2 `--policy-trainer.lr` default 2e-4 (critic LR follows); F-3 policy grad-norm clip 1.0; F-4 pre-clip, **mean per 50-iteration log window, no per-update clip indicator**; F-5 512 env steps per iteration (= `num_envs`, arm-independent) |
| **PS-3** clip clause evaluable, or ruling (i)/(ii) signed (ii also implemented) | **false — BLOCKED_ON_SIGNATURE** | F-4 shows no per-update pre-clip norm and no per-update clip indicator, so the PLAN §2.2 F-3/F-4 rule applies. M-6 = `null`. Ruling text below |
| **PS-4** env-step parity (F-5) or signed acceptance of the gap | **true** | F-5 source proof: one vectorised `env.step` per iteration (`loop.py:161-163`, `:177`), no arm-dependent branch, `num_envs` from config only (`config.py:25`, `loop.py:59`), `world == 1` (`distributed.py:20-27`). No signature needed. V-2 (a) still checks `time/updates` at it 1600 |
| **PS-5** SIGINT launcher check (f) passed | **true** | `logs/p4prep/sigint-check-attempt2.log` `9dd5ccd6056c2cce291288342ad6e2c1cda8de5f28351834263ba92131b4a58a`: `SIGINT_CHECK attempt=2 result=PASS exit_code=130 harness_stop=true timeout=false sidecar=present control=ignored natural_exit_ok=true`. Attempt 1 (`logs/p4prep/sigint-check-attempt1.log` `11fe82f7a8ee633a41ff4c6a34a31007f2d2906fc5f335dd4f3b092da2c69d3b`) also passed. Its summary line misreports `exit_code=3`: a later sub-test in the check script overwrote the variable. The gate fields inside that log show `exit_code=130`. Both attempts used the same driver bytes (`e87478fd…`) |

**Result: P4 attempt 1 must not start.** PS-3 is open. PS-1, PS-2, PS-4 and PS-5 hold.

## Verdict tool (PLAN §8.2)

`spikes/B0/verdict/verdict_b0.py` `9caa744a65ef5206fd46f532c4d13529b7773d076ee725ee4cb98ec192774a3b` (with helpers listed in `logs/seal.log`, event `VERDICT-TOOL`) is sealed **before any P4 deposit exists** (`logs/colab/` and `logs/xn4090/` hold no `b0-*.tgz`).

## Signature asks (human lead)

Under PLAN §2.2 a ruling under PS-3 or PS-4 is a Class-2 amendment, signed before attempt 1. Per this packet's instructions, the asks are recorded here and **not** appended to the PLAN. After a signature, a later wake appends the signed text to `spikes/B0/PLAN.md` as `Amendment v1` and seals the PLAN's new sha256. No signature has been invented here.

### Ask 1 (required, PS-3) — sign exactly one of the two options

> **PLAN Amendment v1 (Class 2), spikes/B0/PLAN.md sha256 ed6b6a54a860bbfc67d7c822b5394804b8d408f6aae57fbeb118d2ea63c52557, PS-3 ruling.**
> Upstream fact F-4 (`packets/P4/UPSTREAM_FACTS.md`) shows that tb `policy/policy_grad_norm` is the pre-clip norm averaged over each 50-iteration log window, and that no per-update clip indicator is logged.
>
> **Option (i) — omit the clip clause.** The divergence rule §6.3 (b) ("clip fraction (M-6) above 0.5") is omitted for P4. Divergence is decided by §6.3 (a) only (NaN/inf in tb at steps ≤ 1600, or an R-DIV exception before the scoring endpoint). M-6 is reported as `null`. The B0 decision carries a stability-evidence confound, disclosed under Confounds item 10. No logged-point proxy is used.
>
> **Option (ii) — add per-update clip logging.** An observation-only change request (CR-B0-2) adds a per-update clip numerator and denominator over iterations (1200, 1600] without editing any D-004 frozen file. PS-3 holds only after CR-B0-2 is implemented and sealed (new tarball and manifest addendum), a CPU or short-venue check log shows those fields written, and the verdict tool computes M-6 from them.
>
> Signed: ____________________ (human lead)  Option: (i) / (ii)  Date/time (UTC): ____________________

Orchestrator note (not a recommendation that binds the signer): option (i) can start P4 without new code. Option (ii) needs a new CR. Upstream logs metrics through a module-level loop with no hook point for per-update grad norms other than wrapping `PolicyTrainer.update` in-process (as `train_entry` already wraps `Trainer.__init__`), and that would be a change to the frozen wrapper or a new wrapper file. Expect at least one more CPU packet plus a short GPU check.

### Ask 2 (confirmation, F-1 reading; affects PS-1 only if rejected)

> **F-1 reading, spikes/B0/PLAN.md §2.2 (a).** The upstream flag `--schedule.total-iterations` caps training at iteration N, but it also sets the cosine LR horizon (`loop.py:184`; `schedule.py:9-11`). Setting it to 1600 would decay every LR to 3% of base by iteration 1250. With the frozen default the LR stays ≈ base for the whole budget. I confirm that this flag counts as **unsuitable** under §2.2 (a), so the harness stop (§4.3) ends every attempt and no cap flag goes into `configs/b0_microbench.yaml`.
>
> Signed: ____________________ (human lead)  Confirm / Reject  Date/time (UTC): ____________________

If rejected, CR-B0-1 (a), (b) and (e) are regenerated with `--schedule.total-iterations: 1600`, the driver's harness stop becomes `wait $TR`, and PS-1 and PS-5 are re-established before attempt 1.

### Flag carried from the PLAN (no gate, for the human lead)

PLAN §0 depth disclosure: B0 → D-004 → D-001 may count as Provisional-on-Provisional (method §13.3 cap). The PLAN left this to the human lead. It is not a PS gate, and P4-prep does not resolve it.

## Disclosures

0. **Integration check (driver → deposit → verdict).** `logs/p4prep/driver-mock-attempt2/` ran the driver's main loop with a fake trainer and eval. They emitted genuine TF event files, real-format logs, seams, sidecars and eval JSONs via `spikes/B0/verdict/make_fixture.py`, with a scripted DIV at `b0_mlp_matched_s1` and an INFRA at `b0_attention_s2`. The verdict tool, run on that deposit with a scratch seal log (`mock-seal.log`, **not** `logs/seal.log`), printed `B0_VERDICT verdict=PASS outcome=NONINFERIOR basis=margin delta=0.0 delta_thr=0.05 failing_ids=[] blocked=[]`. All 10 driver classes equalled the verdict's own classes, the `b0lr05` pair replaced seed 1, `b0_attention_s2_a2` was scored, and V-2 argv parity held. This is a pipeline test on synthetic numbers, not evidence about B0.
1. **Helper alignment after the SIGINT check.** After reviewing the verdict tool, `b0_driver_helper.py` was changed so its scheduling classifier uses the same rules as the verdict tool: every pre-endpoint traceback is tested for R-DIV/OOM, the same OOM pattern is used, and duplicate tb steps resolve to the latest wall time before the non-finite test. The helper is not on the SIGINT path. `b0_driver.sh` (`e87478fd…`) is byte-identical between the SIGINT check and the tarball.
2. **Verdict tool reading choices.** `spikes/B0/verdict/IMPLEMENTATION_NOTES.md` lists 31 resolved ambiguities. Three go beyond the literal §6.4 row-1 list and should be noted by the human lead: `venue_mixed` → BLOCKED (from PLAN §2.3); a gate slot with no attempt at all → V-1…V-4 false → BLOCKED; and runner `BLOCKED.md` codes other than `spend_cap`/`R1_unresolved` → BLOCKED as `blocked_md:<code>` (method §12.2 plan gap). The harness SIGINT's `KeyboardInterrupt` traceback on every completed attempt is recorded as `post_endpoint_anomaly` and never moves the verdict (PLAN §3.3).
3. **Mock driver run.** `logs/p4prep/driver-mock-attempt1/` ran the driver's main loop on the box with a fake trainer, eval and `nvidia-smi`, setup and V-0 stubbed out, `/content` remapped into that directory, and `POLL_S=1`. That is a **modified copy** of the driver, used only to test scheduling, divergence pairs, INFRA retry, harness stop, eval, archive and packing. It is not evidence for any gate. The SIGINT check (PS-5) used the unmodified driver bytes.
4. **Upstream clone.** `packets/P4/upstream-ro/SuperMimic-Reproduced/` is a read-only clone at the pin, kept for citation checking. It is not in the tarball and not under `code/`.
5. **Verdict tool authorship.** A separate Claude subagent process (not the PLAN adjudicator, and not the runner) wrote the verdict tool from the PLAN text and `packets/P4/BUNDLE_CONTRACT.md`. The Orchestrator reviewed and tested it before sealing (OVERLAY-001 rule 6).
