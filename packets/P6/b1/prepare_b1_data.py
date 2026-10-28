"""GPU-host data step for B1 (RT job and arms job): RT-a retarget of the clip slots, QA, npz for the used clips.

Runtime only (X-002): the CSVs are read into memory from ``$HF_ENDPOINT`` at the pinned dataset revision; the npz files
go to ``--out-npz`` on the GPU host and are never deposited. Writes only aggregate QA numbers to ``--qa-out``.

Slot rule ``plan`` (spikes/B1-RT/PLAN.md §3, default): per slot, the first clip is used if it passes RT-4 QA, else the
pre-declared replacement; a slot whose two clips both fail is dropped. Fewer than 3 usable slots -> exit 3 (RT-b
trigger, BLOCKED). Slot rule ``first`` is valid only under a sealed Class-2 amendment that waives RT-4 (ASK option C):
the first clip of every slot is used, its QA is recorded, and nothing is selected on QA.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # packets/P6/b1/<file> -> program root
sys.path.insert(0, str(ROOT / "spikes" / "B1-RT"))
import retarget_rta as R  # noqa: E402
import rt_cpu as T  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev", required=True, help="dataset revision (commit sha) recorded by the box RT-4 run")
    ap.add_argument("--out-npz", required=True)
    ap.add_argument("--qa-out", required=True)
    ap.add_argument("--expect", default=None, help="box results-cpu JSON: CSV sha256 per clip must match")
    ap.add_argument("--slot-rule", choices=("plan", "first"), default="plan")
    a = ap.parse_args()
    expect = {}
    if a.expect:
        box = json.loads(Path(a.expect).read_text())
        for rec in box["RT-4"]["slots"].values():
            for t in rec["tried"]:
                expect[t["clip"]] = t["csv_sha256"]
    out_dir = Path(a.out_npz)
    out_dir.mkdir(parents=True, exist_ok=True)
    ctx = R.make_ctx()
    res = {"rev": a.rev, "slot_rule": a.slot_rule, "sign_check_ok": ctx.check["ok"], "scale": ctx.scale, "slots": {},
           "csv_sha_mismatch": []}
    for slot, first, repl in T.SLOTS:
        rec = {"tried": [], "used": None}
        for name in ((first,) if a.slot_rule == "first" else (first, repl)):
            raw, h = T.fetch_clip(name, a.rev)
            if expect and expect.get(name) not in (None, h):
                res["csv_sha_mismatch"].append(name)
            qa, mot = T.clip_qa(raw, ctx)
            qa.update(clip=name, csv_sha256=h)
            rec["tried"].append(qa)
            if qa["pass"] or a.slot_rule == "first":
                R.write_npz(out_dir / f"{name}.npz", mot, ctx, f"lafan1-retarget:{name}")
                rec["used"] = name
                break
        res["slots"][slot] = rec
    used = [r["used"] for r in res["slots"].values() if r["used"]]
    res["used_clips"] = used
    res["n_slots"] = len(used)
    need = 4 if a.slot_rule == "first" else 3
    res["pass"] = bool(ctx.check["ok"] and len(used) >= need and not res["csv_sha_mismatch"])
    Path(a.qa_out).write_text(json.dumps(res, indent=2, default=float))
    print(f"B1DATA pass={res['pass']} used={','.join(used)} csv_sha_mismatch={res['csv_sha_mismatch']}", flush=True)
    sys.exit(0 if res["pass"] else 3)


if __name__ == "__main__":
    main()
