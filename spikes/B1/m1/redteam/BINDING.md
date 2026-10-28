# M1 amendment red-team binding (objections only; not a contest)

- **Packet:** B1-M1 (Class-2 amendment M1, post-hoc re-score). Single-Orchestrator amendment packet. No A.7 contest roster; program-root `roster.md` (P1, frozen) is not edited.
- **Slot:** cross-family red team / reviewer (OVERLAY-002 rule 4; brief §5 item 6).
- **Catalog entry:** `codex-astra` (OpenAI Codex family; A.6 secondary preference). Exact identifier `gpt-6-astra`, codex-cli 0.163.0. Effort: high (catalog default).
- **Limits:** 30 min wall clock per round (`timeout 1800`).
- **Tools / sandbox:** shell, `-s read-only`, `-C` program root. No writes. Deliverable = last message, deposited mechanically by the Orchestrator.
- **Invocation:** `codex exec -m gpt-6-astra -c model_reasoning_effort=high -s read-only -C <program root> --skip-git-repo-check --json -o spikes/B1/m1/redteam/redteam-r<N>-last-message.txt - < spikes/B1/m1/redteam/prompt-redteam-r<N>.md`
- **Inputs:** prompt + amendment draft hashes in `redteam-r<N>-inputs.sha256`.
- **Restriction:** must not open the deposit tgz, `logs/xn4090/**/open-*`, or `orch/analysis/b1-eval-metric/evals.json`, and must not compute arm-level quantities under any candidate metric. The event log is audited (grep) before seal.
- **Dispositions:** Orchestrator, in `spikes/B1/m1/REDTEAM-DISPOSITION.md`. The Orchestrator wrote the amendment, so it rules on objections to its own draft (disclosed).
