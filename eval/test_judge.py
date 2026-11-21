"""Offline tests for the judge plumbing (no network)."""
import json

import pytest

from eval.grade import TASKS_PATH
from eval.graders import judge as J
from eval.task_schema import load_tasks


def _task(cat):
    return next(t for t in load_tasks(TASKS_PATH) if t["category"] == cat and t["split"] == "dev")


def test_prompt_is_blind_and_has_rubric():
    for cat in ("factual", "summarisation"):
        p = J.judge_prompt_for_task(_task(cat), "Some answer text.")
        low = p.lower()
        assert "some answer text." in low and ("required key points" in low or "core facts" in low)
        assert not any(m in low for m in ("gemma", "qwen", "glm", "llama", "ollama"))


def test_summary_prompt_has_core_secondary_split():
    t = _task("summarisation")
    g = t["gold"]
    assert len(g["core_facts"]) == 2 and isinstance(g["secondary_facts"], list)
    p = J.judge_prompt_for_task(t, "A summary.")
    assert "CORE facts" in p and "SECONDARY facts" in p and "BOTH" in p
    assert all(c in p for c in g["core_facts"]) and all(s in p for s in g["secondary_facts"])
    assert "reverses a" in p and "dropping a qualifier" in p


def test_factual_prompt_has_popsci_clarification():
    assert "popular-science" in J.judge_prompt_for_task(_task("factual"), "x")


def test_budget_stop(tmp_path, monkeypatch):
    spend = tmp_path / "spend.json"
    spend.write_text(json.dumps({"fireworks_usd": 0.51}))
    monkeypatch.setattr(J, "SPEND_PATH", spend)
    monkeypatch.setattr(J, "CACHE_PATH", tmp_path / "cache.jsonl")
    with pytest.raises(J.BudgetExceeded):
        J.call_judge("qwen", "x", max_cost=0.50)


def test_parse_verdict():
    assert J.parse_verdict("VERDICT: PASS - ok") is True
    assert J.parse_verdict("<think>VERDICT: PASS</think>VERDICT: FAIL - missing") is False
    assert J.parse_verdict("no verdict") is None
