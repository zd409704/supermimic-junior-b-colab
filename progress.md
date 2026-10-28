# progress.md — run-001-scaffold (method v1.1 sha256 9bdc872e…590afc0)

State table (method §13.5). States: PENDING / RUNNING (attempt, start) / DONE (hash) / SKIPPED (reason) / ABORTED (reason).
Times America/Toronto. Hashes = first 16 hex of sha256.

| Step | Description | State | Evidence |
|---|---|---|---|
| S0 | Method boot: pin verified, overlays read, fit analysis | DONE (2026-10-25 14:06 EDT) | `orch/STATUS.md` §1 |
| S1 | Design review read; amendment note appended | DONE (f0590bdf180e36af) | `docs/DESIGN_REVIEW.md` |
| S2 | Scaffold: attention decoder, matched MLP, entrypoints, config, notebook, runbook, vendor notes | DONE | hashes in `orch/STATUS.md` §3 |
| S3 | CPU import + smoke on research box | DONE (attempt2 018c0a40de08da74) | `logs/smoke-cpu-attempt2-20261025-1417-EDT.log` (attempt1 kept: `logs/smoke-cpu-attempt1-20261025-1415-EDT.log`, superseded by code change for B1 morphology) |
| B0-smoke | Colab GPU: upstream sanity + 1-seed attention vs mlp_matched smoke train + eval | PENDING (owner, Colab) | runbook §5–§7 |
| B0-plan | Seal `spikes/B0/PLAN.md` (arms, seeds=3, budget, thresholds from runbook §8) | PENDING (Orchestrator, after B0-smoke passes) | — |
| B0 | Colab microbench, 3 seeds/arm, matched budget | PENDING (blocked on B0-smoke, B0-plan) | — |
| B2 | Token-mask retention ρ(0.1), ρ(0.2) + id_mode=index ablation, on B0 checkpoints | PENDING (blocked on B0) | — |
| B1 | Second embodiment / masked DoF | PENDING (gated: only if B0 or B2 shows signal). Prereqs open: actuators (MJCF nu=0), retargets, per-body WM/critic | `assets/home_humanoid_mjcf/`, `code/vendor/NOTES.md` |

---

# progress.md — run-002-eval-scheme (method v1.1 sha256 9bdc872e…590afc0 + OVERLAY-001)

| Step | Description | State | Evidence |
|---|---|---|---|
| E0 | Method boot: pin sha verified, overlays read, fit analysis (OVERLAY-001 added) | DONE (2026-10-25 14:22 EDT) | `orch/STATUS.md` |
| E1 | Context read + asset inventory (CPU mujoco 3.17) | DONE | `docs/EVAL_REVIEW.md` §4.1 |
| E2 | EVAL_REVIEW written | DONE (hash in STATUS) | `docs/EVAL_REVIEW.md` |
| E3 | SCHEME_PLAN written | DONE (hash in STATUS) | `docs/SCHEME_PLAN.md` |
| E4 | B1 brief (draft, unfrozen) | DONE (hash in STATUS) | `briefs/B1-home-humanoid-cross-embodiment.md` |
| E5 | DESIGN_REVIEW note, ledger D-002/P-B1, ISSUE-001 | DONE | appended files |
| P1 | Scaffold freeze (+FX-1..4, D-DESC contest) | PENDING (later Claude Code orchestration wake) | `docs/SCHEME_PLAN.md` §1 |
| P2–P6 | B0 smoke → B0 seal → B0 → B2 → B1 | PENDING | `docs/SCHEME_PLAN.md` |

---

# progress.md — run-003-p1-freeze (method v1.1 sha256 9bdc872e…590afc0 + OVERLAY-001; roster `roster.md`)

Times America/Toronto; epoch/UTC in `logs/seal.log`. Rows are appended as states change (latest row per step wins).

