"""P5 B2 driver helper (CR-B2-1 (e)); stdlib only, run as `$PY -I b2_driver_helper.py <cmd> ...`.

Used by packets/P5/b2_driver.sh for scheduling (spikes/B2/PLAN.md §4.1, §4.2, §10) and the per-exec eval file
check (§4.2 eval-only cells, §4.3). Attempt classification, the CPU-test check and the GPU-name parse are the
frozen CR-B0-1 helper's (packets/P4/b0_driver_helper.py, imported unchanged): B0 PLAN §3.3 applies unchanged
(PLAN §4.2). The driver class decides scheduling only; verdict_b2.py recomputes every class from the evidence.

Commands
  next       --state F --total-hours H [--spend-cap 6]
             -> "UEVAL <P4 AID>" | "UPERM <P4 AID>" | "FINISH <AID> <tag> <cfg> <arm> <diverged>"
                | "CELL <tag> <cfg> <arm> <seed> <N> <newcell>" | "DONE" | "SPENDCAP"
  evalcheck  --dir D --run RUN --arm ARM --mode full|mask0   -> exit 0: every expected file and a final exit=0;
             1: a next exec is authorized (recorded non-zero exit or a missing file); 2: not authorized
  classify   (frozen CR-B0-1 helper)   cputest (frozen, 14 PASS / 3 SKIP)   gpuname (frozen)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
P4 = HERE.parent / "P4"
sys.path.insert(0, str(P4))
import b0_driver_helper as b0h  # noqa: E402  (frozen CR-B0-1 file)

CFG = {"b0": "/content/junior/configs/b0_microbench.yaml", "b2mt": "/content/junior/configs/b2_mtrain.yaml",
       "b2idx": "/content/junior/configs/b2_idx.yaml"}
SEEDS = (0, 1, 2)
# PLAN §4.1 step 2 order
U_AIDS = tuple(f"b0_{arm}_s{s}_a1" for s in SEEDS for arm in ("attention", "mlp_matched"))
# PLAN §4.1 steps 4-5
CELLS = tuple([("b2mt", arm, s) for s in SEEDS for arm in ("attention", "mlp_mind")] + [("b2idx", "attention", s) for s in SEEDS])
MASK_SEEDS = (7100, 7101, 7102)
MASK_FRACS = ("0.10", "0.20")
EXIT_RE = re.compile(r"^exit=(-?\d+)\s*$", re.M)


def records(state: Path, kind: str) -> list[list[str]]:
    out = []
    if state.exists():
        for ln in state.read_text().splitlines():
            p = ln.split()
            if p and p[0] == kind:
                out.append(p)
    return out


def next_item(a) -> None:
    st = Path(a.state)
    ueval = {p[1] for p in records(st, "UEVAL") if len(p) >= 2}
    perm = {p[1] for p in records(st, "PERM") if len(p) >= 2}
    # the cap (PLAN §10) is checked before every new work item: U evals, U PERM checks and new cells
    for aid in U_AIDS:
        if aid not in ueval:
            print("SPENDCAP" if a.total_hours >= a.spend_cap else f"UEVAL {aid}")
            return
    for aid in U_AIDS:
        if f"b2u_{aid}" not in perm:
            print("SPENDCAP" if a.total_hours >= a.spend_cap else f"UPERM {aid}")
            return
    attempts = b0h.load_attempts(st)
    # a completed attempt whose evals / PERM were interrupted (no EVALDONE) is finished first, before any new cell
    done = {p[1] for p in records(st, "EVALDONE") if len(p) >= 2}
    for aid, _cls, div, completed in attempts:
        if completed and aid not in done:
            tag, rest = aid.split("_", 1)
            arm = rest.rsplit("_s", 1)[0]
            print("FINISH", aid, tag, CFG[tag], arm, str(div).lower())
            return
    for tag, arm, seed in CELLS:
        fin, _div, n = b0h.cell_status(f"{tag}_{arm}_s{seed}", attempts)
        if not fin:
            if n == 0 and a.total_hours >= a.spend_cap:  # cap checked between cells only (PLAN §10)
                print("SPENDCAP")
                return
            print("CELL", tag, CFG[tag], arm, seed, n + 1, int(n == 0))
            return
    print("DONE")


def expected_files(run: str, arm: str, mode: str) -> list[str]:
    conds = [("0.00", 0)] + ([(f, s) for s in MASK_SEEDS for f in MASK_FRACS] if mode == "full" else [])
    out = []
    for f, s in conds:
        out += [f"{run}_{arm}_mask{f}_ms{s}.json", f"maskstream_mask{f}_ms{s}.npz", f"maskstream_mask{f}_ms{s}.json"]
    return out


def evalcheck(a) -> None:
    d = Path(a.dir)
    log = (d / "eval.log").read_text(errors="replace") if (d / "eval.log").exists() else ""
    codes = EXIT_RE.findall(log)
    missing = [f for f in expected_files(a.run, a.arm, a.mode) if not (d / f).is_file()]
    ok = bool(codes) and codes[-1] == "0" and not missing
    # PLAN §4.2: a next exec only after a recorded non-zero exit or a missing expected file (same rule as verdict_b2)
    retry = not ok and (bool(missing) or (bool(codes) and codes[-1] != "0"))
    print(f"evalcheck dir={d} mode={a.mode} exit={codes[-1] if codes else 'none'} missing={len(missing)} "
          f"ok={str(ok).lower()} retry_authorized={str(retry).lower()}")
    sys.exit(0 if ok else (1 if retry else 2))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("next")
    p.add_argument("--state", required=True)
    p.add_argument("--total-hours", type=float, required=True)
    p.add_argument("--spend-cap", type=float, default=6.0)
    p = sub.add_parser("evalcheck")
    for k in ("--dir", "--run", "--arm"):
        p.add_argument(k, required=True)
    p.add_argument("--mode", choices=("full", "mask0"), required=True)
    p = sub.add_parser("classify")
    for k in ("--aid", "--log", "--tb-dir", "--harness", "--sidecar", "--out"):
        p.add_argument(k, required=True)
    p = sub.add_parser("cputest")
    p.add_argument("--log", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("gpuname")
    p.add_argument("--smi", required=True)
    a = ap.parse_args()
    {"next": next_item, "evalcheck": evalcheck, "classify": b0h.classify, "cputest": b0h.cputest,
     "gpuname": b0h.gpuname}[a.cmd](a)


if __name__ == "__main__":
    main()
