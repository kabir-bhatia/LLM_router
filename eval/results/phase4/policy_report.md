# Phase 4 policy report (dev split only, 240 tasks, API spend $0 - all numbers are replays of Phase 3 answers)

## Baselines (D2, D12)

- **B1** = kimi-k3p1-pro: accuracy 99.2%, cost $0.4408 on the 240 dev tasks (most accurate API model on the dev tasks; ties go to the cheaper).
- **B2** = deepseek-v4p1-flash: accuracy 98.8%, cost $0.0821; lower bound of (B2 - B1) = -0.021 (passes the 3-point test). D12: cheapest single API model at most 3 points worse than B1 at 95% confidence (one-sided paired bootstrap over all 240 dev tasks).

## Labels used in the replay

The router sees the classifiers' guesses in production, so the **official** replay and the guardrail use out-of-fold predicted labels: the category comes from the 5-fold CV hybrid task-type classifier and the difficulty from the fold's difficulty model (`predicted_labels.json`, written by `eval_difficulty.py`; every task is predicted by a model that did not train on it). The cell rule itself is derived on the true labels. Replays with the true labels are shown for reference only. A task predicted out-of-scope goes straight to B1.

## Main router: 8 laptop-class local models + APIs (GPU-server models excluded, D1/D11)

Local options: gemma3:1b, gemma3:4b, granite4:350m, llama3.2:1b, llama3.2:3b, phi3.5:3.8b, qwen2.5-coder:1.5b, qwen3:1.7b.

| policy | accuracy | cost (USD) | vs B1 cost | vs B2 cost | solver / local / escalated / API |
|---|---|---|---|---|---|
| always B1 | 99.2% | 0.4408 | 1.00x | 5.37x | - |
| always B2 | 98.8% | 0.0821 | 0.19x | 1.00x | - |
| specified policy (`raw`), predicted labels (official), solvers on | 97.9% | 0.0808 | 0.18x | 0.98x | 45 / 78 / 11 / 106 |
| specified policy (`raw`), predicted labels (official), solvers off | 97.9% | 0.0849 | 0.19x | 1.03x | 0 / 101 / 11 / 128 |
| specified policy (`raw`), true labels (reference), solvers on | 97.9% | 0.0641 | 0.15x | 0.78x | 49 / 82 / 11 / 98 |
| cascade variant, predicted labels (official), solvers on | 97.9% | 0.0862 | 0.20x | 1.05x | 45 / 66 / 42 / 87 |
| cascade variant, predicted labels (official), solvers off | 97.5% | 0.0924 | 0.21x | 1.13x | 0 / 85 / 56 / 99 |
| cascade variant, true labels (reference), solvers on | 97.5% | 0.0683 | 0.16x | 0.83x | 49 / 77 / 35 / 79 |

**Savings, specified policy, predicted labels:** 81.7% cheaper than B1 ($0.3601 on the 240 tasks), +1.6% vs B2 (positive = cheaper than B2, negative = dearer); accuracy -1.3% vs B1, -0.8% vs B2.

**Who answers (specified policy, predicted labels):** solvers 45 (19%), local models 78 (32%), escalated to B2 after a validator rejection 11 (5%), routed straight to an API model 106 (44%). So 51% of the tasks are answered without any paid call.

**Escalation target (D12 update, 2026-11-21):** validator-rejected local answers and out-of-scope prompts go to B2, not B1 (with B1 as escalation target the router cost more than always-B2). B1 stays the reference of the guardrail and the top of every cell's ladder, so cells can still be handed back to B1.

`raw` = D12 cell rule on each option's own dev accuracy (the specified policy). `cascade` = same rule but local options are judged by their accuracy *with* validators and escalation, a variant for comparison.

### Policy table, specified policy (`routing_policy.json`)

Guardrail (D12, replayed on the out-of-fold predicted labels): router at most 3 points worse than B1 at 95%, one-sided paired bootstrap over 240 tasks. **Final: PASSED** - router 97.9% vs B1 99.2%, lower bound of the difference -0.029. Solvers enabled: True.

