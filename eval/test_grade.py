"""Tests for the answer store and the grading pipeline."""
from eval.answers import append_answer, make_record, read_answers
from eval.grade import TASKS_PATH, grade_answers, summarise, wilson
from eval.task_schema import load_tasks


def test_wilson():
    assert wilson(0, 0) == (0.0, 0.0)
    lo, hi = wilson(10, 10)
    assert hi == 1.0 and 0.70 < lo < 0.75
    lo, hi = wilson(5, 10)
    assert abs(lo - 0.237) < 0.005 and abs(hi - 0.763) < 0.005


def test_roundtrip_and_grade(tmp_path):
    tasks = load_tasks(TASKS_PATH)
    m = next(t for t in tasks if t["category"] == "math" and t["split"] == "dev")
    s = next(t for t in tasks if t["category"] == "sentiment" and t["split"] == "dev")
    f = next(t for t in tasks if t["category"] == "factual" and t["split"] == "dev")
    p = tmp_path / "a.jsonl"
    append_answer(p, make_record(m["id"], "x", "t", "r", f"ANSWER: {m['gold']['answer']}"))
    append_answer(p, make_record(s["id"], "x", "t", "r", "I really don't know"))
    append_answer(p, make_record(f["id"], "x", "t", "r", "some text"))
    append_answer(p, make_record(tasks[0]["id"], "x", "t", "r", "", error="timeout"))
    rows = grade_answers(read_answers(p), tasks)
    assert rows[0]["passed"] is True and not rows[0]["unparsed"]
    assert rows[1]["passed"] is False and rows[1]["unparsed"]
    assert rows[2]["passed"] is None  # needs the judge
    assert rows[3]["unparsed"] and rows[3]["passed"] is False
    summ = summarise(rows)["x"]
    assert summ["cells"]["math"]["all"]["k"] == 1
    assert summ["cells"]["factual"]["all"]["pending"] >= 1
    assert summ["unparsed_total"] == 2
