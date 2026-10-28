"""CR-B2-1 (b): P5 train entry point (spikes/B2/PLAN.md §2.3 (b), §4.1).

Registers the ``mlp_mind`` arm in the frozen ``train_entry`` (``POLICY_ARMS`` + wrapped ``build_decoder``) and
then calls the frozen ``train_entry.main()`` unchanged. Same CLI as ``code/train_entry.py``::

    python /content/junior/packets/P5/p5_train_entry.py --mode upstream --policy mlp_mind \
        --config /content/junior/configs/b2_mtrain.yaml --seed 0
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[1] / "code"
for p in (str(CODE), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import mlp_mind  # noqa: E402

mlp_mind.register()

import train_entry  # noqa: E402

if __name__ == "__main__":
    train_entry.main()
