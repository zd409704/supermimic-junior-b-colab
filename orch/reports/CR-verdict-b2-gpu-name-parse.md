# CR note: VERDICT-TOOL-B2 GPU-name parse (unique model / visible device)

- **Status:** filed, not applied. Provisional. The sealed `spikes/B2/verdict/verdict_b2.py` (`cd2ac741d2ffad7353c7cf62ca5f325a5402ec4d7e6a6c6f5887ecff511c994c`) and the reused `spikes/B0/verdict/verdict_b0.py` (`9caa744a65ef5206fd46f532c4d13529b7773d076ee725ee4cb98ec192774a3b`) are **not** modified in this packet.
- **Trigger:** P5 B2 attempt 1 machine verdict BLOCKED on `gpu_mismatch` and B2-V-2(c) (results `c184bb889d0f101eb24eed66a76b278807ebb5101011a64c47118a1a2df5b29a`). Waived as a harness defect by owner decision `9985fc8fcd3a391b9577895a3bedf0c3643970b6ec701b7d96c4082ed0a3ef86`, item 2.
- **Amendment class for the fix:** Class 0 (tooling) for future packets. A fix applied to an already-scored packet would change a verdict input, so it must not be backported to P5 results. P5 is covered by the Class-2 waiver.

## Defect

1. `verdict_b0.py:1427` `parse_gpu_name(text)` collects the Name column from **every** GPU row of `meta/nvidia-smi.txt` and returns `" + ".join(names)`.
2. `verdict_b2.py:720-723` compares that joined string to the single literal `GPU_NAME = "NVIDIA GeForce RTX 4090"` (`all(g == GPU_NAME ...)`). The same `gpu_ok` feeds B2-V-2(c) at lines 813/815.
3. On XN-4090-GPU2 the bundle captured the full host table: 8 rows, each `NVIDIA GeForce RTX 4090`. The job pinned `CUDA_VISIBLE_DEVICES=0` (job JSON `remote.cuda_visible_devices`, `gpu_uuid GPU-fb0522c7-d42b-41f1-f24b-4729e2c2174c`). One model was present and one device was used, but the joined string is 8 names long and fails the equality check.
4. P4 did not block on the same table because `verdict_b0.py:1030` only requires `len(set(gpu_names)) == 1` across deposits. It does not compare against a literal.
5. Test gap: `test_verdict_b2.py::test_gpu_not_4090` uses a single-row fixture (`make_fixture_b2.nvsmi`). No fixture has a multi-row host table.

## Proposed fix (next tool version, own seal + tests)

- `parse_gpu_names(text) -> list[(index, name)]`. Keep the existing joined string only as a reported field.
- Resolve the device(s) the job used. Preferred order: (a) a captured `nvidia-smi -i $CUDA_VISIBLE_DEVICES --query-gpu=index,uuid,name --format=csv` line, which the driver should add to `meta/` (bundle contract change, Class 0); (b) else `CUDA_VISIBLE_DEVICES` from the bundle (session / job JSON) mapped to rows of the host table; (c) else the unique set of model names over all rows.
- Pass rule: the set of names for the used device(s) is exactly `{GPU_NAME}`. Mixed models among the used devices → `gpu_mismatch`. Mixed models elsewhere on the host but not used → reported, not blocking.
- Emit `gpu_names_unique`, `gpu_visible_devices` and `gpu_name_used` in results, and keep `gpu_name` = the used model, not the join.
- Tests: 8× identical 4090 table → pass; 8-row table with the visible device being an L4 → `gpu_mismatch`; mixed host where the visible device is a 4090 → pass, with the mix reported; missing `nvidia-smi.txt` → block as today.

## Not done here

No code change, no re-run of VERDICT-TOOL-B2, no GPU. A future packet adopts the fix through a sealed tool version, at a packet boundary.
