# P5 PLAN red-team binding (objections only; not a contest)

- **Packet:** P5, `spikes/B2/PLAN.md`. Single-Orchestrator PLAN packet. No A.7 contest roster is required, and program-root `roster.md` (P1) is not edited.
- **Slot:** Red team / reviewer (SCHEME_PLAN §7: `codex-astra` high on each PLAN).
- **Catalog entry:** `codex-astra` (OpenAI Codex family; A.6 secondary preference). Exact identifier `gpt-6-astra`, codex-cli 0.163.0.
- **Effort:** high (catalog default).
- **Limits:** 30 min wall clock per round (`timeout 1800`).
- **Tools / sandbox:** shell, `-s read-only`, `-C` program root. No writes. Deliverable = last message, deposited mechanically by the Orchestrator.
- **Invocation:** `codex exec -m gpt-6-astra -c model_reasoning_effort=high -s read-only -C <program root> --skip-git-repo-check --json -o spikes/B2/redteam/redteam-r<N>-last-message.txt - < spikes/B2/redteam/prompt-redteam-r<N>.md`
- **Prompt / inputs:** `prompt-redteam-r<N>.md`. Prompt and PLAN-draft hashes are in `redteam-r<N>-inputs.sha256`.
- **Context files:** listed inside each prompt.
- **Dispositions:** by the Orchestrator, in `REDTEAM-DISPOSITION.md`. The Orchestrator wrote the PLAN, so it rules on the objections to its own draft. This is disclosed in PLAN §12 item 9.
