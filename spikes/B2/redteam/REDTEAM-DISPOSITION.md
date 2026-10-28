# P5 PLAN red-team dispositions

Binding: `BINDING.md` (`codex-astra` / `gpt-6-astra`, high, read-only). Dispositions are by the Orchestrator, who is also the PLAN author (disclosed in PLAN §12 item 9).

## Round 1: draft 1 → draft 2

- **Draft 1:** `65cae1df4ac4eab9da4f1cd9c504b2625b46f79a612092e68c999ca56ded0f6c` (`PLAN-draft1-65cae1df.md`).
- **Prompt:** `prompt-redteam-r1.md`. Input hashes in `redteam-r1-inputs.sha256`.
- **Output:** `redteam-r1-last-message.txt` (events in `redteam-r1-events.jsonl`).
- **Result:** REVISE, with 2 BLOCKER, 5 MAJOR and 1 MINOR objections. **All 8 were applied**; none was rejected.
- **Draft 2:** `f11633a24d56b8963269303e15e0dce009efd5fcb3db2ca7dc9a1937a2a52d10`.

| # | Sev | Disposition | Where in draft 2 |
|---|---|---|---|
| 1 | MAJOR | Applied. Verified against P4 `eval.log` (`Setting seed: 0` once per condition, from the env stack). Draft 1's claim that the 0.20 stream "starts after 0.10's draws" is not established by the evidence. The finding is now that P4 mask pairing is **unverified**. The dedicated-generator procedure is kept, and the legacy label is `unverified_global_rng` | §3, §2.1, §5.5, §7.3, §9.4 |
| 2 | BLOCKER | Applied. There is now one divergence definition (B0 §6.3(a)), applied whether or not the attempt completed. Precedence over B2-V-1 is set, with the B0 §6.4 integrity-only checks for diverged runs | §4.2, §7.1 B2-V-1, §7.3 |
| 3 | MAJOR | Applied. With `t_status = diverged`, B2-L-1/L-2 are not evaluated (reported only). Row 3 requires `t_status = ok`. The text and the table agree | §7.3 |
| 4 | MAJOR | Applied. New outcome `U_GAIN_T_UNEVALUABLE`. ABSENCE_REPRESENTATION_ONLY requires `t_status = ok`. `b2_gain` stays false | §7.2, §9.4 |
| 5 | BLOCKER | Applied. A zero mask-0 R_H on a scored run makes the verdict BLOCKED (`rho_undefined`). No seed is ever omitted or imputed. Null propagation is defined for the shadow and reported statistics, and the SE is null when n < 2 | §7.3, §9.4 |
| 6 | MAJOR | Applied. `auto_mask_frac = 0.0` is set and asserted. The masked variant uses an explicit shared mask that is permuted with the tokens. The exact frozen denominator with `max(·, 1e-12)` is used | §6 |
| 7 | MAJOR | Applied. The margins are described as heuristic decision margins. The guaranteed-conservatism claim and "significantly" are removed, and the covariance limitation is disclosed | §5.4, §7.2 |
| 8 | MINOR | Applied. Added `ablation_status`, per-cell reasons, n-stated aggregates for n ≥ 2, and null labels when incomplete | §7.4, §9.4 |

## Round 2: draft 2 → draft 3

- **Prompt:** `prompt-redteam-r2.md`. **Output:** `redteam-r2-last-message.txt`.
- **Result:** REVISE. R1-1 and R1-3…R1-8 RESOLVED. **R1-2 NOT RESOLVED** (BLOCKER), plus 2 new objections (#9 MAJOR, #10 MINOR). **All applied.**
- **Draft 3:** `3d1b9b57c36e0ee7b2ae4324bd2d17b79d3116057d1c5367a2522599ab658c46`.

| # | Sev | Disposition | Where in draft 3 |
|---|---|---|---|
| R1-2 | BLOCKER | Applied. One list of the exempt checks for diverged runs (endpoint-dependent parts of B2-V-1, B2-V-2(a), B2-V-4, MS, PERM) and of the retained checks (integrity, argv, GPU, seams and sidecar). The required set is aligned with the divergence flag | §4.2, §7.3 |
| 9 | MAJOR | Applied. When `t_status = diverged`, the T aggregates and `g_t` are null (`drho_t=null g_t=null`). Per-run values are kept. A report-only `t_partial` block is added | §7.3 |
| 10 | MINOR | Applied. For an ablation run with zero R_H(0): its ρ is null, `keying_rho` and its label are null, and the verdict is unaffected | §7.4 |

## Round 3: draft 3 → sealed text

- **Prompt:** `prompt-redteam-r3.md`. **Output:** `redteam-r3-last-message.txt`.
- **Result:** R1-2, #9 and #10 RESOLVED. No new BLOCKER or MAJOR objections. **REDTEAM-RESULT: SEAL-OK.**
- The sealed PLAN differs from draft 3 only in §12 item 9 (the review record sentence).
