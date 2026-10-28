"""Mock upstream benchmark module: load_policy_from_checkpoint builds `Policy` (rebound by install_upstream_policy)."""
import hashlib
import torch
from supermimic.policy.nets import Policy, PolicyCfg  # noqa: F401  (module global, rebound in-process)


def load_policy_from_checkpoint(path, device):
    torch.manual_seed(int(hashlib.sha256(str(path).encode()).hexdigest()[:8], 16))
    pol = Policy(PolicyCfg()).eval()
    return pol, {"env": {"future_frames": 10, "anchor_obs": True}}
