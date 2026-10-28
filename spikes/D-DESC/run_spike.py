"""D-DESC spike harness. Run from program root: .venv/bin/python -B spikes/D-DESC/run_spike.py"""
import datetime, glob, hashlib, json, sys, time, warnings
from pathlib import Path

import mujoco
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import descriptor_v2 as D  # noqa: E402
from attention_policy import hinge_joint_names, morphology_from_mjmodel  # noqa: E402

ROOT = D.ROOT
SEED = 0
V1_PARAMS = 463489
INERTIA = dict(leg=0.01, arm=0.005, head=0.002)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def s4_hashes(xml):
    h = {"xml": sha(xml)}
    man = json.load(open(ROOT / "assets/home_humanoid_mjcf/mesh_manifest.json"))
    for e in man:
        h[e["name"]] = sha(ROOT / "assets/home_humanoid_mjcf/meshes" / e["name"])
    return h, man


def home_inputs(model, scale=1.0):
    names = hinge_joint_names(model)
    jid = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, n) for n in names]
    eff = [float(model.jnt_actfrcrange[j, 1]) * scale ** 4 for j in jid]
    ap = D.home_actuator_params(names, eff, INERTIA)
    if scale != 1.0:  # sigma fixed => kp = 0.25 tau / sigma0 (keeps the consistency check quiet)
        base = D.home_actuator_params(names, [float(model.jnt_actfrcrange[j, 1]) for j in jid], INERTIA)
        ap = [D.ActuatorParams(a.effort_limit, 0.25 * a.effort_limit / b.action_scale, a.damping, b.action_scale)
              for a, b in zip(ap, base)]
    return names, D.home_default_qpos(names), ap


def scaled(path, s):
    m = mujoco.MjModel.from_xml_path(str(path))
    for f in ("body_pos", "body_ipos", "jnt_pos", "geom_pos", "geom_size"):
        getattr(m, f)[:] *= s
    m.body_mass[:] *= s ** 3
    m.body_inertia[:] *= s ** 5
    return m


