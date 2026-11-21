"""Phase 6 step 5a: grade every system on the 160 test tasks with the frozen graders and judge (eval/grade.py, D8/D10).

Systems: router_main_gpu_run1..3, router_main_cpu_check, router_gpu_server_run1 (Kaggle), B1_run1..3, B2_run1..3 (laptop).
Router answers are graded as plain answer text; the judge rule 'no model grades itself' uses the model that actually answered.
Output: eval/results/phase6/graded_scores.jsonl (one row per system x task, with layer / answering model / trace summary for the report).
Resumable: rows already in the file are skipped. Nothing here changes a grader, prompt, threshold or rubric.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from eval.answers import read_answers
from eval.grade import grade_answer
from eval.graders.judge import make_judge_fn
from eval.task_schema import load_tasks

ROOT = Path(__file__).resolve().parent
P6 = ROOT / "results" / "phase6"
KOUT = P6 / "kaggle_out" / "phase6_out"
OUT = P6 / "graded_scores.jsonl"
ROUTER_RUNS = ["main_gpu_run1", "main_gpu_run2", "main_gpu_run3", "main_cpu_check", "gpu_server_run1"]


def systems():
    for r in ROUTER_RUNS:
        rows = json.loads((KOUT / r / "results.json").read_text(encoding="utf-8"))["results"]
        yield f"router_{r}", [dict(task_id=x["id"], model=f"router_{r}", provider="router", run_id=r, raw_text=x.get("answer") or "",
                                   extracted=None, tokens_in=None, tokens_out=None, tokens_reasoning=None, latency_ms=x.get("latency_ms"),
                                   cost_usd=x.get("cost_usd") or 0.0, error=x.get("error"), _by=x.get("model") or "", _row=x) for x in rows]
    ans = read_answers(P6 / "answers_b1b2.jsonl")
    for m, tag in (("kimi-k3p1-pro", "B1"), ("deepseek-v4p1-flash", "B2")):
        for run in (1, 2, 3):
            yield f"{tag}_run{run}", [dict(a, model=f"{tag}_run{run}", _by=m, _row=None) for a in ans
                                      if a["model"] == m and a["run_id"] == f"phase6_b_run{run}"]


def main():
    tasks = {t["id"]: t for t in load_tasks(ROOT / "tasks_8cat.json") if t["split"] == "test"}
    assert len(tasks) == 160
    judge = make_judge_fn("default", 0.50)

    def jfn(task, ans, res):
        return judge(task, dict(ans, model=ans["_by"]), res)

    done = set()
    if OUT.exists():
        done = {(json.loads(l)["system"], json.loads(l)["task_id"]) for l in OUT.read_text(encoding="utf-8").splitlines() if l.strip()}
    with open(OUT, "a", encoding="utf-8") as f:
        for name, answers in systems():
            assert len(answers) == 160, (name, len(answers))
            n = 0
            for a in answers:
                if (name, a["task_id"]) in done:
                    continue
                row = grade_answer(tasks[a["task_id"]], a, jfn)
                row["system"] = name
                row["answered_by"] = a["_by"]
                x = a["_row"]
                if x:
                    row.update(layer=x.get("layer"), pred_category=x.get("category"), pred_difficulty=x.get("difficulty"),
                               label_source=x.get("label_source"), escalated=x.get("escalated"), plan=x.get("plan"), trace=x.get("trace"),
                               router_status=x.get("status"))
                f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
                f.flush()
                n += 1
            print(name, "graded", n, flush=True)


if __name__ == "__main__":
    sys.exit(main())
