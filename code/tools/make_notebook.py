"""Generate notebooks/colab_smoke.ipynb (kept as a script so the notebook is reproducible)."""
import sys
import nbformat as nbf

nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
C = []
C.append(md("""# Junior-(B) attention decoder on a SuperMimic-style loop — Colab smoke

Program `supermimic-junior-b-colab` · Provisional · runbook: `docs/COLAB_RUNBOOK.md`.

Cells marked **[GPU]** require a Colab GPU runtime (L4 preferred, T4 fallback). Cells marked **[CPU ok]** also run without a GPU.
Nothing here has been verified on Colab yet — record driver/GPU and every deviation in your run log.

Motion data (LAFAN1, CC BY-NC-ND 4.0) is downloaded to this runtime only. Do **not** copy motion files or checkpoints back into the program tree."""))
C.append(md("## 1. Runtime check [CPU ok]"))
C.append(code("!nvidia-smi || echo 'NO GPU: only [CPU ok] cells will work'\n!python --version"))
C.append(md("## 2. Program code [CPU ok]\nUpload `junior_b_colab.tgz` (made on the research box, see runbook §2) when prompted, or place it at `/content/junior_b_colab.tgz`."))
C.append(code("""import os
if not os.path.exists('/content/junior/code/attention_policy.py'):
    if not os.path.exists('/content/junior_b_colab.tgz'):
        from google.colab import files
        files.upload()  # choose junior_b_colab.tgz
    !mkdir -p /content/junior && tar xzf /content/junior_b_colab.tgz -C /content/junior
!ls /content/junior/code"""))
C.append(md("## 3. Upstream reproduction at pin [CPU ok to install; runtime needs GPU]"))
C.append(code("""!pip install -q uv
UP = '/content/SuperMimic-Reproduced'
PIN = 'd9be385b3eeb13a638fb33fb200d3bfd9be9839f'
if not os.path.exists(UP):
    !git clone https://github.com/CuboiLeo/SuperMimic-Reproduced {UP}
!git -C {UP} checkout -q {PIN} && git -C {UP} log -1 --format='%H %cd'
!cd {UP} && uv sync 2>&1 | tail -3
!uv pip install -q --python {UP}/.venv/bin/python pyyaml
PY = f'{UP}/.venv/bin/python'"""))
C.append(code("""# R1 check: CUDA 13 wheels vs Colab driver. If False on a GPU runtime, see runbook §2 fallback.
!{PY} -c "import torch; print(torch.__version__, 'cuda', torch.cuda.is_available(), torch.version.cuda)"
!{PY} -c "import warp as wp; wp.init(); print('warp', wp.__version__)" """))
C.append(md("## 4. Import smoke [CPU ok]"))
C.append(code("""%cd /content/junior
!{PY} code/tests/test_smoke.py
!{PY} code/train_entry.py --policy attention
!{PY} code/eval_entry.py"""))
C.append(md("## 5. Motion subset (4 LAFAN1-style clips) [CPU ok]"))
C.append(code("""%cd {UP}
import yaml
cfg = yaml.safe_load(open('/content/junior/configs/colab_smoke.yaml'))['upstream']
from huggingface_hub import snapshot_download  # installed with upstream deps; else: pip install huggingface_hub
snapshot_download(cfg['dataset_repo'], repo_type='dataset', local_dir='data/raw/lafan1',
                  allow_patterns=[f"{cfg['dataset_subdir']}/{n}.csv" for n in cfg['clips']])
SUB = cfg['dataset_subdir']
!env -u PYTHONPATH {PY} scripts/data/csv_to_npz_batch.py --input-dir data/raw/lafan1/{SUB} --output-dir {cfg['npz_dir']} --input-fps 30 --workers 2
!ls {cfg['npz_dir']}"""))
C.append(md("## 6. Upstream sanity, unmodified decoder [GPU] (optional, ~6 min)"))
C.append(code("""RUN_SANITY = False
if RUN_SANITY:
    !cd {UP} && env -u PYTHONPATH {PY} -m supermimic.scripts.train --run-name up_sanity --data.npz-dir {cfg['npz_dir']} --env.num-envs 256 --policy-trainer.batch-size 256 --policy-trainer.horizon 16 --policy-trainer.compile None --schedule.max-hours 0.1"""))
C.append(md("## 7. B0 smoke train — attention vs matched MLP [GPU] (requires Colab GPU; ~0.5 h per arm)\nSet `RUN_TRAIN = True` deliberately. Check seams S1–S5 (`code/vendor/NOTES.md`, runbook §6) on the first run: grep the log for `[seam]`."))
C.append(code("""RUN_TRAIN = False
ARMS = ['attention', 'mlp_matched']
SEED = 0
if RUN_TRAIN:
    for arm in ARMS:
        !cd {UP} && env -u PYTHONPATH {PY} /content/junior/code/train_entry.py --mode upstream --policy {arm} --config /content/junior/configs/colab_smoke.yaml --seed {SEED} 2>&1 | tee logs/train_{arm}_s{SEED}.log | tail -20"""))
C.append(md("## 8. Eval + B2 mask [GPU] (requires Colab GPU)"))
C.append(code("""RUN_EVAL = False
if RUN_EVAL:
    for arm in ARMS:
        !cd {UP} && env -u PYTHONPATH {PY} /content/junior/code/eval_entry.py --mode upstream --config /content/junior/configs/colab_smoke.yaml --ckpt logs/b0_smoke_{arm}_s{SEED}/ckpt_latest.pt
    !ls {UP}/logs/eval"""))
C.append(md("## 9. Collect metrics (no data, no checkpoints)"))
C.append(code("""import glob, shutil, subprocess, time
stamp = time.strftime('%Y%m%d-%H%M')
out = f'/content/out_{stamp}'
os.makedirs(out, exist_ok=True)
for f in glob.glob(f'{UP}/logs/train_*.log'):
    shutil.copy(f, out)
if os.path.isdir(f'{UP}/logs/eval'):
    shutil.copytree(f'{UP}/logs/eval', f'{out}/eval', dirs_exist_ok=True)
for d in glob.glob(f'{UP}/logs/b0_smoke_*'):
    dst = f'{out}/{os.path.basename(d)}'
    os.makedirs(dst, exist_ok=True)
    if os.path.exists(f'{d}/junior_policy.json'):
        shutil.copy(f'{d}/junior_policy.json', dst)
    if os.path.isdir(f'{d}/tb'):
        shutil.copytree(f'{d}/tb', f'{dst}/tb', dirs_exist_ok=True)
subprocess.run(f'nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv > {out}/gpu.csv', shell=True)
shutil.make_archive(out, 'gztar', '/content', os.path.basename(out))
print('download', out + '.tar.gz', '-> program tree logs/colab/<date>/  (metrics only: no motion data, no checkpoints)')"""))
nb["cells"] = C
nb["metadata"] = {"accelerator": "GPU", "colab": {"provenance": []}, "kernelspec": {"name": "python3", "display_name": "Python 3"}}
nbf.write(nb, sys.argv[1])
