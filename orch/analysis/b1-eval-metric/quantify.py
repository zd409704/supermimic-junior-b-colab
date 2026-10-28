"""Descriptive quantification of B1 arms attempt-1 eval clip-failure (read-only; CPU).
Usage: python3 -I quantify.py <open-tree-root> <out.json>
Does NOT compute arm-level AULC or outcome under any alternative metric (see brief §4)."""
import json, sys, glob, os, re, statistics as st
root, out = sys.argv[1], sys.argv[2]
rows = []
for p in sorted(glob.glob(os.path.join(root, "logs/eval/*/it*/exec*/*_mask0.00.json"))):
    m = re.search(r"eval/b1(\w+?)_(attention|mlp_matched)_s(\d)_a1/it(\d+)/exec(\d)/", p)
    arm = {"HAxfer": "H-A-xfer", "HAscratch": "H-A-scratch", "HMxfer": "H-M-xfer", "HMscratch": "H-M-scratch",
           "HAfrozen": "H-A-frozen", "HAxfernoscale": "H-A-xfer-noscale"}[m.group(1)]
    d = json.load(open(p))
    rows.append(dict(arm=arm, seed=int(m.group(3)), it=int(m.group(4)), exec=int(m.group(5)),
                     failed=d["summary"]["failed"], R=d["summary"]["mean_norm_return"],
                     Rsw=d["summary"]["step_weighted_norm_return"],
                     clips={c["name"]: dict(frames=c["frames"], steps=c["steps"], nr=c["norm_return"],
                                            failed=c["failed"], fail_step=c["fail_step"]) for c in d["clips"]}))
json.dump(rows, open(out, "w"), indent=1)
print("evals", len(rows), "execs>1", sum(r["exec"] > 1 for r in rows))
# 1. failed-count histogram overall and per arm
from collections import Counter, defaultdict
print("failed hist", sorted(Counter(r["failed"] for r in rows).items()))
for arm in sorted({r["arm"] for r in rows}):
    rs = [r for r in rows if r["arm"] == arm]
    print(f"  {arm:18s} n={len(rs):3d} hist={sorted(Counter(r['failed'] for r in rs).items())}")
# 2. R by failed count
for k in sorted({r["failed"] for r in rows}):
    v = [r["R"] for r in rows if r["failed"] == k]
    print(f"failed={k}: n={len(v)} R mean={st.mean(v):.4f} min={min(v):.4f} max={max(v):.4f}")
# 3. per clip failure counts, fail_step and completion fraction
clips = sorted(rows[0]["clips"])
for c in clips:
    f = [r["clips"][c] for r in rows]
    fl = [x for x in f if x["failed"]]
    ok = [x for x in f if not x["failed"]]
    fs = sorted(x["fail_step"] for x in fl)
    print(f"clip {c:16s} frames={f[0]['frames']} failed {len(fl)}/{len(f)}", end="")
    if fs: print(f" fail_step min={fs[0]} med={st.median(fs)} max={fs[-1]} distinct={len(set(fs))}"
                 f" frac_med={st.median(x['fail_step']/x['frames'] for x in fl):.4f}", end="")
    if fl: print(f" nr|failed mean={st.mean(x['nr'] for x in fl):.4f}", end="")
    if ok: print(f" nr|ok mean={st.mean(x['nr'] for x in ok):.4f}", end="")
    print()
# 4. fail-step buckets
b = Counter()
for r in rows:
    for c, x in r["clips"].items():
        if x["failed"]:
            fr = x["fail_step"] / x["frames"]
            b[(c, "<1%" if fr < .01 else "<10%" if fr < .1 else "<50%" if fr < .5 else ">=50%")] += 1
print("fail-frac buckets", sorted(b.items()))
# 5. failure pattern signatures
print("pattern", sorted(Counter(tuple(c for c in clips if r["clips"][c]["failed"]) for r in rows).items(), key=lambda t: -t[1]))
# 6. per-arm per-seed per-it table
for arm in sorted({r["arm"] for r in rows}):
    for s in sorted({r["seed"] for r in rows if r["arm"] == arm}):
        rs = sorted([r for r in rows if r["arm"] == arm and r["seed"] == s], key=lambda r: r["it"])
        print(f"{arm:18s} s{s} failed=" + " ".join(str(r["failed"]) for r in rs) + "  R=" + " ".join(f"{r['R']:.3f}" for r in rs))
# 7. completion-weighted per-step sums: share of total eval steps and frames survived
tot_frames = sum(x["frames"] for x in rows[0]["clips"].values())
cov = [sum(x["steps"] for x in r["clips"].values()) / tot_frames for r in rows]
print(f"survived-frame coverage mean={st.mean(cov):.4f} min={min(cov):.4f} max={max(cov):.4f}")
for k in sorted({r["failed"] for r in rows}):
    v = [c for c, r in zip(cov, rows) if r["failed"] == k]
    print(f"  coverage | failed={k}: mean={st.mean(v):.4f}")
# 8. correlation R vs coverage (Pearson) across all evals
def pear(a, b):
    ma, mb = st.mean(a), st.mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    return num / (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** .5
print(f"pearson(R, coverage)={pear([r['R'] for r in rows], cov):.4f}")
print(f"pearson(R, failed)={pear([r['R'] for r in rows], [r['failed'] for r in rows]):.4f}")
# 9. (appended) term saturation in nominal (failed==1) evals vs all-failed evals; re-reads raw JSONs
mx = {"motion_global_root_pos": .01, "motion_global_root_ori": .01, "motion_body_pos": .02, "motion_body_ori": .02,
      "motion_body_lin_vel": .02, "motion_body_ang_vel": .02}
terms = []
for p in sorted(glob.glob(os.path.join(root, "logs/eval/*/it*/exec*/*_mask0.00.json"))):
    d = json.load(open(p)); terms.append((d["summary"]["failed"], d["summary"]["terms"]))
for k in list(mx) + ["action_rate_l2", "joint_limit"]:
    for f in (1, 4):
        v = [t[k] for ff, t in terms if ff == f]
        print(f"term {k:24s} failed={f} mean={st.mean(v):.5f} sd={st.pstdev(v):.5f}" + (f" sat={st.mean(v)/mx[k]:.3f}" if k in mx else ""))
