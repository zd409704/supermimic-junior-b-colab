#!/usr/bin/env python3
"""B0 machine verdict (spikes/B0/PLAN.md §3.3, §4.3-4.4, §5, §6, §8.2-8.3). Stdlib only; run with `python -I`.

Reads one or more sealed P4 deposit archives, extracts them safely, classifies every attempt from evidence,
computes metrics M-1..M-10, gates V-0..V-4, L-1, L-2, DIV, REF-1..4, the §6.2 comparison and the §6.4 ordered
decision table. Writes results.json, appends one block per deposit to runs.log, and prints exactly one
`B0_VERDICT ...` line on stdout. Diagnostics go to stderr.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import os
import re
import stat
import struct
import sys
import tarfile
import tempfile

TOOL_VERSION = "1.0"
T_HORIZON = 500
BUDGET_IT = 1600
CKPTS = (400, 800, 1200, 1600)
MASKS = ("0.00", "0.10", "0.20")
REGISTERED_CLIPS = ("walk1_subject1", "run1_subject2", "dance1_subject1", "jumps1_subject1")
GATE_ARMS = ("attention", "mlp_matched")
REF_ARM = "mlp_upstream"
GATE_SEEDS = (0, 1, 2)
LOGGED_TAGS = ("train/episode_len", "train/episode_norm_return", "wm/loss", "time/updates")
R_DIV = re.compile(r"(?i)\b(nan|inf)\b|non-?finite|not finite")
R_OOM = re.compile(r"(?i)out[ -]of[ -]memory|OutOfMemoryError")
AID_RE = re.compile(r"^(b0|b0lr05)_(attention|mlp_matched|mlp_upstream)_s(\d+)_a(\d+)$")
ENDPOINT_PREFIX = "it %d |" % BUDGET_IT
SAFETY_CAP_LINE = "[INFO] max_hours reached, stopping"


def log(*a):
    print(*a, file=sys.stderr)


# ----------------------------------------------------------------------------------------- TF event reader
_CRC_TABLE = []
for _i in range(256):
    _c = _i
    for _ in range(8):
        _c = (_c >> 1) ^ 0x82F63B78 if _c & 1 else _c >> 1
    _CRC_TABLE.append(_c)


def crc32c(data: bytes) -> int:
    c = 0xFFFFFFFF
    t = _CRC_TABLE
    for b in data:
        c = t[(c ^ b) & 0xFF] ^ (c >> 8)
    return c ^ 0xFFFFFFFF


def masked_crc(data: bytes) -> int:
    c = crc32c(data)
    return (((c >> 15) | (c << 17)) + 0xA282EAD8) & 0xFFFFFFFF


def _varint(b, i):
    r = s = 0
    while True:
        c = b[i]
        i += 1
        r |= (c & 0x7F) << s
        s += 7
        if not c & 0x80:
            return r, i


def _fields(b):
    i = 0
    n = len(b)
    while i < n:
        k, i = _varint(b, i)
        f, t = k >> 3, k & 7
        if t == 0:
            v, i = _varint(b, i)
        elif t == 1:
            v = b[i:i + 8]
            i += 8
        elif t == 5:
            v = b[i:i + 4]
            i += 4
        elif t == 2:
            ln, i = _varint(b, i)
            v = b[i:i + ln]
            i += ln
        else:
            raise ValueError("unsupported wire type %d" % t)
        yield f, t, v


def _tensor_float(b):
    dtype = None
    fv = []
    content = b""
    for f, t, v in _fields(b):
        if f == 1 and t == 0:
            dtype = v
        elif f == 5 and t == 5:
            fv.append(struct.unpack("<f", v)[0])
        elif f == 5 and t == 2:
            fv += list(struct.unpack("<%df" % (len(v) // 4), v))
        elif f == 6 and t == 1:
            fv.append(struct.unpack("<d", v)[0])
        elif f == 6 and t == 2:
            fv += list(struct.unpack("<%dd" % (len(v) // 8), v))
        elif f == 4 and t == 2:
            content = v
    if fv:
        return fv[0]
    if content and dtype == 1 and len(content) == 4:
        return struct.unpack("<f", content)[0]
    if content and dtype == 2 and len(content) == 8:
        return struct.unpack("<d", content)[0]
    return None


def read_events(path):
    """Return (records, info). records: list of (tag, step, wall_time, value, order). Verifies TFRecord CRCs."""
    with open(path, "rb") as fh:
        data = fh.read()
    recs = []
    info = {"path": path, "crc_errors": 0, "truncated": False, "records": 0}
    p = 0
    order = 0
    while p < len(data):
        if p + 12 > len(data):
            info["truncated"] = True
            break
        hdr = data[p:p + 8]
        (n,) = struct.unpack("<Q", hdr)
        (lcrc,) = struct.unpack("<I", data[p + 8:p + 12])
        if masked_crc(hdr) != lcrc:
            info["crc_errors"] += 1
            break
        if p + 12 + n + 4 > len(data):
            info["truncated"] = True
            break
        rec = data[p + 12:p + 12 + n]
        (dcrc,) = struct.unpack("<I", data[p + 12 + n:p + 16 + n])
        p += 16 + n
        if masked_crc(rec) != dcrc:
            info["crc_errors"] += 1
            continue
        info["records"] += 1
        wall = 0.0
        step = 0
        summ = None
        for f, t, v in _fields(rec):
            if f == 1 and t == 1:
                wall = struct.unpack("<d", v)[0]
            elif f == 2 and t == 0:
                step = v - (1 << 64) if v >= (1 << 63) else v
            elif f == 5 and t == 2:
                summ = v
        if summ is None:
            continue
        for f, t, v in _fields(summ):
            if f != 1 or t != 2:
                continue
            tag = None
            val = None
            for f2, t2, v2 in _fields(v):
                if f2 == 1 and t2 == 2:
                    tag = v2.decode("utf-8", "replace")
                elif f2 == 2 and t2 == 5:
                    val = struct.unpack("<f", v2)[0]
                elif f2 == 8 and t2 == 2:
                    val = _tensor_float(v2)
            if tag is not None and val is not None:
                recs.append((tag, step, wall, val, order))
                order += 1
    return recs, info


def dedupe_series(records):
    """§5 TB rule: for duplicate (tag, step) the value with the latest wall time wins (ties: later record)."""
    best = {}
    for idx, (tag, step, wall, val, _o) in enumerate(records):
        key = (tag, step)
        cur = best.get(key)
        if cur is None or (wall, idx) >= (cur[0], cur[1]):
            best[key] = (wall, idx, val)
    series = {}
    for (tag, step), (_w, _i, val) in best.items():
        series.setdefault(tag, {})[step] = val
    return series


# ----------------------------------------------------------------------------------------- helpers
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def kv_file(text):
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def finite_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def tf(s):
    return str(s).strip().lower() == "true"


def jnum(x):
    """JSON-safe number (non-finite -> string)."""
    if isinstance(x, float) and not math.isfinite(x):
        return repr(x)
    return x


# ----------------------------------------------------------------------------------------- archive handling
def check_members(tf_):
    """§8.2 member path checks. Returns list of problems (empty = safe)."""
    bad = []
    for m in tf_.getmembers():
        name = m.name
        parts = name.replace("\\", "/").split("/")
        if name.startswith("/") or re.match(r"^[A-Za-z]:", name):
            bad.append("absolute path: %s" % name)
            continue
        if ".." in parts:
            bad.append("parent ref: %s" % name)
            continue
        if name.endswith(".pt"):
            bad.append("checkpoint member: %s" % name)
            continue
        if m.issym():
            ln = m.linkname
            tgt = os.path.normpath(os.path.join(os.path.dirname(name), ln))
            if ln.startswith("/") or tgt == ".." or tgt.startswith("../") or tgt.endswith(".pt"):
                bad.append("symlink escapes: %s -> %s" % (name, ln))
        elif m.islnk():
            ln = m.linkname
            lparts = ln.replace("\\", "/").split("/")
            if ln.startswith("/") or ".." in lparts or ln.endswith(".pt"):
                bad.append("hardlink escapes: %s -> %s" % (name, ln))
        elif not (m.isfile() or m.isdir()):
            bad.append("special member: %s" % name)
    return bad


def safe_extract(tgz, dest):
    with tarfile.open(tgz, "r:*") as t:
        bad = check_members(t)
        if bad:
            return bad
        t.extractall(dest, filter="data")
    # read-only after extraction
    for root, dirs, files in os.walk(dest):
        for f in files:
            p = os.path.join(root, f)
            if not os.path.islink(p):
                os.chmod(p, 0o444)
    return []


def seal_lookup(seal_text, sha):
    for line in seal_text.splitlines():
        toks = line.split()
        for i, t in enumerate(toks):
            if t == "DEPOSIT" and i + 1 < len(toks) and toks[i + 1] in ("colab", "xn4090") and sha in toks[i + 2:]:
                return line.strip(), toks[i + 1]
    return None, None


class Store:
    """Merged view of the extracted deposits. Later session parts win for duplicate relative paths."""

    def __init__(self):
        self.files = {}  # rel -> (abs, deposit_index)
        self.dups = []

    def add_root(self, root, didx):
        for r, dirs, files in os.walk(root):
            for f in files:
                ap = os.path.join(r, f)
                rel = os.path.relpath(ap, root).replace(os.sep, "/")
                if rel.startswith("./"):
                    rel = rel[2:]
                if rel in self.files:
                    self.dups.append(rel)
                self.files[rel] = (ap, didx)

    def get(self, rel):
        v = self.files.get(rel)
        return v[0] if v else None

    def ls(self, prefix):
        return sorted(r for r in self.files if r.startswith(prefix))

    def has_prefix(self, prefix):
        return any(r.startswith(prefix) for r in self.files)


# ----------------------------------------------------------------------------------------- train log parsing
def split_lines(text):
    return re.split(r"\r\n|\n|\r", text)


def find_tracebacks(lines):
    """Return list of chains: {start, end, final_line}. Final line = first non-indented line after a
    `Traceback (most recent call last):` body. Chained tracebacks are merged; the chain's last final line counts."""
    chains = []
    i = 0
    n = len(lines)
    while i < n:
        if lines[i].startswith("Traceback (most recent call last):"):
            start = i
            final = None
            final_idx = None
            j = i + 1
            while True:
                while j < n and (lines[j].startswith((" ", "\t")) or lines[j] == ""):
                    j += 1
                if j < n:
                    final = lines[j]
                    final_idx = j
                    j += 1
                else:
                    break
                # chained?
                k = j
                while k < n and (lines[k].strip() == "" or lines[k].startswith("During handling of the above exception")
                                 or lines[k].startswith("The above exception was the direct cause")):
                    k += 1
                if k < n and k > j and lines[k].startswith("Traceback (most recent call last):"):
                    j = k + 1
                    continue
                break
            chains.append({"start": start, "end": final_idx if final_idx is not None else n - 1,
                           "final_line": final})
            i = (final_idx + 1) if final_idx is not None else n
        else:
            i += 1
    return chains


