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
from attention_policy import DEPTH_NORM, MORPH_DIM_V1, MORPH_DIM_V2  # noqa: E402
from descriptor_v2 import (  # noqa: E402
    ActuatorParams, actuator_params_from_robot_cfg, default_synthetic_v2, home_actuator_params, home_default_qpos,
    morphology_v2, ref29_actuator_params, synthetic_morphology_v2,
)
from train_entry import (  # noqa: E402
    action_scale_match, attention_cfg, SeamProbe, build_decoder, find_env, install_upstream_policy, joint_order_match, load_config, load_morphology,
    obs_layout_check, resolve_init_joint_pos, tyro_argv,
)

CFG = load_config(CODE.parent / "configs" / "colab_smoke.yaml")
CFG_V1 = {**CFG, "attention": {**CFG["attention"], "descriptor": "v1"}}
SPIKE = CODE.parent / "spikes" / "D-DESC" / "descriptor_v2.py"
J, H, L = 29, 10, 32
DEFAULT_NAMES = __import__("attention_policy").DEFAULT_JOINT_NAMES


def _batch(n=8):
    return torch.tanh(torch.randn(n, L)), torch.randn(n, H * (3 * J + 6))


def test_shapes_and_distinct_morphology():
    m1 = synthetic_morphology()
    assert m1.shape == (J, MORPH_DIM_V1) and torch.unique(m1, dim=0).shape[0] == J
    m2 = default_synthetic_v2()
    assert m2.shape == (J, MORPH_DIM_V2) == (J, 16) and torch.unique(m2, dim=0).shape[0] == J and torch.isfinite(m2).all()
    assert attention_cfg(CFG).morph_dim == 16 and attention_cfg(CFG_V1).morph_dim == 12
    assert attention_cfg({}).morph_dim == 16  # v2 is the default
    z, o = _batch()
    assert AttentionDecoder(attention_cfg(CFG))(z, o).shape == (8, J)  # v2 (default synthetic v2 rows)
    assert AttentionDecoder(attention_cfg(CFG_V1), morphology=m1)(z, o).shape == (8, J)  # v1 path still works
    assert AttentionDecoder(AttentionDecoderCfg(morph_dim=12))(z, o).shape == (8, J)  # v1 synthetic fallback


def test_permutation_equivariance():
    for cfg in (CFG, CFG_V1):
        dec = build_decoder("attention", cfg).eval()
        z, o = _batch()
        perm = torch.randperm(J)
        with torch.no_grad():
            a = dec(z, o)
            b = dec(z, permute_obs_history(o, perm, J, H), morphology=dec.morphology[perm])
        rel = float((b - a[:, perm]).abs().max() / a.abs().mean().clamp_min(1e-12))
        assert rel < 1e-4, (cfg["attention"]["descriptor"], rel)


def test_mask_and_grad():
    dec = AttentionDecoder(AttentionDecoderCfg())
    z, o = _batch()
    a = dec(z, o, token_mask=random_token_mask(8, J, 0.2))
    a.square().sum().backward()
    assert all(p.grad is not None for p in dec.parameters() if p.requires_grad and p is not dec.index_embed)


def test_param_match_within_5pct():
    counts = {}
    for cfg in (CFG, CFG_V1):
        att, mlp = build_decoder("attention", cfg), build_decoder("mlp_matched", cfg)
        counts[cfg["attention"]["descriptor"]] = count_params(att)
        assert abs(count_params(mlp) - count_params(att)) / count_params(att) < 0.05
    assert counts["v2"] - counts["v1"] == 4 * 128  # only morph_mlp[0] widens (12 -> 16 inputs)


def _owner_xml():
    """The single owner-provided MJCF, found by glob (asset contract: exactly one *.xml)."""
    xmls = sorted((CODE.parent / "assets" / "home_humanoid_mjcf").glob("*.xml"))
    assert len(xmls) <= 1, f"asset contract: expected exactly one *.xml, found {[x.name for x in xmls]}"
    return xmls[0] if xmls else None


