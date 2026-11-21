"""Measure solver coverage (share answered) and precision (share of answers correct) on dev items.

Set A = what the solvers were built on; B + hand = never seen while building (D7). Dev split only.
Writes eval/results/phase4/solver_report.md and solver_results.json.
"""
from __future__ import annotations

import json
from pathlib import Path

from router.data import ROOT, load_dev
from router.solvers.logic_solver import solve_logic
from router.solvers.math_solver import solve_math


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))


def run():
    dev = load_dev()
    rows = []
    for t in dev:
        if t["category"] == "math":
            r = solve_math(t["prompt"])
            ans = r.answer
            correct = ans is not None and float(ans) == float(t["gold"]["answer"])
            why = r.recipe or r.reason
        elif t["category"] == "logic":
            r = solve_logic(t["prompt"])
            ans = r.answer
            correct = ans is not None and ans == t["gold"]["answer"]
            why = r.reason or "unique solution"
        else:
            continue
        rows.append({"id": t["id"], "category": t["category"], "set": t["template_set"], "difficulty": t["difficulty"],
                     "answered": ans is not None, "correct": bool(correct), "answer": ans, "gold": t["gold"]["answer"],
                     "why": why})
    return rows


def summarise(rows, cat, sets):
    sub = [r for r in rows if r["category"] == cat and r["set"] in sets]
    n = len(sub)
    a = sum(r["answered"] for r in sub)
    c = sum(r["correct"] for r in sub)
    return n, a, c


def main():
    rows = run()
    out = ROOT / "eval" / "results" / "phase4"
    out.mkdir(parents=True, exist_ok=True)
    (out / "solver_results.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    lines = ["# Solver results (dev split only)", "",
             "Solvers were built looking only at dev template-set-A items (D7). Set B + hand-written dev items were first looked at when this "
             "report was generated. Coverage = share answered; precision = share of answers that match gold. Wilson 95% intervals.", "",
             "| category | items | n | answered | coverage | correct among answered | precision [95% CI] |", "|---|---|---|---|---|---|---|"]
    for cat in ("math", "logic"):
        for label, sets in (("set A (built on)", ("A",)), ("set B + hand (never seen)", ("B", "hand")), ("all dev", ("A", "B", "hand"))):
            n, a, c = summarise(rows, cat, sets)
            lo, hi = wilson(c, a)
            prec = f"{c}/{a} = {100*c/a:.0f}% [{100*lo:.0f}-{100*hi:.0f}]" if a else "n/a (nothing answered)"
            lines.append(f"| {cat} | {label} | {n} | {a} | {100*a/n:.0f}% | {c} | {prec} |")
    lines += ["", "## Per-item results on set B + hand (unseen)", "", "| id | set | difficulty | answered | correct | answer | gold | reason / recipe |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["set"] != "A":
            lines.append(f"| {r['id']} | {r['set']} | {r['difficulty']} | {r['answered']} | {r['correct']} | {r['answer']} | {r['gold']} | {r['why']} |")
    wrong = [r["id"] for r in rows if r["answered"] and not r["correct"]]
    lines += ["", f"Wrong answers (any set): {wrong if wrong else 'none'}"]
    (out / "solver_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
