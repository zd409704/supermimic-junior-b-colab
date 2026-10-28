"""P5-prep driver mock: stand-in for p5_train_entry.py --mode upstream (no GPU, no simulator).

Prints a trainer log in the real format (B0 fixture lines, real tyro argv from the frozen train_entry), writes a
genuine tb event file (B0 fixture writer), ckpt_0000400..1600 stubs, keeps "training" after the endpoint, and writes
the sidecar in a finally block, as train_entry.run_upstream does. MOCK_<run>=infra (first attempt only) / div.
"""
import argparse, json, os, sys, time
from pathlib import Path
R = "/srv/claude/research/supermimic-junior-b-colab"
sys.path.insert(0, R + "/spikes/B0/verdict")
import make_fixture as mf
J = Path(os.environ["MOCK_J"])
sys.path[:0] = [str(J / "code"), str(J / "packets" / "P5")]
import mlp_mind; mlp_mind.register()
import train_entry
mf.RATE["mlp_mind"] = 0.74
mf.PARAMS["mlp_mind"] = 467491
ap = argparse.ArgumentParser(); ap.add_argument("--mode"); ap.add_argument("--policy"); ap.add_argument("--config"); ap.add_argument("--seed", type=int)
a = ap.parse_args()
cfg = train_entry.load_config(a.config); cfg["seed"] = a.seed
argv = train_entry.tyro_argv(cfg, a.policy)
run = Path("logs") / argv[1]; run.mkdir(parents=True, exist_ok=True)
flag = Path(os.environ["MOCK_M"]) / f"infra_done_{run.name}"
mode = os.environ.get("MOCK_" + run.name, "")
kw = {}
if mode == "div":
    kw = dict(outcome="div_crash", nan_step=800)
elif mode == "infra" and not flag.exists():
    kw = dict(outcome="traceback", pre_exc=(['  File "x"'], "RuntimeError: CUDA error: unspecified launch failure"))
spec = mf.default_attempt(f"{argv[1]}_a1", **kw)
lines = mf.train_log(spec).splitlines()
lines = [("[train_entry] upstream argv: " + " ".join(argv)) if l.startswith("[train_entry] upstream argv:") else l for l in lines]
if spec["outcome"] == "completed":
    lines = lines[:max(i for i, l in enumerate(lines) if l.startswith("Traceback"))]
(run / "tb").mkdir(exist_ok=True)
(run / "tb" / f"events.out.tfevents.{int(time.time())}.mock").write_bytes(mf.event_file_bytes(spec))
dec = train_entry.build_decoder(a.policy, {**cfg, "attention": {**cfg["attention"], "morphology": "synthetic"}})
side = {**train_entry.decoder_sidecar(a.policy, cfg, dec), "train_mask_frac": float(cfg["b2"]["train_mask_frac"]),
        "default_pose_source": "env_init_state", "argv": argv,
        "seam": mf.sidecar(spec)["seam"]}
if a.policy == "attention":
    side["descriptor"] = {"version": "v2", "sha256": mf.DESCRIPTOR_SHA}
try:
    for l in lines:
        if l.startswith("Traceback") and spec["outcome"] != "completed":
            flag.touch(); print("\n".join(lines[lines.index(l):]), flush=True); sys.exit(1)
        print(l, flush=True)
        if l.startswith("it "):
            it = int(l.split()[1])
            if it % 400 == 0 and it <= 1600:
                (run / f"ckpt_{it:07d}.pt").write_bytes(b"x" * 100)
    while True:
        time.sleep(0.2)
finally:
    (run / "junior_policy.json").write_text(json.dumps(side, indent=2))