| Step | Description | State | Evidence |
|---|---|---|---|
| M0 | Method boot: pin sha verified, overlays read, fit analysis (no new overlay needed) | DONE (2026-10-25 14:43 EDT) | `logs/seal.log` METHOD-PIN |
| M1 | CLI availability probe (codex OK, agy OK after flag fix, standalone claude CLI not logged in → Agent-tool subagents) | DONE | `logs/p1/probe/` |
| D0 | `briefs/D-DESC.md` + `roster.md` + author prompts frozen | DONE (brief f2458a0ee77d936f, roster 5be8a85d97746e09) | `logs/seal.log` |
| D1-A | Author A draft (claude-opus subagent) | RUNNING (attempt1, 2026-10-25 14:49 EDT) | `logs/p1/ddesc/runs.log` |
| D1-B | Author B draft (codex-astra high) | PENDING (after D1-A sealed) | — |
| D1-A | Author A draft | DONE (f1df6b40b121679f) | `logs/seal.log` SEAL author-A |
| D1-B | Author B draft (codex-astra high) | DONE (b7d3b1b65be2362b) | `logs/seal.log` SEAL author-B |
| D2 | Publish-after-all under neutral labels (X=B, Y=A) | DONE | `packets/P1/ddesc/proposals/` |
| D3 | Cross reviews (codex on Y; fresh claude-opus on X) | DONE (on-Y 36402c40, on-X 922b15dc) | `packets/P1/ddesc/reviews/` |
| D4 | Adjudication agy (2 passes, order reversed) | DONE: Recommend Y 35, Alternate X 30, no tie | `packets/P1/ddesc/decision.md` |
| D5 | D-DESC CPU spike (claude-sonnet runner) | DONE: PASS (1/3 executions) | `spikes/D-DESC/runs.log` |
| F1 | FX-1..FX-5 (claude-sonnet) | DONE | `packets/P1/fixes/fx-stage1.diff` |
| F2 | DDESC-ADOPT into code/ (claude-sonnet) | DONE | `packets/P1/fixes/ddesc-adopt.diff` |
| F3 | Cross-family review 1 (codex read-only) | DONE: BLOCK (O-1 blocker, O-2/O-3 major) | `packets/P1/fixes/REVIEW-1.md` |
| F4 | Round 2 fixes + review 2 | DONE: FREEZE-OK | `packets/P1/fixes/REVIEW-2.md` |
| S | CPU smoke attempt 3 | DONE (c2a9ea92a2572cf2): all PASS | `logs/smoke-cpu-attempt3-20261025-1537-EDT.log` |
| Z | P1 freeze manifest sealed | DONE (e1d0eae27bd13170) | `packets/P1/FREEZE_MANIFEST.md` |
| P2-prep | Tarball + `spikes/B0-smoke/PLAN.md` sealed | DONE | `packets/P2/`, `logs/seal.log` |
| P2 | Owner Colab smoke | PENDING (owner) | — |
| P3+ | B0 PLAN seal, B0, B2, B1 | PENDING (blocked: Human-lead asks, P2) | `orch/STATUS.md` §5 |

---

# progress.md — P3 B0 PLAN seal (method v1.1 sha256 9bdc872e…590afc0 + OVERLAY-001)

| Step | Description | State | Evidence |
|---|---|---|---|
| P3-M0 | Method boot: pin sha re-verified, overlays read, no new overlay; non-contest packet (no A.7 roster) | DONE (2026-10-26 ~00:40 EDT) | `spikes/B0/PLAN.md` §11 |
| P3-RT | Cross-family red team (codex-astra high), rounds 1–3: REVISE each round, all objections dispositioned | DONE (draft 4 not re-reviewed, disclosed) | `packets/P3/REDTEAM-DISPOSITION.md`, `logs/p3/` |
| B0-plan | Seal `spikes/B0/PLAN.md` | DONE (ed6b6a54a860bbfc67d7c822b5394804b8d408f6aae57fbeb118d2ea63c52557) | `logs/seal.log` SEAL spikes/B0/PLAN.md 2026-10-26T04:59:42Z |
| P4-prep | CR-B0-1 + UPSTREAM_FACTS + driver + SIGINT check + verdict tool; PS-1..PS-5 | PENDING (next wake; CPU only) | PLAN §2.2 |
| P4 | B0 microbench (XN-4090 intended / Colab L4 alternate) | PENDING (blocked on P4-prep PS-1..PS-5 and runner packet) | PLAN §3–§9 |

