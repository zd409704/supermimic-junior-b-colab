# spikes/B2/PLAN.md — P5 B2 mask / ablation on B0 checkpoints, pre-registered

**Written by:** Orchestrator (Claude Code, `claude-opus`, medium effort), P5 wake, 2026-10-26 EDT (America/Toronto). **Method:** v1.1, sha256 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0` (re-verified at boot) + `method/local/README.md` specials + `method/local/OVERLAY-001-owner-colab-runner.md`. No new overlay is needed (§13).
**Revision:** draft 3. Drafts 1 (`65cae1df…`) and 2 (`f11633a2…`) were revised after two cross-family red-team rounds (§12 item 9). **Status:** sealed when its sha256 is appended to `logs/seal.log` (event `SEAL spikes/B2/PLAN.md`). After sealing, changes are appended `Amendment vN` blocks only. A change to a scoring input (metric, threshold, seeds, arms, attempt cap, pass rule) is Class 2: the human lead signs it before P5 attempt 1 starts, otherwise it waits for the next packet (method §10.4).
**Decision cap:** Provisional. **Nothing in this file has been executed.** No P5 training, eval or GPU spend has happened. Spending starts only after this PLAN is sealed, the P5-prep items (§2.3) are sealed, and the Manager issues START for a runner packet that cites this PLAN's sha256 (§10).
**Wording:** "home humanoid" / "plant" for the second body (not used in B2). The B2 body is "the upstream 29-DoF humanoid". No commercial product brands appear in this file.
**Not reopened:** P4 is closed: machine **PASS / NONINFERIOR** (superior flag on primary R_H), Provisional. This PLAN does not re-score P4, does not modify `spikes/B0/PLAN.md` (it only points at it) and does not rewrite the P4 deposit archive.

---

## 0. Authority and inheritance (by ledger ID, method §13.3)

| Item | Binds this packet as | Source |
|---|---|---|
| D-001 Junior-(B) decoder on the unchanged WM loop | Explicit assumption (Provisional) | `program-ledger.md` |
| D-003 descriptor v2 + action-scale handling | Explicit assumption (Provisional), frozen in code | `packets/P1/ddesc/decision.md` |
| D-004 P1 scaffold freeze, extended by CR-B0-1 | Explicit assumption (Provisional). Frozen code inputs (§2) | `packets/P1/FREEZE_MANIFEST.md`, `packets/P4/MANIFEST_ADDENDUM.md` |
| B0 PLAN (base `ed6b6a54…2c52557`, full with Amendment v1 `356c389f4c2efd47249f741b23f69bde19043a0ed8dc6e2c637abe397b9e145a`) | Definitions referenced by ID (M-1 R_H, T = 500, V-1…V-4, L-1, L-2, §3.3 attempt classes, §6.3(a) divergence after Amendment v1). Not modified | `spikes/B0/PLAN.md` |
| P4 machine verdict: PASS / NONINFERIOR, `b0_outcome = NONINFERIOR`, `superior = true` | **Input to the combined gate (§8), cited only.** Not recomputed | `orch/reports/VERDICT-P4-b0-attempt1-relaunch3-results.json` sha256 `76507d8a9488cd295add444d9e9463da1bf7ab62c2216733043c535f3c6f8d3d`; report `…-20261026.md` `2bb0de08…` |
| P4 deposit (sealed, opened for score) | Source of the threshold freeze (§5.4) and of the legacy M-10 table (§5.5). Not rewritten | `logs/xn4090/2026-10-26/b0-20261026-0919.tgz` sha256 `1f49118213d53538485303aa0b3f09bb5f068daeb06eb325045fd83a3118dde1` (seal `DEPOSIT xn4090` 2026-10-26T10:22:04Z); open tree `logs/xn4090/2026-10-26/open-b0-20261026-0919/` (read-only) |
| RV-2 (B2 mask-fairness arms as specified), RV-8 (equal env steps / updates primary), BLK-12 (paid GPU; XN-4090-GPU2 preferred when a sealed PLAN names it; no spend until a sealed PLAN asks) | Signed (owner delegated to Manager, 2026-10-26 00:36 EDT) | `orch/reports/DECISION-RV-BLK-20261026.md` |
| HF Hub unreachable on xn-4090; `HF_ENDPOINT=https://hf-mirror.com` works | Venue fact (§9.3) | `orch/reports/DIAG-P4-motion-fetch-20261026.md`, seal `DIAG-MOTION b818a714421f3a36ce32e77d8ad72ed8ac67fac2ab1338cf1e2475baff5ed5f7` |

**Depth disclosure (§13.3).** B2 depends on the B0 checkpoints (B2 → B0 → D-004 → D-001), all Provisional. The B2 outcome is capped at Provisional. RV-7/BLK-10 stays deferred to the B1 brief, as ruled.

---

## 1. Mechanism under test

SCHEME_PLAN §3: **robustness to missing joint-observation tokens**, on the single upstream 29-DoF humanoid, using the B0 decoders.

