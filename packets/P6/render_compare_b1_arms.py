#!/usr/bin/env python3
"""Headless B1 arms compare recorder (visual artifact only): H-A-scratch / H-A-xfer / H-M-xfer, seed 0, it 1600.

Adapted from packets/P4/render_compare_b0.py. The policy is loaded exactly as the sealed B1 eval path does
(packets/P6/b1/p6_entry.py cmd_eval: install(init="scratch", probe=False) + junior_policy.json sidecar, then
supermimic.eval.benchmark.load_policy_from_checkpoint), on the home humanoid (SM_BODY_MODULE=sm_body_home) and the
patched B1 upstream tree. Deterministic mask-0 rollout of one clip from its start, rendered with the env's
OffscreenRenderer (render_mode="rgb_array") and streamed to an ffmpeg pipe (no frame lists held in RAM).

Outputs per arm and clip a labelled MP4, then one side-by-side MP4 per clip built by ffmpeg hstack; an arm whose
rollout ended earlier is held on its last frame (tpad clone) so the panels stay in sync.

Does not amend spikes/B1/PLAN.md, does not reopen B1 scoring or the M1 post-hoc re-score, and computes no score.
The per-clip step counts in summary.json describe the video length only.

Ckpt locations (sealed driver meta of deposit f95155af..., meta/harness_stop_<aid>.txt; *.pt were excluded from the
bundle by PLAN §8): <upstream>/logs/<run>/ckpt_0001600.pt with <run> = b1<arm without dashes>_<policy>_s<seed>.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "egl")
os.environ["SM_BODY_MODULE"] = "sm_body_home"  # p6_entry._check_body requires it before supermimic is imported

import numpy as np

# arm -> (run tag, policy); run dir = b1<tag>_<policy>_s<seed> (packets/P6/b1arms_driver.sh run_arm)
ARMS: dict[str, tuple[str, str]] = {
    "H-A-scratch": ("b1HAscratch", "attention"),
    "H-A-xfer": ("b1HAxfer", "attention"),
    "H-M-xfer": ("b1HMxfer", "mlp_matched"),
    "H-M-scratch": ("b1HMscratch", "mlp_matched"),
}
# ckpt_0001600.pt byte sizes at the harness stop (sealed meta/harness_stop_<aid>_a1.txt, ckpt_stable=true, seed 0)
EXPECT_BYTES_S0: dict[str, int] = {
    "H-A-scratch": 159445702,
    "H-A-xfer": 159445702,
    "H-M-xfer": 158486223,
    "H-M-scratch": 159357327,
}
PANEL_W, PANEL_H = 640, 480


# ------------------------------------------------------------------ labels (tiny 5x7 bitmap font, as the B0 recorder)
_FONT: dict[str, list[str]] = {
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


def label_frame(img: np.ndarray, lines: list[str], scale: int = 2) -> np.ndarray:
    """Darken a top bar and burn up to two ASCII lines into an RGB uint8 frame (no PIL)."""
    out = np.ascontiguousarray(img[..., :3], dtype=np.uint8).copy()
    h, w = out.shape[:2]
    line_h = 9 * scale
    bar_h = min(h // 4, 6 + line_h * len(lines))
    out[:bar_h] = (out[:bar_h].astype(np.uint16) * 2 // 5).astype(np.uint8)
    for li, text in enumerate(lines):
        x, y = 6, 4 + li * line_h
        for ch in text.upper():
            if x > w - 6 * scale:
                break
            glyph = _FONT.get(ch, _FONT["?"])
            for r, row in enumerate(glyph):
                for c, bit in enumerate(row):
                    if bit == "1":
                        out[y + r * scale : y + (r + 1) * scale, x + c * scale : x + (c + 1) * scale] = 240
            x += 6 * scale
    return out


# ------------------------------------------------------------------ ffmpeg
def ffmpeg_exe(explicit: str | None) -> str:
    if explicit:
        return explicit
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg  # noqa: PLC0415  (installed --no-deps into a side dir by run.sh if no system ffmpeg)

    return imageio_ffmpeg.get_ffmpeg_exe()


class Mp4Writer:
    """Raw RGB frames on stdin -> H.264 yuv420p MP4. Frames are cropped/padded to even width and height."""

    def __init__(self, ff: str, path: Path, w: int, h: int, fps: float):
        self.w, self.h = w - w % 2, h - h % 2
        self.path = path
        self.n = 0
        path.parent.mkdir(parents=True, exist_ok=True)
        self.p = subprocess.Popen(
            [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{self.w}x{self.h}",
             "-r", f"{fps:g}", "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)],
            stdin=subprocess.PIPE,
        )

    def append(self, fr: np.ndarray) -> None:
        fr = np.ascontiguousarray(fr[: self.h, : self.w, :3], dtype=np.uint8)
        if fr.shape[:2] != (self.h, self.w):
            fr = np.pad(fr, ((0, self.h - fr.shape[0]), (0, self.w - fr.shape[1]), (0, 0)))
        self.p.stdin.write(fr.tobytes())
        self.n += 1

    def close(self) -> None:
        self.p.stdin.close()
        if self.p.wait() != 0:
            raise RuntimeError(f"ffmpeg failed for {self.path}")


def side_by_side(ff: str, inputs: list[Path], n_frames: list[int], fps: float, out: Path) -> None:
    """hstack the per-arm MP4s; shorter inputs hold their last (labelled) frame until the longest one ends."""
    n_max = max(n_frames)
    parts, labels = [], []
    for i, n in enumerate(n_frames):
        pad = (n_max - n) / fps
        parts.append(f"[{i}:v]tpad=stop_mode=clone:stop_duration={pad:.4f},setpts=PTS-STARTPTS[v{i}]")
        labels.append(f"[v{i}]")
    graph = ";".join(parts) + ";" + "".join(labels) + f"hstack=inputs={len(inputs)}[out]"
    cmd = [ff, "-y", "-loglevel", "error"]
    for p in inputs:
        cmd += ["-i", str(p)]
    cmd += ["-filter_complex", graph, "-map", "[out]", "-frames:v", str(n_max), "-r", f"{fps:g}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(out)]
    subprocess.run(cmd, check=True)


# ------------------------------------------------------------------ ckpts
def run_dir(upstream: Path, arm: str, seed: int) -> Path:
    tag, pol = ARMS[arm]
    return upstream / "logs" / f"{tag}_{pol}_s{seed}"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def check_ckpt(upstream: Path, arm: str, seed: int, it: str) -> dict:
    """Presence + identity of one B1 ckpt. Identity = sealed harness-stop byte size (s0) and sidecar policy."""
    rd = run_dir(upstream, arm, seed)
    ck = rd / f"ckpt_{it}.pt"
    side = rd / "junior_policy.json"
    rec = {"arm": arm, "ckpt": str(ck), "sidecar": str(side), "ok": False}
    if not ck.is_file():
        rec["reason"] = "ckpt missing"
        return rec
    if not side.is_file():
        rec["reason"] = "junior_policy.json missing"
        return rec
    rec["bytes"] = ck.stat().st_size
    want = EXPECT_BYTES_S0.get(arm) if (seed == 0 and it == "0001600") else None
    rec["expect_bytes"] = want
    if want is not None and rec["bytes"] != want:
        rec["reason"] = f"size {rec['bytes']} != sealed harness-stop size {want}"
        return rec
    meta = json.loads(side.read_text())
    if meta.get("policy") != ARMS[arm][1]:
        rec["reason"] = f"sidecar policy {meta.get('policy')} != {ARMS[arm][1]}"
        return rec
    rec["sidecar_init"] = meta.get("init")
    rec["sha256"] = sha256_file(ck)
    rec["ok"] = True
    return rec


# ------------------------------------------------------------------ policy / env (B1 eval path)
def setup_paths(junior: Path) -> None:
    for p in (junior / "code", junior / "packets" / "P6" / "b1", junior / "spikes" / "B1-RT"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


def load_b1_policy(ckpt: Path, cfg: dict, device: str):
    """As p6_entry.cmd_eval: rebind Policy in supermimic.eval.benchmark, then load_policy_from_checkpoint."""
    import p6_entry as PE  # noqa: PLC0415

    PE._check_body()
    meta = json.loads((ckpt.parent / "junior_policy.json").read_text())
    arm = meta["policy"]
    if meta.get("attention"):
        cfg = {**cfg, "attention": meta["attention"]}
    import supermimic.eval.benchmark as bench  # noqa: PLC0415

    info = PE.install(arm, cfg, ("supermimic.eval.benchmark",), init="scratch", probe=False,
                      mlp_hidden=meta.get("mlp_hidden") if arm == "mlp_matched" else None)
    want = (meta.get("descriptor") or {}).get("sha256")
    got = (info.get("descriptor") or {}).get("sha256")
    if arm == "attention" and want and want != got:
        raise RuntimeError(f"descriptor sha256 mismatch: sidecar {want} vs rebuilt {got}")
    policy, pcfg = bench.load_policy_from_checkpoint(ckpt, device)
    policy.decoder.auto_mask_frac = 0.0
    return policy, pcfg, info, meta


def make_render_env(npz: Path, pcfg: dict, device: str):
    from mjlab.envs.manager_based_rl_env import ManagerBasedRlEnv  # noqa: PLC0415
    from supermimic.envs import SuperMimicEnvCfgArgs, make_env_cfg  # noqa: PLC0415

    args = SuperMimicEnvCfgArgs(
        npz_files=[str(npz)], num_envs=1, future_frames=pcfg["env"]["future_frames"], episode_length_s=1.0e5,
        action_noise_std=0.0, obs_noise=False, reset_noise=False, domain_randomization=False, sampling_mode="start",
        record_transitions=False, seed=0, anchor_obs=pcfg["env"].get("anchor_obs", False), debug_vis=False,
    )
    cfg = make_env_cfg(args)
    cfg.viewer.height, cfg.viewer.width = PANEL_H, PANEL_W
    return ManagerBasedRlEnv(cfg, device=device, render_mode="rgb_array")


def rollout_to_mp4(policy, env, writer_factory, head: str, clip: str, max_steps: int) -> dict:
    import torch  # noqa: PLC0415

    cmd = env.command_manager.get_term("motion")
    lib = cmd.library
    cmd.forced_frame[:] = lib.clip_start[0]
    obs, _ = env.reset()
    cmd.forced_frame[:] = lib.clip_start[0]
    dt = float(env.step_dt)
    fps = min(1.0 / dt, 50.0)
    w = None
    steps, end = 0, "cap"
    t0 = time.time()
    with torch.no_grad():
        for _ in range(max_steps):
            act = policy(obs["policy"], obs["goal"])
            obs, _rew, term, tout, _ = env.step(act)
            steps += 1
            done = bool(term[0] or tout[0])
            if done:
                end = "fell" if bool(term[0]) else "clip_end"
            rgb = env.render()
            if rgb is None:
                continue
            rgb = np.asarray(rgb)
            if w is None:
                w = writer_factory(rgb.shape[1], rgb.shape[0], fps)
            tag = {"cap": f"T {steps * dt:5.1f}S", "fell": f"FELL AT {steps * dt:.1f}S",
                   "clip_end": f"CLIP END {steps * dt:.1f}S"}[end if done else "cap"]
            w.append(label_frame(rgb, [head, f"{clip} | {tag}"]))
            if done:
                break
    if w is None:
        raise RuntimeError("env.render() returned no frames")
    w.close()
    if steps >= max_steps and end == "cap":
        end = "max_steps_cap"
    return {"steps": steps, "end": end, "n_frames": w.n, "fps": fps, "step_dt": dt,
            "clip_frames": int(lib.clips[0].length), "clip_name": lib.clips[0].name,
            "wall_s": round(time.time() - t0, 3)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--junior", type=Path, required=True, help="tree unpacked from the sealed B1ARMS tarball")
    ap.add_argument("--upstream", type=Path, default=Path("/content/SuperMimic-Reproduced-b1"))
    ap.add_argument("--config", type=Path, default=None, help="default <junior>/packets/P6/configs/b1_home.yaml")
    ap.add_argument("--npz-dir", type=Path, default=None, help="default <upstream>/data/npz/b1_home")
    ap.add_argument("--out-dir", type=Path, default=Path("/content/b1-arms-compare-videos"))
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--max-steps", type=int, default=3600, help="~72 s at 50 Hz; caps GPU time")
    ap.add_argument("--arms", nargs="+", default=["H-A-scratch", "H-A-xfer", "H-M-xfer"])
    ap.add_argument("--optional-arms", nargs="*", default=["H-M-scratch"], help="rendered only if the ckpt checks pass")
    ap.add_argument("--clips", nargs="+", default=["walk1_subject1", "dance1_subject1"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--it", default="0001600")
    ap.add_argument("--ffmpeg", default=None)
    ap.add_argument("--check-only", action="store_true", help="ckpt/npz preflight only; exit 4 if a required item fails")
    a = ap.parse_args()

    for arm in [*a.arms, *a.optional_arms]:
        if arm not in ARMS:
            ap.error(f"unknown arm {arm}")
    npz_dir = a.npz_dir or a.upstream / "data" / "npz" / "b1_home"
    a.out_dir.mkdir(parents=True, exist_ok=True)

    # ---- preflight (no GPU)
    pre = {"required": {}, "optional": {}, "npz": {}}
    ok = True
    for arm in a.arms:
        r = check_ckpt(a.upstream, arm, a.seed, a.it)
        pre["required"][arm] = r
        print(f"CKPT_{'OK' if r['ok'] else 'FAIL'} arm={arm} path={r['ckpt']} bytes={r.get('bytes')} "
              f"sha256={r.get('sha256', '-')} {r.get('reason', '')}", flush=True)
        ok &= r["ok"]
    for arm in a.optional_arms:
        r = check_ckpt(a.upstream, arm, a.seed, a.it)
        pre["optional"][arm] = r
        print(f"CKPT_{'OK' if r['ok'] else 'SKIP'} arm={arm} (optional) path={r['ckpt']} {r.get('reason', '')}",
              flush=True)
    for clip in a.clips:
        p = npz_dir / f"{clip}.npz"
        pre["npz"][clip] = {"path": str(p), "ok": p.is_file(), "sha256": sha256_file(p) if p.is_file() else None}
        print(f"NPZ_{'OK' if p.is_file() else 'FAIL'} clip={clip} path={p}", flush=True)
        ok &= p.is_file()
    (a.out_dir / "preflight.json").write_text(json.dumps(pre, indent=2))
    if not ok:
        print("PREFLIGHT_FAIL (no rendering; no retrain)", flush=True)
        sys.exit(4)
    print("PREFLIGHT_OK", flush=True)
    if a.check_only:
        return

    # ---- render
    import torch  # noqa: PLC0415

    setup_paths(a.junior)
    import train_entry as TE  # noqa: PLC0415

    cfg = TE.load_config(a.config or a.junior / "packets" / "P6" / "configs" / "b1_home.yaml")
    ff = ffmpeg_exe(a.ffmpeg)
    arms = [*a.arms, *[x for x in a.optional_arms if pre["optional"][x]["ok"] and x not in a.arms]]
    summary = {"note": "visual artifact only; not a score; does not reopen B1 / M1",
               "arms": {}, "clips": list(a.clips), "seed": a.seed, "it": a.it, "max_steps": a.max_steps,
               "device": a.device, "ffmpeg": ff, "preflight": pre, "side_by_side": {}}
    per_clip: dict[str, list[tuple[str, Path, int, float]]] = {c: [] for c in a.clips}

    for arm in arms:
        ck = run_dir(a.upstream, arm, a.seed) / f"ckpt_{a.it}.pt"
        print(f"[render] loading {arm} from {ck}", flush=True)
        policy, pcfg, info, meta = load_b1_policy(ck, cfg, a.device)
        summary["arms"][arm] = {"ckpt": str(ck), "policy": meta.get("policy"), "init": meta.get("init"),
                                "params_total": info.get("params_total"), "clips": {}}
        for clip in a.clips:
            out_mp4 = a.out_dir / f"{arm}_s{a.seed}_it{a.it}_{clip}.mp4"
            print(f"[render] {arm} / {clip} ...", flush=True)
            env = make_render_env(npz_dir / f"{clip}.npz", pcfg, a.device)
            try:
                m = rollout_to_mp4(policy, env, lambda w, h, fps, p=out_mp4: Mp4Writer(ff, p, w, h, fps),
                                   f"{arm} S{a.seed} IT{int(a.it)}", clip, a.max_steps)
            finally:
                env.close()
            m["mp4"] = str(out_mp4)
            m["mp4_bytes"] = out_mp4.stat().st_size
            summary["arms"][arm]["clips"][clip] = m
            per_clip[clip].append((arm, out_mp4, m["n_frames"], m["fps"]))
            print(f"[render] wrote {out_mp4} frames={m['n_frames']} end={m['end']} wall={m['wall_s']}s", flush=True)
            torch.cuda.empty_cache()
        del policy
        torch.cuda.empty_cache()

    for clip, rows in per_clip.items():
        if len(rows) < 2:
            continue
        side = a.out_dir / f"compare_s{a.seed}_it{a.it}_{clip}_sidebyside.mp4"
        try:
            side_by_side(ff, [r[1] for r in rows], [r[2] for r in rows], rows[0][3], side)
            summary["side_by_side"][clip] = {"path": str(side), "arms": [r[0] for r in rows],
                                             "n_frames": max(r[2] for r in rows), "bytes": side.stat().st_size}
            print(f"[render] wrote {side} arms={[r[0] for r in rows]}", flush=True)
        except subprocess.CalledProcessError as e:  # per-arm MP4s still stand
            summary["side_by_side"][clip] = {"error": str(e)}
            print(f"[render] side-by-side {clip} FAILED: {e} (per-arm MP4s kept)", flush=True)

    (a.out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps({k: v for k, v in summary.items() if k != "preflight"}, indent=2, default=str))
    print("[render] DONE", flush=True)


if __name__ == "__main__":
    main()