| cell | model | kind | n | B1 misses | reason (cell rule on true labels) |
|---|---|---|---|---|---|
| code_debug|easy | qwen2.5-coder:1.5b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| code_debug|hard | hyde/glm-5.3-flash | api | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| code_gen|easy | llama3.2:3b | local | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| code_gen|hard | gpt-oss-120b | api | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from hyde/glm-5.3-flash to gpt-oss-120b (cell loss vs B1: 1 tasks) |
| factual|easy | phi3.5:3.8b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from gemma3:1b to gemma3:4b (cell loss vs B1: 3 tasks); HANDED BACK by the guardrail from gemma3:4b to phi3.5:3.8b (cell loss vs B1: 2 tasks) |
| factual|hard | phi3.5:3.8b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| logic|easy | hyde/glm-5.3-flash | api | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| logic|hard | gpt-oss-120b | api | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| math|easy | qwen3:1.7b | local | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| math|hard | gemma3:4b | local | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| ner|easy | hyde/glm-5.3-flash | api | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from gemma3:4b to hyde/glm-5.3-flash (cell loss vs B1: 1 tasks) |
| ner|hard | hyde/glm-5.3-flash | api | 15 | 1 | accuracy 93% (1 misses of 15) vs B1 1 misses; rule: at most 2 misses and >= 80% |
| sentiment|easy | llama3.2:3b | local | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from qwen3:1.7b to llama3.2:3b (cell loss vs B1: 1 tasks) |
| sentiment|hard | gemma3:4b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from llama3.2:3b to gemma3:4b (cell loss vs B1: 1 tasks) |
| summarisation|easy | deepseek-v4p1-flash | api | 15 | 1 | accuracy 93% (1 misses of 15) vs B1 1 misses; rule: at most 2 misses and >= 80% |
| summarisation|hard | kimi-k3p1-pro | api | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from deepseek-v4p1-flash to kimi-k3p1-pro (cell loss vs B1: 1 tasks) |
| out of scope | deepseek-v4p1-flash | api | | | D9: no category fits -> straight to the fallback model (B2) |

Guardrail log (every step):

| step | action | passed | lower bound | router acc |
|---|---|---|---|---|
| 0 | initial policy | False | -0.071 | 94.6% |
| 1 | hand back factual|easy: gemma3:1b -> gemma3:4b | False | -0.067 | 95.0% |
| 2 | hand back factual|easy: gemma3:4b -> phi3.5:3.8b | False | -0.058 | 95.8% |
| 3 | hand back summarisation|hard: deepseek-v4p1-flash -> kimi-k3p1-pro | False | -0.054 | 96.2% |
| 4 | hand back sentiment|easy: qwen3:1.7b -> llama3.2:3b | False | -0.046 | 96.7% |
| 5 | hand back ner|easy: gemma3:4b -> hyde/glm-5.3-flash | False | -0.042 | 97.1% |
| 6 | hand back code_gen|hard: hyde/glm-5.3-flash -> gpt-oss-120b | False | -0.037 | 97.5% |
| 7 | hand back sentiment|hard: llama3.2:3b -> gemma3:4b | True | -0.029 | 97.9% |

Cells handed back: code_gen|hard, factual|easy, ner|easy, sentiment|easy, sentiment|hard, summarisation|hard.

### Policy table, cascade variant (`routing_policy_cascade.json`)

Guardrail (D12, replayed on the out-of-fold predicted labels): router at most 3 points worse than B1 at 95%, one-sided paired bootstrap over 240 tasks. **Final: PASSED** - router 97.9% vs B1 99.2%, lower bound of the difference -0.029. Solvers enabled: True.

