"""Phase 2 dry run: local models on the dev split, system prompts per category, temperature 0.
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
