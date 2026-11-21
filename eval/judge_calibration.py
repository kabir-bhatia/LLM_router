"""Phase 2 step 5: judge calibration set (D8).

Builds ~40 dev answers (20 factual + 20 summaries that met their constraint), mixed answering models and
stratified by a cheap lexical key-point coverage score (so likely passes AND likely fails are included, without
using either judge to choose), grades them with BOTH judges, and writes:
  eval/results/judge_calibration_sheet.md      for Kabir to hand-label (no model names, no judge verdicts)
  eval/results/judge_calibration_key.json      item -> task, model, both judge verdicts (kept apart from the sheet)
Run: .venv/Scripts/python.exe -X utf8 -m eval.judge_calibration [--max-cost 0.5]
"""

from __future__ import annotations

import argparse
import json
import random
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from eval.grade import TASKS_PATH
from eval.graders import grade
from eval.graders.common import strip_thinking
from eval.graders.constraint import summary_text
from eval.graders.judge import JUDGES, call_judge, judge_prompt_for_task, spent_usd
from eval.task_schema import load_tasks

ROOT = Path(__file__).resolve().parent
ANS = ROOT / "results" / "phase2_dryrun" / "answers_dryrun.jsonl"
KEY = ROOT / "results" / "judge_calibration_key.json"
SHEET = ROOT / "results" / "judge_calibration_sheet.md"
SEED = 20261120
STOP = {"the", "and", "that", "with", "from", "this", "than", "into", "are", "was", "for", "its", "has", "have", "not"}


def words(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 3 and w not in STOP}


def coverage(task: dict, text: str) -> float:
    """Share of required points whose content words are at least half present in the answer."""
    g = task["gold"]
    pts = g["key_points"] if task["category"] == "factual" else g["key_facts"]
    have = words(text)
    ok = 0
    for p in pts:
        w = words(p)
        ok += bool(w) and len(w & have) / len(w) >= 0.5
    return ok / len(pts)


def pick(cands: list, n: int, rng: random.Random) -> list:
    """cands sorted by coverage; take the lowest, the highest, and the middle, alternating models."""
    cands = sorted(cands, key=lambda c: (c["cov"], c["task_id"]))
    k = len(cands)
    idx = sorted({round(i * (k - 1) / (n - 1)) for i in range(n)})
    return [cands[i] for i in idx]


def build() -> list:
    tasks = {t["id"]: t for t in load_tasks(TASKS_PATH)}
    answers = [json.loads(l) for l in ANS.read_text(encoding="utf-8").splitlines() if l.strip()]
    pool = {"factual": [], "summarisation": []}
    for a in answers:
        t = tasks[a["task_id"]]
        if t["split"] != "dev" or t["category"] not in pool:
            continue
        text = a["raw_text"]
        if t["category"] == "summarisation":
            if not grade(t, text).needs_judge:  # constraint violated -> never reaches the judge
                continue
        pool[t["category"]].append({"task_id": t["id"], "model": a["model"], "raw_text": text,
                                    "cov": coverage(t, summary_text(text) if t["category"] == "summarisation" else text)})
    rng = random.Random(SEED)
    chosen = []
    for cat, cands in pool.items():
        for model in sorted({c["model"] for c in cands}):
            mine = [c for c in cands if c["model"] == model]
            chosen += [dict(c, category=cat) for c in pick(mine, 10, rng)]
    rng.shuffle(chosen)
    for i, c in enumerate(chosen, 1):
        c["item"] = i
    return chosen


def run_judges(items: list, tasks: dict, max_cost: float) -> None:
    def one(it):
        p = judge_prompt_for_task(tasks[it["task_id"]], it["raw_text"])
        it["verdicts"] = {j: call_judge(j, p, max_cost) for j in JUDGES}
        return it

    with ThreadPoolExecutor(4) as ex:
        list(ex.map(one, items))


def sheet(items: list, tasks: dict) -> str:
    L = ["# Judge calibration sheet (Phase 2, D8)", "",
         f"{len(items)} answers from small local models. For each, write **PASS** or **FAIL** after `Label:`. "
         "Model names and judge verdicts are hidden on purpose.", "",
         "**Rubric (same as the judges').** FAIL only if the answer states something wrong or that contradicts the "
         "reference/source, or if a REQUIRED point is missing. Correct extra detail never fails. OPTIONAL points never decide. "
         "Ignore style and length (summary length/format limits are already checked by code).", ""]
    for it in items:
        t = tasks[it["task_id"]]
        g = t["gold"]
        L += [f"---", "", f"## Item {it['item']}  ({'factual' if t['category'] == 'factual' else 'summary'})", ""]
        if t["category"] == "factual":
            L += ["**Question:**", f"> {g['question']}", "", f"**Reference answer:** {g['reference']}", "",
                  "**REQUIRED points:**"] + [f"- {k}" for k in g["key_points"]]
            if g.get("optional_points"):
                L += ["", "**OPTIONAL points:**"] + [f"- {k}" for k in g["optional_points"]]
            ans = strip_thinking(it["raw_text"]).strip()
        else:
            L += [f"**Task given to the model:**", f"> {t['prompt'][:200].splitlines()[0]} ...", "",
                  "**Source text:**", f"> {g['source_text']}", "", f"**Constraint (already verified OK):** {g['constraints']}", "",
                  "**REQUIRED facts (each must be in the summary):**"] + [f"- {k}" for k in g["key_facts"]]
            ans = summary_text(it["raw_text"])
        L += ["", "**Candidate answer:**", ""] + ["> " + ln for ln in ans.splitlines()] + ["", "**Label:** ", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-cost", type=float, default=0.50)
    ap.add_argument("--keep-sheet", action="store_true",
                    help="re-judge and rewrite the key only; never touch the hand-labelled sheet")
    a = ap.parse_args()
    tasks = {t["id"]: t for t in load_tasks(TASKS_PATH)}
    items = build()
    run_judges(items, tasks, a.max_cost)
    KEY.write_text(json.dumps([{k: v for k, v in it.items() if k != "raw_text"} | {"raw_text_len": len(it["raw_text"])}
                               for it in items], indent=1), encoding="utf-8")
    if not a.keep_sheet:
        SHEET.write_text(sheet(items, tasks), encoding="utf-8")
    both = [it for it in items if all(v["passed"] is not None for v in it["verdicts"].values())]
    agree = sum(it["verdicts"]["glm"]["passed"] == it["verdicts"]["qwen"]["passed"] for it in both)
    print(f"items {len(items)}; judges agree with each other on {agree}/{len(both)}; Fireworks spent so far ${spent_usd():.4f}")
    for j in JUDGES:
        print(j, "PASS", sum(it["verdicts"][j]["passed"] is True for it in items), "FAIL",
              sum(it["verdicts"][j]["passed"] is False for it in items), "none", sum(it["verdicts"][j]["passed"] is None for it in items))


if __name__ == "__main__":
    main()
