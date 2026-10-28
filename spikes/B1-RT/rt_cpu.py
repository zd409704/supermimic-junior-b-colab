"""B1-RT CPU harness: RT-1..RT-5 (spikes/B1-RT/PLAN.md §2; SCHEME_PLAN §5). Machine verdict on stdout.

Run from the program root (research box, P6 CPU env)::

    WARP_CACHE_PATH=packets/P6/cpuenv/warp-cache packets/P6/cpuenv/.venv/bin/python -B spikes/B1-RT/rt_cpu.py \
        --attempt N [--clips-from hf|none]

Writes ``spikes/B1-RT/results-cpu-attemptN.json`` and appends one line per check to ``spikes/B1-RT/runs.log``.
Motion clips are fetched into process memory only (brief A1.1-7); nothing derived from them is written except the
aggregate numbers in the results file.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "code"))
import home_humanoid as H  # noqa: E402
import retarget_rta as R  # noqa: E402

DATASET = "lvhaidong/LAFAN1_Retargeting_Dataset"
HF = os.environ.get("HF_ENDPOINT", "https://huggingface.co").rstrip("/")
SUBDIR = "g1"
# PLAN §3: four clip slots (the P4 clips) and one pre-declared replacement each.
SLOTS = [("walk", "walk1_subject1", "walk1_subject2"), ("run", "run1_subject2", "run1_subject5"),
         ("dance", "dance1_subject1", "dance1_subject2"), ("jump", "jumps1_subject1", "jumps1_subject2")]
SIM_DT, DECIM, ITERS, LS_ITERS = 0.005, 4, 10, 20
CTRL_DT = SIM_DT * DECIM

# thresholds (SCHEME_PLAN §5, frozen in PLAN §2)
RT3_DROP, RT3_TILT, RT3_SETTLE_S, RT3_WINDOW_S = 0.03, 0.10, 0.5, 2.0
RT4_CLIP_EPS, RT4_CLIP_FRAC, RT4_PEN_P95, RT4_SKATE_P95, RT4_H_LO, RT4_H_HI = 0.05, 0.10, 0.01, 0.10, 0.6, 1.1
RT4_STANCE_Z = 0.02


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def code_hash() -> dict:
    return {p: sha(HERE / p) for p in ("rt_cpu.py", "home_humanoid.py", "retarget_rta.py", "supermimic_compat.py")}


def sim_opts(m: mujoco.MjModel) -> mujoco.MjModel:
    m.opt.timestep, m.opt.iterations, m.opt.ls_iterations = SIM_DT, ITERS, LS_ITERS
    return m


def rpy(q):
    w, x, y, z = q
    roll = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x))))
    return roll, pitch


def feet_in_contact(m, d) -> set[str]:
    out = set()
    for c in d.contact[: d.ncon]:
        for g in (c.geom1, c.geom2):
            n = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, g) or ""
            if re.fullmatch(H.FOOT_GEOM_REGEX, n):
                out.add(n[0])
    return out


# ---------------------------------------------------------------------------------------------- RT-1
def rt1(h_before: dict) -> dict:
    m = H.load_overlaid_model()
    owner = mujoco.MjModel.from_xml_path(str(H.asset_xml()))
    nfree = int(sum(owner.jnt_type == mujoco.mjtJoint.mjJNT_FREE))
    nhinge = int(sum(owner.jnt_type == mujoco.mjtJoint.mjJNT_HINGE))
    out = {"compiles": True, "n_free": nfree, "n_hinge": nhinge, "nbody": int(owner.nbody),
           "hashes_before_ok": h_before["ok"], "xml_sha256": h_before["xml_sha256"],
           "n_mesh_hashed": h_before["n_manifest"], "mesh_mismatch": h_before["mesh_mismatch"],
           "overlaid_nbody": int(m.nbody), "standing_root_height": H.standing_root_height(),
           "height_ratio_as5": H.height_ratio()}
    out["pass_pre"] = bool(nfree == 1 and nhinge == 22 and owner.nbody == 28 and m.nbody == 28 and h_before["ok"])
    return out


# ---------------------------------------------------------------------------------------------- RT-2
def rt2() -> dict:
    from attention_policy import hinge_joint_names
    from descriptor_v2 import actuator_params_from_robot_cfg, morphology_v2
    from mjlab.entity import Entity
    from mjlab.scene import Scene, SceneCfg
    from mjlab.terrains import TerrainEntityCfg

    out = {}
    m = H.load_overlaid_model()
    owner = mujoco.MjModel.from_xml_path(str(H.asset_xml()))
    tr = tuple(mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, m.actuator_trnid[i, 0]) for i in range(m.nu))
    pos_act = all(m.actuator_biastype[i] == mujoco.mjtBias.mjBIAS_AFFINE and m.actuator_gaintype[i] == mujoco.mjtGain.mjGAIN_FIXED
                  for i in range(m.nu))
    fr_ok = all(np.allclose(m.actuator_forcerange[i], owner.jnt_actfrcrange[owner.joint(n).id]) for i, n in enumerate(tr))
    out["cpu"] = {"nu": int(m.nu), "one_position_actuator_per_hinge": bool(pos_act and len(set(tr)) == 22),
                  "forcerange_eq_actuatorfrcrange": bool(fr_ok)}
    # mjlab path: entity + scene with the scene's own terrain
    ent = Entity(H.get_home_humanoid_robot_cfg())
    em = ent.spec.compile()
    etr = tuple(mujoco.mj_id2name(em, mujoco.mjtObj.mjOBJ_JOINT, em.actuator_trnid[i, 0]) for i in range(em.nu))
    fr_e = all(np.allclose(em.actuator_forcerange[i], owner.jnt_actfrcrange[owner.joint(n).id]) for i, n in enumerate(etr))
    scene = Scene(SceneCfg(terrain=TerrainEntityCfg(terrain_type="plane"), num_envs=1,
                           entities={"robot": H.get_home_humanoid_robot_cfg()}), device="cpu")
    sm = scene.compile()
    planes = [g for g in range(sm.ngeom) if sm.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE]
    robot_planes = [g for g in planes if (mujoco.mj_id2name(sm, mujoco.mjtObj.mjOBJ_BODY, sm.geom_bodyid[g]) or "").startswith("robot/")
                    or (mujoco.mj_id2name(sm, mujoco.mjtObj.mjOBJ_GEOM, g) or "").startswith("robot/")]
    out["mjlab"] = {"nu": int(em.nu), "forcerange_eq_actuatorfrcrange": bool(fr_e), "scene_planes": len(planes),
                    "robot_planes": len(robot_planes), "entity_joint_names": list(ent.joint_names)}
    # self-contacts at the default pose (CPU overlaid model and mjlab scene model)
    d = mujoco.MjData(m)
    mujoco.mj_resetDataKeyframe(m, d, m.key("home").id)
    mujoco.mj_forward(m, d)
    fl = m.geom("scene_floor").id
    self_cpu = sum(1 for c in d.contact[: d.ncon] if fl not in (c.geom1, c.geom2))
    sd = mujoco.MjData(sm)
    mujoco.mj_resetDataKeyframe(sm, sd, 0) if sm.nkey else None
    mujoco.mj_forward(sm, sd)
    floor_geoms = set(planes)
    self_mj = sum(1 for c in sd.contact[: sd.ncon] if not ({c.geom1, c.geom2} & floor_geoms))
    out["self_contacts_default_pose"] = {"cpu": int(self_cpu), "mjlab_scene": int(self_mj), "mjlab_nkey": int(sm.nkey)}
    # order: actuator == hinge == descriptor rows (S1 for body 2)
    names = hinge_joint_names(owner)
    params = actuator_params_from_robot_cfg(H.get_home_humanoid_robot_cfg(), H.HOME_HUMANOID_ACTION_SCALE, names)
    morph, meta = morphology_v2(owner, names, H.default_joint_pos(), params)
    out["order"] = {"hinge": list(names) == list(H.JOINT_NAMES), "cpu_actuator": list(tr) == list(names),
                    "mjlab_actuator": list(etr) == list(names), "mjlab_entity_joints": list(ent.joint_names) == list(names),
                    "descriptor_rows": list(meta["names"]) == list(names), "descriptor_shape": list(morph.shape),
                    "descriptor_finite": bool(np.isfinite(morph.numpy()).all())}
    out["pass"] = bool(
        out["cpu"]["nu"] == 22 and out["cpu"]["one_position_actuator_per_hinge"] and out["cpu"]["forcerange_eq_actuatorfrcrange"]
        and out["mjlab"]["nu"] == 22 and out["mjlab"]["forcerange_eq_actuatorfrcrange"]
        and out["mjlab"]["scene_planes"] == 1 and out["mjlab"]["robot_planes"] == 0
        and self_cpu == 0 and self_mj == 0 and all(v for k, v in out["order"].items() if isinstance(v, bool)))
    return out


# ---------------------------------------------------------------------------------------------- RT-3
def stand(kp_scale: float) -> dict:
    m = sim_opts(H.load_overlaid_model(kp_scale=kp_scale))
    d = mujoco.MjData(m)
    mujoco.mj_resetDataKeyframe(m, d, m.key("home").id)
    d.ctrl[:] = H.default_joint_pos()
    for _ in range(int(round(RT3_SETTLE_S / SIM_DT))):
        mujoco.mj_step(m, d)
    z0 = float(d.qpos[2])
    max_tilt = 0.0
    for _ in range(int(round(RT3_WINDOW_S / SIM_DT))):
        mujoco.mj_step(m, d)
        r, p = rpy(d.qpos[3:7])
        max_tilt = max(max_tilt, abs(r), abs(p))
    r, p = rpy(d.qpos[3:7])
    feet = feet_in_contact(m, d)
    finite = bool(np.isfinite(d.qpos).all() and np.isfinite(d.qvel).all())
    res = {"kp_scale": kp_scale, "z_start": z0, "drop": z0 - float(d.qpos[2]), "roll_end": r, "pitch_end": p,
           "max_abs_tilt": max_tilt, "feet_in_contact_end": sorted(feet), "finite": finite}
    res["stand_ok"] = bool(finite and res["drop"] < RT3_DROP and max_tilt < RT3_TILT and feet == {"l", "r"})
    return res


def rt3() -> dict:
    runs = {str(k): stand(k) for k in (1.0, 0.5, 1.5)}
    return {"runs": runs, "pass": bool(runs["1.0"]["stand_ok"] and all(r["finite"] for r in runs.values()))}


# ---------------------------------------------------------------------------------------------- clips
def dataset_revision() -> str | None:
    try:
        with urllib.request.urlopen(f"{HF}/api/datasets/{DATASET}", timeout=60) as r:
            return json.load(r).get("sha")
    except Exception as e:  # noqa: BLE001
        return f"unavailable: {e!r}"


# Fix #2 (orch/owner-decisions/20261027-0752-AsiaShanghai-p6-lafan1-fetch-fix.md, sha256 768d6a0a…): the box
# CSV sha256 of the slot_rule=first clips (results-cpu-attempt1.json); any source must reproduce these bytes.
CSV_PINS = {"walk1_subject1": "68c7887438e94f1f3d9ebacd3a8ce59251a22c7b05129a0f5d7cacaedc48c28d",
            "run1_subject2": "ec02af4447a62214a6fec6afff60c75d0ecc8f80f8fb45e3cd4119fed9ceac8d",
            "dance1_subject1": "e2a369e92e5ad076c5acffff7bce53157a0e6cd9e7e9f6a08dadfb1eb2928d8f",
            "jumps1_subject1": "3f55c1a0f87564044a71817d62dc2a40aa76332aa1cab3f1c817333a197c78c2"}
# Read-only local copies (the P4 tree on xn-4090); $LAFAN1_G1_DIR (os.pathsep-separated) is tried first.
LAFAN1_G1_DEFAULTS = ("/content/SuperMimic-Reproduced/data/raw/lafan1/g1",
                      "/data/muchuan/p4-b0-attempt1/workdir/SuperMimic-Reproduced/data/raw/lafan1/g1")


def _clip_bytes(name: str, rev: str) -> tuple[bytes, str]:
    """Bytes of ``{SUBDIR}/{name}.csv``: local dir, else huggingface_hub, else the urllib resolve URL."""
    env = [d for d in os.environ.get("LAFAN1_G1_DIR", "").split(os.pathsep) if d]
    for d in (*env, *LAFAN1_G1_DEFAULTS):
        p = Path(d) / f"{name}.csv"
        if p.is_file():
            return p.read_bytes(), f"local:{p}"  # read only; the tree is never written
    errs = []
    try:
        import tempfile

        from huggingface_hub import hf_hub_download
        with tempfile.TemporaryDirectory(prefix="lafan1-") as tmp:  # removed on exit: nothing persists on disk
            f = hf_hub_download(DATASET, f"{SUBDIR}/{name}.csv", repo_type="dataset", revision=rev, cache_dir=tmp,
                                endpoint=HF)
            return Path(f).read_bytes(), f"hf_hub:{HF}@{rev}"
    except Exception as e:  # noqa: BLE001
        errs.append(f"hf_hub: {e!r}")
    url = f"{HF}/datasets/{DATASET}/resolve/{rev}/{SUBDIR}/{name}.csv"
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            return r.read(), f"urllib:{url}"
    except Exception as e:
        raise RuntimeError(f"fetch_clip {name}: no local copy; {'; '.join(errs)}; urllib: {e!r}") from e


def fetch_clip(name: str, rev: str, pin: str | None = None) -> tuple[np.ndarray, str]:
    data, src = _clip_bytes(name, rev)  # in memory only (X-002)
    h = hashlib.sha256(data).hexdigest()
    want = pin or CSV_PINS.get(name)
    print(f"FETCH_CLIP name={name} src={src} sha256={h} pin={want or '-'}", file=sys.stderr, flush=True)
    if want and h != want:
        raise ValueError(f"fetch_clip {name}: sha256 {h} != pin {want} (src {src})")
    return R.parse_csv_bytes(data), h


def foot_body_states(hm: mujoco.MjModel, qpos: np.ndarray):
    """Per frame: lowest sole z per foot and foot (ankle roll body) xy."""
    d = mujoco.MjData(hm)
    T = qpos.shape[0]
    z = np.empty((T, 2))
    xy = np.empty((T, 2, 2))
    geoms = {s: [g for g in range(hm.ngeom) if re.fullmatch(rf"^{s}_foot[1-4]_collision$", mujoco.mj_id2name(hm, mujoco.mjtObj.mjOBJ_GEOM, g) or "")]
             for s in ("l", "r")}
    bodies = [hm.body("l_ankle_roll_link").id, hm.body("r_ankle_roll_link").id]
    for t in range(T):
        d.qpos[:] = qpos[t]
        mujoco.mj_kinematics(hm, d)
        for k, s in enumerate(("l", "r")):
            zz = []
            for g in geoms[s]:
                rr, half = hm.geom_size[g, 0], hm.geom_size[g, 1]
                ax = d.geom_xmat[g].reshape(3, 3)[:, 2]
                c = d.geom_xpos[g]
                zz.append(min(c[2] + half * ax[2], c[2] - half * ax[2]) - rr)
            z[t, k] = min(zz)
            xy[t, k] = d.xpos[bodies[k], :2]
    return z, xy


def clip_qa(raw: np.ndarray, ctx: R.RetargetCtx) -> tuple[dict, object]:
    rt = R.retarget_raw(raw, ctx)
    mot = R.to_motion(rt["raw"])  # 50 fps
    T = mot.num_frames
    qpos = np.concatenate([mot.root_pos, mot.root_quat, mot.joint_pos], axis=1)
    # clipping, evaluated on the 30 fps input frames (where the map acts)
    over = np.maximum(rt["q_unclipped"] - ctx.hi, 0) + np.maximum(ctx.lo - rt["q_unclipped"], 0)
    clip_frac = float(np.mean(over.max(axis=1) > RT4_CLIP_EPS))
    worst = {H.JOINT_NAMES[j]: float(np.mean(over[:, j] > RT4_CLIP_EPS)) for j in range(H.NUM_JOINTS) if np.any(over[:, j] > RT4_CLIP_EPS)}
    z, xy = foot_body_states(ctx.hm, qpos)
    pen = np.maximum(-z.min(axis=1), 0.0)
    pen_p95 = float(np.percentile(pen, 95))
    vel = np.zeros((T, 2))
    vel[1:] = np.linalg.norm(np.diff(xy, axis=0), axis=-1) / (1.0 / R.OUTPUT_FPS)
    vel[0] = vel[1]
    stance = z.argmin(axis=1)
    has = z.min(axis=1) < RT4_STANCE_Z
    sk = vel[np.arange(T), stance][has]
    skate_p95 = float(np.percentile(sk, 95)) if sk.size else float("nan")
    h0 = H.standing_root_height()
    rh = mot.root_pos[:, 2] / h0
    p5, p95 = float(np.percentile(rh, 5)), float(np.percentile(rh, 95))
    res = {"frames_50fps": int(T), "z_offset": rt["z_offset"], "clip_frac": clip_frac, "clip_by_joint": worst,
           "penetration_p95_m": pen_p95, "skate_p95_mps": skate_p95, "stance_frames": int(has.sum()),
           "root_height_ratio_p5": p5, "root_height_ratio_p95": p95}
    res["checks"] = {"clip": clip_frac <= RT4_CLIP_FRAC, "penetration": pen_p95 <= RT4_PEN_P95,
                     "skate": bool(skate_p95 <= RT4_SKATE_P95), "root_height": bool(p5 >= RT4_H_LO and p95 <= RT4_H_HI)}
    res["pass"] = bool(all(res["checks"].values()))
    return res, mot


# ---------------------------------------------------------------------------------------------- RT-5
def replay_probe(mot) -> dict:
    m = sim_opts(H.load_overlaid_model())
    d = mujoco.MjData(m)
    T = mot.num_frames
    d.qpos[0:3], d.qpos[3:7], d.qpos[7:] = mot.root_pos[0], mot.root_quat[0], mot.joint_pos[0]
    d.qvel[6:] = mot.joint_vel[0]
    d.qvel[0:3] = mot.root_lin_vel_w[0]
    mujoco.mj_forward(m, d)
    thr = H.termination_height_threshold()
    g = np.array([0.0, 0.0, -1.0])
    t_fall, finite = None, True
    for t in range(1, T):
        d.ctrl[:] = mot.joint_pos[t]
        for _ in range(DECIM):
            mujoco.mj_step(m, d)
        if not (np.isfinite(d.qpos).all() and np.isfinite(d.qvel).all()):
            finite = False
            break
        q_ref = mot.root_quat[t]
        def grav_b(q):
            w, x, y, z = q
            Rm = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                           [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                           [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])
            return Rm.T @ g
        tilt = abs(grav_b(q_ref)[2] - grav_b(d.qpos[3:7])[2])
        if abs(mot.root_pos[t, 2] - d.qpos[2]) > thr or tilt > 0.8:
            t_fall = t * CTRL_DT
            break
    return {"time_to_fall_s": t_fall, "clip_s": (T - 1) * CTRL_DT, "survived": t_fall is None, "finite": finite}


# ---------------------------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--attempt", type=int, required=True)
    ap.add_argument("--clips-from", choices=("hf", "none"), default="hf")
    a = ap.parse_args()
    t0 = time.time()
    out_path = HERE / f"results-cpu-attempt{a.attempt}.json"
    if out_path.exists():
        sys.exit(f"{out_path} exists (one file per attempt; never overwrite)")
    res = {"harness": "spikes/B1-RT/rt_cpu.py", "attempt": a.attempt, "start_utc": utc(), "code_sha256": code_hash(),
           "mujoco": mujoco.__version__, "venue": "research box CPU"}
    h_before = H.asset_hashes()
    res["RT-1"] = rt1(h_before)
    res["RT-2"] = rt2()
    res["RT-3"] = rt3()
    ctx = R.make_ctx()
    res["AS-4_sign_check"] = ctx.check
    res["retarget_scale"] = ctx.scale
    if a.clips_from == "hf":
        rev = dataset_revision()
        res["dataset"] = {"repo": DATASET, "subdir": SUBDIR, "revision": rev}
        slots, probes = {}, {}
        for slot, first, repl in SLOTS:
            rec = {"tried": []}
            for name in (first, repl):
                raw, h = fetch_clip(name, rev if rev and not rev.startswith("unavailable") else "main")
                qa, mot = clip_qa(raw, ctx)
                qa.update(clip=name, csv_sha256=h, input_frames=int(raw.shape[0]))
                rec["tried"].append(qa)
                probes[name] = replay_probe(mot)
                del raw, mot
                if qa["pass"]:
                    break
            rec["used"] = rec["tried"][-1]["clip"] if rec["tried"][-1]["pass"] else None
            rec["pass"] = rec["used"] is not None
            slots[slot] = rec
        n_pass = sum(r["pass"] for r in slots.values())
        res["RT-4"] = {"slots": slots, "n_slots_pass": n_pass, "sign_check_ok": ctx.check["ok"],
                       "pass": bool(ctx.check["ok"] and n_pass >= 3), "rtb_triggered": bool(n_pass < 3)}
        res["RT-5"] = {"probes": probes, "recorded": True, "all_finite": all(p["finite"] for p in probes.values())}
    else:
        res["RT-4"] = {"pass": None, "note": "clips not fetched"}
        res["RT-5"] = {"recorded": False}
    res["RT-1"]["hashes_after_ok"] = H.asset_hashes() == h_before
    res["RT-1"]["pass"] = bool(res["RT-1"]["pass_pre"] and res["RT-1"]["hashes_after_ok"])
    res["end_utc"] = utc()
    res["wall_s"] = round(time.time() - t0, 1)
    cpu_pass = {k: res[k].get("pass") for k in ("RT-1", "RT-2", "RT-3", "RT-4")}
    res["cpu_checks_pass"] = cpu_pass
    res["rt5_recorded_finite"] = bool(res["RT-5"].get("recorded") and res["RT-5"].get("all_finite"))
    out_path.write_text(json.dumps(res, indent=2, default=float))
    with open(HERE / "runs.log", "a") as f:
        for k in ("RT-1", "RT-2", "RT-3", "RT-4"):
            f.write(f"{res['end_utc']} attempt={a.attempt} check={k} pass={cpu_pass[k]} code=rt_cpu.py:{res['code_sha256']['rt_cpu.py'][:12]} "
                    f"results={out_path.name}\n")
        f.write(f"{res['end_utc']} attempt={a.attempt} check=RT-5 recorded={res['RT-5'].get('recorded')} finite={res['rt5_recorded_finite']}\n")
    print("B1RT_CPU_VERDICT " + " ".join(f"{k}={v}" for k, v in cpu_pass.items()) + f" RT-5_recorded={res['rt5_recorded_finite']}")


if __name__ == "__main__":
    main()