def main():
    torch.manual_seed(SEED)
    V = {}
    R = {}
    xml = glob.glob(str(ROOT / "assets/home_humanoid_mjcf/*.xml"))
    assert len(xml) == 1
    xml = xml[0]
    h_before, manifest = s4_hashes(xml)
    model = mujoco.MjModel.from_xml_path(xml)
    names, qd, ap = home_inputs(model)
    J_h = len(names)
    assert J_h == 22, J_h
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        home, hmeta = D.morphology_v2(model, names, qd, ap)
    assert not w, [str(x.message) for x in w]
    ref_names = D.DEFAULT_JOINT_NAMES
    ref_ap, ref_q = D.ref29_actuator_params(ref_names)
    ref, rmeta = D.synthetic_morphology_v2(ref_names, ref_q, ref_ap)

    # S-1
    def distinct(x):
        return len({tuple(r) for r in np.round(x.numpy(), 5)})
    V["S-1"] = bool(torch.isfinite(home).all() and torch.isfinite(ref).all()
                    and distinct(home) == J_h and distinct(ref) == 29)
    R["S-1"] = dict(home=[J_h, distinct(home)], ref=[29, distinct(ref)])

    # S-2 / S-3
    errs = []
    for desc, J in ((home, J_h), (ref, 29)):
        cfg = D.AttentionDecoderCfg(num_joints=J, morph_dim=16)
        dec = D.AttentionDecoder(cfg, desc).eval()
        z = torch.randn(8, cfg.latent_dim)
        obs = torch.randn(8, cfg.history * (3 * J + 6))
        with torch.no_grad():
            a = dec(z, obs)
            for _ in range(8):
                perm = torch.randperm(J)
                b = dec(z, D.permute_obs_history(obs, perm, J, cfg.history), morphology=desc[perm])
                errs.append(float((b - a[:, perm]).norm() / (a.norm() + 1e-12)))
    V["S-2"] = max(errs) < 1e-4
    R["S-2"] = max(errs)
    n_v1 = D.count_params(D.AttentionDecoder(D.AttentionDecoderCfg()))
    n_v2 = D.count_params(D.AttentionDecoder(D.AttentionDecoderCfg(morph_dim=16), ref))
    mlp = D.build_matched_mlp(n_v2)
    n_mlp = D.count_params(mlp)
    R["S-3"] = dict(v1_actual=n_v1, v1_plan=V1_PARAMS, v2=n_v2, change=(n_v2 - V1_PARAMS) / V1_PARAMS,
                    mlp=n_mlp, mlp_hidden=list(mlp.cfg.hidden), mlp_match=(n_mlp - n_v2) / n_v2)
    V["S-3"] = bool(abs(R["S-3"]["change"]) <= 0.05 and abs(R["S-3"]["mlp_match"]) <= 0.05)

    # F1
    groups = {}
    ok = True
    for exprs, e, a in D._REF_GROUPS:
        pass
    import re
    cnt = []
    for n in ref_names:
        m = sum(1 for exprs, e, a in D._REF_GROUPS for x in exprs if re.fullmatch(x, n))
        cnt.append(m)
    sig = {}
    for a in ref_ap:
        sig[round(a.action_scale, 4)] = sig.get(round(a.action_scale, 4), 0) + 1
    exp = {0.0745: 4, 0.3507: 4, 0.4386: 16, 0.5475: 5}
    ok = all(c == 1 for c in cnt) and len(ref_ap) == 29
    got = sorted((a.action_scale for a in ref_ap))
    for s_, c_ in exp.items():
        ok &= sum(1 for a in ref_ap if abs(a.action_scale - s_) <= 1e-3) == c_
    V["F1"] = bool(ok)
    R["F1"] = dict(match_counts_all_one=all(c == 1 for c in cnt), sigma_counts=sig)

    # F2
    dmax = {}
    for s in (0.5, 2.0):
        ms = scaled(xml, s)
        nm, q2, ap2 = home_inputs(ms, s)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            d2, _ = D.morphology_v2(ms, nm, q2, ap2)
        dmax[s] = float((d2 - home).abs().max())
        if w:
            R.setdefault("F2_warnings", []).append(str(w[0].message))
    V["F2"] = all(v < 1e-5 for v in dmax.values())
    R["F2"] = {str(k): v for k, v in dmax.items()}

    # F3
    idx = {n: i for i, n in enumerate(names)}
    f3 = 0.0
    f3_rng = 0.0
    pairs = 0
    for n, i in idx.items():
        if not n.startswith("l_"):
            continue
        k = idx["r_" + n[2:]]
        left, right = home[i].numpy().astype(float), home[k].numpy().astype(float)
        exp_r = left.copy()
        exp_r[1] = -left[1]
        exp_r[10] = -left[10]
        axis = np.abs(left[3:6])
        if axis.argmax() != 1:  # x/z-axis joint: rotation sense flips under the y-mirror
            exp_r[6] = -left[6]
            exp_r[7], exp_r[8] = -left[8], -left[7]
        diff = np.abs(exp_r - right)
        f3_rng = max(f3_rng, diff[[7, 8]].max())
        f3 = max(f3, np.delete(diff, [7, 8]).max())
        pairs += 1
    V["F3"] = bool(f3 < 1e-4 and f3_rng < 1e-3)
    R["F3"] = dict(pairs=pairs, max_other=f3, max_range=f3_rng)

    # F4
    ref_ls, ref_lt = ref[:, 14].numpy(), ref[:, 15].numpy()
    ln2 = float(np.log(2))
    hs, ht = home[:, 14].numpy(), home[:, 15].numpy()
    V["F4"] = bool(hs.min() >= ref_ls.min() - ln2 and hs.max() <= ref_ls.max() + ln2
                   and ht.min() >= ref_lt.min() - ln2 and ht.max() <= ref_lt.max() + ln2)
    R["F4"] = dict(ref_log_sigma=[float(ref_ls.min()), float(ref_ls.max())], home_log_sigma=[float(hs.min()), float(hs.max())],
                   ref_log_tau=[float(ref_lt.min()), float(ref_lt.max())], home_log_tau=[float(ht.min()), float(ht.max())])

    # T-1
    perm = torch.randperm(29).tolist()
    pn = [ref_names[i] for i in perm]
    p_ap = [ref_ap[i] for i in perm]
    p_q = [ref_q[i] for i in perm]
    pd, _ = D.synthetic_morphology_v2(pn, p_q, p_ap)
    t1 = float((pd - ref[perm]).abs().max())
    pd0, _ = D.synthetic_morphology_v2(pn)
    od0, _ = D.synthetic_morphology_v2(ref_names)
    t1b = float((pd0 - od0[perm]).abs().max())
    V["T-1"] = bool(t1 == 0.0 and t1b == 0.0)
    R["T-1"] = dict(with_params=t1, no_params=t1b)

    # T-2
    t2 = True
    keys = ("scale_norm", "ablate", "matrix", "sha256")
    try:
        hn, mh = D.morphology_v2(model, names, qd, ap, scale_norm=False)
        rn, mr = D.synthetic_morphology_v2(ref_names, ref_q, ref_ap, scale_norm=False)
        t2 = all(k in m for m in (mh, mr, hmeta, rmeta) for k in keys)
        t2 &= (mh["scale_norm"] is False) and mh["L"] == hmeta["L"]
        t2 &= (hn[:, 15] == home[:, 15]).all().item() and (hn[:, :3] != home[:, :3]).any().item()
        t2 &= hashlib.sha256(np.array(mh["matrix"], dtype=np.float32).tobytes()).hexdigest() == mh["sha256"]
        R["T-2"] = dict(home_absmax=float(hn.abs().max()), ref_absmax=float(rn.abs().max()))
    except AssertionError as e:
        t2 = False
        R["T-2"] = str(e)
    V["T-2"] = bool(t2)

    # S-4
    h_after, _ = s4_hashes(xml)
    man_ok = all(h_before[e["name"]] == e["sha256"] for e in manifest)
    V["S-4"] = bool(h_before == h_after and len(manifest) == 27)
    R["S-4"] = dict(n_meshes=len(manifest), manifest_matches=man_ok, xml_sha256=h_before["xml"])

    # R-1
    rep = {}
    d1 = morphology_from_mjmodel(model, names, qd)
    k = names.index("l_calf_joint")
    rep["left_knee_v1"] = d1[k].tolist()
    rep["left_knee_v2"] = home[k].tolist()
    rep["v2_min_max"] = {"home": [home.min(0).values.tolist(), home.max(0).values.tolist()],
                         "ref29": [ref.min(0).values.tolist(), ref.max(0).values.tolist()]}
    z = torch.randn(512, 32)
    obs = torch.randn(512, 10 * (3 * 29 + 6))
    ref_v1 = D.synthetic_morphology_v2 and __import__("attention_policy").synthetic_morphology()
    for tag, md, mm in (("v1", 12, ref_v1), ("v2", 16, ref)):
        dec = D.AttentionDecoder(D.AttentionDecoderCfg(morph_dim=md), mm)
        dec(z, obs).sum().backward()
        t0 = time.perf_counter()
        for _ in range(5):
            dec.zero_grad()
            dec(z, obs).sum().backward()
        rep[f"fwd_bwd_s_{tag}"] = (time.perf_counter() - t0) / 5
    R["R-1"] = rep

    binding = ["S-1", "S-2", "S-3", "S-4", "F1", "F2", "F3", "F4", "T-1", "T-2"]
    verdict = {k: V[k] for k in binding}
    verdict["pass"] = all(V[k] for k in binding)
    line = "SPIKE_VERDICT " + json.dumps(verdict)
    json.dump(dict(verdict=verdict, details=R, seed=SEED), open(HERE / "results.json", "w"), indent=1)
    print(json.dumps(R, indent=1))
    print(line)
    with open(HERE / "runs.log", "a") as f:
        f.write(f"{datetime.datetime.now(datetime.timezone.utc).isoformat()} | .venv/bin/python -B spikes/D-DESC/run_spike.py"
                f" | descriptor_v2.py={sha(HERE/'descriptor_v2.py')} run_spike.py={sha(HERE/'run_spike.py')} | seed={SEED} | {line}\n")


if __name__ == "__main__":
    main()
