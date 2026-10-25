# EVAL_REVIEW: SuperMimic-style WM loop + Junior-(B) shared attention policy, with home-humanoid cross-embodiment

**Packet:** run-002-eval-scheme (evaluation + written scheme only). **Written:** 2026-10-25 14:23–14:50 EDT (America/Toronto).
**Method:** global pin v1.1, sha256 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0` (verified). Overlay: `method/local/README.md`, plus `method/local/OVERLAY-001-owner-colab-runner.md` from this packet.
**Decision cap:** Provisional. **Author:** Claude Code (single model, `claude-opus`). This is a single-author evaluation, not a contest adjudication. Under method §6.3 and §11.5 it counts as one reviewed opinion, not as independent agreement.
**Companion:** `docs/SCHEME_PLAN.md` (packets, arms, criteria), `briefs/B1-home-humanoid-cross-embodiment.md`.

No Colab or GPU training has run in this program. Every performance statement below is a hypothesis or an upstream claim (ledger X-001). None is a result.

---

## 0. Verdict (summary)

**Accept the scheme with revisions (Provisional).**

| # | Item | Verdict |
|---|---|---|
| V1 | Do not use Junior-(A), the energy-based differentiable soft-body plant, as the world model | **Accept (unchanged).** §2 gives the reasons. Nothing in this review reverses the consensus |
| V2 | Junior-(B) shared per-actuator attention decoder in place of the MLP decoder, with WM/BPTT loop unchanged | **Accept** as the architecture under test |
| V3 | B0 as the gate to B1 ("kill if attention ≤ MLP …") | **Revise.** On one fixed body, B0 tests the *cost of generality*, not its benefit. Gate B1 on **non-inferiority** plus stability, not on superiority (§3.3, RV-1) |
| V4 | B2 permutation test | **Accept the scaffold amendment.** Permutation is architectural. The empirical content is mask retention ρ(f). Add a mask-fairness rule for the MLP arms (RV-2) |
| V5 | B1 as "second embodiment" | **Revise and make concrete.** Only the *decoder* is body-agnostic. The motion encoder, goal layout, WM, critic, action scaling and reference motion are all body-specific. B1 must be defined as transfer of the shared decoder with per-body encoder/WM/critic (§4, RV-3..RV-6) |
| V6 | Colab plus the public mjlab reproduction as venue/stack | **Accept**, with the feasibility risks in §5 and a human gate on paid Colab compute |
| V7 | Prior scaffold | **Keep as frozen provisional scaffolding.** It got several engineering choices right. It also skipped process, and it has gaps that matter for B1 (§6) |

The revisions RV-1..RV-8 (§7) are proposals to the Human lead. They change kill and gate wording in `docs/DESIGN_REVIEW.md` §3, so they need a signature before `spikes/B0/PLAN.md` is sealed. No B0 plan is sealed yet, so no contest is affected (method §10.4, Class 2, step not started).

---

## 1. What the scheme is (restated so the critique has a target)

- **Plant:** a rigid floating-base humanoid tracking reference motion (LAFAN1-scale clips) in MuJoCo / MuJoCo Warp, through the public mjlab reproduction (X-001).
- **Learning loop (SuperMimic-style):** a learned differentiable world model (WM) is trained on simulator transitions. The policy is trained by imagining H-step rollouts inside the WM and back-propagating the tracking objective through time (BPTT). A lighter joint-critic variant is a parallel line (A0/A1) and is not blocked by this work.
- **Policy:** `a = Decoder(MotionEncoder(goal), obs_hist)`. Upstream decoder: an MLP from `[z(32), obs_hist(930)]` to 29 joint position-target offsets.
- **Change under test (Junior-(B)):** replace only the decoder with a shared per-actuator attention module. There is one token per hinge joint (state history plus a morphology descriptor), a root token and a z token. A shared query MLP, cross-attention and a shared readout produce one scalar per actuator. Code: `code/attention_policy.py`.
- **Experiments:** B0 (attention vs param-matched MLP), B2 (permute/mask), B1 (second body: the owner-provided home humanoid under `assets/home_humanoid_mjcf/`).

---

## 2. Junior-(A) vs Junior-(B): why they must stay separate

The Junior line contributes two things that are independent:

| | **Junior-(A): energy-based differentiable soft-body plant** | **Junior-(B): morphology-adaptive shared attention policy** |
|---|---|---|
| What it is | An analytic, differentiable physics model (mass-spring / energy minimisation) used as the thing gradients flow through | A policy factorisation: shared weights per actuator, attention over body tokens, keyed by body descriptors |
| What problem it solves there | Gives smooth gradients for a soft body where contact is mild | Lets one policy drive bodies with different numbers of vertices/muscles |
| Fit to a rigid humanoid with stiff foot contact | **Poor.** (1) Model mismatch: rigid links, joint limits and impulsive ground contact are not soft-body energy terms. (2) SuperMimic learns a WM *specifically so that* policy gradients do not pass through non-smooth rigid contact. An analytic plant brings back exactly that pathology, or smooths it into a different, wrong plant. (3) The colleague result that a lighter joint critic nearly matches the generative WM suggests the predictor is not the bottleneck on this tracking line, so a heavier physics predictor buys little. | **Plausible.** The scarce piece on this line is a policy that factorises across body graphs. Junior-(B) is exactly that, and it can be swapped in at a clean seam |
| Status here | **Out of scope as a WM substitute** (V1). It may be revisited only as a separate, explicitly briefed question (for example, a soft-contact foot model), never as a silent WM swap | **In scope** |

Mapping (B) onto a rigid body is not one-to-one, and the scaffold docstring states this correctly. Junior's muscles are homogeneous and its vertices are geometric points. A humanoid's actuators differ in effort limit, gain, range and role. Its "vertices" are joints in a kinematic tree. So the morphology descriptor carries more of the weight than it does in Junior, and **actuator properties belong in the descriptor** (RV-4). Without them, "the same weights for every actuator" asks one readout to output a 3.7 N·m head command and a 21 N·m hip command with nothing to tell them apart except geometry.

**Strong reason to reverse the no-(A)-as-WM consensus?** None found. The consensus stands.

---

## 3. SuperMimic-loop assumptions that the scheme relies on

### 3.1 Assumptions that hold (from reading the upstream seam; not verified on GPU)

- **A1. Decoder-only swap is clean.** The decoder's input is `(z, obs_hist)` and its output is the 29-d action. The WM consumes actions, not decoder internals. Replacing the decoder leaves the WM interface unchanged (`code/vendor/NOTES.md` seam table).
- **A2. Checkpoint and eval compatibility.** The subclass keeps the `policy` state_dict layout and the forward signature. A sidecar JSON rebuilds the decoder for eval.
- **A3. Initial-action parity.** Both arms use the same last-layer gain (0.01), so early rollouts in both arms start near the default pose.

### 3.2 Assumptions that are untested and could break B0

- **A4. BPTT stability through attention.** The decoder sits inside the H-step imagination graph. That means gradients pass through H × (softmax + LayerNorm + MHA). Softmax saturation and LayerNorm gradients over 16–32 steps are a known source of exploding or vanishing gradients that an MLP decoder does not have to the same degree. *Test:* log the per-update policy grad-norm and clip fraction for both arms (SCHEME_PLAN M-6). A NaN or a persistent clip saturation in only the attention arm is an architecture-interaction finding, not a tuning nuisance.
- **A5. Shared data distribution.** The WM is trained on data from the current policy. A decoder that explores differently changes the WM's training distribution, so arms differ by more than the decoder. This is inherent and acceptable, but B0 must report WM loss per arm so the reader can see it.
- **A6. Compute parity.** Matched params are not matched compute: about 27× forward FLOPs per sample (scaffold amendment, R4). The decoder runs once per imagined step, so the factor applies to the whole imagination loop. Under an equal wall-clock budget, the attention arm gets fewer updates. **Primary budget: equal env steps and equal policy updates. Secondary: equal wall clock.** Both are reported. The kill clause "AND slower" is dropped as a kill condition and kept as a reported cost (RV-1).
- **A7. Observation layout.** The 930-d term-major history (S2) and the joint order shared by the descriptor rows and the obs/action (S1) are asserted only against our reading of upstream. A silent permutation would make B0 unfair to attention, and only to attention.

### 3.3 The gating logic is aimed at the wrong question (RV-1)

On a single fixed 29-DoF body, there is no structural reason to expect a shared attention decoder to beat a well-tuned MLP on tracking return. The MLP can learn any joint-specific mapping, and the shared decoder is a constrained family. The benefits Junior-(B) claims are **robustness to missing/permuted inputs (B2)** and **reuse across bodies (B1)**. So:

- B0 is a **non-inferiority** test. Question: how much single-body return and compute does generality cost?
- B2 is a **robustness** test.
- B1 is the only **superiority** test of the core claim.

The current rule, "Without a signal, B1 does not start", where signal means attention > MLP by ≥ 0.02 or a B2 retention gain, can kill the idea for the wrong reason: a tie on B0 is the *expected* outcome of a correct design. The proposed rule (SCHEME_PLAN §3) is **proceed to B1 if** attention is non-inferior on B0 (R_att ≥ R_mlp − δ, δ = 0.05, or the pooled-SE equivalent) **and** trains stably (A4). **Kill if** attention is inferior beyond δ **and** shows no B2 retention gain. This is a Class-2 change to future spike criteria and needs the Human lead's signature (§7).

Even if RV-1 is signed, B1 under the method stacks a Provisional decision on another Provisional decision (B1 → B0 decision → D-001). That is depth 2, and method §13.3 caps the depth at 1. Before B1 starts, the Human lead must either sign the depth raise in the B1 brief or Lock D-001. The B1 brief records this as a precondition.

### 3.4 Mask fairness in B2 (RV-2)

The attention arm *removes* masked tokens (key-padding). The MLP arms can only *zero-fill* the masked joint's slices. Neither arm trains with masking in B0 (`train_mask_frac: 0`). Removing an input and zeroing it are not the same perturbation: a zero joint angle is in-distribution and wrong, while a removed token is absent. A ρ gap therefore mixes an architectural property (attention can represent absence) with a perturbation asymmetry. Both are legitimate, but they must be reported under their own names. Add one control: an MLP with a per-joint *mask indicator* input (zero-fill plus a mask bit), trained with the same `train_mask_frac` as an attention arm trained with masking. Report the untrained-mask and trained-mask conditions separately.

---

## 4. Cross-embodiment onto the home humanoid: what can actually transfer

### 4.1 Asset inventory (verified on CPU, mujoco 3.17, 2026-10-25 14:2x EDT)

Directory `assets/home_humanoid_mjcf/`. The primary model is the single `*.xml` file in that directory (sha256 `856ce7021f0adda2…`), with `meshdir="meshes"` resolving to `meshes/` alongside it. The filenames inside the directory are kept as exported, so prose refers only to the directory.

| Property | Value | Consequence |
|---|---|---|
| Joints | 1 free + **22 hinges**: arms 2×4 (shoulder pitch, shoulder roll, upper-arm yaw, elbow), head 2 (yaw, pitch), legs 2×6 (hip pitch, hip roll, thigh yaw, knee ("calf"), ankle pitch, ankle roll) | No waist and no wrist DoF. The leg chain order (pitch→roll→yaw→knee→ankle pitch→roll) matches the upstream 29-DoF body's leg semantics, which helps joint-space retargeting |
| Bodies / mass | 28 bodies, **15.9 kg** total. qpos0 base height 0.385 m. Hip-to-ankle vertical 0.28 m. Camera body about 0.68 m | A compact, roughly half-scale home humanoid relative to the upstream 29-DoF reference body (exact ratio to be measured in B1-P0). Metric descriptors and root-velocity references shift by about 2× |
| **Actuators** | **`nu = 0`** (no `<actuator>` block) | **Blocker BLK-1.** Nothing moves under control |
| Effort limits | `actuatorfrcrange` is set on every hinge: arms ±10, head ±3.7, legs ±21 N·m | Usable as actuator effort limits |
| Armature | **0 on all DoFs**; damping 0.02 | **Blocker BLK-2.** mjlab-style PD gains derived from reflected inertia (stiffness ∝ armature·ω²) come out as zero. Gains need motor data or a documented assumption |
| Collision | 46 primitive collision geoms (capsule/box/sphere). The 27 mesh geoms are visual-only (`contype=conaffinity=0`) | Good for MuJoCo Warp: no mesh-mesh collision cost |
| Self-contact at qpos0 | **4 contacts, wrist links vs hip-pitch/thigh links, penetration up to 8.6 mm** | **BLK-4.** Needs a default pose with arms slightly abducted, or contact exclusions |
| Embedded floors | **Two** plane geoms in the worldbody (`ground`, `floor`) | **BLK-5.** mjlab supplies its own terrain. These must be stripped or excluded at load (via a spec edit at load time, never by editing the owner file) |
| Keyframe / default pose | none (`nkey = 0`); qpos0 is all zeros | **BLK-6.** The tracking env needs a default standing pose. The scaffold descriptor's "default angle" column reads qpos0, not the env default |
| Passive drop | Base z goes from 0.385 to 0.212 m in 1 s with no actuation | As expected with `nu = 0`. It confirms gravity, contacts and mass are sane |
| Meshes | 27 STL, about 70 MB; sha256 of all 27 match `mesh_manifest.json` | Asset intact. Do not re-copy or re-export |
| Sites | 2 anatomical ankle markers (geometric audit markers, per `sources.json`) | Usable as foot keypoints for retarget QA |
| Provenance | `sources.json`: export pack from a learned dense-surface-correspondence retargeting project, plus a reference prepare script | That pipeline needs SMPL-X body models (separately licensed). It is not the default retarget route here (§4.3) |

### 4.2 Which parts of the policy stack are body-agnostic?

| Component | Body-agnostic? | B1 implication |
|---|---|---|
| Attention decoder weights | **Yes, structurally.** No weight depends on J (except the `id_mode=index` ablation). CPU check: a 29-joint decoder returns 22 finite actions for this body | The only component that can transfer |
| Morphology descriptor | **Partly.** Absolute metric anchors (≈2× scale shift); depth normalised by *per-body* max depth (the same joint gets a different value on each body); limb one-hot from names; **no actuator or limit features** | RV-4: scale-normalise anchors; use fixed-constant depth normalisation; add effort limit, joint range and action scale |
| Action semantics | **No.** Upstream actions are position-target offsets scaled per joint by actuator parameters. The same scalar means a different torque on each body | RV-5: the decoder outputs a normalised action, and the per-body env applies its own action scale. The descriptor carries that scale |
| Motion encoder / goal | **No.** The goal vector (680 or 689 dims) is laid out against the 29-DoF reference | Per-body encoder (B1 MVP). Tokenised per-joint goals are a later arm (RV-3) |
| World model / critic | **No.** Sized to the 29-DoF state (71 = 2·29 + 13). Under the same layout this body is 2·22 + 13 = 57 (verify) | Per-body WM and critic, trained from scratch. A shared, tokenised WM is out of scope for B1; it would be its own question |
| Reference motion | **No.** The LAFAN1 retargets exist only for the upstream body | BLK-3: a retarget route is needed (§4.3) |
| Env config | **No.** Tracked bodies, termination bodies, default pose and actuator groups are named per body | BLK-8: a per-body mjlab tracking config |

**So "cross-embodiment" here means:** the same decoder *architecture* and (for transfer arms) the same decoder *weights* are reused across the two bodies, while each body gets its own encoder, WM, critic, env config and reference motion. Zero-shot whole-policy transfer is **impossible by construction** in this stack, and no document should imply otherwise. The scaffold's `test_b1_second_body_from_owner_mjcf` is a shape and finiteness test. It is **not** evidence of cross-embodiment.

### 4.3 Retarget routes for the home humanoid

| Route | Method | Cost | Quality risk | Use |
|---|---|---|---|---|
| **RT-a, joint-space map (default for B1 smoke)** | Map the upstream 29-DoF LAFAN1 retargets joint by joint (hip pitch/roll/yaw→hip pitch/roll/thigh, knee→calf, ankles, shoulder pitch/roll/yaw→shoulder pitch/roll/upper-arm, elbow). Drop waist and wrists, hold the head at 0, check axis signs against the descriptor axes, clip to limits. Scale root height and planar velocity by the leg-length ratio | CPU, deterministic, small | Foot skate and contact inconsistency. The missing waist changes upper-body balance. Clipping on the asymmetric hip-roll ranges | B1 pipeline smoke and first arms. Gate the quality with retarget QA (SCHEME_PLAN §5, RT-4) |
| RT-b, keypoint IK from source mocap | Scaled keypoint IK (feet, pelvis, hands, head) per frame with limit constraints | CPU, moderate | Lower skate. Needs care with LAFAN1 skeleton scaling | Upgrade if RT-a fails QA on more than 1 of the 4 smoke clips |
| RT-c, learned dense correspondence (export-pack provenance) | Learned surface-correspondence retargeting | GPU plus external body models with their own license | Unknown here | Out of scope for Colab-first B1. Reference only |

**Licensing (R10):** LAFAN1 motion is CC BY-NC-ND 4.0 (X-002). A retarget onto a new body is an adaptation. Generate it only at Colab runtime. Never commit or share it. The Human lead should confirm that private, non-shared research adaptations are acceptable before B1 runs (decision ask in STATUS).

---

## 5. Colab / mjlab feasibility

| Item | Assessment |
|---|---|
| Stack | The public mjlab reproduction (X-001, MIT) runs on uv/Python 3.12 with MuJoCo Warp. That is the right Colab-first choice over container-heavy alternatives |
| R1 driver vs CUDA-13 wheels | The most likely first failure. The runbook has an unverified CUDA-12 fallback. A wheel substitution is a deviation and must be logged |
| R2 T4 (sm_75) | Prefer L4. On T4, halve `num_envs` and batch for all arms together |
| Session limits (R6) | B0 at 3 seeds × 2 arms + 1 reference seed, 0.5 h each, is about 3.5 GPU-h before eval. That is several sessions, so checkpoint and resume are needed. B1 adds per-body WM training: at least 2× B0 |
| Paid compute | Colab compute units are paid compute. **Human gate (method §6 rule 4)** before B0 and B1 microbenches, but not for the 1-seed smoke if the owner already runs it |
| Home humanoid in MuJoCo Warp | Favourable: primitive collisions only and 22 DoF (fewer than 29). Unverified in Warp until B1-P0 |
| Absolute returns (R3) | Low at 0.5 h on a small GPU. Only relative, matched-budget comparisons are claims |
| Who runs it | The owner runs Colab. The research box has no NVIDIA GPU. `method/local/OVERLAY-001` records how a human-run spike keeps §12.2 discipline |

**Feasible?** B0 smoke and B0 microbench: yes, conditional on R1. B2: yes, it reuses B0 checkpoints (plus small ablation trainings). B1: feasible at smoke scale after BLK-1..BLK-8 are cleared. The transfer arms are the most expensive part of the program.

---

## 6. Prior scaffold: what it got right, what it skipped

### 6.1 Got right (keep)

1. **Clean seam.** It rebinds the upstream `Policy` name through a subclass and edits no upstream file. Checkpoint layout and forward signature are preserved, and a sidecar records the arm config.
2. **Param-matched comparator** (+1.0%), plus an honest **compute-asymmetry amendment** (27× FLOPs), plus a compute-heavier reference arm.
3. **It recognised that B2 permutation is architectural** (rel err 2.2e-6 vs O(1) for the MLPs and the index ablation), and moved the empirical content to mask retention.
4. A **non-actuated root token** that is never masked. z enters as a key/value token and in every query/readout.
5. **No overclaiming.** It refuses `--mode upstream` without CUDA, says "plumbing only" on the toy BPTT, and never claims Colab training.
6. **Licensing hygiene.** Motion data is downloaded only at runtime, and nothing is committed.
7. **Append-only evidence.** The failed smoke attempt 1 was kept. A ledger exists with X/D/P entries.
8. It **noted the B1 prerequisites** (nu=0, no retargets, per-body WM).

### 6.2 Skipped process (fix going forward)

1. **Implementation before evaluation and scheme.** A solo implementation sprint ran before any brief, rubric or scheme. The owner corrected this. It is filed as `method-issues/ISSUE-001.md`.
2. **No brief with a rubric before solutions** (method §4 Step 1, §5). The attention design and its hyperparameters (d=128, 1 self-attention layer, descriptor features) were chosen and "accepted" by the same agent. D-001 rests on "thread consensus". Per §6 rule 3 that is weak evidence, and D-001 is correctly Provisional, but nobody has red-teamed the design.
3. **No competing draft** on the two choices that matter most for B1: descriptor design and goal representation. SCHEME_PLAN P1/P6 open these as two-author packets.
4. **Seam tested only against a fake package.** That is fine as plumbing, but it must not be read as a verified integration (S1–S3 remain open).
5. **Placeholder clip names** in `configs/colab_smoke.yaml`. Nobody has verified that they exist in the dataset.

### 6.3 Technical gaps that matter later (no fix in this packet)

| ID | Gap | Affects | Proposed handling |
|---|---|---|---|
| GAP-1 | Descriptor "default angle" reads `qpos0`, not the env default pose | B0 (minor), B1 | Pre-freeze fix FX-1 (SCHEME_PLAN P1) |
| GAP-2 | Depth normalised by per-body max depth | B1 transfer | FX-2: fixed constant |
| GAP-3 | Absolute metric anchors (≈2× scale shift across bodies) | B1 transfer | RV-4, B1 design packet |
| GAP-4 | No actuator or limit features in the descriptor | B1 transfer (and B0 readout) | RV-4, B1 design packet |
| GAP-5 | Action-scale semantics differ per body | B1 transfer | RV-5 |
| GAP-6 | MLP mask = zero-fill with no indicator | B2 interpretation | RV-2 |
| GAP-7 | `test_b1_*` is a shape test only | Claims hygiene | Rename in prose to "J-agnostic shape test". No code change now |

---

## 7. Revisions proposed (need Human lead signature where marked)

| ID | Revision | Class (method §10.4) | Signature? |
|---|---|---|---|
| RV-1 | B0 becomes a non-inferiority gate (δ = 0.05) plus a stability check. "Slower" becomes a reported cost, not a kill term. B1 is the superiority test | 2 (future spike criteria, not yet sealed) | **Yes** |
| RV-2 | B2 adds an MLP mask-indicator control and separates untrained-mask from trained-mask conditions | 2 | **Yes** (with B0/B2 PLAN) |
| RV-3 | B1 MVP: shared decoder, per-body encoder/WM/critic. Tokenised-goal encoder is a later arm | Scheme scope | Yes (B1 brief) |
| RV-4 | Descriptor v2 for B1: scale-normalised anchors, fixed depth normalisation, actuator/limit/action-scale features | B1 design packet (two authors) | Via B1 adjudication |
| RV-5 | Normalised action output. The per-body env applies the scale | B1 design packet | Via B1 adjudication |
| RV-6 | Retarget route RT-a by default, RT-b on QA failure | B1 | Yes (B1 brief) |
| RV-7 | Provisional depth-2 chain for B1: sign the raise or Lock D-001 | Governance (§13.3) | **Yes** |
| RV-8 | Primary budget = equal env steps and updates. Equal wall clock is secondary and reported | 2 | **Yes** (with B0 PLAN) |

---

## 8. Risk register (R1–R6 inherited from `docs/COLAB_RUNBOOK.md` §9; new from R7)

| ID | Risk | Likelihood / impact | Mitigation / owner packet |
|---|---|---|---|
| R1 | CUDA-13 wheels vs Colab driver | High / blocks all GPU work | Fallback index, logged deviation. P2 |
| R2 | MuJoCo Warp on T4 | Med / slow or blocked | L4 preferred. P2 |
| R3 | Low absolute returns at Colab budget | Certain / limits claims | Relative, matched-budget claims only |
| R4 | Params ≠ compute (27×) | Certain / confound | RV-8. Report cost per update |
| R5 | Joint-order mismatch (S1), per body | Med / silently unfair | Assert on the first run of each body. P2, B1-P0 |
| R6 | Colab disconnects | High / lost runs | `max-hours`, resume, copy logs out after each arm |
| R7 | Descriptor scale shift between bodies (GAP-3) | High for transfer arms | RV-4. Scale-normalisation ablation in B1 |
| R8 | Action semantics differ per body (GAP-5) | High for transfer arms | RV-5 |
| R9 | Goal/encoder is body-specific, so "transfer" is decoder-only | Certain / limits claim scope | RV-3. State the scope in every B1 claim |
| R10 | Retarget quality (RT-a) and LAFAN1 ND licensing of adaptations | Med / High | QA gate RT-4, RT-b fallback. Runtime-only. Human lead confirmation |
| R11 | Zero armature and unknown motor data, so PD gains are assumed | High / changes task difficulty | Documented assumption plus a ±50% gain sensitivity check in B1-P0 |
| R12 | Self-contact at default pose; two embedded floors | Certain / env breaks | Default pose with arm abduction or contact excludes. Strip floors at load. B1-P0 |
| R13 | BPTT instability through attention (A4) | Med / kills the attention arm for a non-architectural reason | Grad-norm logging. Same clip setting for both arms. Pre-registered single retry rule in PLAN |
| R14 | Wall-clock confound (A6) | Certain | RV-8 |
| R15 | B0 superiority gate kills B1 for the wrong reason | Med / loses the main question | RV-1 |
| R16 | Statistical power at 3 seeds | High / unresolved ties | Pre-registered tie → "inconclusive", not "kill". Seeds may increase only by sealed amendment |
| R17 | Single-author design (consensus theater) | Med | Two-author packets for B1 design choices (SCHEME_PLAN P6) |
| R18 | Plant-class wording leakage from exported filenames and upstream identifiers | Low / policy | Prose refers to directories and roles only. Filenames stay as exported for path stability |
| R19 | Provisional depth-2 chain (B1 → B0 → D-001) | Certain / governance block | RV-7 |
| R20 | Upstream pin drift (repo HEAD moves) | Low | Commit pin in NOTES. No floating `main` |

---

## 9. Confounds of this evaluation

- Single author and single model family. No blind review and no adjudicator. Agreement with the prior design review is **framed agreement** (§11.5): the prior review was in this author's readable context.
- No GPU access. Upstream internals (goal layout, gain recipe, state size) are inferred from the scaffold's notes and the pinned source as summarised there. They were not re-read from upstream in this packet.
- The asset inventory is CPU MuJoCo 3.17 only. MuJoCo Warp behaviour is not checked.
