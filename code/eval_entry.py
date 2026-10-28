"""Eval entrypoint: B2 permutation / token-mask checks and the upstream benchmark seam.

Modes
-----
``--mode smoke`` (CPU; random inputs, untrained weights)
    B2-perm: permute joint order in obs history + morphology, un-permute actions, report max |da|.
      The attention arm (id_mode=morph) is equivariant by construction, so this is a correctness
      check (expect ~1e-6), not an empirical finding. MLP / id_mode=index arms are expected to break.
    B2-mask: action change when 10-20% of non-root joint tokens are dropped (sanity: finite, nonzero).

``--mode upstream`` (Colab GPU; trained checkpoint + motion npz)
    Rebinds ``Policy`` in ``supermimic.eval.benchmark`` using the run's ``junior_policy.json`` sidecar,
    then runs the upstream whole-clip benchmark (normalised return, failures) once unmasked and once
    per ``b2.mask_fracs`` via the decoder's ``auto_mask_frac`` hook. Writes one JSON per condition.

Usage::

    python code/eval_entry.py                                   # CPU smoke, all arms
    python code/eval_entry.py --mode upstream --ckpt logs/<run>/ckpt_latest.pt   # Colab
"""

from __future__ import annotations

import argparse
import json
import runpy
import sys
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from attention_policy import permute_obs_history, random_token_mask  # noqa: E402
from train_entry import POLICY_ARMS, PROGRAM_ROOT, build_decoder, install_upstream_policy, load_config  # noqa: E402


@torch.no_grad()
def b2_smoke(arm: str, cfg: dict, n: int = 32, seed: int = 0) -> dict:
    torch.manual_seed(seed)
    j, h, latent = 29, 10, 32
    dec = build_decoder(arm, cfg, latent, h, j).eval()
    z = torch.tanh(torch.randn(n, latent))
    obs = torch.randn(n, h * (3 * j + 6))
    base = dec(z, obs)
    perm_err = []
    morph = getattr(dec, "morphology", None)
    for t in range(cfg.get("b2", {}).get("perm_trials", 8)):
        perm = torch.randperm(j, generator=torch.Generator().manual_seed(100 + t))
        kw = {"morphology": morph[perm]} if morph is not None else {}
        out = dec(z, permute_obs_history(obs, perm, j, h), **kw)
        unperm = torch.empty_like(out)
        unperm[:, perm] = out
        perm_err.append(float((unperm - base).abs().max()))
    mask_delta = {}
    for frac in cfg.get("b2", {}).get("mask_fracs", [0.1, 0.2]):
        m = random_token_mask(n, j, frac, generator=torch.Generator().manual_seed(7))
        out = dec(z, obs, token_mask=m)
        mask_delta[str(frac)] = {"mean_abs_da": float((out - base).abs().mean()), "finite": bool(torch.isfinite(out).all())}
    scale = float(base.abs().mean())
    return {"policy": arm, "action_mean_abs": scale, "perm_max_abs_err": max(perm_err),
            "perm_rel_err": max(perm_err) / max(scale, 1e-12), "mask": mask_delta}


def run_upstream(ckpt: Path, cfg: dict, arm: str | None) -> None:
    if not torch.cuda.is_available():
        sys.exit("[eval_entry] --mode upstream requires a CUDA GPU (Colab T4/L4).")
    sidecar = ckpt.parent / "junior_policy.json"
    meta = json.loads(sidecar.read_text()) if sidecar.exists() else {}
    arm = arm or meta.get("policy")
    assert arm in POLICY_ARMS, f"policy arm unknown (no sidecar at {sidecar}); pass --policy"
    if meta.get("attention"):
        cfg = {**cfg, "attention": meta["attention"]}
    import supermimic.eval.benchmark as bench  # noqa: PLC0415

    info = install_upstream_policy(arm, cfg, ("supermimic.eval.benchmark",))
    want = (meta.get("descriptor") or {}).get("sha256")
    got = (info.get("descriptor") or {}).get("sha256")
    # only the attention arm consumes the descriptor; MLP arms record it but are not gated by it
    if arm == "attention" and want and want != got:  # descriptor rebuilt from the upstream loaders must equal the trained one
        raise RuntimeError(f"[eval_entry] descriptor sha256 mismatch: sidecar {want} vs rebuilt {got}")
    orig_load = bench.load_policy_from_checkpoint
    up, ev = cfg["upstream"], cfg.get("eval", {})
    out_dir = Path(ev.get("out_dir", "logs/eval"))
    out_dir.mkdir(parents=True, exist_ok=True)
    script = Path(up["repo_dir"]) / "scripts" / "eval_benchmark.py"
    for frac in [0.0, *cfg.get("b2", {}).get("mask_fracs", [])]:
        def load(path, device, _f=frac):
            policy, pcfg = orig_load(path, device)
            policy.decoder.auto_mask_frac = _f
            return policy, pcfg

        bench.load_policy_from_checkpoint = load
        out = out_dir / f"{ckpt.parent.name}_{arm}_mask{frac:.2f}.json"
        sys.argv = ["eval_benchmark.py", "--ckpt", str(ckpt), "--npz-dir", up["npz_dir"],
                    "--num-envs", str(ev.get("num_envs", 64)), "--out", str(out)]
        if up.get("pass_clip_filter") and up.get("clips"):
            sys.argv += ["--clips", *up["clips"]]
        print("[eval_entry]", " ".join(sys.argv))
        try:
            runpy.run_path(str(script), run_name="__main__")
        except SystemExit as e:  # tyro exits 0 on success in some versions
            if e.code not in (0, None):
                raise


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("smoke", "upstream"), default="smoke")
    ap.add_argument("--policy", choices=POLICY_ARMS, default=None)
    ap.add_argument("--config", default=str(PROGRAM_ROOT / "configs" / "colab_smoke.yaml"))
    ap.add_argument("--ckpt", type=Path, default=None)
    ap.add_argument("--out", default=str(PROGRAM_ROOT / "logs" / "smoke"))
    a = ap.parse_args()
    cfg = load_config(a.config)
    if a.mode == "smoke":
        arms = [a.policy] if a.policy else list(POLICY_ARMS)
        res = [b2_smoke(arm, cfg) for arm in arms]
        idx_cfg = {**cfg, "attention": {**cfg.get("attention", {}), "id_mode": "index"}}
        res.append({**b2_smoke("attention", idx_cfg), "policy": "attention[id_mode=index]"})
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "b2_smoke.json").write_text(json.dumps(res, indent=2))
        print(json.dumps(res, indent=2))
    else:
        assert a.ckpt is not None, "--ckpt required in upstream mode"
        run_upstream(a.ckpt, cfg, a.policy)


if __name__ == "__main__":
    main()
