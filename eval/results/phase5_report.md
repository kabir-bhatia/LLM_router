# Phase 5 report: the hybrid router

Branch `rebuild/hybrid-router`. Everything here is on the **dev split only**; the test split was never read.
Policy used: `eval/results/phase4/routing_policy.json` (B1 = kimi-k3p1-pro is the reference; escalation and out-of-scope go to B2 = deepseek-v4p1-flash; guardrail run on predicted labels).

## 1. Architecture and request flow

```
request ─► classify  (strong rule → else MiniLM + logistic regression, out-of-scope threshold)   router/labeler.py, classify.py
        ─► difficulty (cheap features + category → easy | hard)                                  router/labeler.py, difficulty.py
        ─► policy lookup  routing_policy.json["category|difficulty"] → plan                      router/policy.py
        ─► run the plan, cheapest step first                                                     router/pipeline.py
             1. solver   (math, logic; when policy.solvers_enabled)
                         pure-Python parser → D13 translator (phi3.5:3.8b math, gemma3:4b logic; local model translates, Python solves) → defer
             2. local    the cell's local model, benchmark system prompt, temperature 0, validators must pass;
                         one 30 s budget shared by the translator and the local model
             3. API      the cell's model; error / blank reply → ONE retry on escalate_to (B2)
        ─► Result: answer, category, difficulty, layer, model, cost, savings vs B1, latency, escalated, full trace
out_of_scope ─► straight to the policy's out_of_scope model (B2)
```

- Same per-category system prompts as the benchmark (`eval/graders/formats.py`); paid models run at low reasoning effort (D11), same output budgets as `eval/run_api.py`; local models use the Phase 3 Kaggle `num_predict` values.
- `route()` never raises: a failed step moves to the next; if every step fails the Result has `error` and an empty answer (`/v1/route` then answers 503).
- A validator failure or a local timeout escalates to the cell's `escalate_to`; an API step is not validated (only an error or blank reply escalates), exactly as in the Phase 4 replay.
- Components: `router/config.py`, `models.py` (Ollama, Fireworks/Hyde, Gemini; retries, timeouts, token + reasoning-token logging, list-price cost), `policy.py`, `labeler.py`, `pipeline.py`, `run.py` (batch CLI), `logging.py` (JSONL), `recorded.py` + `replay_check.py` (replay consistency), `embed_fast.py`, `fakes.py`; `POST /v1/route` in `src/api/routes.py` (old endpoints kept, marked deprecated / legacy).
- Policy path comes from config (`ROUTER_POLICY_PATH` or `--policy`); no cell or model name is hard-coded.

## 2. Tests

| File | Tests | What it covers |
|---|---|---|
| `router/tests/test_phase5_models_policy.py` | 33 | config, cost maths, retries / 429 backoff, no-raise, policy validation and plans |
| `router/tests/test_pipeline.py` | 22 | escalation rules, out-of-scope, solver + translator, time budget, cost, never-raises, **fake-model end-to-end on 16 dev tasks (2 per category)** |
| `router/tests/test_run.py` | 9 | batch CLI: sequential local / parallel API, deadline, incremental writes, resume, one bad task |
| `router/tests/test_replay_consistency.py` | 7 | replay consistency (section 3) |
| `router/tests/test_embed_fast.py` | 1 | in-process MiniLM gives identical classifier outputs |
| `tests/test_route_endpoint.py` | 7 | `/v1/route`, JSONL + request-log table, legacy endpoints marked |

Total: 79 new tests. Whole suite (`tests`, `router`, `eval`): **269 passed, 1 skipped**. No test uses the network.

## 3. Replay consistency (the key check)

`router/replay_check.py` runs the production `Router` over all 240 dev tasks with a **recorded-answers client** (`router/recorded.py`: Phase 3 answers for the local and API models, Phase 4 translator replies), once with the true labels and once with `predicted_labels.json`, and compares each task's path, correctness, cost and model with `policy_lib.replay()` on the same policy. Correctness of a router answer is the Phase 3 graded result of the recorded answer it returned. Raw output: `eval/results/phase5_replay_check.json`.

