# FOLLOWON_BRIEF — B1 eval metric validity and clip-failure (home humanoid)

**Status:** SEALED, **Provisional**. Diagnostic brief only. It changes no verdict, no PLAN and no ledger decision.
**Written:** 2026-10-27 ~06:20 EDT (UTC times are in `logs/seal.log`) by the Orchestrator (Claude · claude-opus-5-5, Claude Code). CPU only. No GPU, no Colab, no SSH.
**Authority:** `orch/owner-decisions/20261027-1800-AsiaShanghai-b1-eval-metric-followon-brief-START.md` sha256 `02f949927a10d448c392e201384f1f5efbdc7047c9b807a5835c15d19cfbb795`. Prior close: `orch/owner-decisions/20261027-1745-AsiaShanghai-p6-arms-CLOSE-INCONCLUSIVE.md` `5d8cf393044efcab8ab899ae9c51a463f7a2214643ea7c87eddf34127c4d2ebd`.
**Method:** global v1.1 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0` (sha verified at boot) + `method/local/README.md` specials 1–5 + `OVERLAY-001`. The boot analysis found no need for a new overlay: this is a single-author, non-contest diagnostic packet, so A.7 roster allocation does not apply and program-root `roster.md` (`5be8a85d…`, frozen) is unchanged. **Disclosed:** no cross-family red team was run on this brief (see §6).
**Labels:** **[OBS]** = counted directly from sealed artifacts. **[INF]** = inference from those counts or from code. **[PROP]** = proposal.

---

## 1. Sealed verdict (restated; not reopened)

```
B1_VERDICT verdict=PASS outcome=INCONCLUSIVE failing=[] aulc_HA_xfer=0.5361342107547861 aulc_HA_scratch=0.5023742432955027 aulc_HM_xfer=0.519483948911739 se=0.014513165235814461 partial_outcome=null plan=1088752b tool=62c3ae20
```

| Artifact | sha256 (verified at boot) |
|---|---|
| `orch/reports/VERDICT-P6-b1-arms-attempt1-results.json` | `64644e3c594de07a6819b685b1d0f956849eaafbff56b3ad87eab0cbb70c1403` |
| `orch/reports/VERDICT-P6-b1-arms-attempt1-20261027.md` | `90a7922141eb2bba4fcfbeffab73ddb0d448503eff25facceab03b9e89cb8034` |
| `orch/jobs/p6-b1-arms.json` (SCORED/CLOSED) | `4538b088382b5d2a1a4cf86523e18210228ae7a188f2ed17980114d539951a32` |
| `logs/xn4090/2026-10-27/b1arms-20261027-0935.tgz` (read-only) | `f95155af47357026d69f7c06f01c3d20ca806aa3378fce125322001d1094126d` |
| `spikes/B1/verdict_b1.py` | `62c3ae20151345950e44541569c45599860bf5c996c4b98f0243eada0f3b6ed6` |
| `spikes/B1/PLAN.md` (not amended here) | `1088752ba26a8798d721aa93d6e10d1b7bdb7fb924d9d72879acc78d8c2304c8` |
| Gate `orch/reports/VERDICT-P6-b1-rt-attempt2-results.json` (PASS a2, waived=[RT-4]) | `126c23349ef6770ce7a8c5e3d9d7b60c66dceb7803ae27824f8d2651cc07be2d` |

**The INCONCLUSIVE outcome stands.** The sealed metric gives xfer/scratch = 1.067, short of the 1.2 needed, so the result is not KILL and not SIGNAL. Nothing below re-scores the outcome. All PLAN §0 disclosures still apply: the P5 caveat (Δρ_U(0.2) = −0.557, NO_GAIN, u_deficit), RT-4 waived under Class-2 option C, and the claim scope (within-plant arm comparison on RT-a references).

## 2. Where the metric comes from (code) [OBS]

The upstream benchmark, `packets/P6/upstream-b1/SuperMimic-Reproduced/src/supermimic/eval/benchmark.py` (sha256 `81ab68c5…`, identical to `pristine/`), computes:

- `norm_return = Σ_t r_t / (max_r · steps)`, with `max_r = 0.1` and **`steps` = the steps actually survived**, not the clip length `frames`.
- `failed = term` (true when a termination fires before the clip ends). Terminations come from `envs/mdp/terminations.py` (`6335cfe6…`): root height deviation > 0.25 m, or root tilt deviation > 0.8, measured against the **reference**. Neither checks horizontal root drift.
- `summary.mean_norm_return` (the PLAN §5 R_k) is the unweighted mean of the 4 clip `norm_return` values. `summary.failed` is reported but **does not enter R_k**.
- `num_envs = min(64, n_clips) = 4`, the policy is deterministic, there is no noise or randomisation, and every rollout starts at frame 0. Each R_k is therefore **one deterministic rollout per clip**. The "64 envs" in PLAN §5 has no averaging effect.

So R_k is a **survival-conditioned per-step return**. A clip that terminates after 35 steps is scored only on those 35 steps, and failing has no direct cost.

## 3. Quantification (attempt-1 deposit, read-only) [OBS]

Script: `orch/analysis/b1-eval-metric/quantify.py` (`ebdc86d2…`), run with `python3 -I` on the open tree `logs/xn4090/2026-10-27/open-b1arms-20261027-0935/`. Output: `quantify.out` (`9aa84c7e…`). Per-eval table: `evals.json` (`743e7db8…`). There were 140 eval JSONs at mask 0.0, all exec1, with no re-executions.

### 3.1 Failed-clip count per eval, by arm

| Arm | evals | failed=1 | =2 | =3 | =4 | ≥2 |
|---|---|---|---|---|---|---|
| **H-A-xfer** | 30 | 19 | 2 | 1 | **8** | **11 (37 %)** |
| **H-A-scratch** | 30 | 25 | 1 | 0 | 4 | 5 (17 %) |
| **H-M-xfer** | 30 | 27 | 1 | 0 | 2 | 3 (10 %) |
| H-M-scratch | 30 | 27 | 1 | 0 | 2 | 3 (10 %) |
| H-A-frozen | 10 | 4 | 1 | 1 | 4 | 6 (60 %) |
| H-A-xfer-noscale | 10 | 9 | 0 | 1 | 0 | 1 (10 %) |
| **All** | **140** | **111** | 6 | 3 | **20** | 29 |

Every eval has failed ≥ 1, so 140/140 evals fail at least one clip. Evals with failed ≥ 2 occur at every eval point except it 1440: it160 4, it320 3, it480 2, it640 5, it800 4, it960 3, it1120 5, it1280 1, it1600 2.

### 3.2 Per seed and eval point (it 160 → 1600)

| Run | failed per point | R_k per point |
|---|---|---|
| H-A-xfer s0 | 3 1 1 4 4 1 4 1 1 1 | .602 .498 .501 .567 .632 .495 .668 .504 .519 .507 |
| H-A-xfer s1 | 1 4 4 1 1 4 4 1 1 1 | .518 .585 .586 .511 .498 .574 .630 .518 .490 .528 |
| H-A-xfer s2 | 4 1 1 2 1 1 1 1 1 2 | .603 .488 .484 .510 .506 .520 .521 .519 .507 .528 |
| H-A-scratch s0 | 1 1 1 4 1 1 1 1 1 1 | .512 .517 .463 .605 .488 .506 .488 .517 .524 .521 |
| H-A-scratch s1 | 1 1 1 1 1 1 1 1 1 1 | .519 **.204** .521 .506 .473 .518 .519 .508 .513 .502 |
| H-A-scratch s2 | 1 2 1 4 4 4 1 1 1 1 | .563 .525 .436 .573 .561 .525 .506 .513 .490 .518 |
| H-M-xfer s0 | 1 1 1 1 1 1 2 1 1 1 | .508 .516 .513 .513 .519 .516 .486 .514 .479 .517 |
| H-M-xfer s1 | 1 1 1 1 1 1 1 1 1 1 | .519 .562 .516 .516 .470 .510 .508 .509 .515 .516 |
| H-M-xfer s2 | 4 1 1 1 1 1 4 1 1 1 | .622 .503 .519 .517 .518 .521 .663 .501 .518 .525 |
| H-M-scratch s0 | 1 1 1 1 1 1 1 1 1 1 | .519 .519 .518 .518 .517 .518 .499 .517 .519 .519 |
| H-M-scratch s1 | 1 1 1 1 1 1 4 1 1 2 | .519 .519 .518 .517 .517 .517 **.274** .517 .517 .540 |
| H-M-scratch s2 | 1 1 1 1 4 1 1 1 1 1 | .519 .520 .519 .518 .574 .517 .518 .517 .518 .516 |
| H-A-frozen s0 | 4 4 4 4 3 2 1 1 1 1 | .596 .637 .631 .642 .542 .569 .517 .518 .517 .518 |
| H-A-xfer-noscale s0 | 1 1 1 1 1 1 1 3 1 1 | .502 .500 .453 .502 .529 .510 .511 .586 .505 .527 |

### 3.3 R_k versus failure and coverage

Coverage is the share of the 43 753 clip frames that the eval actually survived.

| failed | n | R_k mean | R_k range | coverage mean |
|---|---|---|---|---|
| 1 | 111 | 0.5082 | 0.204–0.563 | 0.970 |
| 2 | 6 | 0.5262 | 0.486–0.569 | 0.701 |
| 3 | 3 | 0.5763 | 0.542–0.602 | 0.364 |
| 4 | 20 | **0.5875** | 0.275–0.668 | **0.051** |

Pearson(R_k, coverage) = **−0.560** and Pearson(R_k, failed) = **+0.554** over the 140 evals: **the less of the clips a policy survives, the higher it scores.** The median all-failed eval survives 376.5 of 43 753 frames (0.9 %). Its R_k averages only the first ~0.7–2 s of each clip. The only all-failed eval that scores low is H-M-scratch s1 it1120: all 4 clips fail at steps 33–36 (an immediate fall), giving R = 0.274.

### 3.4 Per clip

| Clip (frames @50 fps) | failed / 140 | fail_step | norm_return when failed / when survived |
|---|---|---|---|
| dance1_subject1 (6574) | **140** | **= 5336 in 116/140** (106.7 s, 81.2 % of the clip), identical across all six arms, both architectures, every init and seed. The other 24 fail at 36–3600 | 0.520 / — |
| jumps1_subject1 (12222) | 24 | median 80.5 (0.66 %), max 3635 | 0.586 / 0.502 |
| run1_subject2 (11891) | 23 | median 117 (0.98 %), max 7545 | 0.570 / 0.437 |
| walk1_subject1 (13066) | 25 | median 75 (0.57 %), max 8080 | 0.602 / 0.590 |

Failure patterns: {dance1 only} 111, {all four} 20, and 9 other mixtures. Non-dance clips fail **early** (under 10 % of the clip) in 65 of 72 cases, and on average each failed clip scores higher than the same clip when survived.

### 3.5 Which reward terms move (per-step mean, dt-scaled; ceiling in brackets)

| Term [ceiling] | failed=1 mean (sd) | saturation | failed=4 mean | saturation |
|---|---|---|---|---|
| global_root_pos [0.01] | 0.00062 (0.00002) | **0.06** | 0.00690 | **0.69** |
| global_root_ori [0.01] | 0.00203 (0.00027) | 0.20 | 0.00475 | 0.48 |
| body_pos [0.02] | 0.01930 (0.00011) | **0.97** | 0.01845 | 0.92 |
| body_ori [0.02] | 0.00295 (0.00058) | 0.15 | 0.00147 | 0.07 |
| body_lin_vel [0.02] | 0.01571 (0.00005) | 0.79 | 0.01615 | 0.81 |
| body_ang_vel [0.02] | 0.01112 (0.00021) | 0.56 | 0.01329 | 0.66 |

The all-failed R_k excess (+0.079) comes almost entirely from the **global-root terms**, which score well only before global drift builds up. In nominal evals, the policy survives about 97 % of the frames while global root-position reward is about 6 % of its ceiling. That is, the robot stays upright but drifts away from the reference trajectory, and the terminations do not test for this. Body_pos (97 % saturated, sd 1e-4) and body_lin_vel (sd 5e-5) are near-constant offsets that do not discriminate between arms.

### 3.6 Training-side context (TB dumps, `meta/tb_*.json`)

`train/episode_norm_return` uses the same survival-conditioned normalisation. It stays at 0.40–0.55 for all 14 runs from it 50 to it 1600. `train/episode_len` grows from about 30 to about 100–450 steps, noisily, with a common spike near it 500 in most scratch and H-M runs. The quantity that does change with training, survival, is the one R_k removes. [OBS for the numbers; INF for the reading]

### 3.7 Upstream evals (29-DoF reference body, D-005 / D-006) [OBS]

`orch/analysis/b1-eval-metric/p4p5_failstats.out` (`4d677eec…`):

- P4 B0 results (`76507d8a…`): mask-0 clip evals **112/112 failed**, median fail_step 61, max 2089.
- P5 B2 results (`c184bb88…`): **168/168 failed**, median 59, max 2566.

The same survival-conditioned R therefore scored B0 non-inferiority and the B2 retention ratios, on 29-DoF policies that survived about 1.2 s per clip. **This brief does not reopen P4/P5** (1800 decision §5). This is a disclosure for the Manager (§7).

### 3.8 Deliberately not computed

Arm-level AULC and outcomes under any alternative metric were **not** computed. A future amendment should choose its metric before seeing what that metric does to H-A-xfer versus H-A-scratch (see §5 a1/a2). Every per-eval quantity above is descriptive.

## 4. Hypotheses

| ID | Hypothesis | Label | Evidence for / against | Weight |
|---|---|---|---|---|
| H1 | **Metric definition.** The per-step normalisation by survived steps rewards early termination and ignores the lost horizon, so R_k is not monotone in tracking quality | [INF] from code §2 and data §3.3 | Coverage 0.05 → R 0.588 vs coverage 0.97 → R 0.508. r = −0.56. Matches the code line exactly | **Primary. Near-certain.** |
| H2 | **Reference defect (retarget QA, RT-4 waived).** dance1 frame ~5336 is unattainable on the home body (root height or tilt step in the RT-a reference), giving a constant "failed ≥ 1" floor that is a property of the references, not of the policies | [INF] | Identical fail_step in 116/140 evals across architectures, inits and seeds. dance1 RT QA failed (clip-frac 0.281, penetration p95 0.0202 m, root-height ratio p5 0.898). Not verifiable on the box, because the home-body npz is on the GPU host only (X-002) | High for dance1; explains `failed ≥ 1`, **not** the R inflation |
| H3 | **Harness mask / eval harness.** The mask or the clip queue causes the failures | [INF] | All 140 are mask 0.0. The queue gives 1 env per clip, and resets are per-env. Terminations are the training ones (0.25 m / 0.8). No harness defect found | **Low. Ruled out as cause.** The harness does add single-sample variance (H5) |
| H4 | **Reward scaling / composition.** The fixed `max_r = 0.1`, saturated terms (body_pos ~0.97) and a drifting global-root term compress R into ≈0.50–0.52 with a large constant offset. A **ratio** criterion (xfer ≥ 1.2 × scratch) on an offset metric is close to unattainable | [INF] | Nominal-mode sd of body_pos 1e-4 and lin_vel 5e-5; root_pos 6 % saturated with sd 2e-5. Arm AULC range 0.50–0.57. 1.2 × 0.502 = 0.603 would need R above every nominal eval | High as a cause of **flat R_k** and of INCONCLUSIVE being structurally likely |
| H5 | **Eval horizon / sampling.** One deterministic rollout per clip on long clips (131–261 s), at 10 points, makes R_k a single draw dominated by rare collapse events (a policy falling within ~35–120 steps at a given checkpoint). Training survival is still unstable at 1600 iterations (episode_len ~100–450) | [INF] | 29/140 evals are multi-fail. Collapses are scattered across seeds and points (§3.2) with no monotone trend | Medium. Explains the **scatter**, which AULC then integrates |
| H6 | **Arm × collapse interaction.** H-A-xfer collapses more often (11/30 multi-fail vs scratch 5/30, H-M-xfer 3/30). Under H1 each collapse *raises* its R_k, so part of the +0.034 xfer–scratch AULC gap may come from collapse frequency rather than learning speed | [INF], not tested (§3.8) | Counts in §3.1 | Unknown sign once corrected. **This is why the INCONCLUSIVE reading should not be read as "almost SIGNAL".** |

## 5. Candidate remedies (ordered as required)

"Re-score" means recomputing from the sealed attempt-1 eval JSONs. Every field needed (`norm_return`, `steps`, `frames`, `failed`, per-clip `terms`) is in the deposit. Any re-score of attempt 1 is **post hoc** on observed data. It must be labelled as such, it cannot replace the attempt-1 machine line, and it stays Provisional.

| # | Remedy | Class | Venue | Sealed PLAN amendment before any re-score? |
|---|---|---|---|---|
| **a1** | **Metric redefinition, completion-aware.** R_full = mean over clips of Σr / (max_r · frames) = `norm_return · steps / frames`, so unsurvived frames count as zero. Report the survival fraction S = Σsteps / Σframes and the multi-fail count beside it. Optionally a tracking-only variant that drops the global-root terms | **2** (changes the scoring input) | **CPU** (from deposit) | **Yes.** Amendment + `verdict_b1.py` v1.1 sealed and CPU-mocked before it reads the deposit. Human-lead signature |
| a2 | **Invalid-eval handling.** Pre-registered rule: an eval with any non-reference-defect clip failing below X % of the clip is a "collapse". Either score it via a1, or mark it invalid with a pre-registered imputation and a cap on invalid points per run | 2 | CPU | Yes |
| a3 | **Criterion form.** Replace the 1.2× ratio with a difference margin (or a ratio on an offset-free metric), pre-registered on a1's scale | 2 | CPU | Yes (with a1) |
| a0 | **Observation-only report.** Add S, R_full and the collapse counts to the record without touching the verdict | 1 (symmetric observation) | CPU | No. **Not recommended before a1:** it would show arm-level effects of the candidate metrics before the amendment chooses one (§3.8) |
| b1 | **Clip set: dance1 handling.** Pre-register a dance1 window [0, 5300) or an exclusion, and do not count the fixed-frame failure as a failure | 2 | CPU (re-score of failure counts / R_full) | Yes |
| b2 | **Verify H2.** Read-only dump of the home-body dance1 reference root height/tilt for frames 5200–5400, from the npz on the GPU host | 1 (observation only) | **xn-4090 host, CPU-only access** (data is host-resident). Needs a Manager START (no GPU) | No for the check itself. Any resulting clip change goes under b1 |
| b3 | **Eval protocol.** Add an xy-drift termination or metric; multiple start frames / rollouts per clip to cut single-draw variance | 2 | **xn-4090 GPU**, re-eval of existing checkpoints (no retrain), if the intermediate checkpoints are retained on the host (unverified) | Yes |
| b4 | Mask changes | — | — | Not indicated. Mask 0.0 is not implicated (H3) |
| c | **More seeds** | 2 | xn-4090 GPU. About 0.54 GPU-h per run incl. evals (7.50 h / 14 runs). +3 seeds × 3 primary arms ≈ 4.8 GPU-h | Yes (PLAN §5 already requires it). **Not recommended before a1:** more seeds add precision to a quantity H1 shows is mis-specified |
| d | **RT-b better references** (keypoint IK) | 2. In practice a new B1-RT packet plus a full arms re-run | CPU (retarget + QA) then xn-4090 GPU (all arms) | Yes, plus a new RT PLAN. Addresses H2 and the claim-scope confound. Largest cost; defer until a1/b2 show whether references or the metric dominate |
| e | **No action.** Accept INCONCLUSIVE as is | 0 | — | No. Minimum: the H1 disclosure (§3, §3.7) is carried into any citation of D-005/D-006/B1 |

### Amendment outline (proposal only; PLAN.md is not amended in this packet) [PROP]

`spikes/B1/AMENDMENT-M1-eval-metric` (Class 2), appended under PLAN §5, never edited in place:

1. **Scope:** re-score the sealed deposit `f95155af…` only. No training, no GPU, no new seeds.
2. **Primary metric** R_full,k (a1). Pre-register **before any computation**: the dance1 rule (b1: window or exclusion; one is primary, the other a sensitivity), the root-term variant as secondary or omitted, and the collapse rule (a2).
3. **Criterion:** a pre-registered form on the R_full scale (a3), with SE as before (ddof = 1). The KILL/SIGNAL structure is kept.
4. **Labelling:** "post-hoc re-score (M1)". The attempt-1 machine line stays on record and is not superseded. Outcome cap Provisional, single-candidate. Depth rules A1.1-1 unchanged.
5. **Tool:** `verdict_b1.py` v1.1. The v1.0 logic is kept verbatim behind a flag, with a CPU mock test and the tool sha sealed before it opens the deposit. It is run by a non-adjudicator process (OVERLAY-001 rule 6).
6. **Red team:** `codex-astra` high (A.6 secondary family) reviews the amendment text before seal. This also closes the PLAN §9 gap.
7. **Kill criterion for M1 itself:** if fewer than 2 of the 3 primary arms have valid evals under the a2 rule, M1 reports BLOCKED, not an outcome.

## 6. Non-goals (this brief and any immediate follow-up)

- **No attempt 2** of `p6-b1-arms`. PLAN §7 does not authorise it, because the job did not fail on INFRA.
- **No Colab**, no xn-4090 GPU START, no SSH from this packet.
- **No P4/P5 reopen.** §3.7 is a disclosure, not a re-adjudication of D-005/D-006.
- **No seed add** without a sealed amendment (PLAN §5).
- **No depth-3 build** on B1 without a further signature (A1.1-1). B1 stays Provisional, single-candidate, INCONCLUSIVE.
- No edit to `spikes/B1/PLAN.md`, the verdict tool, the deposit or the open tree in this packet.
- No arm-level computation under alternative metrics in this packet (§3.8).
- **Disclosed gap:** no cross-family red team on this brief. Its findings are counts and code reading, reproducible from the cited script.

## 7. Recommendation (Manager next step)

The flat R_k and the "all-failed scores higher" pattern are explained by the metric itself: upstream `norm_return` divides by survived steps, so early collapse raises the score (H1). A reference-side event at dance1 frame 5336 (H2) adds a constant one-clip failure floor, and R is compressed by saturated and drifting terms (H4). B1's INCONCLUSIVE therefore says little about transfer either way, and adding seeds would not fix that. **Recommend:** HOLD the arms as closed. If the Manager wants an answer from the existing data, sign a narrow **Class-2 amendment M1** (outline §5) for a **CPU-only, post-hoc-labelled re-score** of the sealed deposit with a completion-aware metric pre-registered before any computation, after a `codex-astra` high red team of the amendment. Optionally also authorise a **CPU-only, no-GPU read** of the dance1 reference on the xn-4090 host (b2) to confirm H2. Defer seeds (c) and RT-b (d) until M1 and b2 report. Separately, append a ledger observation that D-005/D-006 were scored on the same survival-conditioned R (P4 112/112, P5 168/168 clip evals failed, median ~60 steps). Do not reopen them, but carry the caveat into any citation and weigh it before any packet builds on them.
