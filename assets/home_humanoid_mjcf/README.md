# Home-humanoid MuJoCo assets (cross-embodiment)

Owner-provided MuJoCo XML + STL meshes for the second body used in cross-embodiment / B1 work.

## Layout

- Primary `.xml` MuJoCo model in this folder (meshdir=`meshes`); export basename retained on disk so mesh relative paths keep working — refer by path/glob, do not expand commercial product branding in prose.
- `meshes/` — 27 STL link meshes
- `mesh_manifest.json`, companion `.json` config, `sources.json`, `prepare_robot.py.reference.txt` — provenance / config notes from the export pack (brand tokens scrubbed in Claude-visible text 2026-10-26)

## Path

`/srv/claude/research/supermimic-junior-b-colab/assets/home_humanoid_mjcf/`

## Notes for Claude Code

- Prefer calling this body "home humanoid" in docs, briefs, and prompts; do not expand commercial product branding in prose.
- Filenames under this folder are kept as exported so mesh relative paths keep working.
- Wire Colab / mjlab loaders to this XML path when cross-embodiment needs a second morphology.
- Do not delete or re-export meshes without an owner decision.
