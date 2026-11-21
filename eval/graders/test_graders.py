"""Self-tests: every grader must score known-good and known-bad answers correctly.

Real model outputs come from eval/results/kaggle_smoke/results_gpu_smoke.json.
Run: .venv/Scripts/python.exe -m pytest eval/graders
"""

import json
from pathlib import Path

import pytest

from eval.graders import grade
from eval.graders.code_tests import extract_code, run_tests
from eval.graders.constraint import count_sentences, count_words
from eval.graders.judge import build_judge_prompt, parse_verdict
from eval.graders.ner_f1 import grade_ner, norm_date

SMOKE = json.loads((Path(__file__).parents[1] / "results" / "kaggle_smoke" / "results_gpu_smoke.json")
                   .read_text(encoding="utf-8"))


def smoke(model, pid):
    return next(r["text"] for r in SMOKE if r["model"] == model and r["id"] == pid)


def T(grader, gold, category="math"):
    return {"grader": grader, "gold": gold, "category": category}


# ---------------- numeric ----------------
MATH = T("numeric", {"answer": 270, "tolerance": 0})


@pytest.mark.parametrize("model", ["llama3.2:3b", "gemma3:4b"])
def test_numeric_smoke_correct(model):
    assert grade(MATH, smoke(model, "smoke-math")).passed is True


def test_numeric_smoke_qwen_coder_wrong():
    # qwen2.5-coder:1.5b got this problem wrong (hand check: "150")
    assert grade(MATH, smoke("qwen2.5-coder:1.5b", "smoke-math")).passed is False


@pytest.mark.parametrize("text,ok", [
    ("Working...\nANSWER: 270", True),
    ("ANSWER: $270", True),
    ("ANSWER: 1,250", False),
    ("**ANSWER: 270**", True),
    ("so it's \\boxed{270}", True),
    ("The result is 270 notebooks.", True),
    ("ANSWER: 271", False),
    ("ANSWER: 27", False),
    ("I could not solve this.", False),
    ("<think>maybe 270</think>ANSWER: 150", False),
])
def test_numeric_formats(text, ok):
    assert grade(MATH, text).passed is ok


def test_numeric_tolerance():
    t = T("numeric", {"answer": 83.33, "tolerance": 0.01})
    assert grade(t, "ANSWER: 83.33").passed
    assert grade(t, "ANSWER: 83.34").passed
    assert not grade(t, "ANSWER: 83.4").passed
    assert grade(T("numeric", {"answer": 1250, "tolerance": 0}), "ANSWER: 1,250").passed


# ---------------- exact (logic) ----------------
LOGIC = T("exact", {"answer": "Ben", "choices": ["Ana", "Ben", "Cy"]}, "logic")


def test_exact_smoke():
    assert grade(LOGIC, smoke("gemma3:4b", "smoke-logic")).passed is True      # states Ben
    assert grade(LOGIC, smoke("qwen2.5-coder:1.5b", "smoke-logic")).passed is False  # says Ana
    assert grade(LOGIC, smoke("llama3.2:3b", "smoke-logic")).passed is False


@pytest.mark.parametrize("text,ok", [
    ("ANSWER: Ben", True), ("ANSWER: ben.", True), ("ANSWER: **Ben**", True), ("ANSWER: Ana", False),
    ("Ben does not own fish.\nANSWER: Ana", False),
    ("Reasoning mentions Ana and Ben.\nSo the cat owner is Ben", True),
    ("Therefore Ana or Ben owns it", False),
])
def test_exact_formats(text, ok):
    assert grade(LOGIC, text).passed is ok


# ---------------- label (sentiment) ----------------
SENT = T("label", {"label": "mixed"}, "sentiment")


