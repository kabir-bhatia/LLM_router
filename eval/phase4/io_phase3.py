"""Load the Phase 3 benchmark outputs (dev split only) into the structures policy_lib expects.

Scores: graded rows (eval/grade.py output: *_scores.jsonl, one row per answer with task_id, model, passed, cost_usd, latency_ms, split).
Answers: raw answer rows (answers_*.jsonl with raw_text), needed to run the validators on local answers.
A model is 'local' if its name contains ':' (Ollama tag, e.g. qwen3:1.7b), otherwise 'api'.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

from router.data import ROOT, load_dev

PHASE3 = ROOT / "eval" / "results" / "phase3"


def kind_of(model: str) -> str:
    return "local" if ":" in model else "api"


def read_jsonl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def load_results(score_files=None):
    dev_ids = {t["id"] for t in load_dev()}
    files = score_files or sorted(glob.glob(str(PHASE3 / "**" / "*_scores.jsonl"), recursive=True))
    results, kinds = {}, {}
    for f in files:
        for r in read_jsonl(f):
            if r["task_id"] not in dev_ids:
                assert r.get("split") != "test", "a test-split row reached the Phase 4 loader"
                continue
            assert r.get("split", "dev") == "dev"
            m = r["model"]
            kinds[m] = kind_of(m)
            results[(m, r["task_id"])] = {"passed": r["passed"], "cost": 0.0 if kinds[m] == "local" else (r.get("cost_usd") or 0.0),
                                          "latency_ms": r.get("latency_ms")}
    return results, kinds, files


def load_answers(answer_files=None, models=None):
    files = answer_files or sorted(glob.glob(str(PHASE3 / "**" / "answers_*.jsonl"), recursive=True))
    files = [f for f in files if not f.endswith("_scores.jsonl")]
    out = {}
    for f in files:
        for r in read_jsonl(f):
            if models is None or r["model"] in models:
                out[(r["model"], r["task_id"])] = r.get("raw_text") or ""
    return out
