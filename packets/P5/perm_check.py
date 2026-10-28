"""CR-B2-1 (d): permutation architectural check (spikes/B2/PLAN.md §6).

Reproduces the frozen ``eval_entry.b2_smoke`` permutation test on one decoder: ``torch.manual_seed(0)``,
n = 32, z = tanh(randn), obs = randn (drawn on CPU, then moved to the decoder's device), 8 permutations from
``torch.Generator().manual_seed(100 + t)``; permute the obs history (and the morphology, if the decoder has one),
un-permute the actions. rel err = max_t max |unperm_t - base| / max(mean |base|, 1e-12).

Values (PLAN §6): ``rel_err_tf32off`` (fp32, TF32 off; the gated value), ``rel_err_default`` (TF32 flags as
found at process start), ``rel_err_masked`` (TF32 off; one explicit mask m, f = 0.2, from the frozen
``random_token_mask`` with ``torch.Generator().manual_seed(7100)``; base call ``token_mask = m``, permutation t
``token_mask = m[:, perm_t]``). ``decoder.auto_mask_frac`` is set to 0.0 before any call and asserted 0.0
before every call. Pass: ``rel_err_tf32off < 1e-4``.

Modes::

    # venue (CUDA): checkpoint through the frozen upstream load path with the run's sidecar, as eval_entry does
    python perm_check.py --mode upstream --config <cfg> --ckpt <dir>/ckpt_0001600.pt --id <ID> --role gate|report \
        --out meta/perm_<ID>.json
    # CPU (prep tests): randomly initialised decoder from the frozen factory (synthetic morphology)
    python perm_check.py --mode cpu --policy attention|mlp_matched|mlp_mind [--id-mode index] --out <file>
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1] / "code"
for p in (str(CODE), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import mlp_mind  # noqa: E402

mlp_mind.register()

import train_entry  # noqa: E402
from attention_policy import permute_obs_history, random_token_mask  # noqa: E402  (frozen function)

THRESHOLD = 1e-4
N, TRIALS, MASK_FRAC, MASK_SEED = 32, 8, 0.2, 7100


@torch.no_grad()
def perm_rel_err(dec: torch.nn.Module, device, masked: bool = False, n: int = N, trials: int = TRIALS) -> dict:
    j, h, latent = dec.cfg.num_joints, dec.cfg.history, dec.cfg.latent_dim
    torch.manual_seed(0)
    z = torch.tanh(torch.randn(n, latent)).to(device)
    obs = torch.randn(n, h * (3 * j + 6)).to(device)
    m = random_token_mask(n, j, MASK_FRAC, generator=torch.Generator().manual_seed(MASK_SEED)).to(device) if masked else None
    assert dec.auto_mask_frac == 0.0, dec.auto_mask_frac
    base = dec(z, obs, token_mask=m) if masked else dec(z, obs)
    morph = getattr(dec, "morphology", None)
    errs = []
    for t in range(trials):
        perm = torch.randperm(j, generator=torch.Generator().manual_seed(100 + t))
        pd = perm.to(device)
        kw = {"morphology": morph[pd]} if morph is not None else {}
        if masked:
            kw["token_mask"] = m[:, pd]
        assert dec.auto_mask_frac == 0.0, dec.auto_mask_frac
        out = dec(z, permute_obs_history(obs, pd, j, h), **kw)
        unperm = torch.empty_like(out)
        unperm[:, pd] = out
        errs.append(float((unperm - base).abs().max()))
    scale = float(base.abs().mean())
    return {"perm_max_abs_err": max(errs), "action_mean_abs": scale, "rel_err": max(errs) / max(scale, 1e-12),
            "per_trial_max_abs_err": errs}


def finite_or_null(x):
    """Non-finite floats (a broken decoder can give NaN) are written as null; PERM then fails, it does not crash."""
    if isinstance(x, float) and not math.isfinite(x):
        return None
    if isinstance(x, dict):
        return {k: finite_or_null(v) for k, v in x.items()}
    if isinstance(x, list):
        return [finite_or_null(v) for v in x]
    return x


def tf32_flags() -> dict:
    return {"matmul": bool(torch.backends.cuda.matmul.allow_tf32), "cudnn": bool(torch.backends.cudnn.allow_tf32)}


def set_tf32(flags: dict) -> None:
    torch.backends.cuda.matmul.allow_tf32 = flags["matmul"]
    torch.backends.cudnn.allow_tf32 = flags["cudnn"]


def check(dec: torch.nn.Module, device) -> dict:
    dec = dec.float().eval()
    loaded = float(getattr(dec, "auto_mask_frac", 0.0))
    dec.auto_mask_frac = 0.0
    default = tf32_flags()
    set_tf32({"matmul": False, "cudnn": False})
    off = perm_rel_err(dec, device)
    masked = perm_rel_err(dec, device, masked=True)
    set_tf32(default)
    dflt = perm_rel_err(dec, device)
    set_tf32({"matmul": False, "cudnn": False})
    return {"rel_err_tf32off": off["rel_err"], "rel_err_default": dflt["rel_err"], "rel_err_masked": masked["rel_err"],
            "tf32off": off, "default": dflt, "masked": masked, "tf32_default_flags": default,
            "auto_mask_frac_loaded": loaded, "auto_mask_frac_used": dec.auto_mask_frac,
            "latent_dim": dec.cfg.latent_dim, "history": dec.cfg.history, "num_joints": dec.cfg.num_joints,
            "n": N, "trials": TRIALS, "mask_frac": MASK_FRAC, "mask_seed": MASK_SEED, "device": str(device),
            "torch": torch.__version__, "decoder_class": type(dec).__name__,
            "has_morphology": getattr(dec, "morphology", None) is not None,
            "id_mode": getattr(dec.cfg, "id_mode", None), "threshold": THRESHOLD,
            "pass": off["rel_err"] < THRESHOLD}


def load_upstream_decoder(ckpt: Path, cfg: dict):
    """Frozen load path as in ``eval_entry.run_upstream``: sidecar -> install_upstream_policy -> upstream loader."""
    if not torch.cuda.is_available():
        sys.exit("[perm_check] --mode upstream requires a CUDA GPU")
    sidecar = ckpt.parent / "junior_policy.json"
    meta = json.loads(sidecar.read_text())
    arm = meta.get("policy")
    assert arm in train_entry.POLICY_ARMS, f"policy arm unknown in {sidecar}"
    if meta.get("attention"):
        cfg = {**cfg, "attention": meta["attention"]}
    import supermimic.eval.benchmark as bench  # noqa: PLC0415

    info = train_entry.install_upstream_policy(arm, cfg, ("supermimic.eval.benchmark",))
    want = (meta.get("descriptor") or {}).get("sha256")
    got = (info.get("descriptor") or {}).get("sha256")
    if arm == "attention" and want and want != got:
        raise RuntimeError(f"[perm_check] descriptor sha256 mismatch: sidecar {want} vs rebuilt {got}")
    policy, _pcfg = bench.load_policy_from_checkpoint(str(ckpt), "cuda:0")
    return policy.decoder, arm, meta, {"sidecar_descriptor_sha256": want, "rebuilt_descriptor_sha256": got}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("upstream", "cpu"), required=True)
    ap.add_argument("--config", default=str(HERE.parents[1] / "configs" / "colab_smoke.yaml"))
    ap.add_argument("--ckpt", type=Path)
    ap.add_argument("--id", default=None)
    ap.add_argument("--role", choices=("gate", "report"), default="report")
    ap.add_argument("--policy", default="attention")
    ap.add_argument("--id-mode", choices=("morph", "index"), default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cfg = train_entry.load_config(a.config)
    if a.mode == "upstream":
        dec, arm, meta, extra = load_upstream_decoder(a.ckpt, cfg)
        res = check(dec, torch.device("cuda:0"))
        res.update(extra, arm=arm, sidecar_train_mask_frac=meta.get("train_mask_frac"), ckpt=str(a.ckpt))
    else:
        cfg = {**cfg, "attention": {**cfg.get("attention", {}), "morphology": "synthetic"}}
        if a.id_mode:
            cfg["attention"]["id_mode"] = a.id_mode
        torch.manual_seed(0)
        dec = train_entry.build_decoder(a.policy, cfg)
        res = check(dec, torch.device("cpu"))
        res.update(arm=a.policy, ckpt=None, note="CPU prep mode: random init, synthetic morphology")
    res.update(id=a.id, role=a.role, mode=a.mode)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(finite_or_null(res), indent=1, allow_nan=False))
    print(f"PERM id={a.id} arm={res['arm']} role={a.role} rel_err_tf32off={res['rel_err_tf32off']!r} "
          f"rel_err_default={res['rel_err_default']!r} rel_err_masked={res['rel_err_masked']!r} pass={str(res['pass']).lower()}")


if __name__ == "__main__":
    main()
