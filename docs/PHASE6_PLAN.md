# Phase 6 plan: the final test on held-out tasks

**Goal:** measure the router, B1 (kimi-k3p1-pro) and B2 (deepseek-v4p1-flash) on the **160 test tasks**,
which no model, policy, classifier or solver decision has seen. These are the project's
reported results.

**Not in Phase 6:** changing the policy, the classifiers, the solvers or the graders after the test split is opened.

**Cost:** about **$1.3 Fireworks** (B1 ≈ $0.88, B2 ≈ $0.16, router ≈ $0.25 incl. the CPU check run); judge = GLM on
Hyde (free). Credit left ≈ $13. Hard cap for the phase: **$3**.

---

## 1. Freeze first (before anything touches the test split)

1. Tag the commit `phase6-frozen`. Record SHA-256 hashes of `routing_policy.json`, `routing_policy_gpu_server.json`,
   the classifier and difficulty model files, `eval/graders/`, `eval/tasks_8cat.json` in `eval/results/phase6/FREEZE.md`.
2. **Bug rule after opening:** only a crash or a wiring bug (not a "this answer was graded wrong" preference) may be
   fixed. Every fix is written in `FREEZE.md` with the reason, and **all** systems are re-run after it, never only the
   affected tasks. Policy, thresholds, prompts and judge rubric cannot change.

## 2. What is run

| System | Where | Runs | What it measures |
|---|---|---|---|
| **Router** (main policy: 8 laptop-class local models + APIs) | Kaggle T4, local models on GPU | 3 | Accuracy, cost, path shares, spread over runs |
| **Router, CPU deployment check** | Kaggle, local models CPU-only, 30 s budget active | 1 | What a CPU-only box really does: on dev, ~4 of 19 local answers in the CPU sample took > 30 s (phi3.5 factual, gemma3:4b hard math), so the GPU run overstates local share |
| **B1** always kimi-k3p1-pro | Laptop (`eval/run_api.py`) | 3 | Reference accuracy and cost |
| **B2** always deepseek-v4p1-flash | Laptop | 3 | The tougher comparison |
| **Router, GPU-server scenario** (`routing_policy_gpu_server.json`) | Kaggle T4 | 1 | Separate "own GPU box" scenario (D1/D11), priced marginal and with hardware |

All use the same per-category system prompts, low reasoning effort (D11), temperature 0. Kaggle receives **prompts and
ids only**, never the gold answers; grading happens on the laptop.

## 3. Grading and statistics

- Same graders and judge as Phase 3 (GLM 5.3 Flash; Qwen for GLM's own factual/summary answers).
- Accuracy with Wilson 95% CI, overall and per category; mean ± spread over the 3 runs (D3).
- **Guardrail re-check on test:** router vs B1, one-sided paired bootstrap, 3-point margin (D12). Reported pass or fail,
  whichever it is. A fail is a result, not something to fix.
- Classifier accuracy on test (task type, difficulty, out-of-scope), solver coverage and precision on test set B + hand
  items (D7), validator catch rate, escalation rate, every wrong answer that came from a local model or a solver.

## 4. Cost reporting

- Savings vs B1 and vs B2, **marginal** (local = $0) and **with hardware** (D5: CPU latency × $0.05/h; GPU tier at
  $0.35/h), from measured tokens at list price.
- **Traffic mixes (D6):** per category, equal mix, "support desk", "developer tools", "analyst"; the range is reported.
- Categories at 0 API cost: the honest "N of 8" count (a category counts only if **every** test
  task in it was answered by a solver or local model, in all 3 runs).

## 5. Outputs

`eval/results/phase6/`: raw answers per system and run, graded files, `FREEZE.md`, `final_report.md` with:
headline table (router / B1 / B2: accuracy, cost, savings), per-category table, traffic-mix table, CPU-check and
GPU-server scenario, guardrail result, classifier/solver/validator numbers, plots (accuracy vs cost; cost by category;
path shares), and a headline summary of the measured numbers.

## 6. Order of work

| Step | What | Who |
|---|---|---|
| 1 | Freeze: tag, hashes, `FREEZE.md` | Claude |
| 2 | Build `notebooks/phase6_router_kaggle.ipynb` (3 GPU runs + CPU check + GPU-server run; test prompts only; keys from Kaggle Secrets; `--resume`) and a test-prompts file | Claude |
| 3 | Run B1 and B2 × 3 on the laptop (≈ $1.0) | Claude |
| 4 | **Add Kaggle Secrets, run the notebook, put the zip in `eval/results/phase6/`** | **Kabir** (≈ 2–3 h of Kaggle time, mostly unattended) |
| 5 | Grade everything, statistics, plots, `final_report.md` | Claude |
| 6 | Review the report together; decide the write-up for Phase 7 | Kabir + Claude |

**Done when:** `final_report.md` exists with the tables above, every number traces to a raw file, and the freeze record
shows nothing was tuned after the test split was opened.

## 7. Decisions needed from Kabir (defaults in bold)

1. **Where the router's API calls run:** **from Kaggle, keys stored as Kaggle Secrets** (one true end-to-end run). Or
   split: Kaggle answers only the local/solver steps, the laptop replays them and makes the API calls (keys never leave
   the laptop, but the router run is stitched together).
2. **CPU deployment check run:** **yes, 1 run** (~1 h of Kaggle CPU time, ≈ $0.07). Or skip and only state the caveat.
3. **GPU-server scenario run:** **yes, 1 run** (~30 min of GPU time, ≈ $0.05). Or skip and keep it a dev-only number.
4. **Runs per system:** **3** (D3). Or 1 to save time and Kaggle hours.