| cell | model | kind | n | B1 misses | reason (cell rule on true labels) |
|---|---|---|---|---|---|
| code_debug|easy | qwen2.5-coder:1.5b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| code_debug|hard | hyde/glm-5.3-flash | api | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| code_gen|easy | llama3.2:3b | local | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| code_gen|hard | gpt-oss-120b | api | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from hyde/glm-5.3-flash to gpt-oss-120b (cell loss vs B1: 1 tasks) |
| factual|easy | phi3.5:3.8b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from gemma3:1b to gemma3:4b (cell loss vs B1: 3 tasks); HANDED BACK by the guardrail from gemma3:4b to phi3.5:3.8b (cell loss vs B1: 2 tasks) |
| factual|hard | gpt-oss-120b | api | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from phi3.5:3.8b to hyde/glm-5.3-flash (cell loss vs B1: 1 tasks); HANDED BACK by the guardrail from hyde/glm-5.3-flash to gpt-oss-120b (cell loss vs B1: 1 tasks) |
| logic|easy | phi3.5:3.8b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| logic|hard | gpt-oss-120b | api | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| math|easy | qwen3:1.7b | local | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| math|hard | granite4:350m | local | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| ner|easy | granite4:350m | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| ner|hard | gemma3:4b | local | 15 | 1 | accuracy 87% (2 misses of 15) vs B1 1 misses; rule: at most 2 misses and >= 80%; HANDED BACK by the guardrail from granite4:350m to llama3.2:1b (cell loss vs B1: 2 tasks); HANDED BACK by the guardrail from llama3.2:1b to gemma3:4b (cell loss vs B1: 1 tasks) |
| sentiment|easy | qwen2.5-coder:1.5b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| sentiment|hard | gemma3:4b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from qwen2.5-coder:1.5b to llama3.2:1b (cell loss vs B1: 2 tasks); HANDED BACK by the guardrail from llama3.2:1b to llama3.2:3b (cell loss vs B1: 3 tasks); HANDED BACK by the guardrail from llama3.2:3b to gemma3:4b (cell loss vs B1: 1 tasks) |
| summarisation|easy | deepseek-v4p1-flash | api | 15 | 1 | accuracy 93% (1 misses of 15) vs B1 1 misses; rule: at most 2 misses and >= 80% |
| summarisation|hard | kimi-k3p1-pro | api | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from deepseek-v4p1-flash to kimi-k3p1-pro (cell loss vs B1: 1 tasks) |
| out of scope | deepseek-v4p1-flash | api | | | D9: no category fits -> straight to the fallback model (B2) |

Guardrail log (every step):

| step | action | passed | lower bound | router acc |
|---|---|---|---|---|
| 0 | initial policy | False | -0.079 | 93.8% |
| 1 | hand back factual|easy: gemma3:1b -> gemma3:4b | False | -0.075 | 94.2% |
| 2 | hand back ner|hard: granite4:350m -> llama3.2:1b | False | -0.071 | 94.6% |
| 3 | hand back sentiment|hard: qwen2.5-coder:1.5b -> llama3.2:1b | False | -0.079 | 94.2% |
| 4 | hand back sentiment|hard: llama3.2:1b -> llama3.2:3b | False | -0.067 | 95.0% |
| 5 | hand back factual|easy: gemma3:4b -> phi3.5:3.8b | False | -0.058 | 95.8% |
| 6 | hand back summarisation|hard: deepseek-v4p1-flash -> kimi-k3p1-pro | False | -0.054 | 96.2% |
| 7 | hand back ner|hard: llama3.2:1b -> gemma3:4b | False | -0.046 | 96.7% |
| 8 | hand back code_gen|hard: hyde/glm-5.3-flash -> gpt-oss-120b | False | -0.037 | 97.1% |
| 9 | hand back sentiment|hard: llama3.2:3b -> gemma3:4b | False | -0.033 | 97.5% |
| 10 | hand back factual|hard: phi3.5:3.8b -> hyde/glm-5.3-flash | False | -0.033 | 97.5% |
| 11 | hand back factual|hard: hyde/glm-5.3-flash -> gpt-oss-120b | True | -0.029 | 97.9% |

Cells handed back: code_gen|hard, factual|easy, factual|hard, ner|hard, sentiment|hard, summarisation|hard.

## Separate scenario: self-hosted GPU-server tier (gemma3:12b, phi4:14b, qwen2.5:14b)

These three models are not part of the 16 (D1/D11). This scenario answers 'what if the company runs a GPU box?': the same policy search with them added as local options. Priced two ways (D5): **marginal $0** per local answer (the `cost` column) and **with hardware** = measured latency x $0.35/h (T4 instance), added for every attempt a GPU-tier model makes (including attempts that are then escalated). Guardrail on predicted labels as above.

