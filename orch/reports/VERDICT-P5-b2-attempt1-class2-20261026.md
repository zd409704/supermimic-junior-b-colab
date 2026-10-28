# VERDICT P5 B2 attempt 1: Class-2 amended score (Provisional)

- **Stamp:** 2026-10-26 17:20 EDT (2026-10-26T21:20Z)
- **Status:** Provisional. Home-humanoid / plant-class scope only. The reduced-scale B2 spike (512 envs, H = 16) is not a robustness claim.
- **Method:** v1.1 pin `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0` + OVERLAY-001. PLAN `spikes/B2/PLAN.md` `5d1f26f776a3ea56c2becd3ec2fa2cf8e88bd62c43a20f79415a96e82a3da11d` (unchanged).
- **Authority:** owner/Manager Class-2 decision `orch/owner-decisions/20261026-1719-EDT-p5-b2-class2-iv-gpu-waive.md`, sha256 `9985fc8fcd3a391b9577895a3bedf0c3643970b6ec701b7d96c4082ed0a3ef86`, sealed 2026-10-26T21:20:12Z before this amendment.
- **No GPU, no re-eval, no retrain.** Every number below comes from the sealed machine results `orch/reports/VERDICT-P5-b2-attempt1-results.json` (`c184bb889d0f101eb24eed66a76b278807ebb5101011a64c47118a1a2df5b29a`), via `packets/P5/class2_amend_b2.py` (`172f5630b21c85cad61e4b68ef0ed1749b9a81f3b872d99f6b434eb63b7d8da5`, run with `python3 -I`). The script checks both input sha256s and refuses to run if any row-1 reason other than the waived ones is present, if U-ID, MS, B2-V-1/3/4 or PERM is false, if B2-V-2 (a) or (b) fails, or if row 3 would match.
- **Amended results:** `orch/reports/VERDICT-P5-b2-attempt1-class2-results.json`. Its sha256 is in `logs/seal.log` (event `VERDICT-P5-CLASS2`).

## 1. Machine verdict (unchanged, quoted for audit)

```
B2_VERDICT verdict=BLOCKED outcome=null drho_u=-0.5570149528058929 g_u=0.43792569029292255 drho_t=0.9423446992931261 g_t=1.1404454055571487 t_status=ok gate_b1=Go failing_ids=[] blocked=[gpu_mismatch,U-REPRO,B2-V-2]
```

The machine results file and the original report (`79fda4e6…`) are not modified. This note is an addendum. It does not replace them.

## 2. Class-2 decisions applied

| Row-1 reason | Decision | Basis |
|---|---|---|
| **U-REPRO** (false; U-ID true) | **Option (iv):** accept with per-clip differences disclosed (§4). Score U from the P5 re-evals. Option (v) is not chosen | PLAN §7.3 last bullet; decision item 1 |
| **gpu_mismatch** and **B2-V-2(c)** | **Waived** as a harness join defect (§5). B2-V-2 (a) updates = 624 and (b) argv identical pass on all 6 scored `b2mt` runs (and on the 3 reported `b2idx` runs) | Decision item 2 |

With both waivers, no row-1 condition remains. Row 2: PERM passes. Row 3: `t_status = ok`, and B2-L-1 and B2-L-2 both pass. The required set is complete, and the spend cap was not hit. So **§7.3 row 4 applies: verdict = PASS**, and §7.2 is computed.

## 3. Amended outcome (§7.2, f = 0.20 primary)

```
B2_VERDICT_CLASS2 verdict=PASS outcome=NO_GAIN drho_u=-0.5570149528058929 g_u=0.43792569029292255 drho_t=0.9423446992931261 g_t=1.1404454055571487 t_status=ok u_gain=false u_deficit=true t_gap_kept=false t_deficit=false b2_gain=false gate_b1=Go decision_row=4 machine_was=BLOCKED waivers=[U-REPRO:iv,gpu_mismatch]
```

| Quantity | Value | Rule | Result |
|---|---|---|---|
| Δρ_U(0.20) | −0.5570 (attention 0.3674, mlp_matched 0.9244; SE 0.2190) | u_gain: ≥ g_U = 0.4379 | **false** |
| | | u_deficit: ≤ −g_U | **true** |
| Δρ_T(0.20) | +0.9423 (attention_mtrain 2.1005, mlp_mind_mtrain 1.1581; SE 0.5702) | t_gap_kept: t_status ok and ≥ g_T = 1.1404 | **false** |
| | | t_deficit: ≤ −g_T | false |
| `b2_outcome` | **NO_GAIN** | not u_gain | |
| `b2_gain` | **false** | outcome = ROBUSTNESS_GAIN | |
| `gate_b1` | **Go** (as computed; B0 NONINFERIOR, `76507d8a…`) | PLAN §8 | unchanged |

- **Shadow outcomes (non-binding).** ρ_step: U Δ = −0.0357 vs margin 0.17 → NO_GAIN. ΔR (absolute): U Δ = +0.0295 vs margin 0.17 → NO_GAIN. `metric_disagreement = false`. The machine run left these `null` because it stopped at row 1. The script derived them with the same §7.2 table and the margins already in the results file.
- **PASS means B2 was validly executed under the PLAN after the Class-2 waivers. It is not a claim that attention is more robust.** NO_GAIN with u_deficit is a PASS-verdict outcome (§7.3).
- **Mandatory caveat (PLAN §8; `caveat_required = true`).** Any later write-up citing the B0 + B2 gate states: *under untrained token masking (f = 0.20), the attention decoder kept a smaller fraction of its unmasked return than mlp_matched: Δρ_H(0.2) = −0.557 (g_U = 0.438, u_deficit true). Under equal masked training, Δρ_T(0.2) = +0.942 did not reach g_T = 1.140. b2_outcome = NO_GAIN (Provisional, after the Class-2 waivers U-REPRO:iv and gpu_mismatch).*
- Ablation (report-only, never moves the verdict; from machine results): keying_mask0 = −0.012 (SE 0.081) `no_detectable_difference`; keying_rho = +0.298 (SE 0.095) `keying_helps`.

