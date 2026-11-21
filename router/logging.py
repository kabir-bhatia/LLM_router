"""One JSONL line per routed request (thread-safe, append-only).

Prompt text is NOT logged by default (only its length and a short hash); the trace keeps every step's model, outcome, reason,
tokens (incl. reasoning tokens), latency and cost, but never the model's answer text.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from pathlib import Path
from typing import Optional


def log_record(result, request_id: Optional[str] = None, task_id: Optional[str] = None, log_prompt: bool = False, **extra) -> dict:
    p = result.prompt or ""
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()), "request_id": request_id or uuid.uuid4().hex[:12],
           "task_id": task_id, "prompt_chars": len(p), "prompt_sha1": hashlib.sha1(p.encode("utf-8")).hexdigest()[:12],
           "category": result.category, "difficulty": result.difficulty, "label_source": result.label_source,
           "plan": result.plan, "layer": result.layer, "model": result.model, "escalated": result.escalated,
           "cost_usd": result.cost_usd, "b1_cost_usd": result.b1_cost_usd, "savings_usd": result.savings_usd,
           "latency_ms": result.latency_ms, "error": result.error, "trace": result.trace}
    if log_prompt:
        rec["prompt"] = p
    rec.update(extra)
    return rec


class RequestLogger:
    def __init__(self, path):
        self.path = Path(path) if path else None
        self._lock = threading.Lock()
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, result, **kw) -> dict:
        rec = log_record(result, **kw)
        if self.path:
            line = json.dumps(rec, ensure_ascii=False, default=str)
            with self._lock, open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        return rec
