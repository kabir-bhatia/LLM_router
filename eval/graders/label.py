"""Label grader (sentiment). Gold: {"label": "mixed", "labels": [...optional allowed set...]}."""

from __future__ import annotations

import re

from .common import GradeResult, extract_answer_line, strip_thinking

DEFAULT_LABELS = ("positive", "negative", "mixed", "neutral")


def _first_label(text: str, labels) -> str | None:
    best, pos = None, None
    for lab in labels:
        m = re.search(rf"(?<!\w){lab}(?!\w)", text, re.IGNORECASE)
        if m and (pos is None or m.start() < pos):
            best, pos = lab, m.start()
    return best


def grade_label(response: str, gold: dict) -> GradeResult:
    labels = tuple(gold.get("labels", DEFAULT_LABELS))
    want = gold["label"].lower()
    cand = extract_answer_line(response)
    how = "answer_line"
    got = _first_label(cand, labels) if cand else None
    if got is None:
        # lenient fallback: the first label word in the response ("Mixed - the review ...")
        got = _first_label(strip_thinking(response), labels)
        how = "fallback_first_label"
    if got is None:
        return GradeResult(False, 0.0, "no label found", None)
    ok = got == want
    body = strip_thinking(response)
    reason_present = len(re.sub(r"(?im)^\s*answer\s*:.*$", "", body).split()) >= 4
    return GradeResult(ok, float(ok), f"got {got} want {want} via {how}", got,
                       meta={"how": how, "reason_present": reason_present})