def test_b1_second_body_from_owner_mjcf():
    """J-agnostic shape test: the 29-joint decoder runs on a J'-joint body (skipped without mujoco/asset).

    This checks tensor shapes and finiteness only; it is not evidence of cross-embodiment transfer.
    """
    xml = _owner_xml()
    try:
        import mujoco
    except ImportError:
        print("SKIP J-agnostic shape test: mujoco not installed")
        return
    if xml is None:
        print("SKIP J-agnostic shape test: asset missing")
        return
    from attention_policy import morphology_from_mjmodel

    m2 = morphology_from_mjmodel(mujoco.MjModel.from_xml_path(str(xml)))
    j2 = m2.shape[0]
    assert j2 == 22 and torch.isfinite(m2).all() and torch.unique(m2, dim=0).shape[0] == j2
    dec = AttentionDecoder(AttentionDecoderCfg(morph_dim=12)).eval()  # built for the 29-joint body (v1 path)
    z = torch.tanh(torch.randn(4, L))
    with torch.no_grad():
        a = dec(z, torch.randn(4, H * (3 * j2 + 6)), morphology=m2)
    assert a.shape == (4, j2) and torch.isfinite(a).all()
    # v2 rows of the same body (home actuator placeholder) feed the default (v2) decoder
    from attention_policy import hinge_joint_names

    model = mujoco.MjModel.from_xml_path(str(xml))
    names = hinge_joint_names(model)
    eff = [float(model.jnt_actfrcrange[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, n), 1]) for n in names]
    ap = home_actuator_params(names, eff, dict(leg=0.01, arm=0.005, head=0.002))
    m16, meta = morphology_v2(model, names, home_default_qpos(names), ap)
    assert m16.shape == (j2, 16) and meta["names"] == list(names)
    with torch.no_grad():
        a = AttentionDecoder(AttentionDecoderCfg()).eval()(z, torch.randn(4, H * (3 * j2 + 6)), morphology=m16)
    assert a.shape == (4, j2) and torch.isfinite(a).all()


def test_fx1_default_pose_and_fx2_depth_norm():
    xml = _owner_xml()
    try:
        import mujoco
    except ImportError:
        print("SKIP fx1/fx2 mjmodel checks: mujoco not installed")
        return
    if xml is None:
        print("SKIP fx1/fx2 mjmodel checks: asset missing")
        return
    from attention_policy import hinge_joint_names, morphology_from_mjmodel

    model = mujoco.MjModel.from_xml_path(str(xml))
    names = hinge_joint_names(model)
    info0: dict = {}
    base = morphology_from_mjmodel(model, info=info0)
    assert info0["default_pose_source"] == "qpos0-fallback" and info0["joint_names"] == list(names)
    arr = [0.1 * (i + 1) for i in range(len(names))]
    info1: dict = {}
    m_arr = morphology_from_mjmodel(model, default_qpos=arr, info=info1)
    m_map = morphology_from_mjmodel(model, default_qpos=dict(zip(names, arr)))
    assert info1["default_pose_source"] == "default_qpos"
    assert torch.allclose(m_arr[:, 6], torch.tensor(arr, dtype=torch.float32))
    assert torch.equal(m_arr, m_map)
    keep = [i for i in range(MORPH_DIM_V1) if i != 6]  # only the default-angle column changes
    assert torch.equal(m_arr[:, keep], base[:, keep])
    try:
        morphology_from_mjmodel(model, default_qpos=arr[:-1])
        raise AssertionError("short default_qpos must raise")
    except ValueError:
        pass
    # FX-2: depth column = integer depth / fixed constant (same constant as the synthetic descriptor)
    d = base[:, 7] * DEPTH_NORM
    assert torch.allclose(d, d.round(), atol=1e-4) and DEPTH_NORM == 8.0
    ds = synthetic_morphology()[:, 7] * DEPTH_NORM
    assert torch.allclose(ds, ds.round(), atol=1e-4)


def test_fx1_unimportable_loader_fails_loudly():
    cfg = {"attention": {"morphology": "upstream_mjmodel"}, "upstream": {"model_loader": "no_such_pkg_xyz:load"}}
    try:
        load_morphology(cfg, 29)
        raise AssertionError("unimportable loader must raise")
    except RuntimeError as e:
        assert "model_loader" in str(e)


def test_fx1_resolve_init_joint_pos():
    assert resolve_init_joint_pos({".*_knee_joint": 0.6, "left_hip_pitch_joint": -0.3}, ["left_hip_pitch_joint", "left_knee_joint", "x"]) == [-0.3, 0.6, 0.0]
    try:
        resolve_init_joint_pos({".*_joint": 0.1, "a_joint": 0.2}, ["a_joint"])
        raise AssertionError("conflicting patterns must raise")
    except ValueError:
        pass


