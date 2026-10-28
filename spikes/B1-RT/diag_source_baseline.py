"""Diagnostic (not an RT attempt): the RT-4 metrics measured on the 29-DoF reference body's own source motion.

Purpose: tell a retarget defect apart from a metric that the source motion itself cannot meet. Same clips, same
50 fps resampling, same definitions as ``rt_cpu.clip_qa`` (penetration after the same median-lowest-sole-at-0 offset;
stance foot = foot with the lower sole point when < 0.02 m; skate = planar speed of its ankle-roll link). Sole points
of the reference body = its foot collision geoms (regex ``^(left|right)_foot[1-7]_collision$``; spheres/capsules/boxes).
Motion stays in memory. Output: ``spikes/B1-RT/diag-source-baseline-attempt<N>.json``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import retarget_rta as R  # noqa: E402
import rt_cpu as T  # noqa: E402
from supermimic_compat import resample_motion  # noqa: E402

FOOT_RE = r"^(left|right)_foot[1-7]_collision$"


def lowest_point(m, d, g) -> float:
    t, s, c = m.geom_type[g], m.geom_size[g], d.geom_xpos[g]
    Rm = d.geom_xmat[g].reshape(3, 3)
    if t == mujoco.mjtGeom.mjGEOM_SPHERE:
        return c[2] - s[0]
    if t == mujoco.mjtGeom.mjGEOM_CAPSULE:
        ax = Rm[:, 2]
        return min(c[2] + s[1] * ax[2], c[2] - s[1] * ax[2]) - s[0]
    if t == mujoco.mjtGeom.mjGEOM_BOX:
        return c[2] - float(np.abs(Rm[2, :]) @ s[:3])
    raise ValueError(f"geom type {t}")


def source_metrics(rm, raw) -> dict:
    mot = resample_motion(raw, R.INPUT_FPS, R.OUTPUT_FPS)
    d = mujoco.MjData(rm)
    names = [mujoco.mj_id2name(rm, mujoco.mjtObj.mjOBJ_GEOM, g) or "" for g in range(rm.ngeom)]
    feet = {s: [g for g, n in enumerate(names) if re.fullmatch(FOOT_RE, n) and n.startswith(s)] for s in ("left", "right")}
    bodies = [rm.body("left_ankle_roll_link").id, rm.body("right_ankle_roll_link").id]
    Tn = mot.num_frames
    z = np.empty((Tn, 2))
    xy = np.empty((Tn, 2, 2))
    for t in range(Tn):
        d.qpos[0:3], d.qpos[3:7], d.qpos[7:] = mot.root_pos[t], mot.root_quat[t], mot.joint_pos[t]
        mujoco.mj_kinematics(rm, d)
        for k, s in enumerate(("left", "right")):
            z[t, k] = min(lowest_point(rm, d, g) for g in feet[s])
            xy[t, k] = d.xpos[bodies[k], :2]
    zmin = z.min(axis=1)
    off = -float(np.median(zmin))
    z = z + off
    pen = np.maximum(-z.min(axis=1), 0.0)
    vel = np.zeros((Tn, 2))
    vel[1:] = np.linalg.norm(np.diff(xy, axis=0), axis=-1) * R.OUTPUT_FPS
    vel[0] = vel[1]
    st = z.argmin(axis=1)
    has = z.min(axis=1) < T.RT4_STANCE_Z
    sk = vel[np.arange(Tn), st][has]
    return {"frames_50fps": int(Tn), "raw_lowest_sole_median_m": -off, "penetration_p95_m": float(np.percentile(pen, 95)),
            "skate_p50_mps": float(np.percentile(sk, 50)), "skate_p95_mps": float(np.percentile(sk, 95)),
            "stance_frames": int(has.sum()), "n_foot_geoms": {s: len(v) for s, v in feet.items()}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--attempt", type=int, required=True)
    ap.add_argument("--rev", required=True)
    a = ap.parse_args()
    out = HERE / f"diag-source-baseline-attempt{a.attempt}.json"
    if out.exists():
        sys.exit(f"{out} exists")
    rm = R.ref_model()
    res = {"script": "spikes/B1-RT/diag_source_baseline.py", "rev": a.rev, "clips": {}}
    for _, first, repl in T.SLOTS:
        for name in (first, repl):
            raw, h = T.fetch_clip(name, a.rev)
            res["clips"][name] = {"csv_sha256": h, **source_metrics(rm, raw)}
            del raw
    out.write_text(json.dumps(res, indent=2))
    for k, v in res["clips"].items():
        print(f"SRC {k} pen_p95={v['penetration_p95_m']:.4f} skate_p50={v['skate_p50_mps']:.3f} skate_p95={v['skate_p95_mps']:.3f}")


if __name__ == "__main__":
    main()
