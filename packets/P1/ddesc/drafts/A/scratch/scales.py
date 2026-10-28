import math, sys
sys.path.insert(0,"code")
def a2(r,g):
    return r[0]*(g[1]*g[2])**2 + r[1]*g[2]**2 + r[2]
A={"5020":a2((0.139e-4,0.017e-4,0.169e-4),(1,1+46/18,1+56/16)),
"7520_14":a2((0.489e-4,0.098e-4,0.533e-4),(1,4.5,1+48/22)),
"7520_22":a2((0.489e-4,0.109e-4,0.738e-4),(1,4.5,5)),
"4010":a2((0.068e-4,0,0),(1,5,5))}
E={"5020":25,"7520_14":88,"7520_22":139,"4010":5}
w=10*2*3.1415926535
for k in A:
    kp=A[k]*w*w; kd=2*2*A[k]*w
    print(k, "arm",A[k],"kp",round(kp,2),"kd",round(kd,3),"tau",E[k],"sigma",round(0.25*E[k]/kp,4))
kp=2*A["5020"]*w*w; print("x2 5020 (waist p/r, ankle) kp",round(kp,2),"tau",50,"sigma",round(0.25*50/kp,4))
import torch
from attention_policy import AttentionDecoder, AttentionDecoderCfg, count_params
from mlp_baseline import build_matched_mlp
for md in (12,16):
    a=count_params(AttentionDecoder(AttentionDecoderCfg(morph_dim=md), morphology=torch.randn(29,md)))
    m=build_matched_mlp(a); print(md,a,count_params(m),m.cfg.hidden, (count_params(m)-a)/a)
