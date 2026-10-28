"""P4-prep SIGINT check (PLAN §2.2 (f)): stand-in for train_entry.py --mode upstream.

Mimics the frozen wrapper: prints log lines up to `it 1600 |`, writes logs/<run>/ckpt_0001600.pt, keeps
"training", and writes logs/<run>/junior_policy.json in a `finally:` block (as train_entry.run_upstream does).
"""
import json, os, signal, sys, time
from pathlib import Path

run_dir = Path(sys.argv[1])
run_dir.mkdir(parents=True, exist_ok=True)
print(f"[dummy] pid={os.getpid()} SIGINT handler at start: {signal.getsignal(signal.SIGINT)!r}", flush=True)
try:
    for it in range(50, 1601, 50):
        print(f"it {it} | 0.00 h | 0.0 it/s | updates 0 | dummy", flush=True)
        time.sleep(0.05)
    (run_dir / "ckpt_0001600.pt").write_bytes(b"\0" * 4096)
    it = 1600
    while True:  # training continues past the endpoint until the harness stop
        it += 1
        time.sleep(0.5)
finally:
    (run_dir / "junior_policy.json").write_text(json.dumps({"finally": True, "pid": os.getpid()}))
    print("[dummy] finally ran, sidecar written", flush=True)