def parse_seam_line(rest):
    toks = rest.split()
    if not toks:
        return None, {}
    sid = toks[0]
    if len(toks) > 1 and toks[1] == "detail":
        return sid, None
    return sid, dict(re.findall(r"(\w+)=(\S+)", rest))


def parse_train_log(text):
    lines = split_lines(text)
    out = {"present": True, "endpoint_idx": None, "argv": None, "params_line": None, "seam_lines": [],
           "seams": {}, "seam_bad_pre": False, "seam_unverified_line": False, "safety_cap_idx": None,
           "tracebacks": [], "last_it": None}
    for i, ln in enumerate(lines):
        if out["endpoint_idx"] is None and ln.startswith(ENDPOINT_PREFIX):
            out["endpoint_idx"] = i
        if out["argv"] is None and ln.startswith("[train_entry] upstream argv:"):
            out["argv"] = ln[len("[train_entry] upstream argv:"):].split()
        if out["params_line"] is None and ln.startswith("[INFO] params:"):
            out["params_line"] = ln.strip()
        if ln.startswith(SAFETY_CAP_LINE) and out["safety_cap_idx"] is None:
            out["safety_cap_idx"] = i
        m = re.match(r"^it (\d+) \|", ln)
        if m:
            out["last_it"] = int(m.group(1))
        if ln.startswith("[seam] "):
            rest = ln[len("[seam] "):]
            out["seam_lines"].append((i, ln))
            pre = out["endpoint_idx"] is None or i < out["endpoint_idx"]
            if "unverified" in rest:
                out["seam_unverified_line"] = True
                if pre:
                    out["seam_bad_pre"] = True
            sid, kv = parse_seam_line(rest)
            if kv:
                for k, v in kv.items():
                    if v in ("false", "unverified") and pre:
                        out["seam_bad_pre"] = True
                key = {"S1": "joint_order_match", "S2": "term_major_ok", "S3": "compile",
                       "S4": "default_pose_source", "S5": "env_action_scale_match"}.get(sid)
                if key and key in kv:
                    out["seams"][sid] = kv[key]
    ep = out["endpoint_idx"]
    for ch in find_tracebacks(lines):
        ch["pre_endpoint"] = ep is None or ch["start"] < ep
        out["tracebacks"].append(ch)
    return out


def norm_seam(v):
    if isinstance(v, str):
        if v == "true":
            return True
        if v == "false":
            return False
    return v


# ----------------------------------------------------------------------------------------- eval
def rh_of(clips):
    return sum(c["norm_return"] * min(c["steps"], T_HORIZON) for c in clips) / (4.0 * T_HORIZON)


def check_eval_json(d):
    """V-4 content checks for one mask JSON. Returns list of problems."""
    probs = []
    if not isinstance(d, dict):
        return ["not an object"]
    clips = d.get("clips")
    summ = d.get("summary")
    if not isinstance(clips, list):
        return ["clips missing"]
    names = [c.get("name") if isinstance(c, dict) else None for c in clips]
    if sorted(n for n in names if isinstance(n, str)) != sorted(REGISTERED_CLIPS) or len(names) != 4:
        probs.append("clip names %s != registered" % names)
    for c in clips:
        if not isinstance(c, dict):
            probs.append("clip not object")
            continue
        if not (is_int(c.get("steps")) and c["steps"] >= 1):
            probs.append("%s steps invalid" % c.get("name"))
        if not finite_num(c.get("norm_return")):
            probs.append("%s norm_return not finite" % c.get("name"))
        if not isinstance(c.get("failed"), bool):
            probs.append("%s failed not bool" % c.get("name"))
        elif c["failed"] and not is_int(c.get("fail_step")):
            probs.append("%s fail_step missing" % c.get("name"))
    if not isinstance(summ, dict):
        probs.append("summary missing")
    else:
        if not finite_num(summ.get("mean_norm_return")):
            probs.append("summary.mean_norm_return not finite")
        if not finite_num(summ.get("step_weighted_norm_return")):
            probs.append("summary.step_weighted_norm_return not finite")
        if not is_int(summ.get("failed")):
            probs.append("summary.failed not int")
        terms = summ.get("terms")
        if not (isinstance(terms, dict) and terms and all(finite_num(v) for v in terms.values())):
            probs.append("summary.terms empty or non-finite")
    return probs


def mask_metrics(d):
    clips = d["clips"]
    summ = d["summary"]
    return {
        "r_h": rh_of(clips),
        "r_step": summ["mean_norm_return"],
        "r_step_weighted": summ["step_weighted_norm_return"],
        "cum": sum(c["norm_return"] * c["steps"] for c in clips),
        "surv_steps": sum(c["steps"] for c in clips),
        "fail_count": summ["failed"],
        "clips": [{"name": c["name"], "steps": c["steps"], "failed": c["failed"], "fail_step": c.get("fail_step"),
                   "norm_return": c["norm_return"]} for c in clips],
        "terms": summ["terms"],
        "over_T": sum(1 for c in clips if c["steps"] > T_HORIZON),
    }


def ckpt_path_ok(evlog_text, expected_rel):
    paths = re.findall(r"^\[eval_entry\].*?--ckpt\s+(\S+)", evlog_text, flags=re.M)
    if not paths:
        return False, "no [eval_entry] --ckpt line"
    for p in paths:
        pn = p.replace("\\", "/")
        if not (pn == expected_rel or pn.endswith("/" + expected_rel) or pn == "./" + expected_rel):
            return False, "ckpt path %s != %s" % (p, expected_rel)
    return True, "ok"


