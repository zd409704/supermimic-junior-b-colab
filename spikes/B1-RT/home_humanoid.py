"""Home humanoid: asset contract, load-time overlay and plant constants (B1-P0 / P6a; SCHEME_PLAN §5).

The owner files under ``assets/home_humanoid_mjcf/`` are read-only. Everything this module changes is applied
to an in-memory ``mujoco.MjSpec`` at load time:

* the two embedded floor planes are deleted (BLK-5; the scene supplies its own terrain);
* every collision geom gets a stable name (``<body>_collision<k>``; the 4 sole capsules of each foot become
  ``l_foot<k>_collision`` / ``r_foot<k>_collision``) so mjlab collision / friction configs can address them;
* one position actuator per hinge (BLK-1), gains from AS-1, force range = the hinge ``actuatorfrcrange``;
  joint armature set to the AS-1 reflected inertia (BLK-2);
* a ``home`` keyframe at the AS-2 default pose (BLK-6), standing on z = 0.

Two consumers share the same constants:
* :func:`get_home_humanoid_robot_cfg` — mjlab ``EntityCfg`` (GPU env, RT-6..RT-8, P6d). mjlab adds the actuators
  and the keyframe itself from ``articulation`` / ``init_state``;
* :func:`load_overlaid_model` — plain CPU MuJoCo model with the same actuators (RT-1..RT-5, FK, retarget).

Assumption IDs (AS-n) refer to ``spikes/B1-RT/ASSUMPTIONS.md``. Prose and identifiers say "home humanoid";
exported filenames are reached only through the directory glob.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
PROGRAM_ROOT = HERE.parents[1]
ASSET_DIR = Path(os.environ.get("HOME_HUMANOID_ASSET_DIR", PROGRAM_ROOT / "assets" / "home_humanoid_mjcf"))
OWNER_XML_SHA256 = "856ce7021f0adda213b598c6db8b6efe3d298360931a7e7612aba21787076d82"
N_MESHES = 27

# Hinge order of the owner MJCF (= actuator order = obs joint order = descriptor row order; S1 for body 2).
JOINT_NAMES: tuple[str, ...] = (
    "r_shoulder_pitch_joint", "r_shoulder_roll_joint", "r_upper_arm_joint", "r_elbow_joint",
    "l_shoulder_pitch_joint", "l_shoulder_roll_joint", "l_upper_arm_joint", "l_elbow_joint",
    "head_yaw_joint", "head_pitch_joint",
    "r_hip_pitch_joint", "r_hip_roll_joint", "r_thigh_joint", "r_calf_joint", "r_ankle_pitch_joint", "r_ankle_roll_joint",
    "l_hip_pitch_joint", "l_hip_roll_joint", "l_thigh_joint", "l_calf_joint", "l_ankle_pitch_joint", "l_ankle_roll_joint",
)
NUM_JOINTS = len(JOINT_NAMES)
N_BODIES = 28  # incl. world

# ------------------------------------------------------------------------------------------- AS-1 actuators
# Armature is 0 in the MJCF and no motor data exists (BLK-2). Assumed reflected inertia per joint group, natural
# frequency 10 Hz and damping ratio 2 as in the upstream recipe: kp = I wn^2, kd = 2 zeta I wn. Arm/head values are
# the D-DESC spike's; the leg value (0.015, D-DESC used 0.01) is the smallest of {0.01, 0.015, 0.02, 0.03} whose
# zero-action stand passes RT-3 with half margin (logs/p6/as1-calibration-attempt1.log). Effort limits = the MJCF
# actuatorfrcrange of each group.
NATURAL_FREQ = 10 * 2.0 * 3.1415926535
DAMPING_RATIO = 2.0
GROUPS: dict[str, dict] = {
    "leg": {"expr": (r"[lr]_hip_pitch_joint", r"[lr]_hip_roll_joint", r"[lr]_thigh_joint", r"[lr]_calf_joint",
                     r"[lr]_ankle_pitch_joint", r"[lr]_ankle_roll_joint"), "armature": 0.015, "effort": 21.0},
    "arm": {"expr": (r"[lr]_shoulder_pitch_joint", r"[lr]_shoulder_roll_joint", r"[lr]_upper_arm_joint",
                     r"[lr]_elbow_joint"), "armature": 0.005, "effort": 10.0},
    "head": {"expr": (r"head_yaw_joint", r"head_pitch_joint"), "armature": 0.002, "effort": 3.7},
}


def group_of(joint: str) -> str:
    hits = [g for g, v in GROUPS.items() if any(re.fullmatch(x, joint) for x in v["expr"])]
    if len(hits) != 1:
        raise ValueError(f"{joint}: matched {len(hits)} actuator groups")
    return hits[0]


def gains(group: str, kp_scale: float = 1.0) -> tuple[float, float]:
    a = GROUPS[group]["armature"]
    return kp_scale * a * NATURAL_FREQ**2, 2.0 * DAMPING_RATIO * a * NATURAL_FREQ


def action_scale() -> dict[str, float]:
    """Env action scale per group expression: sigma = 0.25 * effort / kp (upstream rule; D-003)."""
    out = {}
    for g, v in GROUPS.items():
        kp, _ = gains(g)
        for x in v["expr"]:
            out[x] = 0.25 * v["effort"] / kp
    return out


# ------------------------------------------------------------------------------------------- AS-2 default pose
# Knees and hips slightly flexed (calf positive = flexion; hip/ankle pitch negative), shoulder roll abducted so the
# wrists clear the hip/thigh capsules (BLK-4). Joints not listed are 0.
DEFAULT_POSE: dict[str, float] = {
    r"[lr]_hip_pitch_joint": -0.2,
    r"[lr]_calf_joint": 0.4,
    r"[lr]_ankle_pitch_joint": -0.2,
    r"l_shoulder_roll_joint": 0.2,
    r"r_shoulder_roll_joint": -0.2,
}


def default_joint_pos() -> np.ndarray:
    out = []
    for n in JOINT_NAMES:
        v = [val for x, val in DEFAULT_POSE.items() if re.fullmatch(x, n)]
        if len(v) > 1:
            raise ValueError(f"{n}: several default-pose patterns")
        out.append(v[0] if v else 0.0)
    return np.asarray(out, dtype=np.float64)


# ------------------------------------------------------------------------------------------- AS-3 bodies
# Semantic counterparts of the upstream 14 tracked bodies (pelvis/hip roll/knee/ankle roll/torso/shoulder roll/
# elbow/wrist), plus the head pitch link (SCHEME_PLAN AS-3). Anchor = torso, root = base (free-joint body).
TRACKED_BODIES: tuple[str, ...] = (
    "base_link",
    "l_hip_roll_link", "l_calf_link", "l_ankle_roll_link",
    "r_hip_roll_link", "r_calf_link", "r_ankle_roll_link",
    "torso_link",
    "l_shoulder_roll_link", "l_elbow_link", "l_wrist_link",
    "r_shoulder_roll_link", "r_elbow_link", "r_wrist_link",
    "head_pitch_link",
)
ANCHOR_BODY = "torso_link"
ROOT_BODY = "base_link"
COM_BODY = "torso_link"
FOOT_BODIES = ("l_ankle_roll_link", "r_ankle_roll_link")
FOOT_GEOM_REGEX = r"^(l|r)_foot[1-4]_collision$"
FOOT_SITES = ("l_anatomical_ankle", "r_anatomical_ankle")
# The 29-DoF reference termination height threshold (0.25 m) and torso COM randomisation (+-0.05 m) are lengths;
# both are multiplied by the standing-height ratio measured in RT-1 (AS-5).
REF_ROOT_HEIGHT_THRESHOLD = 0.25


# ------------------------------------------------------------------------------------------- asset contract
def asset_xml() -> Path:
    xs = sorted(ASSET_DIR.glob("*.xml"))
    if len(xs) != 1:
        raise RuntimeError(f"home humanoid: expected exactly one *.xml under {ASSET_DIR}, found {len(xs)}")
    return xs[0]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def asset_hashes() -> dict:
    """sha256 of the owner XML and every manifest mesh, compared to the contract. Raises nothing; see ``ok``."""
    xml = asset_xml()
    man = json.loads((ASSET_DIR / "mesh_manifest.json").read_text())
    meshes = {e["name"]: {"expected": e["sha256"], "actual": _sha(ASSET_DIR / "meshes" / e["name"])} for e in man}
    out = {
        "xml_sha256": _sha(xml),
        "xml_expected": OWNER_XML_SHA256,
        "n_manifest": len(man),
        "n_mesh_files": len(list((ASSET_DIR / "meshes").glob("*"))),
        "mesh_mismatch": sorted(n for n, v in meshes.items() if v["expected"] != v["actual"]),
        "manifest_sha256": _sha(ASSET_DIR / "mesh_manifest.json"),
    }
    out["ok"] = (out["xml_sha256"] == OWNER_XML_SHA256 and out["n_manifest"] == N_MESHES
                 and out["n_mesh_files"] == N_MESHES and not out["mesh_mismatch"])
    return out


def verify_asset() -> dict:
    h = asset_hashes()
    if not h["ok"]:
        raise RuntimeError(f"home humanoid asset contract violated: {h}")
    return h


# ------------------------------------------------------------------------------------------- load-time overlay
def owner_spec() -> mujoco.MjSpec:
    """Owner MJCF as an MjSpec (meshdir resolves next to the XML). Not modified on disk."""
    return mujoco.MjSpec.from_file(str(asset_xml()))


def _body_of(geom: mujoco.MjsGeom) -> str:
    return geom.parent.name


def overlay_spec(spec: mujoco.MjSpec) -> dict:
    """Geometry-only overlay shared by both consumers: delete floors, name collision geoms. Returns a report."""
    rep = {"deleted_floor_geoms": [], "named_collision_geoms": 0, "foot_geoms": []}
    for g in list(spec.worldbody.geoms):
        if g.type == mujoco.mjtGeom.mjGEOM_PLANE:
            rep["deleted_floor_geoms"].append(g.name)
            spec.delete(g)
    per_body: dict[str, int] = {}
    for g in spec.geoms:
        if g.contype == 0 and g.conaffinity == 0:
            continue  # visual mesh geoms (contype=conaffinity=0 in the owner file)
        b = _body_of(g)
        if g.name:
            continue
        if b in FOOT_BODIES and g.type == mujoco.mjtGeom.mjGEOM_CAPSULE:
            k = per_body.get(b + ":foot", 0) + 1
            per_body[b + ":foot"] = k
            g.name = f"{b[0]}_foot{k}_collision"
            rep["foot_geoms"].append(g.name)
        else:
            k = per_body.get(b, 0) + 1
            per_body[b] = k
            g.name = f"{b}_collision{k}"
        rep["named_collision_geoms"] += 1
    return rep


def add_position_actuators(spec: mujoco.MjSpec, kp_scale: float = 1.0) -> None:
    """CPU-MuJoCo mirror of mjlab ``BuiltinPositionActuatorCfg`` (one <position> per hinge, joint order)."""
    for n in JOINT_NAMES:
        g = group_of(n)
        kp, kd = gains(g, kp_scale)
        e = GROUPS[g]["effort"]
        j = spec.joint(n)
        j.armature = GROUPS[g]["armature"]
        a = spec.add_actuator(name=n, target=n, trntype=mujoco.mjtTrn.mjTRN_JOINT)
        a.set_to_position(kp=kp, kv=kd)
        a.forcelimited = mujoco.mjtLimited.mjLIMITED_TRUE
        a.forcerange = np.array([-e, e])


def standing_root_height(model: mujoco.MjModel | None = None) -> float:
    """Base height at the AS-2 pose with the lowest sole point on z = 0 (kinematic, no contacts)."""
    m = model or load_overlaid_model(with_floor=False, add_keyframe=False)
    d = mujoco.MjData(m)
    d.qpos[:] = 0.0
    d.qpos[3] = 1.0
    d.qpos[7:] = default_joint_pos()
    mujoco.mj_kinematics(m, d)
    return float(d.qpos[2] - lowest_sole_z(m, d))


def lowest_sole_z(m: mujoco.MjModel, d: mujoco.MjData) -> float:
    """Lowest point of the foot capsules (sole geoms) in world z."""
    zs = []
    for gi in range(m.ngeom):
        name = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, gi) or ""
        if re.fullmatch(FOOT_GEOM_REGEX, name):
            r, half = m.geom_size[gi, 0], m.geom_size[gi, 1]
            axis = d.geom_xmat[gi].reshape(3, 3)[:, 2]
            c = d.geom_xpos[gi]
            zs.append(min(c[2] + half * axis[2], c[2] - half * axis[2]) - r)
    if not zs:
        raise RuntimeError("no sole geoms found")
    return float(min(zs))


def load_overlaid_model(*, with_floor: bool = True, add_actuators: bool = True, kp_scale: float = 1.0,
                        add_keyframe: bool = True) -> mujoco.MjModel:
    """CPU MjModel: owner MJCF + overlay (+ a scene floor plane, + actuators, + ``home`` keyframe)."""
    spec = owner_spec()
    overlay_spec(spec)
    if add_actuators:
        add_position_actuators(spec, kp_scale)
    if with_floor:
        spec.worldbody.add_geom(name="scene_floor", type=mujoco.mjtGeom.mjGEOM_PLANE, size=[0, 0, 0.05],
                                contype=1, conaffinity=1)
    if add_keyframe:
        h = standing_root_height()
        q = np.zeros(7 + NUM_JOINTS)
        q[2], q[3], q[7:] = h, 1.0, default_joint_pos()
        spec.add_key(name="home", qpos=q, ctrl=default_joint_pos() if add_actuators else [])
    m = spec.compile()
    hinge = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, j) for j in range(1, m.njnt)]
    if tuple(hinge) != JOINT_NAMES:
        raise RuntimeError(f"home humanoid hinge order differs from JOINT_NAMES: {hinge}")
    return m


# ------------------------------------------------------------------------------------------- mjlab entity
def _spec_fn() -> mujoco.MjSpec:
    spec = owner_spec()
    overlay_spec(spec)
    return spec


def get_home_humanoid_robot_cfg():
    """mjlab ``EntityCfg`` for the home humanoid (imports mjlab lazily so the CPU checks run without it)."""
    from mjlab.actuator import BuiltinPositionActuatorCfg
    from mjlab.entity import EntityArticulationInfoCfg, EntityCfg
    from mjlab.utils.spec_config import CollisionCfg

    acts = []
    for g, v in GROUPS.items():
        kp, kd = gains(g)
        acts.append(BuiltinPositionActuatorCfg(target_names_expr=v["expr"], stiffness=kp, damping=kd,
                                               effort_limit=v["effort"], armature=v["armature"]))
    collision = CollisionCfg(
        geom_names_expr=(r".*_collision\d*",),
        contype=1,
        conaffinity=1,
        condim={FOOT_GEOM_REGEX: 3, r".*": 1},
        priority={FOOT_GEOM_REGEX: 1, r".*": 0},
        friction={FOOT_GEOM_REGEX: (0.6,)},
    )
    init = EntityCfg.InitialStateCfg(pos=(0.0, 0.0, standing_root_height() + 0.005), joint_pos=dict(DEFAULT_POSE),
                                     joint_vel={".*": 0.0})
    return EntityCfg(init_state=init, collisions=(collision,), spec_fn=_spec_fn,
                     articulation=EntityArticulationInfoCfg(actuators=tuple(acts), soft_joint_pos_limit_factor=0.9),
                     sort_actuators=True)


HOME_HUMANOID_ACTION_SCALE = action_scale()


def height_ratio() -> float:
    """Standing base height of the home humanoid / standing pelvis height of the 29-DoF reference (AS-5)."""
    return standing_root_height() / REF_STANDING_ROOT_HEIGHT


# Reference standing pelvis height used by AS-5: the 29-DoF reference KNEES_BENT keyframe root z (mjlab constants).
REF_STANDING_ROOT_HEIGHT = 0.76


def termination_height_threshold() -> float:
    return REF_ROOT_HEIGHT_THRESHOLD * height_ratio()

