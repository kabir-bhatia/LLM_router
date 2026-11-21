"""Phase 3 API runner: the 8 paid-API models on the DEV split at LOW reasoning effort (D11).

Usage (from the repo root):
  .venv/Scripts/python.exe -X utf8 -m eval.run_api --smoke                 # 2 tasks per category per model (16)
  .venv/Scripts/python.exe -X utf8 -m eval.run_api                         # all 240 dev tasks, all 8 models
  .venv/Scripts/python.exe -X utf8 -m eval.run_api --models gpt-oss-120b --max-cost 5.00

Answers go to eval/results/phase3/answers_api.jsonl (eval/answers.py schema + finish_reason, reasoning/total
tokens). Resumable: finished (model, task) pairs with no error are skipped, so a smoke run counts toward the
full run (same settings). Cost = tokens x list price in eval/model_prices.json for every model (Hyde GLM and
Gemini are free to us but priced at list so the comparison is fair). The hard cap (--max-cost) applies to
Fireworks only and includes the spend already in the answer store.

Only the dev split is ever read. Keys come from the gitignored .env via src.config; they are never printed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
import time
from pathlib import Path

from eval.answers import append_answer, make_record
from eval.graders.formats import system_prompt
from eval.task_schema import load_tasks

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "results" / "phase3"
STORE = OUT_DIR / "answers_api.jsonl"
RUN_ID = "phase3_api_low"
PRICES = json.loads((ROOT / "model_prices.json").read_text(encoding="utf-8"))
FW = "accounts/fireworks/models/"

# Output budget INCLUDES reasoning tokens, so it is far above what the answer itself needs; finish_reason is logged.
MAX_TOKENS = {"math": 6000, "logic": 6000, "code_debug": 6000, "code_gen": 6000, "ner": 3000,
              "summarisation": 3000, "factual": 3000, "sentiment": 2000}

# name -> (provider, api model id, list price key, concurrency)
MODELS = {
    "nemotron-lightning-3p5-30b-a3b": ("fireworks", FW + "nemotron-lightning-3p5-30b-a3b", ("fireworks", FW + "nemotron-lightning-3p5-30b-a3b"), 6),
    "gpt-oss-120b": ("fireworks", FW + "gpt-oss-120b", ("fireworks", FW + "gpt-oss-120b"), 6),
    "minimax-m3p1-flash": ("fireworks", FW + "minimax-m3p1-flash", ("fireworks", FW + "minimax-m3p1-flash"), 6),
    "deepseek-v4p1-flash": ("fireworks", FW + "deepseek-v4p1-flash", ("fireworks", FW + "deepseek-v4p1-flash"), 6),
    "glm-5p3": ("fireworks", FW + "glm-5p3", ("fireworks", FW + "glm-5p3"), 6),
    "kimi-k3p1-pro": ("fireworks", FW + "kimi-k3p1-pro", ("fireworks", FW + "kimi-k3p1-pro"), 6),
    "hyde/glm-5.3-flash": ("hyde", "hyde/glm-5.3-flash", ("hyde", "hyde/glm-5.3-flash"), 4),
    "gemini-3.1-flash-lite": ("gemini", "gemini-3.1-flash-lite", ("gemini", "gemini-3.1-flash-lite"), 1),
}
GEMINI_MIN_INTERVAL = 4.5  # seconds between calls: free tier is ~15 requests/min on the 3.x models


def price(name: str) -> tuple:
    p = PRICES[MODELS[name][2][0]][MODELS[name][2][1]]
    return p["input"], p["output"]


def cost_usd(name: str, tin, tout) -> float:
    pi, po = price(name)
    return ((tin or 0) * pi + (tout or 0) * po) / 1e6


class Budget:
    """Fireworks hard cap. Counts spend already in the store plus a reserve for calls in flight."""

    def __init__(self, cap: float, spent: float):
        self.cap, self.spent, self.inflight = cap, spent, {}
        self.mean = {}

    def reserve(self, model: str) -> float:
        return self.mean.get(model, 0.004)

    def try_start(self, model: str) -> bool:
        pending = sum(n * self.reserve(m) for m, n in self.inflight.items())
        if self.spent + pending + self.reserve(model) > self.cap:
            return False
        self.inflight[model] = self.inflight.get(model, 0) + 1
        return True

    def finish(self, model: str, cost: float):
        self.inflight[model] -= 1
        self.spent += cost


class Retry(Exception):
    pass


async def call_openai_compat(provider, api_model, system, prompt, max_tokens):
    payload = {"model": api_model, "temperature": 0, "max_tokens": max_tokens, "reasoning_effort": "low",
               "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
    data, ms = await provider.chat(payload)
    ch = (data.get("choices") or [{}])[0]
    usage = data.get("usage") or {}
    det = usage.get("completion_tokens_details") or {}
    return dict(text=(ch.get("message") or {}).get("content") or "", finish=ch.get("finish_reason"),
                tin=usage.get("prompt_tokens"), tout=usage.get("completion_tokens"),
                treason=det.get("reasoning_tokens"), ms=ms)


class GeminiCaller:
    def __init__(self):
        from google import genai
        from google.genai import types
        from src.config import get_settings
        self.types = types
        self.client = genai.Client(api_key=get_settings().google_api_key)
        self.lock = asyncio.Lock()
        self.last = 0.0

    async def __call__(self, api_model, system, prompt, max_tokens):
        async with self.lock:  # one request at a time, spaced out
            wait = GEMINI_MIN_INTERVAL - (time.monotonic() - self.last)
            if wait > 0:
                await asyncio.sleep(wait)
            self.last = time.monotonic()
        t = self.types
        cfg = t.GenerateContentConfig(system_instruction=system, temperature=0, max_output_tokens=max_tokens,
                                      thinking_config=t.ThinkingConfig(thinking_level="LOW"))
        t0 = time.perf_counter()
        r = await self.client.aio.models.generate_content(model=api_model, contents=prompt, config=cfg)
        ms = int((time.perf_counter() - t0) * 1000)
        text = ""
        finish = None
        for c in r.candidates or []:
            finish = str(c.finish_reason).split(".")[-1] if c.finish_reason is not None else None
            for p in (c.content.parts if c.content and c.content.parts else []):
                if getattr(p, "text", None) and not getattr(p, "thought", False):
                    text += p.text
        u = r.usage_metadata
        thoughts = (u.thoughts_token_count or 0) if u else 0
        cand = (u.candidates_token_count or 0) if u else 0
        return dict(text=text, finish=finish, tin=u.prompt_token_count if u else None, tout=cand + thoughts,
                    treason=thoughts, ms=ms)


def is_rate_limit(e: Exception) -> bool:
    s = f"{type(e).__name__} {e}"
    return "RateLimit" in s or "429" in s or "RESOURCE_EXHAUSTED" in s


def is_retriable(e: Exception) -> bool:
    s = f"{type(e).__name__} {e}"
    if "ModelNotFound" in s or "HTTP 4" in s and "429" not in s and "408" not in s:
        return False
    return True


async def run_model(name, tasks, store_lock, budget, providers, gemini, counters):
    prov, api_model, _, conc = MODELS[name]
    sem = asyncio.Semaphore(conc)
    caller = None if prov == "gemini" else providers[prov]

    async def one(t):
        async with sem:
            if prov == "fireworks":
                while not budget.try_start(name):
                    if budget.spent >= budget.cap - 1e-9 or not any(budget.inflight.values()):
                        counters["stopped"] = True
                        return
                    await asyncio.sleep(1)
            sysmsg, mt = system_prompt(t["category"]), MAX_TOKENS[t["category"]]
            err, res = None, None
            for attempt in range(6):
                try:
                    if prov == "gemini":
                        res = await gemini(api_model, sysmsg, t["prompt"], mt)
                    else:
                        res = await call_openai_compat(caller, api_model, sysmsg, t["prompt"], mt)
                    err = None
                    break
                except Exception as e:  # noqa: BLE001
                    err = f"{type(e).__name__}: {str(e)[:250]}"
                    if not is_retriable(e) or attempt == 5:
                        break
                    base = 20 if is_rate_limit(e) else 2
                    await asyncio.sleep(min(120, base * 2 ** attempt) + random.random())
            c = cost_usd(name, res["tin"], res["tout"]) if res else 0.0
            rec = make_record(t["id"], name, prov, RUN_ID, raw_text=res["text"] if res else "",
                              tokens_in=res["tin"] if res else None, tokens_out=res["tout"] if res else None,
                              tokens_reasoning=res["treason"] if res else None, latency_ms=res["ms"] if res else None,
                              cost_usd=c, error=err)
            rec["finish_reason"] = res["finish"] if res else None
            rec["max_tokens"] = mt
            async with store_lock:
                append_answer(STORE, rec)
                counters["n"] += 1
                counters["cost"][prov] = counters["cost"].get(prov, 0.0) + c
                counters["err"] += bool(err)
                counters["trunc"] += (res or {}).get("finish") in ("length", "MAX_TOKENS")
                if prov == "fireworks":
                    budget.finish(name, c)
                    k = counters.setdefault("k_" + name, [0, 0.0])
                    k[0] += 1
                    k[1] += c
                    budget.mean[name] = k[1] / k[0]
                if counters["n"] % 10 == 0:
                    print(f"[{counters['n']}/{counters['total']}] errors {counters['err']} truncated {counters['trunc']} "
                          f"spend {', '.join(f'{k} ${v:.4f}' for k, v in counters['cost'].items())}", flush=True)

    await asyncio.gather(*(one(t) for t in tasks))


def smoke_tasks(dev):
    out = []
    for c in sorted({t["category"] for t in dev}):
        pool = sorted((t for t in dev if t["category"] == c), key=lambda t: t["id"])
        out += [next(t for t in pool if t["difficulty"] == "easy"), next(t for t in pool if t["difficulty"] == "hard")]
    return out


def load_store():
    done, spent_fw = set(), 0.0
    if STORE.exists():
        for line in STORE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r["provider"] == "fireworks":
                    spent_fw += r["cost_usd"] or 0
                if not r["error"]:
                    done.add((r["model"], r["task_id"]))
    return done, spent_fw


async def amain(a):
    from src.providers.openai_compat import OpenAICompatProvider
    dev = [t for t in load_tasks(ROOT / "tasks_8cat.json") if t["split"] == "dev"]
    assert len(dev) == 240 and all(t["split"] == "dev" for t in dev)  # the test split is never sent anywhere
    tasks = smoke_tasks(dev) if a.smoke else dev
    names = a.models or list(MODELS)
    for n in names:
        if n not in MODELS:
            sys.exit(f"unknown model {n}; choose from {list(MODELS)}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    done, spent_fw = load_store()
    budget = Budget(a.max_cost, spent_fw)
    print(f"Fireworks spend already in store: ${spent_fw:.4f} (cap ${a.max_cost:.2f})")
    providers = {}
    if any(MODELS[n][0] == "fireworks" for n in names):
        providers["fireworks"] = OpenAICompatProvider.fireworks(timeout=300)
    if any(MODELS[n][0] == "hyde" for n in names):
        providers["hyde"] = OpenAICompatProvider.hyde(timeout=300)
    gemini = GeminiCaller() if any(MODELS[n][0] == "gemini" for n in names) else None
    work = {n: [t for t in tasks if (n, t["id"]) not in done] for n in names}
    counters = {"n": 0, "total": sum(len(v) for v in work.values()), "cost": {}, "err": 0, "trunc": 0, "stopped": False}
    print({n: len(v) for n, v in work.items()})
    lock = asyncio.Lock()
    # cheap Fireworks models first, premium ones last, so a cap hit costs the least
    await asyncio.gather(*(run_model(n, work[n], lock, budget, providers, gemini, counters) for n in names if work[n]))
    for p in providers.values():
        await p.close()
    print(f"done: {counters['n']} calls, errors {counters['err']}, truncated {counters['trunc']}, "
          f"spend this run {counters['cost']}, Fireworks total ${budget.spent:.4f}")
    if counters["stopped"]:
        print("STOPPED by --max-cost: re-run with a higher cap only after checking the spend.")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="2 tasks per category (1 easy, 1 hard) per model")
    ap.add_argument("--models", nargs="+", default=None)
    ap.add_argument("--max-cost", type=float, default=5.00, help="hard stop for total Fireworks spend, USD")
    a = ap.parse_args(argv)
    asyncio.run(amain(a))


if __name__ == "__main__":
    main()
