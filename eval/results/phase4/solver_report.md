# Solver results (dev split only)

Solvers were built looking only at dev template-set-A items (D7). Set B + hand-written dev items were first looked at when this report was generated. Coverage = share answered; precision = share of answers that match gold. Wilson 95% intervals.

| category | items | n | answered | coverage | correct among answered | precision [95% CI] |
|---|---|---|---|---|---|---|
| math | set A (built on) | 22 | 22 | 100% | 22 | 22/22 = 100% [85-100] |
| math | set B + hand (never seen) | 8 | 0 | 0% | 0 | n/a (nothing answered) |
| math | all dev | 30 | 22 | 73% | 22 | 22/22 = 100% [85-100] |
| logic | set A (built on) | 22 | 22 | 100% | 22 | 22/22 = 100% [85-100] |
| logic | set B + hand (never seen) | 8 | 0 | 0% | 0 | n/a (nothing answered) |
| logic | all dev | 30 | 22 | 73% | 22 | 22/22 = 100% [85-100] |

## Per-item results on set B + hand (unseen)

| id | set | difficulty | answered | correct | answer | gold | reason / recipe |
|---|---|---|---|---|---|---|---|
| math-004 | B | hard | False | False | None | 16488 | no recipe matched with certainty |
| math-010 | B | easy | False | False | None | 10 | no recipe matched with certainty |
| math-011 | hand | easy | False | False | None | 750 | no recipe matched with certainty |
| math-022 | B | easy | False | False | None | 560 | no recipe matched with certainty |
| math-025 | hand | easy | False | False | None | 480 | no recipe matched with certainty |
| math-031 | B | hard | False | False | None | 17616 | no recipe matched with certainty |
| math-041 | B | hard | False | False | None | 34 | no recipe matched with certainty |
| math-044 | B | hard | False | False | None | 62 | no recipe matched with certainty |
| logic-015 | B | hard | False | False | None | Cy | no item list |
| logic-019 | B | hard | False | False | None | Noor | no item list |
| logic-025 | B | hard | False | False | None | Raj | no entity header |
| logic-029 | hand | easy | False | False | None | mixed | no entity header |
| logic-034 | hand | hard | False | False | None | Isha | no item list |
| logic-037 | B | easy | False | False | None | Ben | no item list |
| logic-048 | B | easy | False | False | None | Tomas | no item list |
| logic-049 | B | easy | False | False | None | Dia | no item list |

Wrong answers (any set): none
