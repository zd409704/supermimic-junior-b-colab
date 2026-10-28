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
import re
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
    DEFAULT_JOINT_NAMES,
    DESCRIPTOR_DIMS,
    count_params,
    hinge_joint_names,
    make_upstream_policy_class,
    morphology_from_mjmodel,
    random_token_mask,
    synthetic_morphology,
)
from descriptor_v2 import (  # noqa: E402
    actuator_params_from_robot_cfg,
    morphology_v2,
    ref29_actuator_params,
    synthetic_morphology_v2,
)
from mlp_baseline import MLPDecoder, MLPDecoderCfg, build_matched_mlp  # noqa: E402

PROGRAM_ROOT = HERE.parent
POLICY_ARMS = ("attention", "mlp_matched", "mlp_upstream")


def load_config(path: str | Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def descriptor_version(cfg: dict) -> str:
    """``attention.descriptor``: ``v2`` (default, production) or ``v1``."""
    v = cfg.get("attention", {}).get("descriptor", "v2")
    if v not in DESCRIPTOR_DIMS:
        raise ValueError(f"attention.descriptor must be one of {sorted(DESCRIPTOR_DIMS)}, got {v!r}")
    return v


def attention_cfg(cfg: dict, latent_dim: int = 32, history: int = 10, num_joints: int = 29) -> AttentionDecoderCfg:
    names = {f.name for f in fields(AttentionDecoderCfg)}
    over = {k: (tuple(v) if isinstance(v, list) else v) for k, v in cfg.get("attention", {}).items() if k in names}
    dim = DESCRIPTOR_DIMS[descriptor_version(cfg)]
    if over.get("morph_dim", dim) != dim:
        raise ValueError(f"attention.morph_dim={over['morph_dim']} conflicts with attention.descriptor (needs {dim})")
    over["morph_dim"] = dim  # follows the descriptor: 16 for v2, 12 for v1
    return AttentionDecoderCfg(latent_dim=latent_dim, history=history, num_joints=num_joints, **over)


def _import_ref(ref: str, what: str):
    """Import ``module:attr``; in upstream mode a failure is fatal (no silent fallback)."""
    mod, fn = ref.split(":")
    try:
        return getattr(importlib.import_module(mod), fn)
    except (ImportError, AttributeError) as e:
        raise RuntimeError(f"[train_entry] cannot import configured {what} {ref!r}: {e!r}") from e


def resolve_init_joint_pos(init_joint_pos, joint_names) -> list[float]:
    """Resolve an entity-config ``joint_pos`` (regex -> angle) to per-joint angles in ``joint_names`` order.

    Joints matching no pattern get 0.0; joints matching several patterns with different values raise.
    """
    out = []
    for n in joint_names:
        vals = {float(v) for pat, v in init_joint_pos.items() if re.fullmatch(pat, n)}
        if len(vals) > 1:
            raise ValueError(f"joint {n!r} matches several init-state patterns with different values: {sorted(vals)}")
        out.append(vals.pop() if vals else 0.0)
    return out


def default_qpos_from_robot_cfg(cfg: dict, joint_names) -> list[float] | None:
    """Env default pose (initial joint positions of the upstream robot entity config), or None if unconfigured."""
    ref = cfg.get("upstream", {}).get("robot_cfg_loader")
    if not ref:
        return None
    robot_cfg = _import_ref(ref, "robot_cfg_loader")()
    try:
        init_jp = robot_cfg.init_state.joint_pos
    except AttributeError as e:
        raise RuntimeError(f"[train_entry] robot entity config from {ref!r} has no init_state.joint_pos") from e
    return resolve_init_joint_pos(init_jp, joint_names)


def action_scale_from_cfg(cfg: dict):
    """Env action scale (regex -> value dict or number) via the configured loader; raises if not obtainable."""
    ref = cfg.get("upstream", {}).get("action_scale_loader")
    if not ref:
        raise RuntimeError("[train_entry] descriptor v2 on the upstream path needs upstream.action_scale_loader in the config")
    obj = _import_ref(ref, "action_scale_loader")
    return obj() if callable(obj) else obj


def load_morphology(cfg: dict, num_joints: int, info: dict | None = None) -> torch.Tensor:
    """Descriptor rows for the policy body. ``info`` (optional dict) receives default_pose_source / joint_names
    (and, for v2, ``descriptor_meta`` / ``actuator_source``)."""
    src = cfg.get("attention", {}).get("morphology", "synthetic")
    ver = descriptor_version(cfg)
    info = {} if info is None else info
    info["descriptor_version"] = ver
    if src == "upstream_mjmodel":
        model = _import_ref(cfg["upstream"]["model_loader"], "model_loader")()
        names = hinge_joint_names(model)
        dq = default_qpos_from_robot_cfg(cfg, names)
        if ver == "v1":
            m = morphology_from_mjmodel(model, default_qpos=dq, info=info)
        else:
            if dq is None:
                raise RuntimeError("[train_entry] descriptor v2 needs upstream.robot_cfg_loader (env default pose)")
            robot_cfg = _import_ref(cfg["upstream"]["robot_cfg_loader"], "robot_cfg_loader")()
            params = actuator_params_from_robot_cfg(robot_cfg, action_scale_from_cfg(cfg), names)
            ab = tuple(cfg.get("attention", {}).get("descriptor_ablate", ()))
            sn = bool(cfg.get("attention", {}).get("descriptor_scale_norm", True))
            m, meta = morphology_v2(model, names, dq, params, scale_norm=sn, ablate=ab)
            info.update(default_pose_source="default_qpos", joint_names=list(names), descriptor_meta=meta,
                        actuator_source="upstream_robot_cfg")
        if dq is not None:
            info["default_pose_source"] = "env_init_state"
        assert m.shape[0] == num_joints, f"model has {m.shape[0]} hinge joints, policy expects {num_joints}"
        return m
    names = list(DEFAULT_JOINT_NAMES[:num_joints])
    info.update(default_pose_source="synthetic", joint_names=names)
    if ver == "v1":
        return synthetic_morphology()[:num_joints]
    params, q = ref29_actuator_params(names)  # CPU-only reference fixture, never on the upstream path
    m, meta = synthetic_morphology_v2(names, q, params)
    info.update(descriptor_meta=meta, actuator_source="ref29_cpu_fixture")
    return m


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
        out["descriptor_version"] = descriptor_version(cfg)
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


# ------------------------------------------------------------------- seam instrumentation (observation-only)
def _names(x) -> list[str] | None:
    return None if x is None else [str(n) for n in x]


def _tri(v) -> str:
    return v if isinstance(v, str) else str(bool(v)).lower()


def joint_order_match(descriptor, entity, action) -> tuple[bool | str, str]:
    """S1: descriptor rows, robot entity AND action order must all be compared and identical.

    Returns True / False / "unverified" (action order not exposed, everything else equal). Only True passes."""
    seqs = {"descriptor": _names(descriptor), "entity": _names(entity), "action": _names(action)}
    avail = {k: v for k, v in seqs.items() if v is not None}
    if "descriptor" not in avail or "entity" not in avail:
        return False, f"missing sequences: {sorted(set(seqs) - set(avail))}"
    ref = avail["descriptor"]
    bad = [k for k, v in avail.items() if v != ref]
    detail = f"compared={sorted(avail)}" + (f" mismatch={bad}" if bad else "")
    if bad:
        return False, detail
    if "action" not in avail:
        return "unverified", detail + " (action order not exposed; S1 unverified)"
    return True, detail


EXPECTED_POLICY_TERMS = ["joint_pos", "joint_vel", "base_ang_vel", "projected_gravity", "actions"]
# Upstream names: packets/P1/ddesc/context/upstream-d9be385/src_supermimic_envs_tracking_env_cfg.py (policy_terms dict, lines 98-104).


def obs_layout_check(obs_dim: int, term_dims, num_joints: int, history: int, term_names=None) -> tuple[bool | str, str]:
    """S2: term NAMES must be exactly EXPECTED_POLICY_TERMS in order, and dims must carry the history (term-major).

    Returns True / False / "unverified". Unknown names, or per-frame term dims (flattening not inspectable), are
    "unverified"; only True passes."""
    expected = history * (3 * num_joints + 6)
    if obs_dim != expected:
        return False, f"obs_dim {obs_dim} != expected {expected}"
    if term_names is None:
        return "unverified", "policy observation term names not exposed by env; order unverified"
    names = [str(n) for n in term_names]
    if names != EXPECTED_POLICY_TERMS:
        return False, f"term names {names} != expected order {EXPECTED_POLICY_TERMS}"
    if term_dims is None:
        return "unverified", "term dims not exposed by env; layout unverified beyond total dim"
    per_frame = [num_joints, num_joints, 3, 3, num_joints]
    td = [int(x) for x in term_dims]
    if td == [history * d for d in per_frame]:
        return True, "names in upstream order; terms carry the history (term-major)"
    if td == per_frame:
        return "unverified", "per-frame term dims; history flattening cannot be inspected"
    return False, f"term dims {td} do not match term-major {per_frame} (x{history})"


def find_env(trainer):
    """Locate the upstream env (an object with ``scene``) on a constructed trainer, without upstream edits."""
    cands = [getattr(trainer, a, None) for a in ("env", "envs", "train_env", "_env", "vec_env")]
    cands += list(getattr(trainer, "__dict__", {}).values())
    for c in cands:
        c = getattr(c, "unwrapped", c)
        if c is not None and hasattr(c, "scene"):
            return c
    return None


def entity_joint_names(env) -> list[str] | None:
    try:
        return list(env.scene["robot"].joint_names)
    except Exception:  # noqa: BLE001  (duck-typed upstream object)
        return None


def action_joint_names(env) -> list[str] | None:
    am = getattr(env, "action_manager", None)
    terms = getattr(am, "_terms", None)
    terms = list(terms.values()) if isinstance(terms, dict) else list(terms or [])
    for t in terms:
        for attr in ("target_names", "joint_names", "_target_names", "_joint_names"):
            v = getattr(t, attr, None)
            if v is not None:
                return list(v)
    return None


def env_action_scale_offset(env):
    """(names, scale, offset) per joint of the env's joint-position action term, or None if not exposed."""
    am = getattr(env, "action_manager", None)
    terms = getattr(am, "_terms", None)
    terms = list(terms.values()) if isinstance(terms, dict) else list(terms or [])
    for t in terms:
        names = next((getattr(t, a) for a in ("target_names", "joint_names", "_target_names", "_joint_names")
                      if getattr(t, a, None) is not None), None)
        scale, offset = getattr(t, "_scale", getattr(t, "scale", None)), getattr(t, "_offset", getattr(t, "offset", None))
        if names is None or scale is None or offset is None:
            continue
        n = len(names)

        def per_joint(x):
            x = torch.as_tensor(x, dtype=torch.float64).detach().cpu()
            if x.dim() == 2:  # (num_envs, J): envs share one scale; use env 0
                x = x[0]
            return x.expand(n).tolist() if x.dim() == 0 else x.reshape(-1).tolist()

        sc, off = per_joint(scale), per_joint(offset)
        if len(sc) == n and len(off) == n:
            return [str(x) for x in names], sc, off
    return None


def action_scale_match(env_terms, meta, rel_tol: float = 1e-6) -> tuple[bool, str]:
    """S5: env action-manager scale/offset per joint name vs sidecar sigma/q_def (relative tolerance)."""
    if meta is None:
        return False, "no descriptor v2 meta to compare against"
    if env_terms is None:
        return False, "env action scale/offset not exposed"
    names, scale, offset = env_terms
    env = {n: (s, o) for n, s, o in zip(names, scale, offset)}
    missing = [n for n in meta["names"] if n not in env]
    if missing:
        return False, f"joints missing from env action term: {missing[:5]}"

    def close(a, b):
        return abs(a - b) <= rel_tol * max(abs(a), abs(b))

    bad = [n for n, sg, qd in zip(meta["names"], meta["sigma"], meta["q_def"])
           if not (close(env[n][0], float(sg)) and close(env[n][1], float(qd)))]
    return not bad, (f"mismatch joints={bad[:5]} (n={len(bad)})" if bad else f"compared={len(meta['names'])} joints rel_tol={rel_tol}")


def policy_term_dims(env) -> list[int] | None:
    om = getattr(env, "observation_manager", None)
    try:
        dims = om.group_obs_term_dim["policy"]
        return [int(torch.Size(d).numel()) if not isinstance(d, int) else d for d in dims]
    except Exception:  # noqa: BLE001
        return None


def policy_term_names(env) -> list[str] | None:
    om = getattr(env, "observation_manager", None)
    for attr in ("active_terms", "group_obs_term_names"):
        try:
            return [str(n) for n in getattr(om, attr)["policy"]]
        except Exception:  # noqa: BLE001
            continue
    return None


class SeamProbe:
    """Prints/records seams S1-S5 on the upstream path; observation-only except that S1 mismatch raises."""

    def __init__(self, morph_info: dict, compile_value: str, num_joints: int = 29, history: int = 10, emit=print):
        self.morph_info, self.compile_value, self.j, self.h, self.emit = morph_info, compile_value, num_joints, history, emit
        self.seam: dict = {}
        self.term_dims = None
        self.term_names = None

    def _line(self, text: str) -> None:
        self.emit(f"[seam] {text}")

    def report_s4(self) -> None:
        src = self.morph_info.get("default_pose_source")
        val = "env_init_state" if src == "env_init_state" else "qpos0-fallback" if src == "qpos0-fallback" else str(src)
        self.seam["S4_default_pose_source"] = val
        self._line(f"S4 default_pose_source={val}")

    def report_s5(self, env) -> None:
        meta = self.morph_info.get("descriptor_meta")
        if self.morph_info.get("descriptor_version") == "v1":
            self.seam["S5_env_action_scale_match"] = "na"
            self._line("S5 env_action_scale_match=na")
            self._line("S5 detail descriptor v1 carries no action scale")
            return
        ok, detail = action_scale_match(env_action_scale_offset(env), meta)
        self.seam.update(S5_env_action_scale_match=ok, S5_detail=detail)
        self._line(f"S5 env_action_scale_match={str(ok).lower()}")
        self._line(f"S5 detail {detail}")
        if not ok:
            raise RuntimeError(f"[seam] S5 env action scale/offset differ from descriptor sigma/q_def: {detail}")

    def on_trainer_ready(self, trainer) -> None:
        env = find_env(trainer)
        if env is None:
            self.seam["S1_joint_order_match"] = False
            self._line("S1 joint_order_match=false")
            raise RuntimeError("[seam] S1: upstream env not found on trainer; cannot verify joint order")
        ok, detail = joint_order_match(self.morph_info.get("joint_names"), entity_joint_names(env), action_joint_names(env))
        self.seam.update(S1_joint_order_match=ok, S1_detail=detail)
        self._line(f"S1 joint_order_match={_tri(ok)}")
        self._line(f"S1 detail {detail}")
        if ok is not True:
            raise RuntimeError(f"[seam] S1 joint order {_tri(ok)} (descriptor rows / robot entity / action order): {detail}")
        self.report_s5(env)
        self.term_dims = policy_term_dims(env)
        self.term_names = policy_term_names(env)
        tcfg = getattr(getattr(trainer, "cfg", None), "policy_trainer", None)
        comp = getattr(tcfg, "compile", self.compile_value)
        self.seam["S3_compile"] = str(comp)
        self._line(f"S3 compile={comp}")

    def on_first_decoder_call(self, obs_hist: torch.Tensor) -> None:
        dim = int(obs_hist.shape[-1])
        ok, detail = obs_layout_check(dim, self.term_dims, self.j, self.h, self.term_names)
        self.seam.update(S2_obs_policy_dim=dim, S2_term_major_ok=ok, S2_detail=detail)
        self._line(f"S2 obs_policy_dim={dim} term_major_ok={_tri(ok)}")
        self._line(f"S2 detail {detail}")
        if ok is not True:
            raise RuntimeError(f"[seam] S2 term_major_ok={_tri(ok)}: {detail}")

    def attach_decoder(self, dec: torch.nn.Module) -> None:
        def pre_hook(_m, args, kwargs):
            handle.remove()
            obs = args[1] if len(args) > 1 else kwargs.get("obs_hist")
            if obs is not None:
                self.on_first_decoder_call(obs)

        handle = dec.register_forward_pre_hook(pre_hook, with_kwargs=True)

    def install(self, targets: tuple[str, ...]) -> None:
        """Wrap ``Trainer.__init__`` of the upstream training-loop module (in-process, no upstream edits)."""
        loop = importlib.import_module(targets[0])
        trainer_cls = getattr(loop, "Trainer", None)
        if trainer_cls is None:
            raise RuntimeError(f"[seam] {targets[0]} has no Trainer; cannot attach S1-S3 instrumentation")
        orig, probe = trainer_cls.__init__, self

        def init(trainer, *a, **k):
            orig(trainer, *a, **k)
            probe.on_trainer_ready(trainer)

        trainer_cls.__init__ = init


def install_upstream_policy(arm: str, cfg: dict, targets: tuple[str, ...], probe_cls=None) -> dict:
    """Rebind ``Policy`` in the given upstream modules to a subclass with our decoder.

    With ``probe_cls`` (train path) the descriptor/default pose is always resolved from the upstream
    loaders (all arms, so S1/S4 are recorded for every arm) and seams S1-S4 are instrumented.
    """
    info: dict = {}
    morph_info: dict = {}
    morphology = None
    if arm == "attention" or probe_cls is not None:
        if probe_cls is not None and cfg.get("attention", {}).get("morphology") != "upstream_mjmodel":
            raise RuntimeError("[train_entry] upstream mode requires attention.morphology: upstream_mjmodel")
        morphology = load_morphology(cfg, 29, morph_info)
    info["default_pose_source"] = morph_info.get("default_pose_source")
    info["descriptor_joint_names"] = morph_info.get("joint_names")
    if morph_info.get("descriptor_meta") is not None:  # full v2 meta (constants, per-joint inputs, matrix, sha256)
        info["descriptor"] = morph_info["descriptor_meta"]
        info["actuator_source"] = morph_info.get("actuator_source")
    probe = None
    if probe_cls is not None:
        compile_value = str(cfg.get("upstream", {}).get("tyro_args", {}).get("--policy-trainer.compile", "unset"))
        probe = probe_cls(morph_info, compile_value)
        probe.report_s4()
        probe.install(targets)
        info["seam"] = probe.seam
    if arm != "attention":
        morphology = None

    def factory(pcfg):
        dec = build_decoder(arm, cfg, latent_dim=pcfg.latent_dim, history=pcfg.history, num_joints=29, morphology=morphology)
        if hasattr(pcfg, "obs_term_scale") and hasattr(dec, "scale"):
            assert tuple(pcfg.obs_term_scale) == tuple(attention_cfg(cfg).obs_term_scale), "obs scale drift vs upstream"
        dec.auto_mask_frac = float(cfg.get("b2", {}).get("train_mask_frac", 0.0))
        info.update(decoder_sidecar(arm, cfg, dec), train_mask_frac=dec.auto_mask_frac)
        if probe is not None:
            probe.attach_decoder(dec)
        return dec

    cls = make_upstream_policy_class(factory)
    for t in targets:
        setattr(importlib.import_module(t), "Policy", cls)
    return info


def run_upstream(arm: str, cfg: dict) -> None:
    if not torch.cuda.is_available():
        sys.exit("[train_entry] --mode upstream requires a CUDA GPU (Colab T4/L4). Use --mode smoke on CPU.")
    info = install_upstream_policy(arm, cfg, ("supermimic.training.loop",), probe_cls=SeamProbe)
    argv = tyro_argv(cfg, arm)
    print("[train_entry] upstream argv:", " ".join(argv))
    sys.argv = ["sm-train", *argv]
    run_dir = Path("logs") / argv[1]
    run_dir.mkdir(parents=True, exist_ok=True)
    from supermimic.scripts.train import main as upstream_main  # noqa: PLC0415

    try:
        upstream_main()
    finally:
        (run_dir / "junior_policy.json").write_text(json.dumps({**info, "argv": argv}, indent=2, default=float))


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
