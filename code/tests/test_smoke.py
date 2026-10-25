"""CPU smoke tests (no simulator, no motion data). Run: python -m pytest code/tests -q  (or python code/tests/test_smoke.py)."""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn as nn

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE))

from attention_policy import AttentionDecoder, AttentionDecoderCfg, count_params, permute_obs_history, random_token_mask, synthetic_morphology  # noqa: E402
from train_entry import build_decoder, install_upstream_policy, load_config, tyro_argv  # noqa: E402

CFG = load_config(CODE.parent / "configs" / "colab_smoke.yaml")
J, H, L = 29, 10, 32


def _batch(n=8):
    return torch.tanh(torch.randn(n, L)), torch.randn(n, H * (3 * J + 6))


def test_shapes_and_distinct_morphology():
    m = synthetic_morphology()
    assert m.shape == (J, 12) and torch.unique(m, dim=0).shape[0] == J
    z, o = _batch()
    assert AttentionDecoder(AttentionDecoderCfg())(z, o).shape == (8, J)


def test_permutation_equivariance():
    dec = AttentionDecoder(AttentionDecoderCfg()).eval()
    z, o = _batch()
    perm = torch.randperm(J)
    with torch.no_grad():
        a = dec(z, o)
        b = dec(z, permute_obs_history(o, perm, J, H), morphology=dec.morphology[perm])
    assert torch.allclose(b, a[:, perm], atol=1e-5)


def test_mask_and_grad():
    dec = AttentionDecoder(AttentionDecoderCfg())
    z, o = _batch()
    a = dec(z, o, token_mask=random_token_mask(8, J, 0.2))
    a.square().sum().backward()
    assert all(p.grad is not None for p in dec.parameters() if p.requires_grad and p is not dec.index_embed)


def test_param_match_within_5pct():
    att, mlp = build_decoder("attention", CFG), build_decoder("mlp_matched", CFG)
    assert abs(count_params(mlp) - count_params(att)) / count_params(att) < 0.05


def test_b1_second_body_from_owner_mjcf():
    """Same decoder weights on the owner-provided 22-hinge home-humanoid MJCF (skipped without mujoco/asset)."""
    xml = CODE.parent / "assets" / "home_humanoid_mjcf" / "pi_plus.xml"
    try:
        import mujoco
    except ImportError:
        print("SKIP b1: mujoco not installed")
        return
    if not xml.exists():
        print("SKIP b1: asset missing")
        return
    from attention_policy import morphology_from_mjmodel

    m2 = morphology_from_mjmodel(mujoco.MjModel.from_xml_path(str(xml)))
    j2 = m2.shape[0]
    assert j2 == 22 and torch.isfinite(m2).all() and torch.unique(m2, dim=0).shape[0] == j2
    dec = AttentionDecoder(AttentionDecoderCfg()).eval()  # built for the 29-joint body
    z = torch.tanh(torch.randn(4, L))
    with torch.no_grad():
        a = dec(z, torch.randn(4, H * (3 * j2 + 6)), morphology=m2)
    assert a.shape == (4, j2) and torch.isfinite(a).all()


def test_upstream_seam_with_fake_package():
    """Exercise install_upstream_policy against a stand-in of the upstream module layout."""

    @dataclass
    class PolicyCfg:
        latent_dim: int = 32
        history: int = 10
        obs_term_scale: tuple = (1.0, 5.0, 2.0, 1.0, 1.0)

    class Policy(nn.Module):  # mirrors upstream: a = dec(enc(goal), obs_hist)
        def __init__(self, cfg):
            super().__init__()
            self.encoders = nn.ModuleDict({"motion": nn.Linear(680, cfg.latent_dim)})
            self.decoder = nn.Linear(cfg.latent_dim + 930, J)

        def forward(self, obs_hist, goal, interface="motion"):
            return self.decoder(torch.tanh(self.encoders[interface](goal)), obs_hist)

    pkg = {name: types.ModuleType(name) for name in ("supermimic", "supermimic.policy", "supermimic.policy.nets", "supermimic.training", "supermimic.training.loop")}
    pkg["supermimic.policy.nets"].Policy = Policy
    pkg["supermimic.training.loop"].Policy = Policy
    saved = {k: sys.modules.get(k) for k in pkg}
    sys.modules.update(pkg)
    try:
        cfg = {**CFG, "attention": {**CFG["attention"], "morphology": "synthetic"}}
        info = install_upstream_policy("attention", cfg, ("supermimic.training.loop",))
        cls = sys.modules["supermimic.training.loop"].Policy
        pol = cls(PolicyCfg())
        assert isinstance(pol.decoder, AttentionDecoder) and info["policy"] == "attention"
        assert pol(torch.randn(4, 930), torch.randn(4, 680)).shape == (4, J)
        argv = tyro_argv(CFG, "attention")
        assert "--env.num-envs" in argv and "--env.anchor-obs" in argv and "--data.npz-dir" in argv
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