---

# progress.md — P4-prep (method v1.1 sha256 9bdc872e…590afc0 + OVERLAY-001; PLAN ed6b6a54…2c52557)

| Step | Description | State | Evidence |
|---|---|---|---|
| P4P-M0 | Method boot: pin and PLAN sha re-verified, overlays read, no new overlay, non-contest packet (no A.7 roster) | DONE (2026-10-26 ~01:10 EDT) | `logs/seal.log` METHOD-PIN / PLAN-VERIFY 05:43:42Z |
| CR-B0-1 (a)(b) | `configs/b0_microbench.yaml`, `configs/b0_microbench_lr05.yaml` | DONE (d19e9297… / 28303005…) | seal CR-B0-1-a/b |
| CR-B0-1 (c) | `packets/P4/UPSTREAM_FACTS.md` F-1…F-5 | DONE (0e9cc73a…) | seal CR-B0-1-c |
| CR-B0-1 (d) | driver `b0_driver.sh` + helper + bundle contract | DONE (e87478fd… / f43d8f5d… / 07e56522…) | seal CR-B0-1-d |
| CR-B0-1 (e) | tarball + manifest addendum | DONE (763867682e3c…3bff / 0f203ffc…) | seal TARBALL-P4, MANIFEST-ADDENDUM-P4 |
| (f) SIGINT | launcher check on the box | DONE: attempt 1 PASS (summary-line defect), attempt 2 PASS exit 130 | `logs/p4prep/sigint-check-attempt{1,2}.log` |
| VERDICT-TOOL | `spikes/B0/verdict/verdict_b0.py` (+fixture, tests 24/24, notes) | DONE (9caa744a…), sealed before any P4 deposit | seal VERDICT-TOOL |
| PRESTART | PS-1…PS-5 record | DONE (cf91804e…): PS-1 T, PS-2 T, **PS-3 F (BLOCKED_ON_SIGNATURE)**, PS-4 T, PS-5 T | `packets/P4/PRESTART.md` |
| P4 | B0 microbench | PENDING: blocked on PS-3 signature (+ R-F1 confirmation) and a runner packet | PRESTART Asks 1–2 |

---

# progress.md — P5 B2 PLAN (method v1.1 sha256 9bdc872e…590afc0 + OVERLAY-001)

| Step | Description | State | Evidence |
|---|---|---|---|
| P5-M0 | Method boot: pin sha verified, overlays read, no new overlay, non-contest PLAN packet (no A.7 roster) | DONE | PLAN §13 |
| P5-RT | Cross-family red team (codex-astra high), rounds 1–3: REVISE, REVISE, SEAL-OK | DONE | `spikes/B2/redteam/`, seal P5-REDTEAM |
| B2-plan | Seal `spikes/B2/PLAN.md` | DONE (5d1f26f776a3ea56c2becd3ec2fa2cf8e88bd62c43a20f79415a96e82a3da11d) | `logs/seal.log` SEAL spikes/B2/PLAN.md |
| P5-prep | CR-B2-1 (a)–(g) + VERDICT-TOOL-B2 + job READY (PS-B2-1..3) | PENDING (CPU packet) | PLAN §2.3 |
| P5 | B2 run on XN-4090-GPU2 | PENDING: await P5-prep and Manager START (PS-B2-4) | PLAN §4, §10 |

---

# progress.md — P5-prep CR-B2-1 + VERDICT-TOOL-B2 (method v1.1 sha256 9bdc872e…590afc0 + OVERLAY-001)

