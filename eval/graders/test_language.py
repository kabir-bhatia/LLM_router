"""Self-tests for the D10 language check."""
from eval.grade import grade_answer
from eval.graders.language import has_non_english_script, non_english_chars


def test_flags_non_english_scripts():
    assert has_non_english_script("The answer is 42. 答案是42")
    assert has_non_english_script("Ответ: 42")
    assert has_non_english_script("こんにちは and hello")
    assert has_non_english_script("한국어")
    assert has_non_english_script("مرحبا")
    assert non_english_chars("abc 你好 你") == ["你", "好"]


def test_allows_english_accents_greek_symbols():
    assert not has_non_english_script("Plain English, 3.14, $5, 10%, naïve café Zoë José")
    assert not has_non_english_script("Area = π r^2, Δx, μ = 5; → ≤ °C × ÷ ✓")
    assert not has_non_english_script("")
    assert not has_non_english_script(None)


def test_ignores_thinking_block():
    assert not has_non_english_script("<think>我想一下</think>The answer is 7.")
    assert has_non_english_script("<think>ok</think>The answer is 七.")


def test_grade_answer_fails_regardless_of_content():
    task = {"id": "t", "category": "math", "difficulty": "easy", "split": "dev", "grader": "numeric",
            "prompt": "2+2?", "gold": {"answer": 4}}
    base = {"model": "m", "run_id": "r", "error": None}
    ok = grade_answer(task, dict(base, raw_text="ANSWER: 4"))
    bad = grade_answer(task, dict(base, raw_text="ANSWER: 4\n答案是4"))
    assert ok["passed"] is True and not ok["language_fail"]
    assert bad["passed"] is False and bad["language_fail"] and "non-English" in bad["detail"]


def test_language_fail_skips_judge():
    calls = []
    task = {"id": "f", "category": "factual", "difficulty": "easy", "split": "dev", "grader": "judge", "prompt": "Q?",
            "gold": {"question": "Q?", "reference": "r", "key_points": ["k"]}}
    ans = {"model": "m", "run_id": "r", "error": None, "raw_text": "这是答案"}
    row = grade_answer(task, ans, judge_fn=lambda *a: calls.append(a) or {"passed": True})
    assert row["passed"] is False and row["language_fail"] and not calls


def test_letterlike_symbols_are_not_other_scripts():
    # false positives found in Phase 3 (correct answers with technical notation)
    assert not has_non_english_script("bacteria ~0.5-5 µm; softmax(QKᵀ / √d_k) V")
    assert not has_non_english_script("Δx·Δp ≥ ℏ/2 and (1 + r/n)ⁿᵗ")
    assert has_non_english_script("150镑 pounds")
