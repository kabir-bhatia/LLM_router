"""Numeric grader: pull a number out of the answer and compare with a tolerance.

`tolerance` is ABSOLUTE. Integer golds should use 0 (an off-by-one must fail);
money/percent golds rounded to 2 decimals use 0.01.
"""

from __future__ import annotations

import re

from .common import GradeResult, extract_answer_line, extract_boxed, last_nonempty_line, strip_thinking

NUM_RE = re.compile(r"[-+]?\$?\s?\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?|[-+]?\.\d+")


def parse_number(s: str):
    """First number in s as float (handles $1,250.50, 12%, '3 /4' not supported), else None."""
    nums = numbers_in(s)
    return nums[0] if nums else None


def numbers_in(s: str) -> list[float]:
    out = []
    for m in NUM_RE.findall(s or ""):
        t = m.replace(",", "").replace("$", "").replace(" ", "")
        try:
            out.append(float(t))
        except ValueError:
            continue
    return out


def grade_numeric(response: str, gold: dict) -> GradeResult:
    want = float(gold["answer"])
    tol = float(gold.get("tolerance", 0.0))
    how = "answer_line"
    cand = extract_answer_line(response)
    if cand is None:
        cand = extract_boxed(response)
        how = "boxed"
    if cand is None:
        # lenient fallback: last number on the last non-empty line, else last number anywhere
        line = last_nonempty_line(response)
        nums = numbers_in(line) or numbers_in(strip_thinking(response))
        cand = str(nums[-1]) if nums else None
        how = "fallback_last_number"
    if cand is None:
        return GradeResult(False, 0.0, "no number found", None)
    got = parse_number(cand)
    if got is None:
        return GradeResult(False, 0.0, f"unparseable answer {cand!r}", cand, meta={"how": how})
    ok = abs(got - want) <= tol + 1e-9
    return GradeResult(ok, 1.0 if ok else 0.0, f"got {got} want {want} (tol {tol}) via {how}", got,
                       meta={"how": how})
