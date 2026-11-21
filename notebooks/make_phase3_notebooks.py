"""Builds the three Phase 3 Kaggle notebooks (self-contained; DEV split prompts only, no gold answers).

Run from the repo root: .venv/Scripts/python.exe -X utf8 notebooks/make_phase3_notebooks.py
Also copies them to C:\\Users\\Kabir\\Downloads when that folder exists.
Settings are identical to the Phase 2 dry run (system prompts, temperature 0, num_predict, num_ctx 4096,
qwen3 think=false), so the gemma3:1b/qwen3:1.7b dry-run answers are reproducible by this runner.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eval.graders.formats import FORMAT_INSTRUCTIONS  # noqa: E402

tasks = json.loads((ROOT / "eval" / "tasks_8cat.json").read_text(encoding="utf-8"))
dev = [{"id": t["id"], "category": t["category"], "difficulty": t["difficulty"], "prompt": t["prompt"]}
       for t in tasks if t["split"] == "dev"]
assert len(dev) == 240 and all(t["split"] == "dev" for t in tasks if t["id"] in {d["id"] for d in dev})
sample = json.loads((ROOT / "eval" / "results" / "phase3" / "cpu_sample_ids.json").read_text(encoding="utf-8"))["ids"]
assert len(sample) == 40 and set(sample) <= {d["id"] for d in dev}

RUNNER = r'''"""Phase 3 local runner: Ollama on Kaggle, dev split, per-category system prompts, temperature 0.
Output: JSONL, one answer per line (fields as in eval/answers.py + done_reason, eval_ms, load_ms). Resumable.
"""
import argparse, json, os, shutil, subprocess, sys, time, urllib.request

HOST = "http://127.0.0.1:11434"
SYSTEM = json.load(open("system_prompts.json", encoding="utf-8"))
NUM_PREDICT = {"math": 768, "logic": 768, "sentiment": 256, "ner": 384, "code_debug": 1024,
               "code_gen": 1024, "summarisation": 256, "factual": 320}


def sh(cmd):
    subprocess.run(cmd, shell=True, check=True)


def install_and_serve():
    if not shutil.which("ollama"):
        sh("apt-get update -qq && apt-get install -y -qq zstd >/dev/null 2>&1 || true")
        sh("curl -fsSL https://ollama.com/install.sh | sh")
    try:
        urllib.request.urlopen(HOST + "/api/version", timeout=2)
        return
    except Exception:
        pass
    subprocess.Popen(["ollama", "serve"], stdout=open("/tmp/ollama.log", "w"), stderr=subprocess.STDOUT)
    for _ in range(60):
        try:
            urllib.request.urlopen(HOST + "/api/version", timeout=2)
            return
        except Exception:
            time.sleep(1)
    sys.exit("ollama server did not start; see /tmp/ollama.log")


def chat(model, category, prompt, cpu):
    opts = {"temperature": 0, "num_predict": NUM_PREDICT[category], "num_ctx": 4096}
    if cpu:
        opts.update(num_gpu=0, num_thread=2)
    payload = {"model": model, "stream": False, "keep_alive": "10m",
               "messages": [{"role": "system", "content": SYSTEM[category]},
                            {"role": "user", "content": prompt}],
               "options": opts}
    if model.startswith("qwen3"):
        payload["think"] = False
    req = urllib.request.Request(HOST + "/api/chat", json.dumps(payload).encode(), {"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=1800) as r:
        d = json.load(r)
    return d, int((time.perf_counter() - t0) * 1000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="tasks_dev.json")
    ap.add_argument("--ids", default=None, help="JSON file with {'ids': [...]} to restrict the tasks")
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--cpu", action="store_true", help="num_gpu=0, num_thread=2")
    a = ap.parse_args()
    tasks = json.load(open(a.tasks, encoding="utf-8"))
    if a.ids:
        keep = set(json.load(open(a.ids))["ids"])
        tasks = [t for t in tasks if t["id"] in keep]
    install_and_serve()
    done = set()
    if os.path.exists(a.out):
        for line in open(a.out, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                done.add((r["model"], r["task_id"]))
    for model in a.models:
        todo = [t for t in tasks if (model, t["id"]) not in done]
        if not todo:
            print(model, "already complete")
            continue
        sh("ollama pull " + model)
        try:  # warm-up so the first recorded answer does not include model load time (not saved)
            chat(model, "sentiment", "The food was fine.", a.cpu)
        except Exception as e:
            print("warm-up failed", model, e)
        n = 0
        for t in todo:
            rec = {"task_id": t["id"], "model": model, "provider": "ollama-kaggle", "run_id": a.run_id,
                   "raw_text": "", "extracted": None, "tokens_in": None, "tokens_out": None,
                   "tokens_reasoning": None, "latency_ms": None, "cost_usd": 0.0, "error": None,
                   "done_reason": None, "eval_ms": None, "load_ms": None}
            try:
                d, ms = chat(model, t["category"], t["prompt"], a.cpu)
                msg = d.get("message", {})
                rec.update(raw_text=msg.get("content", ""), tokens_in=d.get("prompt_eval_count"),
                           tokens_out=d.get("eval_count"), latency_ms=ms, done_reason=d.get("done_reason"),
                           eval_ms=(d.get("eval_duration") or 0) // 1_000_000,
                           load_ms=(d.get("load_duration") or 0) // 1_000_000)
                if msg.get("thinking"):
                    rec["raw_text"] = "<think>" + msg["thinking"] + "</think>" + rec["raw_text"]
            except Exception as e:
                rec["error"] = str(e)[:300]
            with open(a.out, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
            if n % 20 == 0:
                print(model, n, "answered", flush=True)
        sh("ollama stop " + model + " || true")
        sh("ollama rm " + model)
    print("done ->", a.out)


if __name__ == "__main__":
    main()
'''

FILES = [
    ("phase3_run.py", RUNNER),
    ("system_prompts.json", json.dumps(FORMAT_INSTRUCTIONS, indent=1, ensure_ascii=False)),
    ("tasks_dev.json", json.dumps(dev, indent=1, ensure_ascii=False)),
    ("cpu_sample_ids.json", json.dumps({"ids": sample}, indent=1)),
]

CHECK = ("import json, collections\nt = json.load(open('tasks_dev.json'))\n"
         "print(len(t), collections.Counter(x['category'] for x in t))\nassert len(t) == 240\n"
         "assert not any('gold' in x for x in t)")

LOOK = ("import json, pandas as pd\nrows = [json.loads(l) for l in open('{out}') if l.strip()]\n"
        "df = pd.DataFrame(rows)\nprint('records', len(df), 'errors', df['error'].notna().sum())\n"
        "print(df.groupby('model')[['tokens_out', 'latency_ms']].median())\n"
        "print(df.groupby(['model', 'done_reason']).size())")


def common_cells(intro, run_cmds, zipname, out):
    c = [("markdown", intro),
         ("code", "%cd /kaggle/working\n!nvidia-smi --query-gpu=name,memory.total --format=csv || echo no GPU\n!nproc\n!df -h /kaggle/working | tail -1")]
    for name, body in FILES:
        c.append(("code", f"%%writefile {name}\n" + body))
    c.append(("code", CHECK))
    c += run_cmds
    c.append(("markdown", "## Quick look + zip for download"))
    c.append(("code", LOOK.format(out=out)))
    c.append(("code", f"!zip -q {zipname} {out} tasks_dev.json system_prompts.json phase3_run.py cpu_sample_ids.json && ls -lh {zipname}"))
    return c


GPU_A = ["granite4:350m", "gemma3:1b", "llama3.2:1b", "qwen3:1.7b", "qwen2.5-coder:1.5b"]
GPU_B = ["llama3.2:3b", "phi3.5:3.8b", "gemma3:4b"]
SERVER = ["gemma3:12b", "phi4:14b", "qwen2.5:14b"]
CORE8 = GPU_A + GPU_B

nbs = {}
nbs["phase3_local_gpu_a.ipynb"] = common_cells(
    "# Phase 3: local models, GPU accuracy run A (granite4:350m, gemma3:1b, llama3.2:1b, qwen3:1.7b, qwen2.5-coder:1.5b)\n\n"
    "**Settings:** Accelerator = **GPU T4 x2**, Internet = **On**, Persistence = **Files only**.\n\n"
    "240 **dev** tasks per model (the test split and all gold answers are not in this notebook), per-category system prompts, "
    "temperature 0, same `num_predict` as the Phase 2 dry run, qwen3 with thinking off. Resumable: if the session drops, "
    "re-run the run cell and finished (model, task) pairs are skipped. Expect roughly 30-60 min.\n\n"
    "At the end download **`phase3_local_gpu_a.zip`** from the Output panel into `eval/results/phase3/`.",
    [("markdown", "## Run (resumable)"),
     ("code", "!python phase3_run.py --models " + " ".join(GPU_A) + " --out answers_gpu_a.jsonl --run-id phase3_gpu_a")],
    "phase3_local_gpu_a.zip", "answers_gpu_a.jsonl")

nbs["phase3_local_gpu_b.ipynb"] = common_cells(
    "# Phase 3: local models, GPU accuracy run B (llama3.2:3b, phi3.5:3.8b, gemma3:4b) + optional GPU-server tier\n\n"
    "**Settings:** Accelerator = **GPU T4 x2**, Internet = **On**, Persistence = **Files only**.\n\n"
    "Same settings as notebook A. Section 1 runs the three mid-size core models (240 dev tasks each). "
    "**Section 2 is OPTIONAL**: the 'own GPU server' tier (gemma3:12b, phi4:14b, qwen2.5:14b), reported separately, "
    "not part of the 16 models. Run it only if the session time allows (~1-2 h; models of 7-9 GB are pulled and deleted one at a time). "
    "Both write to the same JSONL and are resumable.\n\n"
    "At the end download **`phase3_local_gpu_b.zip`** into `eval/results/phase3/`.",
    [("markdown", "## Section 1: core models (resumable)"),
     ("code", "!python phase3_run.py --models " + " ".join(GPU_B) + " --out answers_gpu_b.jsonl --run-id phase3_gpu_b"),
     ("markdown", "## Section 2 (OPTIONAL): GPU-server tier, outside the 16 models\nSkip this cell if short on session time. Run before zipping."),
     ("code", "!python phase3_run.py --models " + " ".join(SERVER) + " --out answers_gpu_b.jsonl --run-id phase3_gpu_server")],
    "phase3_local_gpu_b.zip", "answers_gpu_b.jsonl")

nbs["phase3_local_cpu.ipynb"] = common_cells(
    "# Phase 3: local models, CPU speed run (2 threads, no GPU), 40-task dev sample\n\n"
    "**Settings:** Accelerator = **None**, Internet = **On**, Persistence = **Files only**.\n\n"
    "Eight core models on a fixed 40-task dev sample (5 per category, seeded; ids in `cpu_sample_ids.json`), "
    "`num_gpu=0`, `num_thread=2`, a warm-up call before each model so load time is not counted. "
    "Resumable. Expect roughly 1-2 h in total (the 3-4B models are slowest).\n\n"
    "At the end download **`phase3_local_cpu.zip`** into `eval/results/phase3/`.",
    [("markdown", "## Run (resumable)"),
     ("code", "!python phase3_run.py --cpu --ids cpu_sample_ids.json --models " + " ".join(CORE8) + " --out answers_cpu.jsonl --run-id phase3_cpu")],
    "phase3_local_cpu.zip", "answers_cpu.jsonl")


def mk(kind, src):
    lines = src.split("\n")
    lines = [l + "\n" for l in lines[:-1]] + [lines[-1]]
    c = {"cell_type": kind, "metadata": {}, "source": lines}
    if kind == "code":
        c.update(execution_count=None, outputs=[])
    return c


dl = Path(r"C:\Users\Kabir\Downloads")
for name, cells in nbs.items():
    nb = {"cells": [mk(k, s) for k, s in cells],
          "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    out = ROOT / "notebooks" / name
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", out)
    if dl.exists():
        shutil.copy(out, dl / name)
        print("  copied to", dl / name)
