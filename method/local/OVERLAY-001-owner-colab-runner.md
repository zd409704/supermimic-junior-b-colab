# OVERLAY-001: owner-run Colab spikes (append-only)

**Extends:** global METHOD `pins/orchestrating-ai-research-teams.v1.1-9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0.md`, sha256 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0`.
**Added:** 2026-10-25 EDT, run-002-eval-scheme. **Status:** Provisional rule special. It does not replace any global rule.

**Why this is a special.** The global method assumes the Experiment runner is an agent process with tool-call logging (§11.6, §12.2). In this program every GPU spike is run by the **human owner** on Colab, because the research box has no NVIDIA GPU (`method/local/README.md`, special 1). The global text does not say how the §12.2 runner discipline applies to a human runner.

**Rules.**
1. The owner may hold the Experiment-runner slot for GPU spikes. `roster.md` records it as `runner: owner (human), venue: Colab <GPU type>`, with the `nvidia-smi` header copied from the run.
2. The runner receives only the sealed `spikes/<id>/PLAN.md`, the frozen tarball (with its hash in the P1 manifest) and the notebook/runbook. It does not receive the adjudication reasoning.
3. Every execution, including failed and aborted ones, is returned as a raw bundle. It is deposited unmodified under `logs/colab/<date>/`, and its sha256 is appended to `logs/seal.log` **before** any agent reads or analyses it (§12.3, mechanical deposit).
4. Any deviation (wheel substitution, `num_envs` halving, a session restart) goes in the bundle's `deviations.md`, in the owner's words or as captured stdout. An unlisted deviation found later is filed as a method issue.
5. Isolation audit (§11.6) concerns authors, not this runner. Missing tool logs for the human runner do not cap the decision, provided rules 2–4 hold.
6. The machine-readable harness verdict is computed from the deposited bundle by an agent process that is not the packet adjudicator.
