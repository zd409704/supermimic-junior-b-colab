"""End-to-end tests for verdict_b0.py on synthetic deposits (stdlib unittest).

Run:  .venv/bin/python -I -m unittest discover -s spikes/B0/verdict -p 'test_*.py' -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import make_fixture as mf  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TOOL = os.path.join(HERE, "verdict_b0.py")
PLAN = os.path.join(ROOT, "spikes", "B0", "PLAN.md")
FACTS = os.path.join(ROOT, "packets", "P4", "UPSTREAM_FACTS.md")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="b0verdict_")

    def tearDown(self):
        for r, ds, fs in os.walk(self.tmp):
            for d in ds:
                os.chmod(os.path.join(r, d), 0o755)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, deposits, seal_skip=(), tarball_sha=mf.TARBALL_SHA, venue="colab"):
        paths, seal = mf.build(os.path.join(self.tmp, "fx"), deposits, seal_skip=seal_skip)
        out = os.path.join(self.tmp, "results.json")
        runs = os.path.join(self.tmp, "runs.log")
        cmd = [sys.executable, "-I", TOOL, "--seal-log", seal, "--plan", PLAN, "--method-sha",
               "9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0", "--tarball-sha", tarball_sha,
               "--facts", FACTS, "--venue", venue, "--out", out, "--runs-log", runs,
               "--work", os.path.join(self.tmp, "work")]
        for p in paths:
            cmd += ["--deposit", p]
        p = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        lines = p.stdout.splitlines()
        self.assertEqual(len(lines), 1, p.stdout)
        self.assertTrue(lines[0].startswith("B0_VERDICT verdict="), lines[0])
        with open(out) as fh:
            res = json.load(fh)
        self.assertEqual(res["verdict_line"], lines[0])
        with open(runs) as fh:
            self.runs_log = fh.read()
        return lines[0], res

    def assertKeys(self, res):
        top = ["plan_sha256", "method_sha256", "tarball_sha256", "venue", "gpu_name", "deposits", "verdict",
               "decision_row", "failing_ids", "blocked_reason", "b0_outcome", "outcome_basis", "superior",
               "noise_widened", "delta", "delta_threshold", "se_pooled", "rbar_h_attention", "rbar_h_mlp_matched", "T",
               "shadow_outcome_rstep", "metric_disagreement", "budget", "scored_set", "l1_seeds_passing",
               "upstream_facts", "rh_clips_over_T", "attempts", "m9_wallclock"]
        for k in top:
            self.assertIn(k, res)
        for g in ("V-0", "V-1", "V-2", "V-3", "V-4", "L-1", "L-2", "DIV", "REF-1", "REF-2", "REF-3", "REF-4"):
            self.assertIn(g, res)
            self.assertIsInstance(res[g]["pass"], bool, g)
        for k in ("iterations", "updates_at_1600", "parity", "env_steps_per_iter"):
            self.assertIn(k, res["budget"])
        for k in ("W_hours", "r_h_attention_at_W", "r_h_mlp_matched_at_W", "per_run"):
            self.assertIn(k, res["m9_wallclock"])
        for f in ("F-1", "F-2", "F-3", "F-4", "F-5"):
            self.assertIn(f, res["upstream_facts"])
        akeys = ["tag", "arm", "seed", "attempt", "class", "scored", "harness_stop", "reached_1600", "nan",
                 "updates_at_1600", "seams", "descriptor_sha256", "params_policy", "c_train_first5", "c_train_last5",
                 "nret_train_first5", "nret_train_last5", "elen_first5", "elen_last5", "wm_loss_first5",
                 "wm_loss_last5", "clip_fraction_last25", "grad_norm_max", "ms_per_update", "it_per_s",
                 "peak_mem_mib", "hours_at_1600", "hours_at_ckpt", "eval", "aulc_h"]
        for aid, a in res["attempts"].items():
            for k in akeys:
                self.assertIn(k, a, (aid, k))
            self.assertEqual(set(a["seams"]), {"S1", "S2", "S3", "S4", "S5"})
            self.assertIsNone(a["clip_fraction_last25"])
            if a["class"] == "completed":
                for it in ("it0000400", "it0000800", "it0001200", "it0001600"):
                    e = a["eval"][it]
                    self.assertIn("scored_exec", e)
                    for m in ("mask0.00", "mask0.10", "mask0.20"):
                        for k in ("r_h", "r_step", "r_step_weighted", "cum", "surv_steps", "fail_count", "clips", "terms"):
                            self.assertIn(k, e[m])
                    self.assertIn("rho_h", e["mask0.10"])
                    self.assertNotIn("rho_h", e["mask0.00"])


class TestVerdict(Base):
    def test_01_clean_pass_noninferior(self):
        line, r = self.run_tool([{"attempts": mf.clean_attempts()}])
        self.assertKeys(r)
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["decision_row"], 4)
        self.assertEqual(r["b0_outcome"], "NONINFERIOR")
        self.assertEqual(r["outcome_basis"], "margin")
        self.assertAlmostEqual(r["delta"], 0.30 - (0.30 + 0.30 + 0.31) / 3, places=6)
        self.assertEqual(r["delta_threshold"], 0.05)
        self.assertFalse(r["noise_widened"])
        self.assertFalse(r["superior"])
        self.assertEqual(r["shadow_outcome_rstep"], "NONINFERIOR")
        self.assertFalse(r["metric_disagreement"])
        self.assertEqual(r["budget"]["env_steps_per_iter"], 512)
        self.assertTrue(r["budget"]["parity"])
        self.assertEqual(set(r["budget"]["updates_at_1600"].values()), {624})  # latest-wall-time dedupe
        self.assertEqual(r["gpu_name"], "NVIDIA L4")
        self.assertEqual(r["rh_clips_over_T"], 7 * 4 * 3 * 3)  # 3 of 4 clips have steps > 500
        self.assertTrue(r["REF-1"]["pass"] and r["REF-3"]["pass"])
        self.assertIsNotNone(r["m9_wallclock"]["W_hours"])
        a = r["attempts"]["b0_attention_s0_a1"]
        self.assertEqual(a["params_policy"], 464001)
        self.assertAlmostEqual(a["it_per_s"], 0.7, places=4)
        self.assertEqual(a["peak_mem_mib"], 9123.0)
        self.assertAlmostEqual(a["aulc_h"], 0.30 * ((0.5 + 0.7) / 2 + (0.7 + 0.9) / 2 + (0.9 + 1.0) / 2) / 3, places=6)
        self.assertAlmostEqual(a["eval"]["it0001600"]["mask0.10"]["rho_h"], 0.9, places=6)
        self.assertIn("B0_VERDICT verdict=PASS outcome=NONINFERIOR basis=margin", line)
        self.assertIn("failing_ids=[] blocked=[]", line)
        self.assertIn("DEPOSIT path=", self.runs_log)

    def test_02_pass_inferior_margin(self):
        line, r = self.run_tool([{"attempts": mf.clean_attempts((0.20, 0.21, 0.19), (0.30, 0.31, 0.29))}])
        self.assertEqual((r["verdict"], r["b0_outcome"], r["outcome_basis"]), ("PASS", "INFERIOR", "margin"))
        self.assertAlmostEqual(r["delta"], -0.10, places=6)
        self.assertEqual(r["delta_threshold"], 0.05)
        self.assertFalse(r["noise_widened"])

    def test_03_noise_widened(self):
        line, r = self.run_tool([{"attempts": mf.clean_attempts((0.10, 0.30, 0.20), (0.15, 0.45, 0.30))}])
        self.assertEqual((r["verdict"], r["b0_outcome"]), ("PASS", "NONINFERIOR"))
        self.assertTrue(r["noise_widened"])
        self.assertFalse(r["superior"])
        self.assertAlmostEqual(r["delta"], -0.10, places=6)
        self.assertGreater(r["delta_threshold"], 0.2)
        self.assertNotIn("INCONCLUSIVE", line)

    def _div_seed1(self):
        specs = mf.clean_attempts()
        mf.find(specs, "b0_attention_s1_a1").update(outcome="div_crash", nan_step=800, stop_it=800)
        idx = [s["aid"] for s in specs].index("b0_mlp_matched_s1_a1") + 1
        lr = [mf.default_attempt("b0lr05_attention_s1_a1", r_h=0.31),
              mf.default_attempt("b0lr05_mlp_matched_s1_a1", r_h=0.30)]
        return specs[:idx] + lr + specs[idx:]

    def test_04_div_replaced_by_lr05_pair(self):
        line, r = self.run_tool([{"attempts": self._div_seed1()}])
        self.assertEqual((r["verdict"], r["b0_outcome"]), ("PASS", "NONINFERIOR"))
        self.assertEqual(r["scored_set"]["attention_s1"], "b0lr05_attention_s1_a1")
        self.assertEqual(r["scored_set"]["mlp_matched_s1"], "b0lr05_mlp_matched_s1_a1")
        self.assertEqual(r["attempts"]["b0_attention_s1_a1"]["class"], "DIV")
        self.assertTrue(r["attempts"]["b0_attention_s1_a1"]["nan"])
        self.assertFalse(r["attempts"]["b0_mlp_matched_s1_a1"]["in_scored_set"])
        self.assertTrue(r["attempts"]["b0_mlp_matched_s1_a1"]["scored"])
        self.assertEqual(r["DIV"]["retry_pair_seeds"], [1])
        self.assertTrue(r["V-2"]["b_argv_identical"])  # lr05 flag at exactly 0.5 x default is excluded

    def test_05_terminal_attention_divergence(self):
        specs = self._div_seed1()
        mf.find(specs, "b0lr05_attention_s1_a1").update(outcome="div_crash", nan_step=600, stop_it=600)
        line, r = self.run_tool([{"attempts": specs}])
        self.assertEqual((r["verdict"], r["decision_row"], r["b0_outcome"], r["outcome_basis"]),
                         ("PASS", 2, "INFERIOR", "divergence"))
        self.assertIsNone(r["delta"])
        self.assertIsNone(r["delta_threshold"])
        self.assertIsNone(r["se_pooled"])
        self.assertFalse(r["superior"] or r["noise_widened"])
        self.assertIn("delta=null delta_thr=null", line)
        self.assertEqual(r["scored_set"]["attention_s1"], "b0lr05_attention_s1_a1")
        self.assertTrue(r["V-1"]["pass"])  # integrity checks only for the terminal run

    def test_06_terminal_comparator_divergence(self):
        specs = self._div_seed1()
        mf.find(specs, "b0lr05_mlp_matched_s1_a1").update(outcome="div_crash", nan_step=600, stop_it=600)
        line, r = self.run_tool([{"attempts": specs}])
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertIsNone(r["b0_outcome"])
        self.assertIn("terminal_comparator_divergence", r["blocked_reason"])

    def test_07_missing_1600_tb_point(self):
        specs = mf.clean_attempts()
        mf.find(specs, "b0_mlp_matched_s2_a1")["drop_1600"] = True
        line, r = self.run_tool([{"attempts": specs}])
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertIn("V-1", r["blocked_reason"])
        ev = r["V-1"]["per_attempt"]["b0_mlp_matched_s2_a1"]
        self.assertFalse(ev["logged_point_at_1600"])
        self.assertIn("V-1", line)

    def test_08_l1_fails_two_of_three(self):
        specs = mf.clean_attempts()
        mf.find(specs, "b0_attention_s0_a1")["l1"] = "fall"
        mf.find(specs, "b0_attention_s2_a1")["l1"] = "fall"
        line, r = self.run_tool([{"attempts": specs}])
        self.assertEqual((r["verdict"], r["decision_row"], r["failing_ids"]), ("FAIL", 3, ["L-1"]))
        self.assertEqual(r["l1_seeds_passing"], {"attention": 1, "mlp_matched": 3})
        self.assertIsNone(r["b0_outcome"])
        self.assertIn("failing_ids=[L-1]", line)

    def test_09_deposit_not_sealed(self):
        line, r = self.run_tool([{"attempts": mf.clean_attempts()}], seal_skip=(0,))
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertIn("deposit_check", r["blocked_reason"])
        self.assertFalse(r["deposits"][0]["extracted"])

    def test_09b_tarball_sha_mismatch(self):
        line, r = self.run_tool([{"attempts": mf.clean_attempts()}], tarball_sha="00" * 32)
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertIn("deposit_check", r["blocked_reason"])

    def test_09c_unsafe_member_rejected(self):
        import tarfile
        ti = tarfile.TarInfo("../escape.txt")
        ti.size = 1
        line, r = self.run_tool([{"attempts": mf.clean_attempts(), "extra_members": [(ti, b"x")]}])
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertIn("deposit_check", r["blocked_reason"])
        ti2 = tarfile.TarInfo("./logs/ckpt_0001600.pt")
        ti2.size = 1
        line, r = self.run_tool([{"attempts": mf.clean_attempts(), "extra_members": [(ti2, b"x")]}])
        self.assertIn("deposit_check", r["blocked_reason"])
        ti3 = tarfile.TarInfo("./logs/link")
        ti3.type = tarfile.SYMTYPE
        ti3.linkname = "../../etc/passwd"
        line, r = self.run_tool([{"attempts": mf.clean_attempts(), "extra_members": [(ti3, None)]}])
        self.assertIn("deposit_check", r["blocked_reason"])

    def test_10_post_endpoint_anomalies(self):
        specs = mf.clean_attempts()
        mf.find(specs, "b0_attention_s1_a1").update(post_nan=True, post_exc="RuntimeError: non-finite loss detected")
        line, r = self.run_tool([{"attempts": specs}])
        self.assertEqual((r["verdict"], r["b0_outcome"]), ("PASS", "NONINFERIOR"))
        a = r["attempts"]["b0_attention_s1_a1"]
        self.assertEqual(a["class"], "completed")
        self.assertFalse(a["diverged"])
        self.assertFalse(a["nan"])
        kinds = [x["kind"] for x in a["post_endpoint_anomaly"]]
        self.assertIn("tb_nonfinite_after_1600", kinds)
        finals = [x.get("final_line") for x in a["post_endpoint_anomaly"]]
        self.assertIn("RuntimeError: non-finite loss detected", finals)
        self.assertEqual(r["scored_set"]["attention_s1"], "b0_attention_s1_a1")

    def test_11_infra_then_completed(self):
        specs = mf.clean_attempts()
        i = [s["aid"] for s in specs].index("b0_attention_s2_a1")
        specs[i].update(outcome="infra_disconnect", stop_it=900, live=True)
        specs.insert(i + 1, mf.default_attempt("b0_attention_s2_a2", r_h=0.29))
        line, r = self.run_tool([{"attempts": specs}])
        self.assertEqual((r["verdict"], r["b0_outcome"]), ("PASS", "NONINFERIOR"))
        self.assertEqual(r["attempts"]["b0_attention_s2_a1"]["class"], "INFRA")
        self.assertEqual(r["attempts"]["b0_attention_s2_a1"]["infra_cause"], "no_endpoint")
        self.assertTrue(r["attempts"]["b0_attention_s2_a1"]["live_dir_present"])
        self.assertEqual(r["scored_set"]["attention_s2"], "b0_attention_s2_a2")
        self.assertTrue(r["attempts"]["b0_attention_s2_a2"]["scored"])
        self.assertNotIn("b0_attention_s2_a1.live", r["attempts"])

    def test_11b_second_infra_blocks(self):
        specs = mf.clean_attempts()
        i = [s["aid"] for s in specs].index("b0_attention_s2_a1")
        specs[i].update(outcome="infra_disconnect", stop_it=900, live=True)
        specs.insert(i + 1, mf.default_attempt("b0_attention_s2_a2", outcome="infra_disconnect", stop_it=300))
        line, r = self.run_tool([{"attempts": specs}])
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertIn("INFRA_cap", r["blocked_reason"])

    def test_12_two_deposits_merge(self):
        specs = mf.clean_attempts()
        p1 = [s for s in specs if s["seed"] in (0, 1) and s["arm"] != "mlp_upstream"]
        p2 = [s for s in specs if s not in p1]
        line, r = self.run_tool([{"part": 1, "attempts": p1, "session": {"gate_set_complete": "false"}},
                                 {"part": 2, "attempts": p2, "sanity": None}])
        self.assertEqual((r["verdict"], r["b0_outcome"]), ("PASS", "NONINFERIOR"))
        self.assertEqual(len(r["deposits"]), 2)
        self.assertTrue(all(d["extracted"] for d in r["deposits"]))
        self.assertEqual(len(r["attempts"]), 7)
        self.assertTrue(r["V-0"]["pass"])
        self.assertEqual(self.runs_log.count("=== end ==="), 2)

    def test_12b_spend_cap_before_complete(self):
        specs = mf.clean_attempts()
        p1 = [s for s in specs if s["seed"] in (0, 1) and s["arm"] != "mlp_upstream"]
        line, r = self.run_tool([{"part": 1, "attempts": p1, "session": {"spend_cap_hit": "true",
                                                                          "gate_set_complete": "false"}}])
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertIn("spend_cap", r["blocked_reason"])

    def test_13_rdiv_final_line_only(self):
        specs = mf.clean_attempts()
        i = [s["aid"] for s in specs].index("b0_mlp_matched_s0_a1")
        body = ['  File "/content/SuperMimic-Reproduced/src/supermimic/utils/nan_guard.py", line 12, in check_nan',
                "    if torch.isnan(x).any() or torch.isinf(x).any():  # nan / inf guard",
                '  File "/usr/lib/python3.12/socket.py", line 720, in readinto']
        specs[i].update(outcome="traceback", stop_it=700,
                        pre_exc=(body, "ConnectionResetError: [Errno 104] Connection reset by peer"))
        specs.insert(i + 1, mf.default_attempt("b0_mlp_matched_s0_a2", r_h=0.30))
        line, r = self.run_tool([{"attempts": specs}])
        a = r["attempts"]["b0_mlp_matched_s0_a1"]
        self.assertEqual(a["class"], "INFRA")
        self.assertFalse(a["diverged"])
        self.assertEqual(a["infra_cause"], "other_traceback")
        self.assertEqual(r["DIV"]["retry_pair_seeds"], [])
        self.assertEqual(r["scored_set"]["mlp_matched_s0"], "b0_mlp_matched_s0_a2")
        self.assertEqual(r["verdict"], "PASS")

    def test_13b_rdiv_matches_final_line(self):
        specs = mf.clean_attempts()
        i = [s["aid"] for s in specs].index("b0_mlp_matched_s0_a1")
        specs[i].update(outcome="traceback", stop_it=700, pre_exc=(['  File "x.py", line 1, in f'],
                                                                   "ValueError: loss is -inf"))
        line, r = self.run_tool([{"attempts": specs}])
        self.assertEqual(r["attempts"]["b0_mlp_matched_s0_a1"]["class"], "DIV")
        self.assertEqual(r["DIV"]["retry_pair_seeds"], [0])
        self.assertEqual(r["verdict"], "BLOCKED")  # retry pair missing from the deposit -> slot empty
        self.assertIn("V-1", r["blocked_reason"])

    def test_14_mlp_upstream_failure_never_changes_verdict(self):
        _, base = self.run_tool([{"attempts": mf.clean_attempts()}])
        for mod in ({"outcome": "oom", "stop_it": 200}, {"outcome": "div_crash", "nan_step": 400, "stop_it": 400},
                    {"outcome": "seam"}, {"l1": "fall", "l2": "rise", "evals": False}):
            specs = mf.clean_attempts()
            mf.find(specs, "b0_mlp_upstream_s0_a1").update(mod)
            line, r = self.run_tool([{"attempts": specs}])
            self.assertEqual((r["verdict"], r["b0_outcome"], r["delta"], r["blocked_reason"]),
                             (base["verdict"], base["b0_outcome"], base["delta"], base["blocked_reason"]), mod)
            self.assertTrue(not r["REF-1"]["pass"] or not r["REF-3"]["pass"] or not r["REF-4"]["pass"]
                            or not r["REF-2"]["pass"], mod)
        specs = mf.clean_attempts(ref=False)
        line, r = self.run_tool([{"attempts": specs}])
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["REF-1"]["status"], "missing")

    def test_15_v0_fail_and_seam_block(self):
        line, r = self.run_tool([{"attempts": mf.clean_attempts(), "sanity": "fail"}])
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertIn("V-0", r["blocked_reason"])
        specs = mf.clean_attempts()
        mf.find(specs, "b0_attention_s0_a1").update(outcome="seam")
        line, r = self.run_tool([{"attempts": specs}])
        self.assertEqual(r["attempts"]["b0_attention_s0_a1"]["class"], "SEAM")
        self.assertIn("SEAM", r["blocked_reason"])

    def test_16_driver_class_disagreement_reported(self):
        specs = mf.clean_attempts()
        mf.find(specs, "b0_attention_s0_a1")["driver_class"] = "INFRA"
        line, r = self.run_tool([{"attempts": specs}])
        a = r["attempts"]["b0_attention_s0_a1"]
        self.assertEqual(a["class"], "completed")
        self.assertTrue(a["class_disagreement"])
        self.assertEqual(r["verdict"], "PASS")

    def test_17_two_tb_files_fail_v1(self):
        specs = mf.clean_attempts()
        mf.find(specs, "b0_attention_s1_a1")["extra_tb_file"] = True
        line, r = self.run_tool([{"attempts": specs}])
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertFalse(r["V-1"]["per_attempt"]["b0_attention_s1_a1"]["one_tb_file"])


class TestReader(unittest.TestCase):
    def test_roundtrip_and_crc(self):
        import verdict_b0 as v
        spec = mf.default_attempt("b0_attention_s0_a1")
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "events.out.tfevents.1")
            with open(p, "wb") as fh:
                fh.write(mf.event_file_bytes(spec))
            recs, info = v.read_events(p)
            self.assertEqual(info["crc_errors"], 0)
            ser = v.dedupe_series(recs)
            self.assertEqual(ser["time/updates"][1600], 624.0)
            self.assertEqual(len(ser["wm/loss"]), 33)
            # corrupt one byte -> CRC error detected
            with open(p, "rb") as fh:
                b = bytearray(fh.read())
            b[200] ^= 0xFF
            with open(p, "wb") as fh:
                fh.write(bytes(b))
            _, info2 = v.read_events(p)
            self.assertGreater(info2["crc_errors"], 0)
        finally:
            shutil.rmtree(d)

    def test_traceback_parse(self):
        import verdict_b0 as v
        text = "\n".join(["it 50 | x", "Traceback (most recent call last):", '  File "a", line 1', "    nan_check()",
                          "ValueError: bad", "", "During handling of the above exception, another exception occurred:",
                          "", "Traceback (most recent call last):", '  File "b", line 2', "RuntimeError: loss is nan"])
        L = v.parse_train_log(text)
        self.assertEqual([t["final_line"] for t in L["tracebacks"]], ["RuntimeError: loss is nan"])
        self.assertTrue(v.R_DIV.search("RuntimeError: loss is nan"))
        self.assertTrue(v.R_DIV.search("x: value -inf"))
        self.assertFalse(v.R_DIV.search("ValueError: infinite loop guard"))
        self.assertFalse(v.R_DIV.search("ValueError: bad"))


if __name__ == "__main__":
    unittest.main()
