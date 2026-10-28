# Owner decision — P6 B1-RT Class-2 option C (waive RT-4)

- Decision-id: 20261026-1931-EDT
- Program: /srv/claude/research/supermimic-junior-b-colab/
- Answers: orch/reports/ASK-P6-RT4-class2-20261026.md
- Amends: spikes/B1-RT/PLAN.md (b7365b4f…); prior P6 START 3a0254de… and xn-4090 1408aeef…
- Authority: Manager under standing owner rule (research drive without re-ask) + xn-4090 free-use 1855; Class-2 on defective RT-4 acceptance

## Choice: C (recommended)

1. **Waive RT-4** for P6 B1-RT. Keep RT-a references. RT-6 / RT-7 / RT-8 stay binding.
2. Use the **first clip of each slot** (P4 clips). Job `p6-b1-rt`: set `slot_rule=first`, re-seal, set state **READY**.
3. Orchestrator writes and seals `spikes/B1-RT/AMENDMENT-C2-rt4.json` (waive=[RT-4], slot_rule=first, this decision sha) before READY.
4. After RT deposit is SCORED PASS on RT-6/7/8, set `p6-b1-arms` READY under sealed `spikes/B1/PLAN.md` and proceed on xn-4090 without another Manager START.
5. Disclose in every B1 write-up: RT-4 and source-baseline numbers, plus claim-scope line that references were produced by route RT-a which failed retarget QA (skate measure not attainable on the 29-DoF source itself).

## Rejected for now

- B (RT-b keypoint IK + corrected skate/penetration) may run later as its own packet; not blocking P6.
- A alone does not unblock (source-relative still fails).

## Unchanged

- No reopen of P4/P5 scoring
- D-001 Provisional; P5 NO_GAIN / u_deficit caveat carried
- Venue xn-4090-gpu2; JumpServer / Mac mini job state machine

