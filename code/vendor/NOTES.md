# Vendor notes: public mjlab SuperMimic-style reproduction

**Written:** 2026-10-25 (America/Toronto). Nothing is vendored in this tree. Clone it at runtime on Colab.

## Pin

| Item | Value |
|---|---|
| Repo | `https://github.com/CuboiLeo/SuperMimic-Reproduced` (MIT license) |
| Commit | `d9be385b3eeb13a638fb33fb200d3bfd9be9839f` (main, 2026-10-22, the HEAD when this was checked) |
| Base framework | mjlab @ `8bb2bc9e187797689ec82c78c35019afd2fd0376`, pinned by upstream `pyproject.toml` `[tool.uv.sources]` |
| Python | `>=3.12,<3.13` (upstream `requires-python`) |
| Upstream torch | `torch>=2.14.0` from the **cu130** index, plus `warp-lang` from the NVIDIA index and `mujoco-warp~=3.16`. See risk R1 in `docs/COLAB_RUNBOOK.md` |

```bash
git clone https://github.com/CuboiLeo/SuperMimic-Reproduced /content/SuperMimic-Reproduced
git -C /content/SuperMimic-Reproduced checkout d9be385b3eeb13a638fb33fb200d3bfd9be9839f
```

To vendor later (only if needed), use a git submodule at this commit under `code/vendor/SuperMimic-Reproduced` and keep the upstream LICENSE. Do not copy sources in by hand.

## Integration seam (what we change, what we do not)

Upstream policy: `supermimic/policy/nets.py`. It computes `Policy.forward(obs_hist, goal) = decoder(encoders["motion"](goal), obs_hist)`.

- `MotionEncoder`: goal (680, or 689 with `--env.anchor-obs`) → tanh latent z (32). **Unchanged.**
- `Decoder.forward(z, obs_hist)`: `cat(z, obs_hist*scale)` (962 dims) → MLP(2048, 1024, 512, 256) → 29 actions. **This is what gets replaced.**
- `obs_hist`: 930 dims = 10 frames × (joint_pos 29, joint_vel 29, base_ang_vel 3, projected_gravity 3, prev actions 29). The layout is term-major (`flatten_history_term_major` in `world_model/heads.py`). `code/attention_policy.split_obs_history` relies on this layout.

Hook points. We rebind the module-level name `Policy`, so no upstream file is edited:

| Upstream module | Where `Policy` is constructed | Rebound by |
|---|---|---|
| `supermimic.training.loop` | `Trainer.__init__`: `self.policy = Policy(cfg.policy)` | `train_entry.install_upstream_policy` |
| `supermimic.eval.benchmark` | `load_policy_from_checkpoint` | `eval_entry.run_upstream` |

The replacement class is a subclass of the upstream `Policy`. Its `decoder` is our module (`make_upstream_policy_class`), so the checkpoint layout (`policy` state_dict) and the forward signature stay the same. The arm and decoder config are written to `logs/<run>/junior_policy.json` so eval can rebuild the same decoder.

### Seam checks still open (must be verified on the first Colab GPU run)

- **S1 joint order.** The attention arm's morphology rows come from the compiled MuJoCo model's hinge-joint order (`morphology_from_mjmodel`). The policy obs/action order comes from the mjlab robot entity. Assert they match, e.g. compare `env.scene["robot"].joint_names` with the model hinge order. If they do not, a permutation bug would make B0 unfair to the attention arm.
- **S2 obs layout.** Confirm `obs["policy"]` in the upstream loop is the 930-d term-major history above. The CPU tests confirm this only against our own reading of upstream code.
- **S3 compile.** The smoke config sets `--policy-trainer.compile None`. Check whether `torch.compile` handles `nn.MultiheadAttention` with key-padding masks before using it in timing comparisons, and use the same compile setting for both arms.

## Data and licensing

- LAFAN1 retargets for the upstream 29-DoF humanoid asset are on the Hugging Face dataset `lvhaidong/LAFAN1_Retargeting_Dataset`, subdirectory named in `configs/colab_smoke.yaml` (`upstream.dataset_subdir`). The retarget code is BSD-3. The **underlying LAFAN1 motion is CC BY-NC-ND 4.0**.
- Policy: download at Colab runtime into `/content/...` only. **Never commit CSV/npz motion files, converted libraries, or checkpoints trained on them into this program tree.** `.gitignore` covers `data/` and `logs/` in the upstream repo.
- The large BONES-SEED path (6.7 GB compact library) is out of scope for Colab smoke.

## Second body for B1 (owner-provided, in tree)

Since 2026-10-25 14:11 EDT, `assets/home_humanoid_mjcf/` holds an owner-provided home-humanoid MJCF with STL meshes, about 70 MB. Its provenance is in `sources.json`. Do not delete or re-export these files without an owner decision.

CPU check, 2026-10-25 14:17 EDT, mujoco 3.17 CPU wheel: the model loads with 22 hinge joints (2 head, 2×4 arm, 2×6 leg) and 28 bodies. `morphology_from_mjmodel` returns 22 distinct finite descriptor rows. The 29-joint attention decoder accepts the 22-joint morphology and history and returns 22 actions (`test_b1_second_body_from_owner_mjcf`).

B1 prerequisites. None of these are met yet:
- the MJCF defines **no actuators** (`nu = 0`), so an mjlab actuator config is needed
- no motion retargets exist for this body
- the upstream world model and critic are sized to the 29-DoF state (71-d), so this body needs its own WM/critic, or a shared one
- the joint naming differs (`l_`/`r_`, `thigh`, `calf`, `upper_arm`). The descriptor code handles it
