# P3 red-team dispositions — round 1 (draft 1 → draft 2)

- **Red team:** `codex-astra` high, read-only.
- **Review output:** `logs/p3/redteam-attempt1-last-message.txt`.
- **Draft 1:** sha256 `def49fd11a46ab0cbd3ba479350d7c45a8fed858d91c751afcf6a2d66447a27d` (`logs/p3/PLAN-draft1-def49fd1.md`).
- **Result:** REVISE.
- **Dispositions:** made by the Orchestrator. All 17 objections were **applied**; none was rejected.

| # | Sev | Disposition | Where in draft 2 |
|---|---|---|---|
| 1 | BLOCKER | Applied. Ordered decision table. Terminal attention divergence → PASS/INFERIOR with `outcome_basis=divergence` and null statistics. `superior` requires NONINFERIOR | §6.2, §6.4 rows 1–4 |
| 2 | BLOCKER | Applied. V-2(b) allows exactly the F-2 LR flag at 0.5× default for `b0lr05` runs. Update parity is still required | §6.1 V-2 |
| 3 | MAJOR | Applied, without a proxy. F-4 records the semantics of `policy_grad_norm`. The clip clause is evaluated only on per-update data, otherwise it is "not evaluable" and only NaN/inf counts as divergence (disclosed) | §2.2 F-3/F-4, §5 M-6, §6.3, §10.10 |
| 4 | MAJOR | Applied. Closed attempt-class list. The first completed attempt is scored. Completed scientific failures are never retried. The first divergence triggers the paired retry | §3.3, §6.3 |
| 5 | MAJOR | Applied. Attempt IDs `<tag>_<arm>_s<seed>_a<N>`. The run dir is archived before reuse. Logs and memory files are named by attempt ID. Results are keyed by attempt ID | §3.2–3.3, §4.2, §8.1, §8.3 |
| 6 | MAJOR | Applied. The completion condition uses the log line, a stable checkpoint size and the sidecar. The stop is SIGINT, so the wrapper's `finally` block runs. Timeout handling is defined | §4.3 |
| 7 | MAJOR | Applied. F-1 records the cap's unit and endpoint, and the flag is used only if it counts iterations. F-5 records env-steps per iteration. The ≈624-update extrapolation is stated, and V-2 checks updates directly | §2.2, §3.1 |
| 8 | MAJOR | Applied. Train and eval are parameterised by TAG, RUN and AID. The listing covers `b0lr05_*` and archived attempts | §4.2, §4.4 |
| 9 | MAJOR | Applied. `mlp_upstream` checks moved to REF-1..4, reported only. They never move the verdict | §3, §6.1, §6.4 |
| 10 | MAJOR | Applied. The ordered table covers V-0, V-3 (descriptor), the safety cap (INFRA), tracebacks and the spend cap. There is one divergence definition (§6.3), and the "exception" wording was removed from §2.2 | §2.2, §3.3, §6.3, §6.4 |
| 11 | MAJOR | Applied. At most 2 eval executions per (attempt, checkpoint), and exec2 only on failure. All executions are kept. The first execution passing V-4 is scored | §4.4 |
| 12 | MAJOR | Applied. Exact clip names, required finite fields, one tb file per run, a duplicate-step rule, the logged-point definition, and `eval.log` as the checkpoint-identity record | §5 TB rules, §6.1 V-4, §8.1 |
| 13 | MAJOR | Applied. Per-run interpolation, then the mean over seeds. W = min over runs of hours at it 1600, so there is no extrapolation. Null rule below it 400 | §5 M-9 |
| 14 | MAJOR | Applied. The same absolute layout is required on XN-4090 (directories or symlinks). No other path substitution | §2.3 |
| 15 | MAJOR | Applied. C1–C3 removed from CR-B0-1, which is now new files only. Any instrumentation needs its own change request | §2.2 |
| 16 | MINOR | Applied. The RCA values are labelled as raw proxies, and the ×10 M-7 values are given | §6.1 |
| 17 | MINOR | Applied. Exact AULC_H formula, ρ = null on a zero denominator, and schema locations for ρ and terms | §5 M-5/M-10, §8.3 |

