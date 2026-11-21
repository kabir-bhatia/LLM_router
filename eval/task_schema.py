"""Task record schema and validation for eval/tasks_8cat.json."""

from __future__ import annotations

import json
from pathlib import Path

CATEGORIES = ("factual", "math", "sentiment", "summarisation", "ner", "code_debug", "logic", "code_gen")
DIFFICULTIES = ("easy", "hard")
GRADER_FOR_CATEGORY = {
    "math": "numeric", "logic": "exact", "sentiment": "label", "ner": "ner_f1",
    "code_debug": "code_tests", "code_gen": "code_tests", "summarisation": "constraint",
    "factual": "judge",
}
REQUIRED = ("id", "category", "prompt", "gold", "grader", "source", "difficulty", "phrasing", "split", "note")
# template set marker for D7 (math/logic only): "A" = solver-dev, "B" = test only, "hand" = hand-written
TEMPLATE_SETS = ("A", "B", "hand")


def validate_task(t: dict) -> list:
    errs = []
    for k in REQUIRED:
        if k not in t:
            errs.append(f"missing {k}")
    if errs:
        return errs
    if t["category"] not in CATEGORIES:
        errs.append(f"bad category {t['category']}")
    elif t["grader"] != GRADER_FOR_CATEGORY[t["category"]]:
        errs.append(f"grader {t['grader']} != {GRADER_FOR_CATEGORY[t['category']]}")
    if t["difficulty"] not in DIFFICULTIES:
        errs.append(f"bad difficulty {t['difficulty']}")
    if t["split"] not in ("dev", "test", "unsplit"):
        errs.append(f"bad split {t['split']}")
    if not str(t["prompt"]).strip():
        errs.append("empty prompt")
    if not str(t["note"]).strip():
        errs.append("empty note")
    g = t["gold"]
    need = {"numeric": ("answer",), "exact": ("answer",), "label": ("label",), "ner_f1": ("entities",),
            "code_tests": ("tests", "entry_point"), "constraint": ("constraints",), "judge": ("reference",)}
    for k in need.get(t["grader"], ()):
        if k not in g:
            errs.append(f"gold missing {k}")
    if t["category"] in ("math", "logic") and t.get("template_set") not in TEMPLATE_SETS:
        errs.append("math/logic need template_set A|B|hand")
    return errs


def load_tasks(path) -> list:
    return json.loads(Path(path).read_text(encoding="utf-8"))
