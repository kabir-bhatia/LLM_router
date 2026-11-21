# Power of the D4 rule at dev sample sizes (written before Phase 3 results)

**Rule (D4):** a cheaper option may take a cell only if (i) a paired bootstrap says it is at most 5 points worse than B1 with 95% confidence (one-sided: the 5th percentile of the bootstrap difference in accuracy must be >= -5 points) AND (ii) its accuracy is >= 80%.

**Method:** Monte Carlo, 4000 simulated dev cells per row, 2000 bootstrap resamples each (`eval/phase4/power_analysis.py`, seed 20251120). Simulated B1 has true accuracy 95% or 90%; the candidate's true accuracy is B1 minus the gap. Because the data are paired, what matters most is how often the two models disagree: *nested* = the candidate only fails where B1 also fails (plus the gap: the best case for the rule), *moderate* / *high* = extra tasks where the candidate is right and B1 wrong, which are balanced by more tasks where B1 is right and the candidate wrong (the usual case when two different models answer the same tasks).

## cell (n = 15), B1 true accuracy 95%

Share of simulations in which the candidate is **certified** (test passes; in brackets: test AND the 80% floor).

| candidate's true gap vs B1 | nested (no extra disagreement) | moderate (+2% each way) | high (+4% each way) |
|---|---|---|---|
| 0.0 points worse | 100% (100%) | 74% (74%) | 54% (54%) |
| 2.5 points worse | 69% (69%) | 52% (52%) | 37% (37%) |
| 5.0 points worse | 45% (45%) | 33% (33%) | 23% (23%) |
| 7.5 points worse | 31% (31%) | 22% (22%) | 16% (16%) |
| 10.0 points worse | 20% (20%) | 14% (14%) | 11% (11%) |
| 15.0 points worse | 9% (9%) | 6% (6%) | 5% (5%) |
| 20.0 points worse | 4% (4%) | 2% (2%) | 2% (2%) |

## cell (n = 15), B1 true accuracy 90%

Share of simulations in which the candidate is **certified** (test passes; in brackets: test AND the 80% floor).

| candidate's true gap vs B1 | nested (no extra disagreement) | moderate (+4% each way) | high (+8% each way) |
|---|---|---|---|
| 0.0 points worse | 100% (95%) | 54% (53%) | 30% (30%) |
| 2.5 points worse | 69% (65%) | 36% (35%) | 20% (20%) |
| 5.0 points worse | 46% (43%) | 24% (23%) | 13% (13%) |
| 7.5 points worse | 32% (29%) | 15% (15%) | 9% (9%) |
| 10.0 points worse | 20% (19%) | 11% (11%) | 6% (6%) |
| 15.0 points worse | 8% (8%) | 4% (4%) | 2% (2%) |
| 20.0 points worse | 3% (3%) | 2% (2%) | 1% (1%) |

## category (n = 30), B1 true accuracy 95%

Share of simulations in which the candidate is **certified** (test passes; in brackets: test AND the 80% floor).

| candidate's true gap vs B1 | nested (no extra disagreement) | moderate (+2% each way) | high (+4% each way) |
|---|---|---|---|
| 0.0 points worse | 100% (100%) | 55% (55%) | 32% (32%) |
| 2.5 points worse | 46% (46%) | 27% (27%) | 18% (18%) |
| 5.0 points worse | 22% (22%) | 12% (12%) | 9% (9%) |
| 7.5 points worse | 9% (9%) | 6% (6%) | 4% (4%) |
| 10.0 points worse | 4% (4%) | 2% (2%) | 2% (2%) |
| 15.0 points worse | 1% (1%) | 1% (1%) | 0% (0%) |
| 20.0 points worse | 0% (0%) | 0% (0%) | 0% (0%) |

## category (n = 30), B1 true accuracy 90%

Share of simulations in which the candidate is **certified** (test passes; in brackets: test AND the 80% floor).