def test_fx5_seam_helpers_with_fake_objects():
    names = ["a", "b", "c"]
    assert joint_order_match(names, names, names)[0]
    assert not joint_order_match(names, names[::-1], names)[0]
    assert not joint_order_match(names, names, ["a", "c", "b"])[0]
    assert not joint_order_match(None, names, names)[0]
    # O-2 truth table: action order missing is "unverified", never True
    assert joint_order_match(names, names, None)[0] == "unverified"
    assert joint_order_match(names, names, names)[0] is True
    assert joint_order_match(names, names[::-1], None)[0] is False
    dims = [H * J, H * J, H * 3, H * 3, H * J]
    good = ["joint_pos", "joint_vel", "base_ang_vel", "projected_gravity", "actions"]
    D = H * (3 * J + 6)
    assert obs_layout_check(D, dims, J, H, good)[0] is True
    assert obs_layout_check(D, [J, J, 3, 3, J], J, H, good)[0] == "unverified"  # flattening not inspectable
    assert obs_layout_check(D, [J, 3, J, 3, J], J, H, good)[0] is False
    assert obs_layout_check(H * (3 * J + 5), dims, J, H, good)[0] is False
    assert obs_layout_check(D, None, J, H, good)[0] == "unverified"
    assert obs_layout_check(D, dims, J, H, None)[0] == "unverified"
    # O-3 reviewer case: swapped term order with identical dims must not pass
    swapped = ["actions", "joint_vel", "base_ang_vel", "projected_gravity", "joint_pos"]
    assert obs_layout_check(D, [H * J, H * J, H * 3, H * 3, H * J], J, H, swapped)[0] is False
    swapped_probe = SeamProbe({}, "None", emit=lambda _t: None)
    swapped_probe.term_dims, swapped_probe.term_names = [H * J, H * J, H * 3, H * 3, H * J], swapped
    try:
        swapped_probe.on_first_decoder_call(torch.zeros(1, D))
        raise AssertionError("swapped term order must raise")
    except RuntimeError:
        assert swapped_probe.seam["S2_term_major_ok"] is False

    class Robot:
        joint_names = names

    class Env:
        scene = {"robot": Robot()}
        action_manager = types.SimpleNamespace(_terms={"joint_pos": types.SimpleNamespace(target_names=names)})
        observation_manager = types.SimpleNamespace(
            group_obs_term_dim={"policy": [(H * J,), (H * J,), (H * 3,), (H * 3,), (H * J,)]},
            active_terms={"policy": ["joint_pos", "joint_vel", "base_ang_vel", "projected_gravity", "actions"]})

    class Trainer:
        def __init__(self):
            self.env = Env()
            self.cfg = types.SimpleNamespace(policy_trainer=types.SimpleNamespace(compile="None"))

    assert find_env(Trainer()) is not None
    lines: list[str] = []
    info = {"default_pose_source": "env_init_state", "joint_names": names, "descriptor_version": "v1"}
    probe = SeamProbe(info, "None", emit=lines.append)
    probe.report_s4()
    probe.on_trainer_ready(Trainer())
    dec = nn.Linear(L + H * (3 * J + 6), J)
    probe.attach_decoder(dec)
    dec.forward = lambda z, o: z  # replaced forward; hook is a pre-hook so it still fires
    dec(torch.zeros(2, L), torch.zeros(2, H * (3 * J + 6)))
    text = "\n".join(lines)
    assert "[seam] S4 default_pose_source=env_init_state" in text
    assert "[seam] S1 joint_order_match=true" in text and "[seam] S3 compile=None" in text
    assert f"[seam] S2 obs_policy_dim={H * (3 * J + 6)} term_major_ok=true" in text
    assert probe.seam["S1_joint_order_match"] is True and probe.seam["S2_term_major_ok"] is True
    # S1 unverified (action order not exposed): printed as `unverified`, recorded, and raises
    Env.action_manager = None
    lines.clear()
    p2 = SeamProbe(info, "None", emit=lines.append)
    try:
        p2.on_trainer_ready(Trainer())
        raise AssertionError("S1 unverified must raise")
    except RuntimeError:
        assert "[seam] S1 joint_order_match=unverified" in lines and p2.seam["S1_joint_order_match"] == "unverified"
    # S1 mismatch: line is printed first, then it raises
    Robot.joint_names = names[::-1]
    lines.clear()
    try:
        SeamProbe(info, "None", emit=lines.append).on_trainer_ready(Trainer())
        raise AssertionError("S1 mismatch must raise")
    except RuntimeError:
        assert "[seam] S1 joint_order_match=false" in lines


