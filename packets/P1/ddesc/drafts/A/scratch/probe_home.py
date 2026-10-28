import glob, mujoco, numpy as np
xml = glob.glob("assets/home_humanoid_mjcf/*.xml")[0]
m = mujoco.MjModel.from_xml_path(xml); d = mujoco.MjData(m); mujoco.mj_forward(m, d)
print("njnt", m.njnt, "nbody", m.nbody, "nu", m.nu, "nkey", m.nkey, "mass", m.body_mass.sum())
for j in range(m.njnt):
    if m.jnt_type[j] != 3: continue
    n = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, j)
    b = m.jnt_bodyid[j]
    dep=0; bb=b
    while bb>1: bb=m.body_parentid[bb]; dep+=1
    a = d.xmat[1].reshape(3,3).T @ (d.xanchor[j]-d.xpos[1]); ax = d.xmat[1].reshape(3,3).T @ d.xaxis[j]
    print(f"{n:28s} b={mujoco.mj_id2name(m,1,b):22s} dep={dep} rng={m.jnt_range[j].round(3)} lim={m.jnt_limited[j]} frc={m.jnt_actfrcrange[j]} arm={m.dof_armature[m.jnt_dofadr[j]]} damp={m.dof_damping[m.jnt_dofadr[j]]} fl={m.dof_frictionloss[m.jnt_dofadr[j]]} anc={a.round(3)} ax={ax.round(2)}")
for b in range(m.nbody): print(b, mujoco.mj_id2name(m,1,b), m.body_parentid[b], d.xpos[b].round(3), round(m.body_mass[b],3))
