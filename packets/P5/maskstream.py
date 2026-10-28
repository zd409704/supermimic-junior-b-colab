"""CR-B2-1 (c): fixed-seed mask stream (spikes/B2/PLAN.md §2.3 (c), §3).

``MaskStream.random_token_mask`` has the same semantics as the frozen ``attention_policy.random_token_mask``:
exactly k = max(1, round(f * J)) joint tokens per row (f = 0.1 -> 3, f = 0.2 -> 6 for J = 29; the root is not
in the J axis), chosen as the top-k of uniform scores. The scores come from a **dedicated** ``torch.Generator``
on the decoder's device, re-seeded by ``begin(seed, frac)`` at the start of every eval condition. The global
RNG is never used. A call that passes its own ``generator`` (the frozen CPU smoke, the PERM masked variant)
goes to the frozen function unchanged and is not recorded.

Every recorded draw keeps the boolean (N, J) mask. ``end(out_dir, cond)`` writes
``maskstream_<cond>.npz`` (bit-packed stream) and ``maskstream_<cond>.json`` (seed, frac, k, calls,
rows_per_call, sha256 of the packed stream).

``install(stream)`` replaces the module-level name ``random_token_mask`` in ``attention_policy``,
``mlp_baseline`` and ``mlp_mind`` (the three decoder modules). The decoders look the name up at call time.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch

CODE = Path(__file__).resolve().parents[2] / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import attention_policy  # noqa: E402

FROZEN_RANDOM_TOKEN_MASK = attention_policy.random_token_mask
DECODER_MODULES = ("attention_policy", "mlp_baseline", "mlp_mind")


def k_of(frac: float, num_joints: int) -> int:
    return max(1, int(round(frac * num_joints)))


def pack(masks: list[np.ndarray]) -> np.ndarray:
    """(calls, rows, J) bool -> (calls, rows, ceil(J/8)) uint8, bit order 'big' (numpy default)."""
    if not masks:
        return np.zeros((0, 0, 0), dtype=np.uint8)
    return np.packbits(np.stack(masks).astype(bool), axis=-1)


class MaskStream:
    def __init__(self):
        self.seed: int | None = None
        self.frac: float | None = None
        self._gens: dict[str, torch.Generator] = {}
        self.masks: list[np.ndarray] = []
        self.fracs_seen: set[float] = set()
        self.devices: set[str] = set()

    def begin(self, seed: int, frac: float) -> None:
        self.seed, self.frac = int(seed), float(frac)
        self._gens = {}
        self.masks = []
        self.fracs_seen = set()
        self.devices = set()

    def _gen(self, device) -> torch.Generator:
        dev = torch.device(device if device is not None else "cpu")
        key = str(dev)
        if key not in self._gens:
            self._gens[key] = torch.Generator(device=dev).manual_seed(self.seed)
        self.devices.add(key)
        return self._gens[key]

    def random_token_mask(self, n: int, num_joints: int, frac: float, generator: torch.Generator | None = None,
                          device=None) -> torch.Tensor:
        if generator is not None:
            return FROZEN_RANDOM_TOKEN_MASK(n, num_joints, frac, generator=generator, device=device)
        if self.seed is None:
            raise RuntimeError("[maskstream] mask drawn outside an eval condition (no seed set)")
        k = k_of(frac, num_joints)
        scores = torch.rand(n, num_joints, generator=self._gen(device), device=device)
        idx = scores.topk(k, dim=-1).indices
        m = torch.zeros(n, num_joints, dtype=torch.bool, device=device).scatter_(1, idx, True)
        self.masks.append(m.detach().cpu().numpy())
        self.fracs_seen.add(float(frac))
        return m

    def record(self) -> dict:
        packed = pack(self.masks)
        rows = sorted({int(m.shape[0]) for m in self.masks})
        joints = sorted({int(m.shape[1]) for m in self.masks})
        per_row = sorted({int(x) for m in self.masks for x in m.sum(axis=1)})
        return {
            "seed": self.seed, "frac": self.frac,
            "k": k_of(self.frac, joints[0] if joints else 29) if self.frac and self.frac > 0 else 0,
            "calls": len(self.masks),
            "rows_per_call": rows[0] if len(rows) == 1 else rows,
            "num_joints": joints[0] if len(joints) == 1 else joints,
            "true_per_row": per_row,
            "fracs_seen": sorted(self.fracs_seen),
            "generator": "dedicated torch.Generator per device, manual_seed(seed) at condition start",
            "devices": sorted(self.devices),
            "packing": "numpy.packbits(axis=-1) of the (calls, rows, J) bool stream, C order",
            "packed_shape": list(packed.shape),
            "sha256": hashlib.sha256(np.ascontiguousarray(packed).tobytes()).hexdigest(),
        }, packed

    def end(self, out_dir: Path, cond: str, extra: dict | None = None) -> dict:
        meta, packed = self.record()
        meta.update(extra or {})
        out_dir = Path(out_dir)
        np.savez(out_dir / f"maskstream_{cond}.npz", packed=packed, seed=np.int64(meta["seed"]),
                 frac=np.float64(meta["frac"]))
        (out_dir / f"maskstream_{cond}.json").write_text(json.dumps(meta, indent=1))
        self.seed = None
        self.frac = None
        return meta


def install(stream: MaskStream) -> None:
    for name in DECODER_MODULES:
        mod = sys.modules.get(name)
        if mod is None:
            mod = __import__(name)
        setattr(mod, "random_token_mask", stream.random_token_mask)


def load_packed(npz_path: str | Path) -> np.ndarray:
    with np.load(npz_path) as z:
        return z["packed"]
