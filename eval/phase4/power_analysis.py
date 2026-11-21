"""Power of the D4 test (paired bootstrap, one-sided 95%, margin 5 points) + the 80% floor, at n = 15 (cell) and n = 30 (category).

Written BEFORE seeing any Phase 3 results. Simulates paired binary data: B1 has true accuracy p_ref; the candidate is `gap` points worse
(gap = 0 means equally good). Per task the (candidate, B1) outcomes fall in 4 classes; the share of 'discordant' tasks (where exactly one
is right) is the nuisance parameter, so three regimes are shown: nested errors (the candidate fails only on tasks B1 also fails, plus the
gap: minimal discordance), moderate and high discordance. The bootstrap resample of paired tasks is exactly a multinomial draw over
(B1-only-right, cand-only-right, rest), so it is simulated directly.
"""
import numpy as np

from router.data import ROOT

SEED = 20251120
MARGIN, ALPHA, FLOOR = 0.05, 0.05, 0.80
N_SIM, N_BOOT = 4000, 2000
EXTRA ={0.95: (0.0, 0.02, 0.04), 0.90: (0.0, 0.04, 0.08)}  # P(cand right & B1 wrong); capped by 1 - p_ref


def certify_prob(n, p_ref, gap, extra_disc, rng):
    """P(D4 test passes) and P(test AND floor pass). The candidate is right on a task with prob p_ref - gap overall.
    extra_disc = P(cand right & B1 wrong) (the reverse cell grows to keep the accuracy gap)."""
    c = extra_disc                     # P(B1 wrong, cand right)
    b = gap + c                        # P(B1 right, cand wrong)
    if b + c > 1 or b > p_ref or c > 1 - p_ref + 1e-12:
        return None
    both_right = p_ref - b
    both_wrong = 1 - p_ref - c
    probs = np.array([b, c, both_right + both_wrong])
    draws = rng.multinomial(n, probs, size=N_SIM)           # observed (b_k, c_k, rest_k) per simulated dev cell
    passes = np.zeros(N_SIM, bool)
    floor_ok = np.zeros(N_SIM, bool)
    for i, (bk, ck, rk) in enumerate(draws):
        # observed cand accuracy = (both_right_k + c_k)/n; approximate both_right_k by splitting `rest` with the model proportions
        br_k = rng.binomial(rk, both_right / max(both_right + both_wrong, 1e-12))
        floor_ok[i] = (br_k + ck) / n >= FLOOR
        boot = rng.multinomial(n, [bk / n, ck / n, rk / n], size=N_BOOT)
        d = (boot[:, 1] - boot[:, 0]) / n                    # bootstrap diff = (cand-only - B1-only)/n
        passes[i] = np.quantile(d, ALPHA) >= -MARGIN - 1e-12
    return float(passes.mean()), float((passes & floor_ok).mean())