## 4. U-REPRO disclosure (option iv): per-clip, copied from machine `gates.U-REPRO`

U-ID passed: all 6 P4 checkpoints are byte-identical copies (source sha256 = copy sha256, sidecars match). The tolerance is identical `steps` and `failed`, and |Δ norm_return| ≤ 1e-4. Every clip failed in both P4 and P5 (`failed` true/true). 13 of 24 clips fail the tolerance, in 4 of 6 runs. The largest |Δ| is 0.0428.

| Run | Clip | steps P4 | steps P5 | \|Δ norm_return\| |
|---|---|---|---|---|
| b2u_b0_attention_s0_a1 | dance1_subject1 | 577 | 335 | 0.017653 |
| | jumps1_subject1 | 902 | 800 | 0.032028 |
| | run1_subject2 | 412 | 697 | 0.005784 |
| | walk1_subject1 | 747 | 764 | 0.001232 |
| b2u_b0_attention_s1_a1 | dance1_subject1 | 389 | 2566 | 0.002692 |
| | jumps1_subject1 | 127 | 126 | 0.001887 |
| | run1_subject2 | 2089 | 1626 | 0.038516 |
| | walk1_subject1 | 695 | 717 | 0.005954 |
| b2u_b0_attention_s2_a1 | dance1_subject1 | 121 | 114 | 0.002999 |
| | jumps1_subject1 | 174 | 181 | 0.018331 |
| | run1_subject2 | 204 | 186 | 0.042844 |
| | walk1_subject1 | 272 | 203 | 0.041576 |
| b2u_b0_mlp_matched_s2_a1 | walk1_subject1 | 122 | 110 | 0.009102 |

Passing (within tolerance): mlp_matched s0 and s1 (all 4 clips), and mlp_matched s2 (dance1, jumps1, run1). The full 24-clip list is in the amended JSON, `waivers[0].per_clip`.

**What this means for scoring.** All three attention U runs fail to reproduce P4's unmasked eval: episode lengths move by up to several hundred steps on the same checkpoint. Only one mlp_matched clip moves. U is scored from the P5 re-evals, where mask-0 and the masked conditions share one eval path, and no P4 numbers are mixed in. The disclosure is that the attention arm's mask-0 eval is not bit-reproducible across P4 → P5, which adds eval-path noise to ρ_H for attention. The sign and size of Δρ_U (−0.557, more than 2.5 SE) are large relative to the per-clip |Δ| (≤ 0.043 in normalised return). No cause is asserted here. Option (v), an eval-path CR, was not chosen, so the cause is not investigated in this packet.

## 5. gpu_mismatch / B2-V-2(c) waiver rationale

- `meta/nvidia-smi.txt` in the deposit is the full host table: 8 rows, every row `NVIDIA GeForce RTX 4090`. The job used `CUDA_VISIBLE_DEVICES=0` (job JSON `remote.cuda_visible_devices = "0"`, `gpu_uuid GPU-fb0522c7-d42b-41f1-f24b-4729e2c2174c`).
- The reused `parse_gpu_name` joins every row with `" + "`. `verdict_b2.py` then compares that string to the single literal `NVIDIA GeForce RTX 4090`. P4's tool only required the names to be equal across deposits, which is why the same table did not block P4.
- The PLAN §7.3 row-1 condition is "a non-RTX-4090 GPU or mixed GPU models". Neither holds in substance. The failure is in the string comparison, not on the hardware.
- Tool fix filed as a CR note, not applied: `orch/reports/CR-verdict-b2-gpu-name-parse.md` (`11569dcc143a6777384d8a5f09153501f48d132f6e5301d0bb4c0260e5ac9763`). The sealed VERDICT-TOOL-B2 bytes (`cd2ac741…`) are unchanged.

## 6. Confounds (added to PLAN §12)

1. **Verdict by waiver.** The PASS verdict depends on two Class-2 waivers made after the machine verdict was seen. The machine verdict stays BLOCKED on record, and this PASS is the amended verdict. The waivers come from the PLAN's own pre-listed option (iv), plus a tool-defect ruling. Neither changes a threshold or a number.
2. **U-REPRO not met.** See §4. The attention arm's unmasked eval is not reproducible at 1e-4 across packets.
3. **Decision timing.** The owner decision was signed after the outcome inputs (drho_u, drho_t) were visible in the BLOCKED line. Two things limit the effect: the option chosen was pre-listed in the sealed PLAN, and the thresholds g_U and g_T are the machine-computed values, unchanged.
4. PLAN §12 items 1–11 apply unchanged (ratio metric, floor effect, flicker mask model, reduced scale, compute ≠ param parity, and so on).

## 7. Not done / next

- No P6 start, no GPU, no relaunch, no retrain. P4 is not reopened. The drive routine stays paused.
- `gate_b1 = Go` opens P6 **for planning only** (PLAN §8), and only when the Manager orders it. **Next: await Manager.**