def test_label_smoke():
    assert grade(SENT, smoke("gemma3:4b", "smoke-sent")).passed is True
    assert grade(SENT, smoke("llama3.2:3b", "smoke-sent")).passed is True
    assert grade(SENT, smoke("qwen2.5-coder:1.5b", "smoke-sent")).passed is False  # "Negative."
    assert grade(SENT, smoke("gemma3:4b", "smoke-sent")).meta["reason_present"]


@pytest.mark.parametrize("text,ok", [
    ("Mixed because of both.\nANSWER: mixed", True),
    ("ANSWER: Positive", False),
    ("Reason: but overall...\nANSWER: MIXED.", True),
    ("Mixed - positive and negative", True),
    ("Facts only, no positive or negative language. ANSWER: neutral", False),   # inline marker, gold is mixed
])
def test_label_formats(text, ok):
    assert grade(SENT, text).passed is ok


# ---------------- NER ----------------
NER_GOLD = {"entities": [{"text": "Priya Nair", "type": "PERSON"}, {"text": "Infosys", "type": "ORG"},
                         {"text": "Pune", "type": "LOCATION"}, {"text": "3 March 2021", "type": "DATE"}]}
NER = T("ner_f1", NER_GOLD, "ner")


@pytest.mark.parametrize("model", ["gemma3:4b", "qwen2.5-coder:1.5b", "llama3.2:3b"])
def test_ner_smoke_correct(model):
    r = grade(NER, smoke(model, "smoke-ner"))
    assert r.passed and r.score == 1.0, r.detail


def test_ner_wrong_types_and_missing():
    bad = '[{"text":"Priya Nair","type":"ORG"},{"text":"Infosys","type":"ORG"},{"text":"Pune","type":"LOCATION"}]'
    r = grade(NER, bad)
    assert not r.passed and 0 < r.score < 1
    assert not grade(NER, "Priya Nair is a person.").passed


def test_ner_tolerances():
    alt = '{"PER": ["priya  nair"], "ORGANIZATION": ["Infosys"], "GPE": ["Pune"], "DATE": ["March 3, 2021"]}'
    assert grade(NER, alt).passed
    assert not grade(NER, alt.replace("Pune", "Pune city")).passed
    assert norm_date("3rd March, 2021") == norm_date("2021-03-03") == "2021-03-03"
    extra = json.dumps([{"text": "Priya Nair", "type": "PERSON"}, {"text": "Infosys", "type": "ORG"},
                        {"text": "Pune", "type": "LOCATION"}, {"text": "3 March 2021", "type": "DATE"},
                        {"text": "joined", "type": "ORG"}])
    assert not grade(NER, extra).passed  # precision matters


# ---------------- code ----------------
DEBUG = T("code_tests", {"entry_point": "avg", "tests": [
    "assert avg([1, 2, 3]) == 2", "assert avg([5]) == 5", "assert avg([1, 2]) == 1.5"]}, "code_debug")
GEN = T("code_tests", {"entry_point": "second_largest", "tests": [
    "assert second_largest([1, 2, 3]) == 2", "assert second_largest([3, 3, 3]) is None",
    "assert second_largest([5]) is None", "assert second_largest([1, 5, 5, 4]) == 4",
    "assert second_largest([-1, -2]) == -2"]}, "code_gen")


@pytest.mark.parametrize("model", ["qwen2.5-coder:1.5b", "llama3.2:3b", "gemma3:4b"])
def test_code_debug_smoke_fixed(model):
    assert grade(DEBUG, smoke(model, "smoke-debug")).passed is True


@pytest.mark.parametrize("model", ["qwen2.5-coder:1.5b", "gemma3:4b", "llama3.2:3b"])
def test_code_gen_smoke(model):
    r = grade(GEN, smoke(model, "smoke-codegen"))  # all three reference-style solutions are correct
    assert r.passed is True, r.detail


def test_code_buggy_fails():
    buggy = "```python\ndef avg(xs):\n    return sum(xs) / len(xs) - 1\n```"
    assert grade(DEBUG, buggy).passed is False


