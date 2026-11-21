# Judge decision (Phase 2 step 6, D8 + D10)

40 calibration answers (dev split, factual + summaries, two answering models), hand labels: 29 PASS / 11 FAIL. Judges ran with the D10 rubric (summaries: both core facts + nothing wrong; factual strict + popular-science clarification), blind, low reasoning effort.

## Agreement with the hand labels

| slice | n | GLM (hyde/glm-5.3-flash) | Qwen (qwen3p8-max) |
|---|---|---|---|
| overall | 40 | 37/40 = 92% | 35/40 = 88% |
| category: factual | 20 | 19/20 = 95% | 18/20 = 90% |
| category: summarisation | 20 | 18/20 = 90% | 17/20 = 85% |
| answered by gemma3:1b | 20 | 18/20 = 90% | 16/20 = 80% |
| answered by qwen3:1.7b | 20 | 19/20 = 95% | 19/20 = 95% |
| label PASS | 29 | 26/29 = 90% | 25/29 = 86% |
| label FAIL | 11 | 11/11 = 100% | 10/11 = 91% |

## Disagreements with the labels

- **glm**: 3 wrong (0 too lenient = judge PASS where label FAIL; 3 too strict). Items: 6 (fact-028, gemma3:1b, label PASS), 8 (summ-031, qwen3:1.7b, label PASS), 12 (summ-039, gemma3:1b, label PASS)
- **qwen**: 5 wrong (1 too lenient = judge PASS where label FAIL; 4 too strict). Items: 6 (fact-028, gemma3:1b, label PASS), 8 (summ-031, qwen3:1.7b, label PASS), 12 (summ-039, gemma3:1b, label PASS), 18 (summ-004, gemma3:1b, label PASS), 26 (fact-048, gemma3:1b, label FAIL)
- the two judges agree with each other on 38/40

## Decision (D8 rule)

Rule: keep GLM if agreement >= 90% and no more than 5 points below Qwen. GLM 92.5%, Qwen 87.5% (gap -5.0 points, positive = Qwen better).

**Default judge: GLM (`hyde/glm-5.3-flash`, free)**, except that answers from a GLM model are judged by Qwen so no model grades itself.

Wired as `DEFAULT_JUDGE = "glm"` in `eval/graders/judge.py` and `eval/grade.py` (`--judge default`).

n = 40: one item is 2.5 points, so a gap of a few points is within noise; the rule is applied as written.