INTERPRETATION = [
    "## What the numbers say (read from the tables above)", "",
    "1. **Certifying a genuinely equal model is unreliable.** A candidate whose true accuracy equals B1's (gap 0) but which is a *different* model "
    "(so the two disagree on some tasks) is certified only 54-74% of the time at n = 15 (B1 at 95%, disagreement on 4-8% of tasks; 30-54% for B1 at 90%) "
    "and only 32-55% at n = 30 (21-35% for B1 at 90%). Only a model that agrees with B1 on essentially every task passes reliably (the 'nested, gap 0' "
    "column is simply 'same answers as B1').",
    "2. **A candidate sitting exactly at the margin (5 points worse) is certified 13-46% of the time at n = 15 and 7-22% at n = 30.** So the rule does not "
    "give 'up to 5 points worse is fine'; in practice it asks for 'no visible loss versus B1'.",
    "3. **The rule is no more powerful at the category level (n = 30) than at the cell level (n = 15) for equal models; it is more discriminating "
    "against worse ones.** At n = 15 a model 10 points worse is still certified 6-20% of the time and one 15 points worse 2-9% (false accepts); at n = 30 "
    "these fall to 2-4% and 0-1%. Reliably rejecting a deficit (certified <= 10%) needs a gap of about 15 points at n = 15 and about 7.5-10 points at n = 30.",
    "4. **Why:** with so few tasks, one task is 6.7 points (n = 15) or 3.3 points (n = 30). A single net loss to B1 is within the 5-point margin on "
    "the point estimate, but the one-sided bootstrap lower bound drops below -5 points as soon as the models disagree in B1's favour more often than the other way. "
    "The 80% floor rarely adds anything on top (the bracketed figures differ by 0-5 points), except for B1 at 90% at n = 15.",
    "",
    "**Plain statement:** at these sample sizes, almost nothing can route away from B1 on the strength of a different model, unless that model is "
    "(nearly) identical to B1 on the dev tasks. The cells that can pass are those where B1 is near-perfect and the cheaper model is too (e.g. easy "
    "sentiment, easy math with solvers, easy NER), and even there a certified rate of 50-75% per equally-good model is the best case. "
    "Expect few local or cheaper-API routes to be certified by the rule as written, and expect the number to depend on luck at the cell level. "
    "This is a property of the 15/30-task dev samples and the test as defined, not a bug in the code (the code is unit-tested on synthetic data).",
    "",
    "**Not changed by me.** The rule, margin and floor stay as agreed in D4. Levers for Kabir and the parent session to consider (none applied): "
    "(1) a wider margin (e.g. 10 points), (2) a one-sided 90% instead of 95% bound, (3) deciding at the category level only, "
    "(4) more dev tasks per cell or repeated runs, (5) judging a local option by its *cascade* accuracy (validators + escalation to B1), which "
    "`make_policy.py` also produces as `routing_policy_cascade.json`, and (6) reporting the rule's outcome *and* the 'cheapest option within 5 points on the point estimate' "
    "side by side. Whatever is chosen, the final accuracy claim is measured on the held-out test split in Phase 6, not by this rule.",
    "",
    "**Outcome (added after the decision):** D12 was adopted because of this analysis. The per-cell bootstrap test was replaced by a plain count rule per cell "
    "(at most one more miss than B1, and >= 80%) and the statistical guarantee moved to a whole-router test over all 240 dev tasks "
    "(at most 3 points worse than B1 at 95% confidence, one-sided paired bootstrap). The simulation above is unchanged and describes the original D4 test.",
    "",
    f"Caveat on the simulation: the disagreement levels (nested / moderate / high) are assumptions, since real disagreement between a small local model and B1 "
    "is unknown until Phase 3; once it is, `policy_report.md` shows the observed value for every cell.",
]


def main():
    rng = np.random.default_rng(SEED)
    L = ["# Power of the D4 rule at dev sample sizes (written before Phase 3 results)", "",
         "**Rule (D4):** a cheaper option may take a cell only if (i) a paired bootstrap says it is at most 5 points worse than B1 with 95% "
         "confidence (one-sided: the 5th percentile of the bootstrap difference in accuracy must be >= -5 points) AND (ii) its accuracy is >= 80%.",
         "", "**Method:** Monte Carlo, 4000 simulated dev cells per row, 2000 bootstrap resamples each (`eval/phase4/power_analysis.py`, seed 20251120). "
         "Simulated B1 has true accuracy 95% or 90%; the candidate's true accuracy is B1 minus the gap. Because the data are paired, what matters most "
         "is how often the two models disagree: *nested* = the candidate only fails where B1 also fails (plus the gap: the best case for the rule), "
         "*moderate* / *high* = extra tasks where the candidate is right and B1 wrong, which are balanced by more tasks where B1 is right and the candidate wrong "
         "(the usual case when two different models answer the same tasks).", ""]
    results = {}
    for n, label in ((15, "cell (n = 15)"), (30, "category (n = 30)")):
        for p_ref in (0.95, 0.90):
            L += [f"## {label}, B1 true accuracy {p_ref:.0%}", "",
                  "Share of simulations in which the candidate is **certified** (test passes; in brackets: test AND the 80% floor).", "",
                  f"| candidate's true gap vs B1 | nested (no extra disagreement) | moderate (+{EXTRA[p_ref][1]:.0%} each way) | high (+{EXTRA[p_ref][2]:.0%} each way) |", "|---|---|---|---|"]
            for gap in (0.0, 0.025, 0.05, 0.075, 0.10, 0.15, 0.20):
                cells = []
                for extra in EXTRA[p_ref]:
                    r = certify_prob(n, p_ref, gap, extra, rng)
                    cells.append("n/a" if r is None else f"{r[0]:.0%} ({r[1]:.0%})")
                    results[(n, p_ref, gap, extra)] = r
                L.append(f"| {gap*100:.1f} points worse | " + " | ".join(cells) + " |")
            L.append("")
    L += INTERPRETATION
    out = ROOT / "eval" / "results" / "phase4" / "power_analysis.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()