# ----------------------------------------------------------------------------------------- main analysis
class Verdict:
    def __init__(self, a):
        self.a = a
        self.store = Store()
        self.deposits = []
        self.deposit_problems = []
        self.attempts = {}
        self.blocked = []
        self.blocked_detail = []

    # ---------------------------------------------------------------- deposits
    def load_deposits(self):
        a = self.a
        seal_text = read_text(a.seal_log) if os.path.exists(a.seal_log) else ""
        os.makedirs(a.work, exist_ok=True)
        roots = []
        for idx, dep in enumerate(a.deposit):
            rec = {"path": dep, "sha256": None, "seal_line": None, "seal_venue": None, "extracted": False,
                   "problems": [], "part": None, "index": idx}
            self.deposits.append(rec)
            if not os.path.isfile(dep):
                rec["problems"].append("deposit file missing")
                continue
            rec["sha256"] = sha256_file(dep)
            line, venue = seal_lookup(seal_text, rec["sha256"])
            rec["seal_line"] = line
            rec["seal_venue"] = venue
            if line is None:
                rec["problems"].append("sha256 not on a DEPOSIT colab/xn4090 line in seal log (not opened)")
                continue
            dest = tempfile.mkdtemp(prefix="dep%d_%s_" % (idx, rec["sha256"][:12]), dir=a.work)
            try:
                bad = safe_extract(dep, dest)
            except (tarfile.TarError, OSError, ValueError) as e:
                bad = ["extraction error: %s" % e]
            if bad:
                rec["problems"].extend(bad)
                continue
            rec["extracted"] = True
            rec["root"] = dest
            roots.append(rec)
        # per-deposit meta
        for rec in roots:
            root = rec["root"]
            sess_p = os.path.join(root, "meta", "session.txt")
            rec["session"] = kv_file(read_text(sess_p)) if os.path.exists(sess_p) else {}
            try:
                rec["part"] = int(rec["session"].get("part", "1"))
            except ValueError:
                rec["part"] = 1
            tsp = os.path.join(root, "meta", "tarball_sha256.txt")
            if os.path.exists(tsp):
                toks = read_text(tsp).split()
                rec["tarball_sha256"] = toks[0].lower() if toks else None
            else:
                rec["tarball_sha256"] = None
            if rec["tarball_sha256"] != (a.tarball_sha or "").lower():
                rec["problems"].append("meta/tarball_sha256.txt %s != expected %s" % (rec["tarball_sha256"], a.tarball_sha))
            nsp = os.path.join(root, "meta", "nvidia-smi.txt")
            rec["gpu_name"] = parse_gpu_name(read_text(nsp)) if os.path.exists(nsp) else None
            bp = os.path.join(root, "BLOCKED.md")
            rec["blocked_md"] = re.findall(r"BLOCKED_REASON=(\S+)", read_text(bp)) if os.path.exists(bp) else []
            dsp = os.path.join(root, "meta", "driver_state.txt")
            rec["driver_state"] = read_text(dsp).splitlines() if os.path.exists(dsp) else []
            tcp = os.path.join(root, "meta", "torch_cuda.txt")
            rec["torch_cuda"] = read_text(tcp).strip() if os.path.exists(tcp) else None
            sp = os.path.join(root, "train_up_sanity.log")
            rec["sanity_log"] = read_text(sp) if os.path.exists(sp) else None
        for rec in sorted(roots, key=lambda r: (r["part"], r["index"])):
            self.store.add_root(rec["root"], rec["index"])
        self.roots = roots
        for rec in self.deposits:
            if rec["problems"]:
                self.deposit_problems.append({"path": rec["path"], "problems": rec["problems"]})

    # ---------------------------------------------------------------- attempts
    def discover_attempts(self):
        aids = set()
        for rel in self.store.files:
            m = re.match(r"^logs/train_(.+)\.log$", rel)
            if m:
                aids.add(m.group(1))
            m = re.match(r"^logs/attempts/([^/]+)/", rel)
            if m and not m.group(1).endswith(".live"):
                aids.add(m.group(1))
            m = re.match(r"^meta/(?:attempt|harness_stop)_(.+)\.txt$", rel)
            if m:
                aids.add(m.group(1))
            m = re.match(r"^logs/eval/([^/]+)/", rel)
            if m:
                aids.add(m.group(1))
        return sorted(x for x in aids if AID_RE.match(x))

    def analyse_attempt(self, aid):
        st = self.store
        tag, arm, seed, n = AID_RE.match(aid).groups()
        seed, n = int(seed), int(n)
        A = {"tag": tag, "arm": arm, "seed": seed, "attempt": n, "run": "%s_%s_s%d" % (tag, arm, seed)}
        lp = st.get("logs/train_%s.log" % aid)
        L = parse_train_log(read_text(lp)) if lp else {"present": False, "endpoint_idx": None, "argv": None,
                                                         "params_line": None, "seams": {}, "seam_bad_pre": False,
                                                         "seam_unverified_line": False, "safety_cap_idx": None,
                                                         "tracebacks": [], "last_it": None, "seam_lines": []}
        A["_log"] = L
        A["train_log_present"] = L["present"]
        A["reached_1600"] = L["endpoint_idx"] is not None
        hsp = st.get("meta/harness_stop_%s.txt" % aid)
        hs = kv_file(read_text(hsp)) if hsp else None
        A["harness_stop_record"] = hs
        A["harness_stop"] = tf(hs.get("harness_stop")) if hs else None
        atp = st.get("meta/attempt_%s.txt" % aid)
        drv = kv_file(read_text(atp)) if atp else None
        A["driver_record"] = drv
        A["driver_class"] = drv.get("driver_class") if drv else None
        adir = "logs/attempts/%s/" % aid
        A["attempt_dir_present"] = st.has_prefix(adir)
        A["live_dir_present"] = st.has_prefix("logs/attempts/%s.live/" % aid)
        sc = st.get(adir + "junior_policy.json")
        sidecar = None
        if sc:
            try:
                sidecar = json.loads(read_text(sc))
            except ValueError:
                sidecar = None
        A["sidecar_present"] = sidecar is not None
        A["_sidecar"] = sidecar
        # tb
        tbfiles = [r for r in st.ls(adir) if os.path.basename(r).startswith("events.out.tfevents.")]
        A["tb_files"] = tbfiles
        A["tb_file_count"] = len(tbfiles)
        recs = []
        tbinfo = []
        for r in tbfiles:
            rr, info = read_events(st.get(r))
            recs += rr
            info = dict(info)
            info["path"] = r
            tbinfo.append(info)
        A["tb_read_info"] = tbinfo
        series = dedupe_series(recs)
        A["_series"] = series
        nonfin_pre = []
        nonfin_post = []
        for tag_, s in series.items():
            for step, v in s.items():
                if not math.isfinite(v):
                    (nonfin_pre if step <= BUDGET_IT else nonfin_post).append({"tag": tag_, "step": step, "value": repr(v)})
        nonfin_pre.sort(key=lambda x: (x["step"], x["tag"]))
        nonfin_post.sort(key=lambda x: (x["step"], x["tag"]))
        A["nan"] = bool(nonfin_pre)
        A["nonfinite_le_1600"] = nonfin_pre[:20]
        pre_tb = [t for t in L["tracebacks"] if t["pre_endpoint"]]
        post_tb = [t for t in L["tracebacks"] if not t["pre_endpoint"]]
        A["pre_endpoint_final_exception_lines"] = [t["final_line"] for t in pre_tb]
        rdiv_hit = [t["final_line"] for t in pre_tb if t["final_line"] and R_DIV.search(t["final_line"])]
        oom_hit = [t["final_line"] for t in pre_tb if t["final_line"] and R_OOM.search(t["final_line"])]
        # completion condition (§4.3)
        ckpt_stable = bool(hs) and tf(hs.get("ckpt_stable"))
        timeout = bool(hs) and tf(hs.get("harness_stop_timeout"))
        hs_sidecar_ok = (hs or {}).get("sidecar", "present") != "missing"
        completed = A["reached_1600"] and ckpt_stable and A["sidecar_present"] and hs_sidecar_ok and not timeout
        A["completion"] = {"endpoint_line": A["reached_1600"], "ckpt_stable": ckpt_stable,
                           "sidecar_present": A["sidecar_present"], "harness_record_sidecar": (hs or {}).get("sidecar"),
                           "harness_stop_timeout": timeout, "harness_stop_record_present": hs is not None}
        div_a = bool(nonfin_pre) or bool(rdiv_hit)
        if completed:
            cls = "completed"
        elif div_a:
            cls = "DIV"
        elif oom_hit:
            cls = "OOM"
        elif L["seam_bad_pre"]:
            cls = "SEAM"
        else:
            cls = "INFRA"
        A["class"] = cls
        A["diverged"] = cls == "DIV" or (completed and div_a)
        A["divergence_evidence"] = {"tb_nonfinite_le_1600": nonfin_pre[:5], "rdiv_final_lines": rdiv_hit,
                                    "clip_clause_b": "skipped (M-6 null)"}
        cause = None
        if cls == "INFRA":
            if L["safety_cap_idx"] is not None and (L["endpoint_idx"] is None or L["safety_cap_idx"] < L["endpoint_idx"]):
                cause = "safety_cap"
            elif timeout:
                cause = "harness_stop_timeout"
            elif A["reached_1600"] and not ckpt_stable:
                cause = "ckpt_unstable"
            elif A["reached_1600"] and not (A["sidecar_present"] and hs_sidecar_ok):
                cause = "sidecar_missing"
            elif pre_tb:
                cause = "other_traceback"
            else:
                cause = "no_endpoint"
        A["infra_cause"] = cause
        A["class_disagreement"] = (A["driver_class"] is not None and A["driver_class"] != cls)
        anomalies = []
        for x in nonfin_post:
            anomalies.append({"kind": "tb_nonfinite_after_1600", "tag": x["tag"], "step": x["step"], "value": x["value"]})
        for t in post_tb:
            anomalies.append({"kind": "exception_after_endpoint", "final_line": t["final_line"]})
        if timeout:
            anomalies.append({"kind": "harness_stop_timeout"})
        A["post_endpoint_anomaly"] = anomalies
        # seams
        side_seam = (sidecar or {}).get("seam") or {}
        seams = {}
        for sid, skey in (("S1", "S1_joint_order_match"), ("S2", "S2_term_major_ok"), ("S3", "S3_compile"),
                          ("S4", "S4_default_pose_source"), ("S5", "S5_env_action_scale_match")):
            lv = norm_seam(L["seams"].get(sid)) if sid in L["seams"] else None
            sv = side_seam.get(skey)
            seams[sid] = {"log": lv, "sidecar": sv}
        A["_seams_raw"] = seams
        A["seams"] = {k: (v["sidecar"] if v["sidecar"] is not None else v["log"]) for k, v in seams.items()}
        A["seam_unverified_line"] = L["seam_unverified_line"]
        A["descriptor_sha256"] = ((sidecar or {}).get("descriptor") or {}).get("sha256")
        A["params_policy"] = (sidecar or {}).get("params")
        A["params_line"] = L["params_line"]
        A["argv"] = L["argv"]
        # tb-derived numbers
        self.tb_metrics(A, series)
        # gpu memory
        gp = st.get("meta/gpumem_%s.csv" % aid)
        A["peak_mem_mib"] = parse_gpumem(read_text(gp)) if gp else None
        # eval
        A["eval"] = {}
        A["_eval_complete"] = False
        if completed:
            self.eval_attempt(aid, A)
        return A

    def tb_metrics(self, A, s):
        def at(tag_, step):
            v = s.get(tag_, {}).get(step)
            return v
        A["updates_at_1600"] = int(at("time/updates", 1600)) if finite_num(at("time/updates", 1600)) else None
        hrs = {str(k): at("time/hours", k) for k in CKPTS}
        upd = {str(k): at("time/updates", k) for k in CKPTS}
        A["hours_at_ckpt"] = {k: jnum(v) for k, v in hrs.items()}
        A["updates_at_ckpt"] = {k: jnum(v) for k, v in upd.items()}
        A["hours_at_1600"] = jnum(hrs["1600"])
        h4, h16, u4, u16 = hrs["400"], hrs["1600"], upd["400"], upd["1600"]
        A["ms_per_update"] = (1000 * 3600 * (h16 - h4) / (u16 - u4)
                              if all(finite_num(x) for x in (h4, h16, u4, u16)) and u16 != u4 else None)
        A["it_per_s"] = (1200.0 / (3600 * (h16 - h4)) if finite_num(h4) and finite_num(h16) and h16 > h4 else None)
        env = self.env_steps_per_iter
        A["env_steps_per_s"] = (A["it_per_s"] * env) if (A["it_per_s"] is not None and env) else "not derivable"
        spi = {}
        for k in ("sim", "wm", "policy"):
            vals = [v for st_, v in s.get("time/%s_s_per_iter" % k, {}).items() if 400 <= st_ <= 1600 and math.isfinite(v)]
            spi[k] = mean(vals)
        A["s_per_iter_mean_400_1600"] = spi
        gn = [v for st_, v in s.get("policy/policy_grad_norm", {}).items() if st_ <= BUDGET_IT and math.isfinite(v)]
        A["grad_norm_max"] = max(gn) if gn else None
        A["clip_fraction_last25"] = None  # M-6: F-4 gives no per-update norm or clip indicator
        aam = s.get("policy/action_abs_mean", {})
        A["action_abs_mean_at_1600"] = jnum(aam.get(1600))
        # logged points
        steps = None
        for t_ in LOGGED_TAGS:
            st_set = set(s.get(t_, {}).keys())
            steps = st_set if steps is None else steps & st_set
        pts = sorted(x for x in (steps or set()) if x <= BUDGET_IT)
        A["logged_points_le_1600"] = len(pts)
        A["logged_point_at_1600"] = 1600 in (steps or set())
        first_pool = [p for p in pts if finite_num(s["time/updates"][p]) and s["time/updates"][p] >= 20]
        A["window_coverage"] = len(first_pool)
        first5 = first_pool[:5]
        last5 = pts[-5:]
        A["_first5"], A["_last5"] = first5, last5

        def wmean(tag_, idx, fn=None):
            if len(idx) < 5:
                return None
            vals = [(fn(p) if fn else s[tag_][p]) for p in idx]
            return mean(vals)
        ctrain = lambda p: s["train/episode_len"][p] * s["train/episode_norm_return"][p]  # noqa: E731
        A["c_train_first5"] = jnum(wmean(None, first5, ctrain))
        A["c_train_last5"] = jnum(wmean(None, last5, ctrain))
        A["nret_train_first5"] = jnum(wmean("train/episode_norm_return", first5))
        A["nret_train_last5"] = jnum(wmean("train/episode_norm_return", last5))
        A["elen_first5"] = jnum(wmean("train/episode_len", first5))
        A["elen_last5"] = jnum(wmean("train/episode_len", last5))
        A["wm_loss_first5"] = jnum(wmean("wm/loss", first5))
        A["wm_loss_last5"] = jnum(wmean("wm/loss", last5))
        cf, cl = A["c_train_first5"], A["c_train_last5"]
        A["l1_pass"] = (cl > cf) if (finite_num(cf) and finite_num(cl)) else None
        wf, wl = A["wm_loss_first5"], A["wm_loss_last5"]
        A["l2_pass"] = (wl < wf) if (finite_num(wf) and finite_num(wl)) else None

    def eval_attempt(self, aid, A):
        st = self.store
        complete = True
        for it in CKPTS:
            itk = "it%07d" % it
            expected = self.ckpt_map.get((aid, itk), "logs/%s/ckpt_%07d.pt" % (A["run"], it))
            entry = {"scored_exec": None, "executions": {}}
            for k in (1, 2):
                d = "logs/eval/%s/%s/exec%d/" % (aid, itk, k)
                if not st.has_prefix(d):
                    continue
                probs = []
                evl = st.get(d + "eval.log")
                if evl is None:
                    probs.append("eval.log missing")
                    evtext = ""
                else:
                    evtext = read_text(evl)
                    ok, why = ckpt_path_ok(evtext, expected)
                    if not ok:
                        probs.append(why)
                m_exit = re.findall(r"^exit=(-?\d+)\s*$", evtext, flags=re.M)
                jsons = {}
                for f in MASKS:
                    cands = [r for r in st.ls(d) if r.endswith("_mask%s.json" % f) and r.count("/") == d.count("/")]
                    if len(cands) != 1:
                        probs.append("mask %s: %d JSONs" % (f, len(cands)))
                        continue
                    try:
                        jd = json.loads(read_text(st.get(cands[0])))
                    except ValueError as e:
                        probs.append("mask %s: bad JSON %s" % (f, e))
                        continue
                    p2 = check_eval_json(jd)
                    if p2:
                        probs += ["mask %s: %s" % (f, x) for x in p2]
                    else:
                        jsons[f] = jd
                entry["executions"]["exec%d" % k] = {"exit": int(m_exit[-1]) if m_exit else None, "problems": probs}
                if not probs and entry["scored_exec"] is None:
                    entry["scored_exec"] = "exec%d" % k
                    for f in MASKS:
                        entry["mask" + f] = mask_metrics(jsons[f])
            if entry["scored_exec"] is None:
                complete = False
            else:
                base = entry["mask0.00"]
                for f in MASKS[1:]:
                    mm = entry["mask" + f]
                    mm["rho_h"] = (mm["r_h"] / base["r_h"]) if base["r_h"] != 0 else None
                    mm["rho_step"] = (mm["r_step"] / base["r_step"]) if base["r_step"] != 0 else None
            A["eval"][itk] = entry
        A["_eval_complete"] = complete
        rh = [A["eval"]["it%07d" % k].get("mask0.00", {}).get("r_h") for k in CKPTS]
        A["aulc_h"] = (sum((rh[i] + rh[i + 1]) / 2.0 for i in range(3)) / 3.0) if all(x is not None for x in rh) else None

    # ---------------------------------------------------------------- run
    def run(self):
        a = self.a
        self.plan_sha = sha256_file(a.plan)
        self.facts = parse_facts(a.facts)
        f5 = self.facts.get("F-5") or {}
        self.env_steps_per_iter = f5.get("env_steps_per_iter") if isinstance(f5, dict) else None
        f2 = self.facts.get("F-2")
        self.f2_none = not (isinstance(f2, dict) and f2.get("flag") and str(f2.get("flag")).lower() != "none")
        self.f2_flag = f2.get("flag") if isinstance(f2, dict) else None
        self.lr05 = None
        if isinstance(f2, dict):
            if isinstance(f2.get("default"), (int, float)):
                self.lr05 = 0.5 * float(f2["default"])
        self.load_deposits()
        self.ckpt_map = {}
        for rel in self.store.ls("meta/ckpt_map.txt"):
            for line in read_text(self.store.get(rel)).splitlines():
                t = line.split()
                if len(t) >= 3:
                    self.ckpt_map[(t[0], t[1])] = t[2]
        for aid in self.discover_attempts():
            self.attempts[aid] = self.analyse_attempt(aid)
        return self.decide()

    def decide(self):
        a = self.a
        At = self.attempts
        reasons = []
        detail = []

        def block(code, why):
            if code not in reasons:
                reasons.append(code)
            detail.append("%s: %s" % (code, why))

        # deposit / seal
        if not self.a.deposit:
            block("deposit_check", "no deposit given")
        for p in self.deposit_problems:
            block("deposit_check", "%s: %s" % (p["path"], "; ".join(p["problems"])))
        if not self.roots:
            block("deposit_check", "no deposit could be opened")
        # BLOCKED.md / R1
        spend_cap_hit = False
        for rec in self.roots:
            if tf(rec["session"].get("spend_cap_hit", "false")):
                spend_cap_hit = True
            if any(l.startswith("SPEND_CAP_HIT") for l in rec["driver_state"]):
                spend_cap_hit = True
            for code in rec["blocked_md"]:
                if code == "spend_cap":
                    spend_cap_hit = True
                elif code == "R1_unresolved":
                    block("R1_unresolved", "BLOCKED.md in %s" % rec["path"])
                elif code == "tarball_sha_mismatch":
                    block("deposit_check", "BLOCKED.md tarball_sha_mismatch in %s" % rec["path"])
                else:
                    block("blocked_md:%s" % code, "BLOCKED.md in %s" % rec["path"])
            if rec["torch_cuda"] is not None and rec["torch_cuda"].split()[:2][-1:] == ["False"]:
                block("R1_unresolved", "meta/torch_cuda.txt says cuda False in %s" % rec["path"])
        # venue consistency (§2.3)
        venues = set()
        for rec in self.roots:
            venues.add(rec["session"].get("venue") or a.venue)
            if rec.get("seal_venue"):
                venues.add(rec["seal_venue"])
        venues.add(a.venue)
        venue_consistent = len(venues) == 1
        if not venue_consistent:
            block("venue_mixed", "venues seen: %s" % sorted(venues))

        # V-0
        sanity = [r["sanity_log"] for r in self.roots if r["sanity_log"] is not None]
        v0_ev = []
        for txt in sanity:
            v0_ev.append({"cap_reached": SAFETY_CAP_LINE in txt, "traceback": "Traceback" in txt})
        v0 = bool(sanity) and all(e["cap_reached"] and not e["traceback"] for e in v0_ev)
        if not v0:
            block("V-0", "train_up_sanity.log %s" % ("missing" if not sanity else v0_ev))

        # cells
        cells = {}
        for aid, A in At.items():
            cells.setdefault((A["tag"], A["arm"], A["seed"]), []).append(aid)
        cellinfo = {}
        for key, aids in cells.items():
            aids.sort(key=lambda x: At[x]["attempt"])
            scored = next((x for x in aids if At[x]["class"] == "completed"), None)
            first_two = aids[:2]
            infra_n = sum(1 for x in first_two if At[x]["class"] == "INFRA")
            div = next((x for x in aids if At[x]["diverged"]), None)
            notes = []
            if len(aids) > 2:
                notes.append("more than 2 attempts")
            if scored and aids.index(scored) != len(aids) - 1:
                notes.append("attempt started after the scored attempt")
            cellinfo[key] = {"attempts": aids, "scored": scored, "infra_cap": infra_n >= 2, "diverged_attempt": div,
                             "notes": notes}
            if scored:
                At[scored]["scored"] = True
        for A in At.values():
            A.setdefault("scored", False)
            A["in_scored_set"] = False

        # gate-arm OOM/SEAM/INFRA cap
        for key, ci in cellinfo.items():
            tag, arm, seed = key
            if arm not in GATE_ARMS:
                continue
            for x in ci["attempts"]:
                if At[x]["class"] in ("OOM", "SEAM"):
                    block(At[x]["class"], x)
            if ci["infra_cap"]:
                block("INFRA_cap", "%s_%s_s%d" % key)

        # divergence / retry pairs / scored set
        retry_seeds = []
        slots = {}
        terminal_att = {}
        terminal_cmp = {}
        any_gate_div = False
        for s in GATE_SEEDS:
            b0div = [cellinfo[("b0", arm, s)]["diverged_attempt"] for arm in GATE_ARMS
                     if ("b0", arm, s) in cellinfo and cellinfo[("b0", arm, s)]["diverged_attempt"]]
            if b0div:
                any_gate_div = True
            use = "b0lr05" if (b0div and not self.f2_none) else "b0"
            if use == "b0lr05":
                retry_seeds.append(s)
            for arm in GATE_ARMS:
                ci = cellinfo.get((use, arm, s))
                slot = "%s_s%d" % (arm, s)
                aid = None
                if ci:
                    aid = ci["scored"] or ci["diverged_attempt"]
                slots[slot] = aid
                if use == "b0lr05" and ci and ci["diverged_attempt"]:
                    any_gate_div = True
                    if arm == "attention":
                        terminal_att[slot] = ci["diverged_attempt"]
                        slots[slot] = ci["diverged_attempt"]
                    else:
                        terminal_cmp[slot] = ci["diverged_attempt"]
                        slots[slot] = ci["diverged_attempt"]
        for slot, aid in slots.items():
            if aid:
                At[aid]["in_scored_set"] = True
        if self.f2_none and any_gate_div:
            block("F2_none_divergence", "F-2 = none and a gate-arm attempt diverged")
        for slot, aid in terminal_cmp.items():
            block("terminal_comparator_divergence", "%s (%s)" % (slot, aid))
        term_att_aids = set(terminal_att.values())
        checkable = {slot: aid for slot, aid in slots.items()}
        full_runs = [aid for slot, aid in slots.items() if aid and aid not in term_att_aids]
        missing_slots = [slot for slot, aid in slots.items() if aid is None]

        # V-1
        v1 = {"pass": True, "per_attempt": {}, "missing_slots": missing_slots}
        for slot in missing_slots:
            v1["pass"] = False
            v1["per_attempt"]["slot:" + slot] = {"pass": False, "why": "no scored attempt for this slot"}
        for slot, aid in slots.items():
            if not aid:
                continue
            A = At[aid]
            if aid in term_att_aids:
                ev = self.v1_integrity(A)
            else:
                ev = self.v1_full(A)
            v1["per_attempt"][aid] = ev
            if not ev["pass"]:
                v1["pass"] = False
        if not v1["pass"]:
            block("V-1", "; ".join("%s" % k for k, v in v1["per_attempt"].items() if not v["pass"]))

        # V-2
        gpu_names = [r.get("gpu_name") for r in self.roots]
        v2c = bool(gpu_names) and all(g for g in gpu_names) and len(set(gpu_names)) == 1
        upd = {aid: At[aid]["updates_at_1600"] for aid in full_runs}
        v2a = bool(upd) and all(v is not None for v in upd.values()) and len(set(upd.values())) == 1 and not missing_slots
        argv_norm = {}
        argv_prob = {}
        for slot, aid in slots.items():
            if not aid:
                continue
            nrm, prob = self.normalise_argv(At[aid])
            argv_norm[aid] = nrm
            if prob:
                argv_prob[aid] = prob
        vals = [tuple(v) for v in argv_norm.values() if v is not None]
        v2b = (bool(argv_norm) and not argv_prob and all(v is not None for v in argv_norm.values())
               and len(set(vals)) == 1 and not missing_slots)
        v2 = {"pass": v2a and v2b and v2c, "a_updates_parity": v2a, "b_argv_identical": v2b, "c_gpu_identical": v2c,
              "gpu_names": {r["path"]: r.get("gpu_name") for r in self.roots}, "argv_problems": argv_prob,
              "per_attempt": {aid: {"updates_at_1600": At[aid]["updates_at_1600"],
                                    "argv_normalised": " ".join(argv_norm.get(aid) or []) or None}
                              for aid in [x for x in slots.values() if x]}}
        if not v2["pass"]:
            block("V-2", "a=%s b=%s c=%s" % (v2a, v2b, v2c))

        # V-3
        v3 = {"pass": not missing_slots, "per_attempt": {}}
        s3_vals = set()
        desc_vals = set()
        for slot, aid in slots.items():
            if not aid:
                continue
            A = At[aid]
            ev = self.v3_run(A, check_descriptor=(aid not in term_att_aids) or A["sidecar_present"])
            v3["per_attempt"][aid] = ev
            if not ev["pass"]:
                v3["pass"] = False
            s3_vals.add(str(A["seams"].get("S3")))
            if A["arm"] == "attention" and ev.get("descriptor_checked"):
                desc_vals.add(A["descriptor_sha256"])
        v3["S3_identical"] = len(s3_vals) == 1
        v3["descriptor_identical"] = len(desc_vals) == 1 and None not in desc_vals
        if not v3["S3_identical"] or not v3["descriptor_identical"]:
            v3["pass"] = False
        if not v3["pass"]:
            block("V-3", "; ".join(k for k, v in v3["per_attempt"].items() if not v["pass"]) or
                  "S3/descriptor not identical or slot missing")

        # V-4
        v4 = {"pass": not missing_slots, "per_attempt": {}}
        for aid in full_runs:
            A = At[aid]
            ev = {"pass": A["_eval_complete"], "scored_exec": {k: v.get("scored_exec") for k, v in A["eval"].items()},
                  "problems": {k: {e: x["problems"] for e, x in v["executions"].items() if x["problems"]}
                               for k, v in A["eval"].items()}}
            if A["class"] != "completed":
                ev["pass"] = False
                ev["why"] = "not completed"
            v4["per_attempt"][aid] = ev
            if not ev["pass"]:
                v4["pass"] = False
        if not v4["pass"]:
            block("V-4", "; ".join(k for k, v in v4["per_attempt"].items() if not v["pass"]) or "slot missing")

        # spend cap predicate
        gate_set_complete = all(
            (aid is not None and ((aid in term_att_aids) or (At[aid]["class"] == "completed" and At[aid]["_eval_complete"])))
            for aid in slots.values())
        if spend_cap_hit and not gate_set_complete:
            block("spend_cap", "spend cap reached before the gate set was complete")

        # L-1 / L-2
        l1_count = {}
        l1_per = {}
        l2_per = {}
        for arm in GATE_ARMS:
            c = 0
            for s in GATE_SEEDS:
                aid = slots.get("%s_s%d" % (arm, s))
                if aid and aid not in term_att_aids:
                    l1_per[aid] = {"pass": At[aid]["l1_pass"], "c_train_first5": At[aid]["c_train_first5"],
                                   "c_train_last5": At[aid]["c_train_last5"]}
                    l2_per[aid] = {"pass": At[aid]["l2_pass"], "wm_loss_first5": At[aid]["wm_loss_first5"],
                                   "wm_loss_last5": At[aid]["wm_loss_last5"]}
                    if At[aid]["l1_pass"] is True:
                        c += 1
            l1_count[arm] = c
        l1 = all(l1_count[arm] >= 2 for arm in GATE_ARMS)
        l2 = bool(l2_per) and all(v["pass"] is True for v in l2_per.values()) and not missing_slots

        # comparison §6.2
        cmp_ = self.compare(slots, "r_h")
        shadow = self.compare(slots, "r_step")

        # decision
        failing = []
        outcome = basis = None
        superior = noise_widened = False
        delta = delta_thr = se = None
        shadow_outcome = None
        if reasons:
            row, verdict = 1, "BLOCKED"
        elif terminal_att:
            row, verdict = 2, "PASS"
            outcome, basis = "INFERIOR", "divergence"
            shadow_outcome = "INFERIOR"
        elif not (l1 and l2):
            row, verdict = 3, "FAIL"
            if not l1:
                failing.append("L-1")
            if not l2:
                failing.append("L-2")
        else:
            row, verdict = 4, "PASS"
            if cmp_["delta"] is None:  # cannot happen when V-4 holds; guard
                row, verdict = 1, "BLOCKED"
                block("V-4", "R_H not evaluable")
            else:
                outcome, basis = cmp_["outcome"], "margin"
                superior, noise_widened = cmp_["superior"], cmp_["noise_widened"]
                delta, delta_thr, se = cmp_["delta"], cmp_["delta_threshold"], cmp_["se_pooled"]
                shadow_outcome = shadow["outcome"]
        metric_disagreement = bool(outcome is not None and shadow_outcome is not None and shadow_outcome != outcome)

        # DIV gate key
        div_key = {"pass": not (terminal_att or terminal_cmp or (self.f2_none and any_gate_div)),
                   "retry_pair_seeds": retry_seeds, "terminal_attention_divergence": terminal_att,
                   "terminal_comparator_divergence": terminal_cmp, "f2_none": self.f2_none,
                   "clip_clause_b": "skipped (M-6 null; F-4 per_update_clip_indicator=false)",
                   "per_attempt": {aid: {"diverged": A["diverged"], "class": A["class"],
                                         "evidence": A["divergence_evidence"]}
                                   for aid, A in At.items()}}

        # REF rows
        refs = self.ref_rows(cellinfo, spend_cap_hit, gate_set_complete)

        # M-9
        m9 = self.m9(slots)

        # rh counter
        over_T = 0
        for A in At.values():
            for itk, e in A["eval"].items():
                for f in MASKS:
                    mm = e.get("mask" + f)
                    if mm:
                        over_T += mm.get("over_T", 0)

        gpu_name = gpu_names[0] if gpu_names and len(set(gpu_names)) == 1 else None
        res = {
            "tool": {"name": "verdict_b0.py", "version": TOOL_VERSION, "sha256": sha256_file(os.path.abspath(__file__))},
            "plan_sha256": self.plan_sha, "method_sha256": a.method_sha, "tarball_sha256": a.tarball_sha,
            "venue": a.venue, "gpu_name": gpu_name,
            "deposits": [{"path": d["path"], "sha256": d["sha256"], "seal_line": d["seal_line"],
                          "part": d.get("part"), "extracted": d["extracted"], "problems": d["problems"]}
                         for d in self.deposits],
            "verdict": verdict, "decision_row": row, "failing_ids": failing, "blocked_reason": reasons,
            "blocked_detail": detail,
            "b0_outcome": outcome, "outcome_basis": basis, "superior": superior, "noise_widened": noise_widened,
            "delta": delta, "delta_threshold": delta_thr, "se_pooled": se,
            "rbar_h_attention": cmp_["rbar_attention"], "rbar_h_mlp_matched": cmp_["rbar_mlp_matched"],
            "T": T_HORIZON,
            "comparison_raw": cmp_,
            "shadow_outcome_rstep": shadow_outcome, "metric_disagreement": metric_disagreement,
            "shadow_raw": shadow,
            "budget": {"iterations": BUDGET_IT,
                       "updates_at_1600": {aid: At[aid]["updates_at_1600"] for aid in slots.values() if aid},
                       "parity": v2a, "env_steps_per_iter": self.env_steps_per_iter},
            "scored_set": slots,
            "l1_seeds_passing": l1_count,
            "upstream_facts": self.facts,
            "rh_clips_over_T": over_T,
            "spend_cap_hit": spend_cap_hit, "gate_set_complete": gate_set_complete,
            "venue_consistent": venue_consistent,
            "cells": {"%s_%s_s%d" % k: v for k, v in sorted(cellinfo.items())},
            "duplicate_members_across_deposits": sorted(set(self.store.dups)),
            "V-0": {"pass": v0, "per_log": v0_ev},
            "V-1": v1, "V-2": v2, "V-3": v3, "V-4": v4,
            "L-1": {"pass": l1, "seeds_passing": l1_count, "per_attempt": l1_per},
            "L-2": {"pass": l2, "per_attempt": l2_per},
            "DIV": div_key,
        }
        res.update(refs)
        res["m9_wallclock"] = m9
        res["attempts"] = {aid: self.public_attempt(A) for aid, A in sorted(At.items())}
        return res

    # ---------------------------------------------------------------- gate helpers
    def v1_full(self, A):
        s = A["_series"]
        timing = all(finite_num(s.get("time/hours", {}).get(k)) and finite_num(s.get("time/updates", {}).get(k))
                     for k in CKPTS)
        ev = {"completed": A["class"] == "completed", "no_nonfinite_le_1600": not A["nan"],
              "one_tb_file": A["tb_file_count"] == 1, "logged_point_at_1600": A["logged_point_at_1600"],
              "ckpt_timing_tags": timing, "window_coverage": A["window_coverage"],
              "window_coverage_ok": A["window_coverage"] >= 10}
        ev["pass"] = all(v for k, v in ev.items() if k != "window_coverage")
        ev["mode"] = "full"
        return ev

    def v1_integrity(self, A):
        single = A["tb_file_count"] == 1
        ev_tb = single and A["nan"]
        ev_log = bool(A["divergence_evidence"]["rdiv_final_lines"]) and A["train_log_present"]
        ev = {"attempt_dir_present": A["attempt_dir_present"], "one_tb_file": single,
              "train_log_present": A["train_log_present"], "divergence_evidence_ok": ev_tb or ev_log}
        ev["pass"] = all(ev.values())
        ev["mode"] = "integrity (terminal attention divergence; endpoint-dependent checks exempt)"
        return ev

    def normalise_argv(self, A):
        argv = A.get("argv")
        if not argv:
            return None, "argv line missing"
        out = []
        i = 0
        lr_seen = None
        while i < len(argv):
            t = argv[i]
            if t in ("--run-name", "--seed"):
                i += 2
                continue
            if A["tag"] == "b0lr05" and self.f2_flag and t == self.f2_flag:
                lr_seen = argv[i + 1] if i + 1 < len(argv) else None
                i += 2
                continue
            out.append(t)
            i += 1
        if A["tag"] == "b0lr05":
            try:
                ok = lr_seen is not None and self.lr05 is not None and float(lr_seen) == self.lr05
            except ValueError:
                ok = False
            if not ok:
                return out, "b0lr05 LR flag %s=%s != 0.5 x default (%s)" % (self.f2_flag, lr_seen, self.lr05)
        return out, None

    def v3_run(self, A, check_descriptor=True, ref=False):
        raw = A["_seams_raw"]
        probs = []

        def vals(sid):
            return [v for v in (raw[sid]["log"], raw[sid]["sidecar"]) if v is not None]
        for sid in ("S1", "S2"):
            v = vals(sid)
            if not v or any(x is not True for x in v):
                probs.append("%s not true (%s)" % (sid, raw[sid]))
        v3_ = vals("S3")
        if not v3_ or len(set(str(x) for x in v3_)) != 1:
            probs.append("S3 not recorded/consistent (%s)" % raw["S3"])
        if A["seam_unverified_line"]:
            probs.append("unverified seam line")
        ev = {"seams": {k: v for k, v in raw.items()}}
        if A["arm"] == "attention" and not ref:
            v4_ = vals("S4")
            if not v4_ or any(x != "env_init_state" for x in v4_):
                probs.append("S4 != env_init_state (%s)" % raw["S4"])
            v5_ = vals("S5")
            if not v5_ or any(x is not True for x in v5_):
                probs.append("S5 not true (%s)" % raw["S5"])
            ev["descriptor_checked"] = bool(check_descriptor)
            ev["descriptor_sha256"] = A["descriptor_sha256"]
            if check_descriptor and not A["descriptor_sha256"]:
                probs.append("descriptor sha256 missing")
        ev["problems"] = probs
        ev["pass"] = not probs
        return ev

    def compare(self, slots, key):
        vals = {}
        for arm in GATE_ARMS:
            xs = []
            for s in GATE_SEEDS:
                aid = slots.get("%s_s%d" % (arm, s))
                v = None
                if aid:
                    e = self.attempts[aid]["eval"].get("it0001600", {})
                    v = e.get("mask0.00", {}).get(key)
                xs.append(v)
            vals[arm] = xs
        out = {"metric": key, "values": vals, "delta": None, "delta_threshold": None, "se_pooled": None,
               "outcome": None, "superior": False, "noise_widened": False, "rbar_attention": None,
               "rbar_mlp_matched": None}
        if any(v is None for arm in GATE_ARMS for v in vals[arm]):
            ok = [v for v in vals["attention"] if v is not None]
            om = [v for v in vals["mlp_matched"] if v is not None]
            out["rbar_attention"] = mean(ok) if len(ok) == 3 else None
            out["rbar_mlp_matched"] = mean(om) if len(om) == 3 else None
            return out

        def sd(xs):
            m = mean(xs)
            return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
        ra, rm = mean(vals["attention"]), mean(vals["mlp_matched"])
        sa, sm = sd(vals["attention"]), sd(vals["mlp_matched"])
        se = math.sqrt(sa ** 2 / 3 + sm ** 2 / 3)
        delta = ra - rm
        thr = max(0.05, 2 * se)
        nonin = delta >= -thr
        out.update(rbar_attention=ra, rbar_mlp_matched=rm, s_attention=sa, s_mlp_matched=sm, se_pooled=se,
                   delta=delta, delta_threshold=thr, outcome="NONINFERIOR" if nonin else "INFERIOR",
                   superior=bool(nonin and delta >= max(0.02, 2 * se)),
                   noise_widened=bool(nonin and delta < -0.05))
        return out

    def ref_rows(self, cellinfo, spend_cap_hit, gate_set_complete):
        At = self.attempts
        ci = cellinfo.get(("b0", REF_ARM, 0))
        aid = ci["scored"] if ci else None
        ref_attempts = ci["attempts"] if ci else []
        common = {"reference_cell": "b0_%s_s0" % REF_ARM, "attempts": {x: At[x]["class"] for x in ref_attempts},
                  "diverged": {x: At[x]["diverged"] for x in ref_attempts}, "reported_only": True}
        if aid is None:
            status = "incomplete" if (spend_cap_hit and gate_set_complete) else (
                "missing" if not ref_attempts else "not_completed")
            out = {}
            for k in ("REF-1", "REF-2", "REF-3", "REF-4"):
                out[k] = dict(common, status=status, pass_=None)
                out[k]["pass"] = False
                del out[k]["pass_"]
            # seams still reportable from the last attempt
            if ref_attempts:
                out["REF-2"]["per_attempt"] = {ref_attempts[-1]: self.v3_run(At[ref_attempts[-1]], ref=True)}
            return out
        A = At[aid]
        A["in_scored_set"] = False
        r1 = self.v1_full(A)
        r2 = self.v3_run(A, ref=True)
        r3_ok = A["_eval_complete"]
        r4 = {"l1_pass": A["l1_pass"], "l2_pass": A["l2_pass"]}
        return {
            "REF-1": dict(common, status="evaluated", per_attempt={aid: r1}, **{"pass": r1["pass"] and not A["diverged"]}),
            "REF-2": dict(common, status="evaluated", per_attempt={aid: r2}, **{"pass": r2["pass"]}),
            "REF-3": dict(common, status="evaluated", per_attempt={aid: {"scored_exec": {k: v.get("scored_exec") for k, v in A["eval"].items()}}},
                          **{"pass": r3_ok}),
            "REF-4": dict(common, status="evaluated", per_attempt={aid: r4},
                          **{"pass": r4["l1_pass"] is True and r4["l2_pass"] is True}),
        }

    def m9(self, slots):
        At = self.attempts
        hs = []
        for slot, aid in slots.items():
            h = At[aid]["hours_at_1600"] if aid else None
            hs.append(h if finite_num(h) else None)
        W = min(hs) if hs and all(h is not None for h in hs) else None
        per = {}
        for slot, aid in slots.items():
            if not aid:
                continue
            A = At[aid]
            per[aid] = None
            if W is None:
                continue
            hk = [A["hours_at_ckpt"].get(str(k)) for k in CKPTS]
            rk = [A["eval"].get("it%07d" % k, {}).get("mask0.00", {}).get("r_h") for k in CKPTS]
            if any(not finite_num(x) for x in hk) or any(x is None for x in rk):
                continue
            if W < hk[0]:
                continue
            val = None
            for i in range(3):
                if hk[i] <= W <= hk[i + 1]:
                    val = rk[i + 1] if hk[i + 1] == hk[i] else rk[i] + (rk[i + 1] - rk[i]) * (W - hk[i]) / (hk[i + 1] - hk[i])
                    break
            per[aid] = val

        def arm_val(arm):
            xs = [per.get(slots.get("%s_s%d" % (arm, s))) for s in GATE_SEEDS]
            return mean(xs) if all(x is not None for x in xs) else None
        return {"W_hours": W, "r_h_attention_at_W": arm_val("attention"),
                "r_h_mlp_matched_at_W": arm_val("mlp_matched"), "per_run": per}

    def public_attempt(self, A):
        keys = ["tag", "arm", "seed", "attempt", "class", "scored", "in_scored_set", "harness_stop", "harness_stop_record",
                "driver_class", "class_disagreement", "infra_cause", "diverged", "divergence_evidence",
                "post_endpoint_anomaly", "completion", "reached_1600", "nan", "nonfinite_le_1600", "updates_at_1600",
                "seams", "descriptor_sha256", "params_policy", "params_line", "argv",
                "c_train_first5", "c_train_last5", "nret_train_first5", "nret_train_last5", "elen_first5", "elen_last5",
                "wm_loss_first5", "wm_loss_last5", "l1_pass", "l2_pass", "logged_points_le_1600", "window_coverage",
                "clip_fraction_last25", "grad_norm_max", "action_abs_mean_at_1600",
                "ms_per_update", "it_per_s", "env_steps_per_s", "s_per_iter_mean_400_1600", "peak_mem_mib",
                "hours_at_1600", "hours_at_ckpt", "updates_at_ckpt", "tb_files", "tb_file_count", "tb_read_info",
                "train_log_present", "attempt_dir_present", "live_dir_present", "sidecar_present",
                "pre_endpoint_final_exception_lines", "eval", "aulc_h"]
        out = {k: A.get(k) for k in keys}
        out["seams"] = {k: A["seams"].get(k) for k in ("S1", "S2", "S3", "S4", "S5")}
        ev = {}
        for itk, e in A["eval"].items():
            e2 = {}
            for k, v in e.items():
                if isinstance(v, dict) and "over_T" in v:
                    v = {kk: vv for kk, vv in v.items() if kk != "over_T"}
                e2[k] = v
            ev[itk] = e2
        out["eval"] = ev
        return out