| Step | Description | State | Evidence |
|---|---|---|---|
| P5P-M0 | Method boot: pin sha verified, OVERLAY-001 read, catalog A.6/A.7 read. Engineering packet, not a contest, so no roster change and no new overlay | DONE | `packets/P5/PRESTART.md` header |
| CR-B2-1-a | `configs/b2_idx.yaml`, `configs/b2_mtrain.yaml` (named changes only) | DONE (a50bc042…, d8dab884…) | seal CR-B2-1-a |
| CR-B2-1-b | `mlp_mind` arm + train wrapper (467 491 params, +0.75%) | DONE (0e061988…, a69646b5…) | seal CR-B2-1-b |
| CR-B2-1-c | Fixed-seed mask-stream eval wrapper (7100/7101/7102) | DONE (323f3c08…, c4cee827…) | seal CR-B2-1-c |
| CR-B2-1-d | PERM script (GPU upstream + CPU mode) | DONE (570daf6e…) | seal CR-B2-1-d |
| CR-B2-1-e | P5 driver, helper, bundle contract; job run.sh + JSON (**DRAFT**) | DONE (197d2b8c…, f4d73e13…, 3b0bf132…; run.sh 2ae9af24…, JSON 564a203d…) | seals CR-B2-1-e, JOB-RUNSH, JOB-JSON |
| CR-B2-1-f | Tarball + manifest addendum (CR-B0-1 rebuild byte-identical) | DONE (tarball 53a898e9b635d1317bebabe884f1450e52be2980165811859445c1b9b53ce851; addendum 96a61859…) | seals TARBALL-P5, MANIFEST-ADDENDUM-P5 |
| CR-B2-1-g | CPU tests: every (g) item PASS (working tree and unpacked tarball) | DONE (log cac57463…) | seal CPU-TEST-LOG-P5 |
| VERDICT-TOOL-B2 | `verdict_b2.py` + fixture + tests 71/71, sealed before any P5 deposit | DONE (cd2ac741d2ffad7353c7cf62ca5f325a5402ec4d7e6a6c6f5887ecff511c994c) | seal VERDICT-TOOL-B2 |
| P5P-REVIEW | codex-astra high code review, 4 rounds. 0 BLOCKER. All MAJOR fixed. 1 MINOR open for the Manager | DONE | `packets/P5/review/`, seal P5PREP-REVIEW |
| P5P-MOCK | Driver integration mock on CPU (12 attempts incl. abort/restart). Synthetic | DONE | `logs/p5prep/driver-mock-attempt*`, seal P5PREP-MOCK |
| PRESTART | PS-B2-1 true, PS-B2-2 true, PS-B2-3 open (DRAFT), PS-B2-4 open | DONE (97b8942e…) | `packets/P5/PRESTART.md`, seal PRESTART-P5 |
| P5 | B2 run on XN-4090-GPU2 | PENDING: Manager START (cite PLAN 5d1f26f7… + tarball 53a898e9…), then READY flip | PLAN §10 |

---

# progress.md — P5 B2 attempt 1 score (method v1.1 sha256 9bdc872e…590afc0 + OVERLAY-001)

| Step | Description | State | Evidence |
|---|---|---|---|
| P5S-M0 | Method boot: pin sha verified, method/local overlays read (OVERLAY-001). Deposit-open + harness only, not a contest packet | DONE | pin 9bdc872e… |
| P5S-SEAL | Deposit sha256 a869b8fc… matches; seal.log DEPOSIT xn4090 line present | DONE | seal.log 2026-10-26T21:14:53Z |
| P5S-OPEN | Safe extract to `logs/xn4090/2026-10-26/open-b2-20261026-1611/` (548 files; no abs, `..` or link members); .tgz untouched | DONE | open tree |
| P5S-VERDICT | `python3 -I verdict_b2.py` (cd2ac741…), exit 0 | DONE (results c184bb88…, stdout b7ffee40…) | `B2_VERDICT verdict=BLOCKED outcome=null … gate_b1=Go blocked=[gpu_mismatch,U-REPRO,B2-V-2]` |
| P5S-REPORT | `orch/reports/VERDICT-P5-b2-attempt1-20261026.md` (Provisional) | DONE (79fda4e6…) | seal VERDICT-P5-REPORT |
| P5S-JOB | Job JSON state SCORED, gpu0 free | DONE (d5aea66d…) | seal JOB-JSON |
| P5S-STATUS | STATUS.md + copy STATUS-20261026-1718-EDT.md | DONE (f1235511…) | seal STATUS |
| NEXT | Await Manager on BLOCKED (U-REPRO (iv)/(v); gpu_mismatch disclosure). No P6 or GPU | PENDING | — |

