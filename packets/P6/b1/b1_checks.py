"""Post-run checks on the GPU host (spikes/B1-RT/PLAN.md §2 RT-7 / RT-8 (a)); also reused by the B1 arms driver.

    python b1_checks.py rt7 --run-dir logs/<run> --log logs/train_<run>.log --out meta/rt7_<arm>.json
    python b1_checks.py rt8eval --eval-dir <dir> --run <run> --out meta/rt8_eval_<arm>.json
    python b1_checks.py tbdump --run-dir logs/<run> --out meta/tb_<run>.json      # all scalars, for the bundle
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def tb_scalars(run_dir: Path) -> dict[str, list[tuple[int, float]]]:
    from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

    files = sorted((run_dir / "tb").glob("events.*"))
    out: dict[str, list[tuple[int, float]]] = {}
    for f in files:
        ea = EventAccumulator(str(f), size_guidance={"scalars": 0})
        ea.Reload()
        for tag in ea.Tags().get("scalars", []):
            out.setdefault(tag, []).extend((int(e.step), float(e.value)) for e in ea.Scalars(tag))
    for k in out:
        out[k].sort()
    return out


def _mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def rt7(run_dir: Path, log: Path) -> dict:
    sc = tb_scalars(run_dir)
    text = log.read_text(errors="replace") if log.exists() else ""
    nonfinite = sorted({k for k, v in sc.items() for _, x in v if not math.isfinite(x)})
    wm = [x for _, x in sc.get("wm/state_loss", [])]
    ret = dict(sc.get("train/episode_norm_return", []))
    ln = dict(sc.get("train/episode_len", []))
    c = [(s, ret[s] * ln[s]) for s in sorted(ret) if s in ln and s >= 100]
    side = run_dir / "junior_policy.json"
    seam = json.loads(side.read_text()).get("seam", {}) if side.exists() else {}
    res = {
        "run_dir": str(run_dir), "traceback": "Traceback (most recent call last)" in text, "nonfinite_tags": nonfinite,
        "n_tb_tags": len(sc), "last_iteration": max((s for v in sc.values() for s, _ in v), default=None),
        "wm_first3": _mean(wm[:3]), "wm_last3": _mean(wm[-3:]), "n_wm_windows": len(wm),
        "c_first3": _mean([x for _, x in c[:3]]), "c_last3": _mean([x for _, x in c[-3:]]), "n_c_windows": len(c),
        "ckpt_latest": (run_dir / "ckpt_latest.pt").exists(), "sidecar": side.exists(),
        "seam": {k: seam.get(k) for k in ("S1_joint_order_match", "S2_term_major_ok", "S5_env_action_scale_match")},
    }
    res["checks"] = {
        "no_exception_finite": (not res["traceback"]) and not nonfinite and len(sc) > 0,
        "wm_loss_decreases": len(wm) >= 6 and res["wm_last3"] < res["wm_first3"],
        "cum_return_rises": len(c) >= 6 and res["c_last3"] > res["c_first3"],
        "ckpt_and_sidecar": res["ckpt_latest"] and res["sidecar"] and all(v is True for v in res["seam"].values()),
    }
    res["pass"] = all(res["checks"].values())
    return res


def rt8eval(eval_dir: Path, run: str) -> dict:
    files = sorted(eval_dir.glob(f"{run}_*_mask*.json"))
    per = {}
    for f in files:
        d = json.loads(f.read_text())
        rets = [c["norm_return"] for c in d["clips"]]
        per[f.name] = {"n_clips": len(rets), "finite": all(math.isfinite(x) for x in rets), "summary": d["summary"]}
    masks = sorted({f.name.rsplit("_mask", 1)[1][:-5] for f in files})
    res = {"run": run, "files": per, "masks": masks}
    res["pass"] = bool(masks == ["0.00", "0.10", "0.20"] and all(v["finite"] and v["n_clips"] > 0 for v in per.values()))
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a7 = sub.add_parser("rt7")
    a7.add_argument("--run-dir", required=True)
    a7.add_argument("--log", required=True)
    a7.add_argument("--out", required=True)
    a8 = sub.add_parser("rt8eval")
    a8.add_argument("--eval-dir", required=True)
    a8.add_argument("--run", required=True)
    a8.add_argument("--out", required=True)
    td = sub.add_parser("tbdump")
    td.add_argument("--run-dir", required=True)
    td.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "rt7":
        res = rt7(Path(a.run_dir), Path(a.log))
        print(f"RT7 run={Path(a.run_dir).name} pass={res['pass']} checks={res['checks']}", flush=True)
    elif a.cmd == "rt8eval":
        res = rt8eval(Path(a.eval_dir), a.run)
        print(f"RT8E run={a.run} pass={res['pass']} masks={res['masks']}", flush=True)
    else:
        res = tb_scalars(Path(a.run_dir))
    Path(a.out).write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