def test_code_timeout_and_crash_and_network():
    loop = "```python\ndef avg(xs):\n    while True:\n        pass\n```"
    r = grade(DEBUG, loop)
    assert r.passed is False and "timeout" in r.detail
    assert grade(DEBUG, "```python\ndef avg(xs:\n```").passed is False
    net = ("```python\nimport socket\ndef avg(xs):\n    socket.create_connection(('example.com', 80))\n"
           "    return sum(xs)/len(xs)\n```")
    assert grade(DEBUG, net).passed is False
    assert grade(DEBUG, "no code here").passed is False


def test_code_extract_prefers_block_with_entry_point():
    resp = "```python\nprint(avg([1]))\n```\nfixed:\n```python\ndef avg(xs):\n    return sum(xs)/len(xs)\n```\n"
    assert "def avg" in extract_code(resp, "avg")
    assert grade(DEBUG, resp).passed


def test_run_tests_isolated():
    passes, errs, fatal = run_tests("def f(x):\n    return x\n", ["assert f(1)==1", "assert f(1)==2"])
    assert passes == [True, False] and fatal is None


# ---------------- constraint ----------------
def test_constraint_sentences():
    one = T("constraint", {"constraints": {"sentences": 1}}, "summarisation")
    assert grade(one, smoke("gemma3:4b", "smoke-summ")).needs_judge in (True, False)  # runs without crash
    assert grade(one, "The council approved bike lanes after consultation, with a review promised.").needs_judge
    r = grade(one, "The council approved lanes. It will review parking.")
    assert r.passed is False and "2 sentences" in r.detail
    assert count_sentences("Dr. Rao spent 3.5 million. Then left.") == 2
    assert count_sentences("The plan costs $4.2m and runs 3 yrs") == 1


def test_constraint_words_and_bullets():
    w = T("constraint", {"constraints": {"max_words": 8}}, "summarisation")
    assert grade(w, "Council approves new bike lanes after consultations.").needs_judge
    assert grade(w, "The council has approved a brand new network of protected bike lanes today.").passed is False
    b = T("constraint", {"constraints": {"bullets": 3}}, "summarisation")
    assert grade(b, "- one\n- two\n- three").needs_judge
    assert grade(b, "- one\n- two").passed is False
    assert grade(b, "Here are bullets:\n- one\n- two\n- three").needs_judge  # lead-in line tolerated (Phase 2)
    assert grade(b, "Bullets follow, as asked.\n- one\n- two\n- three").passed is False  # other prose outside bullets
    assert count_words("- a b c\n- d") == 4


# ---------------- judge stub ----------------
def test_judge_prompt_and_verdict():
    p = build_judge_prompt("Q?", "ref", ["k1", "k2"], "ans")
    assert "Q?" in p and "- k1" in p and "ans" in p
    assert parse_verdict("VERDICT: PASS - ok") is True
    assert parse_verdict("verdict: fail, wrong") is False
    assert parse_verdict("no idea") is None
    f = {"grader": "judge", "gold": {"reference": "x"}, "category": "factual"}
    assert grade(f, "some answer").needs_judge


def test_dispatch_unknown_grader():
    with pytest.raises(KeyError):
        grade({"grader": "nope", "gold": {}}, "x")


def test_inline_answer_marker():
    neutral = T("label", {"label": "neutral"}, "sentiment")
    # real GLM output: marker at the end of the reasoning line, first label word in the text is 'positive'
    text = "A factual statistic without positive or negative language. ANSWER: neutral"
    assert grade(neutral, text).passed is True
    assert grade(MATH, "so the total is 12, giving ANSWER: 270").passed is True


