"""End-to-end tests for verdict_b2.py on synthetic P5 deposits (stdlib unittest).

Run:  .venv/bin/python -I -m unittest discover -s spikes/B2/verdict -p 'test_*.py' -v
Needs the sealed P4 open tree (logs/xn4090/2026-10-26/open-b0-20261026-0919) for U-REPRO and the legacy table.
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
import make_fixture_b2 as fx  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TOOL = os.path.join(HERE, "verdict_b2.py")
PLAN = os.path.join(ROOT, "spikes", "B2", "PLAN.md")
FACTS = os.path.join(ROOT, "packets", "P4", "UPSTREAM_FACTS.md")
P4_OPEN = os.path.join(ROOT, "logs", "xn4090", "2026-10-26", "open-b0-20261026-0919")
P4_RESULTS = os.path.join(ROOT, "orch", "reports", "VERDICT-P4-b0-attempt1-relaunch3-results.json")


def T(aid, **kw):
    return fx.t_spec(aid, **kw)


def tspecs(over=None, drop=()):
    """Default 9 new attempts with per-AID overrides; `drop` removes AIDs."""
    over = over or {}
    out = []
    for s in fx.default_t_specs():
        if s["aid"] in drop:
            continue
        if s["aid"] in over:
            s = T(s["aid"], **({"r0": 0.22} if s["tag"] == "b2idx" else {}), **over[s["aid"]])
        out.append(s)
    return out


def uspecs(over=None):
    over = over or {}
    return [fx.u_spec(a, **over.get(a, {})) for a in fx.U_AIDS]


def gain_u():
    return {a: {"rho": {"0.10": 0.95, "0.20": 0.90}} for a in fx.U_AIDS if "_attention_" in a} | \
           {a: {"rho": {"0.10": 0.70, "0.20": 0.50}} for a in fx.U_AIDS if "_mlp_matched_" in a}


def gain_t(t_att=0.90, t_mm=0.50):
    o = {}
    for s in (0, 1, 2):
        o["b2mt_attention_s%d_a1" % s] = {"rho": {"0.10": 0.95, "0.20": t_att}}
        o["b2mt_mlp_mind_s%d_a1" % s] = {"rho": {"0.10": 0.80, "0.20": t_mm}}
    return o


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="b2verdict_")

    def tearDown(self):
        for r, ds, fs in os.walk(self.tmp):
            for d in ds:
                os.chmod(os.path.join(r, d), 0o755)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, deposits, seal_skip=(), tarball_sha=fx.TARBALL_SHA, venue="xn4090", seal_venue="xn4090"):
        paths, seal = fx.build(os.path.join(self.tmp, "fx"), deposits, seal_skip=seal_skip, venue=seal_venue)
        out = os.path.join(self.tmp, "results.json")
        runs = os.path.join(self.tmp, "runs.log")
        cmd = [sys.executable, "-I", TOOL, "--seal-log", seal, "--plan", PLAN, "--method-sha",
               "9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0", "--tarball-sha", tarball_sha,
               "--facts", FACTS, "--p4-open-tree", P4_OPEN, "--p4-results", P4_RESULTS, "--venue", venue,
               "--out", out, "--runs-log", runs, "--work", os.path.join(self.tmp, "work")]
        for p in paths:
            cmd += ["--deposit", p]
        p = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        lines = p.stdout.splitlines()
        self.assertEqual(len(lines), 1, p.stdout)
        self.assertTrue(lines[0].startswith("B2_VERDICT verdict="), lines[0])
        with open(out) as fh:
            res = json.load(fh)
        self.assertEqual(res["verdict_line"], lines[0])
        self.line = lines[0]
        with open(runs) as fh:
            self.runs_log = fh.read()
        return res

    def dep(self, **kw):
        d = {"part": 1, "u": uspecs(kw.pop("u_over", None)), "t": tspecs(kw.pop("t_over", None), kw.pop("t_drop", ()))}
        d.update(kw)
        return d


class TestPass(Base):
    def test_clean_no_gain_legacy_direction(self):
        r = self.run_tool([self.dep()])
        self.assertEqual((r["verdict"], r["decision_row"], r["b2_outcome"]), ("PASS", 4, "NO_GAIN"))
        self.assertTrue(all(g["pass"] for g in r["gates"].values()), {k: g["pass"] for k, g in r["gates"].items()})
        self.assertAlmostEqual(r["u"]["f0.20"]["delta_rho"], 0.30 - 0.76, places=9)
        self.assertEqual(r["u"]["f0.20"]["g_u"], 0.17)  # SE ~0 -> floor
        self.assertTrue(r["u_deficit"])
        self.assertFalse(r["u_gain"])
        self.assertAlmostEqual(r["t"]["f0.20"]["delta_rho"], 0.40 - 0.70, places=9)
        self.assertEqual(r["t"]["f0.20"]["g_t"], 0.10)
        self.assertEqual(r["t_status"], "ok")
        self.assertEqual(r["gate_b1"], "Go")
        self.assertTrue(r["caveat_required"])
        self.assertEqual(r["b0_outcome_input"]["value"], "NONINFERIOR")
        self.assertFalse(r["b2_gain"])
        self.assertEqual((r["T"], r["g_u_floor"], r["g_t_floor"], r["r_floor"], r["mask_seeds"], r["primary_f"]),
                         (500, 0.17, 0.10, 0.0393, [7100, 7101, 7102], 0.2))
        self.assertEqual(r["plan_sha256"], "5d1f26f776a3ea56c2becd3ec2fa2cf8e88bd62c43a20f79415a96e82a3da11d")
        self.assertIn("drho_u=", self.line)
        self.assertIn("gate_b1=Go failing_ids=[] blocked=[]", self.line)
        # per-run keys (§9.4)
        u0 = r["runs"]["b2u_b0_attention_s0_a1"]
        self.assertEqual(u0["condition"], "U")
        self.assertEqual(set(u0["eval"]["it0001600"]["mask0.20"]["per_seed"]), {"7100", "7101", "7102"})
        self.assertTrue(u0["repro"]["pass"])
        self.assertLess(u0["perm"]["rel_err_tf32off"], 1e-4)
        t0 = r["runs"]["b2mt_attention_s0_a1"]
        self.assertEqual(t0["condition"], "T")
        self.assertEqual(sorted(t0["eval"]), ["it0000400", "it0000800", "it0001200", "it0001600"])
        self.assertIn("rho_star_h", t0["eval"]["it0001600"]["mask0.20"])
        self.assertIn("UEVAL b2u_b0_attention_s0_a1 scored_exec=exec1", self.runs_log)

    def test_legacy_table_matches_plan(self):
        r = self.run_tool([self.dep()])
        L = r["legacy_p4_m10"]
        self.assertEqual(L["mask_pairing"], "unverified_global_rng")
        self.assertAlmostEqual(L["delta_rho_h_0.20"], -0.459, places=3)
        self.assertAlmostEqual(L["delta_rho_h_0.20_2se"], 0.1718, places=4)
        self.assertAlmostEqual(L["delta_r_h_0.20"], 0.028, places=3)
        self.assertAlmostEqual(L["per_run"]["b0_attention_s0_a1"]["r_h_0.00"], 0.4169, places=4)
        self.assertAlmostEqual(L["per_run"]["b0_attention_s0_a1"]["rho_star_h_0.20"], 0.308, places=3)
        self.assertAlmostEqual(L["means"]["rho_h_0.20"]["mlp_matched"], 0.762, places=3)

    def test_robustness_gain(self):
        r = self.run_tool([self.dep(u_over=gain_u(), t_over=gain_t())])
        self.assertEqual((r["verdict"], r["b2_outcome"]), ("PASS", "ROBUSTNESS_GAIN"))
        self.assertTrue(r["b2_gain"] and r["u_gain"] and r["t_gap_kept"])
        self.assertFalse(r["caveat_required"])
        self.assertEqual(r["gate_b1"], "Go")

    def test_absence_representation_only(self):
        r = self.run_tool([self.dep(u_over=gain_u(), t_over=gain_t(0.60, 0.55))])
        self.assertEqual(r["b2_outcome"], "ABSENCE_REPRESENTATION_ONLY")
        self.assertFalse(r["t_gap_kept"])
        self.assertFalse(r["t_deficit"])
        self.assertTrue(r["caveat_required"])

    def test_t_diverged_u_gain_unevaluable(self):
        over = gain_t()
        over["b2mt_mlp_mind_s1_a1"] = {"outcome": "div_crash"}
        r = self.run_tool([self.dep(u_over=gain_u(), t_over=over)])
        self.assertEqual((r["verdict"], r["decision_row"]), ("PASS", 4), r["blocked_detail"])
        self.assertEqual((r["b2_outcome"], r["t_status"]), ("U_GAIN_T_UNEVALUABLE", "diverged"))
        self.assertIn("drho_t=null g_t=null t_status=diverged", self.line)
        self.assertIsNone(r["gates"]["B2-L-1"]["pass"])
        self.assertEqual(r["t_diverged_attempts"], ["b2mt_mlp_mind_s1_a1"])
        tp = r["t_partial"]["f0.20"]
        self.assertEqual((tp["n_attention_mtrain"], tp["n_mlp_mind_mtrain"]), (3, 2))
        self.assertAlmostEqual(tp["delta_rho"], 0.40, places=9)
        self.assertEqual(r["gates"]["B2-V-1"]["per_attempt"]["b2mt_mlp_mind_s1_a1"]["mode"][:9], "integrity")

    def test_t_diverged_but_completed_is_scored_and_reported(self):
        over = {"b2mt_attention_s2_a1": {"nan_step": 1200}}
        r = self.run_tool([self.dep(t_over=over)])
        self.assertEqual((r["verdict"], r["t_status"], r["b2_outcome"]), ("PASS", "diverged", "NO_GAIN"), r["blocked_detail"])
        self.assertNotIn("b2mt_attention_s2_a1", r["gates"]["PERM"]["gate"])
        self.assertIn("b2mt_attention_s2_a1", r["gates"]["PERM"]["reported"])
        self.assertEqual(r["runs"]["b2mt_attention_s2_a1"]["class"], "completed")

    def test_shadow_disagreement(self):
        u = gain_u()
        for a in fx.U_AIDS:  # per-step means say the opposite
            u[a]["rstep"] = {"0.10": 0.01, "0.20": 0.01} if "_attention_" in a else {"0.10": 0.9, "0.20": 0.9}
        r = self.run_tool([self.dep(u_over=u, t_over=gain_t())])
        self.assertEqual(r["b2_outcome"], "ROBUSTNESS_GAIN")
        self.assertEqual(r["shadow_outcome_rstep"], "NO_GAIN")
        self.assertTrue(r["metric_disagreement"])

    def test_exec2_scored_after_failed_exec1(self):
        u = {"b0_attention_s1_a1": {"exec1_fail": True}}
        r = self.run_tool([self.dep(u_over=u)])
        self.assertEqual(r["verdict"], "PASS", r["blocked_detail"])
        self.assertEqual(r["runs"]["b2u_b0_attention_s1_a1"]["eval"]["it0001600"]["scored_exec"], "exec2")

    def test_multi_part_deposits(self):
        t = tspecs()
        d1 = {"part": 1, "u": uspecs(), "t": t[:4]}
        d2 = {"part": 2, "u": [], "t": t[4:], "identity": fx.identity_text(), "session": {"part": 2}}
        r = self.run_tool([d1, d2])
        self.assertEqual((r["verdict"], r["b2_outcome"]), ("PASS", "NO_GAIN"), r["blocked_detail"])
        self.assertEqual(len(r["deposits"]), 2)

    def test_ablation_labels_and_incomplete(self):
        r = self.run_tool([self.dep()])
        a = r["ablation_idx"]
        self.assertEqual((a["ablation_status"], a["n_runs"]), ("complete", 3))
        self.assertIsNotNone(a["keying_mask0"])
        self.assertIsNotNone(a["keying_rho_label"])
        self.assertEqual(len(a["perm_rel_err"]), 3)
        r = self.run_tool([self.dep(t_drop=("b2idx_attention_s2_a1",), session={"spend_cap_hit": "true"},
                                    state_extra=["SPEND_CAP_HIT 6.01"], blocked=["spend_cap"])])
        self.assertEqual(r["verdict"], "PASS", r["blocked_detail"])  # required set complete: only b2idx stops
        a = r["ablation_idx"]
        self.assertEqual((a["ablation_status"], a["n_runs"], a["keying_mask0_label"]), ("incomplete", 2, None))
        self.assertIsNotNone(a["keying_mask0"])

    def test_ablation_divergence_never_moves_verdict(self):
        r = self.run_tool([self.dep(t_over={"b2idx_attention_s0_a1": {"outcome": "div_crash"}})])
        self.assertEqual((r["verdict"], r["t_status"]), ("PASS", "ok"))
        self.assertEqual(r["ablation_idx"]["cell_status"]["b2idx_attention_s0"]["status"], "diverged")


class TestFail(Base):
    def test_perm_fail_row2(self):
        r = self.run_tool([self.dep(t_over={"b2mt_attention_s1_a1": {"perm": 3e-4}})])
        self.assertEqual((r["verdict"], r["decision_row"], r["failing_ids"], r["b2_outcome"]), ("FAIL", 2, ["PERM"], None))
        self.assertFalse(r["gates"]["PERM"]["gate"]["b2mt_attention_s1_a1"]["pass"])

    def test_perm_missing_on_u_attention(self):
        r = self.run_tool([self.dep(u_over={"b0_attention_s2_a1": {"perm": None}})])
        self.assertEqual((r["verdict"], r["failing_ids"]), ("FAIL", ["PERM"]))

    def test_perm_reported_break_does_not_fail(self):
        r = self.run_tool([self.dep(t_over={"b2idx_attention_s0_a1": {"perm": 9.0}})])
        self.assertEqual(r["verdict"], "PASS")

    def test_l1_fail_row3(self):
        over = {"b2mt_attention_s0_a1": {"l1": "fall"}, "b2mt_attention_s1_a1": {"l1": "fall"}}
        r = self.run_tool([self.dep(t_over=over)])
        self.assertEqual((r["verdict"], r["decision_row"], r["failing_ids"]), ("FAIL", 3, ["B2-L-1"]))

    def test_l2_fail_row3(self):
        r = self.run_tool([self.dep(t_over={"b2mt_mlp_mind_s2_a1": {"l2": "rise"}})])
        self.assertEqual((r["verdict"], r["failing_ids"]), ("FAIL", ["B2-L-2"]))

    def test_l1_not_evaluated_when_diverged(self):
        over = {"b2mt_attention_s0_a1": {"l1": "fall"}, "b2mt_attention_s1_a1": {"l1": "fall"},
                "b2mt_mlp_mind_s0_a1": {"outcome": "div_crash"}}
        r = self.run_tool([self.dep(t_over=over)])
        self.assertEqual((r["verdict"], r["t_status"]), ("PASS", "diverged"))


class TestBlocked(Base):
    def assertBlocked(self, r, code):
        self.assertEqual((r["verdict"], r["decision_row"], r["b2_outcome"]), ("BLOCKED", 1, None))
        self.assertIn(code, r["blocked_reason"], r["blocked_detail"])
        self.assertIn("blocked=[", self.line)

    def test_unsealed_deposit(self):
        self.assertBlocked(self.run_tool([self.dep()], seal_skip=(0,)), "deposit_check")

    def test_tarball_sha_mismatch(self):
        self.assertBlocked(self.run_tool([self.dep()], tarball_sha="ab" * 32), "deposit_check")

    def test_venue_colab(self):
        self.assertBlocked(self.run_tool([self.dep(venue="colab")], venue="colab", seal_venue="colab"), "venue_mismatch")

    def test_gpu_not_4090(self):
        r = self.run_tool([self.dep(gpu="NVIDIA L4")])
        self.assertBlocked(r, "gpu_mismatch")
        self.assertIn("B2-V-2", r["blocked_reason"])

    def test_p4_ckpts_unavailable(self):
        d = {"part": 1, "u": [], "t": [], "blocked": ["p4_ckpts_unavailable"],
             "identity": "candidate_root=/content/SuperMimic-Reproduced match=false\nroot=none\n"}
        r = self.run_tool([d])
        self.assertBlocked(r, "U-ID")
        self.assertFalse(r["gates"]["U-ID"]["pass"])

    def test_uid_size_mismatch(self):
        self.assertBlocked(self.run_tool([self.dep(identity=fx.identity_text(size_break="b0_mlp_matched_s1_a1"))]), "U-ID")

    def test_uid_copy_mismatch(self):
        self.assertBlocked(self.run_tool([self.dep(identity=fx.identity_text(copy_break="b0_attention_s0_a1"))]), "U-ID")

    def test_uid_wrong_root(self):
        self.assertBlocked(self.run_tool([self.dep(identity=fx.identity_text(root="/tmp/elsewhere"))]), "U-ID")

    def test_u_repro_fail(self):
        r = self.run_tool([self.dep(u_over={"b0_mlp_matched_s0_a1": {"repro_break": True}})])
        self.assertBlocked(r, "U-REPRO")
        self.assertFalse(r["runs"]["b2u_b0_mlp_matched_s0_a1"]["repro"]["pass"])

    def test_ms_stream_differs_across_arms(self):
        r = self.run_tool([self.dep(t_over={"b2mt_mlp_mind_s0_a1": {"tamper": {("0.20", 7101): "flip"}}})])
        self.assertBlocked(r, "MS")
        self.assertTrue(any("common prefix" in p for p in r["gates"]["MS"]["problems"]))

    def test_ms_wrong_k(self):
        r = self.run_tool([self.dep(u_over={"b0_attention_s0_a1": {"tamper": {("0.10", 7100): "k"}}})])
        self.assertBlocked(r, "MS")

    def test_ms_calls_mismatch(self):
        self.assertBlocked(self.run_tool([self.dep(u_over={"b0_attention_s2_a1": {"tamper": {("0.20", 7102): "calls"}}})]), "MS")

    def test_ms_wrong_seed(self):
        self.assertBlocked(self.run_tool([self.dep(t_over={"b2mt_attention_s1_a1": {"tamper": {("0.10", 7102): "seed"}}})]), "MS")

    def test_ms_missing_stream_file(self):
        d = self.dep(drop=["logs/eval/b2mt_attention_s0_a1/it0001600/exec1/maskstream_mask0.20_ms7100.npz"])
        r = self.run_tool([d])
        self.assertBlocked(r, "MS")

    def test_ms_on_b2idx_is_reported_only(self):
        r = self.run_tool([self.dep(t_over={"b2idx_attention_s1_a1": {"tamper": {("0.20", 7101): "flip"}}})])
        self.assertEqual(r["verdict"], "PASS")
        self.assertFalse(r["gates"]["MS"]["reported"]["pass"])

    def test_v2_updates(self):
        self.assertBlocked(self.run_tool([self.dep(t_over={"b2mt_attention_s1_a1": {"updates_bump": 3}})]), "B2-V-2")

    def test_v2_argv(self):
        r = self.run_tool([self.dep(t_over={"b2mt_mlp_mind_s2_a1": {"argv_extra": ["--policy-trainer.lr", "0.0001"]}})])
        self.assertBlocked(r, "B2-V-2")

    def test_v3_train_mask_frac(self):
        self.assertBlocked(self.run_tool([self.dep(t_over={"b2mt_attention_s0_a1": {"train_mask_frac": 0.0}})]), "B2-V-3")

    def test_v3_mlp_mind_params(self):
        self.assertBlocked(self.run_tool([self.dep(t_over={"b2mt_mlp_mind_s0_a1": {"params": 520000}})]), "B2-V-3")

    def test_v3_descriptor(self):
        self.assertBlocked(self.run_tool([self.dep(t_over={"b2mt_attention_s2_a1": {"descriptor": "ff" * 32}})]), "B2-V-3")

    def test_v3_seam(self):
        self.assertBlocked(self.run_tool([self.dep(t_over={"b2mt_attention_s2_a1": {"outcome": "seam"}})]), "SEAM")

    def test_v4_missing_curve_eval(self):
        self.assertBlocked(self.run_tool([self.dep(t_over={"b2mt_mlp_mind_s1_a1": {"skip_curve": True}})]), "B2-V-4")

    def test_v4_missing_u_eval(self):
        r = self.run_tool([self.dep(u_over={"b0_mlp_matched_s2_a1": {"evals": False}})])
        self.assertBlocked(r, "B2-V-4")

    def test_t_cell_missing(self):
        r = self.run_tool([self.dep(t_drop=("b2mt_mlp_mind_s2_a1",))])
        self.assertBlocked(r, "B2-V-1")

    def test_t_oom(self):
        self.assertBlocked(self.run_tool([self.dep(t_over={"b2mt_mlp_mind_s0_a1": {"outcome": "oom"}})]), "OOM")

    def test_t_infra_cap(self):
        t = tspecs(drop=("b2mt_attention_s1_a1",))
        t += [T("b2mt_attention_s1_a1", outcome="infra_disconnect"), T("b2mt_attention_s1_a2", outcome="infra_disconnect")]
        self.assertBlocked(self.run_tool([{"part": 1, "u": uspecs(), "t": t}]), "INFRA_cap")

    def test_t_infra_then_completed_passes(self):
        t = tspecs(drop=("b2mt_attention_s1_a1",))
        t += [T("b2mt_attention_s1_a1", outcome="infra_disconnect"), T("b2mt_attention_s1_a2", live=True)]
        r = self.run_tool([{"part": 1, "u": uspecs(), "t": t}])
        self.assertEqual(r["verdict"], "PASS", r["blocked_detail"])
        self.assertEqual(r["scored_set"]["T"]["b2mt_attention_s1"], "b2mt_attention_s1_a2")

    def test_spend_cap_before_required_set(self):
        r = self.run_tool([self.dep(t_drop=("b2mt_mlp_mind_s2_a1", "b2idx_attention_s0_a1", "b2idx_attention_s1_a1",
                                            "b2idx_attention_s2_a1"),
                                    session={"spend_cap_hit": "true"}, blocked=["spend_cap"])])
        self.assertBlocked(r, "spend_cap")

    def test_rho_undefined_t(self):
        r = self.run_tool([self.dep(t_over={"b2mt_mlp_mind_s1_a1": {"r0": 0.0}})])
        self.assertBlocked(r, "rho_undefined:b2mt_mlp_mind_s1_a1")

    def test_blocked_md_plan_gap(self):
        self.assertBlocked(self.run_tool([self.dep(blocked=["plan_gap"])]), "blocked_md:plan_gap")

    def test_r1_unresolved(self):
        self.assertBlocked(self.run_tool([self.dep(blocked=["R1_unresolved"])]), "R1_unresolved")

    def test_extra_exec3_rejected(self):
        d = self.dep()
        src = fx.deposit_files(d)
        pre = "logs/eval/b2u_b0_attention_s0_a1/it0001600/exec1/"
        extra = {k.replace("/exec1/", "/exec3/"): v for k, v in src.items() if k.startswith(pre)}
        d["drop"] = [pre]
        d["extra"] = extra
        self.assertBlocked(self.run_tool([d]), "B2-V-4")

class TestReviewR1(Base):
    """Regression tests for packets/P5/review/review-r1 objections 2, 3, 6, 7."""
    def assertBlocked(self, r, code):
        self.assertEqual((r["verdict"], r["decision_row"]), ("BLOCKED", 1))
        self.assertIn(code, r["blocked_reason"], r["blocked_detail"])

    def _move_exec(self, d, aid_dir, src, dst, keep_src=False):
        files = fx.deposit_files(d)
        pre = "logs/eval/%s/it0001600/%s/" % (aid_dir, src)
        extra = {k.replace("/%s/" % src, "/%s/" % dst): v for k, v in files.items() if k.startswith(pre)}
        if not keep_src:
            d["drop"] = [pre]
        d["extra"] = extra
        return d

    def test_exec2_without_exec1(self):
        d = self._move_exec(self.dep(), "b2u_b0_attention_s0_a1", "exec1", "exec2")
        self.assertBlocked(self.run_tool([d]), "B2-V-4")

    def test_exec3_alongside_valid_exec1(self):
        d = self._move_exec(self.dep(), "b2u_b0_attention_s0_a1", "exec1", "exec3", keep_src=True)
        r = self.run_tool([d])
        self.assertBlocked(r, "B2-V-4")
        self.assertTrue(r["runs"]["b2u_b0_attention_s0_a1"]["eval"]["it0001600"]["executions"])

    def test_exec2_after_clean_exec1_with_bad_content(self):
        d = self.dep()
        files = fx.deposit_files(d)
        pre = "logs/eval/b2mt_attention_s1_a1/it0001600/exec1/"
        bad = pre + "b2mt_attention_s1_attention_mask0.20_ms7101.json"
        jd = json.loads(files[bad])
        jd["summary"].pop("terms")
        extra = {k.replace("/exec1/", "/exec2/"): v for k, v in files.items() if k.startswith(pre)}
        extra[bad] = json.dumps(jd).encode()
        d["extra"] = extra
        self.assertBlocked(self.run_tool([d]), "B2-V-4")

    def test_attempt_after_completed(self):
        t = tspecs() + [T("b2mt_mlp_mind_s0_a2")]
        self.assertBlocked(self.run_tool([{"part": 1, "u": uspecs(), "t": t}]), "attempt_history")

    def test_missing_a1(self):
        t = tspecs(drop=("b2mt_attention_s2_a1",)) + [T("b2mt_attention_s2_a2")]
        self.assertBlocked(self.run_tool([{"part": 1, "u": uspecs(), "t": t}]), "attempt_history")

    def test_attempt_history_in_b2idx_is_reported(self):
        t = tspecs(drop=("b2idx_attention_s1_a1",)) + [T("b2idx_attention_s1_a2", r0=0.22)]
        r = self.run_tool([{"part": 1, "u": uspecs(), "t": t}])
        self.assertEqual(r["verdict"], "PASS", r["blocked_detail"])
        self.assertTrue(r["ablation_idx"]["cell_status"]["b2idx_attention_s1"]["status"].startswith("attempt_history"))

    def test_maskstream_json_not_object(self):
        d = self.dep(extra={"logs/eval/b2mt_attention_s0_a1/it0001600/exec1/maskstream_mask0.10_ms7100.json": b"[]"})
        self.assertBlocked(self.run_tool([d]), "MS")

    def test_maskstream_json_not_object_in_b2idx_is_reported(self):
        d = self.dep(extra={"logs/eval/b2idx_attention_s0_a1/it0001600/exec1/maskstream_mask0.10_ms7100.json": b"[]"})
        r = self.run_tool([d])
        self.assertEqual(r["verdict"], "PASS", r["blocked_detail"])
        self.assertFalse(r["gates"]["MS"]["reported"]["pass"])

    def test_shadow_null_when_t_rstep0_zero(self):
        r = self.run_tool([self.dep(t_over={"b2mt_mlp_mind_s1_a1": {"rstep0": 0.0}})])
        self.assertEqual((r["verdict"], r["b2_outcome"]), ("PASS", "NO_GAIN"), r["blocked_detail"])
        self.assertIsNone(r["shadow_outcome_rstep"])
        self.assertIsNotNone(r["shadow_outcome_abs"])


class TestReviewR2(Base):
    """Regression tests for packets/P5/review/review-r2 items 6 and 10."""
    def test_maskstream_frac_wrong_type(self):
        for aid in ("b2mt_attention_s0_a1", "b2idx_attention_s0_a1"):
            d = self.dep()
            rel = "logs/eval/%s/it0001600/exec1/maskstream_mask0.10_ms7100.json" % aid
            meta = json.loads(fx.deposit_files(d)[rel])
            meta["frac"] = []
            d["extra"] = {rel: json.dumps(meta).encode()}
            r = self.run_tool([d])
            if aid.startswith("b2mt"):
                self.assertEqual(r["verdict"], "BLOCKED")
                self.assertIn("MS", r["blocked_reason"])
            else:
                self.assertEqual(r["verdict"], "PASS", r["blocked_detail"])
                self.assertFalse(r["gates"]["MS"]["reported"]["pass"])

    def test_aborted_part_then_complete_part_passes(self):
        t = tspecs()
        a1 = T("b2mt_attention_s1_a1", outcome="infra_disconnect")
        rest = [x for x in t if x["aid"] != "b2mt_attention_s1_a1"]
        d1 = {"part": 1, "u": uspecs(), "t": [x for x in rest[:2]] + [a1], "blocked": ["aborted"]}
        d2 = {"part": 2, "u": [], "t": [T("b2mt_attention_s1_a2", live=True)] + rest[2:], "session": {"part": 2}}
        r = self.run_tool([d1, d2])
        self.assertEqual(r["verdict"], "PASS", r["blocked_detail"])
        self.assertEqual(len(r["aborted_deposits"]), 1)

    def test_aborted_with_incomplete_required_set(self):
        r = self.run_tool([self.dep(t_drop=("b2mt_mlp_mind_s2_a1",), blocked=["aborted"])])
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertIn("B2-V-1", r["blocked_reason"])  # the evidence gates decide (review r3: abort is provenance only)
        self.assertNotIn("aborted", r["blocked_reason"])

    def test_aborted_does_not_turn_fail_into_blocked(self):
        u = {"b0_attention_s2_a1": {"perm": None}}
        r0 = self.run_tool([self.dep(u_over=u, t_drop=("b2idx_attention_s2_a1",))])
        r1 = self.run_tool([self.dep(u_over=u, t_drop=("b2idx_attention_s2_a1",), blocked=["aborted"])])
        self.assertEqual((r0["verdict"], r0["failing_ids"]), ("FAIL", ["PERM"]))
        self.assertEqual((r1["verdict"], r1["failing_ids"]), ("FAIL", ["PERM"]))

    def test_aborted_during_ablation_does_not_change_verdict(self):
        r = self.run_tool([self.dep(t_drop=("b2idx_attention_s2_a1",), blocked=["aborted"])])
        self.assertEqual(r["verdict"], "PASS", r["blocked_detail"])
        self.assertEqual(r["ablation_idx"]["ablation_status"], "incomplete")


class TestReviewR3(Base):
    """Regression tests for packets/P5/review/review-r3 items 2, 4, 8, 9."""
    def _rel(self, aid, name, it="it0001600", ex="exec1"):
        return "logs/eval/%s/%s/%s/%s" % (aid, it, ex, name)

    def test_exec2_not_authorized_by_missing_exit_record(self):
        d = self.dep()
        files = fx.deposit_files(d)
        aid = "b2mt_attention_s1_a1"
        pre = "logs/eval/%s/it0001600/exec1/" % aid
        extra = {k.replace("/exec1/", "/exec2/"): v for k, v in files.items() if k.startswith(pre)}
        log = files[pre + "eval.log"].decode().replace("exit=0\n", "")
        extra[pre + "eval.log"] = log.encode()
        bad = pre + "b2mt_attention_s1_attention_mask0.20_ms7101.json"
        jd = json.loads(files[bad]); jd["summary"].pop("terms")
        extra[bad] = json.dumps(jd).encode()
        d["extra"] = extra
        r = self.run_tool([d])
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertIn("B2-V-4", r["blocked_reason"])

    def test_exec2_authorized_by_recorded_nonzero_exit(self):
        d = self.dep()
        files = fx.deposit_files(d)
        aid = "b2mt_attention_s1_a1"
        pre = "logs/eval/%s/it0001600/exec1/" % aid
        extra = {k.replace("/exec1/", "/exec2/"): v for k, v in files.items() if k.startswith(pre)}
        extra[pre + "eval.log"] = files[pre + "eval.log"].decode().replace("exit=0\n", "exit=143\n").encode()
        bad = pre + "b2mt_attention_s1_attention_mask0.20_ms7101.json"
        jd = json.loads(files[bad]); jd["summary"].pop("terms")
        extra[bad] = json.dumps(jd).encode()
        d["extra"] = extra
        r = self.run_tool([d])
        self.assertEqual(r["verdict"], "PASS", r["blocked_detail"])
        self.assertEqual(r["runs"][aid]["eval"]["it0001600"]["scored_exec"], "exec2")

    def test_ablation_stream_calls_nan_is_isolated(self):
        rel = self._rel("b2idx_attention_s0_a1", "maskstream_mask0.10_ms7100.json")
        d = self.dep()
        meta = json.loads(fx.deposit_files(d)[rel]); meta["calls"] = float("nan")
        d["extra"] = {rel: json.dumps(meta).encode()}
        r = self.run_tool([d])
        self.assertEqual(r["verdict"], "PASS", r["blocked_detail"])
        self.assertFalse(r["gates"]["MS"]["reported"]["pass"])

    def test_perm_not_object(self):
        r = self.run_tool([self.dep(extra={"meta/perm_b2idx_attention_s1_a1.json": b"[]"})])
        self.assertEqual(r["verdict"], "PASS", r["blocked_detail"])
        r = self.run_tool([self.dep(extra={"meta/perm_b2mt_attention_s0_a1.json": b"[]"})])
        self.assertEqual((r["verdict"], r["failing_ids"]), ("FAIL", ["PERM"]))

    def test_perm_nan_values(self):
        bad = json.dumps({"rel_err_tf32off": float("nan"), "rel_err_default": float("inf"), "rel_err_masked": float("nan"),
                          "auto_mask_frac_used": 0.0}).encode()
        r = self.run_tool([self.dep(extra={"meta/perm_b2idx_attention_s2_a1.json": bad})])
        self.assertEqual(r["verdict"], "PASS", r["blocked_detail"])
        r = self.run_tool([self.dep(extra={"meta/perm_b2u_b0_attention_s1_a1.json": bad})])
        self.assertEqual((r["verdict"], r["failing_ids"]), ("FAIL", ["PERM"]))
        self.assertIsNone(r["gates"]["PERM"]["gate"]["b2u_b0_attention_s1_a1"]["rel_err_tf32off"])

    def test_truncated_npz_header(self):
        import io, zipfile
        zb = io.BytesIO()
        with zipfile.ZipFile(zb, "w") as z:
            z.writestr("packed.npy", b"\x93NUMPY\x01")
        for aid, scored in (("b2idx_attention_s1_a1", False), ("b2mt_mlp_mind_s0_a1", True)):
            r = self.run_tool([self.dep(extra={self._rel(aid, "maskstream_mask0.20_ms7102.npz"): zb.getvalue()})])
            if scored:
                self.assertEqual(r["verdict"], "BLOCKED")
                self.assertIn("MS", r["blocked_reason"])
            else:
                self.assertEqual(r["verdict"], "PASS", r["blocked_detail"])


class TestFuzzIsolation(Base):
    """Review r4 #9 and the general rule behind it: malformed report-only (b2idx) evidence never stops the verdict
    and never changes it; malformed scored evidence gives BLOCKED or FAIL, never a crash."""
    BAD = (b"[1]", b'{"attention": [1], "descriptor": [1], "seam": [1], "params": "x", "train_mask_frac": []}', b"NaN",
           b"\x00garbage")

    def _files(self, aid):
        d = self.dep()
        return d, sorted(k for k in fx.deposit_files(d) if ("/%s/" % aid) in k or k.endswith("_%s.json" % aid)
                         or k.endswith("_%s.txt" % aid) or k.endswith("train_%s.log" % aid))

    def test_report_only_isolation(self):
        aid = "b2idx_attention_s0_a1"
        _d, rels = self._files(aid)
        rels = [r for r in rels if r.endswith((".json", ".npz", ".txt"))]
        picks = [r for r in rels if "junior_policy" in r or "perm_" in r or "attempt_" in r or "harness_" in r]
        picks += [r for r in rels if "/it0001600/" in r and ("mask0.20_ms7101" in r)]
        self.assertGreaterEqual(len(picks), 6, picks)
        for rel in picks:
            for bad in self.BAD:
                d = self.dep(extra={rel: bad})
                r = self.run_tool([d])
                self.assertEqual(r["verdict"], "PASS", (rel, bad, r["blocked_detail"]))

    def test_scored_malformed_never_crashes(self):
        aid = "b2mt_mlp_mind_s1_a1"
        _d, rels = self._files(aid)
        picks = [r for r in rels if "junior_policy" in r or "perm_" in r or "harness_" in r]
        picks += [r for r in rels if "/it0001600/" in r and "mask0.10_ms7100" in r]
        for rel in picks:
            for bad in self.BAD[:2]:
                r = self.run_tool([self.dep(extra={rel: bad})])
                self.assertIn(r["verdict"], ("BLOCKED", "FAIL", "PASS"), rel)


if __name__ == "__main__":
    unittest.main()
