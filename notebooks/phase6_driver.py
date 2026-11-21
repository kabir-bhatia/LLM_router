"""Phase 6 Kaggle driver: serves Ollama, pulls the policies' local models, runs `python -m router.run` on the 160 test prompts.

Order: (a) main policy on GPU x3, (b) one CPU-deployment check (CPU only, 2 threads, 30 s budget), (c) one GPU-server-policy run.
Restart-safe: a finished run (results.json meta.complete) is skipped, a partial run resumes with --resume.
Spend guard: Fireworks spend (sum of API trace steps of non-Hyde, non-Gemini models, over ALL runs in this notebook)
above GUARD_USD stops the running router (its results.json is written after every task), skips the rest and zips.
Keys come from the environment only and are never printed.
"""
import json, os, shutil, subprocess, sys, threading, time, urllib.request
from pathlib import Path

REPO = Path("/kaggle/working/LLM_Router")
OUT = Path("/kaggle/working/phase6_out")
ZIP = Path("/kaggle/working/phase6_results.zip")
HOST = "http://127.0.0.1:11434"
GUARD_USD = 1.50
DEADLINE_S = 4 * 3600
POLICY_MAIN = REPO / "eval/results/phase4/routing_policy.json"
POLICY_GPU = REPO / "eval/results/phase4/routing_policy_gpu_server.json"
TASKS = REPO / "eval/results/phase6/test_prompts.json"
FREE_PREFIXES = ("hyde/", "gemini")

RUNS = [  # name, policy, local_cpu_only
    ("main_gpu_run1", POLICY_MAIN, "0"), ("main_gpu_run2", POLICY_MAIN, "0"), ("main_gpu_run3", POLICY_MAIN, "0"),
    ("main_cpu_check", POLICY_MAIN, "1"), ("gpu_server_run1", POLICY_GPU, "0")]


def sh(cmd, check=True):
    return subprocess.run(cmd, shell=True, check=check)


def alive():
    try:
        urllib.request.urlopen(HOST + "/api/version", timeout=2)
        return True
    except Exception:
        return False


def serve():
    if not shutil.which("ollama"):
        sh("apt-get update -qq && apt-get install -y -qq zstd >/dev/null 2>&1 || true")
        sh("curl -fsSL https://ollama.com/install.sh | sh")
    if alive():
        return
    tmp = Path("/kaggle/temp")  # more room than /kaggle/working for the 8-9 GB server models
    if tmp.exists():
        os.environ.setdefault("OLLAMA_MODELS", str(tmp / "ollama"))
    subprocess.Popen(["ollama", "serve"], stdout=open("/tmp/ollama.log", "w"), stderr=subprocess.STDOUT)
    for _ in range(60):
        if alive():
            return
        time.sleep(1)
    sys.exit("ollama did not start; see /tmp/ollama.log")


def local_models(policy_path):
    p = json.load(open(policy_path, encoding="utf-8"))
    ms = {c["model"] for c in p["cells"].values() if c["kind"] == "local"}
    ms |= {c["initial_model"] for c in p["cells"].values() if str(c.get("initial_model", "")).count(":")}
    return ms


def pull(models):
    for m in sorted(models):
        sh(f"ollama pull {m}")
    sh("df -h /kaggle/working /kaggle/temp 2>/dev/null | cat", check=False)


def fireworks_spend():
    tot = 0.0
    for f in OUT.glob("*/results.json"):
        try:
            rows = json.load(open(f, encoding="utf-8")).get("results", [])
        except Exception:
            continue  # being replaced; next poll reads it
        for r in rows:
            for s in r.get("trace") or []:
                if s.get("step") == "api" and not str(s.get("model", "")).startswith(FREE_PREFIXES):
                    tot += s.get("cost_usd") or 0.0
    return tot


def complete(rdir):
    try:
        return json.load(open(rdir / "results.json", encoding="utf-8"))["meta"].get("complete") is True
    except Exception:
        return False


def run_one(name, policy, cpu_only):
    rdir = OUT / name
    rdir.mkdir(parents=True, exist_ok=True)
    if complete(rdir):
        print(f"[{name}] already complete, skipped")
        return "done"
    env = dict(os.environ, ROUTER_LOCAL_CPU_ONLY=cpu_only, ROUTER_LOCAL_THREADS="2", ROUTER_LOCAL_BUDGET_S="30",
               ROUTER_POLICY_PATH=str(policy), PYTHONPATH=str(REPO), HF_HUB_DISABLE_PROGRESS_BARS="1")
    cmd = [sys.executable, "-m", "router.run", str(TASKS), str(rdir / "results.json"), "--log", str(rdir / "log.jsonl"),
           "--policy", str(policy), "--embed", "inprocess", "--api-workers", "8", "--deadline-s", str(DEADLINE_S), "--resume"]
    print(f"[{name}] start  cpu_only={cpu_only}  policy={policy.name}  spend so far ${fireworks_spend():.4f}", flush=True)
    proc = subprocess.Popen(cmd, cwd=str(REPO), env=env, stdout=open(rdir / "run.log", "a"), stderr=subprocess.STDOUT)
    tripped = False
    while proc.poll() is None:
        time.sleep(10)
        if fireworks_spend() > GUARD_USD:
            tripped = True
            proc.terminate()
            try:
                proc.wait(60)
            except subprocess.TimeoutExpired:
                proc.kill()
    print(f"[{name}] exit {proc.returncode}  spend ${fireworks_spend():.4f}", flush=True)
    return "guard" if tripped else ("done" if complete(rdir) else "partial")


def make_zip():
    sh(f"cd /kaggle/working && rm -f {ZIP.name} && zip -qr {ZIP.name} phase6_out && ls -lh {ZIP.name}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    serve()
    pull(local_models(POLICY_MAIN))
    status = {}
    for i, (name, policy, cpu) in enumerate(RUNS):
        if name == "gpu_server_run1" and not complete(OUT / name) and fireworks_spend() <= GUARD_USD:
            pull(local_models(POLICY_GPU))
        if fireworks_spend() > GUARD_USD:
            status[name] = "skipped (spend guard)"
            continue
        status[name] = run_one(name, policy, cpu)
        make_zip()  # after every run, so a session that dies still leaves a zip
        if status[name] == "guard":
            print("SPEND GUARD tripped: stopped and saved; remaining runs skipped.")
    (OUT / "status.json").write_text(json.dumps({"status": status, "fireworks_spend_usd": round(fireworks_spend(), 5)}, indent=1))
    make_zip()
    print(json.dumps(status, indent=1), f"Fireworks spend ${fireworks_spend():.4f}")


if __name__ == "__main__":
    main()
