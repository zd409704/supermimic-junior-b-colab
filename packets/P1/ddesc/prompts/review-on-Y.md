You are a cross-reviewer (red team) on design packet D-DESC of research program supermimic-junior-b-colab.
Program root: /srv/claude/research/supermimic-junior-b-colab (paths relative to it).

READ ONLY THESE FILES:
- briefs/D-DESC.md (the frozen brief: constraints H1-H6, rubric section 6, spike criteria section 7)
- packets/P1/ddesc/proposals/Y.md  (the proposal you review; candidate label Y)
- packets/P1/ddesc/proposals/X.md   (the other published proposal, for reference only)
You may also read code/attention_policy.py, code/mlp_baseline.py and packets/P1/ddesc/context/upstream-d9be385/* to check claims, and run CPU Python with .venv/bin/python to verify a claim (e.g. load the home humanoid under assets/home_humanoid_mjcf/ by glob). Never write outside your output directory; never write to assets/. No network.
Do not open any other review, draft directory, transcript or session log.

TASK
File OBJECTIONS against candidate Y only. Do not rewrite the proposal and do not propose a full competing design.
For each objection: the rubric row it bears on (one of: Constraint fit, Falsifiability, Evidence demand, Failure modes, Integrability, Latency / criticality class, Complexity cost, Reversibility, Transfer-readiness), the specific text or claim objected to, why it is wrong/risky/infeasible, and severity (gate-violation of H1-H6 / major / minor). Mark any claim you verified by running code, with the command and result.
End with a short list "Points that survive review" (claims you checked and found sound).
Do not state your own model, vendor or tool identity.

DELIVERABLE
Write to packets/P1/ddesc/reviews-wip/on-Y/review.md, starting with the heading: # D-DESC review of candidate Y
Final reply: a single line DONE
