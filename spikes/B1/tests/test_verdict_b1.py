"""CPU fixture tests for spikes/B1/verdict_b1.py (PLAN §5-§6). Run: python3 -m unittest -v test_verdict_b1 (in this dir)."""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tarfile
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_fixture_b1 as F  # noqa: E402

V = F.V
MOCK_BUNDLE = os.environ.get("B1_MOCK_BUNDLE")  # optional: a CPU-mock driver bundle (end-to-end case)


class Base(unittest.TestCase):
    def run_v(self, spec=None, files=None, sealed=True, venue="xn4090", tarball_sha=F.TARBALL_SHA, extra_members=None,
              deposits=None):
        tmp = tempfile.mkdtemp(prefix="b1vt-")
        seal_log = os.path.join(tmp, "seal.log")
        open(seal_log, "w").close()
        paths = []
        for i, fl in enumerate(deposits or [files if files is not None else F.files_of(spec or F.default_spec())]):
            p = F.write_tgz(os.path.join(tmp, f"b1arms-fixture{i}.tgz"), fl, extra_members if i == 0 else None)
            if sealed:
                F.seal(seal_log, p, venue)
            paths.append(p)
        out = os.path.join(tmp, "results.json")
        argv = sum((["--deposit", p] for p in paths), []) + ["--tarball-sha", tarball_sha, "--seal-log", seal_log,
                                                             "--out", out, "--runs-log", os.path.join(tmp, "runs.log")]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            V.main(argv)
        lines = [ln for ln in buf.getvalue().splitlines() if ln.startswith("B1_VERDICT")]
        self.assertEqual(len(lines), 1)
        return json.load(open(out)), lines[0]

    def spec(self, **bases):
        b = {"H-A-scratch": 0.30, "H-A-xfer": 0.40, "H-M-xfer": 0.33, "H-M-scratch": 0.31, "H-A-frozen": 0.20,
             "H-A-xfer-noscale": 0.38}
        b.update({k.replace("_", "-"): v for k, v in bases.items()})
        return F.default_spec(b)


class TestOutcome(Base):
    def test_01_signal_strong(self):
        r, line = self.run_v(self.spec())
        self.assertEqual(r["verdict"], "PASS", r["failing_ids"])
        self.assertEqual(r["outcome"], "SIGNAL_STRONG")
        self.assertIn("verdict=PASS outcome=SIGNAL_STRONG failing=[]", line)
        self.assertEqual(r["comparison"]["ratio_branch"], "1.2x")

    def test_02_signal(self):
        r, _ = self.run_v(self.spec(**{"H-M-xfer": 0.40}))
        self.assertEqual((r["verdict"], r["outcome"]), ("PASS", "SIGNAL"))

    def test_03_inconclusive_ratio(self):
        r, _ = self.run_v(self.spec(**{"H-A-xfer": 0.335, "H-M-xfer": 0.30}))
        self.assertEqual(r["outcome"], "INCONCLUSIVE")
        self.assertFalse(r["comparison"]["ratio_ok"])

    def test_04_kill_not_above_scratch(self):
        r, _ = self.run_v(self.spec(**{"H-A-xfer": 0.30}))  # equal means -> mean(xfer) <= mean(scratch)
        self.assertEqual(r["outcome"], "KILL")
        self.assertTrue(r["comparison"]["kill_xfer_le_scratch"])

    def test_05_kill_below_mlp(self):
        r, _ = self.run_v(self.spec(**{"H-M-xfer": 0.50}))
        self.assertEqual(r["outcome"], "KILL")
        self.assertTrue(r["comparison"]["kill_xfer_below_mlp_2se"])
        self.assertFalse(r["comparison"]["kill_xfer_le_scratch"])

    def test_06_scratch_nonpositive_branch(self):
        r, _ = self.run_v(self.spec(**{"H-A-scratch": -0.155, "H-A-xfer": -0.12, "H-M-xfer": -0.30}))
        # mean scratch = -0.10, xfer = -0.065: diff 0.035 >= 0.2*0.10 -> ratio ok; xfer - mlp >> 2SE
        self.assertEqual(r["comparison"]["ratio_branch"], "abs_0.2")
        self.assertEqual(r["outcome"], "SIGNAL_STRONG")
        r, _ = self.run_v(self.spec(**{"H-A-scratch": -0.155, "H-A-xfer": -0.14, "H-M-xfer": -0.30}))
        self.assertFalse(r["comparison"]["ratio_ok"])
        self.assertEqual(r["outcome"], "INCONCLUSIVE")

    def test_07_aulc_r25_r100_exact(self):
        s = self.spec()
        R = [0.1, 0.2, 0.4, 0.4, 0.5, 0.6, 0.6, 0.7, 0.9, 1.0]
        s["runs"]["b1HAscratch_attention_s0"]["R"] = R
        r, _ = self.run_v(s)
        run = r["runs"]["b1HAscratch_attention_s0"]
        self.assertAlmostEqual(run["aulc"], 4.85 / 9, places=12)
        self.assertAlmostEqual(run["r25"], 0.3, places=12)
        self.assertEqual(run["r100"], 1.0)
        self.assertEqual(run["R"], R)

    def test_08_se_definition(self):
        r, _ = self.run_v(self.spec())
        x = r["arms"]["H-A-xfer"]["aulc"]
        m = r["arms"]["H-M-xfer"]["aulc"]

        def var(v):
            mu = sum(v) / 3
            return sum((a - mu) ** 2 for a in v) / 2

        self.assertAlmostEqual(r["comparison"]["se_HA_xfer_HM_xfer"], (var(x) / 3 + var(m) / 3) ** 0.5, places=12)

    def test_09_secondary_arms_do_not_move_outcome(self):
        s = self.spec(**{"H-M-scratch": 5.0, "H-A-frozen": -5.0})
        r, _ = self.run_v(s)
        self.assertEqual(r["outcome"], "SIGNAL_STRONG")
        self.assertAlmostEqual(r["arms"]["H-M-scratch"]["aulc_mean"], 5.0 + 0.055, places=9)


