# D13 translator evaluation (dev only)

Local model translates (math: one expression; logic: JSON spec), Python solves with the safe evaluator / brute force and answers only when every self-gate passes. Prompts and parsers were developed on set A only (D7); **B + hand are the unseen items (8 per category, so intervals are wide)**. Cells: answered/n (coverage); correct/answered = precision [Wilson 95%].

## math

| translator | set A (built on) | B + hand (unseen) | all dev |
|---|---|---|---|
| pure_python | 22/22 (100%); 22/22 = 100% [85%-100%] | 0/8 answered | 22/30 (73%); 22/22 = 100% [85%-100%] |
| gemma3:1b | 17/22 (77%); 7/17 = 41% [22%-64%] | 4/8 (50%); 4/4 = 100% [51%-100%] | 21/30 (70%); 11/21 = 52% [32%-72%] |
| gemma3:1b (after pure-Python) | 22/22 (100%); 22/22 = 100% [85%-100%] | 4/8 (50%); 4/4 = 100% [51%-100%] | 26/30 (87%); 26/26 = 100% [87%-100%] |
| gemma3:4b | 18/22 (82%); 16/18 = 89% [67%-97%] | 4/8 (50%); 3/4 = 75% [30%-95%] | 22/30 (73%); 19/22 = 86% [67%-95%] |
| gemma3:4b (after pure-Python) | 22/22 (100%); 22/22 = 100% [85%-100%] | 4/8 (50%); 3/4 = 75% [30%-95%] | 26/30 (87%); 25/26 = 96% [81%-99%] |
| phi3.5:3.8b | 21/22 (95%); 21/21 = 100% [85%-100%] | 5/8 (62%); 5/5 = 100% [57%-100%] | 26/30 (87%); 26/26 = 100% [87%-100%] |
| phi3.5:3.8b (after pure-Python) | 22/22 (100%); 22/22 = 100% [85%-100%] | 5/8 (62%); 5/5 = 100% [57%-100%] | 27/30 (90%); 27/27 = 100% [88%-100%] |
| qwen2.5-coder:1.5b | 18/22 (82%); 16/18 = 89% [67%-97%] | 5/8 (62%); 4/5 = 80% [38%-96%] | 23/30 (77%); 20/23 = 87% [68%-95%] |
| qwen2.5-coder:1.5b (after pure-Python) | 22/22 (100%); 22/22 = 100% [85%-100%] | 5/8 (62%); 4/5 = 80% [38%-96%] | 27/30 (90%); 26/27 = 96% [82%-99%] |
| qwen3:1.7b | 17/22 (77%); 14/17 = 82% [59%-94%] | 4/8 (50%); 3/4 = 75% [30%-95%] | 21/30 (70%); 17/21 = 81% [60%-92%] |
| qwen3:1.7b (after pure-Python) | 22/22 (100%); 22/22 = 100% [85%-100%] | 4/8 (50%); 3/4 = 75% [30%-95%] | 26/30 (87%); 25/26 = 96% [81%-99%] |

## logic

| translator | set A (built on) | B + hand (unseen) | all dev |
|---|---|---|---|
| pure_python | 22/22 (100%); 22/22 = 100% [85%-100%] | 0/8 answered | 22/30 (73%); 22/22 = 100% [85%-100%] |
| gemma3:1b | 1/22 (5%); 1/1 = 100% [21%-100%] | 0/8 answered | 1/30 (3%); 1/1 = 100% [21%-100%] |
| gemma3:1b (after pure-Python) | 22/22 (100%); 22/22 = 100% [85%-100%] | 0/8 answered | 22/30 (73%); 22/22 = 100% [85%-100%] |
| gemma3:4b | 9/22 (41%); 9/9 = 100% [70%-100%] | 0/8 answered | 9/30 (30%); 9/9 = 100% [70%-100%] |
| gemma3:4b (after pure-Python) | 22/22 (100%); 22/22 = 100% [85%-100%] | 0/8 answered | 22/30 (73%); 22/22 = 100% [85%-100%] |
| phi3.5:3.8b | 8/22 (36%); 8/8 = 100% [68%-100%] | 1/8 (12%); 0/1 = 0% [0%-79%] | 9/30 (30%); 8/9 = 89% [56%-98%] |
| phi3.5:3.8b (after pure-Python) | 22/22 (100%); 22/22 = 100% [85%-100%] | 1/8 (12%); 0/1 = 0% [0%-79%] | 23/30 (77%); 22/23 = 96% [79%-99%] |
| qwen2.5-coder:1.5b | 12/22 (55%); 12/12 = 100% [76%-100%] | 1/8 (12%); 0/1 = 0% [0%-79%] | 13/30 (43%); 12/13 = 92% [67%-99%] |
| qwen2.5-coder:1.5b (after pure-Python) | 22/22 (100%); 22/22 = 100% [85%-100%] | 1/8 (12%); 0/1 = 0% [0%-79%] | 23/30 (77%); 22/23 = 96% [79%-99%] |
| qwen3:1.7b | 4/22 (18%); 4/4 = 100% [51%-100%] | 1/8 (12%); 1/1 = 100% [21%-100%] | 5/30 (17%); 5/5 = 100% [57%-100%] |
| qwen3:1.7b (after pure-Python) | 22/22 (100%); 22/22 = 100% [85%-100%] | 1/8 (12%); 1/1 = 100% [21%-100%] | 23/30 (77%); 23/23 = 100% [86%-100%] |

## Chosen translator (rule: precision 100% over all 30 dev items of the category, highest coverage; else best precision, then coverage)

- math: **phi3.5:3.8b**
- logic: **gemma3:4b**

Selection used all 30 dev items per category (set A + the unseen B/hand dev items), so the unseen figures above are no longer independent of the choice; the Phase 6 test split (new B/hand items) is the clean check. The combined solver path in the cascade replay is: pure-Python parser, then the chosen translator when it defers (`solver_cascade_results.json`).

## Why replies were rejected (chosen translators)

- math / phi3.5:3.8b: answered x26; literal(s) not from the problem: ['2'] x2; literal(s) not from the problem: ['12', '12'] x1; no plain arithmetic expression in the reply x1
- logic / gemma3:4b: answered x9; no solution x3; position out of range x3; 4 constraints but 3 constraint sentences x2; more than one solution x2; 9 constraints but 7 constraint sentences x1
