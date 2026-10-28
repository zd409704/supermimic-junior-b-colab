#!/usr/bin/env python3
"""CPU stand-in for p6_entry.py (train / eval) and b1_checks.py tbdump, used only by the B1 arms driver CPU mock.

Not part of the arms tarball. No GPU, no torch: it reproduces the on-disk behaviour the driver depends on
(``it N |`` log lines every 50 iterations, ``ckpt_%07d.pt`` every 160, a TF event file, a sidecar written in
``finally`` on SIGINT, one eval JSON per call) so that arm order, harness stop, spend cap, source ckpt check,
attempt 2 and the bundle can be exercised. TF records come from the sealed B0 fixture writer (read-only import).

Behaviour per attempt: B1ARMS_MOCK_BEHAVIOUR = JSON file {"<run>_a<n>": "ok" | "infra" | "nonfinite" |
"evalfail:<it>"}; attempt numbers are counted in B1ARMS_MOCK_STATE. B1ARMS_MOCK_IT_S = seconds per iteration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "spikes" / "B0" / "verdict"))
import make_fixture as MF  # noqa: E402  (sealed 7943c801…, read-only)
import verdict_b0 as VB  # noqa: E402  (sealed 9caa744a…, read-only)

STATE = Path(os.environ.get("B1ARMS_MOCK_STATE", "/tmp/b1arms-mock-state"))
IT_S = float(os.environ.get("B1ARMS_MOCK_IT_S", "0.002"))
HEAD = ["head_yaw_joint", "head_pitch_joint"]
PARAMS = {"attention": 464001, "mlp_matched": 468317}


def behaviour(key: str) -> str:
    f = os.environ.get("B1ARMS_MOCK_BEHAVIOUR")
    return json.loads(Path(f).read_text()).get(key, "ok") if f else "ok"


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def updates(it: int) -> float:
    return 4.0 + 0.4 * (it - 50)


def ret_curve(arm_tag: str, seed: int, it: int) -> float:
    base = {"b1HAscratch": 0.30, "b1HAxfer": 0.42, "b1HMxfer": 0.36}.get(arm_tag, 0.33)
    return base + 0.2 * it / 1600.0 + 0.01 * seed


def cmd_train(a) -> int:
    run = f"{a.run_tag}_{a.policy}_s{a.seed}"
    STATE.mkdir(parents=True, exist_ok=True)
    cnt = STATE / f"{run}.count"
    n = int(cnt.read_text()) + 1 if cnt.exists() else 1
    cnt.write_text(str(n))
    beh = behaviour(f"{run}_a{n}")
    rd = Path("logs") / run
    (rd / "tb").mkdir(parents=True, exist_ok=True)
    argv = ["--run-name", run, "--seed", str(a.seed), "--data.npz-dir", "data/npz/b1_home", "--env.num-envs", "512",
            "--policy-trainer.batch-size", "512", "--policy-trainer.horizon", "16", "--policy-trainer.compile", "None",
            "--schedule.max-hours", "1.5", "--schedule.checkpoint-interval", "160", "--schedule.log-interval", "50",
            "--env.anchor-obs"]
    print("[p6_entry] upstream argv:", " ".join(argv), flush=True)
    info = {"body": "home_humanoid", "num_joints": 22, "init": a.init, "policy": a.policy,
            "seam": {"S1_joint_order_match": True, "S2_term_major_ok": True, "S5_env_action_scale_match": True},
            "params_total": PARAMS[a.policy], "params_trainable": 0 if a.init == "frozen" else PARAMS[a.policy]}
    if a.init != "scratch":
        info["transfer_src"] = {"path": a.src_ckpt, "sha256": sha(a.src_ckpt)}
        if a.policy == "attention":
            info["transfer"] = {"kind": "attention_full_copy", "n_params_copied": 41, "n_values_copied": PARAMS["attention"],
                                "buffers_not_copied": ["morphology", "scale"]}
            if a.init == "frozen":
                info["transfer"]["frozen_values"] = PARAMS["attention"]
        else:
            info["transfer"] = {"kind": "mlp_row_mapped", "hidden": [384, 192, 96, 48], "output_rows_mapped": 20,
                                "output_rows_total": 22, "fresh_joints": HEAD, "hidden_layers_copied": 3}
    ev = rd / "tb" / "events.out.tfevents.mock.0"
    with open(ev, "wb") as fh:
        fh.write(MF.tfrecord(MF.event_bytes(time.time(), file_version="brain.Event:2")))
    try:
        for it in range(1, 3201):
            time.sleep(IT_S)
            if beh == "infra" and it == 700:
                raise RuntimeError("mock INFRA failure (CUDA error: an illegal memory access was encountered)")
            if it % 50 == 0:
                r = float("nan") if beh == "nonfinite" and it >= 500 else ret_curve(a.run_tag, a.seed, it)
                with open(ev, "ab") as fh:
                    for t, v in (("time/updates", updates(it)), ("train/episode_norm_return", r),
                                 ("time/hours", it / 6400.0), ("wm/loss", 1.0 / it)):
                        fh.write(MF.tfrecord(MF.event_bytes(time.time(), it, [(t, v)])))
                print(f"it {it} | {it / 6400:.2f} h | 2.0 it/s | updates {int(updates(it))} | train_ret {r:.3f} (n=300)",
                      flush=True)
            if it % 160 == 0:
                (rd / f"ckpt_{it:07d}.pt").write_bytes(f"{run} a{n} it{it}".encode() * 64)
        (rd / "ckpt_latest.pt").write_bytes(b"latest")
    finally:
        (rd / "junior_policy.json").write_text(json.dumps({**info, "argv": argv, "mock_attempt": n, "mock": beh}, indent=2))
    return 0


def cmd_eval(a) -> int:
    ck = Path(a.ckpt)
    run, it = ck.parent.name, int(ck.stem.split("_")[1])
    STATE.mkdir(parents=True, exist_ok=True)
    beh = behaviour(f"{run}_eval")
    mark = STATE / f"{run}_it{it}.evalfail"
    if beh == f"evalfail:{it}" and not mark.exists():
        mark.write_text("1")
        print("Traceback (most recent call last):\nRuntimeError: mock eval failure", flush=True)
        return 1
    if not ck.exists():
        print(f"missing {ck}", flush=True)
        return 2
    tag, seed = run.split("_")[0], int(run.rsplit("_s", 1)[1])
    r = ret_curve(tag, seed, it) + 0.05
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for f in a.masks:
        clips = [{"name": c, "frames": 600, "steps": 500, "norm_return": r, "failed": False, "fail_step": None, "terms": {}}
                 for c in ("walk1_subject1", "run1_subject2", "dance1_subject1", "jumps1_subject1")]
        d = {"summary": {"clips": 4, "failed": 0, "mean_norm_return": r, "step_weighted_norm_return": r, "terms": {}},
             "clips": clips}
        (out / f"{run}_{ck.stem}_mask{f:.2f}.json").write_text(json.dumps(d))
    return 0


def cmd_tbdump(a) -> int:
    out = {}
    for f in sorted((Path(a.run_dir) / "tb").glob("events.*")):
        recs, _ = VB.read_events(str(f))
        for tag, step, val in ((t, s, v) for t, s, _w, v, _o in recs):
            out.setdefault(tag, []).append((step, val))
    Path(a.out).write_text(json.dumps({k: sorted(v) for k, v in out.items()}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    for k in ("--config", "--policy", "--init", "--src-ckpt", "--run-tag", "--device"):
        t.add_argument(k, default=None)
    t.add_argument("--seed", type=int, required=True)
    e = sub.add_parser("eval")
    for k in ("--config", "--ckpt", "--out-dir", "--device"):
        e.add_argument(k, default=None)
    e.add_argument("--masks", type=float, nargs="+", default=[0.0])
    d = sub.add_parser("tbdump")
    d.add_argument("--run-dir", required=True)
    d.add_argument("--out", required=True)
    a = ap.parse_args()
    return {"train": cmd_train, "eval": cmd_eval, "tbdump": cmd_tbdump}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
