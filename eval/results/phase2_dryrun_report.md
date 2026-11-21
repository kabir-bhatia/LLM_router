# Phase 2 dry run: grader check on real local-model answers

Run: Kaggle T4, `notebooks/phase2_dryrun_kaggle.ipynb`, gemma3:1b and qwen3:1.7b, all 240 **dev** tasks each
(480 answers, 0 call errors), per-category system prompts from `formats.py`, temperature 0.
Answers: `phase2_dryrun/answers_dryrun.jsonl`. Graded with `python -m eval.grade` (scores:
`phase2_dryrun/answers_dryrun_scores.jsonl`, tables: `answers_dryrun_summary.md/.json`). The test split was not touched.

Speed/size: median 83 output tokens and 0.67 s per answer (gemma3:1b); 63 tokens and 0.61 s (qwen3:1.7b, thinking off).
Truncated by `num_predict`: gemma 2 (1 math, 1 logic), qwen 4 (all logic). No `<think>` or `/no_think` text leaked
into any answer (the v2 smoke worry did not recur with `/api/chat`).

## Grader fixes made after inspecting every parse failure and every failed answer

Initially the grader could not parse 5 answers (all qwen3:1.7b NER). I then read **all** failed math, logic, sentiment, NER,
code and constraint-failed summary answers (not only the unparsed ones). Four fixes, each tested in `eval/graders/test_graders.py`:

| # | Problem | Fix | Effect |
|---|---|---|---|
| 1 | qwen3 NER emits the objects without the enclosing list: `{...}, {...}` or `{...}{...}` (ner-001, -004, -007, -017, -037) | `ner_f1.parse_entities` accepts a bare sequence of JSON objects, but only if the text is nothing else (prose around it still fails). Wrong spans/types still score as wrong (ner-007 stays wrong: "Jordan's king"). | qwen NER 16/30 -> 20/30; unparsed 5 -> 0 |
| 2 | `### Final answer:` on one line and `ANSWER: X` on the next: the regex's `\s*` ran across the newline and captured `ANSWER: X` as the value, so correct answers failed (logic-012, -021, -024, -038, -045, -049 for qwen). Also `**Answer:** ANSWER: X`. | `extract_answer_line`: value must be on the same line; a leading `Answer:` inside the value is stripped. | qwen logic 14/30 -> 20/30 (6 wrongly failed answers) |
| 3 | gemma3:1b starts 9 of its summary answers with a lead-in line ("Here's a summary in 3 bullet points:"), which the bullets rule counted as "text outside bullets" (hard fail before the judge) | `constraint.summary_text` drops a one-line lead-in that begins with Here/Sure/Okay/Certainly and ends with ":". Any other prose outside bullets still fails. The Phase 1 test that asserted the opposite was changed accordingly. | gemma bullet summaries now reach the judge instead of failing. **Judgement call, Kabir/parent may veto**: strict reading of "return only the summary" would fail them. |
| 4 | (checked, no change) | Code answers arrive with or without a ```python fence; the extractor handles both. No fenced-code, `\boxed`, thousands-separator (`12,408`, `1872.50`) or currency problems found. | - |

Not grader problems (checked and left alone): model errors in math (wrong arithmetic or reasoning, 3 qwen / 15 gemma), logic
(wrong name; truncated reasoning in 4 qwen + 1 gemma), sentiment (mixed called negative/neutral), NER (extra entities such as
"Jordan's king", wrong type, repetition loop in gemma ner-004), code (real bugs: e.g. `remove_vowels` ignoring case,
`c * 5 / 9 + 32`), summaries that exceed the word limit (1 gemma and 7 qwen answers broke the word limit).
The fallback paths were rare: 3 math answers used "last number" fallback (all truncated or wrong anyway); logic fallback
cases were all truncated runs.

## Results after the fixes (dev split, 30 tasks per category, Wilson 95% CI)

| category | gemma3:1b all | qwen3:1.7b all |
|---|---|---|
| math | 15/30 = 50% [33-67] | 27/30 = 90% [74-97] |
| sentiment | 24/30 = 80% [63-90] | 27/30 = 90% [74-97] |
| ner | 22/30 = 73% [56-86] | 20/30 = 67% [49-81] |
| code_debug | 14/30 = 47% [30-64] | 22/30 = 73% [56-86] |
| logic | 12/30 = 40% [25-58] | 20/30 = 67% [49-81] |
| code_gen | 20/30 = 67% [49-81] | 18/30 = 60% [42-75] |
| factual | 22/30 = 73% [56-86] | 23/30 = 77% [59-88] |
| summarisation | 12/30 = 40% [25-58] | 10/30 = 33% [19-51] |

Easy/hard splits are in `phase2_dryrun/answers_dryrun_summary.md`. Per-cell n is only 15, so these are for sanity, not conclusions.
(Qwen3:1.7b math/sentiment at 90% already clears the D4 80% floor on this tiny sample; the real benchmark decides.)

## Update after the judge decision (D10, round 2 core facts, GLM default judge)

Before: factual and summarisation were `pending` (no judge yet); the six deterministic categories above are unchanged by D10.
After (judge = GLM `hyde/glm-5.3-flash` via `--judge default`, blind, D10 rubric, graded on dev; Fireworks spend for this re-grade $0):

| category | gemma3:1b before -> after | qwen3:1.7b before -> after |
|---|---|---|
| factual | pending -> 22/30 = 73% | pending -> 23/30 = 77% |
| summarisation | pending -> 12/30 = 40% | pending -> 10/30 = 33% |
| the other six | unchanged | unchanged |

Summary failures are mostly definite (word/sentence/bullet limit broken, 1 language fail) rather than judge verdicts. Language check (D10, all categories, code): caught **1 of 480**
dry-run answers: summ-038 by qwen3:1.7b (a stray Chinese character "镑" for "pounds"); none from gemma3:1b. Judge decision and both calibration rounds:
`judge_decision.md` (GLM 92.5% vs hand labels, Qwen 87.5%; round 1 with coarse core facts gave 82.5% for both and was replaced). Per-cell n is 15, so for sanity only.

## Observations worth keeping

- The graders now see real model output of both styles: markdown reasoning with a final `ANSWER:` line, bare code without fences, JSON in fences.
- Both models follow the output format well except for the quirks above, so no further extractor changes are expected before Phase 3, but the 14
  other local models and the API models will bring new quirks: re-check "could not parse" per model after each Phase 3 run (`grade.py` prints it).
- Summary word limits are the main source of definite summary failures for qwen (long answers under tight limits).
- Qwen3 with thinking off still gets the logic puzzles it finishes mostly right; 4 logic answers were cut off at 768 tokens. Phase 3 may want a higher `num_predict` for logic.

## Suggested decision changes (for the parent session; DESIGN_DECISIONS.md not edited)
- None required. Possible note under D3/D8: grader fixes are made only against **dev** answers, and each fix is recorded with a test.