def parse_gpu_name(text):
    names = []
    for line in text.splitlines():
        m = re.match(r"^\|\s+(\d+)\s+(.+?)\s+(On|Off)\s+\|", line)
        if m:
            names.append(m.group(2).strip())
    return " + ".join(names) if names else None


def parse_gpumem(text):
    best = None
    for line in text.splitlines()[1:]:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            continue
        m = re.match(r"^(\d+(?:\.\d+)?)", parts[1])
        if m:
            v = float(m.group(1))
            best = v if best is None else max(best, v)
    return best


def parse_facts(path):
    text = read_text(path)
    blocks = re.findall(r"```json\s*\n(.*?)```", text, flags=re.S)
    if not blocks:
        raise SystemExit("no ```json block in facts file %s" % path)
    return json.loads(blocks[-1])


def fmt(x):
    if x is None:
        return "null"
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, float):
        return repr(x)
    return str(x)


def verdict_line(res):
    return ("B0_VERDICT verdict=%s outcome=%s basis=%s delta=%s delta_thr=%s failing_ids=[%s] blocked=[%s]" % (
        res["verdict"], fmt(res["b0_outcome"]), fmt(res["outcome_basis"]), fmt(res["delta"]),
        fmt(res["delta_threshold"]), ",".join(res["failing_ids"]), ",".join(res["blocked_reason"])))


