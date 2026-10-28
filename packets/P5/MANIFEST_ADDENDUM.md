# CR-B2-1 MANIFEST ADDENDUM (extends packets/P1/FREEZE_MANIFEST.md and packets/P4/MANIFEST_ADDENDUM.md; replaces neither)

**Program:** supermimic-junior-b-colab. **Packet:** P5-prep. **Change request:** CR-B2-1 (`spikes/B2/PLAN.md` §2.3 (a)–(f), sha256 `5d1f26f776a3ea56c2becd3ec2fa2cf8e88bd62c43a20f79415a96e82a3da11d`).
**Method:** v1.1 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0` + OVERLAY-001. **Decision cap:** Provisional. Sealed in `logs/seal.log` (event `MANIFEST-ADDENDUM-P5`).
**Base:** CR-B0-1 tarball `packets/P4/junior_b_colab-CR-B0-1.tgz` sha256 `763867682e3cfa05ca8eb6382ffc9124be2347b898531c60b904061776c33bff` (seal TARBALL-P4), manifest addendum `0f203ffc206fd8e8b4a48f49c4d2bd02ad40a51ae86b0b3d0e0566e20164f79a`.

## 1. The 12 D-004 files and the 6 CR-B0-1 files: unchanged hashes

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
d19e9297bf90530859c25aedc5ed3834064a7fc19838933def6b653e8a4cd495  configs/b0_microbench.yaml
283030054d53cc5b7002d696d9b466ae669b08d2a03960cabab8060fabde4729  configs/b0_microbench_lr05.yaml
70cee6244d39ce861d9e318f354bc1473a179a55fddbbd0d91c036911317bfc7  configs/colab_smoke.yaml
302c27409e836d044659ff98af216a61865acec602951686bee377045c330e6d  docs/COLAB_RUNBOOK.md
5b59be6a8f5467f6f6f2b60f11a42207293436278e07f3f25a3c7de35735f6e8  notebooks/colab_smoke.ipynb
07e565226cc25d8c84b7a3f5701d1264d6aa8549e3808b71c9d0c817bf729634  packets/P4/BUNDLE_CONTRACT.md
0e9cc73a98d7f006647e98210fa9014ee05811b112df8993a6e9b77215b5583f  packets/P4/UPSTREAM_FACTS.md
e87478fd16b7b41bde302cfbf3bda5d45534e58278a35e8a09e8d102218af3be  packets/P4/b0_driver.sh
f43d8f5db9ad45fe6850aa87a4f549be56c6265b27d2e81bbe7dc840adf34b42  packets/P4/b0_driver_helper.py
```

These are the 12 lines of `packets/P1/FREEZE_MANIFEST.md` §1 and the 6 lines of `packets/P4/MANIFEST_ADDENDUM.md` §2, re-checked against the working tree at sealing time (`sha256sum -c`: 18 OK, `logs/p5prep/cpu-tests-attempt1.log` section "freeze"). **Proof that CR-B0-1 is unchanged:** the CR-B0-1 recipe `packets/P4/make_cr_b0_1.sh tar` re-run on the current tree reproduces the sealed CR-B0-1 tarball byte for byte, sha256 `763867682e3cfa05ca8eb6382ffc9124be2347b898531c60b904061776c33bff` (same log, section "CR-B0-1 recipe"). No frozen file was edited. CR-B2-1 is new files only.

## 2. New files (CR-B2-1 (a)–(e), (g); outside `code/`)

