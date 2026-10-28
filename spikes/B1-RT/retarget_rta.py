"""RT-a: joint-space retarget of the 29-DoF reference LAFAN1 retargets onto the home humanoid (AS-4).

Input: one upstream retarget CSV array (N, 36) in the LAFAN1 layout (root pos m, root quat xyzw, 29 joint angles in
the reference joint order), at 30 fps. Output: the home-humanoid motion in the upstream npz layout (50 fps), built by
the upstream ``resample_motion`` / ``forward_kinematics`` routines applied to the home-humanoid model.

Motion data stays in memory unless :func:`write_npz` is called (GPU host only; X-002).
"""

from __future__ import annotations

import io
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import home_humanoid as H  # noqa: E402

# Reference joint order of the upstream CSV (supermimic.data.motion_convert.G1_JOINT_NAMES at the pin).
REF_JOINT_NAMES: tuple[str, ...] = (
    "left_hip_pitch_joint", "left_hip_roll_joint", "left_hip_yaw_joint", "left_knee_joint",
    "left_ankle_pitch_joint", "left_ankle_roll_joint",
    "right_hip_pitch_joint", "right_hip_roll_joint", "right_hip_yaw_joint", "right_knee_joint",
    "right_ankle_pitch_joint", "right_ankle_roll_joint",
    "waist_yaw_joint", "waist_roll_joint", "waist_pitch_joint",
    "left_shoulder_pitch_joint", "left_shoulder_roll_joint", "left_shoulder_yaw_joint", "left_elbow_joint",
    "left_wrist_roll_joint", "left_wrist_pitch_joint", "left_wrist_yaw_joint",
    "right_shoulder_pitch_joint", "right_shoulder_roll_joint", "right_shoulder_yaw_joint", "right_elbow_joint",
    "right_wrist_roll_joint", "right_wrist_pitch_joint", "right_wrist_yaw_joint",
)
INPUT_FPS = 30.0
OUTPUT_FPS = 50.0

# home joint -> reference joint (AS-4 table). Head joints are held at 0; waist and wrists are dropped.
_SUFFIX = {"hip_pitch": "hip_pitch", "hip_roll": "hip_roll", "thigh": "hip_yaw", "calf": "knee",
           "ankle_pitch": "ankle_pitch", "ankle_roll": "ankle_roll", "shoulder_pitch": "shoulder_pitch",
           "shoulder_roll": "shoulder_roll", "upper_arm": "shoulder_yaw", "elbow": "elbow"}
CORRESPONDENCE: dict[str, str] = {}
for _s, _S in (("l", "left"), ("r", "right")):
    for _h, _g in _SUFFIX.items():
        CORRESPONDENCE[f"{_s}_{_h}_joint"] = f"{_S}_{_g}_joint"
OFFSET_JOINTS = ("l_elbow_joint", "r_elbow_joint")  # zero offset -phi (AS-4)
# Child segment used for the zero-pose direction check: joint -> (home parent body, home child body,
# ref parent body, ref child body).
_SEG = {
    "hip_pitch": ("{s}_hip_pitch_link", "{s}_calf_link", "{S}_hip_pitch_link", "{S}_knee_link"),
    "calf": ("{s}_calf_link", "{s}_ankle_pitch_link", "{S}_knee_link", "{S}_ankle_pitch_link"),
    "shoulder_pitch": ("{s}_shoulder_roll_link", "{s}_elbow_link", "{S}_shoulder_roll_link", "{S}_elbow_link"),
}


def ref_model() -> mujoco.MjModel:
    import mjlab

    m = mujoco.MjModel.from_xml_path(str(Path(mjlab.__file__).parent / "asset_zoo/robots/unitree_g1/xmls/g1.xml"))
    names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, j) for j in range(1, m.njnt)]
    assert tuple(names) == REF_JOINT_NAMES, names
    return m


def home_model() -> mujoco.MjModel:
    return H.load_overlaid_model(with_floor=False, add_actuators=False, add_keyframe=False)


def _unit(v):
    return v / np.linalg.norm(v)


def _seg_dir(m, d, a, b):
    return _unit(d.xpos[m.body(b).id] - d.xpos[m.body(a).id])


def elbow_phi(rm: mujoco.MjModel, side: str) -> float:
    """Reference elbow angle at which forearm (elbow->wrist roll) is parallel to upper arm (shoulder roll->elbow)."""
    S = {"l": "left", "r": "right"}[side]
    d = mujoco.MjData(rm)
    j = rm.joint(f"{S}_elbow_joint")

    def misalign(theta):
        d.qpos[:] = rm.qpos0
        d.qpos[j.qposadr[0]] = theta
        mujoco.mj_kinematics(rm, d)
        up = _seg_dir(rm, d, f"{S}_shoulder_roll_link", f"{S}_elbow_link")
        fo = _seg_dir(rm, d, f"{S}_elbow_link", f"{S}_wrist_roll_link")
        return float(np.arccos(np.clip(up @ fo, -1, 1)))

    grid = np.linspace(-0.5, math.pi, 3501)
    best = min(grid, key=misalign)
    return float(best)