def write_runs_log(path, v, res, line):
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    blocks = []
    for d in v.deposits:
        b = ["=== B0 verdict run %s tool=%s sha256=%s ===" % (now, TOOL_VERSION, res["tool"]["sha256"]),
             "DEPOSIT path=%s sha256=%s part=%s extracted=%s" % (d["path"], d["sha256"], d.get("part"), d["extracted"]),
             "SEAL_LINE %s" % (d["seal_line"] or "none")]
        for p in d["problems"]:
            b.append("PROBLEM %s" % p)
        for aid, A in sorted(v.attempts.items()):
            files = [rel for rel, (_ap, di) in v.store.files.items() if di == d["index"] and aid in rel]
            if not files:
                continue
            b.append("ATTEMPT %s class=%s driver_class=%s disagreement=%s completed=%s diverged=%s scored=%s "
                     "in_scored_set=%s infra_cause=%s post_endpoint_anomalies=%d" % (
                         aid, A["class"], A["driver_class"], A["class_disagreement"], A["class"] == "completed",
                         A["diverged"], A["scored"], A["in_scored_set"], A["infra_cause"], len(A["post_endpoint_anomaly"])))
        b.append(line)
        b.append("=== end ===")
        blocks.append("\n".join(b) + "\n")
    with open(path, "a", encoding="utf-8") as fh:
        for b in blocks:
            fh.write(b)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--deposit", action="append", default=[], required=True)
    ap.add_argument("--seal-log", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--method-sha", required=True)
    ap.add_argument("--tarball-sha", required=True)
    ap.add_argument("--facts", required=True)
    ap.add_argument("--venue", choices=("colab", "xn4090"), required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--runs-log", required=True)
    ap.add_argument("--work", required=True)
    a = ap.parse_args(argv)
    v = Verdict(a)
    res = v.run()
    line = verdict_line(res)
    res["verdict_line"] = line
    tmp = a.out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=False, default=str, allow_nan=False)
    os.replace(tmp, a.out)
    write_runs_log(a.runs_log, v, res, line)
    for r in res["blocked_detail"]:
        log("[verdict_b0] " + r)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
