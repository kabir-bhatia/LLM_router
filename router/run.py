"""Batch CLI: route a file of tasks.

    python -m router.run tasks.json results.json --log run.jsonl [--deadline-s 3000] [--api-workers 8] [--resume]
                         [--policy path.json] [--labels labels.json] [--embed cache|inprocess] [--limit N] [--dry-run]

tasks.json   list of {"id": ..., "prompt": ...} (extra fields are ignored; the router classifies by itself)
results.json {"meta": {...}, "results": [one row per finished task, in input order]}, rewritten atomically after EVERY task,
             so an early stop (deadline, crash, Kaggle session end) always leaves valid output; --resume skips finished ids.
--log        JSONL, one line per request (router/logging.py)
--labels     optional {id: [category, difficulty]} to bypass the classifiers (replay / ablation runs)

Concurrency: local-model calls are serialised (one at a time: CPU), paid-API calls run in a thread pool (--api-workers).
Global deadline: no task starts after it, an API call's timeout is clamped to the time left, and unstarted tasks are written
as status "skipped_deadline" (empty answer) so the output still lists every task.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional

from router.logging import RequestLogger
from router.models import ModelReply, kind_of


class LaneClient:
    """Wraps a model client: local calls take a lock (sequential), API calls run concurrently, every call respects the deadline."""

    def __init__(self, inner, deadline: Optional[float] = None, clock: Callable[[], float] = time.monotonic):
        self.inner, self.deadline, self.clock = inner, deadline, clock
        self.prices = getattr(inner, "prices", None)
        self._local = threading.Lock()

    def _clamp(self, timeout):
        if self.deadline is None:
            return timeout, False
        left = self.deadline - self.clock()
        if left <= 0:
            return None, True
        return (min(timeout, left) if timeout else left), False

    def chat(self, model, system, user, max_tokens, timeout=None, json_mode=False) -> ModelReply:
        if kind_of(model) == "local":
            with self._local:
                timeout, over = self._clamp(timeout)
                if over:
                    return ModelReply(model, error="global deadline reached")
                return self.inner.chat(model, system, user, max_tokens, timeout=timeout, json_mode=json_mode)
        timeout, over = self._clamp(timeout)
        if over:
            return ModelReply(model, error="global deadline reached")
        return self.inner.chat(model, system, user, max_tokens, timeout=timeout, json_mode=json_mode)


def _write_atomic(path: Path, payload: dict):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    os.replace(tmp, path)


def result_row(task_id, res, status="done") -> dict:
    d = res.to_dict()
    d.pop("prompt", None)
    return {"id": task_id, "status": status, **d}


def run_batch(tasks: list, router, results_path, logger: Optional[RequestLogger] = None, labels: Optional[dict] = None,
              api_workers: int = 8, deadline_s: Optional[float] = None, resume: bool = False, limit: Optional[int] = None,
              clock: Callable[[], float] = time.monotonic, progress: bool = True) -> dict:
    results_path = Path(results_path)
    t_start = clock()
    deadline = None if deadline_s is None else t_start + deadline_s
    inner = router.client
    router.client = LaneClient(inner, deadline, clock)
    try:
        tasks = tasks[:limit] if limit else tasks
        ids = [t["id"] for t in tasks]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate task ids")
        done = {}
        if resume and results_path.exists():
            prev = json.loads(results_path.read_text(encoding="utf-8"))
            done = {r["id"]: r for r in prev.get("results", []) if r.get("status") == "done"}
        rows = dict(done)
        lock = threading.Lock()
        meta = {"n_tasks": len(tasks), "policy": getattr(router.policy, "source", ""), "api_workers": api_workers,
                "deadline_s": deadline_s, "started": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())}

        def flush(final=False):
            ordered = [rows[i] for i in ids if i in rows]
            m = {**meta, "finished": len(ordered), "complete": final and len(ordered) == len(tasks),
                 "total_cost_usd": sum(r.get("cost_usd") or 0 for r in ordered),
                 "elapsed_s": round(clock() - t_start, 1)}
            _write_atomic(results_path, {"meta": m, "results": ordered})

        def work(t):
            if t["id"] in rows:
                return
            if deadline is not None and clock() >= deadline:
                row = {"id": t["id"], "status": "skipped_deadline", "answer": "", "layer": "error", "error": "global deadline reached"}
            else:
                lab = tuple(labels[t["id"]]) if labels and t["id"] in labels else None
                res = router.route(t["prompt"], labels=lab)
                if logger:
                    logger.write(res, task_id=t["id"])
                row = result_row(t["id"], res)
            with lock:
                rows[t["id"]] = row
                flush()
                if progress:
                    print(f"[{len(rows)}/{len(tasks)}] {t['id']} {row.get('layer')} {row.get('model', '')}", file=sys.stderr, flush=True)

        flush()  # valid (possibly empty) output exists from the start
        with ThreadPoolExecutor(max_workers=max(1, api_workers)) as pool:
            list(pool.map(work, tasks))
        flush(final=True)
        return json.loads(results_path.read_text(encoding="utf-8"))
    finally:
        router.client = inner


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m router.run", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tasks")
    ap.add_argument("results")
    ap.add_argument("--log", default=None)
    ap.add_argument("--policy", default=None, help="routing policy JSON (default: ROUTER_POLICY_PATH / config)")
    ap.add_argument("--labels", default=None)
    ap.add_argument("--api-workers", type=int, default=8)
    ap.add_argument("--deadline-s", type=float, default=None)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--embed", choices=("cache", "inprocess"), default="cache",
                    help="MiniLM embeddings for the classifier: 'cache' (default, laptop: disk cache + one subprocess per unseen prompt) or "
                         "'inprocess' (Kaggle/servers: load the model once and embed all prompts up front in batches)")
    ap.add_argument("--dry-run", action="store_true", help="classify and print each task's plan; call no model")
    a = ap.parse_args(argv)

    from router.config import RouterConfig
    from router.pipeline import build_router
    cfg = RouterConfig()
    if a.policy:
        cfg.policy_path = Path(a.policy)
    tasks = json.loads(Path(a.tasks).read_text(encoding="utf-8"))
    labels = json.loads(Path(a.labels).read_text(encoding="utf-8")) if a.labels else None
    if a.dry_run:
        from router.fakes import FakeClient
        router = build_router(cfg, client=FakeClient(lambda *x: "dry run"))
        for t in tasks[:a.limit] if a.limit else tasks:
            r = router.route(t["prompt"], labels=tuple(labels[t["id"]]) if labels and t["id"] in labels else None)
            print(t["id"], r.category, r.difficulty, " -> ".join(r.plan))
        return 0
    labeler = None
    if a.embed == "inprocess" and not labels:
        from router.embed_fast import InProcessEmbedder
        from router.labeler import Labeler
        emb = InProcessEmbedder()
        emb.prepare([t["prompt"] for t in (tasks[:a.limit] if a.limit else tasks)])
        labeler = Labeler(embed_fn=emb)
    router = build_router(cfg, labeler=labeler)
    out = run_batch(tasks, router, a.results, RequestLogger(a.log), labels, a.api_workers, a.deadline_s, a.resume, a.limit)
    m = out["meta"]
    print(f"finished {m['finished']}/{m['n_tasks']}  cost ${m['total_cost_usd']:.4f}  {m['elapsed_s']}s  complete={m['complete']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
