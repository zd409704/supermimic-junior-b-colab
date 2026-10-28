#!/usr/bin/env python3
"""Headless B0 compare recorder: attention vs mlp_matched vs mlp_upstream.

Loads Junior-(B) arms the same way eval_entry --mode upstream does
(install_upstream_policy + junior_policy.json sidecar), rolls out
deterministic mask-0 clips, and writes labeled MP4s via OffscreenRenderer
(env render_mode=rgb_array).

Does not amend B0/B2 PLANs or reopen scoring.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "egl")

import numpy as np
import torch


def _label_frame(img: np.ndarray, text: str) -> np.ndarray:
    """Burn a short ASCII label into the top-left of an RGB uint8 frame (no PIL)."""
    out = img.copy()
    h, w = out.shape[:2]
    # simple bitmap font via filled rectangles for a bar + crude 5x7 glyphs is heavy;
    # instead draw a solid bar and use imageio text via packing ASCII as colored strip.
    bar_h = min(28, h // 8)
    out[:bar_h, :] = (out[:bar_h, :].astype(np.int16) * 2 // 5).astype(np.uint8)
    # draw characters with a tiny 5x7 font
    font = _TINY_FONT
    x, y = 6, 6
    scale = 2
    for ch in text[:40]:
        glyph = font.get(ch.upper(), font.get("?", None))
        if glyph is None:
            x += 6 * scale
            continue
        for r, row in enumerate(glyph):
            for c, bit in enumerate(row):
                if bit:
                    yy0 = y + r * scale
                    xx0 = x + c * scale
                    out[yy0 : yy0 + scale, xx0 : xx0 + scale] = (240, 240, 240)
        x += 6 * scale
        if x > w - 10:
            break
    return out


# Minimal 5x7 glyphs for A-Z 0-9 _-|/ ().
_TINY_FONT: dict[str, list[str]] = {}


def _build_font() -> None:
    raw = {
        "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
        "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
        "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
        "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
        "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
        "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
        "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
        "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
        "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
        "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
        "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
        "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
        "M": ["10001", "11011", "10101", "10001", "10001", "10001", "10001"],
        "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
        "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
        "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
        "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
        "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
        "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
        "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
        "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
        "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
        "W": ["10001", "10001", "10001", "10001", "10101", "11011", "10001"],
        "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
        "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
        "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
        "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
        "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
        "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
        "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
        "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
        "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
        "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
        "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
        "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
        "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
        "_": ["00000", "00000", "00000", "00000", "00000", "00000", "11111"],
        "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
        "|": ["00100", "00100", "00100", "00100", "00100", "00100", "00100"],
        "/": ["00001", "00010", "00100", "01000", "10000", "00000", "00000"],
        "(": ["00010", "00100", "01000", "01000", "01000", "00100", "00010"],
        ")": ["01000", "00100", "00010", "00010", "00010", "00100", "01000"],
        " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
        "?": ["01110", "10001", "00001", "00010", "00100", "00000", "00100"],
        ".": ["00000", "00000", "00000", "00000", "00000", "00100", "00100"],
        ":": ["00000", "00100", "00100", "00000", "00100", "00100", "00000"],
    }
    for k, rows in raw.items():
        _TINY_FONT[k] = rows


_build_font()


def write_mp4(path: Path, frames: list[np.ndarray], fps: float) -> None:
    import imageio.v2 as imageio

    path.parent.mkdir(parents=True, exist_ok=True)
    # imageio-ffmpeg backend
    with imageio.get_writer(
        str(path),
        fps=fps,
        codec="libx264",
        quality=8,
        pixelformat="yuv420p",
        macro_block_size=1,
    ) as w:
        for fr in frames:
            if fr.dtype != np.uint8:
                fr = np.clip(fr, 0, 255).astype(np.uint8)
            # yuv420p needs even dims
            h, ww = fr.shape[:2]
            if h % 2 or ww % 2:
                fr = fr[: h - (h % 2), : ww - (ww % 2)]
            w.append_data(fr)


def hstack_pad(frames_list: list[list[np.ndarray]], labels: list[str]) -> list[np.ndarray]:
    n = min(len(f) for f in frames_list)
    out = []
    for i in range(n):
        panels = []
        for fr, lab in zip(frames_list, labels):
            panels.append(_label_frame(fr[i], lab))
        # match heights
        h = min(p.shape[0] for p in panels)
        w = min(p.shape[1] for p in panels)
        panels = [p[:h, :w] for p in panels]
        out.append(np.concatenate(panels, axis=1))
    return out


def load_junior_policy(ckpt: Path, arm: str, cfg: dict, device: str):
    """Match eval_entry.run_upstream: rebind Policy then load_policy_from_checkpoint."""
    # junior code must be on sys.path
    sidecar = ckpt.parent / "junior_policy.json"
    meta = json.loads(sidecar.read_text()) if sidecar.exists() else {}
    arm = arm or meta.get("policy")
    if meta.get("attention"):
        cfg = {**cfg, "attention": meta["attention"]}
    from train_entry import POLICY_ARMS, install_upstream_policy

    assert arm in POLICY_ARMS, f"unknown arm {arm}"
    info = install_upstream_policy(arm, cfg, ("supermimic.eval.benchmark",))
    want = (meta.get("descriptor") or {}).get("sha256")
    got = (info.get("descriptor") or {}).get("sha256")
    if arm == "attention" and want and want != got:
        raise RuntimeError(f"descriptor sha256 mismatch: sidecar {want} vs rebuilt {got}")
    from supermimic.eval.benchmark import load_policy_from_checkpoint

    policy, pcfg = load_policy_from_checkpoint(ckpt, device)
    policy.decoder.auto_mask_frac = 0.0
    return policy, pcfg, info


def make_render_env(npz_files: list[str], pcfg: dict, device: str, seed: int = 0):
    from mjlab.envs.manager_based_rl_env import ManagerBasedRlEnv
    from supermimic.envs import SuperMimicEnvCfgArgs, make_env_cfg

    args = SuperMimicEnvCfgArgs(
        npz_files=npz_files,
        num_envs=1,
        future_frames=pcfg["env"]["future_frames"],
        episode_length_s=1.0e5,
        action_noise_std=0.0,
        obs_noise=False,
        reset_noise=False,
        domain_randomization=False,
        sampling_mode="start",
        record_transitions=False,
        seed=seed,
        anchor_obs=pcfg["env"].get("anchor_obs", False),
        debug_vis=False,
    )
    cfg = make_env_cfg(args)
    # bump render resolution a bit for readable side-by-side
    cfg.viewer.height = 480
    cfg.viewer.width = 640
    return ManagerBasedRlEnv(cfg, device=device, render_mode="rgb_array")


@torch.no_grad()
def rollout_frames(
    policy,
    env,
    max_steps: int,
    stop_on_term: bool = True,
) -> tuple[list[np.ndarray], dict]:
    cmd = env.command_manager.get_term("motion")
    lib = cmd.library
    # force clip 0 from start
    cmd.forced_frame[:] = lib.clip_start[0]
    obs, _ = env.reset()
    # after reset, keep forcing start for next auto-reset (we stop on done)
    cmd.forced_frame[:] = lib.clip_start[0]
    frames: list[np.ndarray] = []
    ret = 0.0
    steps = 0
    failed = False
    fail_step = -1
    t0 = time.time()
    for t in range(max_steps):
        act = policy(obs["policy"], obs["goal"])
        obs, rew, term, tout, _ = env.step(act)
        ret += float(rew[0])
        steps += 1
        rgb = env.render()
        if rgb is not None:
            frames.append(np.asarray(rgb))
        done = bool(term[0] or tout[0])
        if done:
            failed = bool(term[0])
            fail_step = steps
            if stop_on_term:
                break
    meta = {
        "steps": steps,
        "norm_return_proxy": ret,
        "failed": failed,
        "fail_step": fail_step,
        "n_frames": len(frames),
        "wall_s": round(time.time() - t0, 3),
        "clip_frames": int(lib.clips[0].length),
        "clip_name": lib.clips[0].name,
        "step_dt": float(env.step_dt),
    }
    return frames, meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--junior-code", type=Path, default=Path("/content/junior/code"))
    ap.add_argument("--config", type=Path, default=Path("/content/junior/configs/b0_microbench.yaml"))
    ap.add_argument("--logs-root", type=Path, default=Path("/content/SuperMimic-Reproduced/logs"))
    ap.add_argument("--npz-dir", type=Path, default=Path("/content/SuperMimic-Reproduced/data/npz/lafan1_smoke"))
    ap.add_argument("--out-dir", type=Path, default=Path("/content/b0-compare-videos"))
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--max-steps", type=int, default=3600, help="~72s at 50 Hz; cap GPU time")
    ap.add_argument("--arms", nargs="+", default=["attention", "mlp_matched", "mlp_upstream"])
    ap.add_argument("--clips", nargs="+", default=["walk1_subject1", "dance1_subject1"])
    ap.add_argument("--seed-tag", default="s0")
    a = ap.parse_args()

    sys.path.insert(0, str(a.junior_code.resolve()))
    from train_entry import load_config

    cfg = load_config(a.config)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"arms": {}, "clips": list(a.clips), "max_steps": a.max_steps, "device": a.device}

    # per arm, per clip frames for side-by-side on walk1
    walk_frames: dict[str, list[np.ndarray]] = {}
    fps_used = 50.0

    for arm in a.arms:
        run = a.logs_root / f"b0_{arm}_{a.seed_tag}"
        ckpt = run / "ckpt_0001600.pt"
        if not ckpt.exists():
            raise FileNotFoundError(f"missing ckpt: {ckpt}")
        print(f"[render] loading {arm} from {ckpt}", flush=True)
        policy, pcfg, info = load_junior_policy(ckpt, arm, cfg, a.device)
        summary["arms"][arm] = {
            "ckpt": str(ckpt),
            "params": info.get("params"),
            "policy": info.get("policy"),
            "clips": {},
        }
        for clip in a.clips:
            npz = a.npz_dir / f"{clip}.npz"
            if not npz.exists():
                raise FileNotFoundError(f"missing motion: {npz}")
            print(f"[render] {arm} / {clip} ...", flush=True)
            env = make_render_env([str(npz)], pcfg, a.device, seed=0)
            try:
                frames, meta = rollout_frames(policy, env, a.max_steps)
            finally:
                env.close()
            fps_used = 1.0 / float(meta["step_dt"])
            labeled = [_label_frame(fr, f"{arm} | {clip}") for fr in frames]
            out_mp4 = a.out_dir / f"{arm}_{a.seed_tag}_{clip}.mp4"
            write_mp4(out_mp4, labeled, fps=min(fps_used, 50.0))
            meta["mp4"] = str(out_mp4)
            meta["mp4_bytes"] = out_mp4.stat().st_size
            summary["arms"][arm]["clips"][clip] = meta
            print(f"[render] wrote {out_mp4} frames={meta['n_frames']} failed={meta['failed']} wall={meta['wall_s']}s", flush=True)
            if clip == "walk1_subject1":
                walk_frames[arm] = frames
            # free CUDA fragmentation a bit
            del frames, labeled
            torch.cuda.empty_cache()
        del policy
        torch.cuda.empty_cache()

    # side-by-side for walk1
    if len(walk_frames) >= 2 and "walk1_subject1" in a.clips:
        order = [x for x in a.arms if x in walk_frames]
        labels = [x for x in order]
        print(f"[render] side-by-side walk1: {labels}", flush=True)
        side = hstack_pad([walk_frames[x] for x in order], labels)
        side_path = a.out_dir / f"compare_{a.seed_tag}_walk1_subject1_sidebyside.mp4"
        write_mp4(side_path, side, fps=min(fps_used, 50.0))
        summary["side_by_side"] = {
            "path": str(side_path),
            "arms": order,
            "n_frames": len(side),
            "bytes": side_path.stat().st_size,
        }
        print(f"[render] wrote {side_path} frames={len(side)}", flush=True)

    summary_path = a.out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("[render] DONE", flush=True)


if __name__ == "__main__":
    main()
