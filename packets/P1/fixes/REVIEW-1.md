# P1 fixes review

**O-1 — DDESC-ADOPT — blocker-for-freeze**  
**Location:** `code/eval_entry.py:77–81`; `code/train_entry.py:476–484`.

Every upstream training arm records the v2 descriptor and its hash because training supplies `probe_cls`. Evaluation supplies no probe and rebuilds the descriptor only for attention. Consequently, both MLP arms have a recorded hash but `got=None`, so their evaluation always raises before running the benchmark. This blocks the required attention-versus-matched-MLP comparison.

Read-only reproduction, mocking upstream imports, CUDA availability, and sidecar reads while retaining the production installation and evaluation functions:

```bash
PYTHONPATH=code PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B - <<'PY'
import json, sys, types
from pathlib import Path
from unittest.mock import patch
import train_entry as t, eval_entry as e
cfg = t.load_config('configs/colab_smoke.yaml')
mods = {n: types.ModuleType(n) for n in
        ('supermimic', 'supermimic.eval', 'supermimic.eval.benchmark')}
meta = {'policy': 'mlp_matched', 'descriptor': {'sha256': 'trained-hash'}}
with patch.dict(sys.modules, mods), patch.object(t, 'make_upstream_policy_class', return_value=object), patch.object(e.torch.cuda, 'is_available', return_value=True), patch.object(Path, 'exists', return_value=True), patch.object(Path, 'read_text', return_value=json.dumps(meta)), patch.object(Path, 'mkdir', side_effect=AssertionError('unexpected write')):
    try:
        e.run_upstream(Path('/virtual/run/ckpt_latest.pt'), cfg, None)
    except RuntimeError as ex:
        print(ex)
PY
```

Output:

```text
[eval_entry] descriptor sha256 mismatch: sidecar trained-hash vs rebuilt None
```

**O-2 — FX-5 — major**  
**Location:** `code/train_entry.py:272–283`, `code/train_entry.py:423–429`.

S1 reports `joint_order_match=true` when the action order is unavailable. That does not establish the requested descriptor/entity/action agreement. The detail message admits that action order is unchecked, but the machine-readable boolean and sidecar still claim success. With selectable descriptor v1, S5 is skipped, so no subsequent action-scale check catches the missing action information.

Evidence from the read-only CPU harness:

```python
print('S1 missing action:',
      joint_order_match(['a', 'b'], ['a', 'b'], None))
```

Executed with `PYTHONPATH=code PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -`, importing `joint_order_match` from `train_entry`. Output:

```text
S1 missing action: (True, "compared=['descriptor', 'entity'] (action order not exposed; unchecked)")
```

**O-3 — FX-5 — major**  
**Location:** `code/train_entry.py:286–299`, `code/train_entry.py:377–383`.

S2 infers observation layout from dimensions alone. Joint position, joint velocity, and actions have identical dimensions; angular velocity and gravity also have identical dimensions. Swapping these terms therefore still produces `term_major_ok=true`, despite feeding the decoder incorrect semantics. The per-frame branch additionally asserts that history was flattened correctly without inspecting the flattening. This can falsely satisfy P2’s S2 acceptance requirement.

Read-only reproduction:

```bash
PYTHONPATH=code PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B - <<'PY'
from types import SimpleNamespace as NS
import torch
from train_entry import SeamProbe, policy_term_dims, obs_layout_check
wrong_order = ['actions', 'joint_vel', 'base_ang_vel',
               'projected_gravity', 'joint_pos']
env = NS(observation_manager=NS(
    group_obs_term_dim={'policy': [(290,), (290,), (30,), (30,), (290,)]},
    active_terms={'policy': wrong_order}))
probe = SeamProbe({}, 'None')
probe.term_dims = policy_term_dims(env)
print('Actual term order:', env.observation_manager.active_terms['policy'])
probe.on_first_decoder_call(torch.zeros(1, 930))
print('Per-frame terms, unknown flattening:',
      obs_layout_check(930, [29, 29, 3, 3, 29], 29, 10))
PY
```

Output:

```text
Actual term order: ['actions', 'joint_vel', 'base_ang_vel', 'projected_gravity', 'joint_pos']
[seam] S2 obs_policy_dim=930 term_major_ok=true
[seam] S2 detail terms carry the history (term-major)
Per-frame terms, unknown flattening: (True, 'per-frame terms in term-major order; history flattened by upstream')
```

Verdict: BLOCK

Blockers:

- **O-1:** The new descriptor hash check prevents evaluation of the required matched-MLP arm.