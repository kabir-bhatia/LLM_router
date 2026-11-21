# Judge decision (Phase 2 step 6, D8 + D10)

40 calibration answers (dev split, factual + summaries, two answering models), hand labels: 29 PASS / 11 FAIL. Judges ran with the D10 rubric (summaries: both core facts + nothing wrong; factual strict + popular-science clarification), blind, low reasoning effort.

## Agreement with the hand labels

| slice | n | GLM (hyde/glm-5.3-flash) | Qwen (qwen3p8-max) |
|---|---|---|---|
| overall | 40 | 33/40 = 82% | 33/40 = 82% |
| category: factual | 20 | 19/20 = 95% | 18/20 = 90% |
| category: summarisation | 20 | 14/20 = 70% | 15/20 = 75% |
| answered by gemma3:1b | 20 | 15/20 = 75% | 15/20 = 75% |
| answered by qwen3:1.7b | 20 | 18/20 = 90% | 18/20 = 90% |
| label PASS | 29 | 22/29 = 76% | 23/29 = 79% |
| label FAIL | 11 | 11/11 = 100% | 10/11 = 91% |

## Disagreements with the labels

- **glm**: 7 wrong (0 too lenient = judge PASS where label FAIL; 7 too strict). Items: 6 (fact-028, gemma3:1b, label PASS), 8 (summ-031, qwen3:1.7b, label PASS), 12 (summ-039, gemma3:1b, label PASS), 13 (summ-013, gemma3:1b, label PASS), 18 (summ-004, gemma3:1b, label PASS), 28 (summ-026, gemma3:1b, label PASS), 30 (summ-036, qwen3:1.7b, label PASS)
- **qwen**: 7 wrong (1 too lenient = judge PASS where label FAIL; 6 too strict). Items: 6 (fact-028, gemma3:1b, label PASS), 8 (summ-031, qwen3:1.7b, label PASS), 12 (summ-039, gemma3:1b, label PASS), 18 (summ-004, gemma3:1b, label PASS), 26 (fact-048, gemma3:1b, label FAIL), 28 (summ-026, gemma3:1b, label PASS), 30 (summ-036, qwen3:1.7b, label PASS)
- the two judges agree with each other on 38/40

## Decision (D8 rule)

Rule: keep GLM if agreement >= 90% and no more than 5 points below Qwen. GLM 82.5%, Qwen 82.5% (gap +0.0 points, positive = Qwen better).

**Default judge: Qwen (`qwen3p8-max`, Fireworks)** for everything.

Wired as `DEFAULT_JUDGE = "qwen"` in `eval/graders/judge.py` and `eval/grade.py` (`--judge default`).

n = 40: one item is 2.5 points, so a gap of a few points is within noise; the rule is applied as written.
