"""P4 B0 driver helper (CR-B0-1 (d)); stdlib only, run as `$PY -I b0_driver_helper.py <cmd> ...`.

Used by packets/P4/b0_driver.sh for scheduling and for the driver's own attempt classification
(spikes/B0/PLAN.md §3.2, §3.3, §6.3). The driver class decides retries only. The verdict tool
(spikes/B0/verdict/verdict_b0.py) recomputes every class from the deposited evidence.

Commands
  next      --state F --total-hours H [--spend-cap 7]   -> "CELL <tag> <cfg> <arm> <seed> <N> <newcell>" | "DONE" | "SPENDCAP"
  classify  --aid A --log F --tb-dir D --harness F --sidecar F --out F   -> prints "<class> <diverged> <completed>"
  cputest   --log F --out F                               -> exit 0 iff 14 PASS lines, 3 of them preceded by SKIP
  gpuname   --smi F                                       -> GPU name from the nvidia-smi header
"""

from __future__ import annotations

import argparse
import math
import re
import struct
import sys
from pathlib import Path

CFG = {"b0": "/content/junior/configs/b0_microbench.yaml", "b0lr05": "/content/junior/configs/b0_microbench_lr05.yaml"}
GATE_ARMS = ("attention", "mlp_matched")
SEEDS = (0, 1, 2)
INFRA_CAP = 2
ENDPOINT = re.compile(r"^it 1600 \|")
R_DIV = re.compile(r"(?i)\b(nan|inf)\b|non-?finite|not finite")  # PLAN §3.3, final exception line only
R_OOM = re.compile(r"(?i)out[ -]of[ -]memory|OutOfMemoryError")  # same pattern as verdict_b0.py
R_SEAM_BAD = re.compile(r"^\[seam\] .*=(unverified|false)\b")


# ------------------------------------------------------------------ tb reader (TF event files)
def _varint(b: bytes, i: int) -> tuple[int, int]:
    r = s = 0
    while True:
        c = b[i]
        i += 1
        r |= (c & 0x7F) << s
        s += 7
        if not c & 0x80:
            return r, i


def _fields(b: bytes):
    i = 0
    while i < len(b):
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
            n, i = _varint(b, i)
            v = b[i:i + n]
            i += n
        else:
            raise ValueError(f"wire type {t}")
        yield f, t, v


