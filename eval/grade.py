"""Grade an answers JSONL file (see eval/answers.py) against eval/tasks_8cat.json.

Usage: .venv/Scripts/python.exe -X utf8 -m eval.grade ANSWERS.jsonl [--split dev] [--out PREFIX] [--judge none|glm|qwen|default]

Writes PREFIX_scores.jsonl (one row per answer) and PREFIX_summary.md/.json:
accuracy per model x category x difficulty with Wilson 95% CIs, and per-model counts of answers the
grader could not parse. Factual and summary answers need the blind judge (D8); with --judge none they
are reported as `pending` and left out of accuracy.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

from eval.answers import read_answers
from eval.graders import grade
from eval.graders.language import non_english_chars
from eval.task_schema import CATEGORIES, load_tasks

ROOT = Path(__file__).resolve().parent
TASKS_PATH = ROOT / "tasks_8cat.json"
DEFAULT_JUDGE = "default"  # D8/D10 decision: see results/judge_decision.md (resolves to judge.DEFAULT_JUDGE)


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def is_unparsed(res, error) -> bool:
    """The grader found nothing to grade: empty/failed call, or no number/label/JSON/code in the text."""
    if error:
        return True
    return res.extracted is None and not res.needs_judge


def grade_answer(task: dict, ans: dict, judge_fn=None) -> dict:
    text = ans["raw_text"] or ""
    if ans.get("error") and not text:
        res = None
        row = dict(passed=False, score=0.0, detail=f"call error: {ans['error']}", extracted=None,
                   needs_judge=False, unparsed=True, judged=False, language_fail=False)
    else:
        res = grade(task, text)
        row = dict(passed=res.passed, score=res.score, detail=res.detail, extracted=res.extracted,
                   needs_judge=res.needs_judge, unparsed=is_unparsed(res, None), judged=False, language_fail=False)
        bad = non_english_chars(text)
        if bad:  # D10: code check for every category, independent of the grader and the judge
            row.update(passed=False, score=0.0, needs_judge=False,
                       detail=f"non-English script ({''.join(bad[:8])}); {res.detail}"[:300])
            row["language_fail"] = True
            res = None
        if res is not None and res.extracted is not None and not isinstance(res.extracted, (str, int, float, list)):
            row["extracted"] = str(res.extracted)
        if res is not None and res.needs_judge and judge_fn is not None:
            v = judge_fn(task, ans, res)
            row.update(passed=v["passed"], score=1.0 if v["passed"] else 0.0, judged=True,
                       judge=v.get("judge"), judge_reason=v.get("reason"))
            if v["passed"] is None:
                row["detail"] += "; judge returned no verdict"
    row.update(task_id=task["id"], model=ans["model"], category=task["category"],
               difficulty=task["difficulty"], split=task["split"], run_id=ans["run_id"],
               tokens_out=ans.get("tokens_out"), latency_ms=ans.get("latency_ms"), cost_usd=ans.get("cost_usd"))
    return row


def grade_answers(answers: list, tasks: list, split=None, judge_fn=None) -> list:
    by_id = {t["id"]: t for t in tasks}
    rows = []
    for a in answers:
        t = by_id[a["task_id"]]
        if split and t["split"] != split:
            continue
        rows.append(grade_answer(t, a, judge_fn))
    return rows


def summarise(rows: list) -> dict:
    """Per model: cells[category][difficulty|all] = {k, n, pending, acc, lo, hi}; unparsed counts."""
    out = {}
    for m in sorted({r["model"] for r in rows}):
        mr = [r for r in rows if r["model"] == m]
        cells = {}
        for c in CATEGORIES:
            cells[c] = {}
            for d in ("easy", "hard", "all"):
                sel = [r for r in mr if r["category"] == c and d in (r["difficulty"], "all")]
                done = [r for r in sel if r["passed"] is not None]
                k = sum(1 for r in done if r["passed"])
                lo, hi = wilson(k, len(done))
                cells[c][d] = dict(k=k, n=len(done), pending=len(sel) - len(done), total=len(sel),
                                   acc=(k / len(done) if done else None), lo=lo, hi=hi)
        unparsed = defaultdict(int)
        for r in mr:
            if r["unparsed"]:
                unparsed[r["category"]] += 1
        out[m] = dict(cells=cells, unparsed=dict(unparsed), unparsed_total=sum(unparsed.values()), n=len(mr),
                      language_fails=sum(1 for r in mr if r.get("language_fail")),
                      errors=sum(1 for r in mr if str(r["detail"]).startswith("call error")),
                      cost_usd=sum(r["cost_usd"] or 0 for r in mr))
    return out


def fmt_cell(c) -> str:
    if c["n"] == 0:
        return f"pending ({c['pending']})" if c["pending"] else "-"
    s = f"{c['k']}/{c['n']} = {c['acc']:.0%} [{c['lo']:.0%}-{c['hi']:.0%}]"
    return s + (f" +{c['pending']} pending" if c["pending"] else "")


def to_markdown(summary: dict, title: str) -> str:
    L = [f"# {title}", "", "Accuracy = passed / graded, Wilson 95% CI in brackets. `pending` = needs the blind judge (not graded yet).", ""]
    for m, s in summary.items():
        L += [f"## {m}  ({s['n']} answers, {s['errors']} call errors, grader could not parse: **{s['unparsed_total']}**, non-English script: **{s['language_fails']}**)", "",
              "| category | easy | hard | all | could not parse |", "|---|---|---|---|---|"]
        for c in CATEGORIES:
            cl = s["cells"][c]
            L.append(f"| {c} | {fmt_cell(cl['easy'])} | {fmt_cell(cl['hard'])} | {fmt_cell(cl['all'])} | "
                     f"{s['unparsed'].get(c, 0)} |")
        L.append("")
    return "\n".join(L)


def make_judge(name: str, max_cost: float = 0.50):
    if name == "none":
        return None
    from eval.graders.judge import make_judge_fn
    return make_judge_fn(name, max_cost)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("answers", nargs="+")
    ap.add_argument("--split", choices=["dev", "test"], default=None)
    ap.add_argument("--out", default=None, help="output prefix (default: first answers file without .jsonl)")
    ap.add_argument("--judge", default=DEFAULT_JUDGE, help="none | glm | qwen | default (D8 rule)")
    ap.add_argument("--max-cost", type=float, default=0.50, help="hard stop for Fireworks judge spend, USD")
    a = ap.parse_args(argv)
    answers = [r for p in a.answers for r in read_answers(p)]
    tasks = load_tasks(TASKS_PATH)
    rows = grade_answers(answers, tasks, a.split, make_judge(a.judge, a.max_cost))
    prefix = a.out or str(Path(a.answers[0]).with_suffix(""))
    with open(prefix + "_scores.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    summ = summarise(rows)
    Path(prefix + "_summary.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    Path(prefix + "_summary.md").write_text(to_markdown(summ, f"Grading summary: {Path(prefix).name}"), encoding="utf-8")
    print(to_markdown(summ, "Grading summary"))


if __name__ == "__main__":
    main()
