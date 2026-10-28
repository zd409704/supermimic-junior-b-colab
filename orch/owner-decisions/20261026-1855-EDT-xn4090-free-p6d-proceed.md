# Owner decision — xn-4090 free use + P6d proceed without re-ask

- Decision-id: 20261026-1855-EDT
- Program: /srv/claude/research/supermimic-junior-b-colab/
- Amends: orch/owner-decisions/20261026-1852-EDT-p6-start.md (3a0254de…)
- Authority: owner chat — XN-4090-GPU2 is owned hardware; train as fast as possible; do not re-ask for venue/spend on that host within program budgets

## Standing for this program (and Manager relay)

1. Prefer **xn-4090-gpu2** over Colab whenever a packet can run there (mutex, JumpServer/Mac mini path).
2. After **P6c** B1 PLAN is sealed, **proceed to P6d** on xn-4090 without another Manager START for GPU venue. Still seal PLAN first; still use orch/jobs READY state machine and seal-before-open deposits.
3. If SCHEME_PLAN text still says Colab for P6b/P6d, write a PLAN / overlay amendment that names xn-4090 as the venue before any READY job. Do not silently flip a sealed Colab-only PLAN.
4. Drive Claude 4 routine may stay paused; Claude 4 / Orchestrator push READY jobs promptly so the 4090 is not idle while work is queued.
5. Carry P5 NO_GAIN / u_deficit caveat unchanged.

## Unchanged hard stops

- No reopen of P4/P5 scoring
- No spend outside disclosed program GPU-hour envelopes without a Class-2 note
