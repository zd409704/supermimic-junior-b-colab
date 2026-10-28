"""Descriptor v2 (candidate Y) -- standalone spike module. Imports code/ read-only."""
from __future__ import annotations

import hashlib
import math
import re
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
from attention_policy import (  # noqa: E402,F401
    DEFAULT_JOINT_NAMES, AttentionDecoder, AttentionDecoderCfg, count_params, permute_obs_history,
    _limb_from_name, _side_from_name,
)
from mlp_baseline import MLPDecoderCfg, build_matched_mlp  # noqa: E402,F401

MORPH_DIM_V2 = 16
DESC_V2 = dict(version="v2", sigma0=0.25, tau_hat0=0.5, depth_c=8.0, range_c=math.pi, g=9.81)
BOUND = 3.5
COLS = dict(anchor_hat=[0, 1, 2], axis=[3, 4, 5], q_def=[6], q_range=[7, 8], chain_depth=[9], side=[10],
            limb=[11, 12, 13], log_sigma=[14], log_tau=[15])
REF_TOTAL_MASS = 35.0  # kg, Y s5 ("M ~ 35 kg"); synthetic reference has no masses


@dataclass(frozen=True)
class ActuatorParams:
    effort_limit: float
    stiffness: float
    damping: float
    action_scale: float


# ---------------------------------------------------------------- actuator parameter builders
def _armature(r, g):
    """Two-stage planetary reflected inertia (mjlab formula, reconstructed; reproduces the
    pinned kp values: r1*(g1 g2 g3)^2 + r2*g3^2 + r3)."""
    return r[0] * (g[0] * g[1] * g[2]) ** 2 + r[1] * g[2] ** 2 + r[2]


_WN = 10 * 2.0 * 3.1415926535
_A5020 = _armature((0.139e-4, 0.017e-4, 0.169e-4), (1, 1 + 46 / 18, 1 + 56 / 16))
_A7520_14 = _armature((0.489e-4, 0.098e-4, 0.533e-4), (1, 4.5, 1 + 48 / 22))
_A7520_22 = _armature((0.489e-4, 0.109e-4, 0.738e-4), (1, 4.5, 5))
_A4010 = _armature((0.068e-4, 0.0, 0.0), (1, 5, 5))
# (name regexes, effort, armature) -- groups exactly as in the pinned constants
_REF_GROUPS = [
    ((r".*_elbow_joint", r".*_shoulder_pitch_joint", r".*_shoulder_roll_joint", r".*_shoulder_yaw_joint",
      r".*_wrist_roll_joint"), 25.0, _A5020),
    ((r".*_hip_pitch_joint", r".*_hip_yaw_joint", r"waist_yaw_joint"), 88.0, _A7520_14),
    ((r".*_hip_roll_joint", r".*_knee_joint"), 139.0, _A7520_22),
    ((r".*_wrist_pitch_joint", r".*_wrist_yaw_joint"), 5.0, _A4010),
    ((r"waist_pitch_joint", r"waist_roll_joint"), 50.0, 2 * _A5020),
    ((r".*_ankle_pitch_joint", r".*_ankle_roll_joint"), 50.0, 2 * _A5020),
]
_KNEES_BENT = [(r".*_hip_pitch_joint", -0.312), (r".*_knee_joint", 0.669), (r".*_ankle_pitch_joint", -0.363),
               (r".*_elbow_joint", 0.6), (r"left_shoulder_roll_joint", 0.2), (r"left_shoulder_pitch_joint", 0.2),
               (r"right_shoulder_roll_joint", -0.2), (r"right_shoulder_pitch_joint", 0.2)]


def ref29_actuator_params(joint_names):
    """-> (list[ActuatorParams], default_qpos list). Each name must match exactly one group expression."""
    out = []
    for n in joint_names:
        hits = [(e, a) for exprs, e, a in _REF_GROUPS for x in exprs if re.fullmatch(x, n)]
        if len(hits) != 1:
            raise ValueError(f"{n}: matched {len(hits)} actuator groups")
        e, a = hits[0]
        kp = a * _WN ** 2
        out.append(ActuatorParams(e, kp, 2.0 * 2.0 * a * _WN, 0.25 * e / kp))
    q = []
    for n in joint_names:
        v = [val for x, val in _KNEES_BENT if re.fullmatch(x, n)]
        q.append(v[-1] if v else 0.0)  # keyframe joint_pos: later patterns do not overlap here
    return out, q


def _home_group(n):
    if any(k in n for k in ("hip", "thigh", "calf", "knee", "ankle")):
        return "leg"
    if any(k in n for k in ("shoulder", "upper_arm", "elbow", "wrist")):
        return "arm"
    if any(k in n for k in ("head", "neck")):
        return "head"
    raise ValueError(n)


