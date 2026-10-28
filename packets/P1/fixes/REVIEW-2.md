# P1 fixes review 2

**O-1 — RESOLVED.** `code/eval_entry.py:81` gates descriptor hashes only for attention. Both MLP arms proceed with a recorded hash and no rebuilt descriptor; attention mismatches still raise.

Command (production installation/evaluation functions retained; upstream dependencies and filesystem operations mocked):

```bash
PYTHONPATH=code PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B - <<'PY'
import json, sys, types
from pathlib import Path
from unittest.mock import patch
import train_entry as t, eval_entry as e

cfg = t.load_config('configs/colab_smoke.yaml')
class PastCheck(Exception): pass

for arm, rebuilt in [
    ('mlp_matched', None), ('mlp_upstream', None),
    ('attention', 'trained-hash'), ('attention', 'other-hash'),
    ('attention', None),
]:
    mods = {n: types.ModuleType(n) for n in
            ('supermimic', 'supermimic.eval', 'supermimic.eval.benchmark')}
    mods['supermimic.eval.benchmark'].load_policy_from_checkpoint = lambda *a, **k: None
    meta = {'policy': arm, 'descriptor': {'sha256': 'trained-hash'}}
    def morphology(cfg, n, info):
        if rebuilt is not None:
            info['descriptor_meta'] = {'sha256': rebuilt}
        return None
    with patch.dict(sys.modules, mods), \
         patch.object(t, 'make_upstream_policy_class', return_value=object), \
         patch.object(t, 'load_morphology', side_effect=morphology), \
         patch.object(e.torch.cuda, 'is_available', return_value=True), \
         patch.object(Path, 'exists', return_value=True), \
         patch.object(Path, 'read_text', return_value=json.dumps(meta)), \
         patch.object(Path, 'mkdir', side_effect=PastCheck):
        try:
            e.run_upstream(Path('/virtual/run/ckpt_latest.pt'), cfg, None)
        except PastCheck:
            print(arm, rebuilt, '=> proceeded past hash check (stopped before mkdir)')
        except RuntimeError as ex:
            print(arm, rebuilt, '=>', ex)
PY
```

Output:

```text
mlp_matched None => proceeded past hash check (stopped before mkdir)
mlp_upstream None => proceeded past hash check (stopped before mkdir)
attention trained-hash => proceeded past hash check (stopped before mkdir)
attention other-hash => [eval_entry] descriptor sha256 mismatch: sidecar trained-hash vs rebuilt other-hash
attention None => [eval_entry] descriptor sha256 mismatch: sidecar trained-hash vs rebuilt None
```

**O-2 — RESOLVED.** Missing action order now produces `"unverified"`, records that value, and raises before S5—even with descriptor v1. Only agreement among all three sequences passes (`code/train_entry.py:276–291`, `454–459`). The shared seam dictionary is serialized by the existing `run_upstream` `finally` block.

Command:

```bash
PYTHONPATH=code PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B - <<'PY'
from types import SimpleNamespace as NS
from train_entry import joint_order_match, SeamProbe
names = ['a', 'b']
print('S1 missing action:', joint_order_match(names, names, None))
env = NS(scene={'robot': NS(joint_names=names)})
probe = SeamProbe({'joint_names': names, 'descriptor_version': 'v1'}, 'None')
try:
    probe.on_trainer_ready(NS(env=env))
except RuntimeError as ex:
    print('Raised:', ex)
print('Recorded:', probe.seam['S1_joint_order_match'])
print('All three agree:', joint_order_match(names, names, names))
print('Entity mismatch:', joint_order_match(names, names[::-1], None))
PY
```

Output:

```text
S1 missing action: ('unverified', "compared=['descriptor', 'entity'] (action order not exposed; S1 unverified)")
[seam] S1 joint_order_match=unverified
[seam] S1 detail compared=['descriptor', 'entity'] (action order not exposed; S1 unverified)
Raised: [seam] S1 joint order unverified (descriptor rows / robot entity / action order): compared=['descriptor', 'entity'] (action order not exposed; S1 unverified)
Recorded: unverified
All three agree: (True, "compared=['action', 'descriptor', 'entity']")
Entity mismatch: (False, "compared=['descriptor', 'entity'] mismatch=['entity']")
```

**O-3 — RESOLVED.** S2 checks exact observation names and order as well as history-carrying dimensions. Swapped equal-sized terms fail; missing names and uninspectable per-frame flattening produce `"unverified"` and raise (`code/train_entry.py:298–319`, `468–475`). The required names match the supplied upstream `policy_terms` definition.

Command:

```bash
PYTHONPATH=code PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B - <<'PY'
from types import SimpleNamespace as NS
import torch
from train_entry import SeamProbe, policy_term_dims, policy_term_names, EXPECTED_POLICY_TERMS

wrong = ['actions', 'joint_vel', 'base_ang_vel', 'projected_gravity', 'joint_pos']
for label, names, dims in [
    ('swapped', wrong, [290, 290, 30, 30, 290]),
    ('per-frame', EXPECTED_POLICY_TERMS, [29, 29, 3, 3, 29]),
    ('missing names', None, [290, 290, 30, 30, 290]),
    ('correct', EXPECTED_POLICY_TERMS, [290, 290, 30, 30, 290]),
]:
    env = NS(observation_manager=NS(
        group_obs_term_dim={'policy': [(d,) for d in dims]},
        active_terms={'policy': names}))
    probe = SeamProbe({}, 'None', emit=lambda _: None)
    probe.term_dims, probe.term_names = policy_term_dims(env), policy_term_names(env)
    try:
        probe.on_first_decoder_call(torch.zeros(1, 930))
        result = 'returned'
    except RuntimeError:
        result = 'raised'
    print(f'{label}: term_major_ok={probe.seam["S2_term_major_ok"]!r}; '
          f'{result}; {probe.seam["S2_detail"]}')
PY
```

Output:

```text
swapped: term_major_ok=False; raised; term names ['actions', 'joint_vel', 'base_ang_vel', 'projected_gravity', 'joint_pos'] != expected order ['joint_pos', 'joint_vel', 'base_ang_vel', 'projected_gravity', 'actions']
per-frame: term_major_ok='unverified'; raised; per-frame term dims; history flattening cannot be inspected
missing names: term_major_ok='unverified'; raised; policy observation term names not exposed by env; order unverified
correct: term_major_ok=True; returned; names in upstream order; terms carry the history (term-major)
```

Regression command:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B code/tests/test_smoke.py
```

Output, exit status 0:

```text
PASS test_shapes_and_distinct_morphology
PASS test_permutation_equivariance
PASS test_mask_and_grad
PASS test_param_match_within_5pct
PASS test_b1_second_body_from_owner_mjcf
PASS test_fx1_default_pose_and_fx2_depth_norm
PASS test_fx1_unimportable_loader_fails_loudly
PASS test_fx1_resolve_init_joint_pos
PASS test_fx5_seam_helpers_with_fake_objects
PASS test_o1_eval_descriptor_hash_only_gates_attention
PASS test_v2_upstream_actuator_params_and_failures
PASS test_v2_s5_action_scale_match
PASS test_v2_matches_spike_module
PASS test_upstream_seam_with_fake_package
```

**New objections:** None identified in the round-2 diff. Validation was read-only CPU testing with mocked upstream objects; the live GPU integration was not exercised.

Verdict: FREEZE-OK