The shared per-joint attention decoder (Junior-(B), `id_mode=morph`) represents a missing joint observation by **removing the token** (key-padding mask; the masked joint's own state is zeroed before its query, `code/attention_policy.py` `forward`). The parameter-matched MLP has no notion of a missing token: a mask **zero-fills** that joint's observation columns (`code/mlp_baseline.py` `_column_keep`). The question has two parts, kept separate (RV-2):

1. **Untrained-mask condition (U).** On the P4 checkpoints, which were trained without masks, does the attention decoder retain more of its unmasked return than `mlp_matched` when 10% or 20% of the non-root joint tokens are dropped at eval?
2. **Trained-mask condition (T).** When both architectures are trained with the same token-drop augmentation (`train_mask_frac = 0.1`), and the MLP is given an explicit per-joint **mask-indicator** input (`mlp_mind`), does the attention advantage survive? A U gap that the T control removes is an "absence-representation advantage, not robustness under equal training" (SCHEME_PLAN §3).

Ablation (report-only): `attention_idx` (`id_mode=index`) asks whether the morphology keying matters, at mask 0 and under masks.

Architectural check: the permutation-equivariance check from the CPU smoke is repeated on GPU checkpoints (§6).

Motion encoder, world model, critic, env config, reward and reference clips are identical across arms and are not under test. **Only the decoder's observation input is masked.** The masks are drawn **independently at every decoder call** (every control step, every env); this is the frozen mask model, a flickering-sensor model, not a persistent sensor loss. It is disclosed (§12 item 4) and not changed.

---

## 2. Inputs (frozen) and P5-prep preconditions

### 2.1 Frozen inputs

| Input | Identity |
|---|---|
| Code tarball (base for P5) | `packets/P4/junior_b_colab-CR-B0-1.tgz`, sha256 `763867682e3cfa05ca8eb6382ffc9124be2347b898531c60b904061776c33bff` (seal TARBALL-P4; manifest addendum `packets/P4/MANIFEST_ADDENDUM.md`) |
| Frozen code used unchanged | All 12 D-004 files and all CR-B0-1 files byte-identical to the CR-B0-1 manifest. In particular `code/train_entry.py`, `code/eval_entry.py`, `code/attention_policy.py`, `code/mlp_baseline.py`, `code/descriptor_v2.py` (sha256 in `packets/P1/FREEZE_MANIFEST.md` §3; B0 PLAN §2.1) |
| Base config | `configs/b0_microbench.yaml` (CR-B0-1 (a), `d19e9297…`). P5 configs (§2.3 (a)) are byte copies of it with named changes only |
| Upstream | `https://github.com/CuboiLeo/SuperMimic-Reproduced` @ `d9be385b3eeb13a638fb33fb200d3bfd9be9839f` |
| Motion data | The 4 clips of the frozen config (`walk1_subject1`, `run1_subject2`, `dance1_subject1`, `jumps1_subject1`). Downloaded on the venue only, never copied back (X-002). BLK-11 accepted |
| P4 checkpoints (untrained-mask source) | The 6 scored gate runs' `ckpt_0001600.pt` and their `junior_policy.json` sidecars, **on the venue** (they never left it; B0 PLAN §8.1). Expected identity, from the sealed P4 deposit: see §2.2 |
| P4 M-10 eval JSONs | Open tree `logs/eval/<AID>/it0001600/exec1/*_mask{0.00,0.10,0.20}.json` for the 6 gate runs (sha256 in §5.4). Used **only** for the threshold freeze (§5.4) and the legacy table (§5.5), and the mask-0 files for the reproducibility check U-REPRO (§7.1). **Not used to score B2**, because their mask pairing across arms is unverified (§3) |

### 2.2 P4 checkpoint identity (expected; checked at run start by the driver, §4.1 step 0)

| P4 AID | Remote path (relative to the P4 upstream clone) | `ckpt_0001600.pt` bytes (P4 `meta/ckpt_dirs_ls.txt`, sha256 `6ddb861f…9e24`) | Sidecar sha256 (deposit `logs/attempts/<AID>/junior_policy.json`) |
|---|---|---|---|
| `b0_attention_s0_a1` | `logs/b0_attention_s0/` | 164415878 | `cc9cac5864d7845578975e2dd3883b53ea8705201ae7a9de55ac0abdadaa2767` |
| `b0_attention_s1_a1` | `logs/b0_attention_s1/` | 164415878 | `9085130f54e0ff9d568f075b7b2439d53c02a9437c8352a66fea64fcb2b30d09` |
| `b0_attention_s2_a1` | `logs/b0_attention_s2/` | 164415878 | `b84b39c174c1a18895b7f66118976039fdaec8c7304c788453c3f951f752edae` |
| `b0_mlp_matched_s0_a1` | `logs/b0_mlp_matched_s0/` | 164427663 | `e08618782fbf5ca107a74bd81494194055fbd50edb43b8eb528b134bbdca370a` |
| `b0_mlp_matched_s1_a1` | `logs/b0_mlp_matched_s1/` | 164427663 | `9a8a0e443aae59ab55ca82621892804c0ad5f1807302231df6c3a89b4dee83d0` |
| `b0_mlp_matched_s2_a1` | `logs/b0_mlp_matched_s2/` | 164427663 | `365096f41c67c789a7d9efc94c630ee259dc10ca5a2070a12cfc3c3098dd1641` |

The P4 upstream clone is expected at `/content/SuperMimic-Reproduced` on XN-4090-GPU2 (P4 `run.sh` ran under `/content`). The pre-registered candidate roots, tried in this order and no others: (1) `/content/SuperMimic-Reproduced`, (2) `/data/muchuan/p4-b0-attempt1/workdir/SuperMimic-Reproduced`. The first root at which **all six** checkpoints have the listed byte size **and** all six sidecars have the listed sha256 is used. P4 recorded no checkpoint sha256; the identity check is therefore size + sidecar hash + U-REPRO (§7.1), disclosed (§12 item 6).

### 2.3 P5-prep (CPU, on the box; a separate packet; must be sealed before START; not done here)

**CR-B2-1** is a change request against D-004 + CR-B0-1 consisting of **new files only**. Every D-004 and CR-B0-1 file stays byte-identical, and the manifest addendum proves it.

- **(a) Configs.** Byte copies of `configs/b0_microbench.yaml` with only these values changed:
  - `configs/b2_idx.yaml`: `run_name: b2idx`, `attention.id_mode: index`.
  - `configs/b2_mtrain.yaml`: `run_name: b2mt`, `b2.train_mask_frac: 0.1`.
  - No tyro argument changes. The upstream argv is therefore identical to P4's except `--run-name` and `--seed` (checked by B2-V-2).
- **(b) `mlp_mind` arm (RV-2 mask-fairness control).** A new decoder class and a wrapper entry point, new files under `packets/P5/`. The wrapper imports the frozen `train_entry` / `eval_entry` modules, adds `mlp_mind` to `train_entry.POLICY_ARMS` and wraps `train_entry.build_decoder` **before** `eval_entry` is imported, and otherwise calls the frozen `main()` unchanged. Frozen files are not edited. Specification:
  - Input = `[z, x ⊙ keep, ind]`: `x` is the scaled observation history exactly as in `MLPDecoder`; `keep` is the frozen `_column_keep` zero-fill; `ind` ∈ {0,1}^29 is the per-joint mask indicator (1 = masked), concatenated **once** (not per history frame). At mask 0, `ind` = 0.
  - Same tapered MLP family as `mlp_matched`, sized by the frozen `matched_hidden` routine to the attention arm's parameter count (464 001) with the enlarged input. Params must be within ±5% of 464 001 (checked by B2-V-3).
  - Same `auto_mask_frac` hook and the same `random_token_mask` call as the frozen decoders, so `train_mask_frac` and the eval mask stream (c) apply identically.
  - The sidecar records `policy: mlp_mind`, `params`, `mlp_hidden`, `train_mask_frac`.
- **(c) Fixed-seed mask-stream eval wrapper (RV-2 fairness procedure, §3).** A new eval entry point under `packets/P5/` that imports the frozen `eval_entry` and replaces the module-level name `random_token_mask` in `attention_policy`, `mlp_baseline` and the `mlp_mind` module with a function that has the **same semantics** (exactly k = max(1, round(f · 29)) tokens per row; f = 0.1 → 3, f = 0.2 → 6; root never in the J axis) but draws its uniform scores from a **dedicated** `torch.Generator` on the decoder's device, re-seeded at the start of every eval condition with the condition's mask seed (§3). It never touches the global RNG. For each condition it writes, beside the frozen benchmark JSON, `maskstream_<cond>.npz` (per decoder call: the boolean (N, 29) mask, bit-packed) and `maskstream_<cond>.json` (`seed`, `frac`, `k`, `calls`, `rows_per_call`, `sha256` of the packed stream). The frozen benchmark loop and JSON format are unchanged.
- **(d) GPU permutation check script** (§6) under `packets/P5/`.
- **(e) P5 driver** under `packets/P5/` implementing exactly §4 and writing exactly §9.1, plus `orch/jobs/p5-b2-attempt1/run.sh` and job JSON (§9.3).
- **(f) New tarball `packets/P5/junior_b_colab-CR-B2-1.tgz`**, deterministic as in P1/P4, plus `packets/P5/MANIFEST_ADDENDUM.md` listing all CR-B0-1 files with unchanged hashes and the new files. Both hashes go into `logs/seal.log`.
- **(g) CPU tests (log sealed):** `mlp_mind` shapes, param count within ±5%, indicator = mask; the mask-stream wrapper gives **identical streams** for an attention, an `mlp_matched` and an `mlp_mind` decoder under the same seed and call sequence, exactly k True per row, and nesting (mask at f = 0.1 ⊆ mask at f = 0.2 for the same seed and call; holds because both take the top-k of the same scores); the permutation script passes on CPU for `attention` (rel err < 1e-4) and reports a break for `mlp_matched` and `attention[id_mode=index]`; the frozen 14-test CPU smoke still passes.
- **(h) Verdict tool** `spikes/B2/verdict/verdict_b2.py` (+ fixture, tests), sealed as `VERDICT-TOOL-B2` **before** any P5 deposit is opened. It is run by an agent process that is not an adjudicator (OVERLAY-001 rule 6).

**Change-request status (instruction item 2).** CR-B2-1 adds an arm and an eval wrapper. Neither edits a frozen file. The `mlp_mind` arm is the RV-2 control that the human lead already accepted ("B2 mask-fairness arms as specified"). The fixed-seed mask stream is a scoring-input decision made **in this PLAN, before any P5 step**, so it is pre-registration, not a mid-run amendment. CR-B2-1 is **requested here**. It takes effect only when (1) the P5-prep packet has sealed (a)–(h) and (2) the Manager's START for the P5 runner packet cites this PLAN's sha256 and the CR-B2-1 tarball sha256. The Orchestrator does not sign for the human lead.

**Pre-start gates (all must hold, recorded in sealed P5-prep files, before P5 attempt 1 spends GPU time):**
- **PS-B2-1.** CR-B2-1 (a)–(g) sealed; CPU test log shows every (g) item passing.
- **PS-B2-2.** `VERDICT-TOOL-B2` sealed, fixture tests passing.
- **PS-B2-3.** Job JSON and `run.sh` sealed, `state = READY`, `env.HF_ENDPOINT = https://hf-mirror.com`, mutex `gpu0`, upload list = CR-B2-1 tarball + `run.sh` with sha256.
- **PS-B2-4.** Manager START cites this PLAN's sha256 and the CR-B2-1 tarball sha256.

A failed pre-start gate is not a P5 attempt and spends nothing. Checkpoint availability cannot be checked from the box (the Orchestrator does not SSH); it is checked at run start (§4.1 step 0) before any training.

---

## 3. Mask-seed fairness (RV-2): settled by source reading

**Finding (frozen code and P4 logs, read at P5 drafting).** In `--mode upstream`, `eval_entry.run_upstream` sets `policy.decoder.auto_mask_frac = f`. The decoders then call `random_token_mask(n, 29, f, device=…)` **with `generator=None`** on every forward call (`attention_policy.py` `AttentionDecoder.forward`; `mlp_baseline.py` `MLPDecoder.forward`). The masks therefore come from the **global CUDA RNG**, which is shared with everything else in the process. `eval_entry` itself does not seed it. However, the upstream benchmark builds a fresh env for every condition with `seed=0` (`src/supermimic/eval/benchmark.py`, `run_benchmark`), and every P4 `eval.log` prints `Setting seed: 0` once per condition (for example `logs/eval/b0_attention_s0_a1/it0001600/exec1/eval.log` lines 4, 176, 296). That line is printed by the env stack, outside the program's code. If it reseeds the global CUDA RNG, then each condition's mask stream starts from the same state in every arm. Whether the streams then stay identical depends on whether the env stack consumes the global RNG between decoder calls, and whether it does so in an arm-dependent way (resets after terminations, for example). Neither property has been read from source or observed. The benchmark runs `num_envs = min(64, 4) = 4` envs, one per clip, and calls the policy once per step until all four clips finish.

**Consequence.** The P4 mask JSONs **may or may not** have used identical masks across arms. Their mask pairing is **unverified**, not refuted. **B2 scoring does not use the P4 mask files.** They are used only to set the noise scale for the threshold freeze (§5.4) and are reported as a legacy table (§5.5) labelled `mask_pairing = unverified_global_rng`.

**Sealed procedure (used for all B2 scoring).**
- Every eval condition is (checkpoint, f, mask seed). Mask seeds: **K = 3, seeds {7100, 7101, 7102}**, identical for every arm, every checkpoint and both f.
- The CR-B2-1 (c) wrapper re-seeds its dedicated generator with the condition's seed at the start of the condition. The mask at decoder call c, env row e is therefore identical across arms whenever both arms make call c. Arms differ only in how many calls they make (clip lengths), so the streams agree on the common prefix. Because env e always plays clip e (4 envs, 4 clips), the pairing is exact per (clip, step).
- f = 0.10 and f = 0.20 under the same seed are **nested** (the 3 dropped tokens are among the 6).
- Mask 0.00 makes no draws and is evaluated once per checkpoint.
- **Mechanical check MS (§7.1)** verifies, from the recorded streams, that the procedure held in the run.

---

## 4. Arms, seeds, budget, attempts, exact run order

### 4.0 Arms

| Arm (tag) | Source | Decoder | Seeds | Condition | Role |
|---|---|---|---|---|---|
| `attention` ρ(f) (`b2u`) | P4 ckpt 1600 | Junior-(B), `id_mode=morph` | 0, 1, 2 (P4 seeds) | U | **Scored** (U comparison) |
| `mlp_matched` ρ(f) zero-fill (`b2u`) | P4 ckpt 1600 | MLP, +0.93% params | 0, 1, 2 | U | **Scored** (U comparator) |
| `attention_mtrain` (`b2mt`, arm `attention`) | New training, `configs/b2_mtrain.yaml` | Junior-(B), `id_mode=morph`, `train_mask_frac 0.1` | 0, 1, 2 | T | **Scored** (T comparison) |
| `mlp_mind_mtrain` (`b2mt`, arm `mlp_mind`) | New training, `configs/b2_mtrain.yaml` | MLP + mask indicator (§2.3 (b)), `train_mask_frac 0.1` | 0, 1, 2 | T | **Scored** (T comparator, RV-2 control) |
| `attention_idx` (`b2idx`, arm `attention`) | New training, `configs/b2_idx.yaml` | Junior-(B), `id_mode=index` | 0, 1, 2 | ablation | **Report-only** (never moves the verdict) |

**Seed counts versus SCHEME_PLAN §3 (draft 1 / 1 / 1).** The draft scheme listed 1 seed for each new training and "3 if budget allows" for `attention_idx`. This PLAN freezes **3 seeds for every new arm**. Reason, from P4 data: with 1 seed per arm, the noise scale of a ρ_H(0.2) difference is √(s_att² + s_mlp²) = 0.149 (P4 seed SDs 0.1135 and 0.0962). Two of those, ≈ 0.30, dwarf the draft T margin of 0.03, so a 1-seed T comparison could not distinguish anything. The budget allows 3 seeds (§10). Seeds may not be added without a sealed amendment.

### 4.1 Budget (RV-8) and run order

- **Primary budget for every new training: 1600 training iterations**, scored checkpoint = `ckpt_0001600.pt`, harness stop exactly as B0 PLAN §4.3 (F-1 unsuitable, Amendment v1). Same `num_envs` 512, batch 512, H 16, compile None, `--env.anchor-obs`, `checkpoint-interval 400`, `max-hours 1.5` safety cap, as in P4. **Equal env steps** (512 env steps per iteration, F-5) and **equal policy updates** (B2-V-2 requires `time/updates` = **624** at it 1600, the P4 value, for every new run).
- Masked training (`b2mt`) changes the decoder input only, not the number of env steps or updates.
- **Run order (single job, one venue, one GPU model):**
  0. **Step 0, checkpoint staging (before any setup that could modify `/content`).** Locate the P4 root per §2.2. `cp -p` the six `ckpt_0001600.pt` + `junior_policy.json` into `/content/p5_p4ckpts/logs/b0_<arm>_s<seed>/` (read-only source; the P4 tree is never written, moved or deleted). Record `ls -l` and sha256 of source and copy into `meta/p4_ckpt_identity.txt`. If no candidate root matches §2.2 in full, write `BLOCKED.md` (`p4_ckpts_unavailable`), deposit, stop. No training starts.
  1. Setup as B0 PLAN §4.1 with the CR-B2-1 tarball (`sha256sum` check → `meta/tarball_sha256.txt`; CPU tests → `meta/cpu_test_smoke.log`; `meta/nvidia-smi.txt`; `meta/pip-freeze.txt`). Motion data download with `HF_ENDPOINT` set (§9.3). **No V-0 env-sanity training** (the venue and stack were validated in P4); `meta/pip-freeze.txt` is compared with the P4 deposit's (`e63a57c5…`), and any difference is reported (`env_drift`).
  2. **U evals** on the six staged P4 checkpoints (§4.3), in the order attention s0, mlp_matched s0, attention s1, mlp_matched s1, attention s2, mlp_matched s2.
  3. **PERM** on the three staged P4 attention checkpoints (§6).
  4. **T trainings**, paired by seed: `b2mt_attention_s0`, `b2mt_mlp_mind_s0`, `b2mt_attention_s1`, `b2mt_mlp_mind_s1`, `b2mt_attention_s2`, `b2mt_mlp_mind_s2`. Each completed attempt is evaluated (§4.3) right after it finishes. PERM on each completed `b2mt` attention checkpoint.
  5. **Ablation trainings** `b2idx_attention_s0`, `_s1`, `_s2`, each evaluated after it finishes; PERM report-only.
- All scheduled cells run, even after a terminal outcome is known. No run is skipped or chosen.

### 4.2 Attempt rules

B0 PLAN §3.3 applies **unchanged**, with tags `b2mt` and `b2idx` (attempt ID `<tag>_<arm>_s<seed>_a<N>`, e.g. `b2mt_mlp_mind_s1_a1`): first completed attempt is scored; classes DIV / OOM / SEAM / INFRA; R-DIV regex; scoring-endpoint boundary; archive every attempt to `logs/attempts/<AID>/` without `*.pt`; live directory moved aside before attempt N ≥ 2; no resume. Differences for P5:
- **No LR-halved retry pair.** P5 has no `lr05` config. A DIV attempt is final for its cell.
- **Divergence (single definition for P5).** A new-training attempt **diverged** if B0 §6.3(a) holds for it: NaN/inf in any tb scalar at a step ≤ 1600, **or** an exception logged before the scoring-endpoint line whose final exception line matches R-DIV. This holds **whether or not the attempt completed** and whatever its §3.3 class. The clip clause §6.3(b) is omitted, as in B0 Amendment v1. A diverged attempt is final for its cell: it is the cell's scored attempt, and no retry is started.
- **Divergence in a T cell:** `t_status = diverged` (listing the AIDs). The cell is not replaced. The remaining T cells still run, evaluate and report. Precedence and exemptions are in §7.3.
- **Diverged runs: exempt and retained checks (every check in §7.1, one list).** For a diverged attempt the **endpoint-dependent** requirements are exempt: B2-V-1 completion, it-1600 point, timing tags and window coverage, and the NaN clause; B2-V-2(a) (updates at it 1600); B2-V-4 (eval content); MS for its evals; PERM. B2-L-1/L-2 are handled by §7.3. The **retained** checks are evaluated in full: B2-V-1 evidence integrity (exactly one tb file in `logs/attempts/<AID>/`, train log present, divergence evidence from that tb file or that log); B2-V-2(b) argv and (c) GPU name; B2-V-3 seams and sidecar fields. If a diverged attempt nevertheless completed, its evals and PERM still run (§4.1) and are **reported only**.
- **OOM, SEAM, or a second INFRA in a T cell:** BLOCKED (§7.3 row 1). In a `b2idx` cell: reported only.
- **INFRA cap** = 2 attempts per cell, as in B0.
- **Eval-only cells (U, step 2)** are not training attempts. An eval execution follows B0 PLAN §4.4: `exec2` only if `exec1` exited non-zero or did not produce all expected files; never a third; the scored execution is the first that passes B2-V-4.

### 4.3 Eval of one checkpoint (U checkpoints and every completed new attempt)

Run from `/content/SuperMimic-Reproduced` with the CR-B2-1 (c) wrapper and the run's config (`b0_microbench.yaml` for U, `b2_mtrain.yaml` / `b2_idx.yaml` for new runs):

| Checkpoint | Conditions |
|---|---|
| it 1600 (every U checkpoint and every new completed attempt) | mask 0.00 once; f ∈ {0.10, 0.20} × mask seed ∈ {7100, 7101, 7102}: **7 conditions** |
| it 400 / 800 / 1200 (new completed attempts only) | mask 0.00 once each (learning curve M-5, reported only) |

Output directory: `logs/eval/<ID>/it<IT>/exec<K>/` with `eval.log`, one benchmark JSON per condition named `<run>_<arm>_mask<f>_ms<seed>.json` (`ms0` for mask 0.00), and the mask-stream files. `<ID>` is `b2u_<P4 AID>` for U checkpoints and the attempt ID for new runs. The `[eval_entry]` argv line in `eval.log` names the checkpoint path (identity record).

---

## 5. Metrics (definitions frozen here)

All per-clip and summary fields are the frozen benchmark JSON fields used in B0 (B0 PLAN §5).

### 5.1 Return and retention

- **R_H(run, condition)** = B0 M-1 exactly: Σ_c norm_return_c · min(steps_c, T) / (4 · T), **T = 500**, over the 4 registered clips, checkpoint 1600.
- **R_H(run, f)** for f > 0 = mean over the 3 mask seeds of R_H(run, f, seed).
- **Retention ρ_H(run, f) = R_H(run, f) / R_H(run, 0.00)**, with the denominator from the **same P5 eval run** (mask 0.00 condition), not from the P4 file. `null` if the denominator is 0. Arm value ρ̄_H(arm, f) = mean over scored seeds.
- **Why R_H, not R_step (instruction item 4).** The sealed B0 primary metric is R_H. P4 showed that the per-step mean ranks the arms in the opposite order from cumulative return (R̄_step attention 0.401 < mlp_matched 0.466, while R̄_H 0.291 > 0.078). A per-step retention ignores the dominant effect of masking, which is earlier termination. ρ_H is therefore primary. ρ_step(run, f) = R_step(f) / R_step(0) is reported, with a non-binding shadow outcome (§7.2).

### 5.2 Comparison statistics (U and T alike)

For a condition X ∈ {U, T} with arms (a, b) = (attention, mlp_matched) for U and (attention_mtrain, mlp_mind_mtrain) for T, at f:
- Δρ_X(f) = ρ̄_H(a, f) − ρ̄_H(b, f).
- SE_X(f) = √(s_a²/n_a + s_b²/n_b), with s the sample SD of per-run ρ_H across seeds (ddof = 1) and n the number of scored seeds.
- **Primary f = 0.20** (SCHEME_PLAN §3). f = 0.10 is computed identically and reported.

### 5.3 Reported-only metrics

- **ΔR_X(f)**: absolute return under masks, R̄_H(a, f) − R̄_H(b, f), with its SE. It shows whether the arm that keeps a smaller fraction still keeps more absolute return.
- **Headroom retention** ρ*_H(run, f) = (R_H(f) − R_floor) / (R_H(0) − R_floor), with **R_floor = 0.0393** frozen (mean P4 mask-0 R_H of `mlp_matched` at it 400, a near-immediate-fall policy). `null` if R_H(0) − R_floor ≤ 0.01. This addresses the floor effect in §12 item 3.
- ρ_step, survival (Σ steps, per-clip steps, `failed`, `fail_step`), Cum (M-1c), all `summary.terms` (B0 §7 reporting rule: no per-step number without survival and cumulative beside it).
- Learning curve at it 400/800/1200/1600, mask 0 (new runs).
- Cost per new run (B0 M-3), and L-1/L-2 window values (B0 M-7, M-4).
- `attention_idx` ablation (§7.4).
- `mlp_mind_mtrain` versus P4 `mlp_matched` and `attention_mtrain` versus P4 `attention`, mask 0 and ρ: what masked training costs or buys each architecture. Cross-packet comparison, reported only.

### 5.4 B2 gain thresholds: frozen from P4 M-10 (instruction item 5)

**Data used.** Sealed deposit `b0-20261026-0919.tgz` (`1f491182…dde1`), open tree, scored executions `exec1` at it 1600, read via the sealed results file `76507d8a…` (`attempts.<AID>.eval.it0001600.mask<f>.rho_h`). Files:

| File (under `logs/eval/<AID>/it0001600/exec1/`) | sha256 |
|---|---|
| `b0_attention_s0_a1/…/b0_attention_s0_attention_mask0.00.json` | `43e9b53ad5fac82ed53f1b098d301b803f8db22f81bfa82abc1b3e627a03372e` |
| `…mask0.10.json` | `dbb9dd73447cda185ac1381a1956f4d7744242e8fe77ba2035452215fe3f5226` |
| `…mask0.20.json` | `0a8ef07f08286f0de18c80d1e12224bfaca54a99f7f800baa08c6db383b74930` |
| `b0_attention_s1_a1/…mask0.00.json` | `f19668e005051fc2d0d1c27b9712841ede20f5bad9483833561116cbacd07983` |
| `…mask0.10.json` | `730167e02bfdf8c349faf103e25d0ce5d04198a889069ff5827e4fe91369dd46` |
| `…mask0.20.json` | `9a45bfd5c605485bd605b31d8ed8d3cc2c6495b524ba740cdaf8ce49c0bdf9a9` |
| `b0_attention_s2_a1/…mask0.00.json` | `7c90eaff64d7dba565a6702f56eb6901486ca3888dfce524f272b3221b87b97c` |
| `…mask0.10.json` | `0d4b1d2d8cf56e4c1ed54a4d5eef07145d27ac4582d46a8ab81b59d504e33571` |
| `…mask0.20.json` | `cf39ee6f36edd1a598267aa52cb3ac09a1c37147962472f6429b2e1bdb5a69b9` |
| `b0_mlp_matched_s0_a1/…mask0.00.json` | `3bfed0f146971edc76305a2ba11b865a44facbee4516adb5be70b8a16c689ca1` |
| `…mask0.10.json` | `28c919cfe62d1ae947da983f0417d9426d04340076bbafd85376340ce00d5aac` |
| `…mask0.20.json` | `d76731650b42d5746a3fca94be0a6feb3aa9b7fce27dd1a00684d66c8906395c` |
| `b0_mlp_matched_s1_a1/…mask0.00.json` | `9d2a56a1d1a0a999f5d3e60c0ce98483ef0f409da4ed0f2daeaf0e394cf18e2c` |
| `…mask0.10.json` | `36c013905108ab06a8fa96f770f6a2fa7b1f4b5908827375793f52891e8adede` |
| `…mask0.20.json` | `a923861af3a90ecb1f17f45613b4cdc3a1ef72ba3e5d08e9901a48a58b1f4b4f` |
| `b0_mlp_matched_s2_a1/…mask0.00.json` | `eeeb390d312079b1f44545fce69b85f9ff8159866010b3c4259bd177ab3044d5` |
| `…mask0.10.json` | `1e9212c86c40d67de496518b8ec1823bca4ed4127be246ac460ce579610cb416` |
| `…mask0.20.json` | `0faaceff6ff0539aa9a90e06d36f4af90c5173680044d458a172e5ddfeaf7e36` |

**Observed noise scale (P4, it 1600, ρ_H).** At f = 0.20: per-seed SD attention 0.1135, mlp_matched 0.0962; SE_pooled of the difference of 3-seed means = 0.0859; **2 · SE = 0.1718**. At f = 0.10: 2 · SE = 0.1579. The scheme's draft margins (0.05 untrained, 0.03 trained) are **below the observed 2-SE seed noise by a factor of 3–6**. Kept as written, they would let a difference of about 0.6 SE count as a gain.

**Frozen thresholds** (same structure as the accepted RV-1 δ: a fixed floor, widened by the noise seen at scoring):

| Threshold | Rule | Frozen floor | Justification |
|---|---|---|---|
| **g_U** (untrained-mask gain margin, f = 0.20) | g_U = max(**0.17**, 2 · SE_U(0.20)) | 0.17 = P4 observed 2 · SE_pooled of Δρ_H(0.20), 0.1718, rounded to 2 decimals | Replaces the draft 0.05. A gain must exceed the seed noise P4 actually showed, and whatever noise P5 shows if larger |
| **g_T** (trained-mask control margin, f = 0.20) | g_T = max(**0.10**, 2 · SE_T(0.20)) | 0.10 = 0.6 × 0.17, keeping the scheme's draft ratio 0.03 / 0.05 | Replaces the draft 0.03. P4 provides no trained-mask data, so the floor scales the U floor by the draft ratio ("the gap is not removed" is meant to be a weaker bar than "there is a gap"). The 2 · SE_T term carries the real T noise (3 seeds per arm, §4.0) |

**Status of these margins.** They are **heuristic decision margins**, not calibrated significance tests. Three seeds per arm give no reliable test level. The SE formula treats the two arms as independent, but the paired mask procedure (§3) makes them correlated, and the formula ignores that covariance. P4's own masks may or may not have been paired (§3), so it is not known whether P4's SDs over- or under-state P5's noise. The floors are frozen so that a lucky low-variance P5 run cannot lower the bar below the noise P4 showed. No outcome label in §7.2 is a significance claim.

### 5.5 Legacy P4 M-10 (mask pairing unverified; reported, never scored)

At it 1600, from the sealed results file (ρ_H = R_H(mask f)/R_H(mask 0) on the P4 files):

| Run | R_H(0) | R_H(0.1) | R_H(0.2) | ρ_H(0.1) | ρ_H(0.2) | ρ_step(0.2) | ρ*_H(0.2) | Surv(0) → Surv(0.2) |
|---|---|---|---|---|---|---|---|---|
| attention s0 | 0.4169 | 0.1975 | 0.1558 | 0.4736 | 0.3736 | 1.0518 | 0.308 | 2638 → 669 |
| attention s1 | 0.2994 | 0.1808 | 0.0516 | 0.6038 | 0.1725 | 0.8514 | 0.047 | 3300 → 336 |
| attention s2 | 0.1563 | 0.0774 | 0.0569 | 0.4954 | 0.3642 | 0.8128 | 0.151 | 771 → 353 |
| mlp_matched s0 | 0.0856 | 0.0721 | 0.0602 | 0.8423 | 0.7032 | 0.9280 | 0.451 | 334 → 254 |
| mlp_matched s1 | 0.0578 | 0.0436 | 0.0411 | 0.7540 | 0.7101 | 1.0325 | 0.095 | 294 → 202 |
| mlp_matched s2 | 0.0894 | 0.0883 | 0.0781 | 0.9869 | 0.8731 | 0.9735 | 0.774 | 356 → 320 |
| **mean attention / mlp** | 0.291 / 0.078 | 0.152 / 0.068 | 0.088 / 0.060 | 0.524 / 0.861 | **0.303 / 0.762** | 0.905 / 0.978 | 0.169 / 0.440 | |

Legacy Δρ_H(0.20) = **−0.459** (2 · SE 0.172). Legacy ΔR_H(0.20) = +0.028 (2 · SE 0.071).

**Disclosure.** These numbers were known when the thresholds were frozen. On these data no g_U ≥ 0 gives a U gain. Attention has the higher absolute return under masks but the lower retained fraction, because masking removes most of its survival advantage while `mlp_matched` was already near the falling floor at mask 0. The thresholds above were derived from the **noise** (the SDs), not from the observed gap, and the same rule applies whatever the paired P5 re-eval shows. P5's U condition is expected to confirm the legacy direction. Its value is that it does so under a verified, paired mask procedure, and that the T control, the ablation and the permutation check are new information.

---

## 6. Permutation architectural check on GPU checkpoints (instruction item 7)

- **Checkpoints:** the 3 staged P4 attention checkpoints (step 3) and every completed `b2mt` attention checkpoint (step 4): **gate PERM**. `b2idx`, P4 `mlp_matched` and `b2mt` `mlp_mind`: reported only (expected to break).
- **Procedure:** load the checkpoint through the frozen upstream load path with the run's sidecar (as `eval_entry` does), take `policy.decoder` in eval mode on CUDA, in fp32 with `torch.backends.cuda.matmul.allow_tf32 = False` and `torch.backends.cudnn.allow_tf32 = False`. **Set `decoder.auto_mask_frac = 0.0` explicitly** before any call: the load path sets it to the sidecar's `train_mask_frac` (0.1 for `b2mt`), and `.eval()` does not disable it. The script asserts it is 0.0 before every primary call. Reproduce the frozen `b2_smoke` permutation test with the checkpoint's own `latent_dim` and `history`: `torch.manual_seed(0)`, n = 32, z = tanh(randn), obs = randn; 8 permutations from `torch.Generator().manual_seed(100 + t)`; permute obs history and morphology, un-permute actions.
- **Metric:** rel err = max_t max |unperm_t − base| / max(mean |base|, 1e-12), exactly the frozen `b2_smoke` `perm_rel_err`. Also reported, never gated: (i) the same with TF32 at its default setting; (ii) a **masked** variant. In (ii) one explicit mask m (n × J, f = 0.2) is drawn once from `torch.Generator().manual_seed(7100)` with the frozen `random_token_mask`. The base call passes `token_mask = m`, and permutation t passes `token_mask = m[:, perm_t]`, with `auto_mask_frac = 0.0` in both.
- **Pass:** rel err < **1e-4** on every PERM-gate checkpoint (TF32-off value). A failure is a bug, not a finding (SCHEME_PLAN §3). Output `meta/perm_<ID>.json`.

---

## 7. Gates and verdict (machine-computed; prose never overrides)

The harness verdict is computed from the deposited bundle by an agent process that is not an adjudicator (OVERLAY-001 rule 6), with the sealed `verdict_b2.py`. Write-up by `claude-sonnet` (SCHEME_PLAN §7). The Orchestrator that wrote this PLAN does not adjudicate it.

### 7.1 Validity checks

| ID | Criterion | Applies to |
|---|---|---|
| **U-ID** | `meta/p4_ckpt_identity.txt` shows all 6 P4 checkpoints at one §2.2 candidate root with the listed sizes and sidecar sha256s, and copy sha256 = source sha256 | U |
| **U-REPRO** | For each of the 6 U checkpoints, the P5 mask-0.00 JSON reproduces the P4 deposit's it-1600 mask-0.00 JSON (sha256 in §5.4): the same 4 clip names; for each clip, identical `steps` and `failed`, and \|Δ norm_return\| ≤ 1e-4 | U |
| **MS** | For every (f, seed): every scored eval execution has its mask-stream files; each call has rows_per_call = 4 and exactly k True per row (k = 3 at 0.10, 6 at 0.20); the recorded `seed` is the condition's seed; for each pair of runs, the streams are byte-identical over their common prefix of calls; the f = 0.10 mask ⊆ the f = 0.20 mask for the same seed and call; `calls` = the benchmark's loop count, i.e. the maximum clip `steps` in that JSON | all scored evals (U, T); `b2idx` reported |
| **B2-V-1** | B0 V-1 applied to each scored new run (completion, no NaN/inf ≤ 1600, one tb file, it-1600 point, timing tags, window coverage). For a **diverged** run (§4.2) only the evidence-integrity part applies (exactly one tb file in `logs/attempts/<AID>/`, train log present, divergence evidence from that tb file or that log). Its endpoint-dependent requirements and the NaN clause are exempt, as for B0 PLAN §6.4 "checkable gate runs" | T; `b2idx` reported |
| **B2-V-2** | Budget parity (RV-8): (a) tb `time/updates` at it 1600 = 624 for every scored new run; (b) `[train_entry] upstream argv` identical to the P4 attention s0 argv except `--run-name` and `--seed`; (c) GPU name in `meta/nvidia-smi.txt` identical to P4's (`NVIDIA GeForce RTX 4090`) | T; `b2idx` reported |
| **B2-V-3** | Seams as B0 V-3; descriptor sha256 in every `b2mt` attention and `b2idx` sidecar equals the P4 attention sidecars' (`3c854f91eb3739e4077dfec354d27a33f7c00cf019eec993a8fb43b66b1e5fe3`); sidecar `train_mask_frac` = 0.1 for `b2mt`, 0.0 for `b2idx`; `attention.id_mode` = `index` for `b2idx`, `morph` otherwise; `mlp_mind` params within ±5% of 464 001 | T; `b2idx` reported |
| **B2-V-4** | B0 V-4 content checks for every expected condition JSON of §4.3 (7 at it 1600; 1 each at 400/800/1200 for new runs), file names as §4.3 | U, T; `b2idx` reported |
| **B2-L-1** | B0 L-1 (C_train rises, first 5 vs last 5 logged points with `time/updates` ≥ 20) on ≥ 2 of 3 scored seeds **in each T arm** | T |
| **B2-L-2** | B0 L-2 (WM loss falls) on every scored T run | T |
| **PERM** | §6 pass on every PERM-gate checkpoint | U attention, T attention |

### 7.2 B2 outcome (machine; f = 0.20 primary)

Computed only when §7.3 reaches row 4.

- **u_gain** = Δρ_U(0.20) ≥ g_U. **u_deficit** = Δρ_U(0.20) ≤ −g_U.
- **t_gap_kept** = t_status is `ok` **and** Δρ_T(0.20) ≥ g_T. **t_deficit** = t_status `ok` and Δρ_T(0.20) ≤ −g_T.
- `t_status` ∈ {`ok`, `diverged`}: `diverged` if any scored T attempt diverged (§4.2).

| `b2_outcome` | Rule | Meaning |
|---|---|---|
| **ROBUSTNESS_GAIN** | u_gain **and** t_gap_kept | "B2 gain" in the SCHEME_PLAN §3 sense |
| **ABSENCE_REPRESENTATION_ONLY** | u_gain **and** t_status `ok` **and not** t_gap_kept | Untrained gap only: "absence-representation advantage, not robustness under equal training" |
| **U_GAIN_T_UNEVALUABLE** | u_gain **and** t_status `diverged` | Untrained gap; the trained control could not be evaluated. Not a B2 gain, and not evidence either way on equal-training robustness |
| **NO_GAIN** | not u_gain | No B2 gain. The `u_deficit` / `t_deficit` flags say whether attention's retention was lower by at least the margin |

- **b2_gain** (input to §8) = (`b2_outcome` = ROBUSTNESS_GAIN).
- **Shadow outcomes (non-binding, reported):** the same table on (i) ρ_step and (ii) ΔR (absolute R_H under mask, with its own 2 · SE margin and the same floors), keyed `shadow_outcome_rstep`, `shadow_outcome_abs`. If either differs from `b2_outcome`, `metric_disagreement = true`.
- f = 0.10 versions of every quantity are reported, with no outcome.

### 7.3 Spike verdict: ordered decision table (first matching row wins)

| # | Condition | `verdict` | `b2_outcome` |
|---|---|---|---|
| 1 | Any of: U-ID false (includes `p4_ckpts_unavailable`); U-REPRO false; MS false on any scored eval; B2-V-1…B2-V-4 false on any scored U or T run; an OOM, SEAM or exhausted INFRA cap in a T cell; the spend cap reached before the required set is complete; a bundle failing the deposit/seal check (§9.2); a non-RTX-4090 GPU or mixed GPU models | **BLOCKED** (`blocked_reason` lists every match) | `null` |
| 2 | PERM false, with no row-1 condition | **FAIL** (`failing_ids` ∋ PERM; a bug, not a finding) | `null` |
| 3 | `t_status` = `ok`, **and** B2-L-1 or B2-L-2 false, with no row-1/2 condition | **FAIL** (`failing_ids` ⊆ {B2-L-1, B2-L-2}) | `null` |
| 4 | All other cases | **PASS** | per §7.2 |

- **Required set** = the 6 U evals, PERM on the 3 P4 attention checkpoints and on every non-diverged scored `b2mt` attention checkpoint, and the 6 T cells. Each T cell needs a scored attempt that is either non-diverged with its scored evals, or diverged (§4.2; a diverged attempt needs no evals). The set is complete when all of these exist. `b2idx` is not in the required set.
- **Divergence precedence.** Any number of diverged T attempts (one or several, in either arm) does **not** by itself make the verdict FAIL or BLOCKED. It sets `t_status = diverged`. Then B2-L-1 and B2-L-2 are **not evaluated** (their values are still reported for the non-diverged T runs), and §7.2 cannot return ROBUSTNESS_GAIN or ABSENCE_REPRESENTATION_ONLY. Row 1 still applies if a diverged run fails its evidence-integrity checks (B2-V-1).
- **Undefined retention.** If R_H(mask 0.00) = 0 for any scored U run, or any non-diverged scored T run, ρ_H is undefined for it. Row 1 then applies (`blocked_reason` ∋ `rho_undefined:<ID>`). A seed is never dropped from a mean, and never imputed. The same applies to the shadow ρ_step (R_step(0) = 0), but only for the shadow outcome: that shadow is then `null`, and the verdict is unaffected. ρ*_H is `null` per §5.3, and a null ρ*_H makes the reported arm mean `null`. Arm means and SEs are computed over exactly the scored seeds listed in `scored_set`. With fewer than 2 values, the SE is `null`.
- **T statistics when `t_status = diverged`.** The T aggregates that enter §7.2 (`t.f*.rho_bar_h_*`, `delta_rho`, `se`, `g_t`, `delta_abs`, `se_abs` and the shadow T values) are `null`. The harness line prints `drho_t=null g_t=null`. Per-run values are kept in `runs.<AID>` for every non-diverged T run, and also for a diverged run where its evals exist. A separate report-only block `t_partial` gives the same aggregates over the non-diverged T runs, with n per arm stated (n ≥ 2 per arm, otherwise null). It never enters §7.2.
- **PASS means B2 was validly executed. It is not a claim that attention is more robust.** NO_GAIN and u_deficit are PASS-verdict outcomes.
- A BLOCKED verdict goes to the human lead with `BLOCKED.md`. For `p4_ckpts_unavailable`, the options the human lead may choose between (each a Class-2 amendment, signed before any further spend): (i) score U from the legacy P4 files with `mask_pairing = unverified_global_rng` and the U result labelled fairness-confounded; (ii) re-train the 6 B0 gate cells under the B0 configs in P5 to regenerate U checkpoints (≈ 1.8 GPU-h); (iii) drop the U condition. For a U-REPRO failure with U-ID true (the checkpoints are the right files but eval does not reproduce), the options are: (iv) accept it with the per-clip differences disclosed and score U from the P5 evals, or (v) treat it as an eval-path defect and file a change request.

### 7.4 Ablation report (attention_idx; never moves the verdict)

- `keying_mask0`: R̄_H(P4 attention, 0) − R̄_H(b2idx, 0), with SE (3 + 3 seeds) and a label: `keying_helps` if ≥ max(0.05, 2 · SE), `keying_hurts` if ≤ −max(0.05, 2 · SE), else `no_detectable_difference`.
- `keying_rho`: ρ̄_H(P4 attention, 0.20) − ρ̄_H(b2idx, 0.20), same labels with max(0.17, 2 · SE).
- PERM on `b2idx` is reported (expected to break; a value < 1e-4 there would itself be a bug report).
- **Completeness.** `ablation_status` = `complete` when all 3 `b2idx` cells have a scored, non-diverged attempt with scored evals. Otherwise it is `incomplete` (spend cap, INFRA, OOM, SEAM or divergence; the reason is listed per cell). Per-run values are always reported for whatever exists. Aggregates and SEs are computed over the existing non-diverged scored runs, with n stated, when n ≥ 2. With n < 2 the aggregates are `null`. Labels are emitted only when `ablation_status = complete`, and are `null` otherwise.
- **Zero unmasked return in the ablation.** If a `b2idx` run has R_H(0.00) = 0, its ρ_H is `null` with reason `rho_undefined`. The `keying_rho` aggregate, its SE and its label are then `null`. `keying_mask0` is still computed, because R_H(0) itself is defined. The spike verdict is unaffected.
- **Confound:** P4 attention was trained in the P4 job and `b2idx` in the P5 job (same tarball code for these paths, same GPU model, `env_drift` reported). This is a cross-packet comparison.

---

## 8. Combined B0 + B2 gate to B1 (SCHEME_PLAN §3, RV-1)

**Inputs:** `b0_outcome` read from the sealed P4 results file (`76507d8a…`): **NONINFERIOR** (superior flag true). `b2_gain` from §7.2.

| Rule (SCHEME_PLAN §3, literal) | Evaluated here |
|---|---|
| **Go** if B0 is non-inferior (or superior) | **Applies.** `gate_b1 = Go` |
| Go-with-caveat if B0 inconclusive and there is a B2 gain | Not applicable (B0 is not inconclusive; the B0 PLAN has no INCONCLUSIVE band) |
| Kill if B0 inferior and no B2 gain | Not applicable |
| Otherwise human lead | Not applicable |

- Because B0 is NONINFERIOR, **the gate value is Go whatever the B2 outcome or verdict.** The harness still emits `gate_b1` from the rule (not from prose). It emits `Go` together with `b2_verdict` and `b2_outcome`, so the reader sees the B2 state.
- **Mandatory caveat carry-over.** If `b2_outcome` ≠ ROBUSTNESS_GAIN, or `u_deficit` is true, or the B2 verdict is not PASS, then every later write-up that cites the B0 + B2 gate (including the B1 brief) states the B2 result in one sentence with its numbers (for example: "under untrained token masking the attention decoder retained a smaller fraction of its unmasked return than mlp_matched, Δρ_H(0.2) = …"). This is a disclosure, not a gate change.
- `gate_b1 = Go` opens P6 for planning only. P6 spend still needs its own sealed PLAN and Manager START (BLK-12).

---

## 9. Must capture, bundle, deposit, harness keys

### 9.1 Bundle

One archive per job, returned unmodified, named `b2-<YYYYMMDD>-<HHMM>[-partN].tgz`. Contents:
- `meta/nvidia-smi.txt`, `meta/pip-freeze.txt`, `meta/cpu_test_smoke.log`, `meta/tarball_sha256.txt`, `meta/p4_ckpt_identity.txt`, `meta/ckpt_dirs_ls.txt` (new runs and staged U checkpoints), `meta/gpumem_<AID>.csv`, `meta/harness_stop_<AID>.txt`, `meta/perm_<ID>.json`, `meta/env_drift.txt` (diff against the P4 pip freeze, may be empty)
- `logs/train_<AID>.log` and `logs/attempts/<AID>/` (sidecar, tb, no `*.pt`) for **every** new attempt, scored or not, plus any `.live` directories without `*.pt`
- `logs/eval/<ID>/it<IT>/exec<K>/` for every eval execution: `eval.log`, condition JSONs, mask-stream files
- `deviations.md` (may be empty), `BLOCKED.md` if applicable, job JSON and remote runner stdout
- **No motion data and no `*.pt` files leave the venue.** The staged copies under `/content/p5_p4ckpts/` and the new checkpoints stay on the venue.

### 9.2 Deposit and seal-before-open

- **Deposit path:** `logs/xn4090/<YYYY-MM-DD>/`, seal event `DEPOSIT xn4090` (or `logs/colab/<YYYY-MM-DD>/`, `DEPOSIT colab`, only after a venue amendment, §9.3).
- The archive is kept byte-identical (mode 0444). Its sha256 goes into `logs/seal.log` **before** any agent opens it (OVERLAY-001 rule 3; venue contract). Every archive is deposited, including failed or aborted ones.
- The verdict process extracts read-only, checks member paths (no absolute paths, no `../`), and writes `spikes/B2/runs.log` (append-only) and `spikes/B2/results.json`.

### 9.3 Venue

- **XN-4090-GPU2** (job contract `/srv/claude/research/METHOD/venues/xn-4090-gpu2.md`), job `p5-b2-attempt1`, mutex `gpu0`, `deposit.remote_glob /content/b2-*.tgz`, `deposit.local_dir logs/xn4090/<date>`. The job JSON goes to `READY` only after upload bytes and JSON are sealed (BLK-12 preference).
- **Why only XN-4090.** The U checkpoints exist only on that host, and B2-V-2(c) needs the P4 GPU model for the trained arms' parity with P4. Colab L4 is **not** a pre-registered alternate for P5. If XN-4090 is unavailable, the run is BLOCKED and a venue change needs a sealed amendment.
- **HF mirror.** `huggingface.co` is unreachable from xn-4090 (DIAG `b818a714…`). `run.sh` and the job env set `HF_ENDPOINT=https://hf-mirror.com` and `HF_HUB_ENABLE_HF_TRANSFER=0`, as in P4 relaunch 3. A motion download failure is INFRA at setup (no attempt consumed), deposited.
- **Paths.** As B0 PLAN §2.3: `/content/junior` = unpacked CR-B2-1 tarball, `/content/SuperMimic-Reproduced` = upstream at the pin. The P5 driver must not delete, re-clone over, or write into the P4 upstream tree's `logs/b0_*` directories. If `/content/SuperMimic-Reproduced` exists with those directories, the driver reuses the clone after `git rev-parse HEAD` = the pin, and writes only `logs/b2*`, `logs/eval/b2*`, `logs/attempts/b2*` and `/content/p5_p4ckpts/`.
- **Allowed without amendment** (record in `deviations.md`): the R1 wheel substitution, the harness stop, reuse of the existing upstream clone at the pin, `HF_ENDPOINT`. Anything else is a plan gap: stop and write `BLOCKED.md` (method §12.2).

### 9.4 `results.json` keys (machine-checkable)

**Top level:**
- **Provenance:** `plan_sha256`, `method_sha256`, `tarball_sha256` (CR-B2-1), `base_tarball_sha256` (CR-B0-1 `763867682e3c…3bff`), `p4_results_sha256` (`76507d8a…`), `p4_deposit_sha256` (`1f491182…`), `venue`, `gpu_name`, `deposits[]`, `env_drift` (bool + diff path).
- **Verdict:** `verdict` ∈ {PASS, FAIL, BLOCKED}, `decision_row` (1–4), `failing_ids[]`, `blocked_reason[]`.
- **Outcome:** `b2_outcome` ∈ {ROBUSTNESS_GAIN, ABSENCE_REPRESENTATION_ONLY, U_GAIN_T_UNEVALUABLE, NO_GAIN, null}, `b2_gain`, `u_gain`, `u_deficit`, `t_gap_kept`, `t_deficit`, `t_status`.
- **U statistics** (keyed `u.f0.20` and `u.f0.10`): `rho_bar_h_attention`, `rho_bar_h_mlp_matched`, `delta_rho`, `se`, `g_u` (f = 0.20 only), plus `delta_abs`, `se_abs`, `rho_step_bar_*`, `rho_star_bar_*`.
- **T statistics** (keyed `t.f0.20`, `t.f0.10`): the same with `attention_mtrain` / `mlp_mind_mtrain` and `g_t`.
- **Frozen constants echoed:** `T` (500), `g_u_floor` (0.17), `g_t_floor` (0.10), `r_floor` (0.0393), `mask_seeds` ([7100, 7101, 7102]), `primary_f` (0.20).
- **Shadow:** `shadow_outcome_rstep`, `shadow_outcome_abs`, `metric_disagreement`.
- **Undefined values:** `rho_undefined[]` (IDs).
- **Gate:** `b0_outcome_input` ("NONINFERIOR", with source sha), `gate_b1` ∈ {Go, Go-with-caveat, Kill, HumanLead}, `caveat_required` (bool, §8).
- **Ablation:** `ablation_idx` = `{ablation_status, n_runs, cell_status{AID: reason}, keying_mask0, keying_mask0_se, keying_mask0_label, keying_rho, keying_rho_se, keying_rho_label, perm_rel_err[]}`.
- **Legacy:** `legacy_p4_m10` (the §5.5 table values, recomputed from the P4 files, labelled `mask_pairing = unverified_global_rng`).
- **Gates:** one key per ID (`U-ID`, `U-REPRO`, `MS`, `B2-V-1`, `B2-V-2`, `B2-V-3`, `B2-V-4`, `B2-L-1`, `B2-L-2`, `PERM`), each with `pass` and per-run evidence.
- **Per run** `runs.<ID>` (U IDs `b2u_<P4 AID>` and every new AID, used or not): `tag`, `arm`, `seed`, `attempt`, `class`, `scored`, `condition` (U/T/ablation), `ckpt_identity` (U), `repro` (U: per-clip steps/failed/Δnorm_return), training checks and windows as B0 `attempts.<AID>` (new runs), `perm` (`rel_err_tf32off`, `rel_err_default`, `rel_err_masked`), and `eval.it<IT>` = `{scored_exec, mask0.00: {r_h, r_step, cum, surv_steps, fail_count, clips[…], terms{…}}, mask<f>: {per_seed: {<seed>: {r_h, r_step, cum, surv_steps, fail_count, clips[…], maskstream_sha256, calls}}, r_h, r_step, rho_h, rho_step, rho_star_h}}`.

**Harness output line** (exactly one):

`B2_VERDICT verdict=<…> outcome=<…> drho_u=<…> g_u=<…> drho_t=<…> g_t=<…> t_status=<…> gate_b1=<…> failing_ids=[…] blocked=[…]`

### 9.5 Also captured (reported, no threshold)

The `params:` line per attempt, compile setting, `nvidia-smi` header, every deviation, the P4-vs-P5 pip freeze diff, eval wall time per condition. Relay notes stay outside the archive.

---

## 10. Cost, budget, spend gate

From P4 on XN-4090-GPU2 (RTX 4090): ≈ 0.28–0.30 h per training run to it 1600 (tb `time/hours`); the whole P4 job (setup, 7 trainings, 84 eval conditions) took 2.44 h wall (06:52:53Z → 09:19:29Z), so ≈ 10–15 s of GPU per eval condition.

| Item | Estimate (RTX 4090) |
|---|---|
| Setup + checkpoint staging | ≈ 0.2 h |
| U evals: 6 checkpoints × 7 conditions | ≈ 0.2 h |
| 6 T trainings + 3 `b2idx` trainings | 9 × ≈ 0.30 h = ≈ 2.7 h |
| Evals of new runs: 9 × (7 + 3) conditions | ≈ 0.4 h |
| PERM checks | < 0.1 h |
| **Total** | **≈ 3.5–4 GPU wall-h** (SCHEME_PLAN §8 draft for P5: 2–2.5 L4-h; the overrun comes from 3 seeds per new arm, §4.0) |

- Inside the BLK-12 envelope (≈ 17–20 L4-h for P4/P5/P6d; P4 used 2.44 h on the 4090).
- **Spend cap for P5: 6 GPU wall-hours** on XN-4090-GPU2, retries included. On reaching it the runner stops after the current cell and deposits. If the required set (§7.3) is incomplete, the verdict is BLOCKED (budget). If it is complete, only `b2idx` work stops and the ablation reports `incomplete`.
- **Spend gate:** no P5 GPU time until (1) this PLAN is sealed, (2) PS-B2-1…PS-B2-3 hold in sealed P5-prep files, and (3) the Manager issues START (PS-B2-4). This PLAN alone authorizes no spend.

---

## 11. Red-team and roster

- P5 PLAN is a single-Orchestrator PLAN packet, not a contest. A.7 contest allocation does not apply, and no new program-root `roster.md` is written; the P1 roster (`5be8a85d…`) is not edited.
- SCHEME_PLAN §7 assigns `codex-astra` high as the red team on each PLAN (catalog A.6 secondary family; A.7 step 3 "remaining slots by documented strengths"). The red-team record for this PLAN is under `spikes/B2/redteam/` (binding, prompt hash, raw output, dispositions), and its outcome is summarised in §12 item 9.
- **Runner slot:** `xn-4090-gpu2 job runner` (remote, via the owner's jump host), recorded in the P5 job JSON. **Verdict process:** a non-adjudicator agent runs the sealed `verdict_b2.py`. **Write-up:** `claude-sonnet`.

---

## 12. Confounds and disclosures (carried into any B2 write-up)

1. **Thresholds frozen after seeing P4 M-10.** The floors (0.17, 0.10) come from P4 seed noise. The legacy U gap (−0.459) was visible when they were set. §5.5 states what that means.
2. **Ratio metric.** ρ_H divides by mask-0 return. Attention's mask-0 R_H is ≈ 3.7× `mlp_matched`'s. Masking removes most of attention's survival advantage, so attention can keep more absolute return and still retain a smaller fraction.
3. **Floor effect.** `mlp_matched` at mask 0 is close to the near-immediate-fall level (R_H ≈ 0.078 vs floor 0.039). A policy near the floor retains a high fraction trivially. ρ*_H and ΔR are reported for this reason. They are not the primary metric, because the scheme's primary is ρ and swapping it after seeing the data would be worse.
4. **Mask model.** Masks are re-drawn at every decoder call (flicker), not held for an episode. Only the decoder's observation input is masked. The motion encoder's goal input is never masked. In masked training (`b2mt`) the WM and critic see unmasked observations. Eval runs only the policy. A persistent-loss model might rank the arms differently. Not tested here.
5. **Paired masks, exact on the common prefix.** Once one arm's clip terminates, later masks have no counterpart. That is inherent to whole-clip eval.
6. **U checkpoint identity** rests on byte size, sidecar sha256 and U-REPRO, because P4 did not hash the `*.pt` files.
7. **Cross-packet comparisons** (`b2idx` vs P4 attention; `*_mtrain` vs P4 arms) mix two jobs. Same GPU model and code paths, `env_drift` reported. The scored T comparison is entirely within P5.
8. **Stability evidence.** As in P4 Amendment v1, the grad-clip clause of the divergence rule is not evaluable; only NaN/inf counts.
9. **Planning and review.** Written by a Claude-family Orchestrator. A cross-family red team (`codex-astra` high, read-only, objections only) reviewed **draft 1** (`65cae1df4ac4eab9da4f1cd9c504b2625b46f79a612092e68c999ca56ded0f6c`) and returned REVISE, with 2 BLOCKER, 5 MAJOR and 1 MINOR objections. Among them: draft 1's §3 claim that the P4 mask streams were unpaired was not established by the evidence and is corrected here to "unverified". The Orchestrator applied all 8 (`spikes/B2/redteam/REDTEAM-DISPOSITION.md`). Round 2 reviewed draft 2 (`f11633a24d56b8963269303e15e0dce009efd5fcb3db2ca7dc9a1937a2a52d10`): 7 of 8 resolved, R1-2 not resolved, plus 2 new (1 MAJOR, 1 MINOR); REVISE. All three were applied in draft 3. Round 3 reviewed draft 3 (`3d1b9b57c36e0ee7b2ae4324bd2d17b79d3116057d1c5367a2522599ab658c46`): R1-2, #9 and #10 RESOLVED, no new BLOCKER or MAJOR, **REDTEAM-RESULT: SEAL-OK**. The sealed text differs from draft 3 only in this item-9 record. Outputs: `spikes/B2/redteam/redteam-r{1,2,3}-last-message.txt`.
10. **Reduced scale** (512 envs, H = 16) and compute parity ≠ param parity (attention FLOPs ≈ 27× mlp_matched), as in B0 PLAN §10.
11. **`mlp_mind` design** (indicator concatenated once, not per history frame) is this PLAN's choice for "MLP with a per-joint mask-indicator input". A per-frame indicator would add 290 inputs instead of 29. The choice was made before any `mlp_mind` data existed.

---

## 13. Method fit (boot step 4)

- No program special beyond the existing overlays is needed. OVERLAY-001 covers human runners. The XN-4090 job runner is covered by the global venue contract and §9.3 (same deposit-before-open and non-adjudicator-verdict rules), as in P4.
- Method pin v1.1 `9bdc872e…590afc0` is unchanged since P4. P5 runs under it.

## 14. Explicitly not done in this packet

- No change to `spikes/B0/PLAN.md`, the P4 deposit, the P4 results or the P4 verdict. P4 stays PASS / NONINFERIOR, historical.
- No change to any D-004 or CR-B0-1 file. CR-B2-1 is specified here and executed in P5-prep.
- No Colab run, no XN-4090 job, no training, no eval, no spend. No P6 start.
