import json

from router.validators import summary_constraints_from_prompt, validate


def ok(cat, prompt, resp):
    return validate(cat, prompt, resp).ok


def test_empty_and_think():
    assert not ok("math", "q", "")
    assert not ok("math", "q", "<think>working it out ... ANSWER: 4")
    assert ok("math", "q", "<think>x</think>so\nANSWER: 4")


def test_math():
    assert ok("math", "p", "work\nANSWER: 1,234")
    assert ok("math", "p", "ANSWER: 12.5")
    assert not ok("math", "p", "the answer is 12")
    assert not ok("math", "p", "ANSWER: twelve")


def test_logic():
    assert ok("logic", "Ann, Bo and Cy ran", "ANSWER: Bo")
    assert not ok("logic", "Ann, Bo and Cy ran", "ANSWER: Zed")
    assert not ok("logic", "Ann, Bo and Cy ran", "ANSWER: it depends on who finished where")
    assert not ok("logic", "Ann", "Bo")


def test_sentiment():
    assert ok("sentiment", "p", "It is upbeat.\nANSWER: positive")
    assert not ok("sentiment", "p", "ANSWER: happy")
    assert not ok("sentiment", "p", "positive")


def test_ner():
    prompt = "Priya Shah met Acme Corp in Paris on 3 May 2021."
    good = json.dumps([{"text": "Priya Shah", "type": "PERSON"}, {"text": "Paris", "type": "LOCATION"}])
    assert ok("ner", prompt, good)
    assert ok("ner", prompt, "```json\n" + good + "\n```")
    assert not ok("ner", prompt, "Entities: Priya Shah, Paris")
    assert not ok("ner", prompt, json.dumps([{"text": "Priya Shah", "type": "ANIMAL"}]))
    assert not ok("ner", prompt, json.dumps([{"text": "Zed Zorro", "type": "PERSON"}]))
    assert not ok("ner", prompt, "[]")


def test_code():
    prompt = "Write `def add(a, b)` that adds."
    assert ok("code_gen", prompt, "```python\ndef add(a, b):\n    return a + b\n```")
    assert not ok("code_gen", prompt, "```python\ndef add(a, b)\n    return a + b\n```")  # syntax error
    assert not ok("code_gen", prompt, "I would use the + operator.")
    assert not ok("code_gen", prompt, "```python\ndef subtract(a, b):\n    return a - b\n```")  # wrong name
    assert not ok("code_debug", "fix f(x)", "```python\nx = 1\n```")  # no def


def test_summary_constraints_parse():
    assert summary_constraints_from_prompt("Summarise as exactly 3 bullet points") == {"bullets": 3}
    assert summary_constraints_from_prompt("in exactly two sentences:") == {"sentences": 2}
    assert summary_constraints_from_prompt("in no more than 35 words") == {"max_words": 35}
    assert summary_constraints_from_prompt("Condense this passage in exactly one sentence.") == {"sentences": 1}


def test_summary():
    p = "Summarise the following text in exactly two sentences: ..."
    assert ok("summarisation", p, "First point. Second point.")
    assert not ok("summarisation", p, "Only one sentence here.")
    p3 = "Summarise as exactly 3 bullet points (each line starting with '- '): ..."
    assert ok("summarisation", p3, "- a\n- b\n- c")
    assert not ok("summarisation", p3, "- a\n- b")
    assert ok("summarisation", p3, "Here is a summary:\n- a\n- b\n- c")
    pw = "Summarise in no more than 5 words: ..."
    assert ok("summarisation", pw, "Short and sweet summary.")
    assert not ok("summarisation", pw, "This summary is much too long to fit")


def test_factual_and_language():
    assert ok("factual", "q", "Photosynthesis converts light energy into chemical energy in plants.")
    assert not ok("factual", "q", "Photosynthesis converts light energy into chemical energy in")  # truncated
    assert not ok("factual", "q", "word " * 200 + ".")
    assert not ok("factual", "q", "The pound 镑 is a currency of the UK people.")