class TestValidity(Base):
    def assertBlocked(self, r, ids):
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertIsNone(r["outcome"])
        for i in ids:
            self.assertIn(i, r["failing_ids"])

    def test_10_missing_primary_run(self):
        s = self.spec()
        s["runs"]["b1HAxfer_attention_s2"]["attempts"] = []
        r, line = self.run_v(s)
        self.assertBlocked(r, ["B1-V-1", "B1-V-2", "B1-V-3"])
        self.assertEqual(r["partial_outcome"], "INCONCLUSIVE")  # SIGNAL_STRONG on 2 seeds, capped (§6 B1-V-1)
        self.assertIn("outcome=null", line)

    def test_11_infra_then_completed_attempt2(self):
        s = self.spec()
        s["runs"]["b1HMxfer_mlp_matched_s1"]["attempts"] = [{"kind": "infra"}, {"kind": "completed"}]
        r, _ = self.run_v(s)
        self.assertEqual(r["verdict"], "PASS", r["failing_ids"])
        self.assertEqual(r["runs"]["b1HMxfer_mlp_matched_s1"]["scored_attempt"], "b1HMxfer_mlp_matched_s1_a2")

    def test_12_nonfinite_is_result_not_retry(self):
        s = self.spec()
        s["runs"]["b1HAscratch_attention_s1"]["attempts"] = [{"kind": "nonfinite"}, {"kind": "completed"}]
        r, _ = self.run_v(s)
        self.assertBlocked(r, ["B1-V-1"])
        self.assertIsNone(r["runs"]["b1HAscratch_attention_s1"]["scored_attempt"])

    def test_13_two_infra_attempts(self):
        s = self.spec()
        s["runs"]["b1HAscratch_attention_s0"]["attempts"] = [{"kind": "infra"}, {"kind": "infra"}]
        r, _ = self.run_v(s)
        self.assertBlocked(r, ["B1-V-1"])

    def test_14_spend_cap_stop(self):
        s = self.spec()
        s["runs"]["b1HMxfer_mlp_matched_s2"]["attempts"] = [{"kind": "spend_cap"}]
        s["blocked"] = ["spend_cap detail=x"]
        r, _ = self.run_v(s)
        self.assertBlocked(r, ["B1-V-1"])
        self.assertEqual(r["runs"]["b1HMxfer_mlp_matched_s2"]["status"], "spend_cap")

    def test_15_spend_cap_in_secondaries_only(self):
        s = self.spec()
        s["runs"]["b1HAfrozen_attention_s0"]["attempts"] = []
        s["runs"]["b1HAxfernoscale_attention_s0"]["attempts"] = []
        s["runs"]["b1HMscratch_mlp_matched_s2"]["attempts"] = [{"kind": "spend_cap"}]
        s["blocked"] = ["spend_cap detail=secondary"]
        r, _ = self.run_v(s)
        self.assertEqual((r["verdict"], r["outcome"]), ("PASS", "SIGNAL_STRONG"))
        self.assertEqual(r["blocked_md"], ["BLOCKED_REASON=spend_cap detail=secondary"])

    def test_16_seam_false(self):
        s = self.spec()
        s["runs"]["b1HAxfer_attention_s0"]["attempts"] = [{"kind": "completed", "sidecar_patch": {"seam.S2_term_major_ok": False}}]
        r, _ = self.run_v(s)
        self.assertBlocked(r, ["B1-V-1"])

    def test_17_eval_nonfinite(self):
        s = self.spec()
        s["runs"]["b1HAxfer_attention_s1"]["R"][4] = float("nan")
        r, _ = self.run_v(s)
        self.assertBlocked(r, ["B1-V-1"])

    def test_18_eval_reexecution(self):
        s = self.spec()
        s["runs"]["b1HAxfer_attention_s1"]["attempts"] = [{"kind": "completed", "exec1_fail": (480,), "exec2_extra": (800,)}]
        r, _ = self.run_v(s)
        self.assertEqual(r["verdict"], "PASS", r["failing_ids"])
        ev = r["runs"]["b1HAxfer_attention_s1"]["eval"]
        self.assertEqual(ev["it0000480"]["scored_exec"], "exec2")
        self.assertEqual(ev["it0000800"]["scored_exec"], "exec1")
        self.assertTrue(any("exec2 present after a valid exec1" in n for n in r["runs"]["b1HAxfer_attention_s1"]["notes"]))

    def test_19_missing_eval_point(self):
        s = self.spec()
        f = F.files_of(s)
        f = {k: v for k, v in f.items() if "b1HMxfer_mlp_matched_s0_a1/it0001440/" not in k}
        r, _ = self.run_v(files=f)
        self.assertBlocked(r, ["B1-V-1"])

    def test_20_updates_differ(self):
        s = self.spec()
        s["runs"]["b1HAscratch_attention_s2"]["attempts"] = [{"kind": "completed", "updates_1600": 625.0}]
        r, _ = self.run_v(s)
        self.assertBlocked(r, ["B1-V-2"])
        self.assertNotIn("B1-V-1", r["failing_ids"])

    def test_21_argv_differs(self):
        s = self.spec()
        argv = ["--run-name", "x", "--seed", "0"] + [a if a != "512" else "256" for a in F.ARGV]
        s["runs"]["b1HMxfer_mlp_matched_s0"]["attempts"] = [{"kind": "completed", "sidecar_patch": {"argv": argv}}]
        r, _ = self.run_v(s)
        self.assertBlocked(r, ["B1-V-2"])

    def test_22_transfer_sha_mismatch(self):
        s = self.spec()
        s["runs"]["b1HAxfer_attention_s1"]["src_sha"] = V.SRC["attention_s0"]  # wrong seed pairing
        r, _ = self.run_v(s)
        self.assertBlocked(r, ["B1-V-3"])

    def test_23_mlp_report(self):
        s = self.spec()
        s["runs"]["b1HMxfer_mlp_matched_s2"]["attempts"] = [{"kind": "completed", "sidecar_patch": {"transfer.output_rows_mapped": 19}}]
        r, _ = self.run_v(s)
        self.assertBlocked(r, ["B1-V-3"])
        s = self.spec()
        s["runs"]["b1HMxfer_mlp_matched_s2"]["attempts"] = [{"kind": "completed", "sidecar_patch": {"transfer.fresh_joints": ["head_yaw_joint", "l_wrist"]}}]
        r, _ = self.run_v(s)
        self.assertBlocked(r, ["B1-V-3"])

    def test_24_attention_partial_load(self):
        s = self.spec()
        s["runs"]["b1HAxfer_attention_s0"]["attempts"] = [{"kind": "completed", "sidecar_patch": {"transfer.n_values_copied": 400000}}]
        r, _ = self.run_v(s)
        self.assertBlocked(r, ["B1-V-3"])

    def test_25_diagnostic_identity_checked(self):
        s = self.spec()
        s["runs"]["b1HAfrozen_attention_s0"]["src_sha"] = "0" * 64
        r, _ = self.run_v(s)
        self.assertBlocked(r, ["B1-V-3"])
        self.assertNotIn("B1-V-1", r["failing_ids"])

    def test_26_data_identity(self):
        for patch in ({"slot_rule": "replacement"}, {"csv_sha_mismatch": ["run1_subject2"]}, {"pass": False},
                      {"used_clips": ["walk1_subject1", "run2_subject1", "dance1_subject1", "jumps1_subject1"]}):
            s = self.spec()
            s["data_qa"].update(patch)
            r, _ = self.run_v(s)
            self.assertBlocked(r, ["B1-V-4"])

    def test_27_gpu(self):
        for rows in (["0, GPU-1, NVIDIA L4"], ["0, GPU-1, NVIDIA GeForce RTX 4090", "1, GPU-2, NVIDIA GeForce RTX 4090"],
                     ["0, GPU-1, NVIDIA GeForce RTX 4090 D"], []):
            s = self.spec()
            s["gpu_rows"] = rows
            r, _ = self.run_v(s)
            self.assertBlocked(r, ["B1-V-5"])
        s = self.spec()
        s["cuda_env"] = ["part=1 CUDA_VISIBLE_DEVICES=1"]
        r, _ = self.run_v(s)
        self.assertBlocked(r, ["B1-V-5"])


