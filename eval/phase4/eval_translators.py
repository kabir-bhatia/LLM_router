"""Offline evaluation of the D13 translators (dev math + logic only).

Input: translations.jsonl from the Kaggle notebook (eval/results/phase4/phase4_solver_translate.zip, or an extracted translations.jsonl).
For every (model, task): parse the reply with router.solvers.translate (self-gating), compare with gold, and report coverage (share answered)
and precision (share of answers correct) on template set A (what the prompts were developed on) and on unseen set B + hand.
Also reports the combined solver path: the pure-Python parser first (free), the LLM-assisted translation when it defers.
The translator is chosen by: precision 100% over all 30 dev items of the category (answered ones), highest coverage; if none reach 100%,
best precision then coverage. Writes translator_report.md, translator_results.json and solver_cascade_results.json (used by make_policy).
"""
import json
import sys
import zipfile
from pathlib import Path

from router.data import ROOT, load_dev
from router.solvers.logic_solver import solve_logic
from router.solvers.math_solver import solve_math
from router.solvers.translate import parse_logic_translation, parse_math_translation

OUT = ROOT / "eval" / "results" / "phase4"


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return max(0.0, c - h), min(1.0, c + h)


def load_translations(path=None):
    p = Path(path) if path else OUT / "phase4_solver_translate.zip"
    if p.suffix == ".zip":
        with zipfile.ZipFile(p) as z:
            txt = z.read("translations.jsonl").decode("utf-8")
    else:
        txt = p.read_text(encoding="utf-8")
    return [json.loads(x) for x in txt.splitlines() if x.strip()]


def correct(task, ans):
    g = task["gold"]["answer"]
    return ans is not None and (float(ans) == float(g) if task["category"] == "math" else ans == g)


def main(path=None):
    dev = {t["id"]: t for t in load_dev()}
    rows = load_translations(path)
    models = sorted({r["model"] for r in rows})
    per = {}     # (model, id) -> (answer or None, reason)
    for r in rows:
        t = dev[r["task_id"]]            # KeyError if a non-dev id is present
        if r.get("error") or not r["raw_text"].strip():
            per[(r["model"], t["id"])] = (None, "call error / empty")
            continue
        res = (parse_math_translation if t["category"] == "math" else parse_logic_translation)(r["raw_text"], t["prompt"])
        per[(r["model"], t["id"])] = (res.answer, res.reason)
    py = {}
    for t in dev.values():
        if t["category"] == "math":
            py[t["id"]] = solve_math(t["prompt"]).answer
        elif t["category"] == "logic":
            py[t["id"]] = solve_logic(t["prompt"]).answer

    def stats(ids, getter):
        n = len(ids)
        a = sum(1 for i in ids if getter(i) is not None)
        c = sum(1 for i in ids if correct(dev[i], getter(i)))
        return {"n": n, "answered": a, "correct": c, "coverage": a / n if n else 0.0, "precision": c / a if a else None}

    sets = {"A": lambda t: t["template_set"] == "A", "B+hand": lambda t: t["template_set"] != "A", "all dev": lambda t: True}
    res = {}
    for cat in ("math", "logic"):
        res[cat] = {}
        for name, flt in sets.items():
            ids = [i for i, t in dev.items() if t["category"] == cat and flt(t)]
            res[cat][name] = {"pure_python": stats(ids, lambda i: py[i])}
            for m in models:
                res[cat][name][m] = stats(ids, lambda i, m=m: per.get((m, i), (None,))[0])
                res[cat][name][m + " (after pure-Python)"] = stats(ids, lambda i, m=m: py[i] if py[i] is not None else per.get((m, i), (None,))[0])
    choice = {}
    for cat in ("math", "logic"):
        best = None
        for m in models:
            s = res[cat]["all dev"][m]
            key = (1 if s["precision"] == 1.0 else 0, s["precision"] or 0.0, s["coverage"]) if s["answered"] else (0, 0.0, 0.0)
            if s["precision"] == 1.0:
                key = (1, 1.0, s["coverage"])
            if best is None or key > best[0]:
                best = (key, m)
        choice[cat] = best[1]
    # combined solver path for the cascade replay: pure-Python first, chosen translator when it defers
    combined = {}
    for i, t in dev.items():
        if t["category"] not in ("math", "logic"):
            continue
        if py[i] is not None:
            ans, src = py[i], "pure_python"
        else:
            ans, src = per.get((choice[t["category"]], i), (None,))[0], "translator:" + choice[t["category"]]
        combined[i] = {"answered": ans is not None, "correct": bool(correct(t, ans)), "source": src if ans is not None else None, "answer": ans}
    (OUT / "translator_results.json").write_text(json.dumps({"results": res, "choice": choice}, indent=1), encoding="utf-8")
    (OUT / "solver_cascade_results.json").write_text(json.dumps(combined, indent=1), encoding="utf-8")

    def cell(s):
        if s["answered"] == 0:
            return f"0/{s['n']} answered"
        lo, hi = wilson(s["correct"], s["answered"])
        return f"{s['answered']}/{s['n']} ({s['coverage']:.0%}); {s['correct']}/{s['answered']} = {s['precision']:.0%} [{lo:.0%}-{hi:.0%}]"

    L = ["# D13 translator evaluation (dev only)", "",
         "Local model translates (math: one expression; logic: JSON spec), Python solves with the safe evaluator / brute force and answers only when "
         "every self-gate passes. Prompts and parsers were developed on set A only (D7); **B + hand are the unseen items (8 per category, so intervals are wide)**. "
         "Cells: answered/n (coverage); correct/answered = precision [Wilson 95%].", ""]
    for cat in ("math", "logic"):
        L += [f"## {cat}", "", "| translator | set A (built on) | B + hand (unseen) | all dev |", "|---|---|---|---|"]
        names = ["pure_python"] + [x for m in models for x in (m, m + " (after pure-Python)")]
        for nm in names:
            L.append(f"| {nm} | " + " | ".join(cell(res[cat][s][nm]) for s in ("A", "B+hand", "all dev")) + " |")
        L.append("")
    L += ["## Chosen translator (rule: precision 100% over all 30 dev items of the category, highest coverage; else best precision, then coverage)", "",
          f"- math: **{choice['math']}**", f"- logic: **{choice['logic']}**", "",
          "Selection used all 30 dev items per category (set A + the unseen B/hand dev items), so the unseen figures above are no longer independent of the choice; "
          "the Phase 6 test split (new B/hand items) is the clean check. The combined solver path in the cascade replay is: pure-Python parser, then the chosen "
          "translator when it defers (`solver_cascade_results.json`).", "", "## Why replies were rejected (chosen translators)", ""]
    for cat in ("math", "logic"):
        from collections import Counter
        c = Counter(per[(choice[cat], i)][1] or "answered" for i, t in dev.items() if t["category"] == cat and (choice[cat], i) in per)
        L.append(f"- {cat} / {choice[cat]}: " + "; ".join(f"{k[:70]} x{v}" for k, v in c.most_common(6)))
    (OUT / "translator_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
