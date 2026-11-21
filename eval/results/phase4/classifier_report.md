# Task-type classifier comparison (dev only)

240 in-scope dev prompts, 5-fold stratified CV (seed 20251120) + 30 out-of-scope prompts (`eval/phase4/oos_prompts.json`, written fresh; never trained on, never used to pick a threshold). Rules were hand-written (not learned), so they are NOT cross-validated and are somewhat optimistic: the author had seen some dev prompts (math/logic set A, summary prompts) when writing them. Embedding OOS threshold = the 5th percentile of the top class probability on in-scope training prompts (inner CV), i.e. at most ~5% of in-scope prompts are sent to B1 needlessly.

| classifier | in-scope accuracy | in-scope wrongly flagged OOS | OOS prompts flagged (of 30) | latency per prompt | cost per 1000 prompts |
|---|---|---|---|---|---|
| (a) rules | 69.6% (abstains on 22%; 88.8% when it fires) | 0.0% | 80% | 177 µs | $0 |
| (b) MiniLM + LR | 96.7% (99.2% before the OOS threshold) | 3.3% | 67% | 41 ms (laptop CPU) | $0 |
| (c) hybrid: rule then embedding | 96.7% | 2.1% | 95% | 20 ms avg | $0 |
| (d) LLM (glm-5.3-flash, zero-shot) | 99.6% | 0.4% | 100% | 1409 ms | $0.041 at market price (257 in / 4 out tokens per call; actual $0 via Hyde) |

Hybrid: 52% of dev prompts decided by a strong rule (accuracy 97.6%); the rest by the embedding model (accuracy 95.7%).
Rules alone: strong rules fire on 52% of prompts with 97.6% accuracy; any rule 78% at 88.8%.
LLM failed calls: 0 (counted as out_of_scope).

## Accuracy per category

| category | rules | embedding | hybrid | LLM |
|---|---|---|---|---|
| factual | 73% | 93% | 93% | 100% |
| math | 80% | 93% | 87% | 100% |
| sentiment | 100% | 100% | 100% | 97% |
| summarisation | 100% | 93% | 100% | 100% |
| ner | 7% | 100% | 100% | 100% |
| code_debug | 67% | 97% | 100% | 100% |
| logic | 73% | 97% | 97% | 100% |
| code_gen | 57% | 100% | 97% | 100% |

## Confusion matrix: rules (rows true, columns predicted; dev in-scope only; rule abstentions appear in the out_of_scope column)

| true \ pred | factua | math | sentim | summar | ner | code_d | logic | code_g | out_of |
|---|---|---|---|---|---|---|---|---|---|
| factual | 22 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| math | 0 | 24 | 0 | 2 | 0 | 0 | 0 | 0 | 4 |
| sentiment | 0 | 0 | 30 | 0 | 0 | 0 | 0 | 0 | 0 |
| summarisation | 0 | 0 | 0 | 30 | 0 | 0 | 0 | 0 | 0 |
| ner | 16 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 12 |
| code_debug | 0 | 2 | 0 | 0 | 0 | 20 | 0 | 0 | 8 |
| logic | 0 | 0 | 0 | 0 | 0 | 0 | 22 | 0 | 8 |
| code_gen | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 17 | 12 |
| out_of_scope | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Confusion matrix: embedding (rows true, columns predicted; dev in-scope only)

| true \ pred | factua | math | sentim | summar | ner | code_d | logic | code_g | out_of |
|---|---|---|---|---|---|---|---|---|---|
| factual | 28 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| math | 0 | 28 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| sentiment | 0 | 0 | 30 | 0 | 0 | 0 | 0 | 0 | 0 |
| summarisation | 0 | 0 | 0 | 28 | 0 | 0 | 0 | 0 | 2 |
| ner | 0 | 0 | 0 | 0 | 30 | 0 | 0 | 0 | 0 |
| code_debug | 0 | 0 | 0 | 0 | 0 | 29 | 0 | 0 | 1 |
| logic | 0 | 0 | 0 | 0 | 0 | 0 | 29 | 0 | 1 |
| code_gen | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 30 | 0 |
| out_of_scope | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Confusion matrix: hybrid (rows true, columns predicted; dev in-scope only)

| true \ pred | factua | math | sentim | summar | ner | code_d | logic | code_g | out_of |
|---|---|---|---|---|---|---|---|---|---|
| factual | 28 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| math | 0 | 26 | 0 | 2 | 0 | 0 | 0 | 0 | 2 |
| sentiment | 0 | 0 | 30 | 0 | 0 | 0 | 0 | 0 | 0 |
| summarisation | 0 | 0 | 0 | 30 | 0 | 0 | 0 | 0 | 0 |
| ner | 0 | 0 | 0 | 0 | 30 | 0 | 0 | 0 | 0 |
| code_debug | 0 | 0 | 0 | 0 | 0 | 30 | 0 | 0 | 0 |
| logic | 0 | 0 | 0 | 0 | 0 | 0 | 29 | 0 | 1 |
| code_gen | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 29 | 0 |
| out_of_scope | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Confusion matrix: llm (rows true, columns predicted; dev in-scope only)

| true \ pred | factua | math | sentim | summar | ner | code_d | logic | code_g | out_of |
|---|---|---|---|---|---|---|---|---|---|
| factual | 30 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| math | 0 | 30 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| sentiment | 0 | 0 | 29 | 0 | 0 | 0 | 0 | 0 | 1 |
| summarisation | 0 | 0 | 0 | 30 | 0 | 0 | 0 | 0 | 0 |
| ner | 0 | 0 | 0 | 0 | 30 | 0 | 0 | 0 | 0 |
| code_debug | 0 | 0 | 0 | 0 | 0 | 30 | 0 | 0 | 0 |
| logic | 0 | 0 | 0 | 0 | 0 | 0 | 30 | 0 | 0 |
| code_gen | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 30 | 0 |
| out_of_scope | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