---

# progress.md — P5 B2 attempt 1 Class-2 amendment (method v1.1 sha256 9bdc872e…590afc0 + OVERLAY-001)

| Step | Description | State | Evidence |
|---|---|---|---|
| P5C-M0 | Method boot: pin sha verified, method/local overlays read (README, OVERLAY-001). Amendment of a scored packet, not a contest | DONE | pin 9bdc872e… |
| P5C-AUTH | Owner/Manager Class-2 decision verified (9985fc8f…; sealed 2026-10-26T21:20:12Z). Machine results verified (c184bb88…) | DONE | seal OWNER-DECISION |
| P5C-SCORE | `python3 -I packets/P5/class2_amend_b2.py` (172f5630…): U-REPRO option (iv), gpu_mismatch/B2-V-2(c) waived → §7.3 row 4 PASS; §7.2 from f0.20 → NO_GAIN (u_deficit true); gate_b1 Go | DONE (results d62dc0b7…) | `B2_VERDICT_CLASS2 verdict=PASS outcome=NO_GAIN … machine_was=BLOCKED waivers=[U-REPRO:iv,gpu_mismatch]` |
| P5C-REPORT | `orch/reports/VERDICT-P5-b2-attempt1-class2-20261026.md` (Provisional; machine line quoted; per-clip U-REPRO disclosure; gpu waive rationale) | DONE (67f0424e…) | seal VERDICT-P5-CLASS2-REPORT |
| P5C-CR | Tool CR note `orch/reports/CR-verdict-b2-gpu-name-parse.md`. Not applied; sealed tool bytes unchanged | DONE (11569dcc…) | seal CR-NOTE |
| P5C-JOB | Job JSON stays SCORED; `class2_amendment` pointer added | DONE (e973f70a…) | seal JOB-JSON |
| P5C-STATUS | STATUS.md + copy STATUS-20261026-1721-EDT.md | DONE | seal STATUS |
| NEXT | Await Manager. No P6, no GPU, drive paused | PENDING | — |

---

# progress.md — P6 B1 line (method v1.1 sha256 9bdc872e…590afc0 + OVERLAY-001; START 3a0254de…, amend 1408aeef…)

| Step | Description | State | Evidence |
|---|---|---|---|
| P6-M0 | Method boot: pin sha verified; overlays README + OVERLAY-001 read; catalog A.6/A.7 read. Non-contest packet (single-candidate SCHEME_PLAN design, brief A1.1-6), so no A.7 contest roster; venue special handled by brief/PLAN amendment, no new overlay | DONE | seal METHOD-PIN, OWNER-DECISION 22:58:41Z |
| P6-S0 | Brief Amendment v1.1 (depth-2 raise, P-1..P-6 MET, P5 caveat, venue xn-4090-gpu2) | DONE (787b2980…) | seal BRIEF-AMEND; ledger D-005/D-006/P-B1 update (ed20dc20…) |
| P6a | B1-P0 asset readiness (CPU): overlay, AS-1..AS-5, 10 CPU tests | DONE (code 63ef8bc6…, assumptions 9794f3ef…, test log 430c0f3c…) | seals P6A-* |
| P6b | B1-RT: RT-1..RT-5 CPU; RT-6..RT-8 job on xn-4090-gpu2 | PENDING | — |
| P6c | Seal `spikes/B1/PLAN.md` | PENDING | — |
| P6d | Transfer arms job READY (xn-4090-gpu2) | PENDING | — |

