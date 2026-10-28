# CR-B0-1 MANIFEST ADDENDUM (extends packets/P1/FREEZE_MANIFEST.md; does not replace it)

**Program:** supermimic-junior-b-colab. **Packet:** P4-prep. **Change request:** CR-B0-1 (`spikes/B0/PLAN.md` §2.2, sha256 `ed6b6a54a860bbfc67d7c822b5394804b8d408f6aae57fbeb118d2ea63c52557`).
**Method:** v1.1 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0` + OVERLAY-001. **Decision cap:** Provisional. Sealed in `logs/seal.log` (event `MANIFEST-ADDENDUM-P4`).
**Base:** P1 FREEZE_MANIFEST sealed `e1d0eae27bd13170b752005eba9dedd65a0daa6bda6f3885a5d01335bf14007a`, manifest digest `cd504ca289016c2a42c2e9a90cbe92723cdb8a95bc5e030ddedc9b16563d5ff0` (reproduced byte-for-byte on 2026-10-26 by `packets/P1/scripts/make_manifest.sh` before any new config existed).

## 1. The 12 D-004 frozen files — unchanged hashes

```
2f7c5431787073566de89a711b2988b1050369c395e992ec602578aa50d5de64  code/attention_policy.py
f313bddf8e5468e513868a95658814105c5463870ab4306e8ffbcec6af848f00  code/descriptor_v2.py
4406a0385e0156034b423f575f8bce2e5433474898b7b50e1ae048af5a4431e3  code/eval_entry.py
d70c0fa1bf5885088d458383a091134d4573ea485f5aa7d2fc35c51c7700caa1  code/mlp_baseline.py
0c234dd458586b6c165c9678058f4de6ad3bc701b11da8110ac8cdfe17270dae  code/requirements-smoke.txt
d190f67cf288eb92f9c8cf10eb106dd2922f56821cb20ff24e4f697e9f7fce7b  code/tests/test_smoke.py
096520611cf90c285140f63830e95a2f4df6b33de561f15d14972396729984f9  code/tools/make_notebook.py
fe585ffe935af132728bc69d4f7ccf044e8fc77b013566b9895af0f3d2e19431  code/train_entry.py
5f18b09c0b6208a955bd18a27706b46a8a0192bc1b92e85b78e9ae90354226fe  code/vendor/NOTES.md
70cee6244d39ce861d9e318f354bc1473a179a55fddbbd0d91c036911317bfc7  configs/colab_smoke.yaml
302c27409e836d044659ff98af216a61865acec602951686bee377045c330e6d  docs/COLAB_RUNBOOK.md
5b59be6a8f5467f6f6f2b60f11a42207293436278e07f3f25a3c7de35735f6e8  notebooks/colab_smoke.ipynb
```

The block above is the P1 §1 block, copied. Each line was re-checked against the working tree (`sha256sum -c`: 12 OK) at sealing time.

## 2. New files (CR-B0-1 (a)–(d); new files only, outside `code/`)

```
d19e9297bf90530859c25aedc5ed3834064a7fc19838933def6b653e8a4cd495  configs/b0_microbench.yaml
283030054d53cc5b7002d696d9b466ae669b08d2a03960cabab8060fabde4729  configs/b0_microbench_lr05.yaml
07e565226cc25d8c84b7a3f5701d1264d6aa8549e3808b71c9d0c817bf729634  packets/P4/BUNDLE_CONTRACT.md
0e9cc73a98d7f006647e98210fa9014ee05811b112df8993a6e9b77215b5583f  packets/P4/UPSTREAM_FACTS.md
e87478fd16b7b41bde302cfbf3bda5d45534e58278a35e8a09e8d102218af3be  packets/P4/b0_driver.sh
f43d8f5db9ad45fe6850aa87a4f549be56c6265b27d2e81bbe7dc840adf34b42  packets/P4/b0_driver_helper.py
```

| File | CR item | Note |
|---|---|---|
| `configs/b0_microbench.yaml` | (a) | byte copy of `configs/colab_smoke.yaml`. Only `run_name: b0`, `--schedule.max-hours: 1.5` and `--schedule.checkpoint-interval: 400` changed. No cap flag (F-1 unsuitable → harness stop) |
| `configs/b0_microbench_lr05.yaml` | (b) | equals (a) with `run_name: b0lr05` plus `--policy-trainer.lr: 0.0001` (0.5 × F-2 default 2e-4) |
| `packets/P4/UPSTREAM_FACTS.md` | (c) | F-1…F-5 with file:line at upstream `d9be385b…` |
| `packets/P4/b0_driver.sh`, `packets/P4/b0_driver_helper.py` | (d) | PLAN §4 driver (signal-restoring launcher, harness stop, closed attempt rules, §8.1 bundle) |
| `packets/P4/BUNDLE_CONTRACT.md` | (d) | machine-readable bundle layout read by the verdict tool |

## 3. Combined listing (18 files) and tarball (CR-B0-1 (e))

`packets/P4/make_cr_b0_1.sh list` (sorted, `LC_ALL=C`) gives the 18 lines of §1 + §2.

Combined listing digest (sha256 of that output): `e1603396beadcd1300c82adfbb56fdf24589a4d45cda0351700dd9fdae6f7f8c`

Tarball `packets/P4/junior_b_colab-CR-B0-1.tgz` (mode 0444): sha256 `763867682e3cfa05ca8eb6382ffc9124be2347b898531c60b904061776c33bff`.
It was built by `packets/P4/make_cr_b0_1.sh tar` with the P1 recipe: GNU tar, sorted names, mtime 2026-10-25 00:00:00 UTC, uid/gid 0, mode 644, gzip -n. The same recipe reproduces the P1 tarball `f69dd11e…1636` exactly. Two independent builds gave identical bytes. Extracted member hashes equal the combined listing.

Not in the tarball: the verdict tool (`spikes/B0/verdict/`, sealed separately as VERDICT-TOOL), the SIGINT check (`packets/P4/sigint_check/`), the read-only upstream clone (`packets/P4/upstream-ro/`) and `packets/P4/PRESTART.md`.

## 4. Runner use (PLAN §4.1)

Upload `junior_b_colab-CR-B0-1.tgz` to `/content/` and `packets/P4/b0_driver.sh` beside it (the driver checks that it is byte-identical to its tarball copy after unpacking). Then run `B0_TARBALL_SHA=<hash above> bash b0_driver.sh`. **No P4 attempt may start until PS-1…PS-5 hold** (`packets/P4/PRESTART.md`; PS-3 is open at the time of sealing).
