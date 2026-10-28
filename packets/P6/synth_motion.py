"""Synthetic (non-licensed) reference-layout motion for CPU smoke tests only: a slow in-place sway/step pattern.

Produces (N, 36) arrays in the upstream CSV layout and converts them through RT-a to home-humanoid npz files.
Never used for any scored run.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spikes" / "B1-RT"))
import retarget_rta as R  # noqa: E402


def synth_raw(seconds: float = 4.0, seed: int = 0, fps: float = 30.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * fps)) / fps
    raw = np.zeros((t.size, 36))
    w = 2 * np.pi * (0.5 + 0.2 * rng.random())
    raw[:, 0] = 0.15 * t
    raw[:, 2] = 0.78
    raw[:, 6] = 1.0  # xyzw identity
    qi = {n: i for i, n in enumerate(R.REF_JOINT_NAMES)}
    for k, s in enumerate(("left", "right")):
        ph = np.pi * k
        raw[:, 7 + qi[f"{s}_hip_pitch_joint"]] = -0.3 + 0.15 * np.sin(w * t + ph)
        raw[:, 7 + qi[f"{s}_knee_joint"]] = 0.6 + 0.2 * np.maximum(0, np.sin(w * t + ph))
        raw[:, 7 + qi[f"{s}_ankle_pitch_joint"]] = -0.3
        raw[:, 7 + qi[f"{s}_elbow_joint"]] = 1.2 + 0.2 * np.sin(w * t + ph + np.pi)
        raw[:, 7 + qi[f"{s}_shoulder_roll_joint"]] = 0.2 if s == "left" else -0.2
    return raw


def write_synth_npz(out_dir: Path, n: int = 2) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ctx = R.make_ctx()
    paths = []
    for i in range(n):
        rt = R.retarget_raw(synth_raw(seed=i), ctx)
        p = out_dir / f"synth{i}.npz"
        R.write_npz(p, R.to_motion(rt["raw"]), ctx, f"synthetic{i}")
        paths.append(p)
    return paths


if __name__ == "__main__":
    print(write_synth_npz(Path(sys.argv[1])))
