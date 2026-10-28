# DIAG — P4 B0 attempt1 relaunch #2 motion-data fetch (2026-10-26)

## Deposit (sealed before open)
- `logs/xn4090/2026-10-26/b0-20261026-0645.tgz` sha256 `8b5ee889edd98e99802df03863c8c2a51bad6f088b79f689b266b747d6e1e1eb`
- Seal: `DEPOSIT xn4090` @ `2026-10-26T06:48:06Z` in `logs/seal.log`
- Kind: setup-only BLOCKED; no trainer; `BLOCKED.md` = `setup_failed detail=motion data download`
- Run log: `logs/xn4090/2026-10-26/run-20261026T063117Z.log`

## Failure mechanism
1. `uv sync` succeeded (~156 pkgs; PyPI + `files.pythonhosted.org` reachable; mjlab git pin resolved during that window).
2. Driver (`packets/P4/b0_driver.sh` setup) calls `huggingface_hub.snapshot_download` for dataset `lvhaidong/LAFAN1_Retargeting_Dataset`, `allow_patterns` = `g1/{walk1_subject1,run1_subject2,dance1_subject1,jumps1_subject1}.csv` (FX-3 verified; ~8.97 MiB total, not LFS).
3. Hub call failed: `httpx.ConnectError: [Errno 101] Network is unreachable` → `LocalEntryNotFoundError` → driver `BLOCKED setup_failed: motion data download`.
4. Live probe on `xn-4090-gpu2` (via Mac mini JumpServer, 2026-10-26T06:49Z):
   - `https://huggingface.co` IPv4+IPv6: connect timeout / unreachable
   - DNS A = `122.248.226.57` (does not answer :443); AAAA = Meta-looking `2a03:2880:…` with no usable IPv6 default route beyond link-local
   - `https://pypi.org` / `files.pythonhosted.org`: OK
   - `https://github.com`: timeout at probe time (prior job still fetched mjlab once)
   - **No** existing `data/raw/lafan1/g1` under job workdir; unrelated local `lafan1` trees under home-humanoid paths are not this HF g1 CSV set

## PLAN constraints (do not violate)
- Motion: runtime-only; never copied back (X-002). Deposit REFUSE if motion files staged.
- BLK-11 ACCEPT: private runtime-only retargets OK for this program.
- Do not put the 4 CSVs into the sealed CR-B0-1 code tarball or into deposits.

## Ranked fixes (smallest first)

### 1. RECOMMENDED — `HF_ENDPOINT` mirror on venue (effort: ~15–30 min)
- Fact: `https://hf-mirror.com` returns HTTP 200 from the GPU host; `huggingface_hub` with `HF_ENDPOINT=https://hf-mirror.com` successfully downloaded `g1/walk1_subject1.csv` (size 2670866, matches Hub listing).
- Change: export `HF_ENDPOINT=https://hf-mirror.com` in `orch/jobs/p4-b0-attempt1/run.sh` (and job JSON `env`) before `b0_driver.sh`; no CR-B0-1 tarball rebuild; X-002 intact (download still on runtime, nothing in deposit).
- Optional hardening: if the 4 CSVs already exist under `data/raw/lafan1/g1/`, skip `snapshot_download` (still convert to npz on runtime).

### 2. Offline pre-seed via Mac mini rsync (effort: ~45–90 min)
- Download 4 CSVs on box or Mac mini (Hub reachable there), rsync into remote `/content/SuperMimic-Reproduced/data/raw/lafan1/g1/` before driver setup; same skip-if-present patch.
- Use if mirror policy is unacceptable. Still keep motion out of deposits.

### 3. Vendor motion into a separate job upload artifact (effort: half-day + governance)
- Add a sealed motion sidecar to job `upload[]` (not the code tarball). Needs PLAN note / Class-2 clarity vs “downloaded only on the runtime”. Larger than (1)/(2).

### 4. Open `huggingface.co` egress (owner/infra only)
- Current path is hard-blocked (DNS/firewall). Not actionable by relay without owner network change.

## READY-to-relaunch checklist (after Manager confirms path)
- [ ] Manager picks fix #1 (or #2); no Colab; Drive stays paused
- [ ] Apply env/run.sh (and optional skip-if-present) change; reseal run.sh sha in job JSON `upload`
- [ ] Job JSON + STATUS `## Jobs` both `READY`; mutex `gpu0` free; remote tmux absent; GPU0 idle
- [ ] Smoke: one-clip or full `snapshot_download` with chosen endpoint on venue before full B0
- [ ] Explicit Manager START; then RUNNING → deposit → seal-before-open → wake

## Not done
- No relaunch. No trainer start. No Colab. No venue change.