def test_o1_eval_descriptor_hash_only_gates_attention():
    import json
    import eval_entry as e
    import train_entry as t
    from pathlib import Path
    from unittest.mock import patch

    class Stop(Exception):
        pass

    mods = {n: types.ModuleType(n) for n in ("supermimic", "supermimic.eval", "supermimic.eval.benchmark")}
    mods["supermimic.eval.benchmark"].load_policy_from_checkpoint = lambda *a, **k: None

    def run(arm, rebuilt):
        meta = {"policy": arm, "descriptor": {"sha256": "trained-hash"}}
        info = {"descriptor": {"sha256": rebuilt}} if rebuilt else {}
        saved = {k: sys.modules.get(k) for k in mods}
        try:
            with patch.dict(sys.modules, mods), patch.object(t, "install_upstream_policy", return_value=info), \
                    patch.object(e, "install_upstream_policy", return_value=info), \
                    patch.object(e.torch.cuda, "is_available", return_value=True), \
                    patch.object(Path, "exists", return_value=True), patch.object(Path, "read_text", return_value=json.dumps(meta)), \
                    patch.object(Path, "mkdir", side_effect=Stop):
                e.run_upstream(Path("/virtual/run/ckpt_latest.pt"), CFG, None)
        except Stop:
            return "proceeded"
        except RuntimeError as ex:
            return str(ex)
        finally:
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    assert run("mlp_matched", None) == "proceeded"  # reviewer scenario: MLP sidecar hash, nothing rebuilt
    assert run("attention", "trained-hash") == "proceeded"
    assert "sha256 mismatch" in run("attention", "other-hash")
    assert "sha256 mismatch" in run("attention", None)


def _fake_robot_cfg(names):
    ref, _ = ref29_actuator_params(names)
    groups = [types.SimpleNamespace(target_names_expr=(n,), effort_limit=a.effort_limit, stiffness=a.stiffness, damping=a.damping)
              for n, a in zip(names, ref)]
    return types.SimpleNamespace(articulation=types.SimpleNamespace(actuators=tuple(groups))), {n: a.action_scale for n, a in zip(names, ref)}


def test_v2_upstream_actuator_params_and_failures():
    names = list(DEFAULT_NAMES)
    rcfg, scale = _fake_robot_cfg(names)
    got = actuator_params_from_robot_cfg(rcfg, scale, names)
    assert got == ref29_actuator_params(names)[0]
    for bad in (lambda: actuator_params_from_robot_cfg(rcfg, scale, names + ["nope_joint"]),
                lambda: actuator_params_from_robot_cfg(rcfg, {**scale, "left_knee_joint": 0.1, ".*_knee_joint": 0.1}, names),
                lambda: actuator_params_from_robot_cfg(types.SimpleNamespace(), scale, names)):
        try:
            bad()
            raise AssertionError("must raise")
        except RuntimeError:
            pass
    # v2 on the upstream path without the action-scale loader fails loudly (no silent reference-table use)
    import train_entry

    cfg = {"attention": {"morphology": "upstream_mjmodel", "descriptor": "v2"},
           "upstream": {"model_loader": "m:f", "robot_cfg_loader": "r:f"}}
    keys = ("_import_ref", "hinge_joint_names", "default_qpos_from_robot_cfg", "actuator_params_from_robot_cfg")
    saved = {k: getattr(train_entry, k) for k in keys}
    train_entry._import_ref = lambda ref, what: (lambda: None)
    train_entry.hinge_joint_names = lambda model: tuple(names)
    train_entry.default_qpos_from_robot_cfg = lambda c, n: [0.0] * len(n)
    try:
        train_entry.load_morphology(cfg, 29)
        raise AssertionError("missing action_scale_loader must raise")
    except RuntimeError as e:
        assert "action_scale_loader" in str(e)
    finally:
        for k, v in saved.items():
            setattr(train_entry, k, v)


