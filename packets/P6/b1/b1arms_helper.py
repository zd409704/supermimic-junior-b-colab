"""B1 arms driver helper (packets/P6/b1arms_driver.sh; spikes/B1/PLAN.md §4, §6, §7). Stdlib only.

    python b1arms_helper.py classify --aid <AID> --log logs/train_<AID>.log --tb-json meta/tb_<AID>.json \
        --harness meta/harness_stop_<AID>.txt --sidecar logs/<RUN>/junior_policy.json [--spend-cap-stop]
        -> prints "<CLASS> <COMPLETED>"; CLASS in COMPLETED | NONFINITE | SPEND_CAP | INFRA
    python b1arms_helper.py srcsha --expect <hex> --out <file> <candidate>...
        -> prints the first candidate whose sha256 equals --expect, or nothing (exit 3)

PLAN §7: attempt 2 only after an INFRA failure before the endpoint. A run that becomes non-finite is a result
(NONFINITE, no retry). A run stopped by the spend cap is SPEND_CAP (no retry). Completion = PLAN B0 §4.3.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ENDPOINT = re.compile(r"^it 1600 \|", re.M)
BUDGET_IT = 1600


def kv(path: Path) -> dict:
    out = {}
    if path.exists():
        for line in path.read_text(errors="replace").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def nonfinite_upto(tb_json: Path, last: int = BUDGET_IT) -> list[str]:
    if not tb_json.exists():
        return []
    try:
        sc = json.loads(tb_json.read_text())
    except ValueError:
        return []
    bad = []
    for tag, pts in sc.items():
        for s, x in pts:
            if int(s) <= last and not math.isfinite(float(x)):
                bad.append(tag)
                break
    return sorted(bad)


def classify(a) -> tuple[str, bool]:
    text = Path(a.log).read_text(errors="replace") if Path(a.log).exists() else ""
    hs = kv(Path(a.harness))
    completed = (bool(ENDPOINT.search(text)) and hs.get("ckpt_stable") == "true"
                 and hs.get("harness_stop_timeout") != "true" and Path(a.sidecar).exists())
    bad = nonfinite_upto(Path(a.tb_json))
    if bad:
        return "NONFINITE", False
    if completed:
        return "COMPLETED", True
    if a.spend_cap_stop:
        return "SPEND_CAP", False
    return "INFRA", False


def sha256(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("classify")
    c.add_argument("--aid", required=True)
    c.add_argument("--log", required=True)
    c.add_argument("--tb-json", required=True)
    c.add_argument("--harness", required=True)
    c.add_argument("--sidecar", required=True)
    c.add_argument("--spend-cap-stop", action="store_true")
    s = sub.add_parser("srcsha")
    s.add_argument("--expect", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("candidates", nargs="*")
    a = ap.parse_args()
    if a.cmd == "classify":
        cls, done = classify(a)
        print(f"{cls} {str(done).lower()}")
        return
    lines, hit = [f"expected_sha256={a.expect}"], None
    for p in a.candidates:
        if not Path(p).is_file():
            lines.append(f"candidate={p} missing")
            continue
        h = sha256(p)
        lines.append(f"candidate={p} sha256={h} match={str(h == a.expect).lower()}")
        if hit is None and h == a.expect:
            hit = p
    lines.append(f"used={hit if hit else 'none'}")
    with open(a.out, "a") as f:
        f.write("\n".join(lines) + "\n")
    if hit is None:
        sys.exit(3)
    print(hit)


if __name__ == "__main__":
    main()
