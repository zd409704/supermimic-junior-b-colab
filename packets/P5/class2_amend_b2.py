#!/usr/bin/env python3
"""P5 B2 Class-2 amendment: re-emit PLAN §7.3 row-4 outcome from the sealed machine results.

Reads (read-only) orch/reports/VERDICT-P5-b2-attempt1-results.json (c184bb88...) and the sealed
owner decision (9985fc8f...). Writes orch/reports/VERDICT-P5-b2-attempt1-class2-results.json.
No GPU, no re-eval: every number comes from the machine results file. Provisional.
Usage: python3 -I packets/P5/class2_amend_b2.py <program_root>
"""
import hashlib, json, os, sys

ROOT = sys.argv[1]
MACHINE = "orch/reports/VERDICT-P5-b2-attempt1-results.json"
MACHINE_SHA = "c184bb889d0f101eb24eed66a76b278807ebb5101011a64c47118a1a2df5b29a"
DECISION = "orch/owner-decisions/20261026-1719-EDT-p5-b2-class2-iv-gpu-waive.md"
DECISION_SHA = "9985fc8fcd3a391b9577895a3bedf0c3643970b6ec701b7d96c4082ed0a3ef86"
PLAN_SHA = "5d1f26f776a3ea56c2becd3ec2fa2cf8e88bd62c43a20f79415a96e82a3da11d"
OUT = "orch/reports/VERDICT-P5-b2-attempt1-class2-results.json"
WAIVED = {"U-REPRO", "gpu_mismatch", "B2-V-2"}


