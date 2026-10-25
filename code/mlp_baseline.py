"""Matched-parameter MLP decoder for the B0 comparison (attention vs MLP on the same WM/critic loop).

Same interface and input scaling as the upstream SuperMimic-style ``Decoder``:
``forward(z, obs_hist) -> actions (N, J)``; input is ``cat(z, obs_hist * scale)``. Hidden widths
follow the upstream taper (w, w/2, w/4, w/8) and ``w`` is solved so that the trainable parameter
count matches a target (normally ``count_params(AttentionDecoder)``) to within ``tol``.

Two MLP arms are meaningful for B0:

* ``mlp_matched`` -- this module at the attention decoder's parameter count (the kill comparison);
* ``mlp_upstream`` -- the upstream default decoder widths (2048, 1024, 512, 256), roughly 10x the
  attention decoder's size; reported as a reference, not as the kill criterion.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn

from attention_policy import AttentionDecoderCfg, _mlp, count_params, obs_scale_vector, random_token_mask

UPSTREAM_DECODER_HIDDEN: tuple[int, ...] = (2048, 1024, 512, 256)


@dataclass
class MLPDecoderCfg:
    latent_dim: int = 32
    history: int = 10
    num_joints: int = 29
    hidden: tuple[int, ...] = UPSTREAM_DECODER_HIDDEN
    last_gain: float = 0.01


class MLPDecoder(nn.Module):
    def __init__(self, cfg: MLPDecoderCfg, apply_obs_scale: bool = True):
        super().__init__()
        self.cfg = cfg
        obs_dim = cfg.history * (3 * cfg.num_joints + 6)
        self.mlp = _mlp(cfg.latent_dim + obs_dim, cfg.hidden, cfg.num_joints, last_gain=cfg.last_gain)
        acfg = AttentionDecoderCfg(latent_dim=cfg.latent_dim, history=cfg.history, num_joints=cfg.num_joints)
        self.register_buffer("scale", obs_scale_vector(acfg) if apply_obs_scale else torch.ones(obs_dim))
        self.auto_mask_frac = 0.0  # same B2 hook as AttentionDecoder

    def forward(self, z: torch.Tensor, obs_hist: torch.Tensor, token_mask: torch.Tensor | None = None,
                morphology: torch.Tensor | None = None) -> torch.Tensor:
        # token_mask / morphology accepted for a uniform B2 harness. A mask zeroes the masked joints'
        # observation columns (the MLP has no notion of a missing token); morphology is ignored.
        x = obs_hist * self.scale
        if token_mask is None and self.auto_mask_frac > 0:
            token_mask = random_token_mask(x.shape[0], self.cfg.num_joints, self.auto_mask_frac, device=x.device)
        if token_mask is not None:
            x = x * _column_keep(token_mask, self.cfg.num_joints, self.cfg.history)
        return self.mlp(torch.cat([z, x], dim=-1))


def _column_keep(token_mask: torch.Tensor, j: int, h: int) -> torch.Tensor:
    keep_j = (~token_mask.bool()).float()  # (N, J)
    joint_block = keep_j.unsqueeze(1).expand(-1, h, -1).reshape(-1, h * j)
    root_block = torch.ones(token_mask.shape[0], 6 * h, device=token_mask.device)
    return torch.cat([joint_block, joint_block, root_block, joint_block], dim=-1)


def taper(width: int, depth: int = 4) -> tuple[int, ...]:
    return tuple(max(8, width // (2**k)) for k in range(depth))


def matched_hidden(target_params: int, cfg: MLPDecoderCfg | None = None, depth: int = 4, tol: float = 0.05) -> tuple[int, ...]:
    """Smallest-error tapered width whose parameter count is within ``tol`` of ``target_params``."""
    cfg = cfg or MLPDecoderCfg()
    best, best_err = None, float("inf")
    for w in range(16, 4097, 8):
        n = count_params(MLPDecoder(MLPDecoderCfg(cfg.latent_dim, cfg.history, cfg.num_joints, taper(w, depth))))
        err = abs(n - target_params) / target_params
        if err < best_err:
            best, best_err = taper(w, depth), err
        if n > target_params * (1 + tol):
            break
    assert best is not None and best_err <= tol, f"no width within {tol:.0%} of {target_params} (best {best_err:.1%})"
    return best


def build_matched_mlp(target_params: int, cfg: MLPDecoderCfg | None = None, depth: int = 4) -> MLPDecoder:
    cfg = cfg or MLPDecoderCfg()
    hidden = matched_hidden(target_params, cfg, depth)
    return MLPDecoder(MLPDecoderCfg(cfg.latent_dim, cfg.history, cfg.num_joints, hidden, cfg.last_gain))


if __name__ == "__main__":
    from attention_policy import AttentionDecoder

    att = AttentionDecoder(AttentionDecoderCfg())
    mlp = build_matched_mlp(count_params(att))
    print("attention", count_params(att), "mlp_matched", count_params(mlp), mlp.cfg.hidden,
          "mlp_upstream", count_params(MLPDecoder(MLPDecoderCfg())))
