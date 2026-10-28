# P3 red-team binding (objections only) — spikes/B0/PLAN.md

Not a contest packet (no competing authors; A.7 contest roster not required). One cross-family reviewer per SCHEME_PLAN §1 P3 / §7. Program `roster.md` (P1, sealed) is not edited.

| Field | Value |
|---|---|
| Role and packet | Red-team reviewer (objections only), P3 |
| Model family / identifier | OpenAI Codex · `gpt-6-astra` (codex-cli 0.163.0), catalog `codex-astra` |
| Effort | high (catalog default) |
| Limits | `timeout 1500` s wall clock, one pass per attempt |
| Tools | shell, read-only |
| Sandbox | `-s read-only -C <program root>`; no writes; deliverable = last message |
| Invocation | `codex exec -m gpt-6-astra -c model_reasoning_effort=high -s read-only -C <root> --skip-git-repo-check --json -o logs/p3/redteam-attemptN-last-message.txt - < packets/P3/prompt-redteam.md` |
| Prompt | `packets/P3/prompt-redteam.md` (sha256 in `logs/p3/redteam-attempt1-inputs.sha256` and seal log) |
| Context files | listed in the prompt |
| Orchestrator | Claude · claude-opus-5-5 (Claude Code), medium; writes and seals the PLAN; dispositions each objection in `packets/P3/REDTEAM-DISPOSITION.md` |
