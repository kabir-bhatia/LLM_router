r"""Builds notebooks/phase6_router_kaggle.ipynb and the Kaggle dataset bundle (eval/results/phase6/phase6_bundle.zip).

Run from the repo root: python -X utf8 notebooks/make_phase6_notebook.py
Bundle = router/ source + router/artifacts, eval/graders (no tests), eval/model_prices.json, the two policy files and
eval/results/phase6/test_prompts.json (ids and prompts only). No gold answers, no tasks_8cat.json, no .env.
Both files are copied to C:\Users\Kabir\Downloads when that folder exists.
"""
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P6 = ROOT / "eval" / "results" / "phase6"
BUNDLE = P6 / "phase6_bundle.zip"
NB = ROOT / "notebooks" / "phase6_router_kaggle.ipynb"

files = [ROOT / "eval/__init__.py", ROOT / "eval/model_prices.json",
         ROOT / "eval/results/phase4/routing_policy.json", ROOT / "eval/results/phase4/routing_policy_gpu_server.json",
         P6 / "test_prompts.json"]
files += [p for p in (ROOT / "router").rglob("*") if p.is_file() and "__pycache__" not in p.parts and "tests" not in p.parts
          and p.suffix in (".py", ".npz")]
files += [p for p in (ROOT / "eval/graders").glob("*.py") if not p.name.startswith("test_")]
with zipfile.ZipFile(BUNDLE, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(files):
        z.write(f, "LLM_Router/" + f.relative_to(ROOT).as_posix())
print("bundle", BUNDLE, len(files), "files")

DRIVER = (ROOT / "notebooks/phase6_driver.py").read_text(encoding="utf-8")

SETUP = r'''import glob, os, shutil, subprocess, zipfile
from pathlib import Path
dst = Path("/kaggle/working/LLM_Router")
if not (dst / "router/__init__.py").exists():
    hits = glob.glob("/kaggle/input/**/router/__init__.py", recursive=True)
    if hits:
        src = Path(hits[0]).parents[1]
        shutil.copytree(src, dst)
    else:
        zips = glob.glob("/kaggle/input/**/*.zip", recursive=True)
        assert zips, "attach the phase6 bundle dataset (Add Input)"
        zipfile.ZipFile(zips[0]).extractall("/kaggle/working")
assert (dst / "eval/results/phase6/test_prompts.json").exists() and (dst / "router/artifacts/task_type_lr.npz").exists()
subprocess.run("pip install -q httpx sentence-transformers scikit-learn numpy", shell=True, check=True)
print("repo ready:", sorted(p.name for p in dst.iterdir()))'''

CHECK = r'''import json
t = json.load(open("/kaggle/working/LLM_Router/eval/results/phase6/test_prompts.json", encoding="utf-8"))
print(len(t), "prompts; fields:", {k for x in t for k in x})
assert len(t) == 160 and {k for x in t for k in x} == {"id", "prompt"}
for p in glob.glob("/kaggle/working/LLM_Router/**/*", recursive=True):
    assert not p.endswith((".env", "tasks_8cat.json")), p'''

SECRETS = r'''import os
from kaggle_secrets import UserSecretsClient
sec = UserSecretsClient()
for k in ("FIREWORKS_API_KEY", "HYDE_API_KEY", "HYDE_BASE_URL"):
    os.environ[k] = sec.get_secret(k).strip()
print({k: bool(os.environ.get(k)) for k in ("FIREWORKS_API_KEY", "HYDE_API_KEY", "HYDE_BASE_URL")})  # True/False only, values never printed'''

cells = [
 ("markdown", "# Phase 6: router on the 160 held-out test tasks\n\n"
  "**Settings:** Accelerator = **GPU T4 x2**, Internet = **On**, Persistence = **Files only**. Add the dataset `phase6-bundle` "
  "(Add Input) and Kaggle Secrets `FIREWORKS_API_KEY`, `HYDE_API_KEY`, `HYDE_BASE_URL`.\n\n"
  "Runs, in order: (a) main policy on GPU x3, (b) CPU-deployment check (CPU only, 2 threads, 30 s budget), "
  "(c) GPU-server-policy run. Each run has its own folder under `phase6_out/` (results.json, log.jsonl, run.log). "
  "Restart-safe: finished runs are skipped, partial runs resume. A Fireworks spend guard ($1.50, whole notebook) stops and saves. "
  "Only prompts and ids are here: no gold answers. Final file: **`/kaggle/working/phase6_results.zip`**, download it into `eval/results/phase6/`."),
 ("code", "%cd /kaggle/working\n!nvidia-smi --query-gpu=name,memory.total --format=csv || echo no GPU\n!nproc\n!df -h /kaggle/working /kaggle/temp | cat"),
 ("markdown", "## 1. Repo from the attached dataset + Python packages"),
 ("code", SETUP),
 ("code", CHECK),
 ("markdown", "## 2. Keys from Kaggle Secrets (not printed)"),
 ("code", SECRETS),
 ("markdown", "## 3. Driver"),
 ("code", "%%writefile /kaggle/working/phase6_driver.py\n" + DRIVER),
 ("markdown", "## 4. Run everything (restart-safe; roughly 2-3 h, mostly unattended)\n"
  "Progress goes to `phase6_out/<run>/run.log` (`!tail -3 /kaggle/working/phase6_out/*/run.log` from another cell). "
  "A zip is refreshed after every run."),
 ("code", "!python -u /kaggle/working/phase6_driver.py"),
 ("markdown", "## 5. Check the zip"),
 ("code", "!ls -lh /kaggle/working/phase6_results.zip && cat /kaggle/working/phase6_out/status.json\n"
          "!grep -rIl -e 'fw_' -e 'sk-' /kaggle/working/phase6_out | head -3 || true"),
]


def mk(kind, src):
    lines = src.split("\n")
    lines = [l + "\n" for l in lines[:-1]] + [lines[-1]]
    c = {"cell_type": kind, "metadata": {}, "source": lines}
    if kind == "code":
        c.update(execution_count=None, outputs=[])
    return c


nb = {"cells": [mk(k, s) for k, s in cells],
      "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                   "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
NB.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print("wrote", NB)
dl = Path(r"C:\Users\Kabir\Downloads")
if dl.exists():
    for f in (NB, BUNDLE):
        shutil.copy(f, dl / f.name)
        print("  copied to", dl / f.name)
