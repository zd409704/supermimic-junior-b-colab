# P1 FREEZE_MANIFEST — scaffold freeze (descriptor v2 + FX-1..FX-5)

**Program:** supermimic-junior-b-colab. **Packet:** P1. **Sealed:** 2026-10-25 EDT (America/Toronto); UTC/epoch in `logs/seal.log` (event `FREEZE P1 manifest`).
**Method:** v1.1, sha256 `9bdc872ea3f92e33893cb71de4db488bf05ca3bce6f78e9ef3fd7e214590afc0` + `method/local/OVERLAY-001-owner-colab-runner.md`. **Decision cap:** Provisional.
**Rule after freeze:** any change to a file listed in §1 needs a change request (method §4 Step 6) and a new manifest. A hash mismatch against this file without one is a Class-3 event.

## 1. Frozen files (`packets/P1/scripts/make_manifest.sh`; sha256, path)

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

Manifest digest (sha256 of the block above as printed by the script): `cd504ca289016c2a42c2e9a90cbe92723cdb8a95bc5e030ddedc9b16563d5ff0`. This equals the digest in the header of the CPU smoke log below, so the smoke ran on exactly these bytes.

## 2. What the frozen code contains

- Descriptor **v2** (D-DESC Recommend = candidate Y; `packets/P1/ddesc/decision.md`), default `attention.descriptor: v2`, morph_dim 16; v1 still selectable. Attention decoder 464 001 params (v1: 463 489); mlp_matched 468 317 (+0.93%).
- Action scaling stays in the upstream env only (no second scale layer); the descriptor carries ln σ and normalised τmax.
- FX-1 default pose from env init state (qpos0 only as a recorded fallback); FX-2 depth/8; FX-3 the 4 clip names verified in the dataset listing (none replaced); FX-4 J-agnostic shape-test wording and glob loading of the owner MJCF; FX-5 seam lines S1–S4, plus S5 (env action scale == descriptor σ). An `unverified` or `false` seam result raises.
- Change log: `packets/P1/fixes/CHANGES.md`; diffs: `fx-stage1.diff`, `ddesc-adopt.diff`, `round2.diff`, `p1-fixes-combined.diff` (pre-round-2). Cross-family review: `REVIEW-1.md` (BLOCK: O-1 blocker, O-2/O-3 major) → round 2 → `REVIEW-2.md` (**FREEZE-OK**, O-1..O-3 resolved).

## 3. Evidence bound to this freeze

| Artifact | sha256 |
|---|---|
| CPU smoke attempt 3 log `logs/smoke-cpu-attempt3-20261025-1537-EDT.log` | `c2a9ea92a2572cf28a9e2bb97f1ffb3ba9efcd5f699f6b2c80ee2e2313bdbf45` |
| P2 tarball `packets/P2/junior_b_colab-P1freeze.tgz` (deterministic: sorted, fixed mtime, uid 0, gzip -n; 12 files = §1) | `f69dd11eb532c10411bfd77e3f1f2c5edd36275f4a0b9c737624bb8cac341636` |
| D-DESC decision `packets/P1/ddesc/decision.md` | `8dcffe7d929a51f9f6fa2c97f0b42318c375b3c01e9a7c1a7e87680196283cd7` |
| D-DESC spike verdict `spikes/D-DESC/runs.log` | `3bb9580642fe9ef05f0b21796c3237932c940ca02b47ff9bf0739b4d045543b9` |
| Fixes review 2 `packets/P1/fixes/REVIEW-2.md` | `13a77e0d96914b60dbf4fd75c01e6247e8cd2bf3df8d38f1a9b82d540e4088d9` |
| `briefs/D-DESC.md` | `f2458a0ee77d936fb56aac9ac7e85aac46cbc0df33896a104063523501c79ca6` |
| `roster.md` | `5be8a85d97746e092de5c1e6e91fefaaafa5c5efebb9b36bc3a0a211708d84f6` |

## 4. Not covered / not claimed

- The owner asset `assets/home_humanoid_mjcf/` is not in the tarball and was not modified. Its XML and 27 mesh hashes were unchanged in the D-DESC spike (S-4).
- The upstream (`--mode upstream`) path, the loader identifiers in `configs/colab_smoke.yaml`, and seams S1–S5 are **unverified** until the owner's P2 Colab run. No Colab or GPU run has happened.
