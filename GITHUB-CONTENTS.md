# GitHub archive contents (lean tree)

Owner STOP + upload decision: 2026-10-28 (Asia/Shanghai).
This private repository is a **lean** archive of the SuperMimic junior-B colab research program after development stop. It is not a runnable training dump.

## Included

- Source and configs: `code/`, `configs/`, `notebooks/`, `spikes/`, `assets/` (home-humanoid MJCF + meshes)
- Packet scripts/docs (not bulky payloads): `packets/`
- Upstream pin vendored as plain files (no nested `.git`): `packets/P4/upstream-ro/SuperMimic-Reproduced/` (public upstream reference clone; see that tree README)
- Briefs, docs, method notes, prompts, top-level markdown (`README.md`, `progress.md`, `program-ledger.md`, `roster.md`)
- Orchestration history kept for audit: `orch/reports/`, `orch/jobs/`, `orch/owner-decisions/`, `orch/STATUS.md`, related orch markdown/JSON (not venue log dumps)

## Omitted (by design)

| Omitted | Why |
|---|---|
| `logs/` (~25G) | Venue training / eval dumps; too large for a lean archive |
| Prior compare-video DEPOSITED artifacts | Lived under omitted `logs/` (and related tgz/mp4); not re-uploaded |
| `data/` | Datasets / local data trees |
| `.venv/`, `**/cpuenv/.venv/`, `**/cpuenv/` | Local Python environments |
| `*.npz`, `*.pt`, `*.pth`, `*.ckpt`, `*.safetensors`, `*.bin` | Model weights / checkpoints |
| `*.tgz`, `*.tar`, `*.tar.gz`, `*.mp4`, `*.avi` | Bulky packet archives and rendered media |
| `__pycache__/`, caches, `dist/`, `build/`, `*.egg-info/` | Build/cache noise |

## Standing notes

- Development STOP: no new packets, no retrain, no scoring reopen, no compare-video redo from this archive alone.
- Scoring HOLD / M1 CLOSEOUT / arms CLOSE stand as recorded in `orch/`.
- Wording in new archive docs uses home-humanoid / plant-class labels (no commercial robot/product/company brands in files added for this upload).
