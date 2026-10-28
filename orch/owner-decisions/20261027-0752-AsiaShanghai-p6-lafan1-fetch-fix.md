# Manager decision — P6 B1-RT LAFAN1 clip-fetch fix (Provisional)

**Stamp:** 2026-10-27 ~07:52 Asia/Shanghai
**Authorized by:** Claude Manager (standing owner autonomy 2026-10-26: decide research drive without re-asking)
**Context:** `p6-b1-rt` DEPOSITED driver BLOCKED `data_step` — `fetch_clip` urllib with `HF_ENDPOINT=https://hf-mirror.com` returns HTTP 403 on xn-4090-gpu2. No RT-6/7/8. Class-2 C (RT-4 waive) unchanged. `p6-b1-arms` stays DRAFT.

## Root cause
`spikes/B1-RT/rt_cpu.py` `fetch_clip` uses raw `urllib.request.urlopen` against `${HF_ENDPOINT}/datasets/.../resolve/...`. On xn-4090 that path returns 403. P4 previously succeeded via `huggingface_hub.snapshot_download` + mirror; those four CSVs remain on the host at `/content/SuperMimic-Reproduced/data/raw/lafan1/g1/` and match box Hub downloads + CPU-pinned `csv_sha256` for slot_rule=first clips:

| clip | sha256 |
|---|---|
| walk1_subject1 | 68c7887438e94f1f3d9ebacd3a8ce59251a22c7b05129a0f5d7cacaedc48c28d |
| run1_subject2 | ec02af4447a62214a6fec6afff60c75d0ecc8f80f8fb45e3cd4119fed9ceac8d |
| dance1_subject1 | e2a369e92e5ad076c5acffff7bce53157a0e6cd9e7e9f6a08dadfb1eb2928d8f |
| jumps1_subject1 | 3f55c1a0f87564044a71817d62dc2a40aa76332aa1cab3f1c817333a197c78c2 |

## Decision — Fix path #2 (local cache / skip-if-present)
1. Patch `fetch_clip` to read from `LAFAN1_G1_DIR` (default candidates include `/content/SuperMimic-Reproduced/data/raw/lafan1/g1`) when `{name}.csv` exists; compute sha256 from bytes (must match pin when pin present). Fallback: `huggingface_hub.hf_hub_download` with `HF_ENDPOINT`; last resort urllib.
2. Relay `run.sh` / job env: `export LAFAN1_G1_DIR=/content/SuperMimic-Reproduced/data/raw/lafan1/g1`. Do not clean that tree. Before START, verify the four first-slot CSVs exist and match the table above.
3. X-002 intact: motion stays runtime-only; never stage CSVs into deposits or the code tarball.
4. After score orch seals SCORED BLOCKED for this deposit: apply patch, reseal packet/run.sh as needed, flip job READY, START on xn-4090 gpu0 (mutex free). No Colab. No P4/P5 reopen. Arms stay DRAFT until RT-6/7/8 PASS.

## Out of scope
- Opening huggingface.co egress on the GPU host
- Vendoring CSVs into sealed upload artifacts
