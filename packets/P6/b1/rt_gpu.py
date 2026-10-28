"""B1-RT GPU-side checks RT-6 (MuJoCo Warp parity + env seams) and the RT-8 transfer-load check.

    SM_BODY_MODULE=sm_body_home python rt_gpu.py rt6 --out meta/rt6.json [--device cuda:0]
    SM_BODY_MODULE=sm_body_home python rt_gpu.py xferload --att <P4 attention ckpt> --mlp <P4 mlp ckpt> \
        --config <b1_home.yaml> --out meta/rt8_xferload.json [--expect-att-sha <hex> --expect-mlp-sha <hex>]

Definitions: spikes/B1-RT/PLAN.md §2 (RT-6, RT-8). Each subcommand prints one ``RT6 ...`` / ``RT8X ...`` line.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import mujoco
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in (ROOT / "code", HERE, ROOT / "spikes" / "B1-RT"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import home_humanoid as H  # noqa: E402

PARITY_TOL_M = 0.01
PARITY_SECONDS = 1.0
SIM_DT, ITERS, LS_ITERS, NCONMAX, NJMAX = 0.005, 10, 20, 35, 250


def rt6(device: str, n_worlds: int = 4) -> dict:
    from mjlab.scene import Scene, SceneCfg
    from mjlab.sim import MujocoCfg, Simulation, SimulationCfg
    from mjlab.terrains import TerrainEntityCfg

    out: dict = {"device": device}
    # (a) parity: identical compiled scene model; MuJoCo Warp (device) vs C MuJoCo (CPU)
    scene = Scene(SceneCfg(terrain=TerrainEntityCfg(terrain_type="plane"), num_envs=n_worlds,
                           entities={"robot": H.get_home_humanoid_robot_cfg()}), device=device)
    model = scene.compile()
    sim = Simulation(num_envs=n_worlds, cfg=SimulationCfg(nconmax=NCONMAX, njmax=NJMAX,
                                                          mujoco=MujocoCfg(timestep=SIM_DT, iterations=ITERS, ls_iterations=LS_ITERS)),
                     model=model, device=device)
    m = sim.mj_model  # options applied
    key = m.key_qpos[0].copy() if m.nkey else None
    assert key is not None, "scene model has no keyframe"
    q0 = torch.as_tensor(key, dtype=torch.float32, device=device)
    ctrl = torch.as_tensor(H.default_joint_pos(), dtype=torch.float32, device=device)
    sim.data.qpos[:] = q0.expand(n_worlds, -1)
    sim.data.qvel[:] = 0.0
    sim.data.ctrl[:] = ctrl.expand(n_worlds, -1)
    sim.forward()
    d = mujoco.MjData(m)
    d.qpos[:] = key
    d.ctrl[:] = H.default_joint_pos()
    mujoco.mj_forward(m, d)
    n_steps = int(round(PARITY_SECONDS / SIM_DT))
    zg, zc = [], []
    for _ in range(n_steps):
        sim.step()
        mujoco.mj_step(m, d)
        zg.append(sim.data.qpos[:, 2].detach().cpu().numpy().copy())
        zc.append(float(d.qpos[2]))
    zg = np.stack(zg)  # (T, W)
    zc = np.asarray(zc)
    err = np.abs(zg - zc[:, None])
    out["parity"] = {"steps": n_steps, "dt": SIM_DT, "max_abs_dz_m": float(err.max()), "final_z_gpu": zg[-1].tolist(),
                     "final_z_cpu": float(zc[-1]), "finite": bool(np.isfinite(zg).all() and np.isfinite(zc).all()),
                     "worlds": n_worlds, "tol_m": PARITY_TOL_M, "model_nu": int(m.nu), "model_opt_timestep": float(m.opt.timestep),
                     "integrator": int(m.opt.integrator)}
    out["parity"]["pass"] = bool(out["parity"]["finite"] and out["parity"]["max_abs_dz_m"] <= PARITY_TOL_M)
    # (b) env seams on the GPU tracking env (S1 order, S2 obs layout, S5 action scale), via the frozen probe helpers
    import train_entry as TE
    from attention_policy import hinge_joint_names
    from descriptor_v2 import actuator_params_from_robot_cfg, morphology_v2
    from supermimic.envs import SuperMimicEnvCfgArgs, make_env
    from supermimic.envs.mdp.motion_library import discover_npz

    npz_dir = Path("data/npz/b1_home")
    files = [str(f) for f in discover_npz(npz_dir)]
    env = make_env(SuperMimicEnvCfgArgs(npz_files=files, num_envs=16, record_transitions=True, anchor_obs=True, seed=0), device=device)
    try:
        owner = mujoco.MjModel.from_xml_path(str(H.asset_xml()))
        names = hinge_joint_names(owner)
        params = actuator_params_from_robot_cfg(H.get_home_humanoid_robot_cfg(), H.HOME_HUMANOID_ACTION_SCALE, names)
        _, meta = morphology_v2(owner, names, H.default_joint_pos(), params)
        s1, s1d = TE.joint_order_match(meta["names"], TE.entity_joint_names(env), TE.action_joint_names(env))
        dims, tnames = TE.policy_term_dims(env), TE.policy_term_names(env)
        obs, _ = env.reset()
        s2, s2d = TE.obs_layout_check(int(obs["policy"].shape[-1]), dims, H.NUM_JOINTS, 10, tnames)
        s5, s5d = TE.action_scale_match(TE.env_action_scale_offset(env), meta)
        out["seams"] = {"S1": TE._tri(s1), "S1_detail": s1d, "S2": TE._tri(s2), "S2_detail": s2d,
                        "obs_policy_dim": int(obs["policy"].shape[-1]), "goal_dim": int(obs["goal"].shape[-1]),
                        "S5": bool(s5), "S5_detail": s5d}
        out["seams"]["pass"] = bool(s1 is True and s2 is True and s5)
    finally:
        env.close()
    out["pass"] = bool(out["parity"]["pass"] and out["seams"]["pass"])
    return out


def xferload(att_ckpt: str, mlp_ckpt: str, cfg_path: str, expect: dict | None = None) -> dict:
    import train_entry as TE
    import transfer as XF
    from p6_entry import NUM_JOINTS, build_decoder22

    cfg = TE.load_config(cfg_path)
    morph = TE.load_morphology(cfg, NUM_JOINTS, {})
    out: dict = {}
    torch.manual_seed(0)
    z = torch.tanh(torch.randn(8, 32))
    obs = torch.randn(8, 10 * (3 * NUM_JOINTS + 6))
    for arm, ck in (("attention", att_ckpt), ("mlp_matched", mlp_ckpt)):
        rec = {"ckpt": ck, "sha256": XF.file_sha256(ck)}
        try:
            sd = XF.p4_decoder_state(ck)
            dec = build_decoder22(arm, cfg, morph if arm == "attention" else None, "xfer", sd, 32)
            rep = XF.init_attention(dec, sd) if arm == "attention" else XF.init_mlp_mapped(dec, sd)
            a = dec(z, obs)
            rec.update(report=rep, out_shape=list(a.shape), finite=bool(torch.isfinite(a).all()), error=None)
            ok = tuple(a.shape) == (8, NUM_JOINTS) and rec["finite"]
            if expect and expect.get(arm):  # PLAN RT-8 (b): sha256 = the P5-verified identity
                rec["expected_sha256"] = expect[arm]
                ok = ok and rec["sha256"] == expect[arm]
            if arm == "mlp_matched":
                ok = ok and rep["output_rows_mapped"] == 20 and rep["fresh_joints"] == ["head_yaw_joint", "head_pitch_joint"]
            rec["pass"] = bool(ok)
        except Exception as e:  # noqa: BLE001  (a load failure is the measured outcome)
            rec.update(error=repr(e), pass_=False)
            rec["pass"] = False
        out[arm] = rec
    out["pass"] = bool(out["attention"]["pass"] and out["mlp_matched"]["pass"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a6 = sub.add_parser("rt6")
    a6.add_argument("--out", required=True)
    a6.add_argument("--device", default="cuda:0")
    ax = sub.add_parser("xferload")
    ax.add_argument("--att", required=True)
    ax.add_argument("--mlp", required=True)
    ax.add_argument("--config", required=True)
    ax.add_argument("--out", required=True)
    ax.add_argument("--expect-att-sha", default=None)
    ax.add_argument("--expect-mlp-sha", default=None)
    a = ap.parse_args()
    if a.cmd == "rt6":
        res = rt6(a.device)
        Path(a.out).write_text(json.dumps(res, indent=2, default=float))
        print(f"RT6 pass={res['pass']} max_abs_dz_m={res['parity']['max_abs_dz_m']:.6f} S1={res['seams']['S1']} "
              f"S2={res['seams']['S2']} S5={res['seams']['S5']}", flush=True)
    else:
        res = xferload(a.att, a.mlp, a.config, {"attention": a.expect_att_sha, "mlp_matched": a.expect_mlp_sha})
        Path(a.out).write_text(json.dumps(res, indent=2, default=float))
        print(f"RT8X pass={res['pass']} attention={res['attention']['pass']} mlp_matched={res['mlp_matched']['pass']}", flush=True)


if __name__ == "__main__":
    main()
