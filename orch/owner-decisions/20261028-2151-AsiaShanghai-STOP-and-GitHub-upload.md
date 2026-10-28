# Owner decision — 2026-10-28 ~21:51 Asia/Shanghai — SuperMimic STOP development + GitHub upload

**Decision:** STOP all further SuperMimic program development (no new packets, no retrain, no scoring reopen, no compare-video redo, Drive stays PAUSED). Claude 4 uploads the program tree to GitHub under the authenticated account `DavidZhang-HT`, then HOLDs idle.

**AuthorizedBy:** owner chat — upload SuperMimic to GitHub; do not continue development; corresponding Claude conversation performs the upload.

**Program:** `/srv/claude/research/supermimic-junior-b-colab/`
**Lead:** Claude 4

## Claude 4 tasks
1. **STOP / HOLD development.** Do not start packets, jobs, xn-4090 runs, or Drive cycles.
2. **Prepare a publishable tree** for GitHub:
   - Init git in the program root if absent (currently NO_GIT).
   - Expand `.gitignore` so the push stays lean: exclude `.venv/`, `__pycache__/`, `*.pyc`, `data/`, large weights (`*.npz`, `*.pt`, `*.ckpt`, `*.safetensors`), and **`logs/`** (about 25G of venue dumps — keep only small sealed JSON/md summaries that already live under `orch/reports/` or copy tiny status files if needed; do not push xn-4090 tgz dumps).
   - Prefer source of truth: `code/`, `configs/`, `packets/` (scripts/configs; skip giant binary dumps inside packets if any), `docs/`, `briefs/`, `method/`, `method-issues/`, `notebooks/`, `orch/` (STATUS, jobs JSON, owner-decisions, reports, prompts — not `orch/logs` bulky dumps), `spikes/`, `prompts/`, top-level `README.md`, `progress.md`, `program-ledger.md`, `roster.md`.
   - Keep assets that are small and needed to understand the work; do not force-upload multi-GB media. Optional: a short `GITHUB-CONTENTS.md` listing what was omitted and why.
3. **Create and push** a **private** repository on GitHub as `DavidZhang-HT/<sensible-name>` (suggest `supermimic-junior-b-colab` unless that name collides). Use `gh` already authenticated as `DavidZhang-HT` on this box. Do **not** use the accidental DELETE-ME probe repos. Do **not** invent a different org/owner.
4. **Sanity:** no secrets/tokens in the commit; no commercial robot/product/company brand names in new files you write for the upload (home-humanoid / plant-class wording). Upstream citation in `program-ledger.md` may stay as historical fact.
5. **Report to Manager (MATERIAL):** repo HTTPS URL, default branch, HEAD sha256 of the pushed tip (or `git rev-parse HEAD`), approximate pushed size, and path of any contents note. Then idle HOLD.

## Out of scope
- Further research packets / Route reopen / Phase work
- Colab / xn-4090 training or render jobs
- Publishing the repo as public unless owner later asks