class TestDeposit(Base):
    def test_30_unsealed(self):
        r, _ = self.run_v(self.spec(), sealed=False)
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertEqual(r["failing_ids"][0], "deposit_check")
        self.assertFalse(r["deposits"][0]["extracted"])

    def test_31_wrong_venue_seal(self):
        r, _ = self.run_v(self.spec(), venue="colab")
        self.assertIn("deposit_check", r["failing_ids"])

    def test_32_tarball_mismatch(self):
        r, _ = self.run_v(self.spec(), tarball_sha="cd34" * 16)
        self.assertIn("deposit_check", r["failing_ids"])
        self.assertIsNone(r["outcome"])

    def test_33_pt_member_rejected(self):
        ti = tarfile.TarInfo("logs/b1HAxfer_attention_s0/ckpt_0001600.pt")
        ti.size = 4
        r, _ = self.run_v(self.spec(), extra_members=[(ti, b"abcd")])
        self.assertIn("deposit_check", r["failing_ids"])
        self.assertFalse(r["deposits"][0]["extracted"])

    def test_34_two_deposits_merge(self):
        s = self.spec()
        full = F.files_of(s)
        part1 = {k: v for k, v in full.items() if "_s2" not in k}
        r, _ = self.run_v(deposits=[part1, full])
        self.assertEqual((r["verdict"], r["outcome"]), ("PASS", "SIGNAL_STRONG"))
        r, _ = self.run_v(deposits=[part1])
        self.assertIn("B1-V-1", r["failing_ids"])

    def test_35_results_shape(self):
        r, line = self.run_v(self.spec())
        for k in ("tool", "tool_sha256", "plan_sha256", "deposits", "deposit_check", "validity", "arms", "comparison",
                  "verdict", "outcome", "failing_ids", "partial_outcome", "runs", "disclosures", "verdict_line"):
            self.assertIn(k, r)
        self.assertEqual(r["plan_sha256"], V.PLAN_SHA256)
        self.assertEqual(sorted(r["validity"]), ["B1-V-1", "B1-V-2", "B1-V-3", "B1-V-4", "B1-V-5"])
        self.assertEqual(len(r["runs"]), 14)
        self.assertEqual(r["verdict_line"], line)
        self.assertRegex(line, r"^B1_VERDICT verdict=(PASS|BLOCKED) outcome=(SIGNAL_STRONG|SIGNAL|INCONCLUSIVE|KILL|null) ")


