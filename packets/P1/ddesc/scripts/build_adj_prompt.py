"""Mechanically assemble an adjudicator prompt instance from the sealed template (no model in the loop)."""
import sys, pathlib
root = pathlib.Path('/srv/claude/research/supermimic-junior-b-colab'); d = root/'packets/P1/ddesc'
order, pas, out = sys.argv[1], sys.argv[2], sys.argv[3]   # order "X,Y" or "Y,X"
t = (d/'prompts/adjudicator-template.md').read_text()
blocks = []
for lab in order.split(','):
    blocks.append(f"===== CANDIDATE {lab} (packets/P1/ddesc/proposals/{lab}.md) =====\n" + (d/f'proposals/{lab}.md').read_text())
for lab in order.split(','):
    blocks.append(f"===== REVIEW OF CANDIDATE {lab} (packets/P1/ddesc/reviews/on-{lab}.md) =====\n" + (d/f'reviews/on-{lab}.md').read_text())
s = t.replace('{{ORDER}}', ' then '.join(order.split(','))).replace('{{PASS}}', pas)
s = s.replace('{{BRIEF}}', (root/'briefs/D-DESC.md').read_text()).replace('{{CANDIDATES_AND_REVIEWS}}', '\n\n'.join(blocks))
pathlib.Path(out).write_text(s)
