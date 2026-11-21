"""Step 6: quality checks, stratified 60/40 split, freeze eval/tasks_8cat.json, write the Phase 1 report data.

Split rule: per (category x difficulty) cell, 10 of 25 tasks go to test (seed fixed). For math and logic
(D7) the test items are drawn ONLY from template set B + hand-written items; all set-A items are dev.
Run: .venv/Scripts/python.exe -X utf8 -m eval.gen.freeze
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

from eval.gen import build_math_logic as BML
from eval.gen import hand_math_logic as H
from eval.gen import items_code_debug, items_code_gen
from eval.gen import logic_gen, math_gen
from eval.graders import grade
from eval.graders.code_tests import run_tests
from eval.graders.constraint import check_constraints
from eval.task_schema import CATEGORIES, validate_task

ROOT = Path(__file__).resolve().parents[1]
SEED = 20251120
TEST_PER_CELL = 10
OUT = ROOT / "tasks_8cat.json"


def load_all():
    tasks = []
    for c in CATEGORIES:
        tasks += json.loads((ROOT / "drafts" / f"{c}.json").read_text(encoding="utf-8"))
    return tasks


def checks(tasks):
    """Return list of (name, n_checked, n_failed, detail)."""
    res = []

    def rec(name, n, failed, detail=""):
        res.append({"check": name, "checked": n, "failed": len(failed), "detail": detail or "; ".join(failed[:5])})

    # schema / ids / prompts
    bad = [f"{t.get('id')}: {validate_task(t)}" for t in tasks if validate_task(t)]
    rec("schema valid (all required fields, grader matches category)", len(tasks), bad)
    ids = Counter(t["id"] for t in tasks)
    rec("unique ids", len(tasks), [k for k, v in ids.items() if v > 1])
    pr = Counter(t["prompt"] for t in tasks)
    rec("unique prompts (exact)", len(tasks), [k[:40] for k, v in pr.items() if v > 1])
    cnt = Counter((t["category"], t["difficulty"]) for t in tasks)
    rec("25 easy + 25 hard per category", 8, [str(k) for k, v in cnt.items() if v != 25])

    by = defaultdict(list)
    for t in tasks:
        by[t["category"]].append(t)

    # gold answer scores 1.0 under its own grader (graders agree with gold)
    fails = []
    for t in by["math"]:
        if not grade(t, f"ANSWER: {t['gold']['answer']}").passed:
            fails.append(t["id"])
    for t in by["logic"]:
        if not grade(t, f"ANSWER: {t['gold']['answer']}").passed:
            fails.append(t["id"])
    for t in by["sentiment"]:
        if not grade(t, f"ANSWER: {t['gold']['label']}").passed:
            fails.append(t["id"])
    for t in by["ner"]:
        gj = json.dumps(t["gold"]["entities"])
        if not grade(t, gj).passed:
            fails.append(t["id"])
        for alt in t["gold"].get("alternatives", []):
            if not grade(t, json.dumps(alt["entities"])).passed:
                fails.append(t["id"] + "-alt")
        for e in t["gold"]["entities"]:
            if e["text"] not in t["prompt"]:
                fails.append(t["id"] + ":" + e["text"])
    rec("gold answers pass their own grader (math, logic, sentiment, NER incl. alternatives; NER spans occur in prompt)",
        sum(len(by[c]) for c in ("math", "logic", "sentiment", "ner")), fails)

    # code: reference passes all tests; for debugging the buggy code in the prompt fails at least one
    fails_gen, fails_dbg, caught = [], [], []
    for t in by["code_gen"]:
        ok, errs, fatal = run_tests(t["gold"]["reference"], t["gold"]["tests"])
        if not all(ok):
            fails_gen.append(t["id"])
    for t in by["code_debug"]:
        ok, _, _ = run_tests(t["gold"]["reference"], t["gold"]["tests"])
        m = re.search(r"```python\n(.*?)```", t["prompt"], re.S)
        okb, _, _ = run_tests(m.group(1), t["gold"]["tests"])
        if not all(ok):
            fails_dbg.append(t["id"] + ":ref")
        if all(okb):
            fails_dbg.append(t["id"] + ":buggy-passes")
        caught.append(sum(1 for x in okb if not x))
    rec("code_gen: reference passes all hidden tests (re-run)", len(by["code_gen"]), fails_gen)
    rec("code_debug: tests pass on reference and fail on the buggy code shown in the prompt (re-run)",
        len(by["code_debug"]), fails_dbg, f"min failing tests on buggy code = {min(caught)}")
    gen_tests = [sum(x.count("assert ") for x in t["gold"]["tests"]) for t in by["code_gen"]]
    dbg_tests = [sum(x.count("assert ") for x in t["gold"]["tests"]) for t in by["code_debug"]]
    res.append({"check": "tests per task", "checked": 100, "failed": 0,
                "detail": f"code_gen {min(gen_tests)}-{max(gen_tests)}, code_debug {min(dbg_tests)}-{max(dbg_tests)} (assert statements)"})

    # math / logic: regenerate deterministically and compare to the draft (generators assert independent
    # re-computation / unique solutions while generating)
    regen_m = (math_gen.generate("A", 11, 11, seed=101) + math_gen.generate("B", 8, 8, seed=202) + H.hand_math_items())
    regen_l = (logic_gen.generate("A", BML.LOGIC_PLAN_A, seed=303) + logic_gen.generate("B", BML.LOGIC_PLAN_B, seed=404)
               + H.hand_logic_items())
    for name, regen in (("math", regen_m), ("logic", regen_l)):
        have = {t["prompt"]: t["gold"] for t in by[name]}
        miss = [r["prompt"][:40] for r in regen if have.get(r["prompt"]) != r["gold"]]
        rec(f"{name}: regeneration reproduces every prompt+gold (independent recomputation / unique-solution asserts re-run)",
            len(regen), miss)

    # summaries: reference passes constraint + facts
    fails = []
    for t in by["summarisation"]:
        g = t["gold"]
        r = grade(t, g["reference_summary"])
        low = g["reference_summary"].lower()
        if r.passed is False or not all(any(h.lower() in low for h in hs) for hs in g["fact_hints"]):
            fails.append(t["id"])
        if "max_words" in g["constraints"] and g["constraints"]["max_words"] <= 25 and len(g["key_facts"]) > 3:
            fails.append(t["id"] + ":>3 facts")
    rec("summarisation: reference_summary meets constraint and contains every required key fact", 50, fails)

    # factual: required points present
    rec("factual: every item has >=1 required key point", 50,
        [t["id"] for t in by["factual"] if not t["gold"]["key_points"]])
    labels = Counter(t["gold"]["label"] for t in by["sentiment"])
    rec("sentiment: labels balanced (13/13/12/12)", 50, [] if sorted(labels.values()) == [12, 12, 13, 13] else [str(labels)])
    return res


def split(tasks):
    rng = random.Random(SEED)
    cells = defaultdict(list)
    for t in tasks:
        cells[(t["category"], t["difficulty"])].append(t)
    for key in sorted(cells):
        pool = cells[key]
        eligible = [t for t in pool if not (t["category"] in ("math", "logic") and t["template_set"] == "A")]
        test_ids = {t["id"] for t in rng.sample(sorted(eligible, key=lambda x: x["id"]), TEST_PER_CELL)}
        for t in pool:
            t["split"] = "test" if t["id"] in test_ids else "dev"
    return tasks


def main():
    tasks = load_all()
    chk = checks(tasks)
    for c in chk:
        print(("FAIL " if c["failed"] else "ok   ") + c["check"], c["checked"], c["detail"][:100])
    assert all(c["failed"] == 0 for c in chk), "quality checks failed; not freezing"
    split(tasks)
    tbl = Counter((t["category"], t["difficulty"], t["split"]) for t in tasks)
    assert all(tbl[(c, d, "test")] >= 8 for c in CATEGORIES for d in ("easy", "hard")), "test cell < 8"
    assert not any(t["split"] == "test" and t["category"] in ("math", "logic") and t["template_set"] == "A" for t in tasks)
    order = {c: i for i, c in enumerate(CATEGORIES)}
    tasks.sort(key=lambda t: (order[t["category"]], t["id"]))
    for t in tasks:
        t.pop("passage_words", None)
    blob = json.dumps(tasks, indent=1, ensure_ascii=False)
    OUT.write_text(blob, encoding="utf-8")
    sha = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    ml = {(t["category"], t["template_set"], t["split"]) for t in tasks if t["category"] in ("math", "logic")}
    summary = {
        "sha256": sha, "n": len(tasks),
        "cells": {f"{c}|{d}|{s}": tbl[(c, d, s)] for c in CATEGORIES for d in ("easy", "hard") for s in ("dev", "test")},
        "template_sets": {f"{c}|{ts}|{s}": sum(1 for t in tasks if (t["category"], t.get("template_set"), t["split"]) == (c, ts, s))
                          for (c, ts, s) in sorted(ml)},
        "checks": chk,
    }
    (ROOT / "results" / "phase1_freeze_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print("frozen", len(tasks), sha[:12])
    print(Counter(t["split"] for t in tasks))


if __name__ == "__main__":
    main()