# Round 2 (draft 2 → draft 3)

- **Draft 2:** `c605c40f34ae10e601fe3a054cbfc8af62a90f2817d535a3e65a84af01598b78` (`logs/p3/PLAN-draft2-c605c40f.md`).
- **Review output:** `logs/p3/redteam-attempt2-last-message.txt`.
- **Result:** REVISE. 9 of the round-1 objections were RESOLVED (#2, #4, #8, #11, #13, #14, #15, #16, #17).
- **Dispositions:** all applied.

| # | Status in round 2 | Disposition | Where in draft 3 |
|---|---|---|---|
| 1 | NOT RESOLVED (BLOCKER) | Applied. "Checkable gate runs" exempt a terminally diverged attention run's missing endpoint evidence. Its argv, GPU and seam checks still apply | §6.4 |
| 3 | NOT RESOLVED | Applied. If the clip clause cannot be evaluated, P4 does not start (PS-3) until the human lead signs one of two Class-2 rulings: omit the clause, or add a logging change request | §2.2 |
| 5 | NOT RESOLVED | Applied. Every attempt's non-`.pt` run directory is copied to `logs/attempts/<AID>/`, and all of them are bundled | §3.3, §4.2, §8.1 |
| 6 | NOT RESOLVED | Applied. A signal-restoring launcher sets SIG_DFL and then execs. A CPU SIGINT/finally check (PS-5) must pass before P4 starts | §2.2 (f), §4.2 |
| 7 | NOT RESOLVED | Applied. Env-step parity must be source-backed or come from a direct counter (PS-4); otherwise a human-lead ruling is needed before start | §2.2 |
| 9 | NOT RESOLVED | Applied. OOM, SEAM and INFRA caps are scoped to gate-arm cells. For the reference cell they are reported only | §3.3, §6.4 |
| 10 | NOT RESOLVED | Applied. Row 1 now covers V-1 to V-4 on the checkable runs, and the table is stated to be exhaustive | §6.4 |
| 12 | NOT RESOLVED | Applied. V-1 requires window coverage (≥ 10 points) and the timing tags at the checkpoints. V-4 validates the required summary fields | §6.1 |
| 18 | NEW | Applied. Only the final exception line is matched, using a word-boundary regex | §3.3, §6.3 |
| 19 | NEW | Applied. One spend-cap predicate (gate set complete or not), shared by §6.4 and §9 | §6.4, §9 |
| 20 | NEW | Applied. A single classification boundary: steps ≤ 1600 and failures before completion. Anything later is `post_endpoint_anomaly` | §3.3, §6.3 |

# Round 3 (draft 3 → draft 4, sealed)

- **Draft 3:** `2a64d475ae6abb26ecbcda1ec4b56f7dd9aeee0ebffde9a669e82edd4126d677` (`logs/p3/PLAN-draft3-2a64d475.md`).
- **Review output:** `logs/p3/redteam-attempt3-last-message.txt`.
- **Result:** REVISE. Round-2 items #1, #5, #6, #7, #9, #10, #12, #18 and #19 were RESOLVED.

| # | Status in round 3 | Disposition | Where in draft 4 |
|---|---|---|---|
| 3 | NOT RESOLVED | Applied. Ruling (ii) satisfies PS-3 only once its logging is implemented, sealed and validated, so that M-6 can be computed. Omission requires an explicit ruling (i). The "no gate depends" sentence now names this exception | §2.2 |
| 20 | NOT RESOLVED | Applied. The scoring endpoint is the `it 1600 \|` log line. Everything after it, scalars and exceptions alike, is `post_endpoint_anomaly`. After the endpoint, an attempt's class follows only from the completion condition (completed or INFRA) | §3.3, §6.3 |
| 21 | NEW | Applied. A terminally diverged attempt is exempt only from endpoint-dependent checks. Integrity checks still apply: a single tb file, the log present, the divergence evidence coming from that file or log, argv, GPU and seams. If they fail, the verdict is BLOCKED | §6.4 |

Review closed after round 3. Draft 4 was not re-reviewed, and the PLAN discloses this (§10 item 8).
