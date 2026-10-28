# Design review: SuperMimic + Junior-(B) on Colab

**Status:** Accept scheme with refinements (Provisional).  
**Date:** 2026-10-25 (America/Toronto)  
**Program:** `/srv/claude/research/supermimic-junior-b-colab/`

## 1. Scheme verdict

**Accept** the thread consensus:

1. Do **not** drop-in replace SuperMimic world model (WM) with Junior/algovivo energy soft-body sim.
2. Prefer **Junior-(B)**: shared attention action policy (vertices/muscles in Junior → joint/link tokens + per-actuator shared attention on a rigid humanoid).
3. Keep SuperMimic imagine/BPTT (or colleague joint-critic) loop; change **policy architecture only**.
4. Validate on small LAFAN1-style set; B2 permute/mask; later B1 multi-embodiment; kill if no gain vs matched-param MLP.

### Refinements

- Treat Junior as two separable contributions: **(A)** energy differentiable plant (out of scope as WM substitute) vs **(B)** shared attention policy (in scope).
- Colab first: mjlab reproduction path over Isaac Docker.
- Box has no GPU: never claim Colab training finished unless a run completed; scaffold + document owner Colab steps.
- Use generic home-humanoid wording in research files (no commercial product brands).

## 2. Why (B) over (A) for this plant

SuperMimic already supplies a learned differentiable predictor and deliberately avoids gradients through non-smooth rigid contact. The scarce bit relative to Junior is **policy factorization across variable body graphs**, not another physics surrogate. Colleague evidence that a lighter critic can nearly match generative WM reward further argues against investing in a heavier physics-as-predictor (A) on the tracking line.

## 3. Experiment map (scaffold targets)

| ID | Question | Notes |
|---|---|---|
| **B0** | Attention policy vs matched MLP decoder on same WM/critic loop | Primary Colab microbench; LAFAN1-scale or tiny clip subset |
| **B2** | Permute token order; mask 10-20% non-root tokens | Invariance / set-structure test |
| **B1** | Second embodiment / masked DoF (later) | Only if B0/B2 show signal |
| **A0/A1** | Learned WM vs joint-critic (colleague line) | Optional parallel; not blocked on (B) |

**Kill:** attention <= MLP on return AND no B2 gain AND slower train -> stop; do not scale library.

## 4. Colab constraints

- No NVIDIA GPU on research box.
- Prefer public mjlab SuperMimic reproduction (uv-friendly) as dependency base; vendor or submodule under `code/vendor/` only as needed with license notes.
- Reduced `num_envs`, short imagination horizon for T4/L4 smoke; full H=32 / large batch is post-Colab or owner GPU.
- Motion data: document download steps (LAFAN1 retargets); do not redistribute restricted motion dumps inside the program tree if licenses forbid it.

## 5. Scaffold deliverables (this orchestration)

- README, this design review, Colab runbook
- Minimal attention policy module (shared Query/Attn/Readout)
- Train/eval stubs wired for reduced configs
- One Colab notebook: install -> smoke forward -> optional short train
- Success/kill metrics checklist
- CPU import smoke on the box where possible

## 6. Out of scope (for now)

- Replacing WM with algovivo
- Full BONES-SEED / 129k-motion scale
- Real-robot deployment claims
- Class-2 sealed contest packets (until Human lead authorizes)

## 7. Asks for Human lead / owner

- Confirm program slug `supermimic-junior-b-colab` (or rename).
- Confirm Colab as first training venue (vs owner local GPU).
- When scaffold is ready: open Colab runbook and run smoke; report return/fail vs MLP.


---

## Amendment note — 2026-10-25 14:14 EDT (America/Toronto), Orchestrator, Provisional

These refine the scheme. They do not reverse it. Measured during the scaffold wake on the research box (CPU only); see `orch/STATUS.md`.

1. **Matched params ≠ matched compute (material for reading B0).** The shared per-actuator decoder applies its weights once per token. At about 0.46 M params, it costs about 25.7 MFLOP/sample forward, vs 0.94 MFLOP for the param-matched MLP (27×) and 9.5 MFLOP for the upstream-width MLP (4.7 M params). As written, the §3 kill clause "AND slower train" will almost always be true. In practice the kill condition is therefore *no return gain AND no B2 gain*. B0 therefore reports three arms: `attention`, `mlp_matched` (kill comparator, unchanged), and `mlp_upstream` (compute-heavier reference, 1 seed). Every arm reports cost per update.
2. **B2 permutation is architectural, not empirical.** With tokens keyed only by default-pose morphology descriptors (`id_mode=morph`), the attention decoder is permutation-equivariant by construction. The CPU smoke measured a relative error of about 2e-6. The empirical B2 signal is **token-mask retention** ρ(f) = R(mask f)/R(0) at f ∈ {0.1, 0.2}, plus the `id_mode=index` ablation, which deliberately breaks equivariance.
3. **Root token.** The floating base has no actuator. Base angular velocity and gravity history form a non-actuated root token that is never masked. The motion latent z enters both as a key/value token and in every query/readout.

---

## Note — 2026-10-25 EDT (America/Toronto), Claude Code eval + scheme packet (run-002), Provisional

The Claude Code evaluation + written-scheme packet is now on disk: **`docs/EVAL_REVIEW.md`** (critique, accept/revise, Junior-(A) vs (B), loop assumptions, Colab feasibility, risks R1–R20, scaffold review) and **`docs/SCHEME_PLAN.md`** (packet sequence P0–P6, arms, acceptance/kill criteria, B1 home-humanoid runnable test, blockers). Cross-embodiment brief: `briefs/B1-home-humanoid-cross-embodiment.md`.

- The no-algovivo/Junior-(A)-as-WM consensus (§1 item 1) is **kept**. No strong reason to reverse was found (EVAL_REVIEW §2).
- Proposed revisions needing Human lead signature before `spikes/B0/PLAN.md` is sealed: **RV-1** (B0 becomes a non-inferiority gate, δ = 0.05; B1 is the superiority test; "slower" is reported, not a kill term), **RV-2** (mask-fairness controls in B2), **RV-7** (Provisional depth-2 chain for B1), **RV-8** (equal env steps/updates primary; wall clock secondary). These would supersede the wording of §3 "Kill" and the "Without a signal, B1 does not start" line once signed. This note does not edit those sections in place.
- B1 scope clarified: only decoder weights transfer. Encoder, WM, critic, env config and references are per body.
