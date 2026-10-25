"""Train entrypoint: Junior-(B) attention decoder vs matched MLP on a SuperMimic-style loop.

Modes
-----
``--mode smoke`` (default; runs on CPU, no simulator, no motion data)
    Builds the selected decoder, checks shapes/param counts, and runs a *toy* imagine/BPTT loop:
    a frozen random linear stand-in "world model" rolled out for ``smoke.horizon`` steps with the
    decoder in the loop, loss backpropagated through the whole horizon. This only proves that
    gradients flow through the decoder across an imagined horizon; it says nothing about tracking.

``--mode upstream`` (Colab GPU only)
    Integration seam to a public mjlab / MuJoCo Warp SuperMimic reproduction (see
    code/vendor/NOTES.md). The upstream trainer builds ``Policy(cfg.policy)`` inside
    ``supermimic.training.loop``; we rebind that name to a subclass whose ``decoder`` is ours, then
    call the upstream CLI with reduced-env tyro flags from the YAML. World model, motion encoder,
    critic, reward, action space and the imagine/BPTT loop are the upstream ones, unchanged.

Usage::

    python code/train_entry.py --policy attention              # CPU smoke
    python code/train_entry.py --policy mlp_matched
    python code/train_entry.py --mode upstream --policy attention --config configs/colab_smoke.yaml
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from dataclasses import asdict, fields
from pathlib import Path

import torch
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from attention_policy import (  # noqa: E402
    AttentionDecoder,
    AttentionDecoderCfg,
    count_params,
    make_upstream_policy_class,
    morphology_from_mjmodel,
    random_token_mask,
    synthetic_morphology,
)
from mlp_baseline import MLPDecoder, MLPDecoderCfg, build_matched_mlp  # noqa: E402

PROGRAM_ROOT = HERE.parent
POLICY_ARMS = ("attention", "mlp_matched", "mlp_upstream")


def load_config(path: str | Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def attention_cfg(cfg: dict, latent_dim: int = 32, history: int = 10, num_joints: int = 29) -> AttentionDecoderCfg:
    names = {f.name for f in fields(AttentionDecoderCfg)}
    over = {k: (tuple(v) if isinstance(v, list) else v) for k, v in cfg.get("attention", {}).items() if k in names}
    return AttentionDecoderCfg(latent_dim=latent_dim, history=history, num_joints=num_joints, **over)


def load_morphology(cfg: dict, num_joints: int) -> torch.Tensor:
    src = cfg.get("attention", {}).get("morphology", "synthetic")
    if src == "upstream_mjmodel":
        mod, fn = cfg["upstream"]["model_loader"].split(":")
        model = getattr(importlib.import_module(mod), fn)()
        m = morphology_from_mjmodel(model)
        assert m.shape[0] == num_joints, f"model has {m.shape[0]} hinge joints, policy expects {num_joints}"
        return m
    return synthetic_morphology()[:num_joints]


def build_decoder(arm: str, cfg: dict, latent_dim: int = 32, history: int = 10, num_joints: int = 29,
                  morphology: torch.Tensor | None = None) -> torch.nn.Module:
    """Factory shared by smoke, upstream train and eval. mlp_matched is sized to the attention arm."""
    acfg = attention_cfg(cfg, latent_dim, history, num_joints)
    if arm == "attention":
        return AttentionDecoder(acfg, morphology=morphology)
    mcfg = MLPDecoderCfg(latent_dim=latent_dim, history=history, num_joints=num_joints)
    if arm == "mlp_upstream":
        return MLPDecoder(mcfg)
    if arm == "mlp_matched":
        return build_matched_mlp(count_params(AttentionDecoder(acfg, morphology=morphology)), mcfg)
    raise ValueError(f"unknown policy arm {arm!r}; choose from {POLICY_ARMS}")


def decoder_sidecar(arm: str, cfg: dict, dec: torch.nn.Module) -> dict:
    out = {"policy": arm, "params": count_params(dec), "attention": cfg.get("attention", {})}
    if isinstance(dec, MLPDecoder):
        out["mlp_hidden"] = list(dec.cfg.hidden)
    if isinstance(dec, AttentionDecoder):
        out["attention_cfg"] = {k: list(v) if isinstance(v, tuple) else v for k, v in asdict(dec.cfg).items()}
    return out


# --------------------------------------------------------------------------------------------- smoke
def run_smoke(arm: str, cfg: dict, out_dir: Path) -> dict:
    s = cfg.get("smoke", {})
    torch.manual_seed(cfg.get("seed", 0))
    dev = torch.device(s.get("device", "cpu"))
    n, horizon, steps = s.get("batch", 64), s.get("horizon", 8), s.get("steps", 20)
    latent, hist, j = 32, 10, 29
    obs_dim = hist * (3 * j + 6)
    dec = build_decoder(arm, cfg, latent, hist, j).to(dev)
    opt = torch.optim.Adam(dec.parameters(), lr=3e-4)

    # Toy frozen "world model": next 93-d proprio frame = A @ frame + B @ action (stand-in only).
    g = torch.Generator().manual_seed(1)
    frame_dim = 3 * j + 6
    A = (torch.eye(frame_dim) * 0.95 + 0.01 * torch.randn(frame_dim, frame_dim, generator=g)).to(dev)
    B = (0.1 * torch.randn(frame_dim, j, generator=g)).to(dev)
    target = (0.3 * torch.randn(n, j, generator=g)).to(dev)
    mask_frac = cfg.get("b2", {}).get("train_mask_frac", 0.0)

    def to_hist(frames: list[torch.Tensor]) -> torch.Tensor:
        h = torch.stack(frames[-hist:], 1)  # (N, H, 93) -> term-major (N, 930)
        jp, jv, av, gr, ac = torch.split(h, (j, j, 3, 3, j), dim=-1)
        return torch.cat([x.reshape(n, -1) for x in (jp, jv, av, gr, ac)], dim=-1)

    losses, t0 = [], time.time()
    for _ in range(steps):
        z = torch.tanh(torch.randn(n, latent, device=dev))
        frames = [0.1 * torch.randn(n, frame_dim, device=dev) for _ in range(hist)]
        loss = 0.0
        for _t in range(horizon):  # imagine: gradients flow through every step (BPTT)
            mask = random_token_mask(n, j, mask_frac, device=dev) if mask_frac > 0 else None
            a = dec(z, to_hist(frames), token_mask=mask)
            nxt = frames[-1] @ A.T + a @ B.T
            nxt = torch.cat([nxt[:, : 3 * j + 6 - j], a], dim=-1)  # last term = previous action
            frames.append(nxt)
            loss = loss + ((nxt[:, :j] - target) ** 2).mean()
        loss = loss / horizon
        opt.zero_grad()
        loss.backward()
        gnorm = float(torch.nn.utils.clip_grad_norm_(dec.parameters(), 1.0))
        opt.step()
        losses.append(float(loss.detach()))
    res = {
        "mode": "smoke", "policy": arm, "params": count_params(dec), "obs_dim": obs_dim,
        "batch": n, "horizon": horizon, "steps": steps, "device": str(dev),
        "loss_first": losses[0], "loss_last": losses[-1], "last_grad_norm": gnorm,
        "finite": all(map(lambda x: x == x and abs(x) < 1e9, losses)),
        "wall_s": round(time.time() - t0, 3),
        "note": "toy linear stand-in WM; verifies BPTT plumbing only, not tracking quality",
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"smoke_{arm}.json").write_text(json.dumps(res, indent=2))
    return res


# ------------------------------------------------------------------------------------------ upstream
def tyro_argv(cfg: dict, arm: str) -> list[str]:
    up = cfg["upstream"]
    argv = ["--run-name", f"{cfg.get('run_name', 'b0')}_{arm}_s{cfg.get('seed', 0)}", "--seed", str(cfg.get("seed", 0)),
            "--data.npz-dir", up["npz_dir"]]
    if up.get("pass_clip_filter") and up.get("clips"):  # npz_dir already holds only the subset
        argv += ["--data.clips", *up["clips"]]
    for k, v in up.get("tyro_args", {}).items():
        if v is True:
            argv.append(k)
        elif v is False:
            argv.append(k.replace("--", "--no-", 1) if "." not in k else k.rsplit(".", 1)[0] + ".no-" + k.rsplit(".", 1)[1])
        else:
            argv += [k, str(v)]
    return argv


def install_upstream_policy(arm: str, cfg: dict, targets: tuple[str, ...]) -> dict:
    """Rebind ``Policy`` in the given upstream modules to a subclass with our decoder."""
    morphology = load_morphology(cfg, 29) if arm == "attention" else None
    info: dict = {}

    def factory(pcfg):
        dec = build_decoder(arm, cfg, latent_dim=pcfg.latent_dim, history=pcfg.history, num_joints=29, morphology=morphology)
        if hasattr(pcfg, "obs_term_scale") and hasattr(dec, "scale"):
            assert tuple(pcfg.obs_term_scale) == tuple(attention_cfg(cfg).obs_term_scale), "obs scale drift vs upstream"
        dec.auto_mask_frac = float(cfg.get("b2", {}).get("train_mask_frac", 0.0))
        info.update(decoder_sidecar(arm, cfg, dec), train_mask_frac=dec.auto_mask_frac)
        return dec

    cls = make_upstream_policy_class(factory)
    for t in targets:
        setattr(importlib.import_module(t), "Policy", cls)
    return info


def run_upstream(arm: str, cfg: dict) -> None:
    if not torch.cuda.is_available():
        sys.exit("[train_entry] --mode upstream requires a CUDA GPU (Colab T4/L4). Use --mode smoke on CPU.")
    info = install_upstream_policy(arm, cfg, ("supermimic.training.loop",))
    argv = tyro_argv(cfg, arm)
    print("[train_entry] upstream argv:", " ".join(argv))
    sys.argv = ["sm-train", *argv]
    run_dir = Path("logs") / argv[1]
    run_dir.mkdir(parents=True, exist_ok=True)
    from supermimic.scripts.train import main as upstream_main  # noqa: PLC0415

    try:
        upstream_main()
    finally:
        (run_dir / "junior_policy.json").write_text(json.dumps({**info, "argv": argv}, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("smoke", "upstream"), default="smoke")
    ap.add_argument("--policy", choices=POLICY_ARMS, default=None, help="overrides config `policy`")
    ap.add_argument("--config", default=str(PROGRAM_ROOT / "configs" / "colab_smoke.yaml"))
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out", default=str(PROGRAM_ROOT / "logs" / "smoke"))
    a = ap.parse_args()
    cfg = load_config(a.config)
    if a.seed is not None:
        cfg["seed"] = a.seed
    arm = a.policy or cfg.get("policy", "attention")
    if a.mode == "smoke":
        print(json.dumps(run_smoke(arm, cfg, Path(a.out)), indent=2))
    else:
        run_upstream(arm, cfg)


if __name__ == "__main__":
    main()
