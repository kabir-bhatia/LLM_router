"""Output validators for the router's local layer (Layer 2).

A local answer is accepted only if it passes its category's validator; otherwise the router escalates to the
paid API. The validators use ONLY the prompt and the response (never gold), so they can run in production.
They check form, not correctness: a wrong but well-formed answer passes (that is the accuracy risk of routing
locally, measured by the cascade replay).

    validate(category, prompt, response) -> Validation(ok, problems)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from eval.graders.code_tests import extract_code
from eval.graders.common import extract_answer_line, strip_thinking
from eval.graders.constraint import check_constraints, summary_text
from eval.graders.language import non_english_chars
from eval.graders.ner_f1 import parse_entities

SENTIMENT_LABELS = ("positive", "negative", "mixed", "neutral")
NER_TYPES = {"PERSON", "ORG", "LOCATION", "DATE"}
NUMBER_RE = re.compile(r"^[-+]?\d+(?:\.\d+)?$")
WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}
FACTUAL_MAX_WORDS = 150  # instruction says 120; 25% slack so a few extra words don't trigger a paid call


@dataclass
class Validation:
    ok: bool
    problems: list = field(default_factory=list)


def _num(tok: str):
    tok = tok.lower()
    return int(tok) if tok.isdigit() else WORD_NUM.get(tok)


def summary_constraints_from_prompt(prompt: str) -> dict:
    """Parse the length/format request out of the user's prompt: 'exactly 3 bullet points',
    'in exactly two sentences', 'in one sentence', 'no more than 35 words', 'at most/under N words'."""
    cons = {}
    low = prompt.lower()
    m = re.search(r"(?:exactly\s+)?(\d+|one|two|three|four|five|six)\s+bullet", low)
    if m and _num(m.group(1)):
        cons["bullets"] = _num(m.group(1))
    m = re.search(r"(?:exactly\s+)?(\d+|one|two|three|four|five|six)\s+sentences?\b", low)
    if m and _num(m.group(1)):
        cons["sentences"] = _num(m.group(1))
    m = re.search(r"(?:no more than|at most|under|within|max(?:imum)?(?: of)?|up to|fewer than|less than)\s+(\d+)\s+words", low)
    if m:
        cons["max_words"] = int(m.group(1))
    return cons


def _common(response: str) -> list:
    problems = []
    if not (response or "").strip():
        return ["empty response"]
    low = response.lower()
    if "<think>" in low and "</think>" not in low:
        problems.append("unterminated <think> (truncated reasoning)")
    body = strip_thinking(response)
    if not body.strip():
        problems.append("nothing outside <think>")
    bad = non_english_chars(response)
    if bad:
        problems.append(f"non-English script: {''.join(bad[:5])}")
    return problems


def _v_math(prompt, response):
    ans = extract_answer_line(response)
    if ans is None:
        return ["no ANSWER: line"]
    boxed = re.search(r"\\boxed\{\s*([-+]?[\d,]+(?:\.\d+)?)\s*\}", ans)
    if boxed:  # "Final Answer: ... \boxed{750}" is a clear numeric answer
        ans = boxed.group(1)
    clean = ans.replace(",", "").replace("$", "").replace("₹", "").strip()
    if not NUMBER_RE.match(clean):
        return [f"answer is not a number: {ans[:30]!r}"]
    return []


def _v_logic(prompt, response):
    ans = extract_answer_line(response)
    if ans is None:
        return ["no ANSWER: line"]
    if len(ans.split()) > 4:
        return [f"answer is not a short name/item: {ans[:40]!r}"]
    if ans.lower() not in prompt.lower():
        return [f"answer {ans!r} does not occur in the puzzle"]
    return []


def _v_sentiment(prompt, response):
    ans = extract_answer_line(response)
    if ans is None:
        return ["no ANSWER: line"]
    first = re.split(r"[\s.,;:!-]+", ans.strip().lower())[0] if ans.strip() else ""
    if first not in SENTIMENT_LABELS:  # "positive. The review ..." counts (the grader takes the first label too)
        return [f"invalid label {ans[:30]!r}"]
    return []


def _v_ner(prompt, response):
    ents = parse_entities(response)
    if ents is None:
        return ["NER output does not parse as JSON"]
    if not ents:
        return ["no entities returned"]
    problems = []
    low = prompt.lower()
    for text, typ in ents:
        if str(typ).upper() not in NER_TYPES:
            problems.append(f"invalid type {typ!r}")
        # dates are normalised to ISO by parse_entities, so only non-date spans can be checked against the prompt
        if str(typ).upper() != "DATE" and str(text).lower() not in low:
            problems.append(f"span not in prompt: {str(text)[:30]!r}")
    return problems[:3]


def _v_code(prompt, response):
    code = extract_code(response)
    if not code or not code.strip():
        return ["no code block"]
    try:
        compile(code, "<answer>", "exec")
    except (SyntaxError, ValueError) as e:
        return [f"code does not compile: {type(e).__name__}"]
    defs = re.findall(r"^\s*def\s+([A-Za-z_]\w*)\s*\(", code, re.MULTILINE)
    if not defs:
        return ["no function definition"]
    wanted = set(re.findall(r"\b([A-Za-z_]\w*)\s*\(", prompt))
    if wanted and not (set(defs) & wanted):
        return [f"none of {defs[:3]} is named in the request"]
    return []


def _v_summary(prompt, response):
    cons = summary_constraints_from_prompt(prompt)
    text = summary_text(response)
    if not text.strip():
        return ["empty summary"]
    if not cons:
        return []  # no checkable constraint in the prompt
    ok, problems = check_constraints(text, cons)
    return problems


def _v_factual(prompt, response):
    body = strip_thinking(response).strip()
    n = len(body.split())
    problems = []
    if n < 5:
        problems.append("answer is too short")
    if n > FACTUAL_MAX_WORDS:
        problems.append(f"{n} words (limit {FACTUAL_MAX_WORDS})")
    if body and not re.search(r"[.!?)\"'`*\]]\s*$", body):
        problems.append("looks truncated (no terminal punctuation)")
    return problems


_CATEGORY = {"math": _v_math, "logic": _v_logic, "sentiment": _v_sentiment, "ner": _v_ner,
             "code_debug": _v_code, "code_gen": _v_code, "summarisation": _v_summary, "factual": _v_factual}


def validate(category: str, prompt: str, response: str) -> Validation:
    problems = _common(response)
    if "empty response" in problems:
        return Validation(False, problems)
    problems += _CATEGORY[category](prompt, response)
    return Validation(not problems, problems)

