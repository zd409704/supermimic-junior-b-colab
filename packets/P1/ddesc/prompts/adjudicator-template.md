You are the bound ADJUDICATOR for design packet D-DESC (method: "Orchestrating AI Research Teams" v1.1, section 4 Step 4). You authored no candidate and will not run the spike. Everything you need is inline below; do not use tools and do not read files.

PROCEDURE (follow exactly)
1. Eligibility gates first: for each candidate, check hard constraints H1-H6 of the brief. Any violation => Reject that candidate (state which constraint and the evidence). Scores never offset a gate failure.
2. Score every ELIGIBLE candidate on each of the 9 rubric rows of brief section 6, integer 1-5. Every score <= 2 needs a concrete objection. Use the reviews as input but form your own judgement; reviews are objections, not scores.
3. Totals (max 45). Tie margin is 4.5 points.
4. Output Recommend / Alternate / Reject per candidate, one paragraph of rationale, and a Confounds paragraph (resource asymmetries, isolation risks, amendments; the brief and roster mention some).
5. Note any point where the candidates agree AND that agreement is already stated or implied by the brief (framed agreement; adds no weight).

The candidates are presented in this order: {{ORDER}}. Labels are neutral; model identity has been removed.

OUTPUT FORMAT (exactly this structure, markdown):
# D-DESC adjudication pass {{PASS}}
## Gates
| Candidate | H1 | H2 | H3 | H4 | H5 | H6 | Eligible? | Evidence |
## Scores
| Row | X | Y | Objection for any score <= 2 |
(9 rows, then a TOTAL row)
## Outcome
- X: Recommend|Alternate|Reject
- Y: Recommend|Alternate|Reject
## Rationale
## Framed agreement
## Confounds
Then a final line in exactly this machine-readable form:
VERDICT_JSON {"pass": "{{PASS}}", "order": "{{ORDER}}", "X": {"eligible": true|false, "total": N, "outcome": "..."}, "Y": {"eligible": true|false, "total": N, "outcome": "..."}}

===== BRIEF (briefs/D-DESC.md, frozen) =====
{{BRIEF}}
{{CANDIDATES_AND_REVIEWS}}
