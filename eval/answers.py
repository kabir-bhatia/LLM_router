"""Answer store: one JSONL file per run, one JSON object per line (model answer to one task).

Fields (all keys always present):
  task_id          id in eval/tasks_8cat.json
  model            e.g. "gemma3:1b"
  provider         "ollama-kaggle" | "fireworks" | "hyde" | "gemini" | "router" ...
  run_id           free text identifying the run, e.g. "phase2_dryrun_gpu"
  raw_text         full model output exactly as returned (thinking blocks included)
  extracted        the answer as extracted by the grader (None until graded; grade.py fills it in its scores file)
  tokens_in / tokens_out / tokens_reasoning   ints or None
  latency_ms       wall-clock per call
  cost_usd         list-price cost of the call (0.0 for local / free)
  error            None, or a short error string (then raw_text is "")
"""

from __future__ import annotations

import json
from pathlib import Path

FIELDS = ("task_id", "model", "provider", "run_id", "raw_text", "extracted",
          "tokens_in", "tokens_out", "tokens_reasoning", "latency_ms", "cost_usd", "error")


def make_record(task_id, model, provider, run_id, raw_text="", extracted=None, tokens_in=None, tokens_out=None,
                tokens_reasoning=None, latency_ms=None, cost_usd=0.0, error=None) -> dict:
    return {"task_id": task_id, "model": model, "provider": provider, "run_id": run_id, "raw_text": raw_text,
            "extracted": extracted, "tokens_in": tokens_in, "tokens_out": tokens_out,
            "tokens_reasoning": tokens_reasoning, "latency_ms": latency_ms, "cost_usd": cost_usd, "error": error}


def validate_record(r: dict) -> list:
    errs = [f"missing {k}" for k in FIELDS if k not in r]
    if not errs and not isinstance(r["raw_text"], str):
        errs.append("raw_text not str")
    return errs


def read_answers(path) -> list:
    out = []
    for i, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            r = json.loads(line)
            errs = validate_record(r)
            if errs:
                raise ValueError(f"{path}:{i}: {errs}")
            out.append(r)
    return out


def append_answer(path, rec: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
