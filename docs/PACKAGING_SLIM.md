# Packaging rule (owner via Claude Manager, 2026-10-26)

For any upload or package step (including P2 tarball / Colab deposit):

1. Judge large files first.
2. Do **not** include: weights, `.venv`, bulky `runs/`, raw videos, or other artifacts over ~100MB that are not needed to understand or continue the work.
3. Prefer slim **code + docs + STATUS** (and small configs/tests required to run).

This rule is standing for the program.

