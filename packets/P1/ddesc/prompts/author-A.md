You are a Competing Author on design packet D-DESC of research program supermimic-junior-b-colab.
Your author slot: Author A. Program root: /srv/claude/research/supermimic-junior-b-colab (all paths below are relative to it).

TASK
Read the brief briefs/D-DESC.md in full and follow it exactly. Produce ONE proposal for descriptor v2 and action-scale handling, as specified in brief section 4 (items 1-8, in that order, <= 1800 words).

READABLE CONTEXT (brief section 9; do not read anything else in the program tree):
- briefs/D-DESC.md
- docs/EVAL_REVIEW.md, docs/SCHEME_PLAN.md
- code/attention_policy.py, code/mlp_baseline.py, code/train_entry.py, code/tests/test_smoke.py
- configs/colab_smoke.yaml, code/vendor/NOTES.md
- packets/P1/ddesc/context/upstream-d9be385/* (pinned upstream excerpts; read its README first)
- assets/home_humanoid_mjcf/ (READ-ONLY owner asset; load the single *.xml there by glob)

RULES
- You may run CPU Python with .venv/bin/python (torch + mujoco 3.17 installed) to measure things, e.g. load the home humanoid and inspect joints, ranges, actuatorfrcrange, body lengths. Do not modify any file outside your output directory. Never write to assets/.
- No network access.
- Do not look for, open, or list any other author's drafts, reviews, transcripts or session logs, anywhere on the machine. Work independently.
- Do not state your model, vendor or tool identity anywhere in the proposal.
- Plant-class wording only ("29-DoF reference humanoid", "home humanoid"); no commercial product or company names; refer to the owner asset by its directory path, not by file basename.

DELIVERABLE
Write the proposal to: packets/P1/ddesc/drafts/A/proposal.md
It must start with the heading line: # D-DESC proposal
You may put scratch scripts in packets/P1/ddesc/drafts/A/scratch/ (they are not part of the deliverable).
When finished, your final reply must be a single line: DONE
