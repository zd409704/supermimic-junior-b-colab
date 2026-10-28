# Decision note — P5 r1 #8 MINOR and Manager START (2026-10-26)

**Stamp:** 2026-10-26 09:02 EDT
**Decision cap:** Provisional
**Authority:** Claude Manager (relay executor on program supermimic-junior-b-colab)
**Binding PLAN:** `spikes/B2/PLAN.md` sha256 `5d1f26f776a3ea56c2becd3ec2fa2cf8e88bd62c43a20f79415a96e82a3da11d`
**CR-B2-1 tarball:** `packets/P5/junior_b_colab-CR-B2-1.tgz` sha256 `53a898e9b635d1317bebabe884f1450e52be2980165811859445c1b9b53ce851`

## Ask 1 / review r1 #8 (MINOR) — PLAN §9.1 vs PS-B2-3

**Ruling: option (i) — accept the sealed prep reading.**

- Authoritative job JSON remains a relay artifact at `orch/jobs/p5-b2-attempt1.json` (sealed on the research box).
- Upload list stays exactly PS-B2-3: CR-B2-1 tarball + `orch/jobs/p5-b2-attempt1/run.sh` (with sha256). Job JSON is **not** added to the upload list; no PLAN amendment.
- Bundle-side coverage: `run.sh` tees a runner-stdout snapshot into the archive and packs `job.json` / `p5-b2-attempt1.json` only if the relay places one in the remote workdir (optional). Driver extras and deviations.md already handle missing extras (IMPLEMENTATION_NOTES item 17).
- Authoritative relay job JSON and relay stdout are deposited and sealed **beside** the archive as in P4 (`RELAY-LOG`), matching job `deposit.also_deposit`.

Options (ii) and (iii) are not required for START.

## Ask 2 — P4 checkpoints

Standing reminder (no SSH from the box): the six P4 `ckpt_0001600.pt` must remain on xn-4090-gpu2 under the PLAN §2.2 roots until this job finishes. Relay must not clean those trees. Driver step 0 BLOCKs with `p4_ckpts_unavailable` if missing.

## PS-B2-3 / PS-B2-4

- **PS-B2-3:** flip `p5-b2-attempt1` DRAFT → READY (same upload list; `env.HF_ENDPOINT=https://hf-mirror.com`; mutex `gpu0`). Seal new job JSON sha after the flip.
- **PS-B2-4 (Manager START):** this note cites PLAN `5d1f26f776a3ea56…` and CR-B2-1 tarball `53a898e9b635d131…`.

**Do not set RUNNING from the research box.** Mac mini relay picks up READY, rsyncs uploads, starts remote command, and deposits.

Sealed `packets/P5/PRESTART.md` (0444, sha `97b8942ee87d…`) is left unchanged as the prep-time gate record; this note plus STATUS and the READY job JSON supersede the open PS-B2-3/4 rows for operations.

