"""Body selection for the B1 cross-embodiment packet (program patch on top of pin d9be385b).

``SM_BODY_MODULE`` unset -> the 29-DoF reference body with the upstream constants, unchanged.
``SM_BODY_MODULE=<module>`` -> a second body. The module must define NUM_JOINTS, JOINT_NAMES, TRACKED_BODIES,
ANCHOR_BODY, ROOT_BODY, COM_BODY, FOOT_GEOM_REGEX, ACTION_SCALE, ROOT_HEIGHT_THRESHOLD, COM_RANGES,
get_robot_cfg() (mjlab EntityCfg) and load_model() (CPU MjModel used for FK and motion conversion).
Every dimension below follows from NJ exactly as the upstream literals follow from 29.
"""

from __future__ import annotations

import importlib
import os

BODY_MODULE = os.environ.get("SM_BODY_MODULE") or None

if BODY_MODULE is None:
    NAME = "reference29"
    NJ = 29
    TRACKED_BODIES: tuple[str, ...] = (
        "pelvis", "left_hip_roll_link", "left_knee_link", "left_ankle_roll_link", "right_hip_roll_link",
        "right_knee_link", "right_ankle_roll_link", "torso_link", "left_shoulder_roll_link", "left_elbow_link",
        "left_wrist_yaw_link", "right_shoulder_roll_link", "right_elbow_link", "right_wrist_yaw_link",
    )
    ANCHOR_BODY = "torso_link"
    ROOT_BODY = "pelvis"
    COM_BODY = "torso_link"
    FOOT_GEOM_REGEX = r"^(left|right)_foot[1-7]_collision$"
    ROOT_HEIGHT_THRESHOLD = 0.25
    COM_RANGES = {0: (-0.025, 0.025), 1: (-0.05, 0.05), 2: (-0.05, 0.05)}

    def get_robot_cfg():
        from mjlab.asset_zoo.robots import get_g1_robot_cfg

        return get_g1_robot_cfg()

    def action_scale():
        from mjlab.asset_zoo.robots import G1_ACTION_SCALE

        return G1_ACTION_SCALE

    def load_model():
        from supermimic.data.motion_convert import load_g1_model

        return load_g1_model()
else:
    _b = importlib.import_module(BODY_MODULE)
    NAME = getattr(_b, "BODY_NAME", BODY_MODULE)
    NJ = int(_b.NUM_JOINTS)
    TRACKED_BODIES = tuple(_b.TRACKED_BODIES)
    ANCHOR_BODY = _b.ANCHOR_BODY
    ROOT_BODY = _b.ROOT_BODY
    COM_BODY = _b.COM_BODY
    FOOT_GEOM_REGEX = _b.FOOT_GEOM_REGEX
    ROOT_HEIGHT_THRESHOLD = float(_b.ROOT_HEIGHT_THRESHOLD)
    COM_RANGES = dict(_b.COM_RANGES)
    get_robot_cfg = _b.get_robot_cfg
    load_model = _b.load_model

    def action_scale():
        return dict(_b.ACTION_SCALE)

NQ = 7 + NJ  # root pos 3 + root quat 4 + hinges
NV = 6 + NJ
STATE_DIM = NQ + NV  # 71 for NJ = 29
DELTA_DIM = 12 + 2 * NJ  # 70
OBS_FRAME = 3 * NJ + 6  # 93
GOAL_FRAME = 2 * NJ + 10  # 68
XI_DIM = 1 + NJ + 3  # 33
