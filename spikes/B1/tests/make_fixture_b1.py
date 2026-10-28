"""Synthetic B1 arms deposits for verdict_b1.py tests (layout = packets/P6/BUNDLE_CONTRACT-b1arms.md).

Each fixture is a dict of rel path -> bytes, built from a spec; TF event files use the sealed B0 fixture writer
(spikes/B0/verdict/make_fixture.py, read-only import).
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "spikes", "B0", "verdict"))
import make_fixture as MF  # noqa: E402

sys.path.insert(0, os.path.dirname(HERE))
import verdict_b1 as V  # noqa: E402

TARBALL_SHA = "ab12" * 16
PARAMS = {"attention": 464001, "mlp_matched": 468317}
ARGV = ["--data.npz-dir", "data/npz/b1_home", "--env.num-envs", "512", "--policy-trainer.batch-size", "512",
        "--policy-trainer.horizon", "16", "--policy-trainer.compile", "None", "--schedule.max-hours", "1.5",
        "--schedule.checkpoint-interval", "160", "--schedule.log-interval", "50", "--env.anchor-obs"]


def linear(base, slope=0.01):
    return [base + slope * k for k in range(1, 11)]


def default_spec(bases=None, seed_delta=(-0.004, 0.0, 0.004)):
    """One spec per run: curve R (10 points) + attempt list. bases: arm -> base return."""
    bases = bases or {"H-A-scratch": 0.30, "H-A-xfer": 0.40, "H-M-xfer": 0.33, "H-M-scratch": 0.31,
                      "H-A-frozen": 0.20, "H-A-xfer-noscale": 0.38}
    runs = {}
    for arm, (tag, pol, init, seeds, role, srck) in V.ARMS.items():
        for s in seeds:
            run = f"{tag}_{pol}_s{s}"
            runs[run] = {"arm": arm, "policy": pol, "init": init, "seed": s, "role": role,
                         "src_sha": V.SRC[srck.format(k=s)] if srck else None,
                         "R": linear(bases[arm] + seed_delta[s]),
                         "attempts": [{"kind": "completed"}]}
    return {"runs": runs, "gpu_rows": ["0, GPU-1111-2222, NVIDIA GeForce RTX 4090"], "cuda_env": ["part=1 CUDA_VISIBLE_DEVICES=0"],
            "data_qa": {"rev": "ce1572906efe6157840e8474d5a0d7aa87481e74", "slot_rule": "first", "csv_sha_mismatch": [],
                        "used_clips": list(V.FIRST_CLIPS), "n_slots": 4, "pass": True},
            "tarball_sha": TARBALL_SHA, "blocked": [], "extra": {}}


def updates(it):
    return 4.0 + 0.4 * (it - 50)


def tb_bytes(att):
    out = MF.tfrecord(MF.event_bytes(1793000000.0, file_version="brain.Event:2"))
    stop = att.get("stop_it", 1700)
    for it in range(50, stop + 1, 50):
        w = 1793000000.0 + it
        r = float("nan") if att.get("nan_at") and it >= att["nan_at"] else 0.4
        u = att.get("updates_1600", updates(1600)) if it == 1600 else updates(it)
        for t, v in (("time/updates", u), ("train/episode_norm_return", r), ("time/hours", it / 6400.0)):
            out += MF.tfrecord(MF.event_bytes(w, it, [(t, v)]))
    return out


def train_log(run, att):
    stop = att.get("stop_it", 1700)
    L = [f"[p6_entry] upstream argv: --run-name {run} ..."]
    for it in range(50, stop + 1, 50):
        L.append(f"it {it} | {it / 6400:.2f} h | 2.0 it/s | updates {int(updates(it))} | train_ret 0.400 (n=300)")
    if att["kind"] == "infra":
        L += ["Traceback (most recent call last):", "RuntimeError: CUDA error: an illegal memory access was encountered"]
    elif att["kind"] in ("completed", "nonfinite"):
        L += ["Traceback (most recent call last):", "KeyboardInterrupt"]
    return "\n".join(L) + "\n"


def sidecar(spec_run, run, att):
    pol, init = spec_run["policy"], spec_run["init"]
    d = {"body": "home_humanoid", "num_joints": 22, "init": init, "policy": pol,
         "seam": {"S1_joint_order_match": True, "S2_term_major_ok": True, "S5_env_action_scale_match": True},
         "params_total": PARAMS[pol], "params_trainable": PARAMS[pol],
         "argv": ["--run-name", run, "--seed", str(spec_run["seed"])] + ARGV}
    if init != "scratch":
        d["transfer_src"] = {"path": f"/content/p5_p4ckpts/logs/b0_{pol}_s{spec_run['seed']}/ckpt_0001600.pt",
                             "sha256": spec_run["src_sha"]}
        if pol == "attention":
            d["transfer"] = {"kind": "attention_full_copy", "n_params_copied": 41, "n_values_copied": PARAMS[pol],
                             "buffers_not_copied": ["morphology", "scale"]}
        else:
            d["transfer"] = {"kind": "mlp_row_mapped", "hidden": [384, 192, 96, 48], "output_rows_mapped": 20,
                             "output_rows_total": 22, "fresh_joints": ["head_yaw_joint", "head_pitch_joint"],
                             "hidden_layers_copied": 3}
    for k, v in att.get("sidecar_patch", {}).items():
        cur = d
        ks = k.split(".")
        for kk in ks[:-1]:
            cur = cur.setdefault(kk, {})
        cur[ks[-1]] = v
    return d


def harness(run, aid, att):
    done = att["kind"] == "completed" or att["kind"] == "nonfinite"
    hs = {"aid": aid, "endpoint_line_seen": str(done).lower(), "ckpt_path": f"logs/{run}/ckpt_0001600.pt",
          "ckpt_size_poll1": "4096" if done else "none", "ckpt_size_poll2": "4096" if done else "none",
          "poll_interval_s": "30", "ckpt_stable": str(done).lower(), "harness_stop": str(done or att["kind"] == "spend_cap").lower(),
          "spend_cap_stop": str(att["kind"] == "spend_cap").lower(), "harness_stop_timeout": "false",
          "exit_code": "130" if done else "1", "sidecar": "present"}
    hs.update(att.get("harness_patch", {}))
    return "".join(f"{k}={v}\n" for k, v in hs.items())


def eval_json(run, it, r):
    clips = [{"name": c, "frames": 600, "steps": 500, "norm_return": r, "failed": False, "fail_step": None, "terms": {}}
             for c in V.FIRST_CLIPS]
    return {"summary": {"clips": 4, "failed": 0, "mean_norm_return": r, "step_weighted_norm_return": r, "terms": {}},
            "clips": clips}


def files_of(spec):
    F = {}
    for run, sr in spec["runs"].items():
        for n, att in enumerate(sr["attempts"], start=1):
            aid = f"{run}_a{n}"
            if att["kind"] in ("completed", "nonfinite") and "stop_it" not in att:
                att = {**att}
            elif att["kind"] in ("infra", "spend_cap"):
                att = {**att, "stop_it": att.get("stop_it", 700)}
            F[f"meta/attempt_{aid}.txt"] = f"aid={aid}\narm={sr['arm']}\nattempt={n}\n".encode()
            F[f"meta/harness_stop_{aid}.txt"] = harness(run, aid, att).encode()
            F[f"logs/train_{aid}.log"] = train_log(run, att).encode()
            if not att.get("no_tb"):
                F[f"logs/attempts/{aid}/tb/events.out.tfevents.1793000000.XN-4090-GPU2.1.0"] = tb_bytes(
                    {**att, "nan_at": att.get("nan_at", 500 if att["kind"] == "nonfinite" else None)})
            if not att.get("no_sidecar"):
                F[f"logs/attempts/{aid}/junior_policy.json"] = json.dumps(sidecar(sr, run, att)).encode()
            if att["kind"] != "completed" or att.get("no_eval"):
                continue
            for k, it in enumerate(V.EVAL_ITS):
                tag = f"{it:07d}"
                r = att.get("R", sr["R"])[k]
                fails = att.get("exec1_fail", ())
                for e in ((1, 2) if it in fails else (1,)) + ((2,) if it in att.get("exec2_extra", ()) else ()):
                    base = f"logs/eval/{aid}/it{tag}/exec{e}/"
                    if e == 1 and it in fails:
                        F[base + "eval.log"] = b"Traceback (most recent call last):\nRuntimeError: x\nexit=1\n"
                        continue
                    F[base + "eval.log"] = f"[p6_entry] eval_benchmark.py --ckpt logs/{run}/ckpt_{tag}.pt\nexit=0\n".encode()
                    F[base + f"{run}_ckpt_{tag}_mask0.00.json"] = json.dumps(eval_json(run, it, r)).encode()
    F["meta/b1_data_qa.json"] = json.dumps(spec["data_qa"]).encode()
    F["meta/gpu_used.csv.txt"] = ("index, uuid, name\n" + "".join(r + "\n" for r in spec["gpu_rows"])).encode()
    F["meta/gpu_env.txt"] = "".join(r + "\n" for r in spec["cuda_env"]).encode()
    F["meta/tarball_sha256.txt"] = f"part=1 {spec['tarball_sha']}  /content/b1arms/junior_b_colab-P6-B1ARMS.tgz\n".encode()
    F["meta/driver_identity.txt"] = b"part=1 driver_sha256=fixture\n"
    F["meta/spend.txt"] = b"spent_hours=6.5 cap=9.0 cap_hit=false\n"
    F["deviations.md"] = b""
    if spec["blocked"]:
        F["BLOCKED.md"] = "".join(f"BLOCKED_REASON={r}\n" for r in spec["blocked"]).encode()
    F.update(spec["extra"])
    return F


def write_tgz(path, files, extra_members=None):
    with tarfile.open(path, "w:gz") as t:
        for rel in sorted(files):
            data = files[rel]
            ti = tarfile.TarInfo(rel)
            ti.size, ti.mtime, ti.mode = len(data), 1793000000, 0o644
            t.addfile(ti, io.BytesIO(data))
        for ti, data in extra_members or []:
            t.addfile(ti, io.BytesIO(data) if data is not None else None)
    return path


def seal(seal_path, tgz, venue="xn4090"):
    sha = hashlib.sha256(open(tgz, "rb").read()).hexdigest()
    with open(seal_path, "a") as fh:
        fh.write(f"2026-10-28T00:00:00Z 1793000000 DEPOSIT {venue} {sha} {tgz} fixture\n")
    return sha


def spec_copy(spec):
    return copy.deepcopy(spec)