def test_v2_s5_action_scale_match():
    names = list(DEFAULT_NAMES)
    ap, q = ref29_actuator_params(names)
    _, meta = synthetic_morphology_v2(names, q, ap)
    env = (names, [a.action_scale for a in ap], list(q))
    assert action_scale_match(env, meta)[0]
    bad = (names, [a.action_scale * (1 + 1e-4) if i == 3 else a.action_scale for i, a in enumerate(ap)], list(q))
    assert not action_scale_match(bad, meta)[0]
    assert not action_scale_match((names, env[1], [x + 0.01 for x in q]), meta)[0]
    assert not action_scale_match(None, meta)[0] and not action_scale_match(env, None)[0]

    class Term:
        target_names = names
        _scale = torch.tensor([env[1]] * 3)  # (num_envs, J)
        _offset = torch.tensor([env[2]] * 3)

    class Env:
        action_manager = types.SimpleNamespace(_terms={"joint_pos": Term()})

    from train_entry import env_action_scale_offset
    assert action_scale_match(env_action_scale_offset(Env()), meta)[0]

    class Robot:
        joint_names = names

    class FakeEnv(Env):
        scene = {"robot": Robot()}

    class Trainer:
        env = FakeEnv()
        cfg = types.SimpleNamespace(policy_trainer=types.SimpleNamespace(compile="None"))

    lines: list[str] = []
    info = {"default_pose_source": "env_init_state", "joint_names": names, "descriptor_version": "v2", "descriptor_meta": meta}
    SeamProbe(info, "None", emit=lines.append).on_trainer_ready(Trainer())
    assert "[seam] S5 env_action_scale_match=true" in lines
    Term._scale = Term._scale * 1.01
    lines.clear()
    try:
        SeamProbe(info, "None", emit=lines.append).on_trainer_ready(Trainer())
        raise AssertionError("S5 mismatch must raise")
    except RuntimeError:
        assert "[seam] S5 env_action_scale_match=false" in lines


def test_v2_matches_spike_module():
    """Port equality with the spike module (skipped if the spike directory is absent)."""
    if not SPIKE.exists():
        print("SKIP spike equality: spike module absent")
        return
    import importlib.util

    spec = importlib.util.spec_from_file_location("spike_descriptor_v2", SPIKE)
    D = importlib.util.module_from_spec(spec)
    sys.modules["spike_descriptor_v2"] = D
    spec.loader.exec_module(D)
    names = list(DEFAULT_NAMES)
    ap, q = ref29_actuator_params(names)
    sap, sq = D.ref29_actuator_params(names)
    assert [tuple(vars(a).values()) for a in ap] == [tuple(vars(a).values()) for a in sap] and q == sq
    m, meta = synthetic_morphology_v2(names, q, ap)
    sm, smeta = D.synthetic_morphology_v2(names, sq, sap)
    assert torch.equal(m, sm) and meta["sha256"] == smeta["sha256"] and meta == smeta
    sh = list(reversed(names))  # order invariance is part of the ported behaviour
    assert torch.equal(synthetic_morphology_v2(sh)[0], D.synthetic_morphology_v2(sh)[0])
    xml = _owner_xml()
    try:
        import mujoco
    except ImportError:
        print("SKIP spike equality (home humanoid): mujoco not installed")
        return
    if xml is None:
        print("SKIP spike equality (home humanoid): asset missing")
        return
    from attention_policy import hinge_joint_names

    model = mujoco.MjModel.from_xml_path(str(xml))
    hn = hinge_joint_names(model)
    eff = [float(model.jnt_actfrcrange[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, n), 1]) for n in hn]
    inertia = dict(leg=0.01, arm=0.005, head=0.002)
    hm, hmeta = morphology_v2(model, hn, home_default_qpos(hn), home_actuator_params(hn, eff, inertia))
    sm, smeta = D.morphology_v2(model, hn, D.home_default_qpos(hn), D.home_actuator_params(hn, eff, inertia))
    assert torch.equal(hm, sm) and hmeta == smeta
    for ab, sn in (((), False), (("q_def",), True)):
        a, ma = morphology_v2(model, hn, home_default_qpos(hn), home_actuator_params(hn, eff, inertia), scale_norm=sn, ablate=ab)
        b, mb = D.morphology_v2(model, hn, D.home_default_qpos(hn), D.home_actuator_params(hn, eff, inertia), scale_norm=sn, ablate=ab)
        assert torch.equal(a, b) and ma == mb


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
