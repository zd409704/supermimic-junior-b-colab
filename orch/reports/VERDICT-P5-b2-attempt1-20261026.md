# P5 B2 attempt 1 — machine verdict

**Stamp:** 2026-10-26 17:17 EDT
**Decision cap:** Provisional
**Venue:** xn-4090-gpu2 (GPU0, CUDA_VISIBLE_DEVICES=0)
**Tool:** `spikes/B2/verdict/verdict_b2.py` (VERDICT-TOOL-B2) v1.0 sha256 `cd2ac741d2ffad7353c7cf62ca5f325a5402ec4d7e6a6c6f5887ecff511c994c`. It reuses `verdict_b0.py` `9caa744a…`.
**PLAN:** `spikes/B2/PLAN.md` sha256 `5d1f26f776a3ea56c2becd3ec2fa2cf8e88bd62c43a20f79415a96e82a3da11d` (unchanged)
**Method:** `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0` + OVERLAY-001
**Tarball CR-B2-1:** `53a898e9b635d1317bebabe884f1450e52be2980165811859445c1b9b53ce851`. The deposit's `meta/tarball_sha256.txt` shows the same value.
**Deposit:** `logs/xn4090/2026-10-26/b2-20261026-1611.tgz` sha256 `a869b8fcb9d66e20b9938b7aa2df9f0896d754e24b8a56877c22275d9058ef86`
**Seal:** `DEPOSIT xn4090` @ `2026-10-26T21:14:53Z`, remote DONE_DRIVER `2026-10-26T16:11:04Z`. The seal was verified before the deposit was opened. The .tgz was not rewritten.
**Open tree:** `logs/xn4090/2026-10-26/open-b2-20261026-1611/`. Its 548 regular files and 123 directories passed a pre-check: no absolute paths, no `..`, no links.
**P4 inputs (read-only):** results `76507d8a…` (b0_outcome NONINFERIOR); P4 deposit `1f491182…`; facts `packets/P4/UPSTREAM_FACTS.md` `0e9cc73a…`

## Machine line

```
B2_VERDICT verdict=BLOCKED outcome=null drho_u=-0.5570149528058929 g_u=0.43792569029292255 drho_t=0.9423446992931261 g_t=1.1404454055571487 t_status=ok gate_b1=Go failing_ids=[] blocked=[gpu_mismatch,U-REPRO,B2-V-2]
```

| Field | Value |
|---|---|
| `verdict` | **BLOCKED** |
| `decision_row` | 1 |
| `b2_outcome` | null |
| `b2_gain` | false |
| `blocked_reason` | `gpu_mismatch`, `U-REPRO`, `B2-V-2` |
| `failing_ids` | [] |
| `gate_b1` | **Go** |
| `caveat_required` | true |
| `t_status` | ok (`t_diverged_attempts` = []) |
| `spend_cap_hit` | false (driver SPENT 3.1039 GPU-h of the 6 cap) |
| `required_set` | complete (u_evals, perm_present, t_cells) |
| `env_drift.drift` | false |
| `metric_disagreement` | false |
| `rho_undefined` | [] |
| `nonfinite_values_nulled` | [] |

## Gates (harness)

| Gate | pass | Harness detail |
|---|---|---|
| U-ID | **true** | All six P4 ckpt_0001600.pt files match on size, sidecar sha256 and source→copy sha256. Root `/content/SuperMimic-Reproduced` |
| U-REPRO | **false** | Fails on b2u_b0_attention_s0/s1/s2 and b2u_b0_mlp_matched_s2 (table below). Passes on mlp_matched s0 and s1. `reference_problems` = [] |
| MS | true | problems [] |
| B2-V-1 | true | missing_cells [] |
| B2-V-2 | **false** | (a) updates_at_1600 = 624 on all 6 T runs and all 3 b2idx runs; (b) argv identical on all of them; (c) `c_gpu` false. The b2idx runs are reported only |
| B2-V-3 | true | S3_identical true |
| B2-V-4 | true | — |
| B2-L-1 | true | seeds passing: attention 3, mlp_mind 3 |
| B2-L-2 | true | — |
| PERM | true | threshold 1e-4 |

### U-REPRO per clip (|Δ norm_return| tolerance 1e-4; `steps` and `failed` must be identical; PLAN §7.1)

| U run | dance1_s1 steps P4→P5 / \|Δ\| | jumps1_s1 | run1_s2 | walk1_s1 | pass |
|---|---|---|---|---|---|
| b2u_b0_attention_s0_a1 | 577→335 / 0.0177 | 902→800 / 0.0320 | 412→697 / 0.0058 | 747→764 / 0.0012 | false |
| b2u_b0_mlp_matched_s0_a1 | 64→64 / 4e-6 | 66→66 / 2e-6 | 84→84 / 1.6e-5 | 120→120 / 5.9e-5 | true |
| b2u_b0_attention_s1_a1 | 389→2566 / 0.0027 | 127→126 / 0.0019 | 2089→1626 / 0.0385 | 695→717 / 0.0060 | false |
| b2u_b0_mlp_matched_s1_a1 | 71→71 / 0 | 59→59 / 0 | 61→61 / 0 | 103→103 / 0 | true |
| b2u_b0_attention_s2_a1 | 121→114 / 0.0030 | 174→181 / 0.0183 | 204→186 / 0.0428 | 272→203 / 0.0416 | false |
| b2u_b0_mlp_matched_s2_a1 | 88→88 / 0 | 64→64 / 0 | 82→82 / 0 | 122→110 / 0.0091 | false |

`failed` was true on both sides for every clip.

### gpu_mismatch / B2-V-2(c) (harness text)

