"""Phase 3 local runner: Ollama on Kaggle, dev split, per-category system prompts, temperature 0.
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