```
a50bc04259fb578c0b6f754977f3593b87f057cca713447d7d10501b2fcd89cf  configs/b2_idx.yaml
d8dab884175af41fe6b5cbb47b0371058edde14511ae504553a195e24be7a739  configs/b2_mtrain.yaml
3b0bf132c53d97cfe2c65a20828bcde34e0e786e198b900f88da203604365f29  packets/P5/BUNDLE_CONTRACT.md
197d2b8cd6955b93241b652c79618ffe525dfb7aeec723ea9f98fe9fda3ac093  packets/P5/b2_driver.sh
f4d73e1379f652268799fd26e0a826e444cd51055ec9be5aa20707159751524b  packets/P5/b2_driver_helper.py
323f3c08d8a840cb5bd53950404dda5965085c44f07cae9664062d078fde089b  packets/P5/maskstream.py
0e061988651c91734197ba50569fa79fd4aeba21e3456e644773866779f0a66e  packets/P5/mlp_mind.py
e63a57c5af1c4d488d92a6db35984f3c8d6ad045e0a4a808acf0078c84873ab7  packets/P5/p4_pip_freeze_ref.txt
c4cee827beed68c6a68205dc1b6abc6cab0426fb3e49f22792d2502a327d8023  packets/P5/p5_eval_entry.py
a69646b51ee21a22e6d4024e1debdd4c93045eb12d536dbd8139fb3c8a8eb805  packets/P5/p5_train_entry.py
570daf6e06cc1be8f526f1ed6e2c4d153a981561ac4a616b98bc7fe61adf2b01  packets/P5/perm_check.py
b4affb0d3590881617f9f60f725a267048eb4fa45473da8c1afcfaf590224c0b  packets/P5/tests/test_p5_prep.py
```

| File | CR item | Note |
|---|---|---|
| `configs/b2_idx.yaml` | (a) | byte copy of `configs/b0_microbench.yaml`; only `run_name: b2idx` and `attention.id_mode: index` changed |
| `configs/b2_mtrain.yaml` | (a) | byte copy; only `run_name: b2mt` and `b2.train_mask_frac: 0.1` changed. No tyro argument changes (upstream argv = P4's except `--run-name`, `--seed`) |
| `packets/P5/mlp_mind.py`, `packets/P5/p5_train_entry.py` | (b) | `mlp_mind` decoder (input `[z, x⊙keep, ind]`, indicator once; 467 491 params, +0.75% of 464 001, hidden (376, 188, 94, 47)) and registration wrapper; frozen `main()` called unchanged |
| `packets/P5/maskstream.py`, `packets/P5/p5_eval_entry.py` | (c) | fixed-seed mask stream (dedicated generator, seeds 7100/7101/7102, k = 3 / 6, nested) and the eval wrapper over one frozen `eval_entry.run_upstream` call per checkpoint |
| `packets/P5/perm_check.py` | (d) | PERM (§6): TF32-off gate value, default-TF32 and masked variants; `--mode cpu` for prep tests |
| `packets/P5/b2_driver.sh`, `packets/P5/b2_driver_helper.py`, `packets/P5/BUNDLE_CONTRACT.md`, `packets/P5/p4_pip_freeze_ref.txt` | (e) | driver (§4, §9.1), helper, bundle contract, P4 pip-freeze reference (byte copy of the P4 deposit's, `e63a57c5…`) |
| `packets/P5/tests/test_p5_prep.py` | (g) | CPU tests (14), also run on the venue (recorded, not gated) |

Outside the tarball (sealed separately): `packets/P5/make_cr_b2_1.sh` (recipe, `fc84f99af866833c2248bb3e471a7aa5a5233546ce775a3b0b7f55ed9d707999`), `packets/P5/run_cpu_tests.sh`, `packets/P5/IMPLEMENTATION_NOTES.md`, `packets/P5/mock/`, `packets/P5/review/`, `orch/jobs/p5-b2-attempt1/run.sh` and `orch/jobs/p5-b2-attempt1.json`.

## 3. Combined listing (30 files) and tarball (CR-B2-1 (f))

`packets/P5/make_cr_b2_1.sh list` (sorted, `LC_ALL=C`) gives the 30 lines of §1 + §2.

Combined listing digest (sha256 of that output): `dc8899563a356a40c9e7723f429568771544744de9dc097895061d7af4cb9553`

Tarball `packets/P5/junior_b_colab-CR-B2-1.tgz` (mode 0444, recipe as P1/P4: GNU tar, sorted names, mtime 2026-10-25 00:00:00 UTC, uid/gid 0, mode 644, `gzip -n`): sha256 `53a898e9b635d1317bebabe884f1450e52be2980165811859445c1b9b53ce851`. Two independent rebuilds give the same bytes (`logs/p5prep/cpu-tests-attempt1.log`).
