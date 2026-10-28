# P5-prep code review binding (objections only; not a contest)

- **Packet:** P5-prep, CR-B2-1 (a)–(g) and VERDICT-TOOL-B2 (h) against `spikes/B2/PLAN.md` sha256 `5d1f26f776a3ea56c2becd3ec2fa2cf8e88bd62c43a20f79415a96e82a3da11d`. Single-author engineering packet (Orchestrator-authored code). No A.7 contest roster; program-root `roster.md` (P1) is not edited.
- **Slot:** Reviewer (cross-family, objections only), same binding as the P5 PLAN red team (`spikes/B2/redteam/BINDING.md`).
- **Catalog entry:** `codex-astra` (OpenAI Codex family; A.6 secondary preference). Exact identifier `gpt-6-astra`, codex-cli 0.163.0. Effort high (catalog default).
- **Limits:** 30 min wall clock per round (`timeout 1800`).
- **Tools / sandbox:** shell, `-s read-only`, `-C` program root. No writes. Deliverable = last message, deposited mechanically (`-o`).
- **Invocation:** `timeout 1800 codex exec -m gpt-6-astra -c model_reasoning_effort=high -s read-only -C <program root> --skip-git-repo-check --json -o packets/P5/review/review-r<N>-last-message.txt - < packets/P5/review/prompt-review-r<N>.md`
- **Dispositions:** by the Orchestrator (the code author), in `packets/P5/review/REVIEW-DISPOSITION.md`. Disclosed: the author rules on objections to its own code.
