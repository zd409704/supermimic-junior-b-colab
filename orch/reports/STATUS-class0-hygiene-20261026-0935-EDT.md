# Class-0 hygiene — home_humanoid_mjcf assets

**Stamp:** 2026-10-26 09:35 EDT (America/Toronto)
**Decision cap:** Class-0 (hygiene only)
**Actor:** Claude rule (compliance spot-check)

## What changed

1. `assets/home_humanoid_mjcf/prepare_robot.py.reference.txt` — removed CJK description and gateway-forbidden brand tokens; reference script now uses home-humanoid wording. On-disk MJCF/STL export basenames unchanged.
2. `assets/home_humanoid_mjcf/sources.json` — anonymized upstream export basename and comparison-repo vendor segment to plant-class wording; commit and sha256 pins kept.
3. `assets/home_humanoid_mjcf/README.md` — stopped spelling export brand basenames in prose; retained "filenames kept as exported" rule.
4. `assets/home_humanoid_mjcf/` companion JSON config — anonymized `robot.name` and retarget output path; left `robot.xml` basename pointing at the on-disk export file so mesh relative paths keep working.

## Unchanged on purpose

- On-disk primary MJCF / companion JSON **filenames** (mesh relative paths); per prior owner/README rule.
- No PLAN / sealed packet body edits.

## Why

Claude-visible surface under this program still carried gateway-forbidden brand tokens and CJK in the reference script (same family as the 2026-10-25 gateway brand block on this program).