| policy | accuracy | API cost, marginal $0 | + GPU hardware | total with hardware | total vs B1 | total vs B2 | solver / local / escalated / API |
|---|---|---|---|---|---|---|---|
| specified policy (`raw`), predicted labels (official) | 97.9% | 0.0787 | 0.0196 | 0.0983 | 0.22x | 1.20x | 45 / 125 / 11 / 59 |
| specified policy (`raw`), true labels (reference) | 97.5% | 0.0621 | 0.0187 | 0.0808 | 0.18x | 0.98x | 49 / 127 / 11 / 53 |
| cascade variant, predicted labels (official) | 97.9% | 0.0755 | 0.0286 | 0.1041 | 0.24x | 1.27x | 45 / 107 / 45 / 43 |
| cascade variant, true labels (reference) | 97.1% | 0.0585 | 0.0267 | 0.0851 | 0.19x | 1.04x | 49 / 116 / 41 / 34 |

Hardware cost counts only the latency of the three GPU-tier answers actually used in the replay; it ignores idle time, which a real server would also pay for.

### GPU-server policy table, specified policy (`routing_policy_gpu_server.json`)

Guardrail (D12, replayed on the out-of-fold predicted labels): router at most 3 points worse than B1 at 95%, one-sided paired bootstrap over 240 tasks. **Final: PASSED** - router 97.9% vs B1 99.2%, lower bound of the difference -0.029. Solvers enabled: True.

| cell | model | kind | n | B1 misses | reason (cell rule on true labels) |
|---|---|---|---|---|---|
| code_debug|easy | qwen2.5-coder:1.5b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| code_debug|hard | phi4:14b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from gemma3:12b to phi4:14b (cell loss vs B1: 1 tasks) |
| code_gen|easy | llama3.2:3b | local | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| code_gen|hard | gpt-oss-120b | api | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from qwen2.5:14b to phi4:14b (cell loss vs B1: 2 tasks); HANDED BACK by the guardrail from phi4:14b to hyde/glm-5.3-flash (cell loss vs B1: 1 tasks); HANDED BACK by the guardrail from hyde/glm-5.3-flash to gpt-oss-120b (cell loss vs B1: 1 tasks) |
| factual|easy | phi3.5:3.8b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from gemma3:1b to gemma3:4b (cell loss vs B1: 3 tasks); HANDED BACK by the guardrail from gemma3:4b to phi3.5:3.8b (cell loss vs B1: 2 tasks) |
| factual|hard | phi3.5:3.8b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| logic|easy | hyde/glm-5.3-flash | api | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| logic|hard | gpt-oss-120b | api | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| math|easy | qwen3:1.7b | local | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| math|hard | gemma3:4b | local | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| ner|easy | gemma3:12b | local | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from gemma3:4b to qwen2.5:14b (cell loss vs B1: 1 tasks); HANDED BACK by the guardrail from qwen2.5:14b to gemma3:12b (cell loss vs B1: 1 tasks) |
| ner|hard | qwen2.5:14b | local | 15 | 1 | accuracy 87% (2 misses of 15) vs B1 1 misses; rule: at most 2 misses and >= 80% |
| sentiment|easy | llama3.2:3b | local | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from qwen3:1.7b to llama3.2:3b (cell loss vs B1: 1 tasks) |
| sentiment|hard | gemma3:4b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from llama3.2:3b to gemma3:4b (cell loss vs B1: 1 tasks) |
| summarisation|easy | deepseek-v4p1-flash | api | 15 | 1 | accuracy 93% (1 misses of 15) vs B1 1 misses; rule: at most 2 misses and >= 80% |
| summarisation|hard | kimi-k3p1-pro | api | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from deepseek-v4p1-flash to kimi-k3p1-pro (cell loss vs B1: 1 tasks) |
| out of scope | deepseek-v4p1-flash | api | | | D9: no category fits -> straight to the fallback model (B2) |

Guardrail log (every step):

