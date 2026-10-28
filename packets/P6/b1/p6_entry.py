"""P6 (B1) train / eval entry for the home humanoid (J = 22) on the body-parametrised upstream.

Reuses the frozen ``code/`` pieces (decoders, descriptor v2, seam probe, tyro argv) unchanged; only the joint count,
the body loaders and the transfer initialisation differ from ``code/train_entry.py``. Requires
``SM_BODY_MODULE=sm_body_home`` and the patched upstream (packets/P6/upstream-b1.patch) on the import path.

Train::

    python p6_entry.py train --config configs/b1_home.yaml --policy attention --seed 0 \
        [--init scratch|xfer|frozen] [--src-ckpt <P4 ckpt_0001600.pt>] [--device cuda:0]

Eval (upstream whole-clip benchmark, one JSON per mask)::

    python p6_entry.py eval --config configs/b1_home.yaml --ckpt logs/<run>/ckpt_0001600.pt --out-dir <dir> \
        [--masks 0.0 0.1 0.2]
"""

from __future__ import annotations

import argparse
import json
import os
import runpy
import sys
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in (ROOT / "code", HERE, ROOT / "spikes" / "B1-RT"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import train_entry as TE  # noqa: E402  (frozen D-004 module, imported read-only)
import transfer as XF  # noqa: E402
from attention_policy import count_params, make_upstream_policy_class  # noqa: E402
from mlp_baseline import MLPDecoder, MLPDecoderCfg  # noqa: E402

NUM_JOINTS = 22
HISTORY = 10
INITS = ("scratch", "xfer", "frozen")


def _check_body() -> None:
    if os.environ.get("SM_BODY_MODULE") != "sm_body_home":
        raise RuntimeError("[p6_entry] SM_BODY_MODULE must be sm_body_home")
    from supermimic import body as B  # noqa: PLC0415

    if B.NJ != NUM_JOINTS:
        raise RuntimeError(f"[p6_entry] patched upstream reports NJ={B.NJ}, expected {NUM_JOINTS}")


def build_decoder22(arm: str, cfg: dict, morphology, init: str, src_sd: dict | None, latent: int, mlp_hidden=None):
    """J=22 decoder. mlp_matched + xfer/frozen keeps the P4 hidden widths; scratch MLP is matched to the J=22 attention."""
    if arm == "attention":
        return TE.build_decoder("attention", cfg, latent, HISTORY, NUM_JOINTS, morphology)
    if arm != "mlp_matched":
        raise ValueError(arm)
    if mlp_hidden is not None:
        return MLPDecoder(MLPDecoderCfg(latent, HISTORY, NUM_JOINTS, tuple(mlp_hidden)))
    if init == "scratch":
        return TE.build_decoder("mlp_matched", cfg, latent, HISTORY, NUM_JOINTS, morphology)
    return MLPDecoder(MLPDecoderCfg(latent, HISTORY, NUM_JOINTS, XF.mlp_hidden_of(src_sd)))


def install(arm: str, cfg: dict, targets: tuple[str, ...], *, init: str = "scratch", src_ckpt: str | None = None,
            probe: bool = True, mlp_hidden=None) -> dict:
    """Rebind ``Policy`` in ``targets`` to a subclass whose decoder is the J=22 Junior decoder (+ transfer init)."""
    if init not in INITS:
        raise ValueError(init)
    if init != "scratch" and not src_ckpt:
        raise RuntimeError("[p6_entry] --src-ckpt is required for init xfer/frozen")
    if cfg.get("attention", {}).get("morphology") != "upstream_mjmodel":
        raise RuntimeError("[p6_entry] attention.morphology must be upstream_mjmodel")
    morph_info: dict = {}
    morphology = TE.load_morphology(cfg, NUM_JOINTS, morph_info)
    info: dict = {"body": "home_humanoid", "num_joints": NUM_JOINTS, "init": init,
                  "default_pose_source": morph_info.get("default_pose_source"),
                  "descriptor_joint_names": morph_info.get("joint_names")}
    if morph_info.get("descriptor_meta") is not None:
        info["descriptor"] = morph_info["descriptor_meta"]
        info["actuator_source"] = morph_info.get("actuator_source")
    sp = None
    if probe:
        compile_value = str(cfg.get("upstream", {}).get("tyro_args", {}).get("--policy-trainer.compile", "unset"))
        sp = TE.SeamProbe(morph_info, compile_value, num_joints=NUM_JOINTS, history=HISTORY)
        sp.report_s4()
        sp.install(targets)
        info["seam"] = sp.seam
    src_sd = None
    if init != "scratch":
        src_sd = XF.p4_decoder_state(src_ckpt)
        info["transfer_src"] = {"path": str(src_ckpt), "sha256": XF.file_sha256(src_ckpt)}
    use_morph = morphology if arm == "attention" else None

    def factory(pcfg):
        dec = build_decoder22(arm, cfg, use_morph, init, src_sd, pcfg.latent_dim, mlp_hidden)
        if init != "scratch":
            rep = XF.init_attention(dec, src_sd) if arm == "attention" else XF.init_mlp_mapped(dec, src_sd)
            if init == "frozen":
                rep["frozen_values"] = XF.freeze(dec)
            info["transfer"] = rep
        dec.auto_mask_frac = float(cfg.get("b2", {}).get("train_mask_frac", 0.0))
        info.update(TE.decoder_sidecar(arm, cfg, dec), train_mask_frac=dec.auto_mask_frac)
        info["params_total"] = sum(p.numel() for p in dec.parameters())
        info["params_trainable"] = count_params(dec)
        if sp is not None:
            sp.attach_decoder(dec)
        return dec

    cls = make_upstream_policy_class(factory)
    import importlib  # noqa: PLC0415

    for t in targets:
        setattr(importlib.import_module(t), "Policy", cls)
    return info


def cmd_train(a) -> None:
    _check_body()
    cfg = TE.load_config(a.config)
    cfg["seed"] = a.seed
    if a.run_tag:
        cfg["run_name"] = a.run_tag
    info = install(a.policy, cfg, ("supermimic.training.loop",), init=a.init, src_ckpt=a.src_ckpt)
    argv = TE.tyro_argv(cfg, a.policy)
    if a.device:
        argv += ["--device", a.device]
    print("[p6_entry] upstream argv:", " ".join(argv), flush=True)
    sys.argv = ["sm-train", *argv]
    run_dir = Path("logs") / argv[1]
    run_dir.mkdir(parents=True, exist_ok=True)
    from supermimic.scripts.train import main as upstream_main  # noqa: PLC0415

    try:
        upstream_main()
    finally:
        (run_dir / "junior_policy.json").write_text(json.dumps({**info, "argv": argv}, indent=2, default=float))


def cmd_eval(a) -> None:
    _check_body()
    cfg = TE.load_config(a.config)
    ckpt = Path(a.ckpt)
    meta = json.loads((ckpt.parent / "junior_policy.json").read_text())
    arm = meta["policy"]
    if meta.get("attention"):
        cfg = {**cfg, "attention": meta["attention"]}
    import supermimic.eval.benchmark as bench  # noqa: PLC0415

    info = install(arm, cfg, ("supermimic.eval.benchmark",), init="scratch", probe=False,
                   mlp_hidden=meta.get("mlp_hidden") if arm == "mlp_matched" else None)
    want = (meta.get("descriptor") or {}).get("sha256")
    got = (info.get("descriptor") or {}).get("sha256")
    if arm == "attention" and want and want != got:
        raise RuntimeError(f"[p6_entry] descriptor sha256 mismatch: sidecar {want} vs rebuilt {got}")
    orig_load = bench.load_policy_from_checkpoint
    up = cfg["upstream"]
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    script = Path(up["repo_dir"]) / "scripts" / "eval_benchmark.py"
    for frac in a.masks:
        def load(path, device, _f=frac):
            policy, pcfg = orig_load(path, device)
            policy.decoder.auto_mask_frac = _f
            return policy, pcfg

        bench.load_policy_from_checkpoint = load
        out = out_dir / f"{ckpt.parent.name}_{ckpt.stem}_mask{frac:.2f}.json"
        sys.argv = ["eval_benchmark.py", "--ckpt", str(ckpt), "--npz-dir", up["npz_dir"],
                    "--num-envs", str(cfg.get("eval", {}).get("num_envs", 64)), "--out", str(out)]
        if a.device:
            sys.argv += ["--device", a.device]
        print("[p6_entry]", " ".join(sys.argv), flush=True)
        try:
            runpy.run_path(str(script), run_name="__main__")
        except SystemExit as e:
            if e.code not in (0, None):
                raise


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("--config", required=True)
    t.add_argument("--policy", choices=("attention", "mlp_matched"), required=True)
    t.add_argument("--seed", type=int, required=True)
    t.add_argument("--init", choices=INITS, default="scratch")
    t.add_argument("--src-ckpt", default=None)
    t.add_argument("--run-tag", default=None, help="overrides config run_name (run dir = <tag>_<arm>_s<seed>)")
    t.add_argument("--device", default=None)
    e = sub.add_parser("eval")
    e.add_argument("--config", required=True)
    e.add_argument("--ckpt", required=True)
    e.add_argument("--out-dir", required=True)
    e.add_argument("--masks", type=float, nargs="+", default=[0.0])
    e.add_argument("--device", default=None)
    a = ap.parse_args()
    cmd_train(a) if a.cmd == "train" else cmd_eval(a)


if __name__ == "__main__":
    main()
