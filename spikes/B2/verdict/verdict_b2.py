#!/usr/bin/env python3
"""B2 machine verdict (spikes/B2/PLAN.md §3, §4.2-4.3, §5, §6, §7, §8, §9.2-9.4). Stdlib only; run with `python -I`.

Reads one or more sealed P5 deposit archives (`b2-*.tgz`), extracts them safely, classifies every new training
attempt from evidence, recomputes the U / T / ablation statistics, gates U-ID, U-REPRO, MS, B2-V-1..B2-V-4,
B2-L-1, B2-L-2 and PERM, applies the §7.3 ordered decision table, the §7.2 outcome table and the §8 combined gate.
Writes results.json, appends one block per deposit to runs.log, and prints exactly one `B2_VERDICT ...` line on
stdout. Diagnostics go to stderr.

Reuse: the sealed B0 verdict tool (`spikes/B0/verdict/verdict_b0.py`, sha256 9caa744a…, VERDICT-TOOL) is imported
unchanged for archive checks and extraction, tb event reading (CRC-checked, latest-wall-time dedupe), train-log
parsing, attempt classification (B0 PLAN §3.3 / §4.3, applied unchanged by B2 PLAN §4.2), the B0 V-1 full and
integrity checks, the B0 V-3 seam checks and the B0 V-4 JSON content checks. Its attempt-ID pattern is rebound
in-process to the P5 tags (`b2mt`, `b2idx`) and arms (`attention`, `mlp_mind`); its file bytes are not changed and
its sha256 is checked at start-up. Reading choices are listed in IMPLEMENTATION_NOTES.md.
"""
from __future__ import annotations

import argparse
import ast
import datetime as _dt
import hashlib
import importlib.util
import json
import math
import os
import re
import struct
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
B0_TOOL = os.path.join(HERE, "..", "..", "B0", "verdict", "verdict_b0.py")
B0_TOOL_SHA = "9caa744a65ef5206fd46f532c4d13529b7773d076ee725ee4cb98ec192774a3b"


