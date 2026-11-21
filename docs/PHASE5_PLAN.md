# Phase 5 plan: build the router

**Goal:** turn the architecture (`docs/architecture.png`) and the Phase 4 outputs (`routing_policy.json`,
classifiers, solvers, validators) into a working router. It must answer real requests, and it must
behave **exactly** like the policy analysis predicted, so that Phase 6's test numbers mean something.

**Not in Phase 5:** running on the test split (Phase 6), the semantic cache (stays off), Docker packaging.

**Cost:** about $0 (tests use recorded or fake model answers); one live smoke run of ≤ $0.05.

---

## 1. How one request flows

```
request ──► classify (hybrid: rules → MiniLM)        → category, or OUT_OF_SCOPE
        ──► difficulty classifier                    → easy | hard
        ──► policy lookup  routing_policy.json["category|difficulty"]
                → a plan, e.g. [solver, local:gemma3:1b, api:deepseek-v4p1-flash, api:B1]
        ──► run the plan, cheapest step first:
             1. solver      pure-Python parser → LLM-assisted (local translates, Python solves) → defer
             2. local model same system prompt as the benchmark; time budget; validators must pass
             3. paid API    model chosen by the policy; blank / failed / invalid → one retry on the next tier up
        ──► answer + trace (steps tried, model, tokens, cost, latency, why it escalated)
OUT_OF_SCOPE ──► straight to B1
```

The **same per-category system prompts** as the benchmark (`eval/graders/formats.py`) are used, so the
accuracy measured on dev carries over to production.

## 2. Components (new files under `router/`)

| File | What it does |
|---|---|
| `router/config.py` | Settings from env vars: Ollama host, API keys, policy path, prices file, per-category `max_tokens`, reasoning effort (low, D11), local time budget, retry limits |
| `router/policy.py` | Loads and validates `routing_policy.json` (format from `eval/phase4/policy_lib.py`); turns a cell into a plan; a placeholder policy for tests |
| `router/models.py` | One client for every model: local (Ollama), Fireworks and Hyde (OpenAI-compatible), Gemini (AI Studio). Retries, timeouts, token and reasoning-token logging, cost at list price (`eval/model_prices.json`) |
| `router/pipeline.py` | `route(prompt) → Result`: classify → plan → run the steps above, with escalation and a full trace. Never raises: any failure moves to the next step |
| `router/run.py` | Batch CLI: `python -m router.run tasks.json results.json --log run.jsonl`. Local calls one at a time (CPU), API calls in a parallel pool, a global deadline, results written after every task (an early stop still leaves valid output) |
| `src/api/routes.py` | New endpoint `POST /v1/route` returning the answer plus category, layer, model, cost and savings vs B1. The old difficulty-router endpoints stay, marked legacy |
| `router/logging.py` | One JSONL line per request (also written to the existing request-log table) |

Phase 4's files (`classify.py`, `difficulty.py`, `solvers/`, `validators.py`) are used as they are, not edited.

## 3. Tests

1. **Unit:** policy loading and validation, plan building, escalation rules (validator fails → next step; timeout → next step; blank API reply → one retry up), out-of-scope route, cost maths.
2. **End-to-end with fake models:** 16 dev tasks (2 per category) through the whole pipeline, no network.
3. **Replay-consistency test, the most important one:** a "recorded answers" model client serves the real Phase 3 answers. Running the production router over all 240 dev tasks must reproduce Phase 4's cascade-replay accuracy and cost **exactly**. If it doesn't, the router and the analysis disagree, and Phase 6 would measure something different from what was planned.
4. **Live smoke:** 8 dev tasks with real cheap API models (≤ $0.05), to prove the wiring works end to end.

## 4. Order of work

| Step | What |
|---|---|
| 1 | Config, model client, policy loader (placeholder policy) + unit tests |
| 2 | Pipeline with escalation and trace + fake-model end-to-end tests |
| 3 | Batch CLI with deadline and incremental writes |
| 4 | `/v1/route` endpoint + logging + API tests |
| 5 | Replay-consistency test (needs Phase 4's real policy; runs after it lands) |
| 6 | Live smoke run, `eval/results/phase5_report.md` |

**Done when:** all tests pass, the replay reproduces Phase 4's numbers exactly, the smoke run works,
and the CLI can be dropped into a Kaggle notebook for Phase 6.

## 5. Decisions needed from Kabir (defaults in bold)

1. **Where to build:** **its own worktree and branch now, in parallel with Phase 4**, merged into
   `rebuild/hybrid-router` with Kabir's OK once Phase 4 is done. Or wait and build on the same branch after Phase 4.
2. **Local time budget per task:** **30 s** (CPU, 2 threads), then escalate to the API. Shorter saves
   time but sends more work to paid models.
3. **Old endpoints:** **keep the original difficulty-router endpoints, marked legacy**, and add
   `/v1/route`. Or replace them.
4. **Semantic cache:** **off** in the new router (the old project showed its 0.92 threshold serves wrong
   answers; out of scope here). Or include it with the Phase 5 threshold finding.