def sha(p):
    with open(os.path.join(ROOT, p), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


for p, want in ((MACHINE, MACHINE_SHA), (DECISION, DECISION_SHA)):
    got = sha(p)
    if got != want:
        sys.exit("sha mismatch %s: %s != %s" % (p, got, want))

with open(os.path.join(ROOT, MACHINE)) as f:
    m = json.load(f)

g = m["gates"]
# Row-1 must contain only the waived reasons; rows 2/3 must not match.
extra = [r for r in m["blocked_reason"] if r not in WAIVED]
if m["verdict"] != "BLOCKED" or extra:
    sys.exit("unexpected machine state: verdict=%s unwaived=%s" % (m["verdict"], extra))
for gid in ("U-ID", "MS", "B2-V-1", "B2-V-3", "B2-V-4", "PERM"):
    if g[gid]["pass"] is not True:
        sys.exit("gate %s not pass; row-1/2 not waivable" % gid)
v2 = g["B2-V-2"]
for aid, ev in v2["per_attempt"].items():
    if not (ev["a_updates_624"] is True and ev["b_argv_identical"] is True):
        sys.exit("B2-V-2 (a)/(b) fail on %s; not covered by waiver" % aid)
if not g["U-ID"]["pass"]:
    sys.exit("U-ID false; option (iv) needs U-ID true")
if m["t_status"] == "ok" and not (g["B2-L-1"]["pass"] and g["B2-L-2"]["pass"]):
    sys.exit("row 3 would match")
if not m["required_set"]["complete"] or m["spend_cap_hit"]:
    sys.exit("required set incomplete / spend cap")

# §7.2 on f = 0.20 (primary)
drho_u, g_u = m["drho_u"], m["g_u"]
drho_t, g_t = m["drho_t"], m["g_t"]
t_ok = m["t_status"] == "ok"
u_gain = drho_u >= g_u
u_deficit = drho_u <= -g_u
t_gap_kept = t_ok and drho_t >= g_t
t_deficit = t_ok and drho_t <= -g_t


def outcome(ug, tok, tkept):
    if not ug:
        return "NO_GAIN"
    if not tok:
        return "U_GAIN_T_UNEVALUABLE"
    return "ROBUSTNESS_GAIN" if tkept else "ABSENCE_REPRESENTATION_ONLY"


b2_outcome = outcome(u_gain, t_ok, t_gap_kept)
b2_gain = b2_outcome == "ROBUSTNESS_GAIN"

# Shadow outcomes (§7.2, non-binding), same table on rstep_delta / delta_abs with their own margins
u20, t20 = m["u"]["f0.20"], m["t"]["f0.20"]
sh_rstep = outcome(u20["rstep_delta"] >= u20["rstep_margin"], t_ok,
                   t_ok and t20["rstep_delta"] >= t20["rstep_margin"])
sh_abs = outcome(u20["delta_abs"] >= u20["abs_margin"], t_ok,
                 t_ok and t20["delta_abs"] >= t20["abs_margin"])

# U-REPRO per-clip disclosure, copied from the machine gate evidence
urepro = []
for aid, run in g["U-REPRO"]["per_run"].items():
    for c in run["clips"]:
        urepro.append({"run": aid, "run_pass": run["pass"], "clip": c["name"],
                       "steps_p4": c["steps_p4"], "steps_p5": c["steps_p5"],
                       "steps_equal": c["steps_p4"] == c["steps_p5"],
                       "failed_p4": c["failed_p4"], "failed_p5": c["failed_p5"],
                       "abs_d_norm_return": c["abs_d_norm_return"], "clip_pass": c["pass"]})
urepro_fail_runs = [aid for aid, r in g["U-REPRO"]["per_run"].items() if not r["pass"]]
fails = [r for r in urepro if not r["clip_pass"]]

machine_line = m["verdict_line"]
line = ("B2_VERDICT_CLASS2 verdict=PASS outcome=%s drho_u=%r g_u=%r drho_t=%r g_t=%r t_status=%s "
        "u_gain=%s u_deficit=%s t_gap_kept=%s t_deficit=%s b2_gain=%s gate_b1=%s decision_row=4 "
        "machine_was=BLOCKED waivers=[U-REPRO:iv,gpu_mismatch]"
        % (b2_outcome, drho_u, g_u, drho_t, g_t, m["t_status"], str(u_gain).lower(),
           str(u_deficit).lower(), str(t_gap_kept).lower(), str(t_deficit).lower(),
           str(b2_gain).lower(), m["gate_b1"]))

out = {
    "amendment": "P5 B2 attempt1 Class-2 amendment (PLAN §7.3 options; owner decision 20261026-1719-EDT)",
    "status": "Provisional",
    "generator": {"path": "packets/P5/class2_amend_b2.py", "sha256": sha("packets/P5/class2_amend_b2.py")},
    "plan_sha256": PLAN_SHA,
    "method_sha256": m["method_sha256"],
    "class2_decision_path": DECISION,
    "class2_decision_sha256": DECISION_SHA,
    "machine_results_path": MACHINE,
    "machine_results_sha256": MACHINE_SHA,
    "machine_blocked_line": machine_line,
    "machine_verdict": m["verdict"],
    "machine_decision_row": m["decision_row"],
    "machine_blocked_reason": m["blocked_reason"],
    "machine_blocked_detail": m["blocked_detail"],
    "waivers": [
        {"id": "U-REPRO", "option": "iv",
         "rule": "PLAN §7.3: U-REPRO false with U-ID true -> (iv) accept with per-clip differences disclosed, score U from the P5 evals",
         "u_id_pass": g["U-ID"]["pass"],
         "u_scored_from": "P5 re-evals (scored_set.U); legacy P4 M-10 stays reported-only (§5.5)",
         "failing_runs": urepro_fail_runs,
         "n_clips_total": len(urepro), "n_clips_fail": len(fails),
         "max_abs_d_norm_return": max(r["abs_d_norm_return"] for r in urepro),
         "per_clip": urepro},
        {"id": "gpu_mismatch", "covers": ["gpu_mismatch", "B2-V-2(c)"],
         "rule": "waived as harness join defect (owner decision item 2)",
         "observed_names": v2["c_gpu"]["names"], "expected": v2["c_gpu"]["expected"],
         "rationale": "meta/nvidia-smi.txt is the full host table: 8 rows, every row 'NVIDIA GeForce RTX 4090' (one model). "
                      "The job ran with CUDA_VISIBLE_DEVICES=0 (job JSON remote.cuda_visible_devices, gpu_uuid "
                      "GPU-fb0522c7-d42b-41f1-f24b-4729e2c2174c). parse_gpu_name (verdict_b0.py, reused) joins all rows with ' + ' "
                      "and verdict_b2.py compares the joined string to the single expected model name. No non-4090 and no mixed "
                      "model is present, so the PLAN §7.3 row-1 condition 'non-RTX-4090 GPU or mixed GPU models' is not met in substance. "
                      "Tool fix filed as CR note orch/reports/CR-verdict-b2-gpu-name-parse.md; sealed tool bytes unchanged.",
         "b2_v2_a_updates_624_all": all(ev["a_updates_624"] for ev in v2["per_attempt"].values()),
         "b2_v2_b_argv_identical_all": all(ev["b_argv_identical"] for ev in v2["per_attempt"].values())},
    ],
    "row_checks_after_waiver": {
        "row1_remaining": [], "row2_perm_pass": g["PERM"]["pass"],
        "row3_l1_pass": g["B2-L-1"]["pass"], "row3_l2_pass": g["B2-L-2"]["pass"],
        "gates_pass": {k: g[k]["pass"] for k in g},
        "required_set": m["required_set"], "spend_cap_hit": m["spend_cap_hit"],
    },
    "verdict": "PASS",
    "verdict_meaning": "PASS = B2 validly executed per PLAN (after Class-2 waivers). Not a claim that attention is more robust (§7.3).",
    "decision_row": 4,
    "failing_ids": [],
    "primary_f": m["primary_f"],
    "drho_u": drho_u, "g_u": g_u, "drho_t": drho_t, "g_t": g_t,
    "t_status": m["t_status"],
    "u_gain": u_gain, "u_deficit": u_deficit, "t_gap_kept": t_gap_kept, "t_deficit": t_deficit,
    "b2_outcome": b2_outcome,
    "b2_gain": b2_gain,
    "shadow_outcome_rstep": sh_rstep,
    "shadow_outcome_abs": sh_abs,
    "metric_disagreement": sh_rstep != b2_outcome or sh_abs != b2_outcome,
    "shadow_inputs": {"u_rstep_delta": u20["rstep_delta"], "u_rstep_margin": u20["rstep_margin"],
                      "t_rstep_delta": t20["rstep_delta"], "t_rstep_margin": t20["rstep_margin"],
                      "u_delta_abs": u20["delta_abs"], "u_abs_margin": u20["abs_margin"],
                      "t_delta_abs": t20["delta_abs"], "t_abs_margin": t20["abs_margin"]},
    "b0_outcome_input": m["b0_outcome_input"],
    "gate_b1": m["gate_b1"],
    "caveat_required": (b2_outcome != "ROBUSTNESS_GAIN") or u_deficit,
    "caveat_sentence": ("Under untrained token masking (f = 0.20) the attention decoder retained a smaller fraction of its "
                        "unmasked return than mlp_matched, Δρ_H(0.2) = %.4f (margin g_U = %.4f; u_deficit = %s); under equal "
                        "masked training Δρ_T(0.2) = %.4f did not reach g_T = %.4f; b2_outcome = %s (Provisional, after Class-2 "
                        "waivers U-REPRO:iv and gpu_mismatch)." % (drho_u, g_u, str(u_deficit).lower(), drho_t, g_t, b2_outcome)),
    "u_f020": u20, "t_f020": t20,
    "ablation_idx": m["ablation_idx"],
    "verdict_line": line,
}

with open(os.path.join(ROOT, OUT), "w") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
    f.write("\n")
print(line)
