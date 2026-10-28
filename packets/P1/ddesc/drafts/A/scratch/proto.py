import glob, math, sys, numpy as np, mujoco, torch
sys.path.insert(0,"code")
from attention_policy import _limb_from_name, _side_from_name, AttentionDecoder, AttentionDecoderCfg, permute_obs_history
SIG0, TAU0, DEPTH_C, G = 0.25, 0.5, 8.0, 9.81
def desc(model, names, qdef, tau, sig, ablate_scale=False):
    d = mujoco.MjData(model); mujoco.mj_forward(model, d)
    R = d.xmat[1].reshape(3,3); p = d.xpos[1]
    ids = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, n) for n in names]
    anc = np.array([R.T@(d.xanchor[j]-p) for j in ids]); ax = np.array([R.T@d.xaxis[j] for j in ids])
    limb = np.array([(_limb_from_name(n) if _limb_from_name(n) is not None else 2) for n in names])
    hinge_body = {model.jnt_bodyid[j]: j for j in range(model.njnt) if model.jnt_type[j]==3}
    name_of = {j: mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j) for j in hinge_body.values()}
    depth=[]
    for n,j,l in zip(names,ids,limb):
        b, k = model.jnt_bodyid[j], 0
        while b > 0:
            if b in hinge_body and _limb_from_name(name_of[hinge_body[b]]) == l: k += 1
            b = model.body_parentid[b]
        depth.append(k)
    depth=np.array(depth); leg = limb==0
    L = anc[leg,2].max()-anc[leg,2].min()
    c = anc[leg & (depth==1)].mean(0)
    if ablate_scale: L, c = 1.0, np.zeros(3)
    M = model.body_mass.sum()
    lo = model.jnt_range[ids,0]; hi = model.jnt_range[ids,1]
    side = np.array([_side_from_name(n) for n in names])
    oh = np.eye(3)[limb]
    rows = np.column_stack([(anc-c)/L, ax, qdef, lo/math.pi, hi/math.pi, depth/DEPTH_C, side, oh,
                            np.log(sig/SIG0), np.log(tau/(M*G*L)/TAU0)])
    return torch.tensor(rows, dtype=torch.float32), dict(L=L, c=c, M=M)
xml = glob.glob("assets/home_humanoid_mjcf/*.xml")[0]
m = mujoco.MjModel.from_xml_path(xml)
names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, j) for j in range(m.njnt) if m.jnt_type[j]==3]
tau = np.array([abs(m.jnt_actfrcrange[mujoco.mj_name2id(m,3,n),1]) for n in names])  # overlay-side read, passed as arg
I = np.array([0.01 if _limb_from_name(n)==0 else (0.002 if "head" in n else 0.005) for n in names])
w=20*math.pi; kp = I*w*w; sig = 0.25*tau/kp
qdef = np.zeros(len(names))
for i,n in enumerate(names):
    if "hip_pitch" in n: qdef[i]=-0.2
    if "calf" in n: qdef[i]=0.4
    if "ankle_pitch" in n: qdef[i]=-0.2
D, meta = desc(m, names, qdef, tau, sig)
print(meta); print("sigma", dict(zip(names, sig.round(3))))
np.set_printoptions(precision=3, suppress=True, linewidth=200)
for n,r in zip(names, D.numpy()): print(f"{n:24s}", r)
print("finite", torch.isfinite(D).all().item(), "distinct", len(set(map(tuple,D.numpy().round(5)))), "/", len(names))
# scale test
m2 = mujoco.MjModel.from_xml_path(xml); s=2.0
m2.body_pos[:] *= s; m2.jnt_pos[:] *= s; m2.body_mass[:] *= s**3
D2,_ = desc(m2, names, qdef, tau*s**4, sig)
D1v,_ = desc(m, names, qdef, tau, sig, True); D2v,_ = desc(m2, names, qdef, tau*s**4, sig, True)
print("scale x2 max|dv2|", (D2-D).abs().max().item(), "no-norm max|d|", (D2v-D1v).abs().max().item())
cfg = AttentionDecoderCfg(num_joints=len(names), morph_dim=16); dec = AttentionDecoder(cfg, morphology=D).eval()
J,H=len(names),10; z=torch.randn(4,32); o=torch.randn(4,H*(3*J+6)); perm=torch.randperm(J)
with torch.no_grad():
    a=dec(z,o); b=dec(z,permute_obs_history(o,perm,J,H),morphology=D[perm])
print("perm rel err", ((b-a[:,perm]).norm()/a.norm()).item())