def test_ner_titles_possessive_and_alternatives():
    gold = {"entities": [{"text": "Kavita Rao", "type": "PERSON"}, {"text": "Kenya", "type": "LOCATION"}]}
    t = T("ner_f1", gold, "ner")
    ok = '[{"text":"Dr. Kavita Rao","type":"PERSON"},{"text":"Kenya\'s","type":"LOCATION"}]'
    assert grade(t, ok).passed
    assert grade(t, ok.replace("Dr. ", "Prof ")).passed
    # a title is only stripped from PERSON spans
    org = T("ner_f1", {"entities": [{"text": "Dr Reddy Labs", "type": "ORG"}]}, "ner")
    assert grade(org, '[{"text":"Dr Reddy Labs","type":"ORG"}]').passed
    assert not grade(org, '[{"text":"Reddy Labs","type":"ORG"}]').passed
    alt = {"entities": [{"text": "Kenya", "type": "LOCATION"}],
           "alternatives": [{"entities": [{"text": "Kenya", "type": "ORG"}]},
                            {"entities": [{"text": "AIIMS", "type": "ORG"}, {"text": "Delhi", "type": "LOCATION"}]}]}
    ta = T("ner_f1", alt, "ner")
    assert grade(ta, '[{"text":"Kenya","type":"LOCATION"}]').passed
    assert grade(ta, '[{"text":"Kenya","type":"ORG"}]').passed
    assert grade(ta, '[{"text":"AIIMS","type":"ORG"},{"text":"Delhi","type":"LOCATION"}]').passed
    assert not grade(ta, '[{"text":"Kenya","type":"PERSON"}]').passed
    # mixing readings is not allowed
    assert not grade(ta, '[{"text":"Kenya","type":"ORG"},{"text":"Delhi","type":"LOCATION"}]').passed


def test_judge_prompt_required_vs_optional():
    p = build_judge_prompt("Q?", "ref", ["must"], "ans", optional=["nice"])
    assert "REQUIRED" in p and "- must" in p and "- nice" in p and "must NOT cause a FAIL" in p


def test_ner_bare_object_sequence():
    """Phase 2 dry run: qwen3:1.7b emits objects without the enclosing list, with or without commas."""
    gold = {"entities": [{"text": "Priya Nair", "type": "PERSON"}, {"text": "Google", "type": "ORG"}]}
    a = '{"text": "Priya Nair", "type": "PERSON"}, {"text": "Google", "type": "ORG"}'
    b = '{"text": "Priya Nair", "type": "PERSON"}{"text": "Google", "type": "ORG"}'
    assert grade_ner(a, gold).passed and grade_ner(b, gold).passed
    # a wrong type still fails
    assert not grade_ner('{"text": "Priya Nair", "type": "ORG"}, {"text": "Google", "type": "ORG"}', gold).passed


def test_answer_marker_on_next_line_and_doubled():
    """Phase 2 dry run: 'Final answer:' on one line then 'ANSWER: X' on the next; '**Answer:** ANSWER: X'."""
    from eval.graders.common import extract_answer_line
    assert extract_answer_line("### Final answer:\nANSWER: Ivan") == "Ivan"
    assert extract_answer_line("**Answer:** ANSWER: Ivan") == "Ivan"
    assert extract_answer_line("so\nANSWER: 14880") == "14880"
    assert extract_answer_line("Answer:\nIvan") is None


def test_summary_lead_in_line_is_ignored_but_other_text_is_not():
    """Phase 2 dry run: gemma3:1b prefixes 'Here's a summary ...:' before the bullets."""
    from eval.graders.constraint import grade_constraint
    gold = {"constraints": {"bullets": 3}, "key_facts": []}
    ok = "Here's a summary in 3 bullet points:\n\n* a b\n* c d\n* e f\n"
    r = grade_constraint(ok, gold)
    assert r.needs_judge and r.meta["constraint_ok"]
    bad = "The text is about X.\n* a b\n* c d\n* e f"
    assert grade_constraint(bad, gold).passed is False
    assert grade_constraint("Here's a summary:\n* a\n* b", gold).passed is False  # still only 2 bullets
