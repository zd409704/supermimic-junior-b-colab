# Home-humanoid MuJoCo assets (cross-embodiment)

Owner-provided MuJoCo XML + STL meshes for the second body used in cross-embodiment / B1 work.

## Layout

- `pi_plus.xml` — MuJoCo model (meshdir=`meshes`)
- `meshes/` — 27 STL link meshes
- `mesh_manifest.json`, `pi_plus.json`, `sources.json`, `prepare_robot.py.reference.txt` — provenance / config notes from the export pack

## Path

`/srv/claude/research/supermimic-junior-b-colab/assets/home_humanoid_mjcf/`

## Notes for Claude Code

- Prefer calling this body "home humanoid" in docs, briefs, and prompts; do not expand commercial product branding in prose.
- Filenames under this folder are kept as exported so mesh relative paths keep working.
- Wire Colab / mjlab loaders to this XML path when cross-embodiment needs a second morphology.
- Do not delete or re-export meshes without an owner decision.
