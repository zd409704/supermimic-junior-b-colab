"""B1 decoder-weight transfer from a P4 (29-DoF reference body) checkpoint into a J=22 home-humanoid decoder.

* attention (H-A-xfer / H-A-frozen / H-A-xfer-noscale): every decoder **parameter** is copied unchanged; none of
  them depends on J (``id_mode=morph``). The buffers ``morphology`` (J x 16 descriptor rows) and ``scale``
  (observation scale vector, length depends on J) are the target body's own and are not copied.
* mlp_matched (H-M-xfer): the decoder keeps the P4 hidden widths. Hidden layers are copied. The input layer's
  columns and the output layer's rows are copied through the joint-semantic map (20 of 22 joints; AS-4 table).
  The two head joints' columns/rows keep their fresh initialisation (SCHEME_PLAN §4).

Every load is reported (keys, shapes, mapped and fresh indices, source sha256) into the run sidecar.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[3]  # packets/P6/b1/<file> -> program root
for p in (ROOT / "code", ROOT / "spikes" / "B1-RT"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
from retarget_rta import CORRESPONDENCE, REF_JOINT_NAMES  # noqa: E402
import home_humanoid as H  # noqa: E402

DECODER_BUFFERS = ("morphology", "scale")


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def p4_decoder_state(ckpt: str | Path) -> dict[str, torch.Tensor]:
    ck = torch.load(ckpt, map_location="cpu", weights_only=False)
    sd = ck["policy"]
    out = {k[len("decoder."):]: v for k, v in sd.items() if k.startswith("decoder.")}
    if not out:
        raise RuntimeError(f"{ckpt}: no decoder.* keys in the policy state dict")
    return out


def mlp_hidden_of(sd: dict[str, torch.Tensor]) -> tuple[int, ...]:
    """Hidden widths of a P4 MLPDecoder state dict (``mlp.<i>.weight`` Linear layers, last one = output)."""
    lin = sorted((int(k.split(".")[1]), v) for k, v in sd.items() if k.startswith("mlp.") and k.endswith(".weight"))
    return tuple(int(w.shape[0]) for _, w in lin[:-1])


def init_attention(dec: torch.nn.Module, src: dict[str, torch.Tensor]) -> dict:
    own = dec.state_dict()
    params = {n for n, _ in dec.named_parameters()}
    src_params = {k: v for k, v in src.items() if k not in DECODER_BUFFERS}
    missing = sorted(params - set(src_params))
    unexpected = sorted(set(src_params) - params)
    bad_shape = sorted(k for k in params & set(src_params) if tuple(own[k].shape) != tuple(src_params[k].shape))
    if missing or unexpected or bad_shape:
        raise RuntimeError(f"attention transfer: missing={missing} unexpected={unexpected} shape={bad_shape}")
    with torch.no_grad():
        for k in params:
            own[k].copy_(src_params[k])
    return {"kind": "attention_full_copy", "n_params_copied": len(params),
            "n_values_copied": int(sum(src_params[k].numel() for k in params)),
            "buffers_not_copied": [b for b in DECODER_BUFFERS if b in src]}


def joint_map() -> list[int | None]:
    """home joint index -> reference joint index (None for head joints)."""
    ref = {n: i for i, n in enumerate(REF_JOINT_NAMES)}
    return [ref[CORRESPONDENCE[n]] if n in CORRESPONDENCE else None for n in H.JOINT_NAMES]


def _input_column_map(latent: int, hist: int, jh: int, jr: int, jm: list[int | None]) -> list[int | None]:
    cols: list[int | None] = list(range(latent))
    off_h, off_r = latent, latent
    for term in ("qpos", "qvel"):
        for t in range(hist):
            for k in range(jh):
                cols.append(None if jm[k] is None else off_r + t * jr + jm[k])
        off_h += hist * jh
        off_r += hist * jr
    for _ in ("angvel", "grav"):
        for t in range(hist):
            for c in range(3):
                cols.append(off_r + t * 3 + c)
        off_h += hist * 3
        off_r += hist * 3
    for t in range(hist):
        for k in range(jh):
            cols.append(None if jm[k] is None else off_r + t * jr + jm[k])
    return cols


def init_mlp_mapped(dec: torch.nn.Module, src: dict[str, torch.Tensor]) -> dict:
    lin = sorted({int(k.split(".")[1]) for k in src if k.startswith("mlp.") and k.endswith(".weight")})
    own = dec.state_dict()
    first, last = lin[0], lin[-1]
    jh, hist, latent = dec.cfg.num_joints, dec.cfg.history, dec.cfg.latent_dim
    jr = len(REF_JOINT_NAMES)
    jm = joint_map()
    cols = _input_column_map(latent, hist, jh, jr, jm)
    w_src, w_own = src[f"mlp.{first}.weight"], own[f"mlp.{first}.weight"]
    if w_own.shape[1] != len(cols) or w_src.shape[1] != latent + hist * (3 * jr + 6) or w_own.shape[0] != w_src.shape[0]:
        raise RuntimeError(f"mlp transfer: input layer shapes own={tuple(w_own.shape)} src={tuple(w_src.shape)}")
    with torch.no_grad():
        n_mapped = 0
        for c, rc in enumerate(cols):
            if rc is not None:
                w_own[:, c] = w_src[:, rc]
                n_mapped += 1
        own[f"mlp.{first}.bias"].copy_(src[f"mlp.{first}.bias"])
        for i in lin[1:-1]:
            for s in ("weight", "bias"):
                if tuple(own[f"mlp.{i}.{s}"].shape) != tuple(src[f"mlp.{i}.{s}"].shape):
                    raise RuntimeError(f"mlp transfer: hidden layer {i} shape mismatch")
                own[f"mlp.{i}.{s}"].copy_(src[f"mlp.{i}.{s}"])
        n_rows = 0
        for k, rk in enumerate(jm):
            if rk is not None:
                own[f"mlp.{last}.weight"][k] = src[f"mlp.{last}.weight"][rk]
                own[f"mlp.{last}.bias"][k] = src[f"mlp.{last}.bias"][rk]
                n_rows += 1
    fresh_joints = [H.JOINT_NAMES[k] for k, rk in enumerate(jm) if rk is None]
    return {"kind": "mlp_row_mapped", "hidden": [int(own[f"mlp.{i}.weight"].shape[0]) for i in lin[:-1]],
            "input_cols_mapped": n_mapped, "input_cols_total": len(cols), "output_rows_mapped": n_rows,
            "output_rows_total": jh, "fresh_joints": fresh_joints, "hidden_layers_copied": len(lin) - 2,
            "joint_map": {H.JOINT_NAMES[k]: (REF_JOINT_NAMES[rk] if rk is not None else None) for k, rk in enumerate(jm)}}


def freeze(dec: torch.nn.Module) -> int:
    n = 0
    for p in dec.parameters():
        p.requires_grad_(False)
        n += p.numel()
    return n
