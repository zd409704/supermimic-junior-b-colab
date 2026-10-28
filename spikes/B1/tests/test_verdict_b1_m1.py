"""CPU fixture tests for verdict_b1.py v1.1 M1 mode (AMENDMENT-M1-eval-metric.md). Synthetic fixtures only.
Run: python3 -m unittest -v test_verdict_b1_m1 (in this dir)."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_fixture_b1 as F  # noqa: E402

V = F.V
FR = dict(V.M1_FRAMES)
AMEND = os.environ.get("B1_M1_AMENDMENT")  # optional: the sealed amendment (else a temp stand-in is pinned)


def clips_nominal(r):
    """All non-dance clips survive; dance1 ends at the defect frame 5336. Every clip norm_return = r -> R_full = r."""
    out = []
    for n, fr in FR.items():
        st = V.M1_W if n == V.M1_DANCE else fr
        out.append({"name": n, "frames": fr, "steps": st, "norm_return": r, "failed": st < fr,
                    "fail_step": st if st < fr else -1, "terms": {}})
    return out


def ejson(clips):
    m = sum(c["norm_return"] for c in clips) / len(clips)
    return {"summary": {"clips": len(clips), "failed": sum(bool(c["failed"]) for c in clips), "mean_norm_return": m,
                        "step_weighted_norm_return": m, "terms": {}}, "clips": clips}


def m1_files(spec, override=None):
    """F.files_of with every scored eval JSON replaced by an M1-shaped one; override(run, it, r) -> clips or None."""
    files = F.files_of(spec)
    pat = re.compile(r"^logs/eval/(?P<aid>.+)_a\d+/it(?P<it>\d{7})/exec\d/(?P<run>.+)_ckpt_\d{7}_mask0\.00\.json$")
    for k in list(files):
        m = pat.match(k)
        if not m:
            continue
        r = json.loads(files[k])["summary"]["mean_norm_return"]
        clips = (override(m["run"], int(m["it"]), r) if override else None) or clips_nominal(r)
        files[k] = json.dumps(ejson(clips)).encode()
    return files


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="b1m1t-")
        if AMEND:
            self.amend = AMEND
        else:
            self.amend = os.path.join(self.tmp, "AMENDMENT-M1-standin.md")
            open(self.amend, "w").write("stand-in\n")
            self._old = V.M1_AMENDMENT_SHA256
            V.M1_AMENDMENT_SHA256 = hashlib.sha256(open(self.amend, "rb").read()).hexdigest()

        self._dep = V.M1_DEPOSIT_SHA256

    def tearDown(self):
        V.M1_DEPOSIT_SHA256 = self._dep
        if not AMEND:
            V.M1_AMENDMENT_SHA256 = self._old

    def spec(self, **bases):
        b = {"H-A-scratch": 0.30, "H-A-xfer": 0.40, "H-M-xfer": 0.33, "H-M-scratch": 0.31, "H-A-frozen": 0.20,
             "H-A-xfer-noscale": 0.38}
        b.update(bases)
        return F.default_spec(b)

    def run_m1(self, spec=None, files=None, override=None, m1=True, out=None, runs_log=None, pin=True, n_dep=1):
        seal_log = os.path.join(self.tmp, "seal.log")
        tgz = F.write_tgz(os.path.join(self.tmp, f"b1arms-m1-{len(os.listdir(self.tmp))}.tgz"),
                          files if files is not None else m1_files(spec or self.spec(), override))
        sha = F.seal(seal_log, tgz)
        if pin:
            V.M1_DEPOSIT_SHA256 = sha
        out = out or os.path.join(self.tmp, "results-M1.json")
        argv = ["--deposit", tgz] * n_dep + ["--tarball-sha", F.TARBALL_SHA, "--seal-log", seal_log, "--out", out,
                "--runs-log", runs_log or os.path.join(self.tmp, "runs-M1.log")]
        if m1:
            argv += ["--amendment-m1", self.amend]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            V.main(argv)
        lines = buf.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        return json.load(open(out)), lines[0]


class TestM1(Base):
    def test_m01_default_mode_is_v10(self):
        r, line = self.run_m1(m1=False, out=os.path.join(self.tmp, "results.json"))
        self.assertTrue(line.startswith("B1_VERDICT verdict=PASS outcome=SIGNAL_STRONG"))
        self.assertNotIn("label", r)

    def test_m02_line_and_shape(self):
        r, line = self.run_m1()
        self.assertRegex(line, r"^B1_M1_VERDICT label=post-hoc-M1 verdict=PASS outcome=SIGNAL_STRONG robust=true failing=\[\] ")
        for k in ("S-excl=", "S-full=", "S-d10=", "S-ratio=", "v10_outcome=INCONCLUSIVE", "plan=1088752b", "amendment="):
            self.assertIn(k, line)
        self.assertEqual(r["label"], "post-hoc re-score (M1)")
        self.assertTrue(r["v10_recomputed_line"].startswith("B1_VERDICT verdict=PASS outcome=SIGNAL_STRONG"))
        # the attempt-1 record is copied from the hash-verified file, never recomputed
        self.assertEqual(r["v10_record"]["sha256"], V.M1_V10_RECORD_SHA256)
        self.assertEqual(r["v10_record"]["outcome"], "INCONCLUSIVE")
        self.assertTrue(r["v10_recomputed_discrepancies"])  # fixture != real deposit
        self.assertEqual(r["verdict_line"], line)
        # nominal clips: R_full (window) == v1.0 R exactly
        run = r["primary"]["runs"]["b1HAxfer_attention_s0"]
        self.assertEqual(run["R_full"], [p["R_v10"] for p in run["points"].values()])
        self.assertEqual(r["primary"]["arms"]["H-A-xfer"]["n_collapse"], 0)

    def test_m03_amendment_sha_pinned(self):
        bad = os.path.join(self.tmp, "other.md")
        open(bad, "w").write("other\n")
        self.amend, keep = bad, self.amend
        with self.assertRaises(SystemExit):
            self.run_m1()
        self.amend = keep

    def test_m04_refuses_protected_outputs(self):
        for kw in ({"out": os.path.join(V.HERE, "results.json")}, {"runs_log": os.path.join(V.HERE, "runs.log")},
                   {"out": os.path.join(V.HERE, "runs.log")}, {"runs_log": os.path.join(V.HERE, "results.json")},
                   {"out": V.M1_V10_RECORD}, {"out": os.path.join(V.HERE, "tests", "..", "results.json")},
                   {"out": os.path.join(self.tmp, "same"), "runs_log": os.path.join(self.tmp, "same")}):
            with self.assertRaises(SystemExit, msg=kw):
                self.run_m1(**kw)
        link = os.path.join(self.tmp, "alias.json")
        os.symlink(os.path.join(V.HERE, "results.json"), link)
        with self.assertRaises(SystemExit):
            self.run_m1(out=link)

    def test_m04b_single_pinned_deposit(self):
        with self.assertRaises(SystemExit):
            self.run_m1(pin=False)  # fixture sha != pinned f95155af
        with self.assertRaises(SystemExit):
            self.run_m1(n_dep=2)

    def test_m04c_malformed_summary_no_crash(self):
        s = self.spec()
        files = m1_files(s)
        k = next(k for k in files if "b1HMxfer_mlp_matched_s2_a1/it0000640/" in k and k.endswith(".json"))
        d = json.loads(files[k])
        d["summary"] = None
        files[k] = json.dumps(d).encode()
        r, _ = self.run_m1(files=files)
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertIn("B1-V-1", r["failing_ids"])

    def test_m05_rfull_exact_collapse_and_rules(self):
        def ov(run, it, r):
            if run == "b1HAscratch_attention_s0" and it == 480:
                c = clips_nominal(0.5)
                for x in c:
                    if x["name"] == "jumps1_subject1":
                        x.update(steps=100, norm_return=0.6, failed=True, fail_step=100)
                return c
        r, _ = self.run_m1(override=ov)
        pt = r["primary"]["runs"]["b1HAscratch_attention_s0"]["points"]["it0000480"]
        want = (0.5 + 0.6 * 100 / 12222 + 0.5 + 0.5) / 4  # dance1 complete in window, jumps collapsed
        self.assertAlmostEqual(pt["R"], want, places=15)
        self.assertEqual((pt["failed"], pt["collapse"]), (1, True))
        self.assertAlmostEqual(pt["S"], (5336 + 100 + 11891 + 13066) / (5336 + 12222 + 11891 + 13066), places=15)
        ex = r["sensitivities"]["S-excl"]["runs"]["b1HAscratch_attention_s0"]["points"]["it0000480"]
        self.assertAlmostEqual(ex["R"], (0.6 * 100 / 12222 + 0.5 + 0.5) / 3, places=15)
        fu = r["sensitivities"]["S-full"]["runs"]["b1HAscratch_attention_s0"]["points"]["it0000480"]
        self.assertAlmostEqual(fu["R"], (0.5 * 5336 / 6574 + 0.6 * 100 / 12222 + 0.5 + 0.5) / 4, places=15)
        self.assertEqual(fu["failed"], 2)
        self.assertEqual(r["primary"]["arms"]["H-A-scratch"]["n_collapse"], 1)

    def test_m06_dance_beyond_window_invalid(self):
        def ov(run, it, r):
            if run == "b1HMxfer_mlp_matched_s1" and it == 160:
                c = clips_nominal(r)
                c[[x["name"] for x in c].index(V.M1_DANCE)].update(steps=6000, fail_step=6000)
                return c
        r, line = self.run_m1(override=ov)
        self.assertEqual((r["verdict"], r["outcome"]), ("BLOCKED", None))
        self.assertIn("M1-valid", r["failing_ids"])
        self.assertIn("outcome=null", line)
        self.assertIsNone(r["robust"])
        self.assertEqual(r["partial_outcome"], "INCONCLUSIVE")  # SIGNAL_STRONG on 2 valid seeds, capped
        self.assertTrue(r["sensitivities"]["S-full"]["m1_valid"])
        self.assertTrue(r["sensitivities"]["S-excl"]["m1_valid"])
        self.assertFalse(r["sensitivities"]["S-d10"]["m1_valid"])

    def test_m07_field_checks(self):
        for patch in ({"frames": 13000}, {"steps": 0}, {"steps": 2.5}, {"norm_return": float("nan")}, {"name": "walk2"}):
            def ov(run, it, r, patch=patch):
                if run == "b1HAxfer_attention_s2" and it == 1600:
                    c = clips_nominal(r)
                    c[3].update(patch)
                    return c
            r, _ = self.run_m1(override=ov)
            self.assertIn("M1-valid", r["failing_ids"], patch)

    def test_m08_summary_mismatch(self):
        s = self.spec()
        files = m1_files(s)
        k = next(k for k in files if "b1HAxfer_attention_s0_a1/it0000800/" in k and k.endswith(".json"))
        d = json.loads(files[k])
        d["summary"]["mean_norm_return"] += 1e-6
        files[k] = json.dumps(d).encode()
        r, _ = self.run_m1(files=files)
        self.assertIn("M1-valid", r["failing_ids"])

    def test_m09_criterion_margin(self):
        # diff 0.02 < delta 0.03 -> INCONCLUSIVE in M1; v1.0 1.2x: 0.32 < 0.36 -> also INCONCLUSIVE
        r, _ = self.run_m1(self.spec(**{"H-A-xfer": 0.32, "H-M-xfer": 0.30}))
        self.assertEqual(r["outcome"], "INCONCLUSIVE")
        self.assertFalse(r["primary"]["comparison"]["gain_ok"])
        # diff 0.04 >= 0.03 -> SIGNAL_STRONG under M1, but S-d10 and S-ratio stay INCONCLUSIVE -> robust false
        r, line = self.run_m1(self.spec(**{"H-A-xfer": 0.34, "H-M-xfer": 0.30}))
        self.assertEqual(r["outcome"], "SIGNAL_STRONG")
        self.assertEqual(r["sensitivities"]["S-d10"]["outcome"], "INCONCLUSIVE")
        self.assertEqual(r["sensitivities"]["S-ratio"]["outcome"], "INCONCLUSIVE")
        self.assertFalse(r["robust"])
        self.assertIn("robust=false", line)

    def test_m10_two_se_floor(self):
        s = self.spec(**{"H-A-xfer": 0.34, "H-M-xfer": 0.30})
        for k, v in s["runs"].items():  # widen H-A-xfer seed spread: sd 0.05 -> 2SE(x,s) > diff 0.04
            if v["arm"] == "H-A-xfer":
                v["R"] = F.linear(0.34 + (-0.05, 0.0, 0.05)[v["seed"]])
        r, _ = self.run_m1(s)
        c = r["primary"]["comparison"]
        self.assertGreater(c["margin_xs"], 0.03)
        self.assertAlmostEqual(c["margin_xs"], 2 * c["se_HA_xfer_HA_scratch"], places=15)
        self.assertEqual(r["outcome"], "INCONCLUSIVE")

    def test_m11_kill(self):
        r, _ = self.run_m1(self.spec(**{"H-A-xfer": 0.30}))
        self.assertEqual(r["outcome"], "KILL")
        r, _ = self.run_m1(self.spec(**{"H-M-xfer": 0.50}))
        self.assertEqual(r["outcome"], "KILL")
        self.assertTrue(r["primary"]["comparison"]["kill_xfer_below_mlp_2se"])

    def test_m12_collapse_penalised_not_rewarded(self):
        """The v1.0 defect: an all-clips-fail-early eval scores higher. Under R_full it scores near zero."""
        def ov(run, it, r):
            if run == "b1HAxfer_attention_s0" and it == 800:
                return [{"name": n, "frames": fr, "steps": 40, "norm_return": 0.9, "failed": True, "fail_step": 40,
                         "terms": {}} for n, fr in FR.items()]
        r, _ = self.run_m1(override=ov)
        pt = r["primary"]["runs"]["b1HAxfer_attention_s0"]["points"]["it0000800"]
        self.assertAlmostEqual(pt["R_v10"], 0.9)
        self.assertLess(pt["R"], 0.01)
        self.assertEqual((pt["failed"], pt["collapse"]), (4, True))

    def test_m13_v10_failure_blocks_m1(self):
        s = self.spec()
        s["gpu_rows"] = ["0, GPU-1, NVIDIA L4"]
        r, _ = self.run_m1(s)
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertIn("B1-V-5", r["failing_ids"])
        self.assertNotIn("M1-valid", r["failing_ids"])

    def test_m14_secondary_invalid_does_not_gate(self):
        def ov(run, it, r):
            if run == "b1HAfrozen_attention_s0" and it == 320:
                c = clips_nominal(r)
                c[0]["frames"] = 1
                return c
        r, _ = self.run_m1(override=ov)
        self.assertEqual(r["verdict"], "PASS")
        self.assertFalse(r["primary"]["runs"]["b1HAfrozen_attention_s0"]["valid"])
        self.assertEqual(r["primary"]["arms"]["H-A-frozen"]["n"], 0)

    def test_m15_bool_and_collapse_boundary(self):
        def ov_bool(run, it, r):
            if run == "b1HAscratch_attention_s1" and it == 160:
                c = clips_nominal(r)
                c[0]["steps"] = True
                return c
        r, _ = self.run_m1(override=ov_bool)
        self.assertIn("M1-valid", r["failing_ids"])

        def ov(run, it, r):
            if run == "b1HAscratch_attention_s1" and it == 160:
                c = clips_nominal(r)
                w = c[[x["name"] for x in c].index("walk1_subject1")]
                w.update(steps=1307, failed=True)  # 10*1307 = 13070 >= 13066 -> not a collapse
                return c
            if run == "b1HAscratch_attention_s1" and it == 320:
                c = clips_nominal(r)
                w = c[[x["name"] for x in c].index("walk1_subject1")]
                w.update(steps=1306, failed=True)  # 13060 < 13066 -> collapse
                return c
        r, _ = self.run_m1(override=ov)
        pts = r["primary"]["runs"]["b1HAscratch_attention_s1"]["points"]
        self.assertEqual((pts["it0000160"]["failed"], pts["it0000160"]["collapse"]), (1, False))
        self.assertEqual((pts["it0000320"]["failed"], pts["it0000320"]["collapse"]), (1, True))

    def test_m16_excl_counts_three_clips(self):
        r, _ = self.run_m1()
        pt = r["sensitivities"]["S-excl"]["runs"]["b1HAxfer_attention_s0"]["points"]["it0000160"]
        self.assertEqual((pt["n_clips"], pt["failed"]), (3, 0))
        pf = r["sensitivities"]["S-full"]["runs"]["b1HAxfer_attention_s0"]["points"]["it0000160"]
        self.assertEqual((pf["n_clips"], pf["failed"]), (4, 1))  # dance1 at 5336 < 6574 fails under S-full

    def test_m17_v10_failure_nulls_every_branch(self):
        s = self.spec()
        s["data_qa"]["pass"] = False
        r, line = self.run_m1(s)
        self.assertIsNone(r["robust"])
        self.assertIn("robust=null", line)
        for k, v in r["sensitivities"].items():
            self.assertIsNone(v["outcome"], k)
            self.assertEqual(v["verdict"], "BLOCKED")
        self.assertEqual(r["partial_outcome"], "INCONCLUSIVE")
        self.assertEqual(r["primary"]["partial_seeds_retained"], {a: [0, 1, 2] for a in V.PRIMARY})

    def test_m18_branches_independent(self):
        """Primary BLOCKED by C1 does not stop S-excl / S-full; partial lists retained seeds."""
        def ov(run, it, r):
            if run == "b1HAxfer_attention_s2" and it == 960:
                c = clips_nominal(r)
                c[[x["name"] for x in c].index(V.M1_DANCE)].update(steps=5400)
                return c
        r, _ = self.run_m1(override=ov)
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertEqual(r["primary"]["partial_seeds_retained"]["H-A-xfer"], [0, 1])
        self.assertEqual(r["sensitivities"]["S-excl"]["outcome"], "SIGNAL_STRONG")
        self.assertEqual(r["sensitivities"]["S-full"]["verdict"], "PASS")
        self.assertIsNone(r["robust"])


    def test_m19_hardlink_outputs(self):
        a = os.path.join(self.tmp, "o.json")
        open(a, "w").close()
        b = os.path.join(self.tmp, "o-link.log")
        os.link(a, b)
        with self.assertRaises(SystemExit):
            self.run_m1(out=a, runs_log=b)

    def test_m20_c2_unit_paths(self):
        """C2 at arm and comparison level (direct calls; synthetic values)."""
        mk = lambda vals: {f"r{i}": {"valid": True, "seed": i, "aulc_full": v, "r25_full": v, "r100_full": v, "S_mean": 1.0,
                                     "n_multifail": 0, "n_collapse": 0} for i, v in enumerate(vals)}  # noqa: E731
        old = V.ARMS["H-A-xfer"]
        mr = mk([1e200, -1e200, 0.0])
        orig_run_of = V.run_of
        try:
            V.run_of = lambda arm, s: f"r{s}"
            a = V.m1_arm_stats_safe(mr, "H-A-xfer")  # sd1 overflows
            self.assertIn("c2_error", a)
        finally:
            V.run_of = orig_run_of
        self.assertEqual(V.ARMS["H-A-xfer"], old)
        st = {k: {"n": 3, "aulc_mean": 0.5, "aulc_sd": 0.01} for k in V.PRIMARY}
        st["H-M-xfer"]["aulc_sd"] = float("inf")
        o, c = V.m1_outcome(st, 0.03)
        self.assertIsNone(o)
        self.assertTrue(c["reason"].startswith("C2"))


    def test_m21_arm_c2_end_to_end(self):
        """A primary-arm aggregation error yields a BLOCKED, fully serialised M1 artifact (no crash)."""
        orig = V.m1_arm_stats

        def boom(mr, arm):
            if arm == "H-A-scratch":
                raise OverflowError("synthetic")
            return orig(mr, arm)
        V.m1_arm_stats = boom
        try:
            r, line = self.run_m1()
        finally:
            V.m1_arm_stats = orig
        self.assertEqual((r["verdict"], r["outcome"], r["partial_outcome"]), ("BLOCKED", None, None))
        self.assertIn("M1-valid", r["failing_ids"])
        a = r["primary"]["arms"]["H-A-scratch"]
        self.assertEqual((a["n"], a["seeds_retained"], a["aulc_mean"]), (3, [0, 1, 2], None))
        self.assertIn("aulc_full_HA_scratch=null", line)
        for v in r["sensitivities"].values():
            self.assertIsNone(v["outcome"])
            self.assertIsNone(v["partial_outcome"])


if __name__ == "__main__":
    unittest.main()
