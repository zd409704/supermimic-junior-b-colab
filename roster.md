# roster.md — P1 (scaffold freeze) incl. D-DESC contest

**Allocated by:** Orchestrator (Claude Code, `claude-opus`), P1 wake, 2026-10-25 EDT (America/Toronto), under method v1.1 A.6/A.7 (sha256 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0`) and `docs/SCHEME_PLAN.md` §7.
**Freeze:** frozen with `briefs/D-DESC.md` when both hashes are appended to `logs/seal.log` (event `FREEZE roster P1`) before D-DESC Step 2. Afterwards: Class-0 invocation fixes only (A.5 rule 5); anything else is a roster change (A.5 rule 4).
**Stakes classification (A.7 step 2):** D-DESC = high-stakes contest (two families required). P1 fixes FX-1..FX-4 = single-author engineering with a cross-family reviewer (no contest).
**Method overlays:** none needed for allocation. No rule exception is taken (Claude family present; second family = Astra high; third family adjudicator from catalog `agy`).

## Availability probe (actual, not intended; A.5 rule 1)

Probe logs: `logs/p1/probe/`.

| Catalog ID | Probe result (2026-10-25 14:43 EDT) | Consequence |
|---|---|---|
| `codex-astra` (`codex -m gpt-6-astra`) | OK. Run header: `provider: openai`, `reasoning effort: high`; reply self-identifies as GPT-6 | Bound as specified |
| `agy` | CLI present (v1.4.7). First probe failed on flag order (Class-0 invocation issue, see attempt log); `agy models` lists third-family models (`gemini-4-argon-*`) as well as Claude/OpenAI-hosted ones | Bound with `--model gemini-4-argon-high` so the adjudicator is pinned to a family that authored nothing |
| `claude-opus` / `claude-sonnet` as standalone `claude --model …` subprocesses | **Unavailable from the Orchestrator's shell:** `Not logged in · Please run /login` (`logs/p1/probe/sonnet-probe-attempt1-*.log`). The Orchestrator did not harvest credentials from other processes to work around this | **Gap.** The Claude-family slots are filled by **Claude Code Agent-tool subagents** spawned by this Orchestrator session (fresh context, not a fork; model `opus` = claude-opus-5-5, model `sonnet` = claude-sonnet-5-5). Same catalog family and model; the invocation differs from the catalog's CLI string. Recorded under Confounds of every decision in this packet |

## Slots

| Role / packet | Family · exact identifier | Effort | Limits | Tools | Sandbox (read / write) | Invocation | Prompt (template · instance hash) | Context files |
|---|---|---|---|---|---|---|---|---|
| **Orchestrator** (P1, all) | Claude · claude-opus-5-5 (Claude Code 2.1.308, `-p --model opus --effort medium`) | medium | wake budget | all | program root | relay launcher `prompts/launch-orch-p1-multiagent.sh` | `prompts/ORCH_P1_MULTIAGENT.txt` | all. **Does not author or adjudicate D-DESC** |
| **Author A** (D-DESC) | Claude · claude-opus-5-5 | medium (catalog default; inherited session effort) | 30 min wall clock | Read, Write, Edit, Bash (CPU `.venv`), Grep/Glob | reads: brief §9 set; writes: `packets/P1/ddesc/drafts/A/` only (by instruction + audit; see Isolation) | Claude Code Agent tool, `subagent_type=general-purpose`, `model=opus`, prompt passed verbatim from instance file | `packets/P1/ddesc/prompts/author-template.md` · `author-A.md` (hash in seal log) | brief §9 |
| **Author B** (D-DESC) | OpenAI Codex · gpt-6-astra (codex-cli 0.163.0) | high (catalog default) | 30 min wall clock (`timeout 1800`) | shell, file write in workspace | `-s workspace-write -C packets/P1/ddesc/drafts/B` (reads OS-wide except mode-000 paths; writes workspace only); no network (sandbox default) | `codex exec -m gpt-6-astra -c model_reasoning_effort=high -s workspace-write -C <B dir> --skip-git-repo-check --json -o <logs>/author-B-last-message.txt - < author-B.md` | template · `author-B.md` | brief §9 |
| **Reviewer of A's draft** (D-DESC Step 3) | OpenAI Codex · gpt-6-astra | high | 20 min | shell, workspace write | `-s workspace-write -C packets/P1/ddesc/reviews-wip/on-A` | as Author B, with review instance | `review-template.md` · instance hash | brief + both published proposals (neutral labels) |
| **Reviewer of B's draft** (D-DESC Step 3) | Claude · claude-opus-5-5, **fresh process** (not Author A's context; §11.3) | medium | 20 min | Read, Write, Bash | writes `packets/P1/ddesc/reviews-wip/on-B/` | Agent tool, `model=opus` | `review-template.md` · instance hash | brief + both published proposals |
| **Adjudicator** (D-DESC Step 4) | Third family · `agy --model gemini-4-argon-high` | high | 20 min per pass (`--print-timeout 1200s`) | none needed (all inputs inline in prompt); tool log via `--log-file` | cwd = empty scratch dir `logs/p1/ddesc/adj-scratch/`; label map mode 000 during passes | `agy --model gemini-4-argon-high --effort high --log-file <log> -p="<prompt>"`, two fresh processes, presentation order X→Y then Y→X | `adjudicator-template.md` · two instance hashes | brief, both proposals, both reviews (neutral labels, inline) |
| **Spike runner** (D-DESC Step 5) | Claude · claude-sonnet-5-5 | medium (inherited) | 30 min | Read, Write, Bash | writes `spikes/D-DESC/` only | Agent tool, `model=sonnet` | `spikes/D-DESC/PLAN.md` (hashed) | PLAN.md + recommended proposal (published) only; **not** the adjudication reasoning |
| **P1 fixes author** (FX-1..FX-4 + adoption of the D-DESC decision into `code/`) | Claude · claude-sonnet-5-5 | medium | 40 min | Read, Write, Edit, Bash | writes `code/`, `configs/`, `notebooks/`, `docs/COLAB_RUNBOOK.md` only | Agent tool, `model=sonnet` | `packets/P1/fixes/prompt-fx.md` (hash in seal log) | EVAL_REVIEW, SCHEME_PLAN, decision.md, code tree |
| **P1 fixes reviewer** (objections only) | OpenAI Codex · gpt-6-astra | high | 20 min | shell (read-only) | `-s read-only`; deliverable = last message, deposited mechanically | `codex exec … -s read-only -o <file>` | `packets/P1/fixes/prompt-fx-review.md` | diff + EVAL_REVIEW §6.3 + SCHEME_PLAN P1 |
| **CPU smoke runner** (P1) | Orchestrator shell (deterministic script, no model judgment) | — | — | shell | `.venv` | same commands as attempt 2, new attempt log | — | — |
| **P2 runner** (B0 Colab smoke) | **owner (human), venue: Colab <GPU type>** (OVERLAY-001 rule 1) | — | — | — | Colab | runbook + `spikes/B0-smoke/PLAN.md` | — | sealed PLAN, tarball, notebook/runbook only |

## Parity (A.5 rule 2) and declared handicaps (rule 3)

- Effort rule for competing authors: **each catalog entry's documented default effort** (opus medium, astra high). Labels are vendor-specific and not commensurable.
- Same wall-clock cap (30 min), same readable context (brief §9), same deliverable affordance (each writes `proposal.md` into its own directory).
- **Declared asymmetries (before Step 2):** (1) Author A runs as a Claude Code subagent whose harness exposes web tools; Author B's codex sandbox has no network. Brief §9 says "No network"; Author A's tool log is audited for any web call, and a hit is reported under Confounds. (2) Author A cannot be OS-sandboxed for reads (same unix user, no read-allowlist); Author B can read OS-wide too. Isolation therefore rests on sequencing + mode-000 + audit (below), not on a read-allowlist. (3) Author B drafts after Author A (sequencing), so B's wall clock starts later; no competitor output is visible to either.

## Isolation procedure (method §11; enforced, then audited)

1. Brief + roster + prompt instances hashed into `logs/seal.log` before any author starts.
2. Author A drafts first. No Author-B output exists anywhere during A's drafting.
3. On A's completion: `sha256` + UTC of `drafts/A/proposal.md` appended to `logs/seal.log`; `chmod 000` on `drafts/A/` and on Author A's subagent transcript directory. The Orchestrator does not read A's draft before publish.
4. Author B drafts. On completion: seal, `chmod 000 drafts/B/`.
5. Breach audit (§11.6): grep Author B's codex `--json` event log for `drafts/A`, `subagents`, `.claude/projects`; grep Author A's transcript for `drafts/B` and web-tool calls. Zero hits required. Results appended to `logs/seal.log`.
6. Publish-after-all: identity-scrub check (mechanical regex, logged), neutral labels by rule *"label X = the sealed draft whose sha256 hex sorts lower; Y = the other"*, copies to `packets/P1/ddesc/proposals/{X,Y}.md`. Label map in `packets/P1/ddesc/label-map.md`, mode 000 during adjudication.
7. Reviews follow the same seal-then-publish rule (codex review first, then Claude review; the first review dir is mode 000 while the second is written).
