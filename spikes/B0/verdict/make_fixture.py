#!/usr/bin/env python3
"""Synthesise realistic P4 B0 deposit archives (.tgz) for testing verdict_b0.py. Stdlib only.

Writes genuine TF event files (TFRecord framing with masked CRC32C), trainer logs in the real format
(`[seam]`, `[train_entry] upstream argv:`, `[INFO] params:`, `it N | ...`), sidecars, eval JSONs, eval logs,
meta files per packets/P4/BUNDLE_CONTRACT.md, and a temporary seal log with DEPOSIT lines.

Usage as a script (writes one clean example deposit + seal log):
    python -I make_fixture.py <outdir>
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
import struct
import sys
import tarfile

TARBALL_SHA = "f00d" * 16
DESCRIPTOR_SHA = "3c854f91eb3739e4077dfec354d27a33f7c00cf019eec993a8fb43b66b1e5fe3"
CLIPS = ("dance1_subject1", "jumps1_subject1", "run1_subject2", "walk1_subject1")
CLIP_STEPS = (520, 500, 610, 505)  # all >= T, so R_H == per-clip norm_return when they are equal
PARAMS = {"attention": 464001, "mlp_matched": 468317, "mlp_upstream": 4718621}
RATE = {"attention": 0.70, "mlp_matched": 0.75, "mlp_upstream": 0.72}

# ------------------------------------------------------------------------------------------ TFRecord writer
_T = []
for _i in range(256):
    _c = _i
    for _ in range(8):
        _c = (_c >> 1) ^ 0x82F63B78 if _c & 1 else _c >> 1
    _T.append(_c)


def crc32c(data: bytes) -> int:
    c = 0xFFFFFFFF
    for b in data:
        c = _T[(c ^ b) & 0xFF] ^ (c >> 8)
    return c ^ 0xFFFFFFFF


def masked_crc(data: bytes) -> int:
    c = crc32c(data)
    return (((c >> 15) | (c << 17)) + 0xA282EAD8) & 0xFFFFFFFF


def _varint(n: int) -> bytes:
    if n < 0:
        n += 1 << 64
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _key(field, wire):
    return _varint((field << 3) | wire)


def _ld(field, payload: bytes) -> bytes:
    return _key(field, 2) + _varint(len(payload)) + payload


def event_bytes(wall: float, step: int | None = None, scalars=None, file_version: str | None = None) -> bytes:
    b = _key(1, 1) + struct.pack("<d", wall)
    if step is not None:
        b += _key(2, 0) + _varint(step)
    if file_version is not None:
        b += _ld(3, file_version.encode())
    if scalars:
        summ = b""
        for tag, val in scalars:
            v = _ld(1, tag.encode()) + _key(2, 5) + struct.pack("<f", val)
            summ += _ld(1, v)
        b += _ld(5, summ)
    return b


def tfrecord(data: bytes) -> bytes:
    hdr = struct.pack("<Q", len(data))
    return hdr + struct.pack("<I", masked_crc(hdr)) + data + struct.pack("<I", masked_crc(data))


# ------------------------------------------------------------------------------------------ attempt content
def default_attempt(aid, **kw):
    tag, rest = aid.split("_", 1)
    arm = rest.rsplit("_s", 1)[0]
    seed = int(rest.rsplit("_s", 1)[1].split("_a")[0])
    n = int(aid.rsplit("_a", 1)[1])
    spec = {"aid": aid, "tag": tag, "arm": arm, "seed": seed, "n": n,
            "outcome": "completed",      # completed | div_crash | infra_disconnect | oom | seam | traceback
            "r_h": 0.30, "l1": "rise", "l2": "fall",
            "nan_step": None, "stop_it": None, "drop_1600": False,
            "post_nan": False, "post_exc": None, "pre_exc": None,
            "live": False, "evals": True, "driver_class": None, "extra_tb_file": False}
    spec.update(kw)
    return spec


def argv_for(spec):
    run = "%s_%s_s%d" % (spec["tag"], spec["arm"], spec["seed"])
    a = ["--run-name", run, "--seed", str(spec["seed"]), "--data.npz-dir", "data/npz/lafan1_smoke",
         "--env.num-envs", "512", "--policy-trainer.batch-size", "512", "--policy-trainer.horizon", "16",
         "--policy-trainer.compile", "None", "--schedule.max-hours", "1.5", "--schedule.checkpoint-interval", "400",
         "--schedule.log-interval", "50", "--env.anchor-obs"]
    if spec["tag"] == "b0lr05":
        a += ["--policy-trainer.lr", "0.0001"]
    return a


def _updates(it):
    return float(max(0, int(round((it - 40) * 0.4))))


def tb_points(spec):
    """Return list of (step, wall, [(tag, value)]) plus extra raw records."""
    last = spec["stop_it"] or (1650 if spec["outcome"] == "completed" else 800)
    rate = RATE[spec["arm"]]
    pts = []
    base_wall = 1792990000.0 + 10000 * spec["seed"] + 100000 * spec["n"]
    for it in range(50, last + 1, 50):
        x = it / 1600.0
        if spec["l1"] == "rise":
            elen = 30.0 + 50.0 * x + spec["seed"]
        else:
            elen = 80.0 - 50.0 * x
        nret = 0.39 - 0.05 * x
        wm = (58.0 * math.exp(-it / 200.0) + 4.0) if spec["l2"] == "fall" else (4.0 + it / 50.0)
        hours = it / (rate * 3600.0) + 0.004
        sc = [("train/episode_len", elen), ("train/episode_norm_return", nret), ("wm/loss", wm),
              ("time/updates", _updates(it)), ("time/hours", hours), ("time/sim_s_per_iter", 0.035),
              ("time/wm_s_per_iter", 0.19), ("time/policy_s_per_iter", 1.10 if spec["arm"] == "attention" else 0.9),
              ("policy/policy_grad_norm", 0.1 + 0.05 * x), ("policy/action_abs_mean", 0.6 * x)]
        if spec["nan_step"] == it:
            sc = [(t, (float("nan") if t == "wm/loss" else v)) for t, v in sc]
        if spec["post_nan"] and it == 1650:
            sc = [(t, (float("nan") if t == "policy/policy_grad_norm" else v)) for t, v in sc]
        if spec["drop_1600"] and it == 1600:
            continue
        pts.append((it, base_wall + it * 1.4, sc))
    return pts


def event_file_bytes(spec):
    out = tfrecord(event_bytes(1792989999.0, file_version="brain.Event:2"))
    pts = tb_points(spec)
    for it, wall, sc in pts:
        for t, v in sc:  # one record per scalar, as the real writer does
            out += tfrecord(event_bytes(wall, it, [(t, v)]))
        if it == 1600:
            # duplicate time/updates at step 1600 with an EARLIER wall time: §5 rule says latest wall time wins
            out += tfrecord(event_bytes(wall - 100.0, it, [("time/updates", 999.0)]))
    return out


def train_log(spec):
    run = "%s_%s_s%d" % (spec["tag"], spec["arm"], spec["seed"])
    rate = RATE[spec["arm"]]
    L = ["/content/SuperMimic-Reproduced/.venv/lib/python3.12/site-packages/torch/jit/_script.py:1491: FutureWarning: "
         "`torch.jit.script` is deprecated. Please switch to `torch.compile` or `torch.export`.",
         "  warnings.warn(",
         "[seam] S4 default_pose_source=env_init_state",
         "[train_entry] upstream argv: " + " ".join(argv_for(spec)),
         "Setting seed: %d" % spec["seed"],
         "Warp 1.18.0 initialized:",
         "     \"cuda:0\"   : \"NVIDIA L4\" (22 GiB, sm_89, mempool enabled)",
         "[INFO] params: world model 8.82M, policy %s, critic 0.237M" % ("8.89M" if spec["arm"] == "mlp_upstream" else "4.64M")]
    if spec["outcome"] == "seam":
        L += ["[seam] S1 joint_order_match=unverified",
              "[seam] S1 detail compared=['descriptor', 'entity'] (action order not exposed; S1 unverified)",
              "Traceback (most recent call last):",
              '  File "/content/junior/code/train_entry.py", line 557, in run_upstream',
              "    upstream_main()",
              "RuntimeError: [seam] S1 joint order unverified (descriptor rows / robot entity / action order): x"]
        return "\n".join(L) + "\n"
    L += ["[seam] S1 joint_order_match=true",
          "[seam] S1 detail compared=['action', 'descriptor', 'entity']",
          "[seam] S5 env_action_scale_match=true",
          "[seam] S5 detail compared=29 joints rel_tol=1e-06",
          "[seam] S3 compile=None",
          "[seam] S2 obs_policy_dim=930 term_major_ok=true",
          "[seam] S2 detail names in upstream order; terms carry the history (term-major)"]
    last = spec["stop_it"] or (1650 if spec["outcome"] == "completed" else 800)
    for it in range(50, last + 1, 50):
        L.append("it %d | %.2f h | %.1f it/s | updates %d | train_ret 0.384 (n=532) | wm nse1 0.0350 nse8 0.0710 | "
                 "imag_ret 0.451 surv 0.609 | t sim/wm/pi 1.7/9.8/58.1s" % (it, it / (rate * 3600), rate, _updates(it)))
        if it == 1600 and spec["outcome"] == "completed":
            pass
    if spec["pre_exc"]:
        body, final = spec["pre_exc"]
        L += ["Traceback (most recent call last):"] + list(body) + [final]
    elif spec["outcome"] == "div_crash":
        L += ["Traceback (most recent call last):",
              '  File "/content/SuperMimic-Reproduced/src/supermimic/training/loop.py", line 193, in train',
              "    pm = self.policy_trainer.update(batch)",
              "RuntimeError: Function 'MseLossBackward0' returned nan values in its 0th output."]
    elif spec["outcome"] == "oom":
        L += ["Traceback (most recent call last):",
              '  File "/content/SuperMimic-Reproduced/src/supermimic/imagination/policy_trainer.py", line 70, in update',
              "    loss.backward()",
              "torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.00 GiB (GPU 0; 22.03 GiB total capacity)"]
    if spec["outcome"] == "completed":
        if spec["post_exc"]:
            L += ["Traceback (most recent call last):",
                  '  File "/content/SuperMimic-Reproduced/src/supermimic/training/loop.py", line 200, in train',
                  "    agg[k] = agg.get(k, 0.0) + v",
                  spec["post_exc"]]
        L += ["Traceback (most recent call last):",
              '  File "/content/junior/code/train_entry.py", line 557, in run_upstream',
              "    upstream_main()",
              '  File "/content/SuperMimic-Reproduced/src/supermimic/training/loop.py", line 161, in train',
              "    obs, rew, term, trunc, info = self.env.step(action)",
              "KeyboardInterrupt"]
    return "\n".join(L) + "\n"


def sidecar(spec):
    run = "%s_%s_s%d" % (spec["tag"], spec["arm"], spec["seed"])
    return {"default_pose_source": "env_init_state",
            "descriptor": {"version": "v2", "sha256": DESCRIPTOR_SHA},
            "actuator_source": "upstream_robot_cfg",
            "seam": {"S4_default_pose_source": "env_init_state", "S1_joint_order_match": True,
                     "S1_detail": "compared=['action', 'descriptor', 'entity']", "S5_env_action_scale_match": True,
                     "S5_detail": "compared=29 joints rel_tol=1e-06", "S3_compile": "None", "S2_obs_policy_dim": 930,
                     "S2_term_major_ok": True, "S2_detail": "names in upstream order; terms carry the history (term-major)"},
            "policy": spec["arm"], "params": PARAMS[spec["arm"]], "train_mask_frac": 0.0, "argv": argv_for(spec),
            "_run": run}


def eval_json(spec, it, mask):
    fac = {400: 0.5, 800: 0.7, 1200: 0.9, 1600: 1.0}[it] * {"0.00": 1.0, "0.10": 0.9, "0.20": 0.8}[mask]
    r = spec["r_h"] * fac
    terms = {"motion_global_root_pos": 0.003, "motion_body_pos": 0.0135, "action_rate_l2": -0.0043,
             "joint_limit": -0.00036}
    clips = []
    for name, steps in zip(CLIPS, CLIP_STEPS):
        failed = steps < 600
        clips.append({"name": name, "frames": 6000 + steps, "steps": steps, "norm_return": r, "failed": failed,
                      "fail_step": steps if failed else None, "terms": dict(terms)})
    tot = sum(CLIP_STEPS)
    return {"summary": {"clips": 4, "failed": sum(1 for c in clips if c["failed"]), "mean_norm_return": r,
                        "step_weighted_norm_return": sum(c["norm_return"] * c["steps"] for c in clips) / tot,
                        "terms": terms}, "clips": clips}


def kv(d):
    return "".join("%s=%s\n" % (k, v) for k, v in d.items())


def attempt_files(spec):
    """Return {relpath: bytes} for one attempt."""
    aid = spec["aid"]
    run = "%s_%s_s%d" % (spec["tag"], spec["arm"], spec["seed"])
    f = {}
    completed = spec["outcome"] == "completed"
    f["logs/train_%s.log" % aid] = train_log(spec).encode()
    adir = "logs/attempts/%s/" % aid
    ev = event_file_bytes(spec)
    f[adir + "tb/events.out.tfevents.1792990000.host.%d.0" % (1000 + spec["n"])] = ev
    if spec["extra_tb_file"]:
        f[adir + "tb/events.out.tfevents.1792990999.host.9999.0"] = tfrecord(event_bytes(1.0, file_version="brain.Event:2"))
    side_present = completed or spec["outcome"] in ("div_crash", "oom", "seam", "traceback")
    if side_present:
        sd = sidecar(spec)
        sd.pop("_run")
        f[adir + "junior_policy.json"] = json.dumps(sd, indent=2).encode()
    f[adir + "config.json"] = json.dumps({"run_name": run}).encode()
    if spec["live"]:
        f["logs/attempts/%s.live/tb/events.out.tfevents.1792990000.host.%d.0" % (aid, 1000 + spec["n"])] = ev
        f["logs/attempts/%s.live/config.json" % aid] = json.dumps({"run_name": run}).encode()
    reached = completed or (spec["stop_it"] or 0) >= 1600
    f["meta/harness_stop_%s.txt" % aid] = kv({
        "aid": aid, "endpoint_line_seen": str(reached).lower(),
        "endpoint_line_utc": "2026-10-27T03:10:00Z" if reached else "none",
        "ckpt_path": "logs/%s/ckpt_0001600.pt" % run,
        "ckpt_size_poll1": "164415878" if reached else "none", "ckpt_size_poll2": "164415878" if reached else "none",
        "poll_interval_s": "30", "ckpt_stable": str(completed).lower(), "harness_stop": str(completed).lower(),
        "signal": "SIGINT" if completed else "none", "sigint_sent_utc": "2026-10-27T03:11:00Z" if completed else "none",
        "trainer_exited_before_signal": str(not completed).lower(), "exit_wait_s": "4" if completed else "0",
        "harness_stop_timeout": "false", "sigkill_sent": "false", "exit_code": "130" if completed else "1",
        "sidecar": "present" if side_present else "missing"}).encode()
    dcls = spec["driver_class"] or {"completed": "completed", "div_crash": "DIV", "oom": "OOM", "seam": "SEAM"}.get(
        spec["outcome"], "INFRA")
    f["meta/attempt_%s.txt" % aid] = kv({
        "aid": aid, "tag": spec["tag"], "arm": spec["arm"], "seed": spec["seed"], "attempt": spec["n"],
        "cfg": "/content/junior/configs/%s.yaml" % ("b0_microbench_lr05" if spec["tag"] == "b0lr05" else "b0_microbench"),
        "start_utc": "2026-10-27T02:00:00Z", "end_utc": "2026-10-27T03:12:00Z",
        "exit_code": "130" if completed else "1", "completed": str(completed).lower(), "driver_class": dcls,
        "driver_diverged": str(spec["outcome"] == "div_crash" or spec["nan_step"] is not None).lower(),
        "infra_cause": "none", "final_exception_line": "none", "evals": "done" if completed else "skipped"}).encode()
    f["meta/gpumem_%s.csv" % aid] = ("timestamp, memory.used [MiB], memory.total [MiB]\n"
                                    "2026/10/27 02:00:05.000, 812 MiB, 23034 MiB\n"
                                    "2026/10/27 02:00:10.000, 9123 MiB, 23034 MiB\n"
                                    "2026/10/27 02:00:15.000, 9050 MiB, 23034 MiB\n").encode()
    if completed and spec["evals"]:
        for it in (400, 800, 1200, 1600):
            d = "logs/eval/%s/it%07d/exec1/" % (aid, it)
            lines = []
            for m in ("0.00", "0.10", "0.20"):
                out = "logs/eval/%s_%s_mask%s.json" % (run, spec["arm"], m)
                lines.append("[eval_entry] eval_benchmark.py --ckpt logs/%s/ckpt_%07d.pt --npz-dir "
                             "data/npz/lafan1_smoke --num-envs 64 --out %s" % (run, it, out))
                f[d + "%s_%s_mask%s.json" % (run, spec["arm"], m)] = json.dumps(eval_json(spec, it, m), indent=1).encode()
            lines.append("exit=0")
            f[d + "eval.log"] = ("\n".join(lines) + "\n").encode()
    return f


NVSMI = """Tue Oct 27 02:50:39 2026
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 580.82.07              Driver Version: 580.82.07      CUDA Version: 13.0     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|=========================================+========================+======================|
|   0  %-30s Off |   00000000:00:03.0 Off |                    0 |
| N/A   46C    P8             16W /   72W |       0MiB /  23034MiB |      0%%      Default |
+-----------------------------------------+------------------------+----------------------+
"""

SANITY_OK = """[INFO] params: world model 8.82M, policy 8.89M, critic 0.235M
it 50 | 0.01 h | 2.1 it/s | updates 4 | train_ret 0.392 (n=250) | wm nse1 0.1819 nse8 0.9615 | imag_ret 0.100 surv 0.000 | t sim/wm/pi 2.2/6.2/15.4s
it 350 | 0.10 h | 0.7 it/s | updates 124 | train_ret 0.430 (n=536) | wm nse1 0.0377 nse8 0.1204 | imag_ret 0.446 surv 0.587 | t sim/wm/pi 1.7/9.6/55.6s
[INFO] max_hours reached, stopping
"""


def deposit_files(dep):
    """dep: {'part', 'attempts': [spec], 'sanity': True|False|'fail', 'gpu', 'tarball_sha', 'session': {},
    'blocked': [codes], 'extra': {rel: bytes}}"""
    f = {}
    part = dep.get("part", 1)
    f["meta/tarball_sha256.txt"] = ("%s  junior_b_colab-CR-B0-1.tgz\n" % dep.get("tarball_sha", TARBALL_SHA)).encode()
    f["meta/cpu_test_smoke.log"] = b"".join(b"SKIP x\nPASS t%d\n" % i if i < 3 else b"PASS t%d\n" % i for i in range(14))
    f["meta/cpu_test_check.txt"] = b"pass_lines=14 skip_before_pass=3 expected=14/3 ok=true\n"
    f["meta/nvidia-smi.txt"] = (NVSMI % dep.get("gpu", "NVIDIA L4")).encode()
    f["meta/pip-freeze.txt"] = b"torch==2.14.1\nnumpy==2.3.0\n"
    f["meta/torch_cuda.txt"] = b"cuda True 2.14.1\n"
    sess = {"part": part, "venue": dep.get("venue", "colab"), "start_utc": "2026-10-27T01:00:00Z",
            "end_utc": "2026-10-27T06:00:00Z", "session_hours": "5.0", "prior_hours": "0", "total_hours": "5.0",
            "spend_cap_hours": "7", "spend_cap_hit": "false", "gate_set_complete": "true", "cells_remaining": ""}
    sess.update(dep.get("session", {}))
    f["meta/session.txt"] = kv(sess).encode()
    state = ["PART %d 2026-10-27T01:00:00Z" % part]
    if dep.get("sanity", True):
        state.append("V0 pass colab NVIDIA_L4")
    for s in dep["attempts"]:
        state.append("ATTEMPT %s %s false %s" % (s["aid"], "completed" if s["outcome"] == "completed" else "INFRA",
                                                  str(s["outcome"] == "completed").lower()))
    f["meta/driver_state.txt"] = ("\n".join(state) + "\n").encode()
    f["meta/driver.log"] = b"[driver] ok\n"
    f["meta/ckpt_dirs_ls.txt"] = b"## logs/attempts\n"
    san = dep.get("sanity", True)
    if san is True:
        f["train_up_sanity.log"] = SANITY_OK.encode()
    elif san == "fail":
        f["train_up_sanity.log"] = (SANITY_OK.replace("[INFO] max_hours reached, stopping\n", "") +
                                    "Traceback (most recent call last):\n  File \"x\"\nRuntimeError: boom\n").encode()
    f["deviations.md"] = b"- [driver] harness stop used (F-1 unsuitable), PLAN 3.4\n"
    if dep.get("blocked"):
        f["BLOCKED.md"] = "".join("BLOCKED_REASON=%s detail=fixture\n" % c for c in dep["blocked"]).encode()
    for s in dep["attempts"]:
        f.update(attempt_files(s))
    f.update(dep.get("extra", {}))
    return f


def write_tgz(path, files, extra_members=None):
    if os.path.exists(path):
        os.remove(path)
    with tarfile.open(path, "w:gz") as t:
        dirs = set()
        for rel in sorted(files):
            parts = rel.split("/")[:-1]
            for i in range(1, len(parts) + 1):
                d = "./" + "/".join(parts[:i])
                if d not in dirs:
                    dirs.add(d)
                    ti = tarfile.TarInfo(d)
                    ti.type = tarfile.DIRTYPE
                    ti.mode = 0o755
                    ti.mtime = 1792990000
                    t.addfile(ti)
            data = files[rel]
            ti = tarfile.TarInfo("./" + rel)
            ti.size = len(data)
            ti.mode = 0o644
            ti.mtime = 1792990000
            t.addfile(ti, io.BytesIO(data))
        for ti, data in (extra_members or []):
            t.addfile(ti, io.BytesIO(data) if data is not None else None)
    os.chmod(path, 0o444)
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def write_seal_log(path, entries, venue="colab"):
    """entries: list of (sha, relpath)."""
    with open(path, "w") as fh:
        fh.write("2026-10-26T04:59:42Z 1792990782 SEAL spikes/B0/PLAN.md sha256=ed6b... P3-B0-PLAN\n")
        for i, (sha, rel) in enumerate(entries):
            fh.write("2026-10-27T07:%02d:00Z %d DEPOSIT %s %s %s P4-B0 byte-identical no-open-yet\n" % (
                i, 1793000000 + i, venue, sha, rel))


# ------------------------------------------------------------------------------------------ scenario helpers
def gate_order():
    out = []
    for s in (0, 1, 2):
        out += [("attention", s), ("mlp_matched", s)]
    return out


def clean_attempts(att_r=(0.30, 0.31, 0.29), mlp_r=(0.30, 0.30, 0.31), ref=True):
    specs = []
    for arm, s in gate_order():
        r = (att_r if arm == "attention" else mlp_r)[s]
        specs.append(default_attempt("b0_%s_s%d_a1" % (arm, s), r_h=r))
    if ref:
        specs.append(default_attempt("b0_mlp_upstream_s0_a1", r_h=0.35))
    return specs


def find(specs, aid):
    for s in specs:
        if s["aid"] == aid:
            return s
    raise KeyError(aid)


def build(outdir, deposits, seal=True, venue="colab", seal_skip=()):
    """Write each deposit tgz into outdir and a seal log. Returns (tgz_paths, seal_log_path)."""
    os.makedirs(outdir, exist_ok=True)
    paths = []
    entries = []
    for i, dep in enumerate(deposits):
        name = "b0-20261027-%04d%s.tgz" % (600 + i, "" if dep.get("part", 1) == 1 else "-part%d" % dep["part"])
        p = os.path.join(outdir, name)
        sha = write_tgz(p, deposit_files(dep), dep.get("extra_members"))
        paths.append(p)
        if seal and i not in seal_skip:
            entries.append((sha, "logs/colab/2026-10-27/" + name))
    sl = os.path.join(outdir, "seal.log")
    write_seal_log(sl, entries, venue)
    return paths, sl


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "fixture_out"
    paths, sl = build(out, [{"part": 1, "attempts": clean_attempts()}])
    print("\n".join(paths + [sl]))


if __name__ == "__main__":
    main()
