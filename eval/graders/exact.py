"""Exact-match grader (logic puzzles: a name / item / position)."""

from __future__ import annotations

import re

from .common import GradeResult, extract_answer_line, last_nonempty_line, norm_text, strip_thinking


def _accepted(gold: dict) -> list[str]:
    ans = gold["answer"]
    alts = gold.get("alternatives", [])
    return [norm_text(a) for a in ([ans] + list(alts))]


def grade_exact(response: str, gold: dict) -> GradeResult:
    accepted = _accepted(gold)
    cand = extract_answer_line(response)
    if cand is not None:
        ok = norm_text(cand) in accepted
        return GradeResult(ok, float(ok), f"answer line {cand!r}", cand, meta={"how": "answer_line"})

    # Lenient fallback: the final line must name the gold answer and no other choice.
    # Without `choices` in gold we only accept a whole-word match of the gold on the last line.
    line = norm_text(last_nonempty_line(response))
    choices = [norm_text(c) for c in gold.get("choices", [])]
    has = lambda w: re.search(rf"(?<!\w){re.escape(w)}(?!\w)", line) is not None  # noqa: E731
    hits = [c for c in (choices or accepted) if has(c)]
    ok = bool(hits) and all(h in accepted for h in hits)
    return GradeResult(ok, float(ok), f"fallback last line {line!r}", line, meta={"how": "fallback"})
