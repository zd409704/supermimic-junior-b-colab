# Upstream reference excerpts (read-only context for D-DESC)

Fetched 2026-10-25 14:5x EDT by the Orchestrator (P1 wake) with `curl` from raw.githubusercontent.com:
- SuperMimic-style reproduction @ `d9be385b3eeb13a638fb33fb200d3bfd9be9839f` (MIT, `LICENSE`): files prefixed `src_supermimic_*`, path separators replaced by `_`.
- mjlab @ `8bb2bc9e187797689ec82c78c35019afd2fd0376` (Apache-2.0, `mjlab_LICENSE`): `mjlab_envs_mdp_actions_actions.py`, `mjlab_utils_actuator.py`, and the 29-DoF reference-humanoid constants file saved as `mjlab_ref29_constants.py`.

**Mechanical identifier redaction (naming policy, R18).** After download, every file was passed through one sed rule, applied identically:
`s/[Uu]nitree_g1/ref29_humanoid/g; s/UNITREE/BRAND/g; s/[Uu]nitree/BRAND/g; s/G1/REF29/g; s/g1/ref29/g; s/[Gg]o1/QUAD12/g; s/i2rt_yam/ARM6/g`.
So `REF29_ACTION_SCALE` in these copies is the upstream symbol for the 29-DoF reference humanoid's per-joint action scale. Nothing else was edited. These are reference copies, not vendored code; nothing under `code/` imports them.
