"""``SM_BODY_MODULE`` adapter: the home humanoid as body 2 of the B1 upstream patch (packets/P6/upstream-b1.patch).

All values come from the sealed P6a module ``spikes/B1-RT/home_humanoid.py`` (AS-1..AS-5); nothing is redefined here.
"""
from __future__ import annotations

import sys
from pathlib import Path

_RT = Path(__file__).resolve().parents[3] / "spikes" / "B1-RT"
if str(_RT) not in sys.path:
    sys.path.insert(0, str(_RT))
import home_humanoid as H  # noqa: E402

BODY_NAME = "home_humanoid"
NUM_JOINTS = H.NUM_JOINTS
JOINT_NAMES = H.JOINT_NAMES
TRACKED_BODIES = H.TRACKED_BODIES
ANCHOR_BODY = H.ANCHOR_BODY
ROOT_BODY = H.ROOT_BODY
COM_BODY = H.COM_BODY
FOOT_GEOM_REGEX = H.FOOT_GEOM_REGEX
ACTION_SCALE = H.HOME_HUMANOID_ACTION_SCALE
_RATIO = H.height_ratio()
ROOT_HEIGHT_THRESHOLD = H.termination_height_threshold()  # AS-5: 0.25 m x height ratio
COM_RANGES = {0: (-0.025 * _RATIO, 0.025 * _RATIO), 1: (-0.05 * _RATIO, 0.05 * _RATIO), 2: (-0.05 * _RATIO, 0.05 * _RATIO)}
get_robot_cfg = H.get_home_humanoid_robot_cfg


def load_model():
    """CPU MjModel for FK / motion conversion: owner MJCF + overlay, no floor, no actuators (kinematics only)."""
    return H.load_overlaid_model(with_floor=False, add_actuators=False, add_keyframe=False)
