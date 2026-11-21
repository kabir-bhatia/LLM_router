"""Shared helpers for the graders: result type and answer extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
# Last "ANSWER: ..." line wins (models sometimes restate the format line early).
# The value must be on the SAME line as the marker ([ \t], not \s): "### Final answer:" followed by an
# "ANSWER: X" line used to capture the whole next line "ANSWER: X" (Phase 2 dry run fix).
ANSWER_RE = re.compile(r"(?:^|[\s>*_`#-])answer[ \t]*[:=][ \t]*(.+?)[ \t]*$", re.IGNORECASE | re.MULTILINE)
LEADING_ANSWER_RE = re.compile(r"^[\s*_`]*answer\s*[:=]\s*", re.IGNORECASE)
BOXED_RE = re.compile(r"\boxed\{([^{}]*)\}")


@dataclass
class GradeResult:
    """Outcome of grading one response.

    passed is None only when the answer still needs the blind judge (factual,
    summary facts); everything else is a definite True/False.
    """

    passed: Optional[bool]
    score: float = 0.0
    detail: str = ""
    extracted: Any = None
    needs_judge: bool = False
    meta: dict = field(default_factory=dict)


def strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks (and an unterminated leading one)."""
    text = THINK_RE.sub("", text or "")
    if "<think>" in text.lower() and "</think>" not in text.lower():
        text = text[: text.lower().index("<think>")]
    return text


def extract_answer_line(text: str) -> Optional[str]:
    """Value after the last `ANSWER:` line, with markdown noise removed; None if absent."""
    matches = ANSWER_RE.findall(strip_thinking(text))
    if not matches:
        return None
    val = matches[-1].strip().strip("*_`").strip()
    val = LEADING_ANSWER_RE.sub("", val)  # "**Answer:** ANSWER: Ivan" -> "Ivan"
    val = val.strip("*_`").strip()
    val = re.sub(r"^\$?\boxed\{(.*)\}\$?$", r"\1", val)
    return val.strip().rstrip(".").strip() or None


def extract_boxed(text: str) -> Optional[str]:
    found = BOXED_RE.findall(strip_thinking(text))
    return found[-1].strip() if found else None


def last_nonempty_line(text: str) -> str:
    lines = [ln.strip() for ln in strip_thinking(text).splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def norm_text(s: str) -> str:
    """casefold, collapse whitespace, drop surrounding punctuation."""
    s = re.sub(r"\s+", " ", str(s)).strip().casefold()
    return s.strip(" \t\r\n.,;:!?\"'`*_()[]{}")