def _tensor_float(b: bytes):
    dtype, vals, content = None, [], b""
    for f, t, v in _fields(b):
        if f == 1 and t == 0:
            dtype = v
        elif f == 5 and t == 5:
            vals.append(struct.unpack("<f", v)[0])
        elif f == 5 and t == 2:
            vals += list(struct.unpack("<%df" % (len(v) // 4), v))
        elif f == 6 and t == 1:
            vals.append(struct.unpack("<d", v)[0])
        elif f == 4 and t == 2:
            content = v
    if vals:
        return vals[0]
    if content and dtype == 1 and len(content) == 4:
        return struct.unpack("<f", content)[0]
    if content and dtype == 2 and len(content) == 8:
        return struct.unpack("<d", content)[0]
    return None


def read_scalars(path: Path) -> list[tuple[str, int, float, float]]:
    """(tag, step, value, wall_time) for every scalar record; truncated tails are ignored."""
    out, data, p = [], path.read_bytes(), 0
    while p + 12 <= len(data):
        n = struct.unpack("<Q", data[p:p + 8])[0]
        rec = data[p + 12:p + 12 + n]
        if len(rec) < n:
            break
        p += 12 + n + 4
        step, summ, wall = 0, None, 0.0
        for f, t, v in _fields(rec):
            if f == 1 and t == 1:
                wall = struct.unpack("<d", v)[0]
            elif f == 2 and t == 0:
                step = v
            elif f == 5 and t == 2:
                summ = v
        if summ is None:
            continue
        for f, t, v in _fields(summ):
            if f != 1:
                continue
            tag = val = None
            for f2, t2, v2 in _fields(v):
                if f2 == 1:
                    tag = v2.decode()
                elif f2 == 2 and t2 == 5:
                    val = struct.unpack("<f", v2)[0]
                elif f2 == 8 and t2 == 2:
                    val = _tensor_float(v2)
            if tag is not None and val is not None:
                out.append((tag, step, val, wall))
    return out


def tb_nonfinite_upto(tb_dir: Path, last_step: int = 1600) -> tuple[bool, str]:
    """PLAN §5 TB rule first (duplicate step: latest wall time wins), then the §3.3/§6.3 (a) non-finite test."""
    files = sorted(tb_dir.glob("events.out.tfevents.*")) if tb_dir.is_dir() else []
    latest: dict[tuple[str, int], tuple[float, float]] = {}
    for f in files:
        for tag, step, val, wall in read_scalars(f):
            if (tag, step) not in latest or wall >= latest[(tag, step)][0]:
                latest[(tag, step)] = (wall, val)
    bad = sorted((step, tag, v) for (tag, step), (_, v) in latest.items() if step <= last_step and not math.isfinite(v))
    if bad:
        return True, f"{bad[0][1]}@{bad[0][0]}={bad[0][2]}"
    return False, f"files={len(files)}"


# ------------------------------------------------------------------ log parsing
def pre_endpoint_lines(log: Path) -> tuple[list[str], bool]:
    lines = log.read_text(errors="replace").splitlines() if log.exists() else []
    for i, ln in enumerate(lines):
        if ENDPOINT.match(ln):
            return lines[:i], True
    return lines, False


def final_exception_lines(lines: list[str]) -> list[str]:
    """Final `ExceptionType: message` line of every traceback in `lines` (body lines are indented)."""
    out = []
    starts = [i for i, ln in enumerate(lines) if ln.startswith("Traceback (most recent call last):")]
    for i in starts:
        for ln in lines[i + 1:]:
            if ln and not ln[0].isspace() and not ln.startswith("Traceback"):
                out.append(ln.strip())
                break
    return out


def kv(path: Path) -> dict[str, str]:
    d: dict[str, str] = {}
    if path.exists():
        for ln in path.read_text().splitlines():
            if "=" in ln:
                k, v = ln.split("=", 1)
                d[k.strip()] = v.split("#", 1)[0].strip()
    return d


def classify(a) -> None:
    hs = kv(Path(a.harness))
    pre, seen = pre_endpoint_lines(Path(a.log))
    excs = final_exception_lines(pre)  # every pre-endpoint traceback is tested (as verdict_b0.py does)
    exc = excs[-1] if excs else None
    nan_tb, nan_detail = tb_nonfinite_upto(Path(a.tb_dir))
    sidecar = Path(a.sidecar).exists()
    timeout = hs.get("harness_stop_timeout") == "true"
    stable = hs.get("ckpt_stable") == "true"
    completed = seen and stable and sidecar and not timeout
    exc_div = any(R_DIV.search(e) for e in excs)
    diverged = nan_tb or exc_div
    cause = "none"
    if completed:
        cls = "completed"
    elif diverged:
        cls = "DIV"
    elif any(R_OOM.search(e) for e in excs):
        cls = "OOM"
    elif any(R_SEAM_BAD.match(ln) for ln in pre):
        cls = "SEAM"
    else:
        cls = "INFRA"
        full = Path(a.log).read_text(errors="replace") if Path(a.log).exists() else ""
        if timeout:
            cause = "harness_stop_timeout"
        elif "[INFO] max_hours reached, stopping" in full and not seen:
            cause = "safety_cap"
        elif seen and not stable:
            cause = "ckpt_unstable"
        elif seen and not sidecar:
            cause = "sidecar_missing"
        elif exc:
            cause = "other_traceback"
        else:
            cause = "no_endpoint"
    rows = {
        "aid": a.aid, "completed": str(completed).lower(), "driver_class": cls,
        "driver_diverged": str(diverged).lower(), "tb_nonfinite_le_1600": f"{str(nan_tb).lower()} ({nan_detail})",
        "endpoint_line_seen": str(seen).lower(), "sidecar": "present" if sidecar else "missing",
        "infra_cause": cause, "final_exception_line": exc or "none",
    }
    with open(a.out, "a") as f:
        for k, v in rows.items():
            f.write(f"{k}={v}\n")
    print(cls, str(diverged).lower(), str(completed).lower())


# ------------------------------------------------------------------ schedule (PLAN §3.2, §3.3, §6.3)
def load_attempts(state: Path) -> list[tuple[str, str, bool, bool]]:
    out = []
    if state.exists():
        for ln in state.read_text().splitlines():
            p = ln.split()
            if len(p) >= 5 and p[0] == "ATTEMPT":
                out.append((p[1], p[2], p[3] == "true", p[4] == "true"))
    return out


def cell_status(cell: str, attempts) -> tuple[bool, bool, int]:
    """(finished, divergent, n_attempts) for cell `<tag>_<arm>_s<seed>`."""
    mine = [x for x in attempts if x[0].rsplit("_a", 1)[0] == cell]
    n = len(mine)
    if not mine:
        return False, False, 0
    aid, cls, div, _ = mine[-1]
    if cls in ("completed", "DIV", "OOM", "SEAM"):
        return True, cls == "DIV" or div, n
    return sum(1 for x in mine if x[1] == "INFRA") >= INFRA_CAP, False, n


def schedule(attempts) -> list[tuple[str, str, int]]:
    """Ordered cells (tag, arm, seed) as far as they are determined by the history."""
    order: list[tuple[str, str, int]] = []
    for s in SEEDS:
        pair = [("b0", arm, s) for arm in GATE_ARMS]
        order += pair
        st = [cell_status(f"{t}_{arm}_s{sd}", attempts) for t, arm, sd in pair]
        if not all(x[0] for x in st):
            return order  # later cells wait for this pair (retry pair runs immediately after it)
        if any(x[1] for x in st):
            order += [("b0lr05", arm, s) for arm in GATE_ARMS]
    order.append(("b0", "mlp_upstream", 0))
    return order


def next_cell(a) -> None:
    attempts = load_attempts(Path(a.state))
    for tag, arm, seed in schedule(attempts):
        fin, _, n = cell_status(f"{tag}_{arm}_s{seed}", attempts)
        if not fin:
            if n == 0 and a.total_hours >= a.spend_cap:  # cap checked between cells only (PLAN §9)
                print("SPENDCAP")
                return
            print("CELL", tag, CFG[tag], arm, seed, n + 1, int(n == 0))
            return
    print("DONE")


def cputest(a) -> None:
    lines = Path(a.log).read_text(errors="replace").splitlines()
    n_pass = sum(1 for ln in lines if ln.startswith("PASS"))
    n_skip = sum(1 for i, ln in enumerate(lines) if ln.startswith("PASS") and i > 0 and lines[i - 1].startswith("SKIP"))
    ok = n_pass == 14 and n_skip == 3
    Path(a.out).write_text(f"pass_lines={n_pass} skip_before_pass={n_skip} expected=14/3 ok={str(ok).lower()}\n")
    sys.exit(0 if ok else 1)


def gpuname(a) -> None:
    for ln in Path(a.smi).read_text(errors="replace").splitlines():
        m = re.match(r"^\|\s+\d+\s+(.+?)\s+(On|Off)\s+\|", ln)
        if m:
            print(m.group(1).replace(" ", "_"))
            return
    print("unknown")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("next")
    p.add_argument("--state", required=True)
    p.add_argument("--total-hours", type=float, required=True)
    p.add_argument("--spend-cap", type=float, default=7.0)
    p = sub.add_parser("classify")
    for k in ("--aid", "--log", "--tb-dir", "--harness", "--sidecar", "--out"):
        p.add_argument(k, required=True)
    p = sub.add_parser("cputest")
    p.add_argument("--log", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("gpuname")
    p.add_argument("--smi", required=True)
    a = ap.parse_args()
    {"next": next_cell, "classify": classify, "cputest": cputest, "gpuname": gpuname}[a.cmd](a)


if __name__ == "__main__":
    main()
