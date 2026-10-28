"""B1-RT machine verdict (spikes/B1-RT/PLAN.md §2 verdict rule). Prose never overrides this output.

    python -I verdict_rt.py --cpu results-cpu-attempt<N>.json [--gpu-open <opened deposit dir>] \
        [--amendment <sealed amendment JSON>] --out results.json

``--amendment`` (optional) is a sealed JSON written from a signed Class-2 decision: {"decision_sha256": ...,
"waive": ["RT-4"], "note": ...}. Waived IDs are reported as ``waived`` and leave the verdict; nothing else changes.
GPU part: reads ``meta/rt6.json``, ``meta/rt8_xferload.json``, ``meta/rt7_<arm>.json`` and ``meta/rt8_eval_<arm>.json``
from the opened bundle (written by the job driver). Missing GPU files -> those IDs are ``not_run``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

IDS = ("RT-1", "RT-2", "RT-3", "RT-4", "RT-6", "RT-7", "RT-8")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cpu", required=True)
    ap.add_argument("--gpu-open", default=None)
    ap.add_argument("--amendment", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cpu_p = Path(a.cpu)
    cpu = json.loads(cpu_p.read_text())
    res: dict = {"tool": "spikes/B1-RT/verdict_rt.py", "tool_sha256": sha(Path(__file__)), "cpu_results": str(cpu_p),
                 "cpu_results_sha256": sha(cpu_p), "checks": {}}
    for k in ("RT-1", "RT-2", "RT-3", "RT-4"):
        res["checks"][k] = {"pass": cpu[k].get("pass"), "source": "cpu"}
    res["checks"]["RT-5"] = {"recorded": bool(cpu.get("rt5_recorded_finite")), "source": "cpu"}
    g = Path(a.gpu_open) if a.gpu_open else None

    def gj(name):
        if g is None:
            return None
        p = g / "meta" / name
        return json.loads(p.read_text()) if p.exists() else None

    rt6, x8 = gj("rt6.json"), gj("rt8_xferload.json")
    rt7 = [gj(f"rt7_{arm}.json") for arm in ("attention", "mlp_matched")]
    ev8 = [gj(f"rt8_eval_{arm}.json") for arm in ("attention", "mlp_matched")]
    res["checks"]["RT-6"] = {"pass": rt6["pass"], "source": "gpu"} if rt6 else {"pass": None, "status": "not_run"}
    res["checks"]["RT-7"] = ({"pass": all(r["pass"] for r in rt7), "source": "gpu", "runs": rt7}
                             if all(r is not None for r in rt7) else {"pass": None, "status": "not_run"})
    if x8 is not None and all(e is not None for e in ev8):
        res["checks"]["RT-8"] = {"pass": bool(x8["pass"] and all(e["pass"] for e in ev8)), "source": "gpu",
                                 "xferload": x8["pass"], "eval": [e["pass"] for e in ev8]}
    else:
        res["checks"]["RT-8"] = {"pass": None, "status": "not_run"}
    waive = []
    if a.amendment:
        am = json.loads(Path(a.amendment).read_text())
        waive = list(am.get("waive", []))
        res["amendment"] = {"path": a.amendment, "sha256": sha(Path(a.amendment)), **am}
    for k in waive:
        res["checks"][k]["waived"] = True
    live = [k for k in IDS if k not in waive]
    failing = [k for k in live if res["checks"][k].get("pass") is False]
    not_run = [k for k in live if res["checks"][k].get("pass") is None]
    rt5 = res["checks"]["RT-5"]["recorded"]
    if failing:
        verdict = "FAIL"
    elif not_run or not rt5:
        verdict = "BLOCKED" if g is not None else "INCOMPLETE"
    else:
        verdict = "PASS"
    res.update(verdict=verdict, failing_ids=failing, not_run=not_run, waived=waive, rt5_recorded=rt5,
               pass_=verdict == "PASS")
    res["pass"] = res.pop("pass_")
    for k in IDS:  # one key per RT-id with boolean pass (PLAN §2 outputs)
        res[k] = {"pass": res["checks"][k].get("pass")}
    res["RT-5"] = {"recorded": rt5}
    Path(a.out).write_text(json.dumps(res, indent=2, default=float))
    print(f"B1RT_VERDICT verdict={verdict} failing_ids=[{','.join(failing)}] not_run=[{','.join(not_run)}] "
          f"waived=[{','.join(waive)}] rt5_recorded={rt5}")


if __name__ == "__main__":
    main()
