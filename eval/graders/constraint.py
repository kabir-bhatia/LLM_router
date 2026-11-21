"""Constraint grader for summaries: sentence count / word limit / bullet count.

Gold: {"constraints": {"sentences": 1} | {"max_words": 40} | {"bullets": 3} (combinable),
       "key_facts": ["...", ...], "fact_hints": [["three", "3"], ...]}.
Key facts are judged by the blind judge; `fact_hints` (alternative keywords per fact) only give a
cheap lexical signal for diagnostics and never decide pass/fail.
A violated constraint is a definite fail; a met one still needs the judge (passed=None).
"""

from __future__ import annotations

import re

from .common import GradeResult, strip_thinking

BULLET_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+\S", re.MULTILINE)
BULLET_PREFIX = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+", re.MULTILINE)
ABBREV = ("dr", "mr", "mrs", "ms", "prof", "st", "vs", "etc", "no", "inc", "ltd", "jr", "sr")


LEAD_IN_RE = re.compile(r"^[\s*_`#>-]*(here|sure|okay|ok|certainly|of course)\b[^\n]*:[\s*_`]*$", re.IGNORECASE)


def summary_text(response: str) -> str:
    body = strip_thinking(response).strip()
    m = re.search(r"(?is)^[\s>*_`#-]*answer\s*:\s*(.*)$", body, re.MULTILINE)
    body = m.group(1).strip() if m else body
    # A one-line conversational lead-in ("Here's a summary in 3 bullet points:") is not part of the
    # summary; gemma3:1b adds one to ~1/4 of its answers despite "return only the summary" (Phase 2).
    # Only a first line that starts with Here/Sure/Okay/Certainly AND ends with ":" is dropped.
    first, sep, rest = body.partition("\n")
    if sep and LEAD_IN_RE.match(first.strip()) and rest.strip():
        body = rest.strip()
    return body


def count_sentences(text: str) -> int:
    t = re.sub(r"\s+", " ", text.strip())
    if not t:
        return 0
    n, buf = 0, ""
    for tok in re.split(r"(?<=[.!?])\s+", t):
        buf = f"{buf} {tok}".strip()
        last = buf.split()[-1].rstrip(".").lower() if buf.split() else ""
        if re.search(r"[.!?][\"')\]]*$", buf) and last not in ABBREV:
            n += 1
            buf = ""
    return n + (1 if buf else 0)


def count_words(text: str) -> int:
    return len(BULLET_PREFIX.sub("", text).split())


def count_bullets(text: str) -> int:
    return len(BULLET_RE.findall(text))


def check_constraints(text: str, cons: dict):
    problems = []
    if "sentences" in cons:
        n = count_sentences(text)
        if n != cons["sentences"]:
            problems.append(f"{n} sentences, want {cons['sentences']}")
    if "max_words" in cons:
        n = count_words(text)
        if n > cons["max_words"]:
            problems.append(f"{n} words, max {cons['max_words']}")
    if "bullets" in cons:
        n = count_bullets(text)
        if n != cons["bullets"]:
            problems.append(f"{n} bullets, want {cons['bullets']}")
        stray = [ln for ln in text.splitlines() if ln.strip() and not BULLET_RE.match(ln)]
        if stray:
            problems.append("text outside bullets")
    return not problems, problems


def grade_constraint(response: str, gold: dict) -> GradeResult:
    text = summary_text(response)
    ok, problems = check_constraints(text, gold["constraints"])
    low = text.lower()
    present = [any(h.lower() in low for h in alts) for alts in (gold.get("fact_hints") or [])]
    return GradeResult(False if not ok else None, 0.0 if not ok else 0.5,
                       "; ".join(problems) or "constraint met", text, needs_judge=ok,
                       meta={"constraint_ok": ok, "fact_hints_present": present})
