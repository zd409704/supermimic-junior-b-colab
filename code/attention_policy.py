"""Junior-(B) morphology-adaptive shared attention action decoder for a rigid home humanoid.

Drop-in replacement for the MLP ``Decoder`` of a SuperMimic-style policy
(``a = dec(enc_motion(goal), obs_hist)``). The motion encoder, the learned world model and the
imagine/BPTT (or joint-critic) loop are untouched; only the decoder architecture changes.

Mapping from the Junior soft-body policy to a rigid humanoid plant
-----------------------------------------------------------------
=====================================  =====================================================
Junior (soft body)                     This module (rigid 29-DoF home humanoid)
=====================================  =====================================================
vertex token                           *joint/link token* j: one per hinge joint (the child
                                       link it drives); features = that joint's slice of the
                                       observation history (pos, vel, previous action)
vertex rest-pose position (ID key)     *morphology descriptor* m_j, computed once from the
                                       default pose: joint anchor position and axis in the
                                       root frame, default angle, tree depth, side sign.
                                       Tokens are keyed by m_j, NOT by array index, so the
                                       decoder is equivariant to joint reordering (B2) and can
                                       be fed a different body graph (B1)
centre / global token                  *root token*: base angular velocity + projected gravity
                                       history (the floating base has no actuator)
muscle                                 *actuator* i (here 1:1 with hinge joints)
muscle query (shared MLP)              QueryMLP(h_i, m_i, z) -- weights shared by all actuators
attention over vertices                multi-head attention of each actuator query over the
                                       root + joint tokens (+ a motion-latent token)
muscle contraction readout             ReadoutMLP(attn_i, h_i, z) -> scalar action a_i (same
                                       action space as the tracker baseline: joint position
                                       target offsets)
(goal / task conditioning)             motion latent z from the unchanged motion encoder,
                                       injected (a) as an extra key/value token, (b) into every
                                       query and readout
=====================================  =====================================================

Observation layout (upstream mjlab reproduction, term-major history, H frames oldest->newest)::

    [joint_pos (H*J) | joint_vel (H*J) | base_ang_vel (H*3) | projected_gravity (H*3) | actions (H*J)]

with each block laid out as ``t * d + k``. Default J = 29, H = 10 -> 930 dims. Per-term scales are
applied by the caller (or by ``obs_scale``) exactly as for the MLP decoder.

Variable body graph (B1): no weight depends on J (except the ``id_mode=index`` ablation table), so the
same trained decoder accepts another body by passing ``morphology`` with J' rows and a J'-joint
observation history; it returns J' actions.

Masking (B2): ``token_mask`` (N, J) bool, True = observation token dropped. Dropped tokens are
excluded from keys/values; every actuator still emits an action (its query falls back to its
morphology descriptor + z).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import torch
import torch.nn as nn

# Generic 29-DoF humanoid joint order used by the upstream reproduction (names are kinematic, not
# brand-specific). Only used to build a synthetic morphology when no MuJoCo model is available.
DEFAULT_JOINT_NAMES: tuple[str, ...] = (
    "left_hip_pitch_joint", "left_hip_roll_joint", "left_hip_yaw_joint", "left_knee_joint",
    "left_ankle_pitch_joint", "left_ankle_roll_joint",
    "right_hip_pitch_joint", "right_hip_roll_joint", "right_hip_yaw_joint", "right_knee_joint",
    "right_ankle_pitch_joint", "right_ankle_roll_joint",
    "waist_yaw_joint", "waist_roll_joint", "waist_pitch_joint",
    "left_shoulder_pitch_joint", "left_shoulder_roll_joint", "left_shoulder_yaw_joint",
    "left_elbow_joint", "left_wrist_roll_joint", "left_wrist_pitch_joint", "left_wrist_yaw_joint",
    "right_shoulder_pitch_joint", "right_shoulder_roll_joint", "right_shoulder_yaw_joint",
    "right_elbow_joint", "right_wrist_roll_joint", "right_wrist_pitch_joint", "right_wrist_yaw_joint",
)

# Upstream per-term scales (divide): joint_pos, joint_vel, base_ang_vel, projected_gravity, actions.
DEFAULT_OBS_TERM_SCALE: tuple[float, ...] = (1.0, 5.0, 2.0, 1.0, 1.0)

MORPH_DIM = 12  # anchor xyz (3) + axis xyz (3) + default angle (1) + depth (1) + side (1) + limb one-hot (3)


@dataclass
class AttentionDecoderCfg:
    latent_dim: int = 32
    history: int = 10
    num_joints: int = 29
    d_model: int = 128
    num_heads: int = 4
    num_self_attn_layers: int = 1  # token self-attention before the per-actuator cross-attention
    query_hidden: tuple[int, ...] = (256,)
    readout_hidden: tuple[int, ...] = (256, 128)
    morph_dim: int = MORPH_DIM
    # "morph": keys are morphology descriptors only (permutation-equivariant; the Junior-(B) arm).
    # "index": learned per-index embedding added (breaks equivariance; ablation only).
    id_mode: str = "morph"
    obs_term_scale: tuple[float, ...] = DEFAULT_OBS_TERM_SCALE
    last_gain: float = 0.01  # matches upstream decoder_last_gain (small initial actions)
    dropout: float = 0.0


def _mlp(in_dim: int, hidden: tuple[int, ...], out_dim: int, last_gain: float | None = None) -> nn.Sequential:
    layers: list[nn.Module] = []
    d = in_dim
    for h in hidden:
        layers += [nn.Linear(d, h), nn.SiLU()]
        d = h
    last = nn.Linear(d, out_dim)
    if last_gain is not None:
        nn.init.orthogonal_(last.weight, gain=last_gain)
        nn.init.zeros_(last.bias)
    layers.append(last)
    return nn.Sequential(*layers)


def _limb_from_name(name: str) -> int | None:
    """0 = leg, 1 = torso/waist, 2 = arm; None if the name gives no hint."""
    if any(k in name for k in ("hip", "knee", "ankle", "thigh", "calf")):
        return 0
    if any(k in name for k in ("waist", "torso", "head", "neck")):
        return 1
    if any(k in name for k in ("shoulder", "elbow", "wrist", "upper_arm", "hand")):
        return 2
    return None


def _side_from_name(name: str) -> float:
    if name.startswith(("left", "l_")):
        return 1.0
    if name.startswith(("right", "r_")):
        return -1.0
    return 0.0


def synthetic_morphology(joint_names: tuple[str, ...] = DEFAULT_JOINT_NAMES) -> torch.Tensor:
    """Name-derived stand-in for the default-pose descriptor (CPU smoke / no MuJoCo model).

    Real runs should use :func:`morphology_from_mjmodel`. This version only guarantees that every
    joint gets a distinct, embodiment-meaningful key (side, limb, chain depth, axis type).
    """
    rows = []
    chain_pos: dict[str, int] = {}
    for name in joint_names:
        side = _side_from_name(name)
        limb = _limb_from_name(name)
        limb = 2 if limb is None else limb
        z = (-0.5, 0.0, 0.4)[limb]
        chain = f"{side}-{limb}"
        depth = chain_pos.get(chain, 0)
        chain_pos[chain] = depth + 1
        axis_name = next((a for a in ("roll", "pitch", "yaw") if a in name), "pitch")
        axis = [0.0, 0.0, 0.0]
        axis[("roll", "pitch", "yaw").index(axis_name)] = 1.0
        if limb == 0:  # legs hang down from the hips
            anchor = [0.0, 0.1 * side, z - 0.1 * depth]
        elif limb == 1:  # waist stacks up the torso
            anchor = [0.0, 0.0, z + 0.05 * depth]
        else:  # arms extend sideways from the shoulders
            anchor = [0.0, (0.15 + 0.08 * depth) * side, z]
        onehot = [0.0, 0.0, 0.0]
        onehot[limb] = 1.0
        rows.append(anchor + axis + [0.0, depth / 6.0, side] + onehot)
    return torch.tensor(rows, dtype=torch.float32)


def morphology_from_mjmodel(model, joint_names: tuple[str, ...] | None = None) -> torch.Tensor:
    """Default-pose morphology descriptor m_j from a compiled ``mujoco.MjModel`` (Colab path).

    For each hinge joint: world anchor and axis at ``qpos0`` expressed relative to the root body,
    the default angle, normalised tree depth, lateral side sign and a coarse limb one-hot.
    Requires ``mujoco`` (installed with the upstream reproduction, not on the research box).
    """
    import mujoco  # noqa: PLC0415  (optional dependency)
    import numpy as np  # noqa: PLC0415

    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    names = joint_names or tuple(
        mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j)
        for j in range(model.njnt) if model.jnt_type[j] == mujoco.mjtJoint.mjJNT_HINGE
    )
    root_body = 1
    root_pos = data.xpos[root_body].copy()
    root_rot = data.xmat[root_body].reshape(3, 3).copy()
    max_depth = 1
    depths = []
    for n in names:
        j = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, n)
        b, d = model.jnt_bodyid[j], 0
        while b > root_body:
            b, d = model.body_parentid[b], d + 1
        depths.append(d)
        max_depth = max(max_depth, d)
    rows = []
    for n, d in zip(names, depths):
        j = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, n)
        anchor = root_rot.T @ (data.xanchor[j] - root_pos)
        axis = root_rot.T @ data.xaxis[j]
        side = float(np.sign(np.round(anchor[1], 3)))
        limb = _limb_from_name(n)
        if limb is None:  # geometric fallback for unfamiliar joint names
            limb = 0 if anchor[2] < -0.1 else (1 if abs(anchor[1]) < 0.05 else 2)
        onehot = [0.0, 0.0, 0.0]
        onehot[limb] = 1.0
        rows.append([*anchor, *axis, float(model.qpos0[model.jnt_qposadr[j]]), d / max_depth, side, *onehot])
    return torch.tensor(rows, dtype=torch.float32)


def obs_scale_vector(cfg: AttentionDecoderCfg) -> torch.Tensor:
    j, h = cfg.num_joints, cfg.history
    dims = (j, j, 3, 3, j)
    return torch.cat([torch.full((h * d,), 1.0 / s) for d, s in zip(dims, cfg.obs_term_scale)])


def split_obs_history(obs_hist: torch.Tensor, num_joints: int, history: int):
    """(N, H*(3J+6)) term-major -> joint tokens (N, J, 3H) and root token (N, 6H)."""
    n, j, h = obs_hist.shape[0], num_joints, history
    sizes = (h * j, h * j, h * 3, h * 3, h * j)
    qpos, qvel, angv, grav, act = torch.split(obs_hist, sizes, dim=-1)
    per_joint = [x.reshape(n, h, j).transpose(1, 2) for x in (qpos, qvel, act)]  # (N, J, H) each
    joint_tok = torch.cat(per_joint, dim=-1)  # (N, J, 3H)
    root_tok = torch.cat([angv, grav], dim=-1)  # (N, 6H)
    return joint_tok, root_tok


class AttentionDecoder(nn.Module):
    """Shared per-actuator attention decoder: ``forward(z, obs_hist) -> actions (N, J)``.

    Same call signature as the upstream MLP ``Decoder`` so it can be swapped in place.
    """

    def __init__(self, cfg: AttentionDecoderCfg, morphology: torch.Tensor | None = None, apply_obs_scale: bool = True):
        super().__init__()
        self.cfg = cfg
        if morphology is None:
            morphology = synthetic_morphology(DEFAULT_JOINT_NAMES[: cfg.num_joints])
        assert morphology.shape == (cfg.num_joints, cfg.morph_dim), morphology.shape
        self.register_buffer("morphology", morphology.clone())
        self.register_buffer("scale", obs_scale_vector(cfg) if apply_obs_scale else torch.ones(cfg.history * (3 * cfg.num_joints + 6)))
        d, h = cfg.d_model, cfg.history

        # Token encoders (shared across joints).
        self.morph_mlp = _mlp(cfg.morph_dim, (d,), d)
        self.joint_state = nn.Linear(3 * h, d)
        self.root_state = _mlp(6 * h, (d,), d)
        self.root_type = nn.Parameter(torch.zeros(d))
        self.z_token = nn.Linear(cfg.latent_dim, d)
        self.index_embed = nn.Embedding(cfg.num_joints, d) if cfg.id_mode == "index" else None
        layer = nn.TransformerEncoderLayer(d, cfg.num_heads, 2 * d, cfg.dropout, activation="gelu", batch_first=True, norm_first=True)
        self.self_attn = nn.TransformerEncoder(layer, cfg.num_self_attn_layers, enable_nested_tensor=False) if cfg.num_self_attn_layers > 0 else None

        # Per-actuator shared query / cross-attention / readout.
        self.query_mlp = _mlp(2 * d + cfg.latent_dim, cfg.query_hidden, d)
        self.kv_norm = nn.LayerNorm(d)
        self.cross_attn = nn.MultiheadAttention(d, cfg.num_heads, dropout=cfg.dropout, batch_first=True)
        self.readout_mlp = _mlp(2 * d + cfg.latent_dim, cfg.readout_hidden, 1, last_gain=cfg.last_gain)
        # If > 0 and no explicit token_mask is passed, drop this fraction of joint tokens per sample.
        # Lets the unchanged upstream loop/benchmark run B2 token-drop (train augmentation or eval).
        self.auto_mask_frac = 0.0

    def obs_scale(self, num_joints: int) -> torch.Tensor:
        if num_joints == self.cfg.num_joints:
            return self.scale
        return obs_scale_vector(replace(self.cfg, num_joints=num_joints)).to(self.scale.device)

    def tokens(self, z: torch.Tensor, obs_hist: torch.Tensor, morphology: torch.Tensor):
        j = morphology.shape[-2]
        joint_feat, root_feat = split_obs_history(obs_hist * self.obs_scale(j), j, self.cfg.history)
        m = self.morph_mlp(morphology)  # (J, d) or (N, J, d)
        if m.dim() == 2:
            m = m.unsqueeze(0).expand(joint_feat.shape[0], -1, -1)
        if self.index_embed is not None:
            m = m + self.index_embed.weight.unsqueeze(0)
        joint_tok = self.joint_state(joint_feat) + m
        root_tok = (self.root_state(root_feat) + self.root_type).unsqueeze(1)
        z_tok = self.z_token(z).unsqueeze(1)
        return joint_tok, root_tok, z_tok, m

    def forward(self, z: torch.Tensor, obs_hist: torch.Tensor, token_mask: torch.Tensor | None = None,
                morphology: torch.Tensor | None = None) -> torch.Tensor:
        morphology = self.morphology if morphology is None else morphology
        if token_mask is None and self.auto_mask_frac > 0:
            token_mask = random_token_mask(obs_hist.shape[0], morphology.shape[-2], self.auto_mask_frac, device=obs_hist.device)
        joint_tok, root_tok, z_tok, m = self.tokens(z, obs_hist, morphology)
        n, j, _ = joint_tok.shape
        kv = torch.cat([root_tok, z_tok, joint_tok], dim=1)  # (N, 2+J, d)
        pad = None
        if token_mask is not None:
            pad = torch.cat([torch.zeros(n, 2, dtype=torch.bool, device=kv.device), token_mask.bool()], dim=1)
        if self.self_attn is not None:
            kv = self.self_attn(kv, src_key_padding_mask=pad)
        kv = self.kv_norm(kv)
        h_joint = kv[:, 2:]
        if token_mask is not None:  # a dropped sensor must not leak into its own actuator's query
            h_joint = torch.where(token_mask.unsqueeze(-1), torch.zeros_like(h_joint), h_joint)
        zj = z.unsqueeze(1).expand(-1, j, -1)
        q = self.query_mlp(torch.cat([h_joint, m, zj], dim=-1))  # (N, J, d) shared weights
        attn, _ = self.cross_attn(q, kv, kv, key_padding_mask=pad, need_weights=False)
        return self.readout_mlp(torch.cat([attn, h_joint, zj], dim=-1)).squeeze(-1)  # (N, J)


def permute_obs_history(obs_hist: torch.Tensor, perm: torch.Tensor, num_joints: int, history: int) -> torch.Tensor:
    """Reorder the joint axis of a term-major history (B2 permutation test)."""
    n, j, h = obs_hist.shape[0], num_joints, history
    sizes = (h * j, h * j, h * 3, h * 3, h * j)
    parts = list(torch.split(obs_hist, sizes, dim=-1))
    for k in (0, 1, 4):
        parts[k] = parts[k].reshape(n, h, j)[:, :, perm].reshape(n, h * j)
    return torch.cat(parts, dim=-1)


def random_token_mask(n: int, num_joints: int, frac: float, generator: torch.Generator | None = None, device=None) -> torch.Tensor:
    """Mask exactly round(frac*J) non-root joint tokens per sample (B2 mask test; root never masked)."""
    k = max(1, int(round(frac * num_joints)))
    scores = torch.rand(n, num_joints, generator=generator, device=device)
    idx = scores.topk(k, dim=-1).indices
    return torch.zeros(n, num_joints, dtype=torch.bool, device=device).scatter_(1, idx, True)


def count_params(m: nn.Module) -> int:
    return sum(p.numel() for p in m.parameters() if p.requires_grad)


def make_upstream_policy_class(decoder_factory):
    """Return a subclass of the upstream ``supermimic.policy.nets.Policy`` whose decoder is replaced.

    ``decoder_factory(policy_cfg) -> nn.Module`` with ``forward(z, obs_hist)``. Import is deferred so
    this file stays importable on the research box without the upstream package.
    """
    from supermimic.policy.nets import Policy  # noqa: PLC0415

    class JuniorBPolicy(Policy):
        def __init__(self, cfg):
            super().__init__(cfg)
            self.decoder = decoder_factory(cfg)

    return JuniorBPolicy


if __name__ == "__main__":
    cfg = AttentionDecoderCfg()
    dec = AttentionDecoder(cfg)
    z = torch.randn(4, cfg.latent_dim)
    o = torch.randn(4, cfg.history * (3 * cfg.num_joints + 6))
    print("actions", tuple(dec(z, o).shape), "params", count_params(dec))