| candidate's true gap vs B1 | nested (no extra disagreement) | moderate (+4% each way) | high (+8% each way) |
|---|---|---|---|
| 0.0 points worse | 100% (97%) | 35% (35%) | 21% (21%) |
| 2.5 points worse | 48% (46%) | 17% (17%) | 12% (12%) |
| 5.0 points worse | 22% (21%) | 9% (9%) | 7% (7%) |
| 7.5 points worse | 10% (10%) | 4% (4%) | 4% (4%) |
| 10.0 points worse | 4% (4%) | 2% (2%) | 2% (2%) |
| 15.0 points worse | 1% (1%) | 0% (0%) | 0% (0%) |
| 20.0 points worse | 0% (0%) | 0% (0%) | 0% (0%) |

## What the numbers say (read from the tables above)

1. **Certifying a genuinely equal model is unreliable.** A candidate whose true accuracy equals B1's (gap 0) but which is a *different* model (so the two disagree on some tasks) is certified only 54-74% of the time at n = 15 (B1 at 95%, disagreement on 4-8% of tasks; 30-54% for B1 at 90%) and only 32-55% at n = 30 (21-35% for B1 at 90%). Only a model that agrees with B1 on essentially every task passes reliably (the 'nested, gap 0' column is simply 'same answers as B1').
2. **A candidate sitting exactly at the margin (5 points worse) is certified 13-46% of the time at n = 15 and 7-22% at n = 30.** So the rule does not give 'up to 5 points worse is fine'; in practice it asks for 'no visible loss versus B1'.
3. **The rule is no more powerful at the category level (n = 30) than at the cell level (n = 15) for equal models; it is more discriminating against worse ones.** At n = 15 a model 10 points worse is still certified 6-20% of the time and one 15 points worse 2-9% (false accepts); at n = 30 these fall to 2-4% and 0-1%. Reliably rejecting a deficit (certified <= 10%) needs a gap of about 15 points at n = 15 and about 7.5-10 points at n = 30.
4. **Why:** with so few tasks, one task is 6.7 points (n = 15) or 3.3 points (n = 30). A single net loss to B1 is within the 5-point margin on the point estimate, but the one-sided bootstrap lower bound drops below -5 points as soon as the models disagree in B1's favour more often than the other way. The 80% floor rarely adds anything on top (the bracketed figures differ by 0-5 points), except for B1 at 90% at n = 15.

**Plain statement:** at these sample sizes, almost nothing can route away from B1 on the strength of a different model, unless that model is (nearly) identical to B1 on the dev tasks. The cells that can pass are those where B1 is near-perfect and the cheaper model is too (e.g. easy sentiment, easy math with solvers, easy NER), and even there a certified rate of 50-75% per equally-good model is the best case. Expect few local or cheaper-API routes to be certified by the rule as written, and expect the number to depend on luck at the cell level. This is a property of the 15/30-task dev samples and the test as defined, not a bug in the code (the code is unit-tested on synthetic data).

**Not changed by me.** The rule, margin and floor stay as agreed in D4. Levers for Kabir and the parent session to consider (none applied): (1) a wider margin (e.g. 10 points), (2) a one-sided 90% instead of 95% bound, (3) deciding at the category level only, (4) more dev tasks per cell or repeated runs, (5) judging a local option by its *cascade* accuracy (validators + escalation to B1), which `make_policy.py` also produces as `routing_policy_cascade.json`, and (6) reporting the rule's outcome *and* the 'cheapest option within 5 points on the point estimate' side by side. Whatever is chosen, the final accuracy claim is measured on the held-out test split in Phase 6, not by this rule.

**Outcome (added after the decision):** D12 was adopted because of this analysis. The per-cell bootstrap test was replaced by a plain count rule per cell (at most one more miss than B1, and >= 80%) and the statistical guarantee moved to a whole-router test over all 240 dev tasks (at most 3 points worse than B1 at 95% confidence, one-sided paired bootstrap). The simulation above is unchanged and describes the original D4 test.

Caveat on the simulation: the disagreement levels (nested / moderate / high) are assumptions, since real disagreement between a small local model and B1 is unknown until Phase 3; once it is, `policy_report.md` shows the observed value for every cell.
