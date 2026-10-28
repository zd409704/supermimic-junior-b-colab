"""Read-only CPU probes of candidate Y; reconstructed formulas, not author code."""
from pathlib import Path
import ast
import math
import re
import sys
from collections import Counter

import mujoco as mj
import numpy as np
import torch

ROOT = Path('/srv/claude/research/supermimic-junior-b-colab')
sys.path.insert(0, str(ROOT / 'code'))
from attention_policy import (AttentionDecoder, AttentionDecoderCfg, DEFAULT_JOINT_NAMES,
                              synthetic_morphology, _limb_from_name, _side_from_name,
                              count_params, permute_obs_history)
from mlp_baseline import build_matched_mlp

torch.set_num_threads(1)
torch.manual_seed(17)

def synthetic_y(names):
    v1 = synthetic_morphology(tuple(names)).numpy()
    p, axis = v1[:, :3], v1[:, 3:6]
    depth = np.rint(v1[:, 7] * 6) + 1  # inclusive; additive convention cannot fix ordering
    leg = v1[:, 9] == 1
    length = np.ptp(p[leg, 2])
    center = p[leg & (depth == 1)].mean(0)
    return torch.tensor(np.column_stack(((p-center)/length, axis, v1[:, 6],
                        np.tile([-0.5/math.pi, 0.5/math.pi], (len(names), 1)),
                        depth/8, v1[:, 8:12], np.zeros((len(names), 2)))), dtype=torch.float32)

names = DEFAULT_JOINT_NAMES
perm = torch.arange(len(names)-1, -1, -1)
a = synthetic_y(names)
b = synthetic_y([names[i] for i in perm])
print('C1 synthetic rebuilt max difference:', (b-a[perm]).abs().max().item())
idx = names.index('left_hip_pitch_joint')
reordered_idx = list(reversed(names)).index('left_hip_pitch_joint')
print('C1 left hip pitch depth original/rebuilt:', a[idx, 9].item(), b[reordered_idx, 9].item())
dec = AttentionDecoder(AttentionDecoderCfg(morph_dim=16), a).eval()
z, obs = torch.randn(2,32), torch.randn(2,930)
with torch.no_grad():
    expected = dec(z,obs)[:,perm]
    obs_p = permute_obs_history(obs,perm,29,10)
    direct = dec(z,obs_p,morphology=a[perm])
    rebuilt = dec(z,obs_p,morphology=b)
print('C1 decoder relative error direct/rebuilt:',
      ((direct-expected).norm()/expected.norm()).item(),
      ((rebuilt-expected).norm()/expected.norm()).item())
v1dec = AttentionDecoder(AttentionDecoderCfg())
matched = build_matched_mlp(count_params(dec))
print('C2 counts v1/v2/matched/widths:',count_params(v1dec),count_params(dec),count_params(matched),matched.cfg.hidden)

# Evaluate only the numeric assignments and actuator records from permitted context.
source = (ROOT/'packets/P1/ddesc/context/upstream-d9be385/mjlab_ref29_constants.py').read_text()
def reflected(rotor, gears):
    return rotor[0]*(gears[1]*gears[2])**2 + rotor[1]*gears[2]**2 + rotor[2]
class Record:
    def __init__(self, **kw): self.__dict__.update(kw)
env = dict(reflected_inertia_from_two_stage_planetary=reflected,
           ElectricActuator=Record, BuiltinPositionActuatorCfg=Record)
prefixes = ('ROTOR_', 'GEARS_', 'ARMATURE_', 'ACTUATOR_', 'STIFFNESS_', 'DAMPING_', 'REF29_ACTUATOR_')
for node in ast.parse(source).body:
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
        name = node.targets[0].id
        if name.startswith(prefixes) or name in ('NATURAL_FREQ','DAMPING_RATIO'):
            exec(compile(ast.Module(body=[node],type_ignores=[]),'<permitted numeric constants>','exec'),env)
groups = [v for k,v in env.items() if k.startswith('REF29_ACTUATOR_')]
scales = []
for name in names:
    found = [g for g in groups if any(re.fullmatch(p,name) for p in g.target_names_expr)]
    assert len(found)==1, (name,len(found))
    g = found[0]
    scales.append(.25*g.effort_limit/g.stiffness)
print('C3 scale counts:',sorted(Counter(round(s,9) for s in scales).items()))
print('C3 kd/kp:',sorted(set(round(g.damping/g.stiffness,9) for g in groups)))

