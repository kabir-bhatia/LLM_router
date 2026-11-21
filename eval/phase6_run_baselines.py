"""Phase 6 step 3: B1 (kimi-k3p1-pro) and B2 (deepseek-v4p1-flash) on the 160 TEST tasks, 3 runs each.

Same settings as Phase 3 (eval/run_api.py): low reasoning effort, temperature 0, per-category system prompts, same output budgets,
same retry logic, list-price cost. It reuses run_api's call/retry/budget code unchanged. Answers go to
eval/results/phase6/answers_b1b2.jsonl (run ids phase6_b_run1..3). Resumable per (model, task, run). Not graded here (step 5).

  python -X utf8 -m eval.phase6_run_baselines [--max-cost 1.5]

Keys come from the gitignored .env via src.config; never printed.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
from pathlib import Path

from eval import run_api as R
from eval.answers import append_answer, make_record
from eval.graders.formats import system_prompt
from eval.task_schema import load_tasks

OUT = Path(__file__).resolve().parent / "results" / "phase6"
STORE = OUT / "answers_b1b2.jsonl"
MODELS = ["kimi-k3p1-pro", "deepseek-v4p1-flash"]
RUNS = [1, 2, 3]


def load_store():
    done, spent = set(), 0.0
    if STORE.exists():
        for line in STORE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                spent += r["cost_usd"] or 0
                if not r["error"]:
                    done.add((r["model"], r["task_id"], r["run_id"]))
    return done, spent


async def amain(a):
    from src.providers.openai_compat import OpenAICompatProvider
    test = [t for t in load_tasks(R.ROOT / "tasks_8cat.json") if t["split"] == "test"]
    assert len(test) == 160
    done, spent = load_store()
    budget = R.Budget(a.max_cost, spent)
    print(f"Fireworks spend already in store: ${spent:.4f} (cap ${a.max_cost:.2f})", flush=True)
    prov = OpenAICompatProvider.fireworks(timeout=300)
    lock = asyncio.Lock()
    counters = {"n": 0, "err": 0, "trunc": 0, "cost": 0.0, "stopped": False}

    async def one(name, run, t, sem):
        run_id = f"phase6_b_run{run}"
        async with sem:
            while not budget.try_start(name):
                if budget.spent >= budget.cap - 1e-9 or not any(budget.inflight.values()):
                    counters["stopped"] = True
                    return
                await asyncio.sleep(1)
            sysmsg, mt = system_prompt(t["category"]), R.MAX_TOKENS[t["category"]]
            err = res = None
            for attempt in range(6):
                try:
                    res = await R.call_openai_compat(prov, R.MODELS[name][1], sysmsg, t["prompt"], mt)
                    err = None
                    break
                except Exception as e:  # noqa: BLE001
                    err = f"{type(e).__name__}: {str(e)[:250]}"
                    if not R.is_retriable(e) or attempt == 5:
                        break
                    await asyncio.sleep(min(120, (20 if R.is_rate_limit(e) else 2) * 2 ** attempt) + random.random())
            c = R.cost_usd(name, res["tin"], res["tout"]) if res else 0.0
            rec = make_record(t["id"], name, "fireworks", run_id, raw_text=res["text"] if res else "",
                              tokens_in=res["tin"] if res else None, tokens_out=res["tout"] if res else None,
                              tokens_reasoning=res["treason"] if res else None, latency_ms=res["ms"] if res else None,
                              cost_usd=c, error=err)
            rec["finish_reason"] = res["finish"] if res else None
            rec["max_tokens"] = mt
            async with lock:
                append_answer(STORE, rec)
                budget.finish(name, c)
                counters["n"] += 1
                counters["cost"] += c
                counters["err"] += bool(err)
                counters["trunc"] += (res or {}).get("finish") == "length"
                k = counters.setdefault("k_" + name, [0, 0.0])
                k[0] += 1
                k[1] += c
                budget.mean[name] = k[1] / k[0]
                if counters["n"] % 20 == 0:
                    print(f"[{counters['n']}] errors {counters['err']} truncated {counters['trunc']} spend ${counters['cost']:.4f} "
                          f"(total ${budget.spent:.4f})", flush=True)

    sems = {m: asyncio.Semaphore(R.MODELS[m][3]) for m in MODELS}
    jobs = [one(m, r, t, sems[m]) for r in RUNS for m in MODELS for t in test if (m, t["id"], f"phase6_b_run{r}") not in done]
    print(f"{len(jobs)} calls to make", flush=True)
    await asyncio.gather(*jobs)
    await prov.close()
    print(f"done: {counters['n']} calls, errors {counters['err']}, truncated {counters['trunc']}, this run ${counters['cost']:.4f}, "
          f"Fireworks total in store ${budget.spent:.4f}" + ("  STOPPED by --max-cost" if counters["stopped"] else ""), flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-cost", type=float, default=1.5, help="hard stop for B1+B2 Fireworks spend, USD (router guard is 1.5; phase cap 3)")
    asyncio.run(amain(ap.parse_args(argv)))


if __name__ == "__main__":
    main()
