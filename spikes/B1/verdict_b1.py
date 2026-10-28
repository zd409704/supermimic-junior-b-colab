#!/usr/bin/env python3
"""B1 machine verdict (spikes/B1/PLAN.md §4-§8). Stdlib only; run with `python -I`.

v1.1: the v1.0 logic is unchanged and is the default. `--amendment-m1 <file>` adds the post-hoc re-score (M1) of
spikes/B1/AMENDMENT-M1-eval-metric.md (sha256 pinned below): R_full, dance1 window, collapse counts, difference
criterion and sensitivities. M1 mode writes results-M1.json / runs-M1.log and prints one `B1_M1_VERDICT ...` line;
it never writes results.json / runs.log.

Reads one or more sealed `b1arms-*.tgz` deposits (job launch 1, and launch 2 if any), extracts them safely, picks the
scored attempt of every run from evidence (PLAN §7; completion = spikes/B0/PLAN.md §4.3), reads R_k at the 10 eval
points (§5), computes AULC / R25 / R100, the validity checks B1-V-1..B1-V-5 (§6) and the §5 outcome. Writes
results.json, appends one block to runs.log and prints exactly one `B1_VERDICT ...` line on stdout.
Bundle layout: packets/P6/BUNDLE_CONTRACT-b1arms.md. Literal readings: spikes/B1/IMPLEMENTATION_NOTES.md.

    python3 -I spikes/B1/verdict_b1.py --deposit logs/xn4090/<date>/b1arms-<stamp>.tgz [--deposit ...] \
        --tarball-sha <arms tarball sha256> [--seal-log logs/seal.log] [--out spikes/B1/results.json] \
        [--runs-log spikes/B1/runs.log] [--amendment-m1 spikes/B1/AMENDMENT-M1-eval-metric.md]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import tempfile

TOOL_VERSION = "1.1"
PLAN_SHA256 = "1088752ba26a8798d721aa93d6e10d1b7bdb7fb924d9d72879acc78d8c2304c8"
B0_VERDICT_SHA256 = "9caa744a65ef5206fd46f532c4d13529b7773d076ee725ee4cb98ec192774a3b"  # sealed P4 tool (helpers only)
HERE = os.path.dirname(os.path.abspath(__file__))
PROGRAM_ROOT = os.path.dirname(os.path.dirname(HERE))
B0_VERDICT = os.path.join(PROGRAM_ROOT, "spikes", "B0", "verdict", "verdict_b0.py")

BUDGET_IT = 1600
EVAL_ITS = tuple(160 * k for k in range(1, 11))  # §5: 10 %..100 % of the budget
ENDPOINT = re.compile(r"^it 1600 \|", re.M)
FIRST_CLIPS = ["walk1_subject1", "run1_subject2", "dance1_subject1", "jumps1_subject1"]  # §3 / B1-V-4
GPU_NAME = "NVIDIA GeForce RTX 4090"  # B1-V-5
SEAMS = ("S1_joint_order_match", "S2_term_major_ok", "S5_env_action_scale_match")
HEAD_JOINTS = ["head_pitch_joint", "head_yaw_joint"]
# §4 transfer identities (P4 ckpt_0001600.pt, P5-verified sha256)
SRC = {
    "attention_s0": "5fb48347dd957b91de4b6780c53bd43d9f1777f56aabc3396aa7351181474a1d",
    "attention_s1": "44971f21d0f9bd3dc2abbbba4775c0597efa09c64da0db376c55eb09a7d61d68",
    "attention_s2": "c09d6b8ae4ecc9c7ced48a587869087bf8bc4803da08694bcd2c15dc233d28e5",
    "mlp_matched_s0": "9ae05d74b9813e4858904a196cffe718d95d1237b41fdd7620aa3c842001913e",
    "mlp_matched_s1": "5eb302ed06aad69fe9793cc0b0f085536423c30c53e1c6ef46653fce77211da9",
    "mlp_matched_s2": "88a396ce00333b4e72b43fafefd2e62f8b83604cf185115e1f9e0a8a32fa73e1",
}
# §4 arms: name -> (run tag, policy, init, seeds, role, source key template)
ARMS = {
    "H-A-scratch": ("b1HAscratch", "attention", "scratch", (0, 1, 2), "primary", None),
    "H-A-xfer": ("b1HAxfer", "attention", "xfer", (0, 1, 2), "primary", "attention_s{k}"),
    "H-M-xfer": ("b1HMxfer", "mlp_matched", "xfer", (0, 1, 2), "primary", "mlp_matched_s{k}"),
    "H-M-scratch": ("b1HMscratch", "mlp_matched", "scratch", (0, 1, 2), "secondary", None),
    "H-A-frozen": ("b1HAfrozen", "attention", "frozen", (0,), "diagnostic", "attention_s0"),
    "H-A-xfer-noscale": ("b1HAxfernoscale", "attention", "xfer", (0,), "diagnostic", "attention_s0"),
}
PRIMARY = ("H-A-scratch", "H-A-xfer", "H-M-xfer")
# M1 (AMENDMENT-M1-eval-metric.md; post-hoc re-score). Used only with --amendment-m1.
M1_AMENDMENT_SHA256 = "d04aca276c6042d7bc56c63bb6a328d62fef451290047d310b64d065475abdfe"
M1_FRAMES = {"walk1_subject1": 13066, "run1_subject2": 11891, "dance1_subject1": 6574, "jumps1_subject1": 12222}  # M1.2
M1_DANCE = "dance1_subject1"
M1_W = 5336  # M1.3 dance1 window
M1_DELTA = 0.03  # M1.5
M1_COLLAPSE_FRAC = 0.10  # M1.4
M1_SUM_TOL = 1e-9  # M1.6 item 4
M1_RULES = ("primary", "excl", "full")  # M1.3: primary window / S-excl / S-full
M1_LABEL = "post-hoc re-score (M1)"
M1_DEPOSIT_SHA256 = "f95155af47357026d69f7c06f01c3d20ca806aa3378fce125322001d1094126d"  # M1.1: the only deposit
M1_V10_RECORD = os.path.join(PROGRAM_ROOT, "orch", "reports", "VERDICT-P6-b1-arms-attempt1-results.json")
M1_V10_RECORD_SHA256 = "64644e3c594de07a6819b685b1d0f956849eaafbff56b3ad87eab0cbb70c1403"  # attempt-1 record (immutable)
DISCLOSURES = [
    "P5 caveat (A1.1-4): B2 returned NO_GAIN with u_deficit = true (delta rho_U(0.2) = -0.557); B1 inherits no "
    "robustness advantage claim for the attention decoder.",
    "RT-4 waived (Class-2 option C, 934b3c9b...): references fail retarget QA; RT-6..RT-8 binding.",
    "Claim scope (A1.1-8 + C): decoder-weight transfer between two rigid humanoids; within-plant arm comparisons on "
    "shared RT-a references; whole-policy zero-shot transfer out of scope. Single candidate; Provisional.",
]


def log(*a):
    print(*a, file=sys.stderr)


def load_b0():
    """Import the sealed B0 verdict tool for its TF-event reader, safe extraction and seal lookup (read-only)."""
    h = hashlib.sha256(open(B0_VERDICT, "rb").read()).hexdigest()
    if h != B0_VERDICT_SHA256:
        raise SystemExit(f"verdict_b0.py sha256 {h} != sealed {B0_VERDICT_SHA256}")
    spec = importlib.util.spec_from_file_location("verdict_b0_ro", B0_VERDICT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


VB = None


def fnum(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def sd1(xs):
    if len(xs) < 2:
        return None
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def jload(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh), None
    except (OSError, ValueError) as e:
        return None, f"{type(e).__name__}: {e}"


def kv(path):
    return VB.kv_file(VB.read_text(path)) if path and os.path.exists(path) else {}


# ----------------------------------------------------------------------------------------- per-attempt evidence
def attempt_evidence(st, run, aid):
    """B0 §4.3 completion from the bundle + §7 classification (non-finite = result; spend cap stop; else INFRA)."""
    ev = {"aid": aid, "problems": []}
    tl = st.get(f"logs/train_{aid}.log")
    text = VB.read_text(tl) if tl else ""
    ev["train_log"] = bool(tl)
    ev["endpoint_line"] = bool(ENDPOINT.search(text))
    hs = kv(st.get(f"meta/harness_stop_{aid}.txt"))
    ev["harness"] = hs
    ev["ckpt_stable"] = hs.get("ckpt_stable") == "true" and hs.get("ckpt_path", "").endswith(f"logs/{run}/ckpt_0001600.pt")
    ev["harness_stop_timeout"] = hs.get("harness_stop_timeout") == "true"
    ev["spend_cap_stop"] = hs.get("spend_cap_stop") == "true"
    sc_path = st.get(f"logs/attempts/{aid}/junior_policy.json")
    side, err = jload(sc_path) if sc_path else (None, "missing")
    ev["sidecar"] = side is not None
    if err and sc_path:
        ev["problems"].append(f"sidecar unreadable: {err}")
    ev["_sidecar"] = side
    tb_files = [r for r in st.ls(f"logs/attempts/{aid}/tb/") if os.path.basename(r).startswith("events.")]
    ev["tb_files"] = len(tb_files)
    recs, infos = [], []
    for r in tb_files:
        rr, info = VB.read_events(st.get(r))
        recs += rr
        infos.append({k: info[k] for k in ("crc_errors", "truncated", "records")})
    ev["tb_read_info"] = infos
    series = VB.dedupe_series(recs)
    ev["_series"] = series
    nonfinite = sorted(t for t, pts in series.items() if any(s <= BUDGET_IT and not math.isfinite(v) for s, v in pts.items()))
    ev["nonfinite_tags_le_1600"] = nonfinite
    upd = series.get("time/updates", {}).get(BUDGET_IT)
    ev["updates_at_1600"] = upd
    ev["completed"] = bool(ev["endpoint_line"] and ev["ckpt_stable"] and not ev["harness_stop_timeout"]
                           and ev["sidecar"] and hs.get("sidecar") != "missing" and not nonfinite and tb_files)
    if nonfinite:
        ev["class"] = "NONFINITE"
    elif ev["completed"]:
        ev["class"] = "COMPLETED"
    elif ev["spend_cap_stop"]:
        ev["class"] = "SPEND_CAP"
    else:
        ev["class"] = "INFRA"
    return ev


def eval_points(st, run, aid):
    """§5: one execution per point; exec2 counts only if exec1 exited non-zero or wrote no JSON."""
    out, notes = {}, []
    for it in EVAL_ITS:
        tag = f"{it:07d}"
        p = {"scored_exec": None, "R": None, "execs": {}}
        for k in (1, 2):
            base = f"logs/eval/{aid}/it{tag}/exec{k}/"
            el = st.get(base + "eval.log")
            if el is None and not st.has_prefix(base):
                continue
            txt = VB.read_text(el) if el else ""
            exits = re.findall(r"^exit=(-?\d+)$", txt, re.M)
            js = [r for r in st.ls(base) if r.endswith("_mask0.00.json")]
            want = base + f"{run}_ckpt_{tag}_mask0.00.json"
            e = {"exit": int(exits[-1]) if exits else None, "json": [os.path.basename(j) for j in js]}
            ok = e["exit"] == 0 and js == [want]
            r = None
            if ok:
                d, err = jload(st.get(want))
                # v1.1 hardening: a non-object summary gives R = None (v1.0 raised AttributeError here)
                sm = d.get("summary", {}) if isinstance(d, dict) else None
                r = sm.get("mean_norm_return") if isinstance(sm, dict) else None
                if err or not isinstance(d, dict):
                    ok = False
                    e["error"] = err or "not an object"
            e["valid"], e["R"] = ok, r
            p["execs"][f"exec{k}"] = e
            if p["scored_exec"] is None:
                if ok:
                    p["scored_exec"], p["R"] = f"exec{k}", r
                    if k == 1 and st.has_prefix(f"logs/eval/{aid}/it{tag}/exec2/"):
                        notes.append(f"it{tag}: exec2 present after a valid exec1 (ignored)")
                    break
        p["R_finite"] = fnum(p["R"])
        out[f"it{tag}"] = p
    return out, notes


def curve_metrics(R):
    """§5: AULC = (1/9) sum_{k=1}^{9} (R_k + R_{k+1}) / 2; R25 = linear between it 320 and it 480; R100 = R_10."""
    if len(R) != 10 or not all(fnum(x) for x in R):
        return None, None, None
    aulc = sum((R[k] + R[k + 1]) / 2.0 for k in range(9)) / 9.0
    r25 = R[1] + (400 - 320) / (480 - 320) * (R[2] - R[1])
    return aulc, r25, R[9]


# ----------------------------------------------------------------------------------------- the run table
def evaluate_runs(st):
    runs = {}
    for arm, (tag, pol, init, seeds, role, srck) in ARMS.items():
        for s in seeds:
            run = f"{tag}_{pol}_s{s}"
            rec = {"arm": arm, "policy": pol, "init": init, "seed": s, "role": role, "attempts": {}, "notes": []}
            if srck:
                rec["src_key"] = srck.format(k=s)
                rec["src_expected_sha256"] = SRC[rec["src_key"]]
            aids = sorted({m.group(1) for r in st.ls("meta/attempt_") for m in [re.match(rf"^meta/attempt_({re.escape(run)}_a(\d+))\.txt$", r)] if m},
                          key=lambda a: int(a.rsplit("_a", 1)[1]))
            for aid in aids:
                n = int(aid.rsplit("_a", 1)[1])
                if n > 2:
                    rec["notes"].append(f"{aid}: beyond the 2-attempt cap (ignored)")
                    continue
                rec["attempts"][aid] = attempt_evidence(st, run, aid)
            scored = None
            a1, a2 = rec["attempts"].get(f"{run}_a1"), rec["attempts"].get(f"{run}_a2")
            if a1 and a1["completed"]:
                scored = a1
                if a2:
                    rec["notes"].append("attempt 2 present after a completed attempt 1 (ignored)")
            elif a1 and a1["class"] == "INFRA" and a2 and a2["completed"]:
                scored = a2
            elif a1 and a1["class"] != "INFRA" and a2:
                rec["notes"].append(f"attempt 2 after a {a1['class']} attempt 1 is not allowed by §7 (ignored)")
            rec["scored_attempt"] = scored["aid"] if scored else None
            last = list(rec["attempts"].values())[-1] if rec["attempts"] else None
            rec["status"] = "completed" if scored else "not_run" if last is None else last["class"].lower()
            if scored:
                pts, notes = eval_points(st, run, scored["aid"])
                rec["eval"], rec["notes"] = pts, rec["notes"] + notes
                R = [pts[f"it{it:07d}"]["R"] for it in EVAL_ITS]
                rec["R"] = R
                rec["aulc"], rec["r25"], rec["r100"] = curve_metrics(R)
            else:
                rec["R"], rec["aulc"], rec["r25"], rec["r100"] = None, None, None, None
            runs[run] = rec
    return runs


def run_of(arm, s):
    tag, pol = ARMS[arm][0], ARMS[arm][1]
    return f"{tag}_{pol}_s{s}"


def strip_argv(argv):
    out, skip = [], False
    for x in argv or []:
        if skip:
            skip = False
            continue
        if x in ("--run-name", "--seed"):
            skip = True
            continue
        out.append(x)
    return out


# ----------------------------------------------------------------------------------------- validity (§6)
def v1(runs):
    bad = []
    for arm in PRIMARY:
        for s in ARMS[arm][3]:
            run = run_of(arm, s)
            r = runs[run]
            if not r["scored_attempt"]:
                bad.append(f"{run}: no completed attempt ({r['status']})")
                continue
            ev = r["attempts"][r["scored_attempt"]]
            side = ev["_sidecar"] or {}
            seam = side.get("seam", {})
            miss = [k for k in SEAMS if seam.get(k) is not True]
            if miss:
                bad.append(f"{run}: seams not true: {miss}")
            nf = [k for k, p in r["eval"].items() if not p["R_finite"]]
            if nf:
                bad.append(f"{run}: eval points without a finite R_k: {nf}")
    return not bad, bad


def v2(runs):
    bad, upd, argvs = [], {}, {}
    for arm in PRIMARY:
        for s in ARMS[arm][3]:
            run = run_of(arm, s)
            r = runs[run]
            if not r["scored_attempt"]:
                bad.append(f"{run}: not evaluable (no completed attempt)")
                continue
            ev = r["attempts"][r["scored_attempt"]]
            if not (ev["endpoint_line"] and ev["ckpt_stable"]):
                bad.append(f"{run}: no it-1600 endpoint")
            u = ev["updates_at_1600"]
            upd[run] = u
            if not fnum(u):
                bad.append(f"{run}: time/updates at it 1600 missing")
            argvs[run] = strip_argv((ev["_sidecar"] or {}).get("argv"))
    vals = {u for u in upd.values() if fnum(u)}
    if len(vals) > 1:
        bad.append(f"time/updates at it 1600 differ: {upd}")
    av = {json.dumps(a) for a in argvs.values()}
    if len(av) > 1:
        bad.append("upstream argv (without --run-name/--seed) differs across primary runs")
    for run, a in argvs.items():
        if "--env.num-envs" not in a or a[a.index("--env.num-envs") + 1:a.index("--env.num-envs") + 2] != ["512"]:
            bad.append(f"{run}: argv lacks --env.num-envs 512")
    return not bad, bad, upd


def v3(runs):
    bad, checked = [], {}
    for run, r in runs.items():
        if r["init"] == "scratch":
            continue
        aid = r["scored_attempt"] or next((a for a in reversed(list(r["attempts"])) if r["attempts"][a]["sidecar"]), None)
        if not aid:
            checked[run] = "not_run"
            if r["role"] != "primary":
                continue
            bad.append(f"{run}: no sidecar (not run)")
            continue
        side = r["attempts"][aid]["_sidecar"] or {}
        got = (side.get("transfer_src") or {}).get("sha256")
        rep = side.get("transfer") or {}
        prob = []
        if got != r["src_expected_sha256"]:
            prob.append(f"transfer_src.sha256 {got} != {r['src_key']} {r['src_expected_sha256']}")
        if side.get("init") != r["init"]:
            prob.append(f"sidecar init {side.get('init')} != {r['init']}")
        if r["policy"] == "attention":
            if not (rep.get("kind") == "attention_full_copy" and fnum(rep.get("n_values_copied"))
                    and rep.get("n_values_copied") == side.get("params_total") and (rep.get("n_params_copied") or 0) > 0):
                prob.append(f"attention report not all-parameters: {({k: rep.get(k) for k in ('kind', 'n_params_copied', 'n_values_copied')})} "
                            f"params_total={side.get('params_total')}")
        else:
            if not (rep.get("kind") == "mlp_row_mapped" and rep.get("output_rows_mapped") == 20
                    and sorted(rep.get("fresh_joints") or []) == HEAD_JOINTS):
                prob.append(f"mlp report: rows_mapped={rep.get('output_rows_mapped')} fresh={rep.get('fresh_joints')}")
        checked[run] = {"attempt": aid, "pass": not prob, "problems": prob}
        bad += [f"{run}: {p}" for p in prob]
    return not bad, bad, checked


def v4(st):
    p = st.get("meta/b1_data_qa.json")
    d, err = jload(p) if p else (None, "missing")
    if not isinstance(d, dict):
        return False, [f"meta/b1_data_qa.json {err or 'not an object'}"], None
    bad = []
    if d.get("pass") is not True:
        bad.append(f"pass={d.get('pass')}")
    if d.get("used_clips") != FIRST_CLIPS:
        bad.append(f"used_clips={d.get('used_clips')}")
    if d.get("csv_sha_mismatch") != []:
        bad.append(f"csv_sha_mismatch={d.get('csv_sha_mismatch')}")
    if d.get("slot_rule") != "first":
        bad.append(f"slot_rule={d.get('slot_rule')}")
    if d.get("mock"):
        bad.append("mock data step")
    return not bad, bad, {k: d.get(k) for k in ("pass", "used_clips", "csv_sha_mismatch", "slot_rule", "rev")}


def v5(st):
    bad, info = [], {}
    p = st.get("meta/gpu_used.csv.txt")
    if not p:
        return False, ["meta/gpu_used.csv.txt missing"], info
    rows = [ln for ln in VB.read_text(p).splitlines() if ln.strip()]
    info["gpu_used"] = rows
    if not rows or [c.strip() for c in rows[0].split(",")] != ["index", "uuid", "name"]:
        bad.append(f"header {rows[:1]}")
    data = rows[1:]
    if len(data) != 1:
        bad.append(f"{len(data)} device rows (need exactly 1)")
    for r in data:
        f = [c.strip() for c in r.split(",")]
        if len(f) != 3 or f[2] != GPU_NAME:
            bad.append(f"device row {r!r} does not name exactly {GPU_NAME!r}")
    env = [ln.strip() for ln in VB.read_text(st.get("meta/gpu_env.txt")).splitlines() if ln.strip()] if st.get("meta/gpu_env.txt") else []
    info["gpu_env"] = env
    if not env or any(not ln.endswith("CUDA_VISIBLE_DEVICES=0") for ln in env):
        bad.append(f"CUDA_VISIBLE_DEVICES record {env}")
    pa = st.get("meta/gpu_used_attempts.txt")
    if pa:
        lines = [ln for ln in VB.read_text(pa).splitlines() if ln.strip()]
        info["per_attempt"] = len(lines)
        for ln in lines:
            f = [c.strip() for c in ln.split(" ", 1)[-1].split(",")]
            if len(f) != 3 or f[2] != GPU_NAME:
                bad.append(f"per-attempt device line {ln!r}")
    return not bad, bad, info


# ----------------------------------------------------------------------------------------- outcome (§5)
def arm_stats(runs, arm):
    vals = [runs[run_of(arm, s)]["aulc"] for s in ARMS[arm][3]]
    vals = [v for v in vals if fnum(v)]
    r25 = [runs[run_of(arm, s)]["r25"] for s in ARMS[arm][3] if fnum(runs[run_of(arm, s)]["r25"])]
    r100 = [runs[run_of(arm, s)]["r100"] for s in ARMS[arm][3] if fnum(runs[run_of(arm, s)]["r100"])]
    return {"n": len(vals), "aulc": vals, "aulc_mean": mean(vals), "aulc_sd": sd1(vals),
            "r25_mean": mean(r25), "r100_mean": mean(r100)}


def outcome(stats):
    x, s, m = stats["H-A-xfer"], stats["H-A-scratch"], stats["H-M-xfer"]
    if min(x["n"], s["n"], m["n"]) < 2:
        return None, {"reason": "fewer than 2 seeds with a full curve in a primary arm"}
    mx, ms, mm = x["aulc_mean"], s["aulc_mean"], m["aulc_mean"]
    se = math.sqrt(x["aulc_sd"] ** 2 / x["n"] + m["aulc_sd"] ** 2 / m["n"])  # §5: s_X^2/3 + s_Y^2/3 at n = 3
    ratio_ok = (mx >= 1.2 * ms) if ms > 0 else (mx - ms >= 0.2 * abs(ms))
    kill = (mx <= ms) or (mx < mm - 2 * se)
    if kill:
        o = "KILL"
    elif ratio_ok and mx - mm >= 2 * se:
        o = "SIGNAL_STRONG"
    elif ratio_ok and mx >= mm - 2 * se:
        o = "SIGNAL"
    else:
        o = "INCONCLUSIVE"
    return o, {"mean_HA_xfer": mx, "mean_HA_scratch": ms, "mean_HM_xfer": mm, "se_HA_xfer_HM_xfer": se,
               "ratio_branch": "1.2x" if ms > 0 else "abs_0.2", "ratio_ok": ratio_ok,
               "kill_xfer_le_scratch": mx <= ms, "kill_xfer_below_mlp_2se": mx < mm - 2 * se,
               "diff_xfer_minus_mlp": mx - mm, "two_se": 2 * se, "n": [x["n"], s["n"], m["n"]]}


# ----------------------------------------------------------------------------------------- M1 post-hoc re-score
def m1_clip_eval(d, rule):
    """M1.2-M1.6 for one scored eval JSON under rule primary|excl|full -> dict(valid, problems, R, S, failed, collapse)."""
    prob = []
    bad = {"valid": False, "R": None, "S": None, "failed": None, "collapse": None}
    clips = d.get("clips") if isinstance(d, dict) else None
    if not (isinstance(clips, list) and len(clips) == 4 and all(isinstance(c, dict) and isinstance(c.get("name"), str) for c in clips)
            and sorted(c["name"] for c in clips) == sorted(M1_FRAMES)):
        return {**bad, "problems": ["I1: clips != the 4 pinned clips"]}
    isint = lambda v: isinstance(v, int) and not isinstance(v, bool)  # noqa: E731
    for c in sorted(clips, key=lambda c: c["name"]):
        n, nr, st_, fr = c["name"], c.get("norm_return"), c.get("steps"), c.get("frames")
        if not fnum(nr):
            prob.append(f"I2: {n}: norm_return {nr!r} not finite")
        if not (isint(fr) and fr == M1_FRAMES[n]):
            prob.append(f"I2: {n}: frames {fr!r} != pinned {M1_FRAMES[n]}")
        elif not (isint(st_) and 1 <= st_ <= fr):
            prob.append(f"I2: {n}: steps {st_!r} not an integer in [1, frames {fr}]")
    if not prob:
        summ = d.get("summary").get("mean_norm_return") if isinstance(d.get("summary"), dict) else None
        if not fnum(summ) or abs(mean([c["norm_return"] for c in sorted(clips, key=lambda c: c["name"])]) - summ) > M1_SUM_TOL:
            prob.append(f"I3: summary.mean_norm_return {summ!r} != mean of clip norm_return")
    if not prob and rule == "primary":
        dc = next(c for c in clips if c["name"] == M1_DANCE)
        if dc["steps"] > M1_W:
            prob.append(f"C1: {M1_DANCE}: steps {dc['steps']} > W {M1_W} (not computable; M1.3)")
    if prob:
        return {**bad, "problems": prob}
    rs, surv, eff, failed, collapse = [], 0, 0, 0, False
    for c in sorted(clips, key=lambda c: c["name"]):
        if c["name"] == M1_DANCE and rule == "excl":
            continue
        F = M1_W if (c["name"] == M1_DANCE and rule == "primary") else c["frames"]
        k = c["steps"]  # <= F here (I2 / C1); never clipped (M1.2)
        rs.append(c["norm_return"] * k / F)
        surv, eff = surv + k, eff + F
        if k < F:
            failed += 1
            if 10 * k < F:  # M1.4 collapse: integer comparison (M1_COLLAPSE_FRAC = 0.10)
                collapse = True
    R, S = mean(rs), surv / eff
    if not (fnum(R) and fnum(S)):
        return {**bad, "problems": [f"C2: derived R {R!r} / S {S!r} not finite"]}
    return {"valid": True, "problems": [], "R": R, "S": S, "failed": failed, "collapse": collapse, "n_clips": len(rs)}


def m1_runs(st, runs, rule):
    """Per run: R_full at the 10 scored points (v1.0 scored attempt/exec), AULC_full/R25/R100, M1 validity, counts."""
    out = {}
    for run, r in runs.items():
        rec = {"arm": r["arm"], "seed": r["seed"], "role": r["role"], "valid": False, "problems": [], "points": {}}
        if not r["scored_attempt"]:
            rec["problems"].append(f"no scored attempt ({r['status']})")
        else:
            aid = r["scored_attempt"]
            for it in EVAL_ITS:
                tag = f"it{it:07d}"
                p = r["eval"][tag]
                if p["scored_exec"] is None:
                    e = {"valid": False, "problems": ["no scored exec"], "R": None, "S": None, "failed": None, "collapse": None}
                else:
                    d, err = jload(st.get(f"logs/eval/{aid}/{tag}/{p['scored_exec']}/{run}_ckpt_{it:07d}_mask0.00.json"))
                    try:
                        e = m1_clip_eval(d, rule) if not err else {"valid": False, "problems": [err], "R": None, "S": None,
                                                                    "failed": None, "collapse": None}
                    except (ArithmeticError, TypeError, ValueError) as ex:  # M1.6 C2
                        e = {"valid": False, "problems": [f"C2: {type(ex).__name__}: {ex}"], "R": None, "S": None,
                             "failed": None, "collapse": None}
                e["R_v10"] = p["R"]
                rec["points"][tag] = e
                rec["problems"] += [f"{tag}: {x}" for x in e["problems"]]
            rec["valid"] = not rec["problems"]
        pts = [rec["points"].get(f"it{it:07d}", {}) for it in EVAL_ITS]
        R = [q.get("R") for q in pts]
        rec["R_full"] = R
        try:
            rec["aulc_full"], rec["r25_full"], rec["r100_full"] = curve_metrics(R) if rec["valid"] else (None, None, None)
        except (ArithmeticError, TypeError, ValueError):
            rec["aulc_full"] = rec["r25_full"] = rec["r100_full"] = float("nan")
        if rec["valid"] and not all(fnum(v) for v in (rec["aulc_full"], rec["r25_full"], rec["r100_full"])):
            rec["problems"].append("C2: derived AULC/R25/R100 not finite")
            rec["valid"] = False
            rec["aulc_full"], rec["r25_full"], rec["r100_full"] = None, None, None
        if rec["valid"]:
            rec["S_mean"] = mean([q["S"] for q in pts])
            rec["n_multifail"] = sum(q["failed"] >= 2 for q in pts)
            rec["n_collapse"] = sum(bool(q["collapse"]) for q in pts)
        out[run] = rec
    return out


def m1_arm_stats_safe(mr, arm):
    """M1.6 C2 at arm level: an arithmetic failure or non-finite aggregate is recorded, not raised."""
    try:
        a = m1_arm_stats(mr, arm)
    except (ArithmeticError, TypeError, ValueError) as ex:  # full schema; statistics unavailable -> null
        ok = [mr[run_of(arm, s)] for s in ARMS[arm][3] if mr[run_of(arm, s)]["valid"]]
        return {"n": len(ok), "seeds_retained": [r["seed"] for r in ok], "aulc": [r["aulc_full"] for r in ok],
                "aulc_mean": None, "aulc_sd": None, "r25_mean": None, "r100_mean": None, "S_mean": None,
                "n_multifail": None, "n_collapse": None, "n_evals": 10 * len(ok), "c2_error": f"{type(ex).__name__}: {ex}"}
    bad = [k for k, v in a.items() if isinstance(v, float) and not math.isfinite(v)]
    if bad:
        a["c2_error"] = f"non-finite aggregate {bad}"
    return a


def m1_arm_stats(mr, arm):
    recs = [mr[run_of(arm, s)] for s in ARMS[arm][3]]
    ok = [r for r in recs if r["valid"]]
    vals = [r["aulc_full"] for r in ok]
    return {"n": len(vals), "seeds_retained": [r["seed"] for r in ok], "aulc": vals, "aulc_mean": mean(vals), "aulc_sd": sd1(vals),
            "r25_mean": mean([r["r25_full"] for r in ok]), "r100_mean": mean([r["r100_full"] for r in ok]),
            "S_mean": mean([r["S_mean"] for r in ok]), "n_multifail": sum(r["n_multifail"] for r in ok),
            "n_collapse": sum(r["n_collapse"] for r in ok), "n_evals": 10 * len(ok)}


def m1_outcome(stats, delta):
    """M1.5: KILL as PLAN §5; SIGNAL(_STRONG) needs mean(x) - mean(s) >= max(delta, 2 SE(x, s)) instead of 1.2x."""
    x, s, m = stats["H-A-xfer"], stats["H-A-scratch"], stats["H-M-xfer"]
    if min(x["n"], s["n"], m["n"]) < 2:
        return None, {"reason": "fewer than 2 M1-valid seeds in a primary arm"}
    mx, ms, mm = x["aulc_mean"], s["aulc_mean"], m["aulc_mean"]
    se_xm = math.sqrt(x["aulc_sd"] ** 2 / x["n"] + m["aulc_sd"] ** 2 / m["n"])
    se_xs = math.sqrt(x["aulc_sd"] ** 2 / x["n"] + s["aulc_sd"] ** 2 / s["n"])
    margin = max(delta, 2 * se_xs)
    ops = (mx, ms, mm, se_xm, se_xs, margin, mx - ms, mx - mm, mm - 2 * se_xm)
    if not all(fnum(v) for v in ops):  # M1.6 C2: validate every operand before classifying
        return None, {"reason": "C2: non-finite comparison operand", "operands": [repr(v) for v in ops]}
    gain_ok = mx - ms >= margin
    kill = (mx <= ms) or (mx < mm - 2 * se_xm)
    if kill:
        o = "KILL"
    elif gain_ok and mx - mm >= 2 * se_xm:
        o = "SIGNAL_STRONG"
    elif gain_ok and mx >= mm - 2 * se_xm:
        o = "SIGNAL"
    else:
        o = "INCONCLUSIVE"
    return o, {"mean_HA_xfer": mx, "mean_HA_scratch": ms, "mean_HM_xfer": mm, "delta": delta,
               "se_HA_xfer_HA_scratch": se_xs, "se_HA_xfer_HM_xfer": se_xm, "diff_xfer_minus_scratch": mx - ms,
               "margin_xs": margin, "gain_ok": gain_ok, "kill_xfer_le_scratch": mx <= ms,
               "kill_xfer_below_mlp_2se": mx < mm - 2 * se_xm, "diff_xfer_minus_mlp": mx - mm, "two_se_xm": 2 * se_xm,
               "lower_bound_mlp_2se": mm - 2 * se_xm,
               "n": [x["n"], s["n"], m["n"]]}


def m1_branch(st, runs, rule, crit, v10_failing):
    """One pre-registered analysis (M1.6: evaluated independently): rule (primary|excl|full) x criterion (diff delta |
    ratio = PLAN §5 verbatim). Scored attempt/exec are the v1.0 ones; no fallback on an M1 validation failure."""
    mr = m1_runs(st, runs, rule)
    stats = {arm: m1_arm_stats_safe(mr, arm) for arm in ARMS}  # secondary-arm C2 errors stay informational
    c2 = [f"C2: arm {arm}: {stats[arm]['c2_error']}" for arm in PRIMARY if "c2_error" in stats[arm]]
    o, cmp_ = None, None
    if not c2:
        try:
            o, cmp_ = outcome(stats) if crit == "ratio" else m1_outcome(stats, crit)
            if crit == "ratio" and o is not None:  # every operand of the PLAN §5 rules (M1.6 C2)
                cmp_["threshold_1_2x_scratch"] = 1.2 * cmp_["mean_HA_scratch"]
                cmp_["threshold_abs_0_2"] = cmp_["mean_HA_scratch"] + 0.2 * abs(cmp_["mean_HA_scratch"])
                cmp_["lower_bound_mlp_2se"] = cmp_["mean_HM_xfer"] - cmp_["two_se"]
        except (ArithmeticError, TypeError, ValueError) as ex:
            c2.append(f"C2: comparison: {type(ex).__name__}: {ex}")
        if o is None and str((cmp_ or {}).get("reason", "")).startswith("C2"):
            c2.append(cmp_["reason"])
        c2 += [f"C2: comparison quantity {k} not finite" for k, v in (cmp_ or {}).items()
               if isinstance(v, float) and not math.isfinite(v)]
    if c2:  # comparison-level C2: outcome and partial outcome are both null
        o = None
    bad = [f"{run}: {p}" for arm in PRIMARY for s in ARMS[arm][3] for run in [run_of(arm, s)] for p in mr[run]["problems"]]
    bad += c2
    failing = list(v10_failing) + (["M1-valid"] if bad else [])
    return {"rule": rule, "criterion": "ratio_1.2x_PLAN5" if crit == "ratio" else f"diff_delta_{crit}",
            "verdict": "BLOCKED" if failing else "PASS", "failing_ids": failing, "m1_valid": not bad, "problems": bad,
            "outcome": None if failing else o,
            "partial_outcome": (None if not failing or o is None else "INCONCLUSIVE" if o in ("SIGNAL", "SIGNAL_STRONG") else o),
            "partial_seeds_retained": ({arm: stats[arm]["seeds_retained"] for arm in PRIMARY} if failing and o is not None else None),
            "comparison": cmp_, "arms": stats, "runs": mr}


def m1_rescore(st, runs, v10_failing, v10_outcome):
    prim = m1_branch(st, runs, "primary", M1_DELTA, v10_failing)
    sens = {"S-excl": m1_branch(st, runs, "excl", M1_DELTA, v10_failing),
            "S-full": m1_branch(st, runs, "full", M1_DELTA, v10_failing),
            "S-d10": m1_branch(st, runs, "primary", 0.10, v10_failing),
            "S-ratio": m1_branch(st, runs, "primary", "ratio", v10_failing)}
    res = {"label": M1_LABEL, "v10_recomputed_outcome": v10_outcome, "v10_recomputed_failing_ids": list(v10_failing),
           "verdict": prim["verdict"], "outcome": prim["outcome"], "partial_outcome": prim["partial_outcome"],
           "failing_ids": prim["failing_ids"]}
    # M1.5: robust only if the primary PASSes and all four sensitivities are non-null; true iff all equal the primary
    if prim["verdict"] != "PASS" or any(v["outcome"] is None for v in sens.values()):
        res["robust"] = None
    else:
        res["robust"] = all(v["outcome"] == prim["outcome"] for v in sens.values())
    res["primary"] = prim
    res["sensitivities"] = sens
    return res


# ----------------------------------------------------------------------------------------- main
def fmt(x):
    if x is None:
        return "null"
    if isinstance(x, list):
        return "[" + ",".join(str(i) for i in x) + "]"
    return repr(x) if isinstance(x, float) else str(x)


def strip_private(o):
    if isinstance(o, dict):
        return {k: strip_private(v) for k, v in o.items() if not k.startswith("_")}
    if isinstance(o, list):
        return [strip_private(v) for v in o]
    if isinstance(o, float) and not math.isfinite(o):
        return repr(o)
    return o


def main(argv=None):
    global VB
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--deposit", action="append", required=True)
    ap.add_argument("--tarball-sha", required=True)
    ap.add_argument("--seal-log", default=os.path.join(PROGRAM_ROOT, "logs", "seal.log"))
    ap.add_argument("--out", default=None, help="default results.json (v1.0 mode) / results-M1.json (M1 mode)")
    ap.add_argument("--runs-log", default=None, help="default runs.log (v1.0 mode) / runs-M1.log (M1 mode)")
    ap.add_argument("--amendment-m1", default=None, help="sealed AMENDMENT-M1-eval-metric.md: post-hoc re-score (M1)")
    a = ap.parse_args(argv)
    m1 = a.amendment_m1 is not None
    a.out = a.out or os.path.join(HERE, "results-M1.json" if m1 else "results.json")
    a.runs_log = a.runs_log or os.path.join(HERE, "runs-M1.log" if m1 else "runs.log")
    if m1:
        am_sha = hashlib.sha256(open(a.amendment_m1, "rb").read()).hexdigest()
        if am_sha != M1_AMENDMENT_SHA256:
            raise SystemExit(f"amendment sha256 {am_sha} != pinned {M1_AMENDMENT_SHA256}")
        m1_guard(a)
    VB = load_b0()
    tool_sha = VB.sha256_file(os.path.abspath(__file__))
    seal_text = VB.read_text(a.seal_log) if os.path.exists(a.seal_log) else ""
    res = {"tool": "spikes/B1/verdict_b1.py", "tool_version": TOOL_VERSION, "tool_sha256": tool_sha,
           "plan_sha256": PLAN_SHA256, "b0_helpers_sha256": B0_VERDICT_SHA256,
           "computed_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "tarball_sha256_expected": a.tarball_sha, "deposits": [], "disclosures": DISCLOSURES}
    deposit_bad = []
    st = VB.Store()
    with tempfile.TemporaryDirectory(prefix="b1verdict-") as tmp:
        for i, dep in enumerate(a.deposit):
            d = {"path": dep, "sha256": VB.sha256_file(dep) if os.path.isfile(dep) else None}
            line, venue = VB.seal_lookup(seal_text, d["sha256"]) if d["sha256"] else (None, None)
            d["seal_line"], d["seal_venue"] = line, venue
            if not line or venue != "xn4090":
                deposit_bad.append(f"{dep}: not sealed as DEPOSIT xn4090")
                d["extracted"] = False
            else:
                dest = os.path.join(tmp, f"d{i}")
                os.makedirs(dest)
                probs = VB.safe_extract(dep, dest)
                d["member_problems"] = probs
                d["extracted"] = not probs
                if probs:
                    deposit_bad.append(f"{dep}: unsafe members {probs[:3]}")
                else:
                    st.add_root(dest, i)
            res["deposits"].append(d)
        res["duplicate_members_across_deposits"] = len(st.dups)
        ts = st.get("meta/tarball_sha256.txt")
        tsl = [ln.split() for ln in VB.read_text(ts).splitlines() if ln.strip()] if ts else []
        got = [t[1] if t[0].startswith("part=") else t[0] for t in tsl if t]
        res["tarball_sha256_recorded"] = got
        if not got or any(g != a.tarball_sha for g in got):
            deposit_bad.append(f"meta/tarball_sha256.txt {got} != {a.tarball_sha}")
        res["driver_identity"] = VB.read_text(st.get("meta/driver_identity.txt")).splitlines() if st.get("meta/driver_identity.txt") else []
        bl = st.get("BLOCKED.md")
        res["blocked_md"] = [ln.strip() for ln in VB.read_text(bl).splitlines() if ln.strip()] if bl else []
        sp = st.get("meta/spend.txt")
        res["spend"] = VB.read_text(sp).splitlines() if sp else []

        runs = evaluate_runs(st)
        val = {}
        ok1, b1 = v1(runs)
        ok2, b2, upd = v2(runs)
        ok3, b3, chk3 = v3(runs)
        ok4, b4, info4 = v4(st)
        ok5, b5, info5 = v5(st)
        val["B1-V-1"] = {"pass": ok1, "problems": b1}
        val["B1-V-2"] = {"pass": ok2, "problems": b2, "updates_at_1600": upd}
        val["B1-V-3"] = {"pass": ok3, "problems": b3, "checked": chk3}
        val["B1-V-4"] = {"pass": ok4, "problems": b4, "data_qa": info4}
        val["B1-V-5"] = {"pass": ok5, "problems": b5, "info": info5}
        failing = [k for k, v in val.items() if not v["pass"]]
        if deposit_bad:
            failing = ["deposit_check"] + failing
        res["deposit_check"] = {"pass": not deposit_bad, "problems": deposit_bad}
        res["validity"] = val
        stats = {arm: arm_stats(runs, arm) for arm in ARMS}
        res["arms"] = stats
        o, cmp_ = outcome(stats)
        res["comparison"] = cmp_
        if failing:
            res["verdict"], res["outcome"] = "BLOCKED", None
            # §6 B1-V-1: partial seeds are reported as INCONCLUSIVE at best, never as a pass
            res["partial_outcome"] = (None if o is None else "INCONCLUSIVE" if o in ("SIGNAL", "SIGNAL_STRONG") else o)
        else:
            res["verdict"], res["outcome"], res["partial_outcome"] = "PASS", o, None
        res["failing_ids"] = failing
        res["runs"] = runs
        if m1:
            r1 = m1_rescore(st, runs, failing, res["outcome"])
    line = (f"B1_VERDICT verdict={res['verdict']} outcome={fmt(res['outcome'])} failing={fmt(res['failing_ids'])} "
            f"aulc_HA_xfer={fmt(stats['H-A-xfer']['aulc_mean'])} aulc_HA_scratch={fmt(stats['H-A-scratch']['aulc_mean'])} "
            f"aulc_HM_xfer={fmt(stats['H-M-xfer']['aulc_mean'])} se={fmt((cmp_ or {}).get('se_HA_xfer_HM_xfer'))} "
            f"partial_outcome={fmt(res['partial_outcome'])} plan={PLAN_SHA256[:8]} tool={tool_sha[:8]}")
    res["verdict_line"] = line
    if m1:
        return m1_write(a, res, r1, tool_sha, am_sha)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(strip_private(res), fh, indent=1, sort_keys=False)
        fh.write("\n")
    with open(a.runs_log, "a", encoding="utf-8") as fh:
        fh.write(f"## {res['computed_utc']} verdict_b1 {TOOL_VERSION} tool={tool_sha}\n")
        for d in res["deposits"]:
            fh.write(f"deposit {d['path']} sha256={d['sha256']} extracted={d.get('extracted')}\n")
        fh.write(line + "\n\n")
    print(line)
    return 0


def m1_guard(a):
    """M1.7: exactly the pinned deposit; outputs must not alias any protected input/record (canonical path + inode)."""
    if len(a.deposit) != 1:
        raise SystemExit(f"M1 mode takes exactly one deposit (got {len(a.deposit)})")
    dsha = hashlib.sha256(open(a.deposit[0], "rb").read()).hexdigest() if os.path.isfile(a.deposit[0]) else None
    if dsha != M1_DEPOSIT_SHA256:
        raise SystemExit(f"deposit sha256 {dsha} != M1 pinned {M1_DEPOSIT_SHA256}")
    protected = [os.path.join(HERE, "results.json"), os.path.join(HERE, "runs.log"), M1_V10_RECORD, a.amendment_m1,
                 a.deposit[0], a.seal_log, os.path.abspath(__file__)]
    outs = [a.out, a.runs_log]
    if os.path.realpath(outs[0]) == os.path.realpath(outs[1]) or (
            os.path.exists(outs[0]) and os.path.exists(outs[1]) and os.path.samefile(outs[0], outs[1])):
        raise SystemExit("--out and --runs-log must differ (path and file identity)")
    for o in outs:
        for p in protected:
            same = os.path.realpath(o) == os.path.realpath(p)
            if not same and os.path.exists(o) and os.path.exists(p):
                same = os.path.samefile(o, p)
            if same:
                raise SystemExit(f"M1 mode must not write {o} (protected: {p})")


def m1_v10_record():
    """M1.2 / M1.9: the immutable attempt-1 record, hash-verified; copied verbatim, never recomputed."""
    raw = open(M1_V10_RECORD, "rb").read()
    h = hashlib.sha256(raw).hexdigest()
    if h != M1_V10_RECORD_SHA256:
        raise SystemExit(f"attempt-1 record sha256 {h} != pinned {M1_V10_RECORD_SHA256}")
    d = json.loads(raw)
    return {"path": os.path.relpath(M1_V10_RECORD, PROGRAM_ROOT), "sha256": h, "verdict_line": d["verdict_line"],
            "verdict": d["verdict"], "outcome": d["outcome"], "failing_ids": d["failing_ids"],
            "arms": {k: {"aulc": v.get("aulc"), "aulc_mean": v.get("aulc_mean")} for k, v in d["arms"].items()},
            "runs": {k: {"R": v.get("R"), "aulc": v.get("aulc"), "r25": v.get("r25"), "r100": v.get("r100")}
                     for k, v in d["runs"].items()}}


def m1_write(a, res, r1, tool_sha, am_sha):
    p, sens, c = r1["primary"], r1["sensitivities"], r1["primary"]["comparison"] or {}
    st_ = p["arms"]
    line = (f"B1_M1_VERDICT label=post-hoc-M1 verdict={r1['verdict']} outcome={fmt(r1['outcome'])} "
            f"robust={fmt(r1['robust']).lower() if r1['robust'] is not None else 'null'} failing={fmt(r1['failing_ids'])} "
            f"aulc_full_HA_xfer={fmt(st_['H-A-xfer']['aulc_mean'])} aulc_full_HA_scratch={fmt(st_['H-A-scratch']['aulc_mean'])} "
            f"aulc_full_HM_xfer={fmt(st_['H-M-xfer']['aulc_mean'])} diff_xs={fmt(c.get('diff_xfer_minus_scratch'))} "
            f"margin_xs={fmt(c.get('margin_xs'))} se_xm={fmt(c.get('se_HA_xfer_HM_xfer'))} "
            + " ".join(f"{k}={fmt(v['outcome'])}" for k, v in sens.items())
            + f" partial_outcome={fmt(r1['partial_outcome'])} v10_outcome={fmt(m1_v10_record()['outcome'])} plan={PLAN_SHA256[:8]} "
            f"amendment={am_sha[:8]} tool={tool_sha[:8]}")
    rec = m1_v10_record()
    recomp_runs = {k: {f: v.get(f) for f in ("R", "aulc", "r25", "r100")} for k, v in res["runs"].items()}
    recomp_arms = {k: {"aulc": v.get("aulc"), "aulc_mean": v.get("aulc_mean")} for k, v in res["arms"].items()}
    disc = []
    for name, hist, new in (("runs", rec["runs"], recomp_runs), ("arms", rec["arms"], recomp_arms)):
        for k in sorted(set(hist) | set(new)):
            if k not in hist or k not in new:
                disc.append(f"{name}.{k}: missing in {'record' if k not in hist else 'recomputation'}")
                continue
            disc += [f"{name}.{k}.{f}" for f in hist[k] if hist[k][f] != new[k].get(f)]
    for f in ("verdict", "outcome", "failing_ids"):
        if rec[f] != res[f if f != "failing_ids" else "failing_ids"]:
            disc.append(f)
    if rec["verdict_line"].split(" tool=")[0] != res["verdict_line"].split(" tool=")[0]:
        disc.append("verdict_line (excluding tool sha)")
    out = {"label": M1_LABEL, "v10_record": rec, "v10_recomputed_discrepancies": disc,
           "v10_recomputed": {"runs": recomp_runs, "arms": recomp_arms}, "tool": res["tool"], "tool_version": TOOL_VERSION, "tool_sha256": tool_sha,
           "plan_sha256": PLAN_SHA256, "amendment_m1_sha256": am_sha, "computed_utc": res["computed_utc"],
           "deposits": res["deposits"], "deposit_check": res["deposit_check"], "validity_v10": res["validity"],
           "v10_recomputed_line": res["verdict_line"], "v10_recomputed_outcome": res["outcome"], "disclosures": DISCLOSURES,
           "constants": {"frames": M1_FRAMES, "dance1_W": M1_W, "delta": M1_DELTA, "collapse_frac": M1_COLLAPSE_FRAC,
                         "sum_tol": M1_SUM_TOL},
           **r1, "verdict_line": line}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(strip_private(out), fh, indent=1, sort_keys=False, allow_nan=False)
        fh.write("\n")
    with open(a.runs_log, "a", encoding="utf-8") as fh:
        fh.write(f"## {res['computed_utc']} verdict_b1 {TOOL_VERSION} M1 {M1_LABEL} tool={tool_sha} amendment={am_sha}\n")
        for d in res["deposits"]:
            fh.write(f"deposit {d['path']} sha256={d['sha256']} extracted={d.get('extracted')}\n")
        fh.write("v1.0 recomputed: " + res["verdict_line"] + "\n")
        fh.write(line + "\n\n")
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
