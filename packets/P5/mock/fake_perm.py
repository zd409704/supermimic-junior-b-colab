"""P5-prep driver mock: stand-in for perm_check.py --mode upstream (the real script is tested on CPU in (g))."""
import argparse, json
ap = argparse.ArgumentParser()
for k in ("--mode", "--config", "--ckpt", "--id", "--role", "--out"):
    ap.add_argument(k)
a = ap.parse_args()
side = json.load(open(a.ckpt.rsplit("/", 1)[0] + "/junior_policy.json"))
arm = side["policy"]; idx = (side.get("attention") or {}).get("id_mode") == "index"
rel = 2.2e-6 if arm == "attention" and not idx else 5.1
json.dump({"id": a.id, "role": a.role, "mode": "upstream", "arm": arm, "ckpt": a.ckpt, "rel_err_tf32off": rel,
           "rel_err_default": rel, "rel_err_masked": rel, "pass": rel < 1e-4, "threshold": 1e-4,
           "auto_mask_frac_loaded": side.get("train_mask_frac"), "auto_mask_frac_used": 0.0, "mock": True}, open(a.out, "w"))
print(f"PERM id={a.id} arm={arm} role={a.role} rel_err_tf32off={rel!r} pass={str(rel < 1e-4).lower()} (mock)")
