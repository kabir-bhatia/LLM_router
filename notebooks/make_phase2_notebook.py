"""Builds notebooks/phase2_dryrun_kaggle.ipynb (self-contained; embeds the DEV split prompts only).

Run: .venv/Scripts/python.exe -X utf8 notebooks/make_phase2_notebook.py   (from the repo root)
The test split and all gold answers never go into the notebook: only id, category, difficulty, prompt of dev tasks.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eval.graders.formats import FORMAT_INSTRUCTIONS  # noqa: E402

tasks = json.loads((ROOT / "eval" / "tasks_8cat.json").read_text(encoding="utf-8"))
dev = [{"id": t["id"], "category": t["category"], "difficulty": t["difficulty"], "prompt": t["prompt"]}
       for t in tasks if t["split"] == "dev"]
assert len(dev) == 240 and all(t["split"] == "dev" for t in tasks if t["id"] in {d["id"] for d in dev})
assert not ({d["id"] for d in dev} & {t["id"] for t in tasks if t["split"] == "test"})

RUNNER = r'''"""Phase 2 dry run: local models on the dev split, system prompts per category, temperature 0.
Output: JSONL, one answer per line (fields as in eval/answers.py). Resumable.
"""
import argparse, json, os, re, shutil, subprocess, sys, time, urllib.request

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


def chat(model, category, prompt):
    payload = {"model": model, "stream": False, "keep_alive": "10m",
               "messages": [{"role": "system", "content": SYSTEM[category]},
                            {"role": "user", "content": prompt}],
               "options": {"temperature": 0, "num_predict": NUM_PREDICT[category], "num_ctx": 4096}}
    if model.startswith("qwen3"):
        payload["think"] = False
    req = urllib.request.Request(HOST + "/api/chat", json.dumps(payload).encode(), {"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.load(r)
    ms = int((time.perf_counter() - t0) * 1000)
    return d, ms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="tasks_dev.json")
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--out", default="answers_dryrun.jsonl")
    ap.add_argument("--run-id", default="phase2_dryrun_gpu")
    a = ap.parse_args()
    tasks = json.load(open(a.tasks, encoding="utf-8"))
    install_and_serve()
    done = set()
    if os.path.exists(a.out):
        for line in open(a.out, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                done.add((r["model"], r["task_id"]))
    for model in a.models:
        sh("ollama pull " + model)
        n = 0
        for t in tasks:
            if (model, t["id"]) in done:
                continue
            rec = {"task_id": t["id"], "model": model, "provider": "ollama-kaggle", "run_id": a.run_id,
                   "raw_text": "", "extracted": None, "tokens_in": None, "tokens_out": None,
                   "tokens_reasoning": None, "latency_ms": None, "cost_usd": 0.0, "error": None,
                   "done_reason": None}
            try:
                d, ms = chat(model, t["category"], t["prompt"])
                msg = d.get("message", {})
                rec.update(raw_text=msg.get("content", ""), tokens_in=d.get("prompt_eval_count"),
                           tokens_out=d.get("eval_count"), latency_ms=ms, done_reason=d.get("done_reason"))
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

md_intro = """# Phase 2 dry run (Kaggle, GPU T4 x2)

**Settings:** Accelerator = **GPU T4 x2**, Internet = **On**, Persistence = **Files only**.

Runs **gemma3:1b** and **qwen3:1.7b** on the **240 dev tasks** (the test split is not in this notebook), with the
per-category system prompts from `eval/graders/formats.py`, temperature 0 and per-category `num_predict`
(code 1024, math/logic 768, rest 256-384). Expect roughly 15-30 min in total.

At the end download **`phase2_dryrun.zip`** from the Output panel and put it in `eval/results/phase2_dryrun/`."""

cells = [
    ("markdown", md_intro),
    ("code", "%cd /kaggle/working\n!nvidia-smi --query-gpu=name,memory.total --format=csv\n!df -h /kaggle/working | tail -1"),
    ("code", "%%writefile phase2_run.py\n" + RUNNER),
    ("code", "%%writefile system_prompts.json\n" + json.dumps(FORMAT_INSTRUCTIONS, indent=1, ensure_ascii=False)),
    ("code", "%%writefile tasks_dev.json\n" + json.dumps(dev, indent=1, ensure_ascii=False)),
    ("code", "import json, collections\nt = json.load(open('tasks_dev.json'))\n"
             "print(len(t), collections.Counter((x['category'], x['difficulty']) for x in t))\nassert len(t) == 240"),
    ("markdown", "## Run both models (resumable: re-run this cell if the session drops)"),
    ("code", "!python phase2_run.py --tasks tasks_dev.json --models gemma3:1b qwen3:1.7b --out answers_dryrun.jsonl"),
    ("markdown", "## Quick look + download"),
    ("code", "import pandas as pd\nrows = [json.loads(l) for l in open('answers_dryrun.jsonl') if l.strip()]\n"
             "df = pd.DataFrame(rows)\nprint('records', len(df), 'errors', df['error'].notna().sum())\n"
             "print(df.groupby('model')[['tokens_out', 'latency_ms']].median())\n"
             "print(df.groupby(['model', 'done_reason']).size())"),
    ("code", "!zip -q phase2_dryrun.zip answers_dryrun.jsonl tasks_dev.json system_prompts.json phase2_run.py && ls -lh phase2_dryrun.zip"),
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
                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
out = ROOT / "notebooks" / "phase2_dryrun_kaggle.ipynb"
out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print("wrote", out, len(dev), "dev tasks")