```
gpu_mismatch: GPU names ['NVIDIA GeForce RTX 4090 + NVIDIA GeForce RTX 4090 + … (8×)'] (need one model, NVIDIA GeForce RTX 4090)
```

## U / T outcomes (computed; verdict BLOCKED, so `b2_outcome` = null)

Primary f = 0.20; mask seeds 7100/7101/7102; T = 500; floors: g_u 0.17, g_t 0.10, r 0.0393.

| Condition | ρ̄_H attention | ρ̄_H comparator | Δρ (SE) | g | Δabs (SE) | r_step Δ (SE) |
|---|---|---|---|---|---|---|
| U (P4 ckpts, f0.20) | 0.3674 | mlp_matched 0.9244 | **−0.5570** (0.2190) | 0.4379 | 0.0295 (0.0460) | −0.0357 (0.0773) |
| U (f0.10) | 0.5940 | mlp_matched 0.9022 | −0.3082 (0.1281) | — | 0.1009 (0.0665) | 0.0530 (0.0577) |
| T (mask-trained, f0.20) | 2.1005 | mlp_mind 1.1581 | **+0.9423** (0.5702) | 1.1404 | 0.2416 (0.0509) | 0.0302 (0.0949) |
| T (f0.10) | 1.4907 | mlp_mind 1.0446 | +0.4461 (0.1537) | — | 0.1907 (0.0799) | −0.0342 (0.0250) |

`u_gain`, `u_deficit`, `t_gap_kept`, `t_deficit`, `shadow_outcome_rstep` and `shadow_outcome_abs` are all null.

**Ablation (b2idx, reported only):** ablation_status complete, 3/3 runs. keying_mask0 −0.0123 (SE 0.0811) is labelled `no_detectable_difference`. keying_rho +0.2979 (SE 0.0954) is labelled `keying_helps`. The comparator is the P5 re-eval of the P4 attention checkpoints.

**Legacy P4 M-10 (mask_pairing = unverified_global_rng; reported only):** Δρ_H@0.20 = −0.4587 (2SE 0.1718).

## Inventory (deposit; not adjudicated)

- **Arms / runs:** T = b2mt_attention_s0..s2 and b2mt_mlp_mind_s0..s2. Ablation = b2idx_attention_s0..s2. U eval-only = b2u_b0_{attention,mlp_matched}_s0..s2. Every training attempt is `_a1`. The driver classed each as `completed` (diverged=false, exit=130 from the harness-stop SIGINT).
- **meta/:** 9 `attempt_*`, 9 `harness_stop_*`, 9 `gpumem_*`, 15 `perm_*.json`, `driver.log`, `driver_state.txt` (PART 1), `env_drift.txt`, `nvidia-smi.txt` (8 GPUs listed), `p4_ckpt_identity.txt`, `ckpt_dirs_ls.txt`, `cpu_test_*`, `pip-freeze.txt`, `session.txt`, `tarball_sha256.txt`, `torch_cuda.txt`.
- **Maskstreams:** 132 `maskstream_*.npz` files (each with a `.json`) under `logs/eval/`; 42 `eval.log`.
- **perm logs:** 15 under `logs/perm/`. The driver log shows report arms with high rel_err and pass=false, e.g. b2idx about 7.8–8.6. The harness PERM gate covers the gate set only and passes.
- **deviations.md:** reuse of the upstream clone at pin d9be385b; HF_ENDPOINT mirror; 9× harness stop (B0 PLAN §4.3, SIGINT).
- **BLOCKED.md:** none in the deposit.

## Disclosures (facts only; prose does not override the harness)

1. The verdict is BLOCKED (decision row 1). Under PLAN §7.3, the escalation for BLOCKED goes to the human lead. For a U-REPRO failure with U-ID true, the PLAN lists options (iv) accept, disclosing the per-clip differences and scoring U from the P5 evals, and (v) treat it as an eval-path defect and file a CR. Either one is a Class-2 decision for the Manager or human lead. The Orchestrator has not chosen.
2. `gpu_mismatch` / B2-V-2(c): `meta/nvidia-smi.txt` is the full host table: 8 × `NVIDIA GeForce RTX 4090`, all one model. The job pinned `CUDA_VISIBLE_DEVICES=0` (GPU UUID `GPU-fb0522c7…`). The harness joined the 8 names with " + " and string-compared the result with the single expected name. The P4 `meta/nvidia-smi.txt` also lists 8 × RTX 4090, and the P4 results record the same joined `gpu_name`; the B0 harness did not block on it. This is reported for the Manager. The harness result stands.
3. U-REPRO: the mismatches are concentrated in the attention checkpoints (3/3), plus one clip in mlp_matched s2. U-ID (checkpoint identity) passed for all six.
4. Report-arm PERM rel_err values in the driver log are high (pass=false). They are not part of the PERM gate.
5. No GPU, Colab, training, or relaunch was done for this packet. The sealed PLAN, the tarball and P4 scoring were not touched.

## Artifacts

| Artifact | sha256 |
|---|---|
| `orch/reports/VERDICT-P5-b2-attempt1-results.json` | `c184bb889d0f101eb24eed66a76b278807ebb5101011a64c47118a1a2df5b29a` |
| `orch/reports/VERDICT-P5-b2-attempt1.stdout` | `b7ffee4060c457decafed983d791bb269789ca06e1a18e407efb5dc69f818aa0` |
| `orch/reports/VERDICT-P5-b2-attempt1.runs.log` | `c8e950b1c47d0b7021addd57bbb4b90bdf0c2e3de87e914c637db78b4c3f6137` |

Harness work dir: `/tmp/verdict-b2-p5-attempt1-work` (scratch, outside the program root, as ordered).
