"""CR-B2-1 (b): ``mlp_mind`` decoder, the RV-2 mask-fairness control (spikes/B2/PLAN.md §2.3 (b)).

An MLP with an explicit per-joint mask-indicator input. Input = ``[z, x * keep, ind]``:

* ``x`` is the scaled observation history exactly as in the frozen ``MLPDecoder`` (``obs_hist * scale``);
* ``keep`` is the frozen ``mlp_baseline._column_keep`` zero-fill of the masked joints' columns;
* ``ind`` in {0,1}^29 is the per-joint mask indicator (1 = masked), concatenated **once** (not per history
  frame). With no mask, ``ind`` = 0.

Same tapered MLP family as ``mlp_matched``. Widths come from the frozen ``mlp_baseline.matched_hidden``
search, run with this class in place of ``MLPDecoder`` so that the counted network has the enlarged input
(``register`` / ``build_mlp_mind`` below). Same ``auto_mask_frac`` hook and the same module-level
``random_token_mask`` call as the frozen decoders, so ``train_mask_frac`` and the P5 eval mask stream
(``maskstream.py``) apply identically.

No frozen file is edited. ``register()`` adds the arm to the frozen ``train_entry`` in-process:
``POLICY_ARMS`` gains ``mlp_mind`` and ``build_decoder`` is wrapped. It must run before ``eval_entry`` is
imported, because ``eval_entry`` binds both names at import time.
"""

from __future__ import annotations

import sys
from pathlib import Path

import torch
import torch.nn as nn

CODE = Path(__file__).resolve().parents[2] / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import mlp_baseline  # noqa: E402
from attention_policy import AttentionDecoder, AttentionDecoderCfg, _mlp, count_params, obs_scale_vector, random_token_mask  # noqa: E402,F401
from mlp_baseline import MLPDecoder, MLPDecoderCfg, _column_keep  # noqa: E402

ARM = "mlp_mind"
ATTENTION_PARAMS = 464001  # PLAN §2.3 (b): the attention arm's parameter count (P4 sidecars)


class MLPMindDecoder(MLPDecoder):
    """``forward(z, obs_hist, token_mask=None, morphology=None) -> actions (N, J)``.

    Subclass of the frozen ``MLPDecoder`` only so that the frozen ``decoder_sidecar`` records
    ``mlp_hidden``; ``__init__`` builds its own (enlarged-input) MLP and does not call the parent's.
    """

    def __init__(self, cfg: MLPDecoderCfg, apply_obs_scale: bool = True):
        nn.Module.__init__(self)
        self.cfg = cfg
        obs_dim = cfg.history * (3 * cfg.num_joints + 6)
        self.mlp = _mlp(cfg.latent_dim + obs_dim + cfg.num_joints, cfg.hidden, cfg.num_joints, last_gain=cfg.last_gain)
        acfg = AttentionDecoderCfg(latent_dim=cfg.latent_dim, history=cfg.history, num_joints=cfg.num_joints)
        self.register_buffer("scale", obs_scale_vector(acfg) if apply_obs_scale else torch.ones(obs_dim))
        self.auto_mask_frac = 0.0  # same B2 hook as the frozen decoders

    def forward(self, z: torch.Tensor, obs_hist: torch.Tensor, token_mask: torch.Tensor | None = None,
                morphology: torch.Tensor | None = None) -> torch.Tensor:
        x = obs_hist * self.scale
        if token_mask is None and self.auto_mask_frac > 0:
            # module-level name, resolved at call time (the P5 eval wrapper replaces it)
            token_mask = random_token_mask(x.shape[0], self.cfg.num_joints, self.auto_mask_frac, device=x.device)
        if token_mask is not None:
            x = x * _column_keep(token_mask, self.cfg.num_joints, self.cfg.history)
            ind = token_mask.bool().to(x.dtype)
        else:
            ind = torch.zeros(x.shape[0], self.cfg.num_joints, dtype=x.dtype, device=x.device)
        return self.mlp(torch.cat([z, x, ind], dim=-1))


def mind_hidden(target_params: int, cfg: MLPDecoderCfg | None = None, depth: int = 4) -> tuple[int, ...]:
    """The frozen ``matched_hidden`` search, counting ``MLPMindDecoder`` (enlarged input) instead of ``MLPDecoder``."""
    saved = mlp_baseline.MLPDecoder
    mlp_baseline.MLPDecoder = MLPMindDecoder
    try:
        return mlp_baseline.matched_hidden(target_params, cfg, depth)
    finally:
        mlp_baseline.MLPDecoder = saved


def build_mlp_mind(target_params: int, cfg: MLPDecoderCfg | None = None, depth: int = 4) -> MLPMindDecoder:
    cfg = cfg or MLPDecoderCfg()
    hidden = mind_hidden(target_params, cfg, depth)
    return MLPMindDecoder(MLPDecoderCfg(cfg.latent_dim, cfg.history, cfg.num_joints, hidden, cfg.last_gain))


def register() -> None:
    """Add ``mlp_mind`` to the frozen ``train_entry`` (idempotent). Call before ``import eval_entry``."""
    import train_entry  # noqa: PLC0415

    if "eval_entry" in sys.modules and ARM not in sys.modules["eval_entry"].POLICY_ARMS:
        raise RuntimeError("[mlp_mind] register() must run before eval_entry is imported")
    if getattr(train_entry.build_decoder, "_p5_mlp_mind", False):
        return
    frozen_build = train_entry.build_decoder

    def build_decoder(arm, cfg, latent_dim=32, history=10, num_joints=29, morphology=None):
        if arm != ARM:
            return frozen_build(arm, cfg, latent_dim, history, num_joints, morphology)
        # sized to the attention arm exactly as the frozen factory sizes mlp_matched
        acfg = train_entry.attention_cfg(cfg, latent_dim, history, num_joints)
        target = count_params(AttentionDecoder(acfg, morphology=morphology))
        return build_mlp_mind(target, MLPDecoderCfg(latent_dim=latent_dim, history=history, num_joints=num_joints))

    build_decoder._p5_mlp_mind = True
    build_decoder.__wrapped__ = frozen_build
    train_entry.build_decoder = build_decoder
    if ARM not in train_entry.POLICY_ARMS:
        train_entry.POLICY_ARMS = (*train_entry.POLICY_ARMS, ARM)


if __name__ == "__main__":
    dec = build_mlp_mind(ATTENTION_PARAMS)
    n = count_params(dec)
    print("mlp_mind", n, dec.cfg.hidden, f"{(n - ATTENTION_PARAMS) / ATTENTION_PARAMS:+.2%}")