@unittest.skipUnless(MOCK_BUNDLE, "set B1_MOCK_BUNDLE to a CPU-mock driver bundle")
class TestMockBundle(Base):
    def test_40_mock_driver_bundle(self):
        """End to end: the CPU-mock driver bundle has mock source shas, mock data and no 4090 -> BLOCKED V-3/V-4/V-5,
        while V-1 and V-2 (order, harness stop, 10 evals, updates parity) pass on the driver's real layout."""
        tmp = tempfile.mkdtemp(prefix="b1vt-mock-")
        seal_log = os.path.join(tmp, "seal.log")
        F.seal(seal_log, MOCK_BUNDLE)
        out = os.path.join(tmp, "results.json")
        tsha = os.environ["B1_MOCK_TARBALL_SHA"]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            V.main(["--deposit", MOCK_BUNDLE, "--tarball-sha", tsha, "--seal-log", seal_log, "--out", out,
                    "--runs-log", os.path.join(tmp, "runs.log")])
        r = json.load(open(out))
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertEqual(r["failing_ids"], ["B1-V-3", "B1-V-4", "B1-V-5"])
        self.assertTrue(r["validity"]["B1-V-1"]["pass"], r["validity"]["B1-V-1"])
        self.assertTrue(r["validity"]["B1-V-2"]["pass"], r["validity"]["B1-V-2"])
        self.assertIsNotNone(r["partial_outcome"])
        print(buf.getvalue().strip(), file=sys.stderr)


if __name__ == "__main__":
    unittest.main()
