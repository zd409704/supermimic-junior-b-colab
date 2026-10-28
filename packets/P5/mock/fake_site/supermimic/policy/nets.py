"""Mock upstream layout: Policy(cfg) with encoders['motion'] and a decoder, a = dec(enc(goal), obs_hist)."""
from dataclasses import dataclass
import torch, torch.nn as nn


@dataclass
class PolicyCfg:
    latent_dim: int = 32
    history: int = 10
    obs_term_scale: tuple = (1.0, 5.0, 2.0, 1.0, 1.0)


class Policy(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.encoders = nn.ModuleDict({"motion": nn.Linear(680, cfg.latent_dim)})
        self.decoder = nn.Linear(cfg.latent_dim + 930, 29)

    def forward(self, obs_hist, goal, interface="motion"):
        return self.decoder(torch.tanh(self.encoders[interface](goal)), obs_hist)
