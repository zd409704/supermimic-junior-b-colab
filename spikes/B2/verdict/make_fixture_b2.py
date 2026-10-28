#!/usr/bin/env python3
"""Synthesise P5 B2 deposit archives (.tgz) in the packets/P5/BUNDLE_CONTRACT.md layout, for testing verdict_b2.py.

Stdlib only. Reuses the sealed B0 fixture writer (spikes/B0/verdict/make_fixture.py: genuine TFRecord event files
with masked CRC32C, trainer logs in the real format, sidecars, harness/attempt records, tgz writer). Adds the P5
pieces: staged-checkpoint identity file, U eval executions whose mask-0.00 JSONs are byte copies of the real P4
it-1600 files (so U-REPRO is checked against the sealed P4 deposit tree), 7-condition evals with mask-stream
files (.npz written as numpy.savez would: zip of a v1 .npy, uint8), PERM JSONs and P5 meta files.

Mask streams: for each seed, a master stream of uniform scores (random.Random(seed)); f = 0.10 takes the top 3,
f = 0.20 the top 6 of the same scores (so the masks nest), and each run's stream is the first `calls` calls of
the master stream, with calls = the maximum clip steps of that condition's JSON (the benchmark loop count).

Usage as a script: python -I make_fixture_b2.py <outdir>   (one clean deposit + seal log)
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import os
import random
import struct
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
_spec = importlib.util.spec_from_file_location("make_fixture_b0", os.path.join(ROOT, "spikes", "B0", "verdict", "make_fixture.py"))
mf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mf)

P4_OPEN = os.path.join(ROOT, "logs", "xn4090", "2026-10-26", "open-b0-20261026-0919")
TARBALL_SHA = "b2b2" * 16
GPU = "NVIDIA GeForce RTX 4090"
DESCRIPTOR_SHA = mf.DESCRIPTOR_SHA
CLIPS = mf.CLIPS
MASK_SEEDS = (7100, 7101, 7102)
FRACS = ("0.10", "0.20")
mf.RATE["mlp_mind"] = 0.74
mf.PARAMS["mlp_mind"] = 467491
P4_SIZES = {"attention": 164415878, "mlp_matched": 164427663}
P4_SIDECAR = {
    "b0_attention_s0_a1": "cc9cac5864d7845578975e2dd3883b53ea8705201ae7a9de55ac0abdadaa2767",
    "b0_attention_s1_a1": "9085130f54e0ff9d568f075b7b2439d53c02a9437c8352a66fea64fcb2b30d09",
    "b0_attention_s2_a1": "b84b39c174c1a18895b7f66118976039fdaec8c7304c788453c3f951f752edae",
    "b0_mlp_matched_s0_a1": "e08618782fbf5ca107a74bd81494194055fbd50edb43b8eb528b134bbdca370a",
    "b0_mlp_matched_s1_a1": "9a8a0e443aae59ab55ca82621892804c0ad5f1807302231df6c3a89b4dee83d0",
    "b0_mlp_matched_s2_a1": "365096f41c67c789a7d9efc94c630ee259dc10ca5a2070a12cfc3c3098dd1641",
}
U_AIDS = tuple("b0_%s_s%d_a1" % (arm, s) for s in (0, 1, 2) for arm in ("attention", "mlp_matched"))


# ------------------------------------------------------------------------------------------ mask streams
_MASTER = {}


def master(seed, calls):
    """List of calls; each call = 4 rows of 29 scores."""
    cur = _MASTER.get(seed)
    if cur is None or len(cur[1]) < calls:
        rng = random.Random(seed)
        rows = [[[rng.random() for _ in range(29)] for _ in range(4)] for _ in range(max(calls, 2000))]
        _MASTER[seed] = cur = (rng, rows)
    return cur[1][:calls]


def mask_rows(scores, k):
    out = []
    for row in scores:
        top = sorted(range(29), key=lambda j: -row[j])[:k]
        out.append([j in top for j in range(29)])
    return out


def pack_row(bits):
    b = bytearray(4)
    for j, v in enumerate(bits):
        if v:
            b[j // 8] |= 0x80 >> (j % 8)
    return bytes(b)


def npy_bytes(shape, body):
    hdr = "{'descr': '|u1', 'fortran_order': False, 'shape': %s, }" % (repr(tuple(shape)),)
    pad = 64 - ((10 + len(hdr) + 1) % 64)
    hdr = hdr + " " * pad + "\n"
    return b"\x93NUMPY\x01\x00" + struct.pack("<H", len(hdr)) + hdr.encode("latin1") + body


def stream_files(seed, f, calls, tamper=None):
    k = 3 if f == "0.10" else 6
    body = b""
    for ci, call in enumerate(master(seed, calls)):
        rows = mask_rows(call, k)
        if tamper == "flip" and ci == 5:
            rows[0] = rows[0][1:] + rows[0][:1]
        if tamper == "k" and ci == 3:
            rows[1][[j for j in range(29) if not rows[1][j]][0]] = True
        body += b"".join(pack_row(r) for r in rows)
    shape = (calls, 4, 4) if calls else (0, 0, 0)
    zb = io.BytesIO()
    with zipfile.ZipFile(zb, "w", zipfile.ZIP_STORED) as z:
        z.writestr("packed.npy", npy_bytes(shape, body))
    meta = {"seed": seed if tamper != "seed" else seed + 1, "frac": float(f), "k": k, "calls": calls,
            "rows_per_call": 4, "num_joints": 29, "true_per_row": [k], "fracs_seen": [float(f)],
            "devices": ["cuda:0"], "packed_shape": list(shape), "sha256": hashlib.sha256(body).hexdigest()}
    return zb.getvalue(), json.dumps(meta, indent=1).encode()


def empty_stream():
    zb = io.BytesIO()
    with zipfile.ZipFile(zb, "w", zipfile.ZIP_STORED) as z:
        z.writestr("packed.npy", npy_bytes((0, 0, 0), b""))
    meta = {"seed": 0, "frac": 0.0, "k": 0, "calls": 0, "rows_per_call": [], "num_joints": [], "true_per_row": [],
            "packed_shape": [0, 0, 0], "sha256": hashlib.sha256(b"").hexdigest()}
    return zb.getvalue(), json.dumps(meta, indent=1).encode()


# ------------------------------------------------------------------------------------------ eval JSONs
def json_from(r_h, steps, failed=True):
    terms = {"motion_global_root_pos": 0.003, "motion_body_pos": 0.0135, "action_rate_l2": -0.0043}
    clips = [{"name": n, "frames": 6000, "steps": s, "norm_return": r_h, "failed": failed, "fail_step": s if failed else -1,
              "terms": dict(terms)} for n, s in zip(CLIPS, steps)]
    return {"summary": {"clips": 4, "failed": 4 if failed else 0, "mean_norm_return": r_h,
                        "step_weighted_norm_return": r_h, "terms": terms}, "clips": clips}


def p4_json(aid, f):
    run = aid[:-3]
    arm = "attention" if "_attention_" in aid else "mlp_matched"
    p = os.path.join(P4_OPEN, "logs", "eval", aid, "it0001600", "exec1", "%s_%s_mask%s.json" % (run, arm, f))
    with open(p, "rb") as fh:
        return fh.read()


def eval_exec_files(d, run, arm, ckpt, it, r0, rho, steps0, steps_off, mask0_bytes=None, tamper=None, exit_code=0,
                    rstep=None, rstep0=None):
    """{rel: bytes} for one exec dir. rho: {f: retention}; steps_off: {f: offset per seed index}."""
    files = {}
    conds = [("0.00", 0)] + ([(f, s) for s in MASK_SEEDS for f in FRACS] if it == 1600 else [])
    lines = ["[p5_eval] argv p5_eval_entry.py --config x --ckpt %s --out-dir %s" % (ckpt, d.rstrip("/"))]
    for f, s in conds:
        c = "mask%s_ms%d" % (f, s)
        lines.append("[eval_entry] eval_benchmark.py --ckpt %s --npz-dir data/npz/lafan1_smoke --num-envs 64 --out "
                     "%s%s_%s_mask%s.json" % (ckpt, d, run, arm, f))
        if f == "0.00":
            if mask0_bytes is not None:
                files[d + "%s_%s_%s.json" % (run, arm, c)] = mask0_bytes
            else:
                j0 = json_from(r0, steps0)
                if rstep0 is not None:
                    j0["summary"]["mean_norm_return"] = rstep0
                files[d + "%s_%s_%s.json" % (run, arm, c)] = json.dumps(j0).encode()
            npz, js = empty_stream()
        else:
            si = MASK_SEEDS.index(s)
            steps = [500 + steps_off[f] + 7 * si + 3 * i for i in range(4)]
            jd = json_from(r0 * rho[f], steps)
            if rstep is not None:
                jd["summary"]["mean_norm_return"] = rstep[f]
            files[d + "%s_%s_%s.json" % (run, arm, c)] = json.dumps(jd).encode()
            t = tamper.get((f, s)) if tamper else None
            calls = max(steps) + (1 if t == "calls" else 0)
            npz, js = stream_files(s, f, calls, tamper=t)
        files[d + "maskstream_%s.npz" % c] = npz
        files[d + "maskstream_%s.json" % c] = js
    lines.append("exit=%d" % exit_code)
    files[d + "eval.log"] = ("\n".join(lines) + "\n").encode()
    return files


# ------------------------------------------------------------------------------------------ U runs
def u_spec(aid, **kw):
    arm = "attention" if "_attention_" in aid else "mlp_matched"
    s = {"aid": aid, "arm": arm, "rho": {"0.10": 0.52, "0.20": 0.30} if arm == "attention" else {"0.10": 0.86, "0.20": 0.76},
         "steps_off": {"0.10": 40, "0.20": 10} if arm == "attention" else {"0.10": 25, "0.20": 5},
         "repro_break": False, "evals": True, "perm": 2.1e-6 if arm == "attention" else 5.8, "tamper": None,
         "exec1_fail": False, "rstep": None}
    s.update(kw)
    return s


def u_files(spec):
    aid, arm = spec["aid"], spec["arm"]
    run = aid[:-3]
    ID = "b2u_" + aid
    f = {}
    m0 = p4_json(aid, "0.00")
    jd = json.loads(m0)
    r0 = mf_rh(jd["clips"])
    if spec["repro_break"]:
        jd["clips"][0]["steps"] += 1
        m0 = json.dumps(jd).encode()
    ckpt = "/content/p5_p4ckpts/logs/%s/ckpt_0001600.pt" % run
    if spec["evals"]:
        k = 1
        if spec["exec1_fail"]:
            d = "logs/eval/%s/it0001600/exec1/" % ID
            bad = eval_exec_files(d, run, arm, ckpt, 1600, r0, spec["rho"], None, spec["steps_off"], m0, exit_code=1)
            bad = {r: v for r, v in bad.items() if "ms7102" not in r}
            f.update(bad)
            k = 2
        d = "logs/eval/%s/it0001600/exec%d/" % (ID, k)
        f.update(eval_exec_files(d, run, arm, ckpt, 1600, r0, spec["rho"], None, spec["steps_off"], m0,
                                 tamper=spec["tamper"], rstep=spec["rstep"]))
    if spec["perm"] is not None:
        f["meta/perm_%s.json" % ID] = perm_json(ID, arm, spec["perm"], role="gate" if arm == "attention" else "report")
    return f


def mf_rh(clips):
    return sum(c["norm_return"] * min(c["steps"], 500) for c in clips) / 2000.0


def perm_json(ID, arm, rel, role="report", used=0.0):
    return json.dumps({"id": ID, "role": role, "mode": "upstream", "arm": arm, "rel_err_tf32off": rel,
                       "rel_err_default": rel * 1.1, "rel_err_masked": rel * 0.9, "pass": rel < 1e-4, "threshold": 1e-4,
                       "auto_mask_frac_used": used, "auto_mask_frac_loaded": 0.1}).encode()


# ------------------------------------------------------------------------------------------ new runs
def t_spec(aid, **kw):
    """aid: b2mt_<arm>_s<seed>_a<N> or b2idx_attention_s<seed>_a<N>."""
    base = mf.default_attempt(aid)
    arm = base["arm"]
    s = dict(base)
    s.update({"r0": 0.30 if arm == "attention" else 0.10,
              "rho": {"0.10": 0.60, "0.20": 0.40} if arm == "attention" else {"0.10": 0.80, "0.20": 0.70},
              "steps_off": {"0.10": 33, "0.20": 12} if arm == "attention" else {"0.10": 20, "0.20": 2},
              "perm": (2.5e-6 if arm == "attention" and base["tag"] == "b2mt" else 4.9),
              "train_mask_frac": 0.1 if base["tag"] == "b2mt" else 0.0,
              "id_mode": "index" if base["tag"] == "b2idx" else "morph", "params": None, "descriptor": DESCRIPTOR_SHA,
              "updates_bump": 0, "argv_extra": [], "tamper": None, "evals_b2": True, "skip_curve": False,
              "rstep0": None})
    s.update(kw)
    s["evals"] = False  # B0-format evals off; B2 evals written below
    return s


def t_files(spec):
    files = mf.attempt_files(spec)
    aid = spec["aid"]
    run = "%s_%s_s%d" % (spec["tag"], spec["arm"], spec["seed"])
    adir = "logs/attempts/%s/" % aid
    if adir + "junior_policy.json" in files:
        sd = json.loads(files[adir + "junior_policy.json"])
        sd["train_mask_frac"] = spec["train_mask_frac"]
        sd["attention"] = {"d_model": 128, "num_heads": 4, "num_self_attn_layers": 1, "query_hidden": [256],
                           "readout_hidden": [256, 128], "descriptor": "v2", "id_mode": spec["id_mode"],
                           "morphology": "upstream_mjmodel"}
        sd["params"] = spec["params"] or mf.PARAMS[spec["arm"]]
        if spec["arm"] == "mlp_mind":
            sd["mlp_hidden"] = [376, 188, 94, 47]
            sd.pop("descriptor", None)
        else:
            sd["descriptor"] = {"version": "v2", "sha256": spec["descriptor"]}
        sd["argv"] = argv_b2(spec)
        files[adir + "junior_policy.json"] = json.dumps(sd, indent=2).encode()
    log = files["logs/train_%s.log" % aid].decode()
    log = log.replace(" ".join(mf.argv_for(spec)), " ".join(argv_b2(spec)))
    files["logs/train_%s.log" % aid] = log.encode()
    if spec["updates_bump"]:
        tbk = [k for k in files if "/tb/events.out.tfevents." in k and k.startswith(adir)][0]
        sp = copy.deepcopy(spec)
        orig = mf._updates
        mf._updates = lambda it: float(orig(it) + (spec["updates_bump"] if it == 1600 else 0))
        try:
            files[tbk] = mf.event_file_bytes(sp)
        finally:
            mf._updates = orig
    att = files["meta/attempt_%s.txt" % aid].decode().replace("b0_microbench.yaml",
                                                                "b2_mtrain.yaml" if spec["tag"] == "b2mt" else "b2_idx.yaml")
    files["meta/attempt_%s.txt" % aid] = att.encode()
    completed = spec["outcome"] == "completed"
    if completed and spec["evals_b2"]:
        for it in (400, 800, 1200, 1600):
            if spec["skip_curve"] and it != 1600:
                continue
            d = "logs/eval/%s/it%07d/exec1/" % (aid, it)
            ckpt = "logs/%s/ckpt_%07d.pt" % (run, it)
            r0 = spec["r0"] * {400: 0.5, 800: 0.7, 1200: 0.9, 1600: 1.0}[it]
            files.update(eval_exec_files(d, run, spec["arm"], ckpt, it, r0, spec["rho"], [520, 505, 610, 530],
                                         spec["steps_off"], tamper=spec["tamper"],
                                         rstep0=spec["rstep0"] if it == 1600 else None))
    if completed and spec["perm"] is not None:
        role = "gate" if spec["tag"] == "b2mt" and spec["arm"] == "attention" else "report"
        files["meta/perm_%s.json" % aid] = perm_json(aid, spec["arm"], spec["perm"], role=role)
    return files


def argv_b2(spec):
    run = "%s_%s_s%d" % (spec["tag"], spec["arm"], spec["seed"])
    a = ["--run-name", run, "--seed", str(spec["seed"]), "--data.npz-dir", "data/npz/lafan1_smoke",
         "--env.num-envs", "512", "--policy-trainer.batch-size", "512", "--policy-trainer.horizon", "16",
         "--policy-trainer.compile", "None", "--schedule.max-hours", "1.5", "--schedule.checkpoint-interval", "400",
         "--schedule.log-interval", "50", "--env.anchor-obs"]
    return a + list(spec["argv_extra"])


# ------------------------------------------------------------------------------------------ deposit
def identity_text(root="/content/SuperMimic-Reproduced", size_break=None, copy_break=None):
    L = ["# P4 checkpoint identity (PLAN §2.2 / §4.1 step 0), 2026-10-27T01:00:00Z",
         "candidate_root=%s match=true" % root, "root=%s" % root]
    src, dst, ss, sd_ = [], [], [], []
    for aid in sorted(P4_SIDECAR):
        run = aid[:-3]
        arm = "attention" if "_attention_" in aid else "mlp_matched"
        size = P4_SIZES[arm] + (1 if aid == size_break else 0)
        ck_sha = hashlib.sha256(("ckpt-" + aid).encode()).hexdigest()
        for base, lst, shl in ((root, src, ss), ("/content/p5_p4ckpts", dst, sd_)):
            ck = "%s/logs/%s/ckpt_0001600.pt" % (base, run)
            sc = "%s/logs/%s/junior_policy.json" % (base, run)
            lst.append("-rw-r--r-- 1 muchuan muchuan %d Oct 26 07:30 %s" % (size, ck))
            lst.append("-rw-r--r-- 1 muchuan muchuan 21000 Oct 26 07:30 %s" % sc)
            c_sha = ck_sha if not (base != root and aid == copy_break) else "0" * 64
            shl.append("%s  %s" % (c_sha, ck))
            shl.append("%s  %s" % (P4_SIDECAR[aid], sc))
    L += ["## ls -l source"] + src + ["## ls -l copy"] + dst + ["## sha256 source"] + ss + ["## sha256 copy"] + sd_
    L.append("copy_equals_source=%s" % ("false" if copy_break else "true"))
    return "\n".join(L) + "\n"


def nvsmi(gpu=GPU):
    return (mf.NVSMI % gpu).encode()


def default_t_specs():
    specs = []
    for s in (0, 1, 2):
        specs += [t_spec("b2mt_attention_s%d_a1" % s), t_spec("b2mt_mlp_mind_s%d_a1" % s)]
    specs += [t_spec("b2idx_attention_s%d_a1" % s, r0=0.22) for s in (0, 1, 2)]
    return specs


def default_u_specs(**kw):
    return [u_spec(a, **kw) for a in U_AIDS]


def deposit_files(dep):
    """dep: {'part', 'u': [u_spec], 't': [t_spec], 'gpu', 'tarball_sha', 'session': {}, 'blocked': [codes],
    'identity': text|None, 'extra': {rel: bytes}, 'drop': [rel prefixes]}"""
    f = {}
    part = dep.get("part", 1)
    f["meta/tarball_sha256.txt"] = ("%s  /content/junior_b_colab-CR-B2-1.tgz\n" % dep.get("tarball_sha", TARBALL_SHA)).encode()
    f["meta/cpu_test_smoke.log"] = b"".join(b"SKIP x\nPASS t%d\n" % i if i < 3 else b"PASS t%d\n" % i for i in range(14))
    f["meta/cpu_test_check.txt"] = b"pass_lines=14 skip_before_pass=3 expected=14/3 ok=true\n"
    f["meta/cpu_test_p5.log"] = b"P5_PREP_TESTS pass=14 fail=0 total=14\nexit=0\n"
    f["meta/nvidia-smi.txt"] = nvsmi(dep.get("gpu", GPU))
    f["meta/pip-freeze.txt"] = b"torch==2.14.1\n"
    f["meta/env_drift.txt"] = dep.get("env_drift", b"")
    f["meta/torch_cuda.txt"] = b"cuda True 2.14.1\n"
    if dep.get("identity", True) is not None:
        f["meta/p4_ckpt_identity.txt"] = (dep["identity"] if isinstance(dep.get("identity"), str) else identity_text()).encode()
    sess = {"part": part, "venue": dep.get("venue", "xn4090"), "start_utc": "2026-10-27T01:00:00Z",
            "end_utc": "2026-10-27T05:00:00Z", "session_hours": "3.8", "prior_hours": "0", "total_hours": "3.8",
            "spend_cap_hours": "6", "spend_cap_hit": "false", "cells_remaining": "none"}
    sess.update(dep.get("session", {}))
    f["meta/session.txt"] = mf.kv(sess).encode()
    state = ["PART %d 2026-10-27T01:00:00Z" % part]
    for s in dep.get("u", []):
        state.append("UEVAL %s ok exec1" % s["aid"])
    for s in dep.get("t", []):
        state.append("ATTEMPT %s %s false %s" % (s["aid"], "completed" if s["outcome"] == "completed" else "INFRA",
                                                  str(s["outcome"] == "completed").lower()))
    state += dep.get("state_extra", [])
    f["meta/driver_state.txt"] = ("\n".join(state) + "\n").encode()
    f["meta/driver.log"] = b"[b2_driver] ok\n"
    f["meta/ckpt_dirs_ls.txt"] = b"## logs/attempts\n"
    f["deviations.md"] = b"- [driver] harness stop (B0 PLAN 4.3, SIGINT) used\n"
    if dep.get("blocked"):
        f["BLOCKED.md"] = "".join("BLOCKED_REASON=%s detail=fixture\n" % c for c in dep["blocked"]).encode()
    for s in dep.get("u", []):
        f.update(u_files(s))
    for s in dep.get("t", []):
        f.update(t_files(s))
    for pre in dep.get("drop", []):
        for k in [k for k in f if k.startswith(pre)]:
            del f[k]
    f.update(dep.get("extra", {}))
    return f


def build(outdir, deposits, seal=True, venue="xn4090", seal_skip=()):
    os.makedirs(outdir, exist_ok=True)
    paths, entries = [], []
    for i, dep in enumerate(deposits):
        name = "b2-20261027-%04d%s.tgz" % (500 + i, "" if dep.get("part", 1) == 1 else "-part%d" % dep["part"])
        p = os.path.join(outdir, name)
        sha = mf.write_tgz(p, deposit_files(dep), dep.get("extra_members"))
        paths.append(p)
        if seal and i not in seal_skip:
            entries.append((sha, "logs/xn4090/2026-10-27/" + name))
    sl = os.path.join(outdir, "seal.log")
    with open(sl, "w") as fh:
        fh.write("2026-10-26T10:48:30Z 1793011710 SEAL spikes/B2/PLAN.md 5d1f26f7... P5\n")
        for i, (sha, rel) in enumerate(entries):
            fh.write("2026-10-27T06:%02d:00Z %d DEPOSIT %s %s %s job=p5-b2-attempt1\n" % (i, 1793080000 + i, venue, sha, rel))
    return paths, sl


def clean():
    return {"part": 1, "u": default_u_specs(), "t": default_t_specs()}


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "fixture_b2_out"
    paths, sl = build(out, [clean()])
    print("\n".join(paths + [sl]))


if __name__ == "__main__":
    main()