model = mj.MjModel.from_xml_path(str(next((ROOT/'assets/home_humanoid_mjcf').glob('*.xml'))))
ids = np.flatnonzero(model.jnt_type == mj.mjtJoint.mjJNT_HINGE)
hnames = [mj.mj_id2name(model,mj.mjtObj.mjOBJ_JOINT,int(j)) for j in ids]
limbs = np.array([_limb_from_name(n) for n in hnames])
limb_by_id = dict(zip(ids,limbs))
hinge_of_body = {int(model.jnt_bodyid[j]):int(j) for j in ids}
depths = []
for j,limb in zip(ids,limbs):
    body, depth = int(model.jnt_bodyid[j]),0
    while body:
        h = hinge_of_body.get(body)
        depth += h is not None and limb_by_id[h] == limb
        body = int(model.body_parentid[body])
    depths.append(depth)
depths = np.array(depths)
def home_y(m, physical_scale=1):
    d = mj.MjData(m); mj.mj_forward(m,d)
    rotation = d.xmat[1].reshape(3,3)
    p = (d.xanchor[ids]-d.xpos[1]) @ rotation
    axis = d.xaxis[ids] @ rotation
    leg = limbs == 0
    length = np.ptp(p[leg,2]); center = p[leg & (depths==1)].mean(0)
    mass = m.body_mass.sum()
    effort = np.array([21 if k==0 else 10 if k==2 else 3.7 for k in limbs])
    inertia = np.array([.01 if k==0 else .005 if k==2 else .002 for k in limbs])
    sigma = .25*effort/(inertia*(20*math.pi)**2)
    effort *= physical_scale**4
    default = np.array([.4 if 'calf' in n else 0 for n in hnames])
    rows = np.column_stack(((p-center)/length,axis,default,m.jnt_range[ids]/math.pi,
        depths/8,[_side_from_name(n) for n in hnames],np.eye(3)[limbs],
        np.log(sigma/.25),np.log(effort/(mass*9.81*length)/.5)))
    return rows,length,center,mass
rows,length,center,mass = home_y(model)
print('C4 home J/nu/L/c/M/distinct/finite/maxabs:',len(ids),model.nu,length,center,mass,
      len(np.unique(np.round(rows,5),axis=0)),np.isfinite(rows).all(),abs(rows).max())
print('C4 home left knee:',rows[hnames.index('l_calf_joint')])
home_tensor = torch.tensor(rows,dtype=torch.float32)
home_dec = AttentionDecoder(AttentionDecoderCfg(num_joints=22,morph_dim=16),home_tensor).eval()
home_perm = torch.arange(21,-1,-1)
home_obs = torch.randn(2,10*(3*22+6))
with torch.no_grad():
    home_expected = home_dec(z,home_obs)[:,home_perm]
    home_permuted = home_dec(z,permute_obs_history(home_obs,home_perm,22,10),morphology=home_tensor[home_perm])
print('C4 home fixed-row permutation relative error:',
      ((home_permuted-home_expected).norm()/home_expected.norm()).item())
left,right = [hnames.index(n) for n in ('l_calf_joint','r_calf_joint')]
print('C5 calf ranges left/right:',model.jnt_range[ids[left]],model.jnt_range[ids[right]])
print('C5 normalized limit mirror residual:',abs(rows[left,7:9]-rows[right,7:9]).max())
for s in (.5,2):
    # Descriptor uses only anchor kinematics and masses: no physics rollout.
    clone = mj.MjModel.from_xml_path(str(next((ROOT/'assets/home_humanoid_mjcf').glob('*.xml'))))
    clone.body_pos[:] *= s; clone.jnt_pos[:] *= s; clone.body_mass[:] *= s**3
    scaled,_,_,_ = home_y(clone,s)
    print('C6 home scale/maxdiff:',s,abs(scaled-rows).max())

# The literal side fallback retains a metric rounding threshold.
print('C7 side fallback at y=.0008 and half-size:',
      np.sign(np.round(.0008,3)),np.sign(np.round(.0004,3)))
print('C8 wrist log_tau at proposal-estimated M=35, L=.65 / ablated L=1:',
      math.log(5/(35*9.81*.65)/.5),math.log(5/(35*9.81)/.5))
print('C8 minimum mass making 5 Nm wrist violate abs(log_tau)<=3.5 at L=1:',
      5/(9.81*.5*math.exp(-3.5)))
