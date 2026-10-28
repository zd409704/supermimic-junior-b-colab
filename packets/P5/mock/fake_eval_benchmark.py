"""Mock upstream scripts/eval_benchmark.py: 4 envs, env e plays clip e, policy called once per loop step on all 4
rows until the last clip ends; clip lengths depend on the checkpoint and the condition; JSON in the upstream format."""
import hashlib, json, sys
import torch
from supermimic.eval.benchmark import load_policy_from_checkpoint
a = sys.argv[1:]
ckpt, out = a[a.index("--ckpt") + 1], a[a.index("--out") + 1]
policy, cfg = load_policy_from_checkpoint(ckpt, "cpu")
print("Setting seed: 0"); torch.manual_seed(0)
h = hashlib.sha256((ckpt + out.rsplit("_mask", 1)[1]).encode()).digest()
steps = [12 + h[i] % 40 for i in range(4)]
names = ["dance1_subject1", "jumps1_subject1", "run1_subject2", "walk1_subject1"]
with torch.no_grad():
    for t in range(max(steps)):
        policy(torch.randn(4, 930), torch.randn(4, 680))
clips = [{"name": n, "frames": 6000, "steps": s, "norm_return": 0.2 + h[4 + i] / 1000.0, "failed": True, "fail_step": s,
          "terms": {"motion_body_pos": 0.01}} for i, (n, s) in enumerate(zip(names, steps))]
summ = {"clips": 4, "failed": 4, "mean_norm_return": sum(c["norm_return"] for c in clips) / 4,
        "step_weighted_norm_return": 0.25, "terms": {"motion_body_pos": 0.01}}
open(out, "w").write(json.dumps({"summary": summ, "clips": clips}, indent=1))
print("saved", out)
