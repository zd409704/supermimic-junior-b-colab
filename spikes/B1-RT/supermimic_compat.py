"""Import the pinned upstream motion routines (resample / FK) without vendoring them.

GPU host: ``supermimic`` is installed in the upstream clone's venv. Research box: fall back to the read-only clone
``packets/P4/upstream-ro/SuperMimic-Reproduced/src`` (pin d9be385b…); run with ``-B`` so no bytecode is written there.
"""
import sys
from pathlib import Path

try:
    from supermimic.data.motion_convert import forward_kinematics, resample_motion  # noqa: F401
except ImportError:
    _src = Path(__file__).resolve().parents[2] / "packets/P4/upstream-ro/SuperMimic-Reproduced/src"
    sys.path.insert(0, str(_src))
    from supermimic.data.motion_convert import forward_kinematics, resample_motion  # noqa: F401,E402
