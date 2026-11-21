# Difficulty classifier (easy/hard), dev only

5-fold CV stratified by category x difficulty (seed 20251120), n = 240 (15 easy + 15 hard per category). The true category is given to the model (at run time it comes from the task-type classifier). Labels are the Phase 1 author labels; Phase 3 will show whether 'hard' really is harder for models. Chance = 50%.

| variant | overall | factual | math | sentiment | summarisation | ner | code_debug | logic | code_gen |
|---|---|---|---|---|---|---|---|---|---|
| features + category | 75.4% | 80% | 93% | 53% | 53% | 87% | 73% | 90% | 73% |
| embedding + category | 54.6% | 53% | 67% | 47% | 37% | 67% | 50% | 67% | 50% |
| features + embedding + category | 56.2% | 50% | 77% | 50% | 37% | 60% | 57% | 70% | 50% |
| per-category models, features only | 78.8% | 73% | 93% | 60% | 80% | 90% | 73% | 93% | 67% |
| majority baseline | 50.0% | 50% | 50% | 50% | 50% | 50% | 50% | 50% | 50% |

Per-category cells have n = 30, so each percentage has a 95% interval of roughly +/-17 points; read the overall column, and treat a category as 'predictable' only when it is far above 50%.
