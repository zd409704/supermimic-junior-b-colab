"""CR-B2-1 (g) CPU tests (spikes/B2/PLAN.md §2.3 (g)). No simulator, no motion data.

Run:  python packets/P5/tests/test_p5_prep.py      (or python -m pytest packets/P5/tests -q)
Script mode prints `PASS <test>` / `FAIL <test>: <error>` per test and a final
`P5_PREP_TESTS pass=<n> fail=<m> total=<t>` line; exit code 0 iff every test passed.

PLAN (g) item -> test:
  mlp_mind shapes                                   test_g1_mlp_mind_shapes
  mlp_mind params within +-5% of 464001             test_g2_mlp_mind_params_within_5pct
  mlp_mind indicator = mask                         test_g3_mlp_mind_indicator_equals_mask
  identical streams attention / mlp_matched / mlp_mind, same seed + call sequence
                                                    test_g4_streams_identical_across_arms, test_g8_eval_wrapper_end_to_end
  exactly k True per row                            test_g5_exactly_k_per_row
  nesting f=0.1 subset of f=0.2                     test_g6_nesting
  permutation script: attention < 1e-4, break for mlp_matched and attention[id_mode=index]
                                                    test_g7_perm_script_cpu
  frozen 14-test CPU smoke still passes             test_g9_frozen_smoke_still_passes
Supporting tests: configs (a), registration order (b), frozen hashes, driver helper (e), common prefix.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import types
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
P5 = HERE.parent
ROOT = P5.parents[1]
CODE = ROOT / "code"
for p in (str(CODE), str(P5)):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np  # noqa: E402
import torch  # noqa: E402
import torch.nn as nn  # noqa: E402

import mlp_mind  # noqa: E402

mlp_mind.register()

import p5_eval_entry  # noqa: E402  (imports the frozen eval_entry after registration)
import eval_entry  # noqa: E402
import maskstream  # noqa: E402
import perm_check  # noqa: E402
import train_entry  # noqa: E402
from attention_policy import AttentionDecoder, count_params  # noqa: E402
from mlp_baseline import MLPDecoder, _column_keep  # noqa: E402

J, H, L = 29, 10, 32
OBS = H * (3 * J + 6)
CFG = train_entry.load_config(ROOT / "configs" / "b0_microbench.yaml")
CFG_SYN = {**CFG, "attention": {**CFG["attention"], "morphology": "synthetic"}}

# 12 D-004 files (packets/P1/FREEZE_MANIFEST.md) + 6 CR-B0-1 files (packets/P4/MANIFEST_ADDENDUM.md)
FROZEN = {
    "code/attention_policy.py": "2f7c5431787073566de89a711b2988b1050369c395e992ec602578aa50d5de64",
    "code/descriptor_v2.py": "f313bddf8e5468e513868a95658814105c5463870ab4306e8ffbcec6af848f00",
    "code/eval_entry.py": "4406a0385e0156034b423f575f8bce2e5433474898b7b50e1ae048af5a4431e3",
    "code/mlp_baseline.py": "d70c0fa1bf5885088d458383a091134d4573ea485f5aa7d2fc35c51c7700caa1",
    "code/requirements-smoke.txt": "0c234dd458586b6c165c9678058f4de6ad3bc701b11da8110ac8cdfe17270dae",
    "code/tests/test_smoke.py": "d190f67cf288eb92f9c8cf10eb106dd2922f56821cb20ff24e4f697e9f7fce7b",
    "code/tools/make_notebook.py": "096520611cf90c285140f63830e95a2f4df6b33de561f15d14972396729984f9",
    "code/train_entry.py": "fe585ffe935af132728bc69d4f7ccf044e8fc77b013566b9895af0f3d2e19431",
    "code/vendor/NOTES.md": "5f18b09c0b6208a955bd18a27706b46a8a0192bc1b92e85b78e9ae90354226fe",
    "configs/colab_smoke.yaml": "70cee6244d39ce861d9e318f354bc1473a179a55fddbbd0d91c036911317bfc7",
    "docs/COLAB_RUNBOOK.md": "302c27409e836d044659ff98af216a61865acec602951686bee377045c330e6d",
    "notebooks/colab_smoke.ipynb": "5b59be6a8f5467f6f6f2b60f11a42207293436278e07f3f25a3c7de35735f6e8",
    "configs/b0_microbench.yaml": "d19e9297bf90530859c25aedc5ed3834064a7fc19838933def6b653e8a4cd495",
    "configs/b0_microbench_lr05.yaml": "283030054d53cc5b7002d696d9b466ae669b08d2a03960cabab8060fabde4729",
    "packets/P4/BUNDLE_CONTRACT.md": "07e565226cc25d8c84b7a3f5701d1264d6aa8549e3808b71c9d0c817bf729634",
    "packets/P4/UPSTREAM_FACTS.md": "0e9cc73a98d7f006647e98210fa9014ee05811b112df8993a6e9b77215b5583f",
    "packets/P4/b0_driver.sh": "e87478fd16b7b41bde302cfbf3bda5d45534e58278a35e8a09e8d102218af3be",
    "packets/P4/b0_driver_helper.py": "f43d8f5db9ad45fe6850aa87a4f549be56c6265b27d2e81bbe7dc840adf34b42",
}


def _batch(n=8, seed=0):
    g = torch.Generator().manual_seed(seed)
    return torch.tanh(torch.randn(n, L, generator=g)), torch.randn(n, OBS, generator=g)


def _decoders():
    torch.manual_seed(0)
    return {arm: train_entry.build_decoder(arm, CFG_SYN).eval() for arm in ("attention", "mlp_matched", "mlp_mind")}


def _stream_of(dec, seed, frac, calls=25, n=4):
    """Drive one decoder through `calls` auto-masked forward calls under a fresh condition; return packed stream."""
    st = maskstream.MaskStream()
    maskstream.install(st)
    dec.auto_mask_frac = frac
    st.begin(seed, frac)
    with torch.no_grad():
        for c in range(calls):
            z, o = _batch(n, seed=1000 + c)
            dec(z, o)
    meta, packed = st.record()
    st.seed = None
    dec.auto_mask_frac = 0.0
    return meta, packed, [m.copy() for m in st.masks]


# ------------------------------------------------------------------------------------------------ (a) configs
def test_a_configs_named_changes_only():
    base = (ROOT / "configs" / "b0_microbench.yaml").read_text().splitlines()
    for name, changed in (("b2_idx", {4: "run_name: b2idx", 15: "  id_mode: index             # morph (Junior-B arm) | index (ablation, breaks permutation equivariance)"}),
                          ("b2_mtrain", {4: "run_name: b2mt", 20: "  train_mask_frac: 0.1       # optional train-time token-drop augmentation (0 = off for B0)"})):
        new = (ROOT / "configs" / f"{name}.yaml").read_text().splitlines()
        assert len(new) == len(base), name
        diff = {i: ln for i, (ln, b) in enumerate(zip(new, base)) if ln != b}
        assert diff == changed, (name, diff)
    b0 = train_entry.tyro_argv(CFG, "attention")
    for name, run in (("b2_idx", "b2idx"), ("b2_mtrain", "b2mt")):
        c = train_entry.load_config(ROOT / "configs" / f"{name}.yaml")
        for arm in ("attention", "mlp_mind"):
            a = train_entry.tyro_argv({**c, "seed": 2}, arm)
            assert a[:4] == ["--run-name", f"{run}_{arm}_s2", "--seed", "2"] and a[4:] == b0[4:], (name, a)
    assert train_entry.load_config(ROOT / "configs" / "b2_idx.yaml")["attention"]["id_mode"] == "index"
    assert train_entry.load_config(ROOT / "configs" / "b2_mtrain.yaml")["b2"]["train_mask_frac"] == 0.1


def test_frozen_files_unchanged():
    bad = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FROZEN
           if hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != FROZEN[f]}
    assert not bad, bad


# ------------------------------------------------------------------------------------------------ (b) mlp_mind
def test_b_registration_and_sidecar():
    assert "mlp_mind" in train_entry.POLICY_ARMS and "mlp_mind" in eval_entry.POLICY_ARMS
    assert train_entry.POLICY_ARMS[:3] == ("attention", "mlp_matched", "mlp_upstream")
    assert eval_entry.build_decoder is train_entry.build_decoder  # eval_entry bound the wrapped factory
    frozen = train_entry.build_decoder.__wrapped__
    for arm in ("attention", "mlp_matched", "mlp_upstream"):  # frozen arms: same class and size as the frozen factory
        a, b = train_entry.build_decoder(arm, CFG_SYN), frozen(arm, CFG_SYN)
        assert type(a) is type(b) and count_params(a) == count_params(b), arm
    mlp_mind.register()  # idempotent
    assert train_entry.POLICY_ARMS.count("mlp_mind") == 1
    # sidecar via the frozen install_upstream_policy (fake upstream module layout, as the frozen smoke test does)
    pkg = _fake_pkg()
    with patch.dict(sys.modules, pkg):
        cfg = train_entry.load_config(ROOT / "configs" / "b2_mtrain.yaml")
        cfg = {**cfg, "attention": {**cfg["attention"], "morphology": "synthetic"}}
        info = train_entry.install_upstream_policy("mlp_mind", cfg, ("supermimic.eval.benchmark",))
        pol = sys.modules["supermimic.eval.benchmark"].Policy(_PolicyCfg())
    assert isinstance(pol.decoder, mlp_mind.MLPMindDecoder) and pol.decoder.auto_mask_frac == 0.1
    assert info["policy"] == "mlp_mind" and info["train_mask_frac"] == 0.1
    assert info["params"] == count_params(pol.decoder) and info["mlp_hidden"] == list(pol.decoder.cfg.hidden)
    # registration after eval_entry import must be refused in a fresh interpreter
    code = ("import sys; sys.path[:0]=[%r,%r]; import eval_entry, mlp_mind\n"
            "try:\n    mlp_mind.register(); print('NO_ERROR')\nexcept RuntimeError: print('REFUSED')") % (str(CODE), str(P5))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(ROOT)).stdout
    assert out.strip().endswith("REFUSED"), out


def test_g1_mlp_mind_shapes():
    dec = train_entry.build_decoder("mlp_mind", CFG_SYN)
    assert isinstance(dec, mlp_mind.MLPMindDecoder) and isinstance(dec, MLPDecoder)
    assert dec.mlp[0].in_features == L + OBS + J and dec.mlp[-1].out_features == J
    z, o = _batch(8)
    m = maskstream.FROZEN_RANDOM_TOKEN_MASK(8, J, 0.2, generator=torch.Generator().manual_seed(3))
    for kw in ({}, {"token_mask": m}, {"token_mask": m, "morphology": torch.zeros(J, 16)}):
        a = dec(z, o, **kw)
        assert a.shape == (8, J) and torch.isfinite(a).all()
    a = dec(z, o, token_mask=m)
    a.square().sum().backward()
    assert all(p.grad is not None for p in dec.parameters())


def test_g2_mlp_mind_params_within_5pct():
    att = train_entry.build_decoder("attention", CFG_SYN)
    assert count_params(att) == mlp_mind.ATTENTION_PARAMS == 464001
    dec = train_entry.build_decoder("mlp_mind", CFG_SYN)
    n = count_params(dec)
    assert abs(n - 464001) / 464001 <= 0.05, n
    assert dec.cfg.hidden == mlp_mind.mind_hidden(464001) == (376, 188, 94, 47) and n == 467491, (dec.cfg.hidden, n)
    # same tapered family as mlp_matched (frozen taper), different width because the input is larger
    from mlp_baseline import taper
    assert dec.cfg.hidden == taper(dec.cfg.hidden[0])
    assert train_entry.build_decoder("mlp_matched", CFG_SYN).cfg.hidden == (384, 192, 96, 48)


def test_g3_mlp_mind_indicator_equals_mask():
    dec = train_entry.build_decoder("mlp_mind", CFG_SYN).eval()
    seen = []
    h = dec.mlp[0].register_forward_pre_hook(lambda _m, args: seen.append(args[0].detach().clone()))
    z, o = _batch(6)
    m = maskstream.FROZEN_RANDOM_TOKEN_MASK(6, J, 0.1, generator=torch.Generator().manual_seed(5))
    with torch.no_grad():
        dec(z, o, token_mask=m)
        dec(z, o)
        st = maskstream.MaskStream()
        maskstream.install(st)
        dec.auto_mask_frac = 0.2
        st.begin(7100, 0.2)
        dec(z, o)
        drawn = torch.from_numpy(st.masks[-1])
        st.seed = None
        dec.auto_mask_frac = 0.0
    h.remove()
    x_masked, x_plain, x_auto = seen
    assert torch.equal(x_masked[:, -J:], m.float()) and torch.equal(x_plain[:, -J:], torch.zeros(6, J))
    assert torch.equal(x_auto[:, -J:], drawn.float()) and int(drawn.sum(1).unique()) == 6
    assert torch.equal(x_masked[:, :L], z)
    keep = _column_keep(m, J, H)
    assert torch.equal(x_masked[:, L:L + OBS], o * dec.scale * keep) and torch.equal(x_plain[:, L:L + OBS], o * dec.scale)


# ------------------------------------------------------------------------------------------------ (c) mask stream
def test_g4_streams_identical_across_arms():
    decs = _decoders()
    rng0 = torch.get_rng_state()
    for frac in (0.1, 0.2):
        for seed in (7100, 7101, 7102):
            res = {arm: _stream_of(d, seed, frac) for arm, d in decs.items()}
            shas = {arm: r[0]["sha256"] for arm, r in res.items()}
            assert len(set(shas.values())) == 1, (frac, seed, shas)
            ref = res["attention"][1]
            assert all(np.array_equal(r[1], ref) for r in res.values())
            assert res["attention"][0]["calls"] == 25 and res["attention"][0]["rows_per_call"] == 4
    assert torch.equal(rng0, torch.get_rng_state()), "mask stream must not touch the global RNG"
    a = _stream_of(decs["attention"], 7100, 0.2)[1]
    b = _stream_of(decs["attention"], 7101, 0.2)[1]
    assert not np.array_equal(a, b), "different seeds must give different streams"


def test_g5_exactly_k_per_row():
    decs = _decoders()
    for frac, k in ((0.1, 3), (0.2, 6)):
        assert maskstream.k_of(frac, J) == k
        for arm, d in decs.items():
            meta, packed, masks = _stream_of(d, 7101, frac, calls=40)
            assert meta["true_per_row"] == [k] and meta["k"] == k, (arm, meta)
            unpacked = np.unpackbits(packed, axis=-1)[..., :J].astype(bool)
            assert np.array_equal(unpacked, np.stack(masks)) and (unpacked.sum(-1) == k).all()


def test_g6_nesting():
    decs = _decoders()
    for seed in (7100, 7101, 7102):
        for arm, d in decs.items():
            _m1, _p1, s1 = _stream_of(d, seed, 0.1, calls=30)
            _m2, _p2, s2 = _stream_of(d, seed, 0.2, calls=30)
            for c, (a, b) in enumerate(zip(s1, s2)):
                assert not (a & ~b).any(), (seed, arm, c)


def test_c_common_prefix_and_explicit_generator_passthrough():
    decs = _decoders()
    _ma, pa, _ = _stream_of(decs["attention"], 7102, 0.2, calls=40)
    _mb, pb, _ = _stream_of(decs["mlp_mind"], 7102, 0.2, calls=17)
    assert np.array_equal(pa[:17], pb)
    st = maskstream.MaskStream()
    maskstream.install(st)
    import attention_policy
    m = attention_policy.random_token_mask(4, J, 0.2, generator=torch.Generator().manual_seed(7))
    ref = maskstream.FROZEN_RANDOM_TOKEN_MASK(4, J, 0.2, generator=torch.Generator().manual_seed(7))
    assert torch.equal(m, ref) and st.masks == []
    try:
        attention_policy.random_token_mask(4, J, 0.2)
        raise AssertionError("draw outside a condition must raise")
    except RuntimeError:
        pass


# --------------------------------------------------------------------- (c) eval wrapper end to end (fake upstream)
@dataclass
class _PolicyCfg:
    latent_dim: int = 32
    history: int = 10
    obs_term_scale: tuple = (1.0, 5.0, 2.0, 1.0, 1.0)


class _Policy(nn.Module):  # mirrors upstream: a = dec(enc(goal), obs_hist)
    def __init__(self, cfg):
        super().__init__()
        self.encoders = nn.ModuleDict({"motion": nn.Linear(680, cfg.latent_dim)})
        self.decoder = nn.Linear(cfg.latent_dim + 930, J)

    def forward(self, obs_hist, goal, interface="motion"):
        return self.decoder(torch.tanh(self.encoders[interface](goal)), obs_hist)


def _fake_pkg():
    names = ("supermimic", "supermimic.policy", "supermimic.policy.nets", "supermimic.eval", "supermimic.eval.benchmark",
             "supermimic.training", "supermimic.training.loop")
    pkg = {n: types.ModuleType(n) for n in names}
    pkg["supermimic.policy.nets"].Policy = _Policy
    bench = pkg["supermimic.eval.benchmark"]
    bench.Policy = _Policy

    def load_policy_from_checkpoint(path, device):
        torch.manual_seed(1234)  # stand-in for weights: deterministic per checkpoint load
        pol = bench.Policy(_PolicyCfg()).to(device).eval()
        return pol, {"env": {"future_frames": 10, "anchor_obs": True}}

    bench.load_policy_from_checkpoint = load_policy_from_checkpoint
    return pkg


FAKE_EVAL_SCRIPT = textwrap.dedent('''
    """Stand-in for upstream scripts/eval_benchmark.py: 4 envs, one clip each, policy called once per loop step."""
    import json, os, sys
    import torch
    from supermimic.eval.benchmark import load_policy_from_checkpoint
    a = sys.argv[1:]
    out = a[a.index("--out") + 1]
    policy, cfg = load_policy_from_checkpoint(a[a.index("--ckpt") + 1], "cpu")
    print("Setting seed: 0"); torch.manual_seed(0)  # the env stack reseeds the global RNG per condition
    steps = [int(x) for x in os.environ["FAKE_CLIP_STEPS"].split(",")]
    names = ["dance1_subject1", "jumps1_subject1", "run1_subject2", "walk1_subject1"]
    with torch.no_grad():
        for t in range(max(steps)):
            policy(torch.randn(4, 930), torch.randn(4, 680))
            torch.rand(int(os.environ.get("FAKE_ENV_DRAWS", "3")))  # arm-dependent global RNG use must not matter
    clips = [{"name": n, "frames": 6000, "steps": s, "norm_return": 0.3, "failed": True, "fail_step": s,
              "terms": {"motion_body_pos": 0.01}} for n, s in zip(names, steps)]
    summ = {"clips": 4, "failed": 4, "mean_norm_return": 0.3, "step_weighted_norm_return": 0.3,
            "terms": {"motion_body_pos": 0.01}}
    open(out, "w").write(json.dumps({"summary": summ, "clips": clips}, indent=1))
    print("saved", out)
''')


def _fake_eval(tmp: Path, arm: str, steps: str, mask0_only=False, env_draws="3", cfg_name="b0_microbench.yaml"):
    repo = tmp / "repo"
    (repo / "scripts").mkdir(parents=True, exist_ok=True)
    (repo / "scripts" / "eval_benchmark.py").write_text(FAKE_EVAL_SCRIPT)
    run = tmp / "ckpts" / f"b0_{arm}_s0"
    run.mkdir(parents=True, exist_ok=True)
    (run / "ckpt_0001600.pt").write_bytes(b"fake")
    side = {"policy": arm, "attention": {**CFG["attention"], "morphology": "synthetic"}}
    (run / "junior_policy.json").write_text(json.dumps(side))
    cfg = copy.deepcopy(train_entry.load_config(ROOT / "configs" / cfg_name))
    cfg["upstream"]["repo_dir"] = str(repo)
    out = tmp / "eval" / arm / ("mask0" if mask0_only else "full")
    with patch.dict(sys.modules, _fake_pkg()), patch.object(eval_entry.torch.cuda, "is_available", return_value=True), \
            patch.dict(os.environ, {"FAKE_CLIP_STEPS": steps, "FAKE_ENV_DRAWS": env_draws}):
        done = p5_eval_entry.run(run / "ckpt_0001600.pt", cfg, out, None, p5_eval_entry.MASK_SEEDS, mask0_only)
    return out, done, run.name


def test_g8_eval_wrapper_end_to_end():
    tmp = Path(tempfile.mkdtemp(prefix="p5eval_"))
    res = {}
    for arm, steps, draws in (("attention", "40,25,31,12", "3"), ("mlp_matched", "18,9,22,7", "11"),
                              ("mlp_mind", "40,25,31,12", "0")):
        out, done, run = _fake_eval(tmp, arm, steps, env_draws=draws)
        files = sorted(p.name for p in out.iterdir())
        conds = ["mask0.00_ms0"] + [f"mask{f}_ms{s}" for s in (7100, 7101, 7102) for f in ("0.10", "0.20")]
        assert [d["cond"] for d in done] == conds
        want = sorted([f"{run}_{arm}_{c}.json" for c in conds] + [f"maskstream_{c}.{e}" for c in conds for e in ("npz", "json")])
        assert files == want, files
        for c in conds:
            meta = json.loads((out / f"maskstream_{c}.json").read_text())
            js = json.loads((out / f"{run}_{arm}_{c}.json").read_text())
            calls = max(cl["steps"] for cl in js["clips"])
            if c == "mask0.00_ms0":
                assert meta["calls"] == 0 and meta["k"] == 0
            else:
                assert meta["calls"] == calls and meta["rows_per_call"] == 4 and meta["seed"] == int(c.split("_ms")[1])
                assert meta["true_per_row"] == [3 if "0.10" in c else 6]
                pk = maskstream.load_packed(out / f"maskstream_{c}.npz")
                assert hashlib.sha256(pk.tobytes()).hexdigest() == meta["sha256"] and pk.shape == (calls, 4, 4)
        res[arm] = out
    for c in [f"mask{f}_ms{s}" for s in (7100, 7101, 7102) for f in ("0.10", "0.20")]:
        streams = {arm: maskstream.load_packed(d / f"maskstream_{c}.npz") for arm, d in res.items()}
        n = min(len(s) for s in streams.values())
        assert all(np.array_equal(s[:n], streams["attention"][:n]) for s in streams.values()), c
        assert np.array_equal(streams["attention"], streams["mlp_mind"]), c
    for s in (7100, 7101, 7102):  # nesting in the recorded files
        a = np.unpackbits(maskstream.load_packed(res["mlp_mind"] / f"maskstream_mask0.10_ms{s}.npz"), axis=-1)
        b = np.unpackbits(maskstream.load_packed(res["mlp_mind"] / f"maskstream_mask0.20_ms{s}.npz"), axis=-1)
        assert not (a & ~b).any()
    out, done, run = _fake_eval(tmp, "mlp_mind", "5,6,7,8", mask0_only=True, cfg_name="b2_mtrain.yaml")
    assert [d["cond"] for d in done] == ["mask0.00_ms0"]
    assert sorted(p.name for p in out.iterdir()) == sorted([f"{run}_mlp_mind_mask0.00_ms0.json", "maskstream_mask0.00_ms0.npz",
                                                            "maskstream_mask0.00_ms0.json"])
    assert json.loads((out / "maskstream_mask0.00_ms0.json").read_text())["calls"] == 0  # train_mask_frac 0.1 overridden to 0


# ------------------------------------------------------------------------------------------------ (d) PERM script
def test_g7_perm_script_cpu():
    tmp = Path(tempfile.mkdtemp(prefix="p5perm_"))
    got = {}
    for name, extra in (("attention", []), ("mlp_matched", []), ("mlp_mind", []), ("attention_index", ["--id-mode", "index"])):
        arm = name.split("_index")[0]
        out = tmp / f"{name}.json"
        p = subprocess.run([sys.executable, str(P5 / "perm_check.py"), "--mode", "cpu", "--policy", arm, *extra,
                            "--out", str(out)], capture_output=True, text=True, cwd=str(ROOT))
        assert p.returncode == 0, p.stderr
        got[name] = json.loads(out.read_text())
        print(p.stdout.strip())
    assert got["attention"]["rel_err_tf32off"] < 1e-4 and got["attention"]["pass"] is True
    assert got["attention"]["rel_err_masked"] < 1e-4 and got["attention"]["auto_mask_frac_used"] == 0.0
    for name in ("mlp_matched", "attention_index", "mlp_mind"):  # reported break
        assert got[name]["rel_err_tf32off"] >= 1e-4 and got[name]["pass"] is False, (name, got[name]["rel_err_tf32off"])
    assert got["attention_index"]["id_mode"] == "index"
    # auto_mask_frac loaded from a b2mt sidecar (0.1) is forced to 0.0 before any call
    dec = train_entry.build_decoder("attention", CFG_SYN)
    dec.auto_mask_frac = 0.1
    r = perm_check.check(dec, torch.device("cpu"))
    assert r["auto_mask_frac_loaded"] == 0.1 and r["auto_mask_frac_used"] == 0.0 and r["pass"]


# ------------------------------------------------------------------------------------------------ frozen smoke
def test_g9_frozen_smoke_still_passes():
    p = subprocess.run([sys.executable, str(CODE / "tests" / "test_smoke.py")], capture_output=True, text=True, cwd=str(ROOT))
    lines = p.stdout.splitlines()
    n_pass = sum(1 for ln in lines if ln.startswith("PASS"))
    n_skip = sum(1 for i, ln in enumerate(lines) if ln.startswith("PASS") and i and lines[i - 1].startswith("SKIP"))
    # 3 skips where mujoco or the owner asset is absent (the tarball ships no asset: the venue's 14/3 rule);
    # 0 skips on the research box, which has both.
    try:
        import mujoco  # noqa: F401
        have = bool(sorted((ROOT / "assets" / "home_humanoid_mjcf").glob("*.xml")))
    except ImportError:
        have = False
    want_skip = 0 if have else 3
    print(f"frozen smoke: returncode={p.returncode} pass_lines={n_pass} skip_before_pass={n_skip} expected=14/{want_skip}")
    assert p.returncode == 0 and n_pass == 14 and n_skip == want_skip, (p.returncode, n_pass, n_skip, p.stderr[-2000:])


# ------------------------------------------------------------------------------------------------ (e) driver helper
def _helper(*args):
    return subprocess.run([sys.executable, "-I", str(P5 / "b2_driver_helper.py"), *args], capture_output=True, text=True)


def test_e_driver_helper_schedule_and_evalcheck():
    tmp = Path(tempfile.mkdtemp(prefix="p5helper_"))
    st = tmp / "state.txt"
    st.write_text("PART 1 x\n")
    seq = []
    for _ in range(40):
        line = _helper("next", "--state", str(st), "--total-hours", "1.0").stdout.strip()
        seq.append(line)
        if line == "DONE":
            break
        p = line.split()
        if p[0] == "UEVAL":
            st.write_text(st.read_text() + f"UEVAL {p[1]} ok exec1\n")
        elif p[0] == "UPERM":
            st.write_text(st.read_text() + f"PERM b2u_{p[1]} 0\n")
        elif p[0] == "CELL":
            aid = f"{p[1]}_{p[3]}_s{p[4]}_a{p[5]}"
            cls = "INFRA" if aid == "b2mt_mlp_mind_s1_a1" else ("DIV" if aid == "b2idx_attention_s0_a1" else "completed")
            st.write_text(st.read_text() + f"ATTEMPT {aid} {cls} {str(cls == 'DIV').lower()} {str(cls == 'completed').lower()}\n")
            if cls == "completed" and aid != "b2mt_attention_s1_a1":
                st.write_text(st.read_text() + f"EVALDONE {aid}\n")
        elif p[0] == "FINISH":
            st.write_text(st.read_text() + f"EVALDONE {p[1]}\n")
    u = [f"b0_{a}_s{s}_a1" for s in (0, 1, 2) for a in ("attention", "mlp_matched")]
    want = [f"UEVAL {x}" for x in u] + [f"UPERM {x}" for x in u]
    cells = [("b2mt", "b2_mtrain", a, s) for s in (0, 1, 2) for a in ("attention", "mlp_mind")] + \
            [("b2idx", "b2_idx", "attention", s) for s in (0, 1, 2)]
    for tag, cfg, arm, s in cells:
        want.append(f"CELL {tag} /content/junior/configs/{cfg}.yaml {arm} {s} 1 1")
        if (tag, arm, s) == ("b2mt", "attention", 1):  # evals interrupted (no EVALDONE): finished before the next cell
            want.append("FINISH b2mt_attention_s1_a1 b2mt /content/junior/configs/b2_mtrain.yaml attention false")
        if (tag, arm, s) == ("b2mt", "mlp_mind", 1):
            want.append(f"CELL {tag} /content/junior/configs/{cfg}.yaml {arm} {s} 2 0")  # INFRA -> attempt 2, no retry pair
    want.append("DONE")
    assert seq == want, "\n".join(seq)
    # spend cap: checked before every new work item (review r1 #4), a started cell still finishes its retries
    st0 = tmp / "state0.txt"
    st0.write_text("PART 1 x\n")
    assert _helper("next", "--state", str(st0), "--total-hours", "6.5").stdout.strip() == "SPENDCAP"
    st0.write_text("".join(f"UEVAL {x} ok exec1\n" for x in u))
    assert _helper("next", "--state", str(st0), "--total-hours", "6.5").stdout.strip() == "SPENDCAP"
    st2 = tmp / "state2.txt"
    st2.write_text("".join(f"UEVAL {x} ok exec1\nPERM b2u_{x} 0\n" for x in u) + "ATTEMPT b2mt_attention_s0_a1 INFRA false false\n")
    assert _helper("next", "--state", str(st2), "--total-hours", "6.5").stdout.split()[:6] == ["CELL", "b2mt", "/content/junior/configs/b2_mtrain.yaml", "attention", "0", "2"]
    st2.write_text(st2.read_text() + "ATTEMPT b2mt_attention_s0_a2 completed false true\nEVALDONE b2mt_attention_s0_a2\n")
    assert _helper("next", "--state", str(st2), "--total-hours", "6.5").stdout.strip() == "SPENDCAP"
    # evalcheck
    d = tmp / "exec1"
    d.mkdir()
    for f in __import__("b2_driver_helper").expected_files("b2mt_attention_s0", "attention", "full"):
        (d / f).write_text("x")
    (d / "eval.log").write_text("[eval_entry] x\nexit=0\n")
    assert _helper("evalcheck", "--dir", str(d), "--run", "b2mt_attention_s0", "--arm", "attention", "--mode", "full").returncode == 0
    (d / "maskstream_mask0.20_ms7102.npz").unlink()
    assert _helper("evalcheck", "--dir", str(d), "--run", "b2mt_attention_s0", "--arm", "attention", "--mode", "full").returncode == 1
    assert _helper("evalcheck", "--dir", str(d), "--run", "b2mt_attention_s0", "--arm", "attention", "--mode", "mask0").returncode == 0
    (d / "eval.log").write_text("exit=1\n")
    assert _helper("evalcheck", "--dir", str(d), "--run", "b2mt_attention_s0", "--arm", "attention", "--mode", "mask0").returncode == 1
    # every file present but no exit record (an execution killed without a record): a next exec is NOT authorized
    (d / "eval.log").write_text("[eval_entry] x\n")
    assert _helper("evalcheck", "--dir", str(d), "--run", "b2mt_attention_s0", "--arm", "attention", "--mode", "mask0").returncode == 2
    # a missing file authorizes the next exec even without an exit record
    assert _helper("evalcheck", "--dir", str(d), "--run", "b2mt_attention_s0", "--arm", "attention", "--mode", "full").returncode == 1


if __name__ == "__main__":
    n_pass = n_fail = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name, flush=True)
                n_pass += 1
            except Exception as e:  # noqa: BLE001
                import traceback
                traceback.print_exc()
                print(f"FAIL {name}: {type(e).__name__}: {e}", flush=True)
                n_fail += 1
    print(f"P5_PREP_TESTS pass={n_pass} fail={n_fail} total={n_pass + n_fail}")
    sys.exit(0 if n_fail == 0 else 1)
