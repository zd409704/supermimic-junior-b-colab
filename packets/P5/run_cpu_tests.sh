#!/usr/bin/env bash
# P5-prep (g) CPU test run (research box). Usage: run_cpu_tests.sh <attempt N>  -> logs/p5prep/cpu-tests-attempt<N>.log
# Sections: freeze hashes; CR-B0-1 recipe reproduces 763867...; CR-B2-1 tarball deterministic and = the sealed file;
# P5 prep tests in the working tree and from the unpacked tarball (venue layout, frozen smoke 14/3); frozen smoke;
# verdict_b2 fixture tests. Final line: CPU_TESTS attempt=<N> result=PASS|FAIL <per-section results>.
set -u
R=/srv/claude/research/supermimic-junior-b-colab; cd $R
N=$1; LOG=$R/logs/p5prep/cpu-tests-attempt$N.log
[ -e "$LOG" ] && { echo "refusing: $LOG exists"; exit 2; }
mkdir -p $R/logs/p5prep
PY=$R/.venv/bin/python; X=$(mktemp -d)
res=()
sec() { echo; echo "## $1 ($(date -u +%Y-%m-%dT%H:%M:%SZ))"; }
{
echo "# P5-prep CPU tests attempt $N, $(date -u +%Y-%m-%dT%H:%M:%SZ), $($PY -c 'import sys,torch,numpy;print("python",sys.version.split()[0],"torch",torch.__version__,"numpy",numpy.__version__)')"
echo "# PLAN 5d1f26f776a3ea56c2becd3ec2fa2cf8e88bd62c43a20f79415a96e82a3da11d; script sha256 $(sha256sum $0 | cut -c1-64)"
sec "freeze: 12 D-004 + 6 CR-B0-1 files byte-identical (sha256sum -c of the P1 and P4 manifest blocks)"
{ sed -n '/^```$/,/^```$/p' packets/P1/FREEZE_MANIFEST.md | grep -v '```'; sed -n '/^## 2\./,/^## 3\./p' packets/P4/MANIFEST_ADDENDUM.md | sed -n '/^```$/,/^```$/p' | grep -v '```'; } > $X/frozen.sha
sha256sum -c $X/frozen.sha; r=$?; echo "frozen_files=$(wc -l < $X/frozen.sha) rc=$r"; res+=("freeze=$([ $r -eq 0 ] && echo ok || echo FAIL)")
sec "CR-B0-1 recipe reproduces the sealed CR-B0-1 tarball"
bash packets/P4/make_cr_b0_1.sh tar $X/p4.tgz; s=$(sha256sum $X/p4.tgz | cut -c1-64); echo "rebuilt $s"
[ "$s" = 763867682e3cfa05ca8eb6382ffc9124be2347b898531c60b904061776c33bff ] && res+=("crb01_rebuild=ok") || res+=("crb01_rebuild=FAIL")
sec "CR-B2-1 tarball: deterministic and equal to packets/P5/junior_b_colab-CR-B2-1.tgz"
bash packets/P5/make_cr_b2_1.sh tar $X/a.tgz; sleep 1; bash packets/P5/make_cr_b2_1.sh tar $X/b.tgz
sha256sum $X/a.tgz $X/b.tgz packets/P5/junior_b_colab-CR-B2-1.tgz; tar tzvf packets/P5/junior_b_colab-CR-B2-1.tgz
[ "$(sha256sum < $X/a.tgz)" = "$(sha256sum < $X/b.tgz)" ] && [ "$(sha256sum < $X/a.tgz)" = "$(sha256sum < packets/P5/junior_b_colab-CR-B2-1.tgz)" ] \
  && res+=("crb21_tarball=ok") || res+=("crb21_tarball=FAIL")
sec "(g) P5 prep tests, working tree"
$PY packets/P5/tests/test_p5_prep.py 2>&1 | grep -E '^(PASS|FAIL|P5_PREP_TESTS|PERM|frozen smoke)|Error'; r=${PIPESTATUS[0]}
res+=("p5_tests_tree=$([ $r -eq 0 ] && echo ok || echo FAIL)")
sec "(g) P5 prep tests, unpacked CR-B2-1 tarball (venue layout: no asset -> frozen smoke 14/3)"
mkdir $X/junior && tar xzf packets/P5/junior_b_colab-CR-B2-1.tgz -C $X/junior
(cd $X/junior && $PY packets/P5/tests/test_p5_prep.py 2>&1 | grep -E '^(PASS|FAIL|P5_PREP_TESTS|PERM|frozen smoke)|Error'; exit ${PIPESTATUS[0]}); r=$?
res+=("p5_tests_tarball=$([ $r -eq 0 ] && echo ok || echo FAIL)")
sec "frozen 14-test CPU smoke (code/tests/test_smoke.py), research box"
$PY code/tests/test_smoke.py 2>&1 | grep -E '^(PASS|SKIP|FAIL)|Error'; r=${PIPESTATUS[0]}
n=$($PY code/tests/test_smoke.py 2>/dev/null | grep -c '^PASS'); echo "pass_lines=$n rc=$r"
res+=("frozen_smoke=$([ $r -eq 0 ] && [ $n -eq 14 ] && echo ok || echo FAIL)")
sec "(h) verdict_b2 fixture tests"
$PY -I -m unittest discover -s spikes/B2/verdict -p 'test_*.py' -v 2>&1 | grep -v '^\[verdict_b2\]'; r=${PIPESTATUS[0]}
res+=("verdict_tests=$([ $r -eq 0 ] && echo ok || echo FAIL)")
all=PASS; for x in "${res[@]}"; do [[ $x == *FAIL ]] && all=FAIL; done
echo; echo "CPU_TESTS attempt=$N result=$all ${res[*]}"
} > "$LOG" 2>&1
tail -1 "$LOG"
