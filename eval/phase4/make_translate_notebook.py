"""Builds notebooks/phase4_solver_translate_kaggle.ipynb (self-contained). Embeds ONLY dev math + logic prompts (id, category, prompt):
no gold, no test tasks, no difficulty or template-set labels.

Run from the repo root: PYTHONPATH=. .venv/Scripts/python.exe -X utf8 eval/phase4/make_translate_notebook.py
"""
import json
from pathlib import Path

from router.data import ROOT, load_dev
from router.solvers.translate import LOGIC_SYSTEM, MATH_SYSTEM

tasks = [{"id": t["id"], "category": t["category"], "prompt": t["prompt"]} for t in load_dev() if t["category"] in ("math", "logic")]
assert len(tasks) == 60 and {t["category"] for t in tasks} == {"math", "logic"}
PROMPTS = {"math": MATH_SYSTEM, "logic": LOGIC_SYSTEM}
MODELS = ["qwen3:1.7b", "gemma3:1b", "qwen2.5-coder:1.5b", "phi3.5:3.8b", "gemma3:4b"]

RUNNER = r'''"""Phase 4 D13: local models TRANSLATE dev math/logic tasks into an expression / JSON spec. Python solves offline.
Temperature 0. Output: JSONL, one reply per line. Resumable."""
import argparse, json, os, shutil, subprocess, sys, time, urllib.request

HOST = "http://127.0.0.1:11434"
SYSTEM = json.load(open("translate_prompts.json", encoding="utf-8"))
NUM_PREDICT = {"math": 256, "logic": 800}


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


def chat(model, category, text):
    label = "Problem: " if category == "math" else "Puzzle: "
    payload = {"model": model, "stream": False, "keep_alive": "10m",
               "messages": [{"role": "system", "content": SYSTEM[category]},
                            {"role": "user", "content": label + text}],
               "options": {"temperature": 0, "num_predict": NUM_PREDICT[category], "num_ctx": 4096}}
    if category == "logic":
        payload["format"] = "json"
    if model.startswith("qwen3"):
        payload["think"] = False
    req = urllib.request.Request(HOST + "/api/chat", json.dumps(payload).encode(), {"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.load(r)
    return d, int((time.perf_counter() - t0) * 1000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="tasks_translate.json")
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--out", default="translations.jsonl")
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
            rec = {"task_id": t["id"], "model": model, "category": t["category"], "raw_text": "", "tokens_out": None,
                   "latency_ms": None, "done_reason": None, "error": None}
            try:
                d, ms = chat(model, t["category"], t["prompt"])
                msg = d.get("message", {})
                rec.update(raw_text=msg.get("content", ""), tokens_out=d.get("eval_count"), latency_ms=ms,
                           done_reason=d.get("done_reason"))
            except Exception as e:
                rec["error"] = str(e)[:300]
            with open(a.out, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
            if n % 20 == 0:
                print(model, n, "done", flush=True)
        sh("ollama stop " + model + " || true")
        sh("ollama rm " + model)
    print("done ->", a.out)


if __name__ == "__main__":
    main()
'''


def md(s):
    return {"cell_type": "markdown", "metadata": {}, "source": s.splitlines(True)}


def code(s):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s.splitlines(True)}


def writefile(name, content):
    return code(f"%%writefile {name}\n{content}")


cells = [
    md("# Phase 4 D13: local models translate math and logic tasks (Kaggle, GPU T4 x2)\n\n"
       "**Settings:** Accelerator = **GPU T4 x2**, Internet = **On**, Persistence = **Files only**.\n\n"
       f"Runs {', '.join('**' + m + '**' for m in MODELS)} on the **60 dev math + logic tasks** (no test tasks, no gold answers in this notebook). "
       "Each model only *translates* (math -> one arithmetic expression, logic -> a JSON spec); the solving and checking are done offline in Python. "
       "Temperature 0; qwen3 with thinking off. Expect roughly 15-30 min in total.\n\n"
       "At the end download **`phase4_solver_translate.zip`** from the Output panel and put it in `eval/results/phase4/`."),
    code("%cd /kaggle/working\n!nvidia-smi --query-gpu=name,memory.total --format=csv\n!df -h /kaggle/working | tail -1"),
    writefile("translate_prompts.json", json.dumps(PROMPTS, indent=1, ensure_ascii=False)),
    writefile("tasks_translate.json", json.dumps(tasks, indent=1, ensure_ascii=False)),
    writefile("translate_run.py", RUNNER),
    code("import json, collections\nt = json.load(open('tasks_translate.json'))\nprint(len(t), collections.Counter(x['category'] for x in t))\n"
         "assert len(t) == 60\nassert all(set(x) == {'id', 'category', 'prompt'} for x in t)"),
    md("## Run all five models (resumable: re-run this cell if the session drops)"),
    code("!python translate_run.py --tasks tasks_translate.json --models " + " ".join(MODELS) + " --out translations.jsonl"),
    md("## Quick look + download"),
    code("import pandas as pd\nrows = [json.loads(l) for l in open('translations.jsonl') if l.strip()]\ndf = pd.DataFrame(rows)\n"
         "print('records', len(df), 'errors', df['error'].notna().sum())\nprint(df.groupby(['model', 'category'])[['tokens_out', 'latency_ms']].median())\n"
         "print(df.groupby(['model', 'done_reason']).size())"),
    code("!zip -q phase4_solver_translate.zip translations.jsonl tasks_translate.json translate_prompts.json translate_run.py && ls -lh phase4_solver_translate.zip"),
]
nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                    "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
out = ROOT / "notebooks" / "phase4_solver_translate_kaggle.ipynb"
out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print("wrote", out, out.stat().st_size, "bytes;", len(tasks), "tasks;", len(MODELS), "models")
