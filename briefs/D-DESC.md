# Brief D-DESC: morphology descriptor v2 and action-scale handling for the shared attention decoder

**Packet:** P1 / D-DESC (two-author design contest, method §4 Steps 1–5). **Stakes:** high (it decides whether the B0 attention checkpoints can serve as the B1 transfer source; SCHEME_PLAN §1 P1).
**Written:** 2026-10-25 EDT (America/Toronto) by the Orchestrator (Claude Code, `claude-opus`, P1 wake). The Orchestrator does **not** author on this packet.
**Method:** v1.1, sha256 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0`. Overlays: `method/local/README.md`, `method/local/OVERLAY-001-owner-colab-runner.md` (not used here; the D-DESC spike is CPU, agent-run).
**Decision cap:** Provisional. **Roster:** `roster.md` (program root), frozen with this brief before Step 2.
**Freeze:** this file is frozen when its sha256 is appended to `logs/seal.log` (event `FREEZE brief D-DESC`). Afterwards only appended `Amendment vN.M` blocks are allowed (method §10.4).

## 1. Inherited items (by ledger ID; method §13.3)

Ledger snapshot: `program-ledger.md` up to and including **P-B1**.

| ID | Binds as |
|---|---|
| X-001 (upstream reproduction pin) | Context. The pinned action/actuator code excerpts are in `packets/P1/ddesc/context/upstream-d9be385/` (identifiers mechanically redacted; see its README) |
| X-003 (owner home-humanoid asset, `assets/home_humanoid_mjcf/`) | Context. Read-only |
| D-001 (Junior-(B) decoder on unchanged WM loop) | **Explicit assumption** (Provisional, depth 1) |
| D-002 (eval + scheme: RV-4, RV-5, GAP-1..GAP-7) | **Explicit assumption** (Provisional, depth 1). This packet depends on D-001 and D-002 directly, not on a chain, so the depth-1 cap holds |

## 2. Problem statement

The attention decoder (`code/attention_policy.py`) keys each joint token by a 12-d morphology descriptor (v1: root-frame anchor xyz, axis xyz, default angle from `qpos0`, depth normalised by per-body max depth, side sign, limb one-hot). The same decoder weights are meant to drive the 29-DoF reference humanoid (B0) and later the **home humanoid** (22 hinges, ≈ half scale, no actuators in the MJCF; B1). v1 has four defects for that purpose (EVAL_REVIEW §6.3): GAP-1 default angle from `qpos0`, GAP-2 per-body depth normalisation, GAP-3 absolute metric anchors (≈ 2× scale shift), GAP-4 no actuator/limit/action-scale features. Separately, the meaning of one action unit differs per body (GAP-5).

**Decide, before B0:**
1. **Descriptor v2:** the exact feature list, each feature's computation from (compiled model, env default pose, per-joint actuator parameters), normalisation constants, and `morph_dim`.
2. **Action-scale handling (RV-5):** how one decoder output unit maps to a joint set-point on each body, and whether/how the scale enters the descriptor.

The pinned upstream code shows the env already applies a per-joint action scale `0.25 · effort_limit / stiffness` plus the default-pose offset (`context/upstream-d9be385/mjlab_ref29_constants.py`, `REF29_ACTION_SCALE`; `src_supermimic_envs_actions.py`). Per SCHEME_PLAN P1 note, a candidate that adds a **second** scaling layer must justify it against that fact; the default expectation is "verify the env scale, carry it in the descriptor".

## 3. Constraints and non-goals

**Hard constraints (violation ⇒ Reject at the eligibility gate):**
- H1. Decoder call signature unchanged: `forward(z, obs_hist, token_mask=None, morphology=None) -> (N, J)`; obs layout unchanged (term-major, H=10). No change to motion encoder, WM, critic or training loop.
- H2. `id_mode=morph` stays exactly permutation-equivariant: permuting joints (obs slices + descriptor rows) permutes actions. No feature may depend on array index.
- H3. Trainable-parameter change of the attention decoder ≤ 5% versus v1 (463 489 at J=29 defaults), and `mlp_matched` re-matches to ±5% by the existing solver.
- H4. Every descriptor feature must be computable **without motion data and without GPU** from: the compiled MuJoCo model, an env default pose vector, and per-joint actuator parameters (effort limit, stiffness/kp, damping/kd, action scale). For the home humanoid these inputs come from load-time assumptions (AS-1 gains, AS-2 default pose; SCHEME_PLAN §5); the descriptor function must take them as **arguments**, never read them from the owner XML (which has `nu=0`, no keyframe). A name-only synthetic fallback must still exist for CPU smoke.
- H5. Owner asset read-only. Plant-class naming only in prose and identifiers; reference the asset by directory and glob, not basename.
- H6. Integrates with the frozen seam: checkpoint `policy` state_dict layout preserved; the descriptor config is recorded in the sidecar JSON so eval rebuilds the same decoder.

**Non-goals:** tokenised per-joint goal encoders; shared multi-body WM/critic; retargeting; home-humanoid actuator gain selection itself (only the interface that receives it); any GPU run; any B0/B1 arm.

## 4. What each candidate delivers (Step 2)

One markdown file, `proposal.md`, in the author's own draft directory, containing in order:
1. **Feature table** for descriptor v2: name, dims, formula, inputs used, normalisation, which GAP it addresses.
2. **Action contract:** decoder output semantics; where scaling happens; what the descriptor carries; how this behaves on both bodies (give the expected per-joint scale ranges on the 29-DoF body from the pinned code, and the formula for the home humanoid given AS-1 gains).
3. **Function signature(s)** and pseudocode precise enough for a runner to implement on CPU in < 150 lines, including the synthetic fallback.
4. **Parameter-count impact** (estimate) and `morph_dim`.
5. **Transfer-readiness argument:** what a descriptor row for "the same functional joint" (e.g. left knee) looks like on both bodies, and which features are scale-free.
6. **Falsifiers:** at least two CPU-checkable observations that would show the design is wrong (these may be added to the spike PLAN by the Orchestrator, identically for the recommended candidate only).
7. **At least one serious rejected alternative**, with reason (method §11.5).
8. **Failure modes** (at least R7, R8 and a B0-fairness risk), each with a detectable signature.

Drafts must **not** state the author's model, vendor or tool identity (neutral-label adjudication, §4 Step 4). Length ≤ 1 800 words.

## 5. Interfaces / contracts

| Interface | Contract |
|---|---|
| Descriptor builder | `morphology_v2(model, joint_names, default_qpos, actuator_params) -> Tensor (J, morph_dim)`; row order == actuator order == obs joint order (S1). Exact argument names may differ but inputs may not exceed H4 |
| Synthetic fallback | name-only builder returning distinct rows of the same `morph_dim` |
| Decoder | `AttentionDecoderCfg.morph_dim` set from v2; nothing else in the decoder changes unless justified under "Complexity cost" |
| Action | Decoder emits a per-joint normalised offset; the per-body env maps it to a set-point (upstream: `raw · scale + default_offset`) |
| Sidecar | records descriptor version, normalisation constants and per-joint inputs |

## 6. Rubric (fixed before drafts; method §5 rows plus one packet row)

Each row 1–5; every score ≤ 2 needs a concrete objection. **Aggregation:** unweighted sum, max 45. **Tie margin:** 4.5 points (10% of max), plus the order-reversal rule (§4 Step 4 (b)). One adjudicator (third family), two passes with presentation order reversed.

| Row | Question for this packet |
|---|---|
| Constraint fit | Obeys H1–H6 and the non-goals? |
| Falsifiability | Do its falsifiers and the spike criteria (§7) fail clearly on CPU? |
| Evidence demand | Validatable on CPU now, without new GPU runs or owner data beyond AS-1/AS-2 inputs? |
| Failure modes | R7 (scale shift), R8 (action semantics), B0 fairness and BPTT-stability (R13) risks named with signatures? |
| Integrability | Fits the existing seam, sidecar, `mlp_matched` re-matching, upstream action pipeline without a second scale layer (or justifies one)? |
| Latency / criticality class | Descriptor is computed once per body (offline tier); no per-step cost increase beyond the morph MLP input width? |
| Complexity cost | Every added feature tied to a named GAP/RV; nothing decorative? |
| Reversibility | Can it be dropped back to v1 (or a feature ablated) without touching B0/B2 artifacts or the owner asset? |
| **Transfer-readiness across a ≈2× scale gap** | Do corresponding joints on the two bodies get comparable descriptors, with scale-dependent quantities normalised by a stated body length? |

**Eligibility gates (before ranking):** any H1–H6 violation ⇒ Reject. There are no Locked claims in the ledger, so no Grade-1/Grade-2 gate applies.

## 7. Spike criteria (recommended candidate only; CPU; method §4 Step 5)

Binding (from SCHEME_PLAN P1); the PLAN may add the recommended candidate's own CPU falsifiers (§4 item 6) but may not relax these:
- **S-1** v2 descriptor finite and with J distinct rows on both bodies: the 29-DoF reference (synthetic-name fallback on the box, because the upstream model is not on the box) **and** the home humanoid (from `assets/home_humanoid_mjcf/` via glob, with documented placeholder AS-1/AS-2 inputs).
- **S-2** Permutation-equivariance relative error < 1e-4 on both bodies.
- **S-3** Attention decoder parameter-count change ≤ 5% vs v1; `mlp_matched` within ±5% of the new attention count.
- **S-4** Owner asset sha256 (XML + 27 meshes per `mesh_manifest.json`) unchanged after the run.

The runner is `claude-sonnet` (roster), working only under `spikes/D-DESC/`, under a hashed `spikes/D-DESC/PLAN.md` (method §12.2).

## 8. Isolation, timing, degraded outcomes

- Isolation and publication: `roster.md` §Isolation (sequential drafting; sibling draft directory mode 000 and sibling transcript mode 000 while the other author drafts; tool-call logs audited for sibling paths; seal then publish-after-all under neutral labels).
- Budgets (wall clock, each): Author draft 30 min; each review 20 min; each adjudication pass 20 min; spike 30 min.
- **If D-DESC cannot run** (an author family unavailable): freeze descriptor v1 + FX-1..FX-4; record that B1 transfer arms need a retrained 29-DoF source (SCHEME_PLAN P1 degraded outcome).
- **If the adjudication is a tie:** P1 freezes with descriptor v1 + FX-1..FX-4; the tie goes to the Human lead; v2 then enters by change request **before P2**, so B0 never runs on an undecided descriptor.
- **If the spike fails:** the Alternate (if any) is spiked once; otherwise the degraded freeze above applies and the decision is recorded as spike-failed.

## 9. Readable context for authors (identical set for both)

`briefs/D-DESC.md`; `docs/EVAL_REVIEW.md`; `docs/SCHEME_PLAN.md`; `code/attention_policy.py`; `code/mlp_baseline.py`; `code/train_entry.py`; `code/tests/test_smoke.py`; `configs/colab_smoke.yaml`; `code/vendor/NOTES.md`; `packets/P1/ddesc/context/upstream-d9be385/*`; `assets/home_humanoid_mjcf/` (read-only; loadable with `.venv/bin/python` + mujoco 3.17). Authors may run CPU Python from `.venv` and write only inside their own draft directory. No network.