def home_actuator_params(joint_names, effort_limits, inertia_by_group, wn=20 * math.pi, zeta=2.0):
    out = []
    for n, tau in zip(joint_names, effort_limits):
        I = inertia_by_group[_home_group(n)]
        kp = I * wn ** 2
        out.append(ActuatorParams(float(tau), kp, 2 * zeta * I * wn, 0.25 * float(tau) / kp))
    return out


def home_default_qpos(joint_names):
    """AS-2 placeholder default pose."""
    pat = [(r".*_hip_pitch_joint", -0.2), (r".*_calf_joint", 0.4), (r".*_ankle_pitch_joint", -0.2),
           (r"l_shoulder_roll_joint", 0.2), (r"r_shoulder_roll_joint", -0.2)]
    return [next((v for x, v in pat if re.fullmatch(x, n)), 0.0) for n in joint_names]


# ---------------------------------------------------------------- core builder
def _onehot(limb):
    o = [0.0, 0.0, 0.0]
    o[limb] = 1.0
    return o


def _assemble(P, A, qdef, rng, depth, side, limb, tau, sig, M, *, scale_norm, ablate, names, extra_meta):
    """P (J,3) root-frame anchors, A (J,3) axes; limb: list of int (resolved)."""
    J = len(names)
    limb = np.asarray(limb)
    leg = limb == 0
    assert leg.sum() >= 2
    L = float(P[leg, 2].max() - P[leg, 2].min())
    hip = leg & (depth == 1)
    c = P[hip].mean(0)
    L_a, c_a = (L, c) if scale_norm else (1.0, np.zeros(3))
    g = DESC_V2["g"]
    log_tau = (np.zeros(J) if tau is None else np.log(np.asarray(tau) / (M * g * L) / DESC_V2["tau_hat0"]))
    log_sig = (np.zeros(J) if sig is None else np.log(np.asarray(sig) / DESC_V2["sigma0"]))
    rows = np.concatenate([(P - c_a) / L_a, A, np.asarray(qdef, float)[:, None],
                           np.asarray(rng, float) / DESC_V2["range_c"], depth[:, None] / DESC_V2["depth_c"],
                           np.asarray(side, float)[:, None], np.array([_onehot(int(l)) for l in limb]),
                           log_sig[:, None], log_tau[:, None]], axis=1)
    for a in ablate:
        rows[:, COLS[a]] = 0.0
    assert np.isfinite(rows).all(), "non-finite descriptor"
    nu = len({tuple(r) for r in np.round(rows, 5)})
    assert nu == J, f"descriptor rows not distinct: {nu}/{J}"
    assert np.abs(rows).max() <= BOUND, f"|x| bound exceeded: {np.abs(rows).max()}"
    r32 = rows.astype(np.float32)
    meta = dict(DESC_V2, L=L, c=c.tolist(), M=float(M), names=list(names), q_def=list(map(float, qdef)),
                range=np.asarray(rng).tolist(), scale_norm=bool(scale_norm), ablate=list(ablate),
                matrix=r32.tolist(), sha256=hashlib.sha256(r32.tobytes()).hexdigest(), **extra_meta)
    return torch.tensor(r32), meta


def morphology_v2(model, joint_names, default_qpos, actuator_params, *, scale_norm=True, ablate=()):
    import mujoco
    names = tuple(joint_names)
    J = len(names)
    d = mujoco.MjData(model)
    mujoco.mj_forward(model, d)
    R, p0 = d.xmat[1].reshape(3, 3).copy(), d.xpos[1].copy()
    jid = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, n) for n in names]
    P = np.stack([R.T @ (d.xanchor[j] - p0) for j in jid])
    A = np.stack([R.T @ d.xaxis[j] for j in jid])
    if hasattr(default_qpos, "keys"):
        qdef = [float(default_qpos[n]) for n in names]
    else:
        qdef = [float(x) for x in default_qpos]
        assert len(qdef) == J
    rng = np.stack([model.jnt_range[j] for j in jid])
    limb = [_limb_from_name(n) for n in names]
    source = ["name" if l is not None else "geometry" for l in limb]
    body_of = [int(model.jnt_bodyid[j]) for j in jid]
    hinge_of_body = {b: i for i, b in enumerate(body_of)}

    def depths(limb_arr):
        out = np.zeros(J)
        for i, b in enumerate(body_of):
            k = 0
            while b > 0:
                h = hinge_of_body.get(b)
                if h is not None and limb_arr[h] == limb_arr[i]:
                    k += 1
                b = int(model.body_parentid[b])
            out[i] = k
        return out

    def stats(limb_arr, depth):
        leg = np.array([l == 0 for l in limb_arr])
        L = P[leg, 2].max() - P[leg, 2].min()
        c = P[leg & (depth == 1)].mean(0)
        return L, c

    if any(l is None for l in limb):  # geometric fallback after L, c (iterate once)
        tmp = [-1 if l is None else l for l in limb]
        depth = depths(tmp)
        L, c = stats(tmp, depth)
        ah = (P - c) / L
        for i, l in enumerate(limb):
            if l is None:
                limb[i] = 0 if ah[i, 2] <= 0.1 else (1 if abs(ah[i, 1]) < 0.15 else 2)
    depth = depths(limb)
    side = []
    for i, n in enumerate(names):
        s = _side_from_name(n)
        side.append(s if s != 0.0 else float(np.sign(np.round(P[i, 1], 3))))
    M = float(model.body_mass.sum())
    tau = [ap.effort_limit for ap in actuator_params]
    sig = [ap.action_scale for ap in actuator_params]
    kp = [ap.stiffness for ap in actuator_params]
    kd = [ap.damping for ap in actuator_params]
    for n, t, s, k in zip(names, tau, sig, kp):
        if abs(s - 0.25 * t / k) > 1e-6 * s:
            warnings.warn(f"{n}: action_scale {s} != 0.25*tau/kp (env sigma stays authoritative)")
    return _assemble(P, A, qdef, rng, depth, side, limb, tau, sig, M, scale_norm=scale_norm, ablate=ablate,
                     names=names, extra_meta=dict(tau=tau, kp=kp, kd=kd, sigma=sig, limb_source=source))


