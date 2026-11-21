"""A model client that serves RECORDED answers (Phase 3 benchmark + Phase 4 translator run) instead of calling models.

Used by the replay-consistency check: the production Router is run over the dev tasks with this client, and its per-task path,
correctness and cost must equal eval/phase4/policy_lib.replay() on the same policy. Dev split only.

A call is matched to a task by the user text (the benchmark sends the raw prompt; the D13 translators send "Problem: "/"Puzzle: " + prompt).
Latency is reported as 0 so the 30 s local budget never fires (the replay has no time model; timeouts are covered by unit tests).
"""
from __future__ import annotations

import json
import threading
import zipfile
from pathlib import Path
from typing import Optional

from router.models import ModelReply, kind_of

ROOT = Path(__file__).resolve().parents[1]
PHASE3 = ROOT / "eval" / "results" / "phase3"
TRANSLATE_ZIP = ROOT / "eval" / "results" / "phase4" / "phase4_solver_translate.zip"


def _jsonl(text):
    return [json.loads(x) for x in text.splitlines() if x.strip()]


class RecordedClient:
    def __init__(self, tasks: list, api_rows: dict, local_answers: dict, translations: dict):
        """api_rows {(model, task_id): answer row}; local_answers {(model, task_id): raw text}; translations {(model, task_id): raw text}."""
        self.by_prompt = {t["prompt"]: t["id"] for t in tasks}
        assert len(self.by_prompt) == len(tasks), "dev prompts must be unique"
        self.api_rows, self.local, self.trans = api_rows, local_answers, translations
        self.calls = []
        self._lock = threading.Lock()

    @classmethod
    def from_disk(cls, tasks: list, answers: dict, kinds: dict) -> "RecordedClient":
        api_rows = {}
        for r in _jsonl((PHASE3 / "answers_api.jsonl").read_text(encoding="utf-8")):
            api_rows[(r["model"], r["task_id"])] = r
        local = {k: v for k, v in answers.items() if kinds.get(k[0]) == "local"}
        trans = {}
        if TRANSLATE_ZIP.exists():
            with zipfile.ZipFile(TRANSLATE_ZIP) as z:
                for r in _jsonl(z.read("translations.jsonl").decode("utf-8")):
                    if not r.get("error"):
                        trans[(r["model"], r["task_id"])] = r["raw_text"]
        return cls(tasks, api_rows, local, trans)

    def _task(self, user: str):
        for pre in ("Problem: ", "Puzzle: "):
            if user.startswith(pre) and user[len(pre):] in self.by_prompt:
                return self.by_prompt[user[len(pre):]], True
        return self.by_prompt.get(user), False

    def chat(self, model, system, user, max_tokens, timeout: Optional[float] = None, json_mode: bool = False) -> ModelReply:
        tid, translated = self._task(user)
        with self._lock:
            self.calls.append({"model": model, "task_id": tid, "translator": translated})
        if tid is None:
            return ModelReply(model, error="recorded: unknown prompt")
        if translated:
            raw = self.trans.get((model, tid))
            return ModelReply(model, text=raw, latency_ms=0) if raw is not None else ModelReply(model, error="recorded: no translation")
        if kind_of(model) == "local":
            raw = self.local.get((model, tid))
            return ModelReply(model, text=raw, latency_ms=0) if raw is not None else ModelReply(model, error="recorded: no local answer")
        r = self.api_rows.get((model, tid))
        if r is None:
            return ModelReply(model, error="recorded: no API answer")
        if r.get("error"):
            return ModelReply(model, error=r["error"], latency_ms=0)
        return ModelReply(model, text=r["raw_text"], tokens_in=r.get("tokens_in"), tokens_out=r.get("tokens_out"),
                          tokens_reasoning=r.get("tokens_reasoning"), latency_ms=0, cost_usd=r.get("cost_usd") or 0.0,
                          finish=r.get("finish_reason"))