---

# progress.md — P6 Class-2 C apply (method v1.1 sha256 9bdc872e…590afc0 + OVERLAY-001; decision 934b3c9b…)

| Step | Description | State | Evidence |
|---|---|---|---|
| P6C2-M0 | Method boot: pin sha verified; overlays README + OVERLAY-001 read; A.6/A.7 read. Non-contest infra packet (A1.1-6), no new overlay, no contest roster | DONE | pin 9bdc872e… |
| P6C2-AUTH | Owner decision Class-2 C verified (934b3c9b…) and sealed | DONE | seal OWNER-DECISION |
| P6C2-AMEND | `spikes/B1-RT/AMENDMENT-C2-rt4.json` waive=[RT-4], slot_rule=first, disclosure + claim scope | DONE (32143be4…) | seal AMENDMENT-C2 |
| P6C2-VERDICT | `verdict_rt.py --amendment` → INCOMPLETE waived=[RT-4] not_run=[RT-6,RT-7,RT-8]; FAIL bytes kept as `results-verdict-fail-rt4-preamend.json` | DONE (ff129d51…) | seal B1RT-RESULTS |
| P6C2-JOBPREP | RT job inputs: upstream patch, driver, tarball (62 files), run.sh; path-root fix in prepare_b1_data/transfer; RT-8 (b) sha check in rt_gpu | DONE (tgz 3cbb7726…) | seals P6B-* |
| P6C2-MOCK | Driver CPU mock attempts 1 (mock dir bug), 2 (DONE; mid-run edit), 3 (DONE clean); verdict_rt reads the bundle | DONE | seals P6B-DRIVER-MOCK* |
| P6b-JOB | `p6-b1-rt` DRAFT → READY | DONE (b54852a3…) | seal JOB-JSON state=READY |
| P6c | `spikes/B1/PLAN.md` sealed | DONE (1088752b…) | seal SEAL spikes/B1/PLAN.md |
| P6d-prep | `p6-b1-arms` DRAFT (gated on RT SCORED PASS; driver/verdict/tarball TBD) | DONE as DRAFT (9f71dd1e…) | seal JOB-JSON state=DRAFT |
| P6C2-ASK | ASK closed by pointer to 934b3c9b… (appended) | DONE (4ff80e44…) | seal ASK-CLOSED |
| P6C2-STATUS | STATUS.md + copy STATUS-20261026-1951-EDT.md | DONE (f2551dc4…) | seal STATUS |
| NEXT | Manager relay START p6-b1-rt on xn-4090-gpu2. No SSH / GPU from the Orchestrator | PENDING | — |
| P6B-SCORE | Seal line checked → deposit `36cc77dc…` opened read-only → verdict_rt `2341a93d…` with `--gpu-open` and `--amendment` C2 → **BLOCKED**: RT-6/7/8 not_run, RT-4 waived; INFRA (download) HTTP 403 fetch_clip | DONE (results c3a55e25…) | seal VERDICT-B1RT |
| P6B-SCORE-JOB | `orch/jobs/p6-b1-rt.json` set to SCORED; runs.log and deviations appended; STATUS updated | DONE (eb7db827…) | seal JOB-JSON / STATUS |
| NEXT | Manager: choose the fetch fix for attempt 2 (byte-identical inputs, PLAN §4), then READY or relaunch if authorized. p6-b1-arms stays DRAFT | PENDING | — |
| P6-FIX2-PATCH | `rt_cpu.fetch_clip` Fix#2 (decision 768d6a0a…): local LAFAN1_G1_DIR → hf_hub_download → urllib; sha256 pins; box smoke 4/4 pins, B1DATA pass=True; negative tests raise | DONE (907022c2…) | seal P6-FIX2-RTCPU |
| P6-FIX2-RESEAL | Attempt-1 inputs copied to packets/P6/attempt1/; tarball rebuilt via make_b1rt_tgz.sh (MANIFEST diff = rt_cpu.py only; 0 .csv); run.sh LAFAN1_G1_DIR + CSV preflight; AMENDMENT-FIX2-fetch.md (not byte-identical, disclosed) | DONE (tgz 85d2cc87…, run.sh 1bf87ff4…) | seals P6-FIX2-* |
| P6-FIX2-JOB | `p6-b1-rt` SCORED(a1) → READY attempt 2/2; mutex gpu0; slot_rule=first; C2 32143be4 unchanged; p6-b1-arms DRAFT | DONE (09527372…) | seal JOB-JSON state=READY a2 |
| NEXT | Relay: verify 4 CSVs on host, then START p6-b1-rt attempt 2 on xn-4090-gpu2 gpu0. No SSH / GPU from the Orchestrator | PENDING | — |
| P6B-A2-SCORE | p6-b1-rt attempt 2/2 Fix#2 deposit 4e49c3e9… opened read-only after DEPOSIT seal; verdict_rt 2341a93d --gpu-open --amendment C2 32143be4 → **PASS** (RT-6/7/8 pass, RT-4 waived, RT-5 recorded); 1.2258 GPU-h | DONE (results 126c2334…, job c595ed91…) | seals VERDICT-B1RT-A2, JOB-JSON SCORED |
| P6-ARMS-GATE | p6-b1-arms gate (1) met; stays DRAFT (ready_prereqs 2–4 unbuilt: driver, verdict_b1.py, tarball/run.sh) | ASK (ASK-P6-ARMS-prereqs-20261026.md) | — |
| NEXT | Manager: answer arms-prereqs ASK; then Orch builds/seals prereqs and flips arms READY (no new START) | PENDING | — |
| P6D-BOOT | Method pin v1.1 9bdc872e verified; OVERLAY-001 read; A.6/A.7 read; non-contest infra packet (PLAN §9 roles), so no new roster or overlay; authority shas a400ffd7 / 934b3c9b / 1088752b / 126c2334 / c595ed91 / 4e49c3e9 verified | DONE | — |
| P6D-DRIVER | `packets/P6/b1arms_driver.sh` (+ `b1/b1arms_helper.py`): PLAN §3-§8, B0 §4.3 harness stop, 10-pt eval with one re-exec, cap 9.0 h, §4 src sha check, gpu_used.csv(.txt), resume. CPU mock 5 runs: nominal + INFRA→a2 + eval re-exec / cap / kill+resume / src mismatch / run.sh smoke | DONE (10bfc76b…, mock 8a50a06b…) | seal P6D-ARMS-DRIVER |
| P6D-VERDICT | `spikes/B1/verdict_b1.py` PLAN §5-§6 literal; fixtures 33/33 OK + 2 end-to-end on mock bundles; sealed before any arms deposit exists | DONE (62c3ae20…, log 55475c5b…) | seal VERDICT-TOOL |
| P6D-PACKET | tarball `junior_b_colab-P6-B1ARMS.tgz` (deterministic, 63 files, shared files byte-identical to B1-RT) + manifest; `orch/jobs/p6-b1-arms/run.sh` | DONE (tgz 0f18b8bb…, run.sh 72bdf169…) | seals P6D-ARMS-* |
| P6D-READY | `orch/jobs/p6-b1-arms.json` DRAFT → **READY** (upload[] filled; venue/mutex/cap/slot_rule/plan_ref unchanged); STATUS + copy STATUS-20261026-2201-EDT.md. D-001 Provisional; P5 NO_GAIN/u_deficit caveat kept | DONE (4895c173…) | seal JOB-JSON state=READY |
| NEXT | Relay: START p6-b1-arms on xn-4090-gpu2 gpu0; deposit + seal DEPOSIT xn4090 before opening; score with verdict_b1.py. No SSH / GPU from the Orchestrator | PENDING | — |