| step | action | passed | lower bound | router acc |
|---|---|---|---|---|
| 0 | initial policy | False | -0.083 | 93.8% |
| 1 | hand back factual|easy: gemma3:1b -> gemma3:4b | False | -0.079 | 94.2% |
| 2 | hand back code_gen|hard: qwen2.5:14b -> phi4:14b | False | -0.071 | 94.6% |
| 3 | hand back factual|easy: gemma3:4b -> phi3.5:3.8b | False | -0.062 | 95.4% |
| 4 | hand back summarisation|hard: deepseek-v4p1-flash -> kimi-k3p1-pro | False | -0.058 | 95.8% |
| 5 | hand back sentiment|easy: qwen3:1.7b -> llama3.2:3b | False | -0.054 | 96.2% |
| 6 | hand back code_debug|hard: gemma3:12b -> phi4:14b | False | -0.046 | 96.7% |
| 7 | hand back ner|easy: gemma3:4b -> qwen2.5:14b | False | -0.046 | 96.7% |
| 8 | hand back ner|easy: qwen2.5:14b -> gemma3:12b | False | -0.042 | 97.1% |
| 9 | hand back code_gen|hard: phi4:14b -> hyde/glm-5.3-flash | False | -0.042 | 97.1% |
| 10 | hand back code_gen|hard: hyde/glm-5.3-flash -> gpt-oss-120b | False | -0.037 | 97.5% |
| 11 | hand back sentiment|hard: llama3.2:3b -> gemma3:4b | True | -0.029 | 97.9% |

Cells handed back: code_debug|hard, code_gen|hard, factual|easy, ner|easy, sentiment|easy, sentiment|hard, summarisation|hard.

### GPU-server policy table, cascade variant (`routing_policy_gpu_server_cascade.json`)

Guardrail (D12, replayed on the out-of-fold predicted labels): router at most 3 points worse than B1 at 95%, one-sided paired bootstrap over 240 tasks. **Final: PASSED** - router 97.9% vs B1 99.2%, lower bound of the difference -0.029. Solvers enabled: True.

