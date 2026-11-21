"""
Run a list of Ollama models over a JSON prompt file on a free Kaggle/Colab T4.

Usage in a notebook cell:

    !python local_bench_ollama.py --prompts prompts.json --models qwen2.5:0.5b qwen3:1.7b \
        --out results_gpu.json
    # CPU-only latency pass (the deployment constraint: 2 threads):
    !python local_bench_ollama.py --prompts prompts.json --models qwen2.5:0.5b --cpu --out results_cpu.json

prompts.json: [{"id": "...", "category": "...", "prompt": "..."}, ...]
Output: one record per (model, prompt) with text, token counts, tokens/s, wall latency.
Models are pulled one at a time and removed after use to keep the disk small.
Note: Kaggle/Colab CPUs differ from the laptop, so CPU latency measured there is
indicative only; re-measure the final candidates on the laptop.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

HOST = "http://127.0.0.1:11434"


def sh(cmd: str) -> None:
    subprocess.run(cmd, shell=True, check=True)


def install_and_serve() -> None:
    if not shutil.which("ollama"):
        # zstd is needed by the Ollama install script on some images
        sh("apt-get update -qq && apt-get install -y -qq zstd >/dev/null 2>&1 || true")
        sh("curl -fsSL https://ollama.com/install.sh | sh")
    try:
        urllib.request.urlopen(f"{HOST}/api/version", timeout=2)
        return
    except Exception:  # noqa: BLE001
        pass
    subprocess.Popen(["ollama", "serve"], stdout=open("/tmp/ollama.log", "w"), stderr=subprocess.STDOUT)
    for _ in range(60):
        try:
            urllib.request.urlopen(f"{HOST}/api/version", timeout=2)
            return
        except Exception:  # noqa: BLE001
            time.sleep(1)
    sys.exit("ollama server did not start; see /tmp/ollama.log")


def generate(model: str, prompt: str, options: dict) -> dict:
    # keep_alive 10m: the model stays loaded for the rest of its prompts (keep_alive 0
    # reloaded it on every prompt, so latency would mostly measure load time).
    # think False: qwen3 otherwise spends hundreds of hidden tokens per answer.
    payload = {"model": model, "prompt": prompt, "stream": False,
               "keep_alive": "10m", "options": options}
    if model.startswith("qwen3"):  # only send `think` to thinking-capable models
        payload["think"] = False
    body = json.dumps(payload).encode()
    req = urllib.request.Request(f"{HOST}/api/generate", body, {"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.load(r)
    ms = int((time.perf_counter() - t0) * 1000)
    ec, ed = d.get("eval_count", 0), d.get("eval_duration", 0)
    raw = d.get("response", "")
    # Thinking models can still emit <think>...</think> (or a stray /no_think) even with
    # think=False. Keep the raw text, but grade only the visible answer.
    text = re.sub(r"<think>.*?(</think>|$)", "", raw, flags=re.S)
    text = re.sub(r"\s*/\s*no_think", "", text).strip()  # also catches "/ no_think"
    leaked = raw.strip() != text  # whitespace-only differences don't count
    return {"text": text, "raw_text": raw if leaked else None,
            "thinking_leaked": leaked, "prompt_tokens": d.get("prompt_eval_count"),
            "completion_tokens": ec, "tokens_per_s": round(ec / (ed / 1e9), 1) if ed else None,
            "load_ms": int(d.get("load_duration", 0) / 1e6), "latency_ms": ms}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--out", default="results.json")
    ap.add_argument("--cpu", action="store_true", help="num_gpu=0, num_thread=2")
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--keep-models", action="store_true")
    a = ap.parse_args()

    prompts = json.load(open(a.prompts, encoding="utf-8"))
    opts = {"temperature": 0, "num_predict": a.max_tokens}
    if a.cpu:
        opts.update(num_gpu=0, num_thread=2)

    install_and_serve()
    results = json.load(open(a.out)) if os.path.exists(a.out) else []
    done = {(r["model"], r["id"]) for r in results}
    for model in a.models:
        sh(f"ollama pull {model}")
        for p in prompts:
            if (model, p["id"]) in done:
                continue
            try:
                rec = generate(model, p["prompt"], opts)
            except Exception as e:  # noqa: BLE001
                rec = {"error": str(e)[:300]}
            results.append({"model": model, "id": p["id"], "category": p.get("category"),
                            "mode": "cpu_2threads" if a.cpu else "gpu", **rec})
            json.dump(results, open(a.out, "w", encoding="utf-8"), indent=1)  # resumable
        sh(f"ollama stop {model} || true")  # free GPU/RAM before the next model
        if not a.keep_models:
            sh(f"ollama rm {model}")
    print(f"wrote {len(results)} records to {a.out}")


if __name__ == "__main__":
    main()