def _load_b0():
    with open(B0_TOOL, "rb") as fh:
        got = hashlib.sha256(fh.read()).hexdigest()
    if got != B0_TOOL_SHA:
        raise SystemExit("[verdict_b2] sealed verdict_b0.py sha256 %s != %s" % (got, B0_TOOL_SHA))
    spec = importlib.util.spec_from_file_location("verdict_b0", B0_TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["verdict_b0"] = mod
    spec.loader.exec_module(mod)
    return mod


V0 = _load_b0()
# P5 attempt IDs (PLAN §4.2); rebinding the module-level pattern makes the sealed discover/analyse code see them
B2_AID_RE = re.compile(r"^(b2mt|b2idx)_(attention|mlp_mind)_s(\d+)_a(\d+)$")
V0.AID_RE = B2_AID_RE

TOOL_VERSION = "1.0"
PLAN_SHA = "5d1f26f776a3ea56c2becd3ec2fa2cf8e88bd62c43a20f79415a96e82a3da11d"
METHOD_SHA = "9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0"
BASE_TARBALL_SHA = "763867682e3cfa05ca8eb6382ffc9124be2347b898531c60b904061776c33bff"
P4_RESULTS_SHA = "76507d8a9488cd295add444d9e9463da1bf7ab62c2216733043c535f3c6f8d3d"
P4_DEPOSIT_SHA = "1f49118213d53538485303aa0b3f09bb5f068daeb06eb325045fd83a3118dde1"
DESCRIPTOR_SHA = "3c854f91eb3739e4077dfec354d27a33f7c00cf019eec993a8fb43b66b1e5fe3"
GPU_NAME = "NVIDIA GeForce RTX 4090"
UPDATES_AT_1600 = 624
ATTENTION_PARAMS = 464001
T_HORIZON = 500
G_U_FLOOR, G_T_FLOOR, R_FLOOR = 0.17, 0.10, 0.0393
KEYING_MASK0_FLOOR, KEYING_RHO_FLOOR = 0.05, 0.17
MASK_SEEDS = (7100, 7101, 7102)
FRACS = ("0.10", "0.20")
K_OF = {"0.10": 3, "0.20": 6}
PRIMARY_F = "0.20"
SEEDS = (0, 1, 2)
CKPTS = (400, 800, 1200, 1600)
PERM_THRESHOLD = 1e-4
REPRO_TOL = 1e-4
P4_ROOTS = ("/content/SuperMimic-Reproduced", "/data/muchuan/p4-b0-attempt1/workdir/SuperMimic-Reproduced")
STAGE_REL = "p5_p4ckpts/logs/%s/ckpt_0001600.pt"
# PLAN §2.2
P4_CKPTS = {
    "b0_attention_s0_a1": (164415878, "cc9cac5864d7845578975e2dd3883b53ea8705201ae7a9de55ac0abdadaa2767"),
    "b0_attention_s1_a1": (164415878, "9085130f54e0ff9d568f075b7b2439d53c02a9437c8352a66fea64fcb2b30d09"),
    "b0_attention_s2_a1": (164415878, "b84b39c174c1a18895b7f66118976039fdaec8c7304c788453c3f951f752edae"),
    "b0_mlp_matched_s0_a1": (164427663, "e08618782fbf5ca107a74bd81494194055fbd50edb43b8eb528b134bbdca370a"),
    "b0_mlp_matched_s1_a1": (164427663, "9a8a0e443aae59ab55ca82621892804c0ad5f1807302231df6c3a89b4dee83d0"),
    "b0_mlp_matched_s2_a1": (164427663, "365096f41c67c789a7d9efc94c630ee259dc10ca5a2070a12cfc3c3098dd1641"),
}
# PLAN §5.4: P4 it-1600 exec1 mask JSONs (relative to the P4 open tree)
P4_FILES = {
    ("b0_attention_s0_a1", "0.00"): "43e9b53ad5fac82ed53f1b098d301b803f8db22f81bfa82abc1b3e627a03372e",
    ("b0_attention_s0_a1", "0.10"): "dbb9dd73447cda185ac1381a1956f4d7744242e8fe77ba2035452215fe3f5226",
    ("b0_attention_s0_a1", "0.20"): "0a8ef07f08286f0de18c80d1e12224bfaca54a99f7f800baa08c6db383b74930",
    ("b0_attention_s1_a1", "0.00"): "f19668e005051fc2d0d1c27b9712841ede20f5bad9483833561116cbacd07983",
    ("b0_attention_s1_a1", "0.10"): "730167e02bfdf8c349faf103e25d0ce5d04198a889069ff5827e4fe91369dd46",
    ("b0_attention_s1_a1", "0.20"): "9a45bfd5c605485bd605b31d8ed8d3cc2c6495b524ba740cdaf8ce49c0bdf9a9",
    ("b0_attention_s2_a1", "0.00"): "7c90eaff64d7dba565a6702f56eb6901486ca3888dfce524f272b3221b87b97c",
    ("b0_attention_s2_a1", "0.10"): "0d4b1d2d8cf56e4c1ed54a4d5eef07145d27ac4582d46a8ab81b59d504e33571",
    ("b0_attention_s2_a1", "0.20"): "cf39ee6f36edd1a598267aa52cb3ac09a1c37147962472f6429b2e1bdb5a69b9",
    ("b0_mlp_matched_s0_a1", "0.00"): "3bfed0f146971edc76305a2ba11b865a44facbee4516adb5be70b8a16c689ca1",
    ("b0_mlp_matched_s0_a1", "0.10"): "28c919cfe62d1ae947da983f0417d9426d04340076bbafd85376340ce00d5aac",
    ("b0_mlp_matched_s0_a1", "0.20"): "d76731650b42d5746a3fca94be0a6feb3aa9b7fce27dd1a00684d66c8906395c",
    ("b0_mlp_matched_s1_a1", "0.00"): "9d2a56a1d1a0a999f5d3e60c0ce98483ef0f409da4ed0f2daeaf0e394cf18e2c",
    ("b0_mlp_matched_s1_a1", "0.10"): "36c013905108ab06a8fa96f770f6a2fa7b1f4b5908827375793f52891e8adede",
    ("b0_mlp_matched_s1_a1", "0.20"): "a923861af3a90ecb1f17f45613b4cdc3a1ef72ba3e5d08e9901a48a58b1f4b4f",
    ("b0_mlp_matched_s2_a1", "0.00"): "eeeb390d312079b1f44545fce69b85f9ff8159866010b3c4259bd177ab3044d5",
    ("b0_mlp_matched_s2_a1", "0.10"): "1e9212c86c40d67de496518b8ec1823bca4ed4127be246ac460ce579610cb416",
    ("b0_mlp_matched_s2_a1", "0.20"): "0faaceff6ff0539aa9a90e06d36f4af90c5173680044d458a172e5ddfeaf7e36",
}
# B2-V-2 (b) reference: upstream argv of P4 attention s0 (sidecar `argv` in deposit 1f491182…, sha256 cc9cac58…)
P4_ATT_S0_ARGV = ["--run-name", "b0_attention_s0", "--seed", "0", "--data.npz-dir", "data/npz/lafan1_smoke",
                  "--env.num-envs", "512", "--policy-trainer.batch-size", "512", "--policy-trainer.horizon", "16",
                  "--policy-trainer.compile", "None", "--schedule.max-hours", "1.5",
                  "--schedule.checkpoint-interval", "400", "--schedule.log-interval", "50", "--env.anchor-obs"]
U_IDS = tuple("b2u_b0_%s_s%d_a1" % (arm, s) for s in SEEDS for arm in ("attention", "mlp_matched"))
T_CELLS = tuple(("b2mt", arm, s) for s in SEEDS for arm in ("attention", "mlp_mind"))
IDX_CELLS = tuple(("b2idx", "attention", s) for s in SEEDS)

log = V0.log
read_text, kv_file, sha256_file, finite_num, mean, tf, fmt = (V0.read_text, V0.kv_file, V0.sha256_file, V0.finite_num,
                                                            V0.mean, V0.tf, V0.fmt)


# ----------------------------------------------------------------------------------------- small helpers
def sd(xs):
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def se2(a, b):
    """SE of a difference of means, arms independent (PLAN §5.2). None with fewer than 2 values in an arm."""
    if a is None or b is None or len(a) < 2 or len(b) < 2:
        return None
    return math.sqrt(sd(a) ** 2 / len(a) + sd(b) ** 2 / len(b))


def all_num(xs):
    return xs is not None and len(xs) > 0 and all(finite_num(x) for x in xs)


def cond_name(f, seed):
    return "mask%s_ms%d" % (f, seed)


def conds_for(it):
    return [("0.00", 0)] + ([(f, s) for s in MASK_SEEDS for f in FRACS] if it == 1600 else [])


def rh_of(clips):
    return sum(c["norm_return"] * min(c["steps"], T_HORIZON) for c in clips) / (4.0 * T_HORIZON)


def read_npz_uint8(path, name="packed"):
    """(shape, bytes) of a uint8 array stored by numpy.savez (stdlib zip + .npy v1/v2/v3 header)."""
    with zipfile.ZipFile(path) as z:
        data = z.read(name + ".npy")
    if data[:6] != b"\x93NUMPY":
        raise ValueError("not an .npy member")
    if len(data) < 12:
        raise ValueError("truncated .npy header")
    major = data[6]
    if major == 1:
        hl, off = struct.unpack("<H", data[8:10])[0], 10
    else:
        hl, off = struct.unpack("<I", data[8:12])[0], 12
    hdr = ast.literal_eval(data[off:off + hl].decode("latin1"))
    if not isinstance(hdr, dict) or not isinstance(hdr.get("shape"), tuple):
        raise ValueError("malformed .npy header")
    if hdr.get("descr") not in ("|u1", "<u1", ">u1", "u1") or hdr.get("fortran_order"):
        raise ValueError("unexpected npy header %s" % hdr)
    shape = tuple(int(x) for x in hdr["shape"])
    n = 1
    for x in shape:
        n *= x
    body = data[off + hl:off + hl + n]
    if len(body) != n:
        raise ValueError("truncated npy body")
    return shape, body


def popcount(bs):
    return sum(bin(b).count("1") for b in bs)


def guard(fn, *args):
    """Evidence check that cannot crash the tool: an exception becomes a failed check with the error recorded
    (gating for scored runs, report-only for the ablation, because the caller decides where the result goes)."""
    try:
        return fn(*args)
    except Exception as e:  # noqa: BLE001
        return {"pass": False, "problems": ["evidence could not be checked: %s: %s" % (type(e).__name__, e)]}


# ----------------------------------------------------------------------------------------- analysis
class B2Verdict(V0.Verdict):
    def __init__(self, a):
        super().__init__(a)
        self.u = {}
        self.ms_streams = {}  # (f, seed) -> {ID: (calls, rows, bytes_per_row, body)}

    # ------------------------------------------------------------- evals (PLAN §4.3, B2-V-4, MS inputs)
    def eval_exec(self, d, run, arm, it, expected_ckpt):
        """Content checks of one exec dir. Returns (problems, metrics per cond, streams per cond, exit)."""
        st = self.store
        probs = []
        evl = st.get(d + "eval.log")
        if evl is None:
            probs.append("eval.log missing")
            evtext = ""
        else:
            evtext = read_text(evl)
            ok, why = V0.ckpt_path_ok(evtext, expected_ckpt)
            if not ok:
                probs.append(why)
            n_lines = len(re.findall(r"^\[eval_entry\].*?--ckpt\s+\S+", evtext, flags=re.M))
            if n_lines != len(conds_for(it)):
                probs.append("%d [eval_entry] lines, expected %d" % (n_lines, len(conds_for(it))))
        m_exit = re.findall(r"^exit=(-?\d+)\s*$", evtext, flags=re.M)
        mets, streams = {}, {}
        for f, s in conds_for(it):
            c = cond_name(f, s)
            rel = d + "%s_%s_%s.json" % (run, arm, c)
            p = st.get(rel)
            if p is None:
                probs.append("%s: JSON missing" % c)
                continue
            try:
                jd = json.loads(read_text(p))
            except ValueError as e:
                probs.append("%s: bad JSON %s" % (c, e))
                continue
            p2 = V0.check_eval_json(jd)
            if p2:
                probs += ["%s: %s" % (c, x) for x in p2]
                continue
            mm = V0.mask_metrics(jd)
            mm["max_steps"] = max(cl["steps"] for cl in jd["clips"])
            mets[c] = mm
            streams[c] = {"json": st.get(d + "maskstream_%s.json" % c), "npz": st.get(d + "maskstream_%s.npz" % c)}
        stray = [r for r in st.ls(d) if r.count("/") == d.count("/") and re.search(r"_mask\d\.\d\d\.json$", r)]
        if stray:
            probs.append("unrenamed benchmark JSONs: %s" % stray)
        return probs, mets, streams, (int(m_exit[-1]) if m_exit else None)

    def expected_files(self, run, arm, it):
        out = []
        for f, s in conds_for(it):
            c = cond_name(f, s)
            out += ["%s_%s_%s.json" % (run, arm, c), "maskstream_%s.npz" % c, "maskstream_%s.json" % c]
        return out

    def eval_id(self, ID, run, arm, its, expected_fn):
        """Execution history (PLAN §4.2 eval cells) then content (B2-V-4). exec1 must exist; exec2 only if exec1
        exited non-zero or lacks an expected file; nothing beyond exec2. A history violation leaves no scored exec."""
        entry_all, complete = {}, True
        for it in its:
            itk = "it%07d" % it
            entry = {"scored_exec": None, "executions": {}, "history_problems": []}
            execs = sorted({r.split("/")[4] for r in self.store.ls("logs/eval/%s/%s/" % (ID, itk)) if r.count("/") >= 5})
            results = {}
            for ex in execs:
                d = "logs/eval/%s/%s/%s/" % (ID, itk, ex)
                probs, mets, streams, ex_code = self.eval_exec(d, run, arm, it, expected_fn(it))
                missing = [f for f in self.expected_files(run, arm, it) if self.store.get(d + f) is None]
                results[ex] = (probs, mets, streams, ex_code, missing)
                entry["executions"][ex] = {"exit": ex_code, "problems": probs, "missing_files": missing}
            hist = entry["history_problems"]
            extra = [ex for ex in execs if ex not in ("exec1", "exec2")]
            if extra:
                hist.append("executions beyond exec2 or misnamed: %s (PLAN §4.2: never a third)" % extra)
            if "exec2" in results:
                if "exec1" not in results:
                    hist.append("exec2 without exec1")
                else:
                    _p, _m, _s, c1, miss1 = results["exec1"]
                    if not ((c1 is not None and c1 != 0) or miss1):  # PLAN §4.2, read strictly (review r3)
                        hist.append("exec2 run although exec1 has every expected file and no recorded non-zero exit (exit=%s)" % c1)
            if execs and not hist:
                for ex in ("exec1", "exec2"):
                    if ex in results and not results[ex][0]:
                        entry["scored_exec"] = ex
                        entry["_mets"], entry["_streams"] = results[ex][1], results[ex][2]
                        break
            if entry["scored_exec"] is None:
                complete = False
            entry_all[itk] = entry
        return entry_all, complete

    def summarise_eval(self, entry):
        """Public eval.<it> block (PLAN §9.4) from a scored exec."""
        if entry.get("scored_exec") is None:
            return {"scored_exec": None, "executions": entry["executions"]}
        mets = entry["_mets"]
        out = {"scored_exec": entry["scored_exec"], "executions": entry["executions"]}
        base = mets["mask0.00_ms0"]
        out["mask0.00"] = {k: base[k] for k in ("r_h", "r_step", "cum", "surv_steps", "fail_count", "clips", "terms")}
        for f in FRACS:
            if cond_name(f, MASK_SEEDS[0]) not in mets:
                continue
            per = {}
            for s in MASK_SEEDS:
                m = mets[cond_name(f, s)]
                sj = self.stream_meta(entry["_streams"][cond_name(f, s)])
                per[str(s)] = {k: m[k] for k in ("r_h", "r_step", "cum", "surv_steps", "fail_count", "clips")}
                sha, calls = sj.get("sha256"), sj.get("calls")
                per[str(s)].update(maskstream_sha256=sha if isinstance(sha, str) else None,
                                   calls=calls if V0.is_int(calls) else None)
            rh = mean([per[str(s)]["r_h"] for s in MASK_SEEDS])
            rs = mean([per[str(s)]["r_step"] for s in MASK_SEEDS])
            blk = {"per_seed": per, "r_h": rh, "r_step": rs,
                   "rho_h": (rh / base["r_h"]) if base["r_h"] != 0 else None,
                   "rho_step": (rs / base["r_step"]) if base["r_step"] != 0 else None}
            den = base["r_h"] - R_FLOOR
            blk["rho_star_h"] = ((rh - R_FLOOR) / den) if den > 0.01 else None
            out["mask" + f] = blk
        return out

    def stream_meta(self, s):
        p = s.get("json") if s else None
        if not p:
            return {}
        try:
            d = json.loads(read_text(p))
        except ValueError:
            return {}
        return d if isinstance(d, dict) else {}

    def eval_attempt(self, aid, A):  # called by the sealed analyse_attempt for completed attempts
        run, arm = A["run"], A["arm"]
        raw, complete = self.eval_id(aid, run, arm, CKPTS, lambda it: "logs/%s/ckpt_%07d.pt" % (run, it))
        A["_eval_raw"] = raw
        A["_eval_complete"] = complete
        A["eval"] = {k: self.summarise_eval(v) for k, v in raw.items()}

    # ------------------------------------------------------------- U runs (eval-only)
    def analyse_u(self, ID):
        p4aid = ID[len("b2u_"):]
        run = p4aid[:-3]
        arm = "attention" if "_attention_" in p4aid else "mlp_matched"
        raw, complete = self.eval_id(ID, run, arm, (1600,), lambda it: STAGE_REL % run)
        U = {"tag": "b2u", "arm": arm, "seed": int(run[-1]), "attempt": None, "class": "eval_only",
             "scored": raw["it0001600"]["scored_exec"] is not None, "condition": "U", "p4_aid": p4aid,
             "_eval_raw": raw, "_eval_complete": complete,
             "eval": {k: self.summarise_eval(v) for k, v in raw.items()}}
        return U

    # ------------------------------------------------------------- U-ID / U-REPRO
    def u_id(self):
        out = {"pass": True, "per_deposit": {}}
        if not self.roots:
            out["pass"] = False
        for rec in self.roots:
            p = os.path.join(rec["root"], "meta", "p4_ckpt_identity.txt")
            ev = {"present": os.path.exists(p), "problems": []}
            if not ev["present"]:
                ev["problems"].append("meta/p4_ckpt_identity.txt missing")
            else:
                ev.update(self.parse_identity(read_text(p)))
            ev["pass"] = not ev["problems"]
            out["per_deposit"][rec["path"]] = ev
            if not ev["pass"]:
                out["pass"] = False
        return out

    def parse_identity(self, text):
        probs = []
        root = None
        sect = None
        ls_src, sha_src, sha_cp = {}, {}, {}
        copy_eq = None
        for ln in text.splitlines():
            if ln.startswith("root="):
                root = ln[5:].strip()
            elif ln.startswith("## "):
                sect = ln[3:].strip()
            elif ln.startswith("copy_equals_source="):
                copy_eq = ln.split("=", 1)[1].strip()
            elif sect == "ls -l source" and ln.strip():
                t = ln.split()
                if len(t) >= 9:
                    ls_src[t[-1]] = t[4]
            elif sect in ("sha256 source", "sha256 copy") and ln.strip():
                t = ln.split()
                if len(t) >= 2:
                    (sha_src if sect == "sha256 source" else sha_cp)[t[1]] = t[0]
        if root not in P4_ROOTS:
            probs.append("root %s is not a PLAN §2.2 candidate" % root)
        per = {}
        for aid, (size, ssha) in P4_CKPTS.items():
            run = aid[:-3]
            ck = "%s/logs/%s/ckpt_0001600.pt" % (root, run)
            sc = "%s/logs/%s/junior_policy.json" % (root, run)
            ckc = "/content/%s" % (STAGE_REL % run)
            scc = ckc.replace("ckpt_0001600.pt", "junior_policy.json")
            e = {"ckpt_size": ls_src.get(ck), "sidecar_sha256": sha_src.get(sc),
                 "ckpt_sha256_source": sha_src.get(ck), "ckpt_sha256_copy": sha_cp.get(ckc),
                 "sidecar_sha256_copy": sha_cp.get(scc)}
            ok = (e["ckpt_size"] == str(size) and e["sidecar_sha256"] == ssha and e["ckpt_sha256_source"] is not None
                  and e["ckpt_sha256_copy"] == e["ckpt_sha256_source"] and e["sidecar_sha256_copy"] == ssha)
            e["pass"] = ok
            if not ok:
                probs.append("%s identity mismatch %s" % (aid, e))
            per[aid] = e
        if copy_eq != "true":
            probs.append("copy_equals_source=%s" % copy_eq)
        return {"root": root, "per_ckpt": per, "copy_equals_source": copy_eq, "problems": probs}

    def p4_ref(self):
        """Load and sha-check the P4 it-1600 mask JSONs (PLAN §5.4)."""
        out, probs = {}, []
        for (aid, f), want in P4_FILES.items():
            run = aid[:-3]
            arm = "attention" if "_attention_" in aid else "mlp_matched"
            p = os.path.join(self.a.p4_open_tree, "logs", "eval", aid, "it0001600", "exec1", "%s_%s_mask%s.json" % (run, arm, f))
            if not os.path.isfile(p):
                probs.append("missing %s" % p)
                continue
            got = sha256_file(p)
            if got != want:
                probs.append("sha256 %s != %s for %s" % (got, want, p))
                continue
            out[(aid, f)] = json.loads(read_text(p))
        return out, probs

    def u_repro(self, U, ref, ref_probs):
        out = {"pass": not ref_probs, "reference_problems": ref_probs, "per_run": {}}
        for ID in U_IDS:
            p4aid = ID[len("b2u_"):]
            e = {"pass": False}
            r = ref.get((p4aid, "0.00"))
            ent = U[ID]["_eval_raw"]["it0001600"]
            mine = ent.get("_mets", {}).get("mask0.00_ms0") if ent.get("scored_exec") else None
            if r is None or mine is None:
                e["why"] = "reference missing" if r is None else "no scored P5 mask-0.00 eval"
            else:
                rc = {c["name"]: c for c in r["clips"]}
                mc = {c["name"]: c for c in mine["clips"]}
                clips = []
                ok = sorted(rc) == sorted(mc) and len(rc) == 4
                for n in sorted(set(rc) | set(mc)):
                    a, b = rc.get(n), mc.get(n)
                    if a is None or b is None:
                        clips.append({"name": n, "present": False})
                        ok = False
                        continue
                    d = abs(a["norm_return"] - b["norm_return"])
                    c_ok = a["steps"] == b["steps"] and a["failed"] == b["failed"] and d <= REPRO_TOL
                    ok = ok and c_ok
                    clips.append({"name": n, "steps_p4": a["steps"], "steps_p5": b["steps"], "failed_p4": a["failed"],
                                  "failed_p5": b["failed"], "abs_d_norm_return": d, "pass": c_ok})
                e = {"pass": ok, "clips": clips}
            out["per_run"][ID] = e
            U[ID]["repro"] = e
            if not e["pass"]:
                out["pass"] = False
        return out

    # ------------------------------------------------------------- MS
    def ms_check(self, runs_scored, runs_reported):
        """PLAN §7.1 MS over the scored it-1600 execs (gate set) and, separately, the reported set."""
        def collect(ids):
            res = {"pass": True, "per_condition": {}, "problems": []}
            for f in FRACS:
                for s in MASK_SEEDS:
                    c = cond_name(f, s)
                    rows = {}
                    for ID, R in ids.items():
                        ent = R["_eval_raw"].get("it0001600", {})
                        if ent.get("scored_exec") is None:
                            res["problems"].append("%s: no scored it1600 exec" % ID)
                            res["pass"] = False
                            continue
                        rows[ID] = self.one_stream(ID, ent, f, s, res)
                    # pairwise common-prefix equality (all against all)
                    ids_ok = [i for i, v in rows.items() if v is not None]
                    for i in range(len(ids_ok)):
                        for j in range(i + 1, len(ids_ok)):
                            a, b = rows[ids_ok[i]], rows[ids_ok[j]]
                            n = min(a["calls"], b["calls"])
                            sz = n * a["row_bytes"] * a["rows"]
                            if a["rows"] != b["rows"] or a["body"][:sz] != b["body"][:sz]:
                                res["problems"].append("%s: streams differ on common prefix %s vs %s" % (c, ids_ok[i], ids_ok[j]))
                                res["pass"] = False
                    res["per_condition"][c] = {ID: ({k: v[k] for k in ("calls", "rows", "sha256", "seed")} if v else None)
                                               for ID, v in rows.items()}
            # nesting within each run: f=0.10 subset of f=0.20, same seed, common prefix of calls
            for ID, R in ids.items():
                ent = R["_eval_raw"].get("it0001600", {})
                if ent.get("scored_exec") is None:
                    continue
                for s in MASK_SEEDS:
                    a = self._streams.get((ID, "0.10", s))
                    b = self._streams.get((ID, "0.20", s))
                    if not a or not b:
                        continue
                    n = min(a["calls"], b["calls"]) * a["rows"] * a["row_bytes"]
                    if any(x & ~y & 0xFF for x, y in zip(a["body"][:n], b["body"][:n])):
                        res["problems"].append("%s seed %d: f=0.10 mask not a subset of f=0.20" % (ID, s))
                        res["pass"] = False
            return res
        self._streams = {}
        gate = collect(runs_scored)
        rep = collect({**runs_scored, **runs_reported}) if runs_reported else None
        return gate, rep

    def one_stream(self, ID, ent, f, s, res):
        c = cond_name(f, s)
        sfiles = ent["_streams"].get(c) or {}
        js, npz = sfiles.get("json"), sfiles.get("npz")
        where = "%s %s %s" % (ID, ent["scored_exec"], c)
        if not js or not npz:
            res["problems"].append("%s: mask-stream file missing" % where)
            res["pass"] = False
            return None
        try:
            meta = json.loads(read_text(js))
            if not isinstance(meta, dict):
                raise ValueError("mask-stream JSON is not an object")
            shape, body = read_npz_uint8(npz)
        except Exception as e:  # noqa: BLE001  any malformed stream file is an MS problem, never a crash
            res["problems"].append("%s: unreadable mask stream (%s)" % (where, e))
            res["pass"] = False
            return None
        probs = []
        if len(shape) != 3:
            probs.append("packed shape %s" % (shape,))
            calls, rows, rb = 0, 0, 0
        else:
            calls, rows, rb = shape
        k = K_OF[f]
        # every field is type-checked before use: malformed metadata is an MS problem, never an exception
        if not (V0.is_int(meta.get("seed")) and meta.get("seed") == s):
            probs.append("seed %r != %d" % (meta.get("seed"), s))
        fr = meta.get("frac")
        if not (finite_num(fr) and abs(fr - float(f)) <= 1e-9):
            probs.append("frac %s != %s" % (meta.get("frac"), f))
        if rows != 4 or not (V0.is_int(meta.get("rows_per_call")) and meta.get("rows_per_call") == 4):
            probs.append("rows_per_call %s / shape rows %s != 4" % (meta.get("rows_per_call"), rows))
        if rb != 4:
            probs.append("bytes per row %s != 4 (29 joints packed)" % rb)
        if not (V0.is_int(meta.get("calls")) and meta.get("calls") == calls):
            probs.append("json calls %s != npz calls %s" % (meta.get("calls"), calls))
        if not isinstance(meta.get("sha256"), str) or hashlib.sha256(body).hexdigest() != meta["sha256"]:
            probs.append("sha256 of packed stream != recorded")
        if rb == 4:
            for i in range(calls * rows):
                row = body[i * rb:(i + 1) * rb]
                if popcount(row) != k or row[3] & 0x07:
                    probs.append("row %d (call %d) has %d True (k=%d) or pad bits set" % (i, i // max(rows, 1), popcount(row), k))
                    break
        mets = ent["_mets"].get(c)
        if mets is None or mets["max_steps"] != calls:
            probs.append("calls %s != benchmark loop count (max clip steps %s)" % (calls, mets and mets["max_steps"]))
        if probs:
            res["problems"] += ["%s: %s" % (where, p) for p in probs]
            res["pass"] = False
        rec = {"calls": calls, "rows": rows, "row_bytes": rb, "body": body, "sha256": meta.get("sha256"), "seed": meta.get("seed")}
        self._streams[(ID, f, s)] = rec
        return rec

    # ------------------------------------------------------------- PERM
    def perm(self, ID):
        p = self.store.get("meta/perm_%s.json" % ID)
        if p is None:
            return {"present": False, "pass": False, "rel_err_tf32off": None, "rel_err_default": None, "rel_err_masked": None}
        try:
            d = json.loads(read_text(p))
        except ValueError:
            return {"present": True, "pass": False, "why": "bad JSON"}
        if not isinstance(d, dict):
            return {"present": True, "pass": False, "why": "PERM JSON is not an object"}
        num = lambda x: x if finite_num(x) else None  # noqa: E731  non-finite reported values -> null
        r = d.get("rel_err_tf32off")
        ok = finite_num(r) and r < PERM_THRESHOLD and d.get("auto_mask_frac_used") == 0.0
        return {"present": True, "pass": bool(ok), "rel_err_tf32off": num(r), "rel_err_default": num(d.get("rel_err_default")),
                "rel_err_masked": num(d.get("rel_err_masked")), "auto_mask_frac_used": num(d.get("auto_mask_frac_used")),
                "role_recorded": d.get("role") if isinstance(d.get("role"), str) else None,
                "arm": d.get("arm") if isinstance(d.get("arm"), str) else None}

    # ------------------------------------------------------------- statistics
    def per_run_vals(self, R, f, key):
        e = R.get("eval", {}).get("it0001600", {})
        if key == "r_h0":
            return (e.get("mask0.00") or {}).get("r_h")
        return (e.get("mask" + f) or {}).get(key)

    def compare(self, ra, rb, f, floor):
        """Δρ, SE, margin; ΔR (abs) and ρ_step / ρ* means (PLAN §5.2, §5.3)."""
        def arr(Rs, key):
            xs = [self.per_run_vals(R, f, key) for R in Rs]
            return xs if all(finite_num(x) for x in xs) and xs else None
        out = {"n_a": len(ra), "n_b": len(rb)}
        for nm, key in (("rho", "rho_h"), ("abs", "r_h"), ("rstep", "rho_step"), ("star", "rho_star_h")):
            a, b = arr(ra, key), arr(rb, key)
            out[nm + "_a"], out[nm + "_b"] = a, b
            out[nm + "_bar_a"] = mean(a) if a else None
            out[nm + "_bar_b"] = mean(b) if b else None
            out[nm + "_delta"] = (out[nm + "_bar_a"] - out[nm + "_bar_b"]) if (a and b) else None
            out[nm + "_se"] = se2(a, b)
            se = out[nm + "_se"]
            out[nm + "_margin"] = max(floor, 2 * se) if se is not None else None
        return out

    @staticmethod
    def outcome(du, gu, t_ok, dt, gt):
        if du is None or gu is None or (t_ok and (dt is None or gt is None)):
            return None, {}  # an undefined input (with t_status ok) gives no outcome (PLAN §7.3 undefined retention)
        u_gain, u_def = du >= gu, du <= -gu
        t_kept = bool(t_ok and dt is not None and gt is not None and dt >= gt)
        t_def = bool(t_ok and dt is not None and gt is not None and dt <= -gt)
        if not u_gain:
            o = "NO_GAIN"
        elif not t_ok:
            o = "U_GAIN_T_UNEVALUABLE"
        elif t_kept:
            o = "ROBUSTNESS_GAIN"
        else:
            o = "ABSENCE_REPRESENTATION_ONLY"
        return o, {"u_gain": u_gain, "u_deficit": u_def, "t_gap_kept": t_kept, "t_deficit": t_def}

    # ------------------------------------------------------------- legacy (§5.5)
    def legacy(self, ref, probs):
        if probs:
            return {"mask_pairing": "unverified_global_rng", "available": False, "problems": probs}
        rows = {}
        for aid in P4_CKPTS:
            m = {f: ref[(aid, f)] for f in ("0.00", "0.10", "0.20")}
            rh = {f: rh_of(m[f]["clips"]) for f in m}
            rs = {f: m[f]["summary"]["mean_norm_return"] for f in m}
            den = rh["0.00"] - R_FLOOR
            rows[aid] = {"r_h_0.00": rh["0.00"], "r_h_0.10": rh["0.10"], "r_h_0.20": rh["0.20"],
                         "rho_h_0.10": rh["0.10"] / rh["0.00"] if rh["0.00"] else None,
                         "rho_h_0.20": rh["0.20"] / rh["0.00"] if rh["0.00"] else None,
                         "rho_step_0.20": rs["0.20"] / rs["0.00"] if rs["0.00"] else None,
                         "rho_star_h_0.20": (rh["0.20"] - R_FLOOR) / den if den > 0.01 else None,
                         "surv_0.00": sum(c["steps"] for c in m["0.00"]["clips"]),
                         "surv_0.20": sum(c["steps"] for c in m["0.20"]["clips"])}
        att = [rows["b0_attention_s%d_a1" % s] for s in SEEDS]
        mlp = [rows["b0_mlp_matched_s%d_a1" % s] for s in SEEDS]
        out = {"mask_pairing": "unverified_global_rng", "available": True, "per_run": rows, "means": {}}
        for k in rows["b0_attention_s0_a1"]:
            a, b = [r[k] for r in att], [r[k] for r in mlp]
            out["means"][k] = {"attention": mean(a) if all_num(a) else None, "mlp_matched": mean(b) if all_num(b) else None}
        for k, nm in (("rho_h_0.20", "delta_rho_h_0.20"), ("rho_h_0.10", "delta_rho_h_0.10"), ("r_h_0.20", "delta_r_h_0.20")):
            a, b = [r[k] for r in att], [r[k] for r in mlp]
            out[nm] = mean(a) - mean(b)
            out[nm + "_2se"] = 2 * se2(a, b)
        return out

    # ------------------------------------------------------------- run
    def run(self):
        a = self.a
        self.plan_sha = sha256_file(a.plan)
        self.facts = V0.parse_facts(a.facts)
        f5 = self.facts.get("F-5") or {}
        self.env_steps_per_iter = f5.get("env_steps_per_iter") if isinstance(f5, dict) else None
        self.f2_flag, self.lr05, self.f2_none = None, None, True
        self.ckpt_map = {}
        self.load_deposits()
        for aid in self.discover_attempts():
            try:
                self.attempts[aid] = self.analyse_attempt(aid)
            except Exception as e:  # noqa: BLE001  malformed evidence: the attempt is unreadable, never scored
                tag, arm, seed, n = B2_AID_RE.match(aid).groups()
                self.attempts[aid] = {"tag": tag, "arm": arm, "seed": int(seed), "attempt": int(n),
                                      "run": "%s_%s_s%s" % (tag, arm, seed), "class": "UNREADABLE", "diverged": False,
                                      "seams": {}, "eval": {}, "_eval_complete": False, "driver_class": None,
                                      "error": "%s: %s" % (type(e).__name__, e)}
        for ID in U_IDS:
            try:
                self.u[ID] = self.analyse_u(ID)
            except Exception as e:  # noqa: BLE001  unreadable U evidence: no scored exec (B2-V-4 false)
                self.u[ID] = {"tag": "b2u", "arm": "attention" if "_attention_" in ID else "mlp_matched",
                              "seed": int(ID[-4]), "attempt": None, "class": "eval_only", "scored": False,
                              "condition": "U", "p4_aid": ID[len("b2u_"):], "error": "%s: %s" % (type(e).__name__, e),
                              "_eval_raw": {"it0001600": {"scored_exec": None, "executions": {}}},
                              "_eval_complete": False, "eval": {"it0001600": {"scored_exec": None, "executions": {}}}}
        return self.decide_b2()

    def decide_b2(self):
        a = self.a
        At, U = self.attempts, self.u
        reasons, detail = [], []

        def block(code, why):
            if code not in reasons:
                reasons.append(code)
            detail.append("%s: %s" % (code, why))

        # ---- provenance and deposit checks
        if self.plan_sha != PLAN_SHA:
            block("plan_sha_mismatch", "PLAN sha256 %s != sealed %s" % (self.plan_sha, PLAN_SHA))
        if not a.deposit:
            block("deposit_check", "no deposit given")
        for p in self.deposit_problems:
            block("deposit_check", "%s: %s" % (p["path"], "; ".join(p["problems"])))
        if not self.roots:
            block("deposit_check", "no deposit could be opened")
        spend_cap_hit = False
        aborted_in = []
        for rec in self.roots:
            if tf(rec["session"].get("spend_cap_hit", "false")) or any(l.startswith("SPEND_CAP_HIT") for l in rec["driver_state"]):
                spend_cap_hit = True
            for code in rec["blocked_md"]:
                if code == "spend_cap":
                    spend_cap_hit = True
                elif code == "aborted":  # provenance only (review r3): the evidence gates decide
                    aborted_in.append(rec["path"])
                elif code == "R1_unresolved":
                    block("R1_unresolved", "BLOCKED.md in %s" % rec["path"])
                elif code == "tarball_sha_mismatch":
                    block("deposit_check", "BLOCKED.md tarball_sha_mismatch in %s" % rec["path"])
                elif code == "p4_ckpts_unavailable":
                    block("U-ID", "BLOCKED.md p4_ckpts_unavailable in %s" % rec["path"])
                else:
                    block("blocked_md:%s" % code, "BLOCKED.md in %s" % rec["path"])
            if rec["torch_cuda"] is not None and rec["torch_cuda"].split()[:2][-1:] == ["False"]:
                block("R1_unresolved", "meta/torch_cuda.txt says cuda False in %s" % rec["path"])
        venues = {a.venue} | {rec["session"].get("venue") or a.venue for rec in self.roots} | \
                 {rec["seal_venue"] for rec in self.roots if rec.get("seal_venue")}
        if venues != {"xn4090"}:
            block("venue_mismatch", "venues %s; PLAN §9.3 pre-registers XN-4090-GPU2 only" % sorted(venues))
        gpu_names = [rec.get("gpu_name") for rec in self.roots]
        gpu_ok = bool(gpu_names) and all(g == GPU_NAME for g in gpu_names)
        if self.roots and not gpu_ok:
            block("gpu_mismatch", "GPU names %s (need one model, %s)" % (gpu_names, GPU_NAME))

        # ---- cells and scored attempts (PLAN §4.2)
        cellinfo = {}
        for aid, A in At.items():
            cellinfo.setdefault((A["tag"], A["arm"], A["seed"]), []).append(aid)
        cells = {}
        for key in list(T_CELLS) + list(IDX_CELLS) + sorted(k for k in cellinfo if k not in T_CELLS and k not in IDX_CELLS):
            aids = sorted(cellinfo.get(key, []), key=lambda x: At[x]["attempt"])
            scored = next((x for x in aids if At[x]["class"] in ("completed", "DIV")), None)
            infra_n = sum(1 for x in aids[:2] if At[x]["class"] == "INFRA")
            notes = []
            # PLAN §4.2 / B0 §3.3 history: attempts a1..aN contiguous; only an INFRA attempt may be followed by
            # another; at most 2 attempts (INFRA cap). A violation leaves the cell without a scored attempt.
            hist = []
            nums = [At[x]["attempt"] for x in aids]
            if aids and nums != list(range(1, len(nums) + 1)):
                hist.append("attempt numbers %s are not a1..a%d" % (nums, len(nums)))
            if len(aids) > 2:
                hist.append("more than 2 attempts")
            for x in aids[:-1]:
                if At[x]["class"] != "INFRA":
                    hist.append("attempt after %s (class %s) is not allowed" % (x, At[x]["class"]))
            if hist:
                scored = None
            notes += hist
            if key not in T_CELLS and key not in IDX_CELLS:
                notes.append("cell not in the PLAN schedule (ignored)")
            cells[key] = {"attempts": aids, "scored": scored, "infra_cap": infra_n >= 2, "history_problems": hist,
                          "oom_seam": [x for x in aids if At[x]["class"] in ("OOM", "SEAM")], "notes": notes,
                          "diverged": bool(scored and At[scored]["diverged"])}
        for A in At.values():
            A["scored"] = False
        for key, ci in cells.items():
            if ci["scored"] and (key in T_CELLS or key in IDX_CELLS):
                At[ci["scored"]]["scored"] = True
            for x in ci["attempts"]:
                At[x]["condition"] = "T" if key in T_CELLS else ("ablation" if key in IDX_CELLS else "unscheduled")
        for key in T_CELLS:
            ci = cells[key]
            for x in ci["oom_seam"]:
                block(At[x]["class"], x)
            if ci["infra_cap"]:
                block("INFRA_cap", "%s_%s_s%d" % key)
            if ci["history_problems"]:
                block("attempt_history", "%s_%s_s%d: %s" % (key + ("; ".join(ci["history_problems"]),)))
        t_scored = {key: cells[key]["scored"] for key in T_CELLS}
        t_missing = [key for key, x in t_scored.items() if x is None]
        t_div = [x for x in t_scored.values() if x and At[x]["diverged"]]
        t_status = "diverged" if t_div else "ok"
        t_full = [x for x in t_scored.values() if x and not At[x]["diverged"]]
        idx_scored = {key: cells[key]["scored"] for key in IDX_CELLS}

        # ---- U-ID, U-REPRO
        uid = self.u_id()
        if not uid["pass"]:
            block("U-ID", "; ".join("%s: %s" % (k, v.get("problems")) for k, v in uid["per_deposit"].items()) or "no deposit")
        ref, ref_probs = self.p4_ref()
        urepro = self.u_repro(U, ref, ref_probs)
        if not urepro["pass"]:
            block("U-REPRO", "; ".join(k for k, v in urepro["per_run"].items() if not v["pass"]) or "; ".join(ref_probs))

        # ---- B2-V-1 (T; b2idx reported)
        def v1_of(aid):
            A = At[aid]
            ev = self.v1_integrity(A) if A["diverged"] else self.v1_full(A)
            return ev
        v1 = {"pass": not t_missing, "per_attempt": {}, "missing_cells": ["%s_%s_s%d" % k for k in t_missing],
              "reported_b2idx": {}}
        for aid in t_scored.values():
            if aid:
                v1["per_attempt"][aid] = guard(v1_of, aid)
                if not v1["per_attempt"][aid]["pass"]:
                    v1["pass"] = False
        for aid in idx_scored.values():
            if aid:
                v1["reported_b2idx"][aid] = guard(v1_of, aid)
        if not v1["pass"]:
            block("B2-V-1", "; ".join([k for k, v in v1["per_attempt"].items() if not v["pass"]] + v1["missing_cells"]))

        # ---- B2-V-2
        ref_norm, _ = self.normalise_argv({"argv": P4_ATT_S0_ARGV, "tag": "b0"})

        def v2_of(aid):
            A = At[aid]
            nrm, prob = self.normalise_argv(A)
            ev = {"updates_at_1600": A["updates_at_1600"],
                  "a_updates_624": (A["updates_at_1600"] == UPDATES_AT_1600) if not A["diverged"] else "exempt (diverged)",
                  "b_argv_identical": bool(nrm is not None and not prob and nrm == ref_norm),
                  "argv_normalised": " ".join(nrm or []) or None}
            ev["pass"] = (ev["a_updates_624"] is True or A["diverged"]) and ev["b_argv_identical"] and gpu_ok
            return ev
        v2 = {"pass": not t_missing and gpu_ok, "c_gpu": {"pass": gpu_ok, "names": gpu_names, "expected": GPU_NAME},
              "reference_argv_normalised": " ".join(ref_norm), "per_attempt": {}, "reported_b2idx": {}}
        for aid in t_scored.values():
            if aid:
                v2["per_attempt"][aid] = guard(v2_of, aid)
                if not v2["per_attempt"][aid]["pass"]:
                    v2["pass"] = False
        for aid in idx_scored.values():
            if aid:
                v2["reported_b2idx"][aid] = guard(v2_of, aid)
        if not v2["pass"]:
            block("B2-V-2", "; ".join(k for k, v in v2["per_attempt"].items() if not v["pass"]) or "missing cell / GPU")

        # ---- B2-V-3
        def v3_of(aid):
            A = At[aid]
            ev = self.v3_run(A, check_descriptor=(A["arm"] == "attention"))
            sc = A.get("_sidecar") or {}
            probs = list(ev["problems"])
            if not isinstance(sc, dict):
                probs.append("sidecar is not a JSON object")
                sc = {}
            att = sc.get("attention") or {}
            if not isinstance(att, dict):
                probs.append("sidecar attention block is not an object")
                att = {}
            if not sc:
                probs.append("sidecar missing")
            want_tmf = 0.1 if A["tag"] == "b2mt" else 0.0
            if sc.get("train_mask_frac") != want_tmf:
                probs.append("train_mask_frac %s != %s" % (sc.get("train_mask_frac"), want_tmf))
            want_id = "index" if A["tag"] == "b2idx" else "morph"
            if att.get("id_mode") != want_id:
                probs.append("attention.id_mode %s != %s" % (att.get("id_mode"), want_id))
            if sc.get("policy") != A["arm"]:
                probs.append("sidecar policy %s != %s" % (sc.get("policy"), A["arm"]))
            if A["arm"] == "attention" and A["descriptor_sha256"] != DESCRIPTOR_SHA:
                probs.append("descriptor sha256 %s != P4 %s" % (A["descriptor_sha256"], DESCRIPTOR_SHA))
            if A["arm"] == "mlp_mind":
                n = sc.get("params")
                if not (V0.is_int(n) and abs(n - ATTENTION_PARAMS) / ATTENTION_PARAMS <= 0.05):
                    probs.append("mlp_mind params %s not within 5%% of %d" % (n, ATTENTION_PARAMS))
                if not sc.get("mlp_hidden"):
                    probs.append("mlp_hidden missing")
            ev["problems"] = probs
            ev["pass"] = not probs
            ev["train_mask_frac"] = sc.get("train_mask_frac")
            ev["id_mode"] = att.get("id_mode")
            ev["params"] = sc.get("params")
            return ev
        v3 = {"pass": not t_missing, "per_attempt": {}, "reported_b2idx": {}}
        s3 = set()
        for aid in t_scored.values():
            if aid:
                v3["per_attempt"][aid] = guard(v3_of, aid)
                s3.add(str(At[aid]["seams"].get("S3")))
                if not v3["per_attempt"][aid]["pass"]:
                    v3["pass"] = False
        v3["S3_identical"] = len(s3) <= 1
        if not v3["S3_identical"]:
            v3["pass"] = False
        for aid in idx_scored.values():
            if aid:
                v3["reported_b2idx"][aid] = guard(v3_of, aid)
        if not v3["pass"]:
            block("B2-V-3", "; ".join(k for k, v in v3["per_attempt"].items() if not v["pass"]) or "missing cell / S3")

        # ---- B2-V-4 (U all; T non-diverged; b2idx reported)
        def v4_of(R, diverged=False):
            if diverged:
                return {"pass": True, "exempt": "diverged", "scored_exec": {k: v.get("scored_exec") for k, v in R.get("eval", {}).items()}}
            ok = bool(R.get("_eval_complete")) and bool(R.get("eval"))
            return {"pass": ok, "scored_exec": {k: v.get("scored_exec") for k, v in R.get("eval", {}).items()},
                    "problems": {k: {e: x["problems"] for e, x in v.get("executions", {}).items() if x["problems"]}
                                 for k, v in R.get("eval", {}).items()}}
        v4 = {"pass": not t_missing, "per_run": {}, "reported_b2idx": {}}
        for ID in U_IDS:
            v4["per_run"][ID] = guard(v4_of, U[ID])
        for aid in t_scored.values():
            if aid:
                A = At[aid]
                v4["per_run"][aid] = guard(v4_of, A, A["diverged"]) if A["class"] == "completed" or A["diverged"] else \
                    {"pass": False, "why": "not completed"}
        for aid in idx_scored.values():
            if aid:
                v4["reported_b2idx"][aid] = guard(v4_of, At[aid])
        if not all(v["pass"] for v in v4["per_run"].values()):
            v4["pass"] = False
        if not v4["pass"]:
            block("B2-V-4", "; ".join(k for k, v in v4["per_run"].items() if not v["pass"]) or "missing cell")

        # ---- MS (scored U and non-diverged T evals; b2idx and diverged-completed T reported)
        ms_gate_ids = {ID: U[ID] for ID in U_IDS}
        ms_gate_ids.update({aid: At[aid] for aid in t_full})
        ms_rep_ids = {aid: At[aid] for aid in idx_scored.values() if aid and not At[aid]["diverged"]
                      and At[aid].get("_eval_raw", {}).get("it0001600", {}).get("scored_exec")}
        ms_rep_ids.update({aid: At[aid] for aid in t_div if At[aid].get("_eval_raw", {}).get("it0001600", {}).get("scored_exec")})
        ms, ms_rep = self.ms_check(ms_gate_ids, ms_rep_ids)
        if not ms["pass"]:
            block("MS", "; ".join(ms["problems"][:10]))

        # ---- undefined retention
        rho_undef = []
        for ID in U_IDS:
            r0 = self.per_run_vals(U[ID], None, "r_h0")
            if r0 == 0:
                rho_undef.append(ID)
        for aid in t_full:
            if self.per_run_vals(At[aid], None, "r_h0") == 0:
                rho_undef.append(aid)
        for x in rho_undef:
            block("rho_undefined:%s" % x, "R_H(mask 0.00) = 0")

        # ---- PERM
        perm_gate_ids = ["b2u_b0_attention_s%d_a1" % s for s in SEEDS] + \
                        [aid for aid in t_full if At[aid]["arm"] == "attention"]
        perm = {"pass": True, "threshold": PERM_THRESHOLD, "gate": {}, "reported": {}}
        for ID in perm_gate_ids:
            perm["gate"][ID] = self.perm(ID)
            if not perm["gate"][ID]["pass"]:
                perm["pass"] = False
        rep_ids = ["b2u_b0_mlp_matched_s%d_a1" % s for s in SEEDS] + \
                  [aid for aid in At if aid not in perm_gate_ids and At[aid]["class"] == "completed"]
        for ID in rep_ids:
            perm["reported"][ID] = self.perm(ID)
        for ID in U_IDS:
            U[ID]["perm"] = perm["gate"].get(ID) or perm["reported"].get(ID)
        for aid, A in At.items():
            A["perm"] = perm["gate"].get(aid) or perm["reported"].get(aid)

        # ---- required set and spend cap (§7.3)
        req = {"u_evals": all(U[ID]["_eval_raw"]["it0001600"]["scored_exec"] for ID in U_IDS),
               "perm_present": all(perm["gate"][ID]["present"] for ID in perm_gate_ids),
               "t_cells": all(x is not None and (At[x]["diverged"] or At[x].get("_eval_complete")) for x in t_scored.values())}
        required_complete = all(req.values())
        if spend_cap_hit and not required_complete:
            block("spend_cap", "spend cap reached before the required set was complete %s" % req)

        # ---- L-1 / L-2 (T, only when t_status ok)
        l1_count = {}
        l1_per, l2_per = {}, {}
        for arm in ("attention", "mlp_mind"):
            c = 0
            for s in SEEDS:
                aid = t_scored.get(("b2mt", arm, s))
                if aid and not At[aid]["diverged"]:
                    l1_per[aid] = {"pass": At[aid]["l1_pass"], "c_train_first5": At[aid]["c_train_first5"],
                                   "c_train_last5": At[aid]["c_train_last5"]}
                    l2_per[aid] = {"pass": At[aid]["l2_pass"], "wm_loss_first5": At[aid]["wm_loss_first5"],
                                   "wm_loss_last5": At[aid]["wm_loss_last5"]}
                    c += At[aid]["l1_pass"] is True
            l1_count[arm] = c
        if t_status == "ok":
            l1 = all(l1_count[arm] >= 2 for arm in l1_count) and not t_missing
            l2 = bool(l2_per) and all(v["pass"] is True for v in l2_per.values()) and not t_missing
        else:
            l1 = l2 = None

        # ---- statistics
        u_att = [U["b2u_b0_attention_s%d_a1" % s] for s in SEEDS]
        u_mlp = [U["b2u_b0_mlp_matched_s%d_a1" % s] for s in SEEDS]
        t_att = [At[t_scored[("b2mt", "attention", s)]] for s in SEEDS if t_scored[("b2mt", "attention", s)]]
        t_mm = [At[t_scored[("b2mt", "mlp_mind", s)]] for s in SEEDS if t_scored[("b2mt", "mlp_mind", s)]]
        u_stats, t_stats, t_partial = {}, {}, {}
        for f in FRACS:
            cu = self.compare(u_att, u_mlp, f, G_U_FLOOR)
            u_stats["f" + f] = self.stat_block(cu, "attention", "mlp_matched", "g_u" if f == PRIMARY_F else None)
            if t_status == "ok" and not t_missing:
                ct = self.compare(t_att, t_mm, f, G_T_FLOOR)
                t_stats["f" + f] = self.stat_block(ct, "attention_mtrain", "mlp_mind_mtrain", "g_t" if f == PRIMARY_F else None)
            else:
                t_stats["f" + f] = self.stat_block(None, "attention_mtrain", "mlp_mind_mtrain", "g_t" if f == PRIMARY_F else None)
            pa = [R for R in t_att if not R["diverged"] and R.get("_eval_complete")]
            pm = [R for R in t_mm if not R["diverged"] and R.get("_eval_complete")]
            if t_status == "diverged" and len(pa) >= 2 and len(pm) >= 2:
                cp = self.compare(pa, pm, f, G_T_FLOOR)
                t_partial["f" + f] = dict(self.stat_block(cp, "attention_mtrain", "mlp_mind_mtrain", "g_t" if f == PRIMARY_F else None),
                                          n_attention_mtrain=len(pa), n_mlp_mind_mtrain=len(pm), report_only=True)
            elif t_status == "diverged":
                t_partial["f" + f] = {"n_attention_mtrain": len(pa), "n_mlp_mind_mtrain": len(pm), "report_only": True,
                                      "note": "n < 2 in an arm: aggregates null"}

        # ---- decision (§7.3)
        failing = []
        outcome, flags = None, {}
        sh_rstep = sh_abs = None
        if reasons:
            row, verdict = 1, "BLOCKED"
        elif not perm["pass"]:
            row, verdict = 2, "FAIL"
            failing = ["PERM"]
        elif t_status == "ok" and not (l1 and l2):
            row, verdict = 3, "FAIL"
            failing = [x for x, ok in (("B2-L-1", l1), ("B2-L-2", l2)) if not ok]
        else:
            row, verdict = 4, "PASS"
            pu, pt = u_stats["f" + PRIMARY_F], t_stats["f" + PRIMARY_F]
            outcome, flags = self.outcome(pu["delta_rho"], pu["g_u"], t_status == "ok", pt["delta_rho"], pt["g_t"])
            if outcome is None:  # guard: cannot happen when V-4 holds
                row, verdict = 1, "BLOCKED"
                reasons.append("B2-V-4")
                detail.append("B2-V-4: primary statistics not evaluable")
            else:
                sh_rstep, _ = self.outcome(pu["rstep_delta"], pu["rstep_margin"], t_status == "ok", pt["rstep_delta"], pt["rstep_margin"])
                sh_abs, _ = self.outcome(pu["delta_abs"], pu["abs_margin"], t_status == "ok", pt["delta_abs"], pt["abs_margin"])
        metric_disagreement = bool(outcome is not None and any(x is not None and x != outcome for x in (sh_rstep, sh_abs)))
        b2_gain = outcome == "ROBUSTNESS_GAIN"

        # ---- §8 combined gate
        b0_in, b0_src = None, {"path": a.p4_results, "sha256": None, "expected_sha256": P4_RESULTS_SHA}
        if os.path.isfile(a.p4_results):
            b0_src["sha256"] = sha256_file(a.p4_results)
            if b0_src["sha256"] == P4_RESULTS_SHA:
                b0_in = json.loads(read_text(a.p4_results)).get("b0_outcome")
        if b0_in in ("NONINFERIOR", "SUPERIOR"):
            gate = "Go"
        elif b0_in == "INCONCLUSIVE" and b2_gain:
            gate = "Go-with-caveat"
        elif b0_in == "INFERIOR" and not b2_gain:
            gate = "Kill"
        else:
            gate = "HumanLead"
        caveat = bool(outcome != "ROBUSTNESS_GAIN" or flags.get("u_deficit") or verdict != "PASS")

        # ---- ablation (§7.4)
        abl = self.ablation(cells, idx_scored, u_att, perm)

        # ---- env drift
        drift = []
        for rec in self.roots:
            p = os.path.join(rec["root"], "meta", "env_drift.txt")
            drift.append({"path": rec["path"], "present": os.path.exists(p),
                          "nonempty": os.path.exists(p) and os.path.getsize(p) > 0})

        pu, pt = u_stats["f" + PRIMARY_F], t_stats["f" + PRIMARY_F]
        res = {
            "tool": {"name": "verdict_b2.py", "version": TOOL_VERSION, "sha256": sha256_file(os.path.abspath(__file__)),
                     "reuses": {"verdict_b0.py": B0_TOOL_SHA}},
            "plan_sha256": self.plan_sha, "method_sha256": a.method_sha, "tarball_sha256": a.tarball_sha,
            "base_tarball_sha256": BASE_TARBALL_SHA, "p4_results_sha256": P4_RESULTS_SHA, "p4_deposit_sha256": P4_DEPOSIT_SHA,
            "venue": a.venue, "gpu_name": gpu_names[0] if gpu_names and len(set(gpu_names)) == 1 else None,
            "deposits": [{"path": d["path"], "sha256": d["sha256"], "seal_line": d["seal_line"], "part": d.get("part"),
                          "extracted": d["extracted"], "problems": d["problems"]} for d in self.deposits],
            "env_drift": {"drift": any(x["nonempty"] for x in drift), "per_deposit": drift, "diff_path": "meta/env_drift.txt"},
            "verdict": verdict, "decision_row": row, "failing_ids": failing, "blocked_reason": reasons,
            "blocked_detail": detail,
            "b2_outcome": outcome, "b2_gain": b2_gain, "u_gain": flags.get("u_gain"), "u_deficit": flags.get("u_deficit"),
            "t_gap_kept": flags.get("t_gap_kept"), "t_deficit": flags.get("t_deficit"), "t_status": t_status,
            "t_diverged_attempts": t_div,
            "u": u_stats, "t": t_stats, "t_partial": t_partial or None,
            "T": T_HORIZON, "g_u_floor": G_U_FLOOR, "g_t_floor": G_T_FLOOR, "r_floor": R_FLOOR,
            "mask_seeds": list(MASK_SEEDS), "primary_f": float(PRIMARY_F),
            "shadow_outcome_rstep": sh_rstep, "shadow_outcome_abs": sh_abs, "metric_disagreement": metric_disagreement,
            "rho_undefined": rho_undef,
            "b0_outcome_input": {"value": b0_in, "source": b0_src}, "gate_b1": gate, "caveat_required": caveat,
            "ablation_idx": abl,
            "legacy_p4_m10": self.legacy(ref, ref_probs),
            "scored_set": {"U": list(U_IDS), "T": {"%s_%s_s%d" % k: v for k, v in t_scored.items()},
                           "ablation": {"%s_%s_s%d" % k: v for k, v in idx_scored.items()}},
            "required_set": dict(req, complete=required_complete), "spend_cap_hit": spend_cap_hit,
            "aborted_deposits": aborted_in,
            "cells": {"%s_%s_s%d" % k: v for k, v in sorted(cells.items())},
            "duplicate_members_across_deposits": sorted(set(self.store.dups)),
            "gates": {"U-ID": uid, "U-REPRO": urepro, "MS": dict(ms, reported=ms_rep), "B2-V-1": v1, "B2-V-2": v2,
                      "B2-V-3": v3, "B2-V-4": v4,
                      "B2-L-1": {"pass": l1, "evaluated": t_status == "ok", "seeds_passing": l1_count, "per_attempt": l1_per},
                      "B2-L-2": {"pass": l2, "evaluated": t_status == "ok", "per_attempt": l2_per},
                      "PERM": perm},
            "drho_u": pu["delta_rho"], "g_u": pu["g_u"], "drho_t": pt["delta_rho"], "g_t": pt["g_t"],
        }
        res["runs"] = {}
        for ID in U_IDS:
            R = U[ID]
            res["runs"][ID] = {"tag": "b2u", "arm": R["arm"], "seed": R["seed"], "attempt": None, "class": "eval_only",
                               "scored": R["scored"], "condition": "U", "p4_aid": R["p4_aid"],
                               "ckpt_identity": {d: v.get("per_ckpt", {}).get(R["p4_aid"]) for d, v in uid["per_deposit"].items()},
                               "repro": R.get("repro"), "perm": R.get("perm"), "eval": R["eval"]}
        for aid, A in sorted(At.items()):
            pub = self.public_attempt(A)
            pub.update(condition=A.get("condition"), perm=A.get("perm"), eval=A.get("eval", {}))
            res["runs"][aid] = pub
        return res

    def stat_block(self, c, na, nb, gkey):
        keys = ("rho_bar_h_" + na, "rho_bar_h_" + nb, "delta_rho", "se", "delta_abs", "se_abs",
                "rho_step_bar_" + na, "rho_step_bar_" + nb, "rho_star_bar_" + na, "rho_star_bar_" + nb,
                "r_bar_h_" + na, "r_bar_h_" + nb, "rstep_delta", "rstep_se", "rstep_margin", "abs_margin")
        if c is None:
            out = {k: None for k in keys}
            if gkey:
                out[gkey] = None
            return out
        out = {"rho_bar_h_" + na: c["rho_bar_a"], "rho_bar_h_" + nb: c["rho_bar_b"], "delta_rho": c["rho_delta"],
               "se": c["rho_se"], "delta_abs": c["abs_delta"], "se_abs": c["abs_se"],
               "r_bar_h_" + na: c["abs_bar_a"], "r_bar_h_" + nb: c["abs_bar_b"],
               "rho_step_bar_" + na: c["rstep_bar_a"], "rho_step_bar_" + nb: c["rstep_bar_b"],
               "rho_star_bar_" + na: c["star_bar_a"], "rho_star_bar_" + nb: c["star_bar_b"],
               "rstep_delta": c["rstep_delta"], "rstep_se": c["rstep_se"], "rstep_margin": c["rstep_margin"],
               "abs_margin": c["abs_margin"], "per_run_rho_" + na: c["rho_a"], "per_run_rho_" + nb: c["rho_b"]}
        if gkey:
            out[gkey] = c["rho_margin"]
        return out

    def ablation(self, cells, idx_scored, u_att, perm):
        At = self.attempts
        status, runs = {}, []
        for key, aid in idx_scored.items():
            name = "%s_%s_s%d" % key
            ci = cells[key]
            if aid is None:
                if ci.get("history_problems"):
                    status[name] = {"aid": ci["attempts"][-1], "status": "attempt_history: " + "; ".join(ci["history_problems"])}
                elif ci["oom_seam"]:
                    status[name] = {"aid": ci["oom_seam"][-1], "status": At[ci["oom_seam"][-1]]["class"]}
                elif ci["infra_cap"]:
                    status[name] = {"aid": ci["attempts"][-1], "status": "INFRA_cap"}
                else:
                    status[name] = {"aid": ci["attempts"][-1] if ci["attempts"] else None,
                                    "status": "not_run_or_incomplete (spend cap or INFRA)"}
                continue
            A = At[aid]
            if A["diverged"]:
                status[name] = {"aid": aid, "status": "diverged"}
            elif not A.get("_eval_complete"):
                status[name] = {"aid": aid, "status": "evals_incomplete"}
            else:
                status[name] = {"aid": aid, "status": "ok"}
                runs.append(A)
        complete = len(runs) == 3
        out = {"ablation_status": "complete" if complete else "incomplete", "n_runs": len(runs), "cell_status": status,
               "comparator": "P4 attention checkpoints as re-evaluated in P5 (U runs b2u_b0_attention_s*)",
               "keying_mask0": None, "keying_mask0_se": None, "keying_mask0_label": None,
               "keying_rho": None, "keying_rho_se": None, "keying_rho_label": None,
               "perm_rel_err": [{"id": aid, "rel_err_tf32off": (perm["reported"].get(aid) or {}).get("rel_err_tf32off")}
                                for aid in idx_scored.values() if aid],
               "rho_undefined": []}
        if len(runs) < 2:
            return out
        a0 = [self.per_run_vals(R, None, "r_h0") for R in u_att]
        b0 = [self.per_run_vals(R, None, "r_h0") for R in runs]
        if all_num(a0) and all_num(b0):
            out["keying_mask0"] = mean(a0) - mean(b0)
            out["keying_mask0_se"] = se2(a0, b0)
        ar = [self.per_run_vals(R, PRIMARY_F, "rho_h") for R in u_att]
        br = [self.per_run_vals(R, PRIMARY_F, "rho_h") for R in runs]
        out["rho_undefined"] = [R["run"] for R in runs if self.per_run_vals(R, PRIMARY_F, "rho_h") is None]
        if all_num(ar) and all_num(br):
            out["keying_rho"] = mean(ar) - mean(br)
            out["keying_rho_se"] = se2(ar, br)

        def label(d, se, floor):
            if d is None or se is None:
                return None
            m = max(floor, 2 * se)
            return "keying_helps" if d >= m else ("keying_hurts" if d <= -m else "no_detectable_difference")
        if complete:
            out["keying_mask0_label"] = label(out["keying_mask0"], out["keying_mask0_se"], KEYING_MASK0_FLOOR)
            out["keying_rho_label"] = label(out["keying_rho"], out["keying_rho_se"], KEYING_RHO_FLOOR)
        return out


# ----------------------------------------------------------------------------------------- output
def sanitize(x, path="", hits=None):
    """Non-finite floats -> null (recorded), so results.json always serialises with allow_nan=False."""
    if isinstance(x, float) and not math.isfinite(x):
        hits.append(path)
        return None
    if isinstance(x, dict):
        return {k: sanitize(v, "%s.%s" % (path, k), hits) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [sanitize(v, "%s[%d]" % (path, i), hits) for i, v in enumerate(x)]
    return x


def verdict_line(res):
    return ("B2_VERDICT verdict=%s outcome=%s drho_u=%s g_u=%s drho_t=%s g_t=%s t_status=%s gate_b1=%s "
            "failing_ids=[%s] blocked=[%s]" % (
                res["verdict"], fmt(res["b2_outcome"]), fmt(res["drho_u"]), fmt(res["g_u"]), fmt(res["drho_t"]),
                fmt(res["g_t"]), res["t_status"], res["gate_b1"], ",".join(res["failing_ids"]),
                ",".join(res["blocked_reason"])))


def write_runs_log(path, v, res, line):
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(path, "a", encoding="utf-8") as fh:
        for d in v.deposits:
            b = ["=== B2 verdict run %s tool=%s sha256=%s ===" % (now, TOOL_VERSION, res["tool"]["sha256"]),
                 "DEPOSIT path=%s sha256=%s part=%s extracted=%s" % (d["path"], d["sha256"], d.get("part"), d["extracted"]),
                 "SEAL_LINE %s" % (d["seal_line"] or "none")]
            b += ["PROBLEM %s" % p for p in d["problems"]]
            for aid, A in sorted(v.attempts.items()):
                if not any(di == d["index"] and aid in rel for rel, (_ap, di) in v.store.files.items()):
                    continue
                b.append("ATTEMPT %s class=%s driver_class=%s completed=%s diverged=%s scored=%s condition=%s" % (
                    aid, A["class"], A["driver_class"], A["class"] == "completed", A["diverged"], A["scored"],
                    A.get("condition")))
            for ID in U_IDS:
                if any(di == d["index"] and ("logs/eval/%s/" % ID) in rel for rel, (_ap, di) in v.store.files.items()):
                    b.append("UEVAL %s scored_exec=%s" % (ID, v.u[ID]["eval"]["it0001600"]["scored_exec"]))
            b += [line, "=== end ==="]
            fh.write("\n".join(b) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--deposit", action="append", default=[], required=True)
    ap.add_argument("--seal-log", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--method-sha", required=True)
    ap.add_argument("--tarball-sha", required=True, help="CR-B2-1 tarball sha256")
    ap.add_argument("--facts", required=True, help="packets/P4/UPSTREAM_FACTS.md")
    ap.add_argument("--p4-open-tree", required=True, help="read-only open tree of the P4 deposit 1f491182…")
    ap.add_argument("--p4-results", required=True, help="orch/reports/VERDICT-P4-b0-attempt1-relaunch3-results.json")
    ap.add_argument("--venue", choices=("colab", "xn4090"), required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--runs-log", required=True)
    ap.add_argument("--work", required=True)
    a = ap.parse_args(argv)
    v = B2Verdict(a)
    res = v.run()
    hits = []
    res = sanitize(res, "", hits)
    res["nonfinite_values_nulled"] = hits
    line = verdict_line(res)
    res["verdict_line"] = line
    tmp = a.out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=False, default=str, allow_nan=False)
    os.replace(tmp, a.out)
    write_runs_log(a.runs_log, v, res, line)
    for r in res["blocked_detail"]:
        log("[verdict_b2] " + r)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
