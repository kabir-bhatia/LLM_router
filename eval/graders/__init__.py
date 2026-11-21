"""Graders for the 8-category eval. Entry point: grade(task, response)."""

from __future__ import annotations

from .code_tests import grade_code
from .common import GradeResult
from .constraint import grade_constraint
from .exact import grade_exact
from .formats import CATEGORIES, FORMAT_INSTRUCTIONS, build_messages, system_prompt
from .label import grade_label
from .ner_f1 import grade_ner
from .numeric import grade_numeric

GRADERS = {
    "numeric": grade_numeric,
    "exact": grade_exact,
    "label": grade_label,
    "ner_f1": grade_ner,
    "code_tests": grade_code,
    "constraint": grade_constraint,
}


def grade(task: dict, response: str) -> GradeResult:
    """Grade one response for one task record (see eval/task_schema.py).

    Graders: numeric, exact, label, ner_f1, code_tests, constraint (summaries; may return
    needs_judge=True) and "judge" (factual; always needs the blind judge in Phase 2).
    """
    name = task["grader"]
    if name == "judge":
        return GradeResult(None, 0.0, "needs blind judge", response, needs_judge=True)
    return GRADERS[name](response, task["gold"])


__all__ = ["grade", "GradeResult", "GRADERS", "CATEGORIES", "FORMAT_INSTRUCTIONS",
           "build_messages", "system_prompt"]