| Labels | Router accuracy | Router cost | Official `replay()` | Per-task differences |
|---|---|---|---|---|
| true | 97.92% | $0.06415 | 97.92%, $0.06415 | **none** (paths solver 49 / local 82 / escalated 11 / api 98) |
| predicted | 97.92% | $0.08101 | 97.92%, $0.08079 | **1 task**, explained below |

**Predicted labels, the one difference: `code_gen-041`.** The classifier calls it `sentiment`. `replay()` validates a recorded answer with the task's *true* category (code_gen: passes) while the router validates with the category it predicted (sentiment: no `ANSWER:` line, fails) and escalates to B2 for $0.00021. The task is routed by the predicted label in both. With each task's category replaced by the predicted one in the reference replay, **the router matches `replay()` exactly (accuracy, cost $0.08101, every task's path)**. So the router follows the replay; the replay's only simplification is validating with the true category. The headline target from the policy file ($0.0808, 97.9%) is reproduced to within that single task (+$0.0002, accuracy unchanged). This is reported, not tolerated: the test asserts the exact match against the predicted-category reference and allows only label-validator differences, each listed, against the official one.

**Blank-API-reply retry.** The replay does not model "blank / failed API reply → one retry on the next tier"; the check reports any task it affects separately (`blank_api_retry_tasks`). **On dev there are none**: the 11 blank API answers in Phase 3 (nemotron-lightning ×10, minimax-m3p1-flash ×1) belong to models the policy never routes to. The retry stays on in production. A test blanks one recorded API answer and checks it is detected and filed separately from real mismatches.

**What the replay cannot test** (covered by unit tests instead): the 30 s local time budget (recorded latency is reported as 0), live API errors / rate limits, and real translator timing.

## 4. Embeddings for Phase 6

Default (laptop) is unchanged: `router/embeddings.py` reads the on-disk MiniLM cache and runs one subprocess per unseen prompt. New option `--embed inprocess` loads MiniLM once in the process and embeds all prompts up front in batches (`router/embed_fast.py`). On dev prompts the embeddings differ by at most 7e-8 and category, difficulty, path and confidence were identical for 20 of 20 prompts checked (and in the test for 10). Loading plus embedding 20 prompts took about 18 s on this laptop.

## 5. Live smoke run (8 dev tasks, one per category)

Command: `python -m router.run eval/results/phase5/smoke_tasks.json eval/results/phase5/smoke_results.json --log eval/results/phase5/smoke_log.jsonl --api-workers 4`. Real Fireworks and Hyde calls, real classifiers. **Total cost $0.0062** (cap was $0.05), 28 s wall clock. Files: `smoke_results.json`, `smoke_log.jsonl`, `smoke_graded.json` (graded with the Phase 2 graders; the judge for factual / summarisation is Hyde GLM, free).

Ollama is not available on this laptop, so every local step failed with a connection error and **escalated to B2**. That exercised the escalation path and the "local down" fallback; the local steps themselves (and their validators on live output) are exercised on Kaggle in Phase 6. (Because of this, the smoke run is not an estimate of the router's cost.)

| Task | Predicted cell | Layer, model | Trace | Cost | Latency | Correct |
|---|---|---|---|---|---|---|
| fact-010 | factual\|easy (embedding) | api, deepseek-v4p1-flash | local phi3.5 ✗ (no Ollama) → api ✓ | $0.00026 | 11.9 s | yes |
| math-010 | math\|easy (embedding) | api, deepseek-v4p1-flash | solver defers → translator ✗ → local qwen3 ✗ → api ✓ | $0.00012 | 28.4 s | yes |
| sent-002 | sentiment\|hard (rule; true cell easy) | api, deepseek-v4p1-flash | local gemma3 ✗ → api ✓ | $0.00013 | 6.5 s | yes |
| summ-008 | summarisation\|hard (rule; true cell easy) | api, kimi-k3p1-pro | api ✓ (policy sends this cell to B1) | $0.00526 | 6.5 s | yes |
| ner-002 | ner\|easy (embedding) | api, hyde/glm-5.3-flash | api ✓ | $0.00003 | 1.1 s | yes |
| code_debug-004 | code_debug\|easy (rule) | api, deepseek-v4p1-flash | local qwen2.5-coder ✗ → api ✓ | $0.00017 | 13.8 s | yes |
| logic-003 | logic\|easy (rule) | solver, python-solver | pure-Python solver ✓ | $0 | 5 ms | yes |
| code_gen-003 | code_gen\|easy (embedding) | api, deepseek-v4p1-flash | local llama3.2 ✗ → api ✓ | $0.00020 | 17.1 s | yes |

8 of 8 correct. Two difficulty labels (sent-002, summ-008) differ from the dataset's, which is the known ~75% difficulty-classifier accuracy; routing followed the predicted cell as designed.

## 6. Departures from `docs/PHASE5_PLAN.md`

1. **API answers are not validated** (only an error or blank reply escalates). The plan says "blank / failed / invalid"; validating would make the router diverge from the Phase 4 replay.
2. **Out-of-scope prompts** get a neutral system prompt and the largest output budget (there is no benchmark prompt for them).
3. **Local time budget** is shared by the translator and the local model and is counted from each reply's reported latency.
4. **Escalation target** is the policy's `escalate_to` (now B2, per the Phase 4 update); the blank-reply retry also goes to `escalate_to` (the plan's "next tier up" reading).
5. **Savings vs B1** is exact when B1 answered and otherwise an estimate (characters / 4 for the input; answer length + 300 reasoning tokens for the output).
6. **Added beyond the plan:** `--resume` and `--dry-run` on the CLI, `--embed inprocess`, `json_mode` on the model client (the logic translator needs Ollama's JSON format), a recorded-answers client.
7. **Local calls default to CPU-only, 2 threads** (as in the plan); set `ROUTER_LOCAL_CPU_ONLY=0` on a GPU box (e.g. Kaggle) so models run on the GPU.
8. The replay check uses the policy's own guardrail numbers as a cross-check; it follows whichever policy file `ROUTER_POLICY_PATH` points at.

## 7. Running the CLI in a Kaggle notebook (Phase 6)

```python
# 1. install Ollama and pull the local models the policy uses (see notebooks/make_phase3_notebooks.py for the serve/pull helper);
#    pip install httpx sentence-transformers numpy scikit-learn
# 2. put the repo (or a zip of router/, eval/graders/, eval/model_prices.json, the policy file) in /kaggle/working/LLM_Router
# 3. keys as Kaggle secrets -> environment variables (never printed): FIREWORKS_API_KEY, HYDE_API_KEY, HYDE_BASE_URL
import os, subprocess
os.environ["ROUTER_LOCAL_CPU_ONLY"] = "0"        # use the T4 GPU for the local models
os.environ["ROUTER_POLICY_PATH"] = "/kaggle/working/LLM_Router/eval/results/phase4/routing_policy.json"
subprocess.run(["python", "-m", "router.run", "test_tasks.json", "results.json", "--log", "run.jsonl",
                "--embed", "inprocess", "--api-workers", "8", "--deadline-s", "36000", "--resume"],
               cwd="/kaggle/working/LLM_Router", check=True)
```

- `test_tasks.json`: a list of `{"id", "prompt"}`; the router classifies by itself. Output `results.json` is rewritten after every task, so a stopped session leaves valid output; re-run with `--resume` to continue.
- `run.jsonl` has one line per request (category, layer, model, cost, savings, latency, full trace; prompt text is not logged).
- Run the router, B1 and B2 on the same tasks, three times each, then grade with `eval/grade.py` (Phase 6).