# Fixed semantic stage table (1-based chain stage within the limb), keyed by joint name (no list order).
_STAGE = [(r"(?:left_|right_|l_|r_)?hip_pitch_joint", 1), (r"(?:left_|right_|l_|r_)?hip_roll_joint", 2),
          (r"(?:left_|right_|l_|r_)?(?:hip_yaw|thigh)_joint", 3), (r"(?:left_|right_|l_|r_)?(?:knee|calf)_joint", 4),
          (r"(?:left_|right_|l_|r_)?ankle_pitch_joint", 5), (r"(?:left_|right_|l_|r_)?ankle_roll_joint", 6),
          (r"waist_yaw_joint", 1), (r"waist_roll_joint", 2), (r"waist_pitch_joint", 3),
          (r"head_yaw_joint", 1), (r"head_pitch_joint", 2),
          (r"(?:left_|right_|l_|r_)?shoulder_pitch_joint", 1), (r"(?:left_|right_|l_|r_)?shoulder_roll_joint", 2),
          (r"(?:left_|right_|l_|r_)?(?:shoulder_yaw|upper_arm)_joint", 3), (r"(?:left_|right_|l_|r_)?elbow_joint", 4),
          (r"(?:left_|right_|l_|r_)?wrist_roll_joint", 5), (r"(?:left_|right_|l_|r_)?wrist_pitch_joint", 6),
          (r"(?:left_|right_|l_|r_)?wrist_yaw_joint", 7)]


def _stage(name):
    h = [s for x, s in _STAGE if re.fullmatch(x, name)]
    if len(h) != 1:
        raise ValueError(f"no unique stage for joint {name!r}")
    return h[0]


def synthetic_morphology_v2(joint_names=DEFAULT_JOINT_NAMES, default_qpos=None, actuator_params=None, *,
                            scale_norm=True, ablate=(), total_mass=REF_TOTAL_MASS):
    """Order-invariant synthetic descriptor: depth/anchors from the stage table keyed by name."""
    names = tuple(joint_names)
    J = len(names)
    P, A, side, limb, depth = [], [], [], [], np.zeros(J)
    for i, n in enumerate(names):
        s = _side_from_name(n)
        l = _limb_from_name(n)
        l = 2 if l is None else l
        st = _stage(n)
        d0 = st - 1
        z = (-0.5, 0.0, 0.4)[l]
        if l == 0:
            a = [0.0, 0.1 * s, z - 0.1 * d0]
        elif l == 1:
            a = [0.0, 0.0, z + 0.05 * d0]
        else:
            a = [0.0, (0.15 + 0.08 * d0) * s, z]
        axn = next((k for k in ("roll", "pitch", "yaw") if k in n), "pitch")
        ax = [0.0, 0.0, 0.0]
        ax[("roll", "pitch", "yaw").index(axn)] = 1.0
        P.append(a); A.append(ax); side.append(s); limb.append(l); depth[i] = st
    P, A = np.array(P), np.array(A)
    qdef = np.zeros(J) if default_qpos is None else np.asarray(default_qpos, float)
    rng = np.tile([-0.5, 0.5], (J, 1))
    if actuator_params is None:
        tau = sig = None
        M = 1.0
        kp = kd = None
    else:
        tau = [ap.effort_limit for ap in actuator_params]
        sig = [ap.action_scale for ap in actuator_params]
        kp = [ap.stiffness for ap in actuator_params]
        kd = [ap.damping for ap in actuator_params]
        M = float(total_mass)
    return _assemble(P, A, qdef, rng, depth, side, limb, tau, sig, M, scale_norm=scale_norm, ablate=ablate,
                     names=names, extra_meta=dict(tau=tau, kp=kp, kd=kd, sigma=sig, limb_source=["name"] * J))
