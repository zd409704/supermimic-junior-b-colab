# Brief B1: home-humanoid cross-embodiment of the Junior-(B) shared attention decoder

**Status:** DRAFT brief, **Provisional**. Not frozen. Step 2 (drafting) must not start until the preconditions in §9 hold and the Orchestrator of the later wake freezes this file (method §10.3).
**Written:** 2026-10-25 EDT (America/Toronto), run-002-eval-scheme, by Claude Code (Orchestrator role, writing the brief only).
**Method:** v1.1, sha256 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0`. Overlays: `method/local/README.md`, `method/local/OVERLAY-001-owner-colab-runner.md`.
**Human lead:** per `README.md`. **Track scope:** cross-embodiment only. B0/B2 are separate packets.

## 1. Inherited items (by ledger ID; method §13.3)

Ledger snapshot: `program-ledger.md` up to and including **D-002**.

| ID | Binds as |
|---|---|
| X-001 (mjlab reproduction pin) | Context. Return claims are not evidence |
| X-002 (motion licensing) | Constraint (runtime-only, never committed) |
| X-003 (owner home-humanoid asset) | Context. Asset is read-only |
| D-001 (Junior-(B) decoder on unchanged WM loop) | **Explicit assumption** (Provisional) |
| D-002 (eval + scheme packet) | **Explicit assumption** (Provisional) |
| B0/B2 decision (to be created in P4/P5) | **Explicit assumption** (Provisional). It makes this packet depth 2. See §9, P-3 |

## 2. Problem statement

Can the weights of a shared per-actuator attention decoder, trained on the upstream 29-DoF reference humanoid inside the SuperMimic-style WM/BPTT loop, be reused on a structurally different **home humanoid** and learn its tracking task faster or better than (a) the same architecture from scratch and (b) a param-matched MLP decoder transferred by joint-semantic row mapping?

The second body is the owner-provided **home humanoid**: 22 hinges (no waist, no wrists, a 2-DoF head), about 15.9 kg, roughly half the scale of the reference body. Asset directory: **`assets/home_humanoid_mjcf/`**. The primary MJCF is the single `*.xml` there, and meshes are in `meshes/` alongside it. Inventory: `docs/EVAL_REVIEW.md` §4.1.

## 3. Constraints and non-goals

**Hard constraints**
1. The world model is not replaced by any analytic/energy-based soft-body plant (D-001, EVAL_REVIEW V1).
2. Only the decoder is shared across bodies. Motion encoder, WM, critic, env config and reference motion are per body (RV-3). No candidate may claim zero-shot whole-policy transfer.
3. Owner asset files are read-only. Every modification is made at load time (EVAL_REVIEW §4.1, SCHEME_PLAN §5). No re-copying or re-exporting of meshes.
4. Motion data and its adaptations exist only on the Colab runtime. They are never committed or shared (X-002).
5. Plant-class naming only ("home humanoid", "29-DoF reference humanoid"). No commercial product or company names in prose, identifiers, configs or prompts. Exported filenames are referenced by directory and glob.
6. Paid compute needs a Human lead gate. GPU work runs on Colab, run by the owner (OVERLAY-001).
7. Equal env-step budgets across arms. Every arm reports wall-clock cost.

**Non-goals**
- A shared multi-body WM or critic.
- Tokenised per-joint goal encoders. These are a possible later packet, and candidates may propose them only as a rejected or deferred alternative.
- Learned dense-correspondence retargeting that needs external body models.
- Real-robot deployment. Locomotion beyond the LAFAN1-style smoke subset.

## 4. What candidates must specify (Step 2 deliverable)

Each Author delivers `proposals/<label>.md` with:
1. **Descriptor/action contract** for both bodies. Use the P1 D-DESC decision if it is Locked or Provisional-adopted. Otherwise propose one, covering scale normalisation, depth normalisation, actuator/limit features and action-scale handling.
2. **Home-humanoid plant overlay.** Actuator model and gains (AS-1, with an explicit assumption if armature stays 0), default pose (AS-2), tracked/termination bodies (AS-3), how the floors are removed and contacts excluded.
3. **Retarget route** (AS-4): the joint correspondence table, axis-sign checks, the scale rule for the root, and the RT-b fallback trigger.
4. **Transfer procedure** for H-A-xfer and the row-mapping rule for H-M-xfer, including what happens to unmapped joints (head) and to body-specific input rows.
5. **Arms, budget and seeds**, following SCHEME_PLAN §4 or with a justified deviation.
6. The **runnable test** following SCHEME_PLAN §5 (B1-RT), with any tightening of its thresholds.
7. **At least one serious rejected alternative**, with the reason (method §11.5).
8. **Failure modes**, and the observation that would show each one occurred.

## 5. Interfaces / contracts

| Interface | Contract |
|---|---|
| Decoder | `forward(z, obs_hist, token_mask=None, morphology=None) -> (N, J)`. Same weights for J=29 and J=22 |
| obs_hist | Term-major `[qpos H·J | qvel H·J | ang_vel H·3 | gravity H·3 | prev_action H·J]`, H=10 |
| Morphology rows | Order == actuator order == obs joint order. Asserted on each body (S1) |
| Action | Per-joint normalised position-target offset. The per-body env applies its scale and default pose |
| Encoder / WM / critic | Per body. Goal and state dims follow from that body's env config. State 57 for the home humanoid is expected and must be verified |
| Outputs | `spikes/B1-RT/`, `spikes/B1/` (`runs.log`, `results.json`, `deviations.md`, `BLOCKED.md` if needed). Raw Colab bundles in `logs/colab/<date>/`, sealed before analysis |

## 6. Rubric (fixed before drafts; method §5)

Each row is scored 1–5, with a concrete objection for every score ≤ 2. Aggregation: unweighted sum (max 40). **Tie margin: 4 points** (10% of max), plus the §4 Step 4 order-reversal and adjudicator-disagreement rules.

| Row | Question for this packet |
|---|---|
| Constraint fit | Obeys §3 (per-body encoder/WM/critic, read-only asset, licensing, naming)? |
| Falsifiability | Do B1-RT and the arm criteria fail clearly within the budget? |
| Evidence demand | GPU-h and owner effort within the SCHEME_PLAN §8 envelope (≈ 10 GPU-h for P6b+P6d)? |
| Failure modes | Are R7, R8, R10, R11 and R13 named, each with a detectable signature? |
| Integrability | Fits the frozen P1 seam (no upstream edits, checkpoint compatibility, sidecar)? |
| Latency / criticality class | Policy-rate decoder cost per update reported, on the same compile setting? |
| Complexity cost | Is every added mechanism tied to a named risk or gap (GAP-1–GAP-7)? |
| Reversibility | Can it be abandoned without touching B0/B2 artifacts or the owner asset? |

**Gates before ranking:** a §3 constraint violation, or a claim of whole-policy zero-shot transfer, means Reject.

## 7. Spike criteria (draft; frozen into `spikes/B1/PLAN.md` at P6c)

- **Stage 1, B1-RT** (SCHEME_PLAN §5): RT-1..RT-4 and RT-6..RT-8 pass, and RT-5 is recorded. Failing any check means `BLOCKED.md`, and no arm runs.
- **Stage 2, arms** (SCHEME_PLAN §4): primary metric AULC over equal env steps, 3 seeds for the main arms.
  - *Signal:* AULC(H-A-xfer) ≥ 1.2 × AULC(H-A-scratch) **and** AULC(H-A-xfer) ≥ AULC(H-M-xfer) − 2·SE.
  - *Stronger claim:* AULC(H-A-xfer) − AULC(H-M-xfer) ≥ 2·SE.
  - *Kill:* AULC(H-A-xfer) ≤ AULC(H-A-scratch), **or** AULC(H-A-xfer) < AULC(H-M-xfer) − 2·SE.
  - *Inconclusive:* anything else. No seeds are added without a sealed amendment.
- The verdict is computed by the harness, machine-readable. Prose never overrides it.

## 8. Roster guidance (allocated under A.7 at freeze; not bound here)

Recommended: Orchestrator `claude-opus` (writes the brief and does not author); Author A `claude-opus` in a separate firewalled process; Author B `codex-astra` high; adjudicator `agy`, or one adjudicator per authoring family if a third family is unavailable; infra/runner code `claude-sonnet`; GPU runner the owner on Colab (OVERLAY-001). The frozen `roster.md` with A.5 fields is written at program root before Step 2.

## 9. Preconditions before Step 2 (all required)

- P-1 B0+B2 combined gate is **Go** or **Go-with-caveat** (SCHEME_PLAN §3), or the Human lead overrides in writing.
- P-2 Human lead has signed RV-1 (non-inferiority gating).
- P-3 **Provisional depth:** the Human lead signs the depth-2 raise in an appended amendment to this brief, **or** D-001 is Locked (method §13.3, RV-7, BLK-10).
- P-4 Human lead confirms that private runtime adaptations of the licensed motion are acceptable (BLK-11).
- P-5 Paid-compute gate for P6b/P6d (BLK-12).
- P-6 P1 freeze manifest exists. D-DESC is decided, or its degraded outcome is recorded.

## 10. Step budgets and degraded outcomes

| Step | Budget | Degraded outcome if skipped or cut |
|---|---|---|
| B1-P0 asset readiness (CPU) | 1 wake | B1-RT cannot start, so the packet pauses |
| Step 2 drafts | 1 wake, equal caps for both authors | A single draft means the decision is capped at Provisional and labelled single-candidate |
| Steps 3–4 review + adjudication | 1 wake | No adjudication means no PLAN seal |
| B1-RT (Colab) | ≈ 1.5 GPU-h | Failure means `BLOCKED.md` and a return to brief amendment |
| B1 arms (Colab) | ≈ 8–9 GPU-h | Partial seeds are reported as inconclusive, never as a pass |

## 11. Artifacts

`briefs/B1-home-humanoid-cross-embodiment.md` (this file; amendments are appended only), `roster.md`, `proposals/`, `reviews/`, `decision.md` (B1), `spikes/B1-RT/`, `spikes/B1/`, `logs/seal.log`, `retrospective.md`.