def sign_check(rm: mujoco.MjModel | None = None, hm: mujoco.MjModel | None = None) -> dict:
    """AS-4 axis-sign / zero-offset check. ``ok`` false fails RT-4."""
    rm = rm or ref_model()
    hm = hm or home_model()
    dr, dh = mujoco.MjData(rm), mujoco.MjData(hm)
    mujoco.mj_kinematics(rm, dr)
    mujoco.mj_kinematics(hm, dh)
    rows, ok = [], True
    for h, g in CORRESPONDENCE.items():
        ah = dh.xaxis[hm.joint(h).id]
        ag = dr.xaxis[rm.joint(g).id]
        dot = float(ah @ ag)
        row = {"home": h, "ref": g, "axis_dot": round(dot, 4), "sign": 1 if dot > 0 else -1}
        if abs(dot) < 0.9 or dot < 0:
            ok = False
            row["fail"] = "axis"
        rows.append(row)
    segs = []
    for s, S in (("l", "left"), ("r", "right")):
        for key, (a, b, ra, rb) in _SEG.items():
            u = _seg_dir(hm, dh, a.format(s=s), b.format(s=s))
            v = _seg_dir(rm, dr, ra.format(S=S), rb.format(S=S))
            ang = math.degrees(math.acos(float(np.clip(u @ v, -1, 1))))
            segs.append({"pair": f"{s}_{key}", "zero_pose_angle_deg": round(ang, 2)})
            if ang > 15.0:
                ok = False
    phi = {s: elbow_phi(rm, s) for s in ("l", "r")}
    if not all(0.9 < p < 1.9 for p in phi.values()):
        ok = False
    return {"ok": ok, "joints": rows, "segments": segs, "elbow_phi": phi}


def leg_length(m: mujoco.MjModel, hip: str, ankle: str) -> float:
    d = mujoco.MjData(m)
    d.qpos[:] = m.qpos0
    mujoco.mj_kinematics(m, d)
    return float(d.xanchor[m.joint(hip).id][2] - d.xanchor[m.joint(ankle).id][2])


@dataclass
class RetargetCtx:
    rm: mujoco.MjModel
    hm: mujoco.MjModel
    scale: float
    phi: dict
    lo: np.ndarray
    hi: np.ndarray
    check: dict


def make_ctx() -> RetargetCtx:
    rm, hm = ref_model(), home_model()
    s = leg_length(hm, "l_hip_pitch_joint", "l_ankle_pitch_joint") / leg_length(rm, "left_hip_pitch_joint", "left_ankle_pitch_joint")
    chk = sign_check(rm, hm)
    rng = np.array([hm.jnt_range[hm.joint(n).id] for n in H.JOINT_NAMES])
    return RetargetCtx(rm, hm, s, chk["elbow_phi"], rng[:, 0], rng[:, 1], chk)


def map_joints(ref_q: np.ndarray, ctx: RetargetCtx) -> tuple[np.ndarray, np.ndarray]:
    """(N,29) reference angles -> (N,22) home angles before clipping, and the clipped angles."""
    idx = {n: i for i, n in enumerate(REF_JOINT_NAMES)}
    out = np.zeros((ref_q.shape[0], H.NUM_JOINTS))
    for k, n in enumerate(H.JOINT_NAMES):
        g = CORRESPONDENCE.get(n)
        if g is None:
            continue  # head: held at 0
        q = ref_q[:, idx[g]].copy()
        if n in OFFSET_JOINTS:
            q = q - ctx.phi[n[0]]
        out[:, k] = q
    return out, np.clip(out, ctx.lo, ctx.hi)


def sole_min_z(hm: mujoco.MjModel, qpos: np.ndarray) -> np.ndarray:
    d = mujoco.MjData(hm)
    out = np.empty(qpos.shape[0])
    for t in range(qpos.shape[0]):
        d.qpos[:] = qpos[t]
        mujoco.mj_kinematics(hm, d)
        out[t] = H.lowest_sole_z(hm, d)
    return out


def retarget_raw(raw: np.ndarray, ctx: RetargetCtx) -> dict:
    """(N,36) reference CSV array -> dict with the (N, 7+22) home raw array (LAFAN1 layout, xyzw) + diagnostics."""
    pos = raw[:, 0:3] * ctx.scale
    quat_xyzw = raw[:, 3:7]
    q_unclipped, q = map_joints(raw[:, 7:], ctx)
    qpos = np.concatenate([pos, quat_xyzw[:, [3, 0, 1, 2]], q], axis=1)
    zmin = sole_min_z(ctx.hm, qpos)
    dz = -float(np.median(zmin))
    pos[:, 2] += dz
    home_raw = np.concatenate([pos, quat_xyzw, q], axis=1)
    return {"raw": home_raw, "q_unclipped": q_unclipped, "z_offset": dz}


def to_motion(home_raw: np.ndarray):
    """Upstream resample (30 -> 50 fps, mjlab velocity conventions). Works for any joint count."""
    from supermimic_compat import resample_motion

    return resample_motion(home_raw, INPUT_FPS, OUTPUT_FPS)


def write_npz(path, motion, ctx: RetargetCtx, source: str) -> None:
    from supermimic_compat import forward_kinematics

    b = forward_kinematics(ctx.hm, motion)
    np.savez(
        path,
        fps=np.array([OUTPUT_FPS], dtype=np.float32),
        joint_pos=motion.joint_pos.astype(np.float32),
        joint_vel=motion.joint_vel.astype(np.float32),
        body_pos_w=b.pos_w.astype(np.float32),
        body_quat_w=b.quat_w.astype(np.float32),
        body_lin_vel_w=b.lin_vel_w.astype(np.float32),
        body_ang_vel_w=b.ang_vel_w.astype(np.float32),
        joint_names=np.array(H.JOINT_NAMES),
        body_names=np.array(b.body_names),
        source=np.array(source + " [RT-a home humanoid]"),
        input_fps=np.array([INPUT_FPS], dtype=np.float32),
    )


def parse_csv_bytes(data: bytes) -> np.ndarray:
    arr = np.loadtxt(io.BytesIO(data), delimiter=",", dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 7 + len(REF_JOINT_NAMES):
        raise ValueError(f"expected (N, 36), got {arr.shape}")
    return arr
