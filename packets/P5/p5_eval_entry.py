"""CR-B2-1 (b)+(c): P5 eval entry point (spikes/B2/PLAN.md §2.3 (c), §3, §4.3).

Registers the ``mlp_mind`` arm (``mlp_mind.register``) **before** the frozen ``eval_entry`` is imported, installs
the fixed-seed mask stream (``maskstream.install``), and calls the frozen ``eval_entry.run_upstream`` once.

The frozen loop evaluates ``[0.0, *cfg["b2"]["mask_fracs"]]`` in order. The wrapper passes a copy of the run's
config whose ``b2.mask_fracs`` lists one entry per masked condition, so that a single frozen call runs exactly
the PLAN §4.3 conditions:

* it 1600: ``mask 0.00`` once, then for each mask seed in (7100, 7101, 7102) each f of the config's
  ``b2.mask_fracs`` (0.10, 0.20): 7 conditions;
* ``--mask0-only`` (it 400 / 800 / 1200): ``mask 0.00`` only.

Each condition is bracketed by a shim around ``eval_entry``'s ``runpy.run_path`` (the frozen call that runs
the upstream ``scripts/eval_benchmark.py``): before it, the dedicated generator is re-seeded with the
condition's seed; after it, the frozen benchmark JSON ``<run>_<arm>_mask<f>.json`` is renamed to
``<run>_<arm>_mask<f>_ms<seed>.json`` (``ms0`` for mask 0.00) and ``maskstream_mask<f>_ms<seed>.{npz,json}``
are written beside it. The upstream benchmark loop and the JSON content are not touched.

Usage (from /content/SuperMimic-Reproduced, CUDA venue)::

    python /content/junior/packets/P5/p5_eval_entry.py --config <cfg.yaml> --ckpt logs/<run>/ckpt_0001600.pt \
        --out-dir logs/eval/<ID>/it0001600/exec1 [--mask0-only] [--mask-seeds 7100 7101 7102]
"""

from __future__ import annotations

import argparse
import copy
import os
import sys
import time
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1] / "code"
for p in (str(CODE), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import mlp_mind  # noqa: E402

mlp_mind.register()  # must precede `import eval_entry` (POLICY_ARMS / build_decoder are bound at import)

import eval_entry  # noqa: E402
import maskstream  # noqa: E402

MASK_SEEDS = (7100, 7101, 7102)  # PLAN §3


def conditions(cfg: dict, seeds=MASK_SEEDS, mask0_only: bool = False) -> list[tuple[float, int]]:
    out = [(0.0, 0)]
    if not mask0_only:
        fracs = [float(f) for f in cfg.get("b2", {}).get("mask_fracs", [])]
        out += [(f, int(s)) for s in seeds for f in fracs]
    return out


def cond_name(frac: float, seed: int) -> str:
    return f"mask{frac:.2f}_ms{seed}"


class ConditionShim:
    """Stands in for the ``runpy`` module inside ``eval_entry``; brackets each frozen ``run_path`` call."""

    def __init__(self, conds, stream: maskstream.MaskStream, out_dir: Path, real_runpy):
        self.conds, self.stream, self.out_dir, self.real = conds, stream, Path(out_dir), real_runpy
        self.i = 0
        self.done: list[dict] = []

    def run_path(self, path, *a, **k):
        if self.i >= len(self.conds):
            raise RuntimeError("[p5_eval] more frozen conditions than scheduled")
        frac, seed = self.conds[self.i]
        out = Path(sys.argv[sys.argv.index("--out") + 1])
        if not out.name.endswith(f"_mask{frac:.2f}.json") or out.parent.resolve() != self.out_dir.resolve():
            raise RuntimeError(f"[p5_eval] frozen condition order mismatch: {out} vs mask{frac:.2f} in {self.out_dir}")
        cond = cond_name(frac, seed)
        print(f"[p5_eval] condition {self.i + 1}/{len(self.conds)} {cond} seed={seed} frac={frac:.2f}", flush=True)
        self.stream.begin(seed, frac)
        t0, start_utc = time.monotonic(), time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        res, exit_ok = None, None
        try:
            res = self.real.run_path(path, *a, **k)
        except SystemExit as e:  # the frozen caller treats code 0/None as success; keep that, after the rename
            if e.code not in (0, None):
                raise
            exit_ok = e
        finally:
            wall = round(time.monotonic() - t0, 3)  # PLAN §9.5: eval wall time per condition (failed ones too)
            meta = self.stream.end(self.out_dir, cond, {"wall_s": wall, "start_utc": start_utc})
            print(f"[p5_eval] maskstream {cond} calls={meta['calls']} k={meta['k']} rows={meta['rows_per_call']} "
                  f"sha256={meta['sha256']} wall_s={wall}", flush=True)
        final = out.with_name(out.name[: -len(".json")] + f"_ms{seed}.json")
        if not out.exists():
            raise RuntimeError(f"[p5_eval] benchmark JSON missing after condition {cond}: {out}")
        os.replace(out, final)
        print(f"[p5_eval] saved {final}", flush=True)
        self.done.append({"cond": cond, "json": str(final), **meta})
        self.i += 1
        if exit_ok is not None:
            raise exit_ok
        return res


def run(ckpt: Path, cfg: dict, out_dir: Path, policy: str | None = None, seeds=MASK_SEEDS, mask0_only: bool = False):
    conds = conditions(cfg, seeds, mask0_only)
    run_cfg = copy.deepcopy(cfg)
    run_cfg.setdefault("b2", {})["mask_fracs"] = [f for f, _s in conds[1:]]
    run_cfg.setdefault("eval", {})["out_dir"] = str(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stream = maskstream.MaskStream()
    maskstream.install(stream)
    real = eval_entry.runpy
    shim = ConditionShim(conds, stream, out_dir, real)
    eval_entry.runpy = types.SimpleNamespace(run_path=shim.run_path)
    try:
        eval_entry.run_upstream(ckpt, run_cfg, policy)
    finally:
        eval_entry.runpy = real
    if shim.i != len(conds):
        raise RuntimeError(f"[p5_eval] ran {shim.i} of {len(conds)} conditions")
    print(f"[p5_eval] done conditions={shim.i} ckpt={ckpt}", flush=True)
    return shim.done


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--ckpt", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--policy", default=None, choices=eval_entry.POLICY_ARMS)
    ap.add_argument("--mask-seeds", type=int, nargs="+", default=list(MASK_SEEDS))
    ap.add_argument("--mask0-only", action="store_true")
    a = ap.parse_args()
    if tuple(a.mask_seeds) != MASK_SEEDS:
        sys.exit(f"[p5_eval] mask seeds are frozen to {MASK_SEEDS} (PLAN §3)")
    print("[p5_eval] argv", " ".join(sys.argv), flush=True)
    run(a.ckpt, eval_entry.load_config(a.config), a.out_dir, a.policy, tuple(a.mask_seeds), a.mask0_only)


if __name__ == "__main__":
    main()