| cell | model | kind | n | B1 misses | reason (cell rule on true labels) |
|---|---|---|---|---|---|
| code_debug|easy | qwen2.5-coder:1.5b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| code_debug|hard | phi4:14b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from gemma3:12b to phi4:14b (cell loss vs B1: 1 tasks) |
| code_gen|easy | llama3.2:3b | local | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| code_gen|hard | gpt-oss-120b | api | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from qwen2.5:14b to phi4:14b (cell loss vs B1: 2 tasks); HANDED BACK by the guardrail from phi4:14b to hyde/glm-5.3-flash (cell loss vs B1: 1 tasks); HANDED BACK by the guardrail from hyde/glm-5.3-flash to gpt-oss-120b (cell loss vs B1: 1 tasks) |
| factual|easy | phi3.5:3.8b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from gemma3:1b to gemma3:4b (cell loss vs B1: 3 tasks); HANDED BACK by the guardrail from gemma3:4b to phi3.5:3.8b (cell loss vs B1: 2 tasks) |
| factual|hard | gemma3:12b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from phi3.5:3.8b to gemma3:12b (cell loss vs B1: 1 tasks) |
| logic|easy | phi3.5:3.8b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| logic|hard | gpt-oss-120b | api | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| math|easy | qwen3:1.7b | local | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| math|hard | granite4:350m | local | 15 | 0 | accuracy 100% (0 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| ner|easy | granite4:350m | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| ner|hard | gemma3:4b | local | 15 | 1 | accuracy 87% (2 misses of 15) vs B1 1 misses; rule: at most 2 misses and >= 80%; HANDED BACK by the guardrail from granite4:350m to llama3.2:1b (cell loss vs B1: 2 tasks); HANDED BACK by the guardrail from llama3.2:1b to gemma3:4b (cell loss vs B1: 1 tasks) |
| sentiment|easy | qwen2.5-coder:1.5b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80% |
| sentiment|hard | gemma3:4b | local | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from qwen2.5-coder:1.5b to llama3.2:1b (cell loss vs B1: 2 tasks); HANDED BACK by the guardrail from llama3.2:1b to llama3.2:3b (cell loss vs B1: 3 tasks); HANDED BACK by the guardrail from llama3.2:3b to gemma3:4b (cell loss vs B1: 1 tasks) |
| summarisation|easy | phi4:14b | local | 15 | 1 | accuracy 87% (2 misses of 15) vs B1 1 misses; rule: at most 2 misses and >= 80% |
| summarisation|hard | kimi-k3p1-pro | api | 15 | 0 | accuracy 93% (1 misses of 15) vs B1 0 misses; rule: at most 1 misses and >= 80%; HANDED BACK by the guardrail from deepseek-v4p1-flash to kimi-k3p1-pro (cell loss vs B1: 1 tasks) |
| out of scope | deepseek-v4p1-flash | api | | | D9: no category fits -> straight to the fallback model (B2) |

Guardrail log (every step):

| step | action | passed | lower bound | router acc |
|---|---|---|---|---|
| 0 | initial policy | False | -0.092 | 92.9% |
| 1 | hand back factual|easy: gemma3:1b -> gemma3:4b | False | -0.087 | 93.3% |
| 2 | hand back ner|hard: granite4:350m -> llama3.2:1b | False | -0.083 | 93.8% |
| 3 | hand back code_gen|hard: qwen2.5:14b -> phi4:14b | False | -0.079 | 94.2% |
| 4 | hand back sentiment|hard: qwen2.5-coder:1.5b -> llama3.2:1b | False | -0.083 | 93.8% |
| 5 | hand back sentiment|hard: llama3.2:1b -> llama3.2:3b | False | -0.071 | 94.6% |
| 6 | hand back factual|easy: gemma3:4b -> phi3.5:3.8b | False | -0.062 | 95.4% |
| 7 | hand back summarisation|hard: deepseek-v4p1-flash -> kimi-k3p1-pro | False | -0.058 | 95.8% |
| 8 | hand back code_debug|hard: gemma3:12b -> phi4:14b | False | -0.054 | 96.2% |
| 9 | hand back ner|hard: llama3.2:1b -> gemma3:4b | False | -0.046 | 96.7% |
| 10 | hand back code_gen|hard: phi4:14b -> hyde/glm-5.3-flash | False | -0.046 | 96.7% |
| 11 | hand back code_gen|hard: hyde/glm-5.3-flash -> gpt-oss-120b | False | -0.037 | 97.1% |
| 12 | hand back sentiment|hard: llama3.2:3b -> gemma3:4b | False | -0.033 | 97.5% |
| 13 | hand back factual|hard: phi3.5:3.8b -> gemma3:12b | True | -0.029 | 97.9% |

Cells handed back: code_debug|hard, code_gen|hard, factual|easy, factual|hard, ner|hard, sentiment|hard, summarisation|hard.

## Solvers (see solver_report.md, translator_report.md)

- Pure-Python solvers: 22/22 set-A dev tasks per category, 100% precision, 0% coverage on the unseen B + hand items (D13 was adopted for that reason).
- D13 translators (dev math + logic, 5 local models): chosen math = phi3.5:3.8b, logic = gemma3:4b (precision 100% on the answered dev items). Combined path (pure-Python first, translator when it defers) answers 27/30 math and 22/30 logic dev items with no wrong answer. Unseen logic B + hand stays at 0/8 answered with the chosen translator; unseen math gains 5/8. Several non-chosen translators gave wrong answers that passed the gates (e.g. gemma3:1b math 11/21 correct), so the gates alone do not guarantee precision; selection on precision is what protects the router. Selection used all 30 dev items per category, so these figures are optimistic until the Phase 6 test split.

## Classifiers (see classifier_report.md, difficulty_report.md)

- Task type, 5-fold CV on dev: rules 69.6%, MiniLM embeddings + logistic regression 96.7%, hybrid (default) 96.7%, LLM (free GLM) 99.6%.
- Difficulty classifier: 75.4%. Predicted labels differ from the true ones on 8 tasks (category) and 62 tasks (difficulty) out of 240.
- Out-of-scope detection and validator results are in classifier_report.md and validator_check.md.

## Power analysis

See power_analysis.md. D12 was adopted because the original per-cell bootstrap test had very low power at n = 15/30; the cell rule is now a count rule and the statistical guarantee is the whole-router guardrail above.

## Caveats

- Everything is measured on the dev split that was also used to choose the routes; the guardrail's confidence is for the dev tasks, not a promise for new tasks. The held-out test split in Phase 6 is the real check.
- Cells have 15 tasks; one task is 6.7 points inside a cell.
