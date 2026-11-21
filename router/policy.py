"""Routing policy: load, validate, and turn a (category, difficulty) cell into a plan.

Format = the output of eval/phase4/policy_lib.py (routing_policy.json):
  {"b1": model, "cells": {"<category>|<easy|hard>": {"model", "kind", "escalate_to", "ladder", ...}},
   "out_of_scope": {"model": ...}, "solvers_enabled": bool, ...}
The router never hard-codes cells or model names: it reads whatever this file says (path in RouterConfig).

Plan for a cell = ordered steps, cheapest first:
  solver  (math / logic only, when the policy has solvers_enabled)   pure Python, then the D13 translator
  local   the cell's local model (validators must pass)              only when the cell's model is local
  api     the cell's API model                                       when the cell's model is an API model
  api     escalate_to (B1): one retry on the next tier up            only if different from the previous API step
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from router.models import is_known, kind_of

CATEGORIES = ("factual", "math", "sentiment", "summarisation", "ner", "code_debug", "logic", "code_gen")
DIFFICULTIES = ("easy", "hard")
SOLVER_CATEGORIES = ("math", "logic")
OOS = "out_of_scope"


class PolicyError(ValueError):
    pass


@dataclass
class Step:
    kind: str                  # "solver" | "local" | "api"
    model: str = ""            # local/api model name; "" for the solver
    role: str = ""             # "primary" | "retry" | "oos"


@dataclass
class Plan:
    cell: str                  # "math|hard" or "out_of_scope"
    steps: list = field(default_factory=list)
    level: str = ""            # how the cell was decided (cell / category fallback), informational


def cell_key(category: str, difficulty: str) -> str:
    return f"{category}|{difficulty}"


def validate(policy: dict, require_full_grid: bool = True) -> dict:
    """Raise PolicyError on anything the router could not execute. Returns the policy."""
    if not isinstance(policy, dict):
        raise PolicyError("policy is not an object")
    for k in ("b1", "cells", "out_of_scope"):
        if k not in policy:
            raise PolicyError(f"missing key {k!r}")
    b1 = policy["b1"]
    if kind_of(b1) != "api" or not is_known(b1):
        raise PolicyError(f"b1 {b1!r} must be a known API model")
    oos = (policy["out_of_scope"] or {}).get("model")
    if not oos or kind_of(oos) != "api" or not is_known(oos):
        raise PolicyError(f"out_of_scope model {oos!r} must be a known API model")
    cells = policy["cells"]
    if not isinstance(cells, dict) or not cells:
        raise PolicyError("no cells")
    for key, c in cells.items():
        cat, _, diff = key.partition("|")
        if cat not in CATEGORIES or diff not in DIFFICULTIES:
            raise PolicyError(f"bad cell key {key!r}")
        m, esc = c.get("model"), c.get("escalate_to", b1)
        if not m or not is_known(m):
            raise PolicyError(f"{key}: unknown model {m!r}")
        if c.get("kind", kind_of(m)) != kind_of(m):
            raise PolicyError(f"{key}: kind {c.get('kind')!r} does not match model {m!r}")
        if kind_of(esc) != "api" or not is_known(esc):
            raise PolicyError(f"{key}: escalate_to {esc!r} must be a known API model")
    if require_full_grid:
        missing = [cell_key(c, d) for c in CATEGORIES for d in DIFFICULTIES if cell_key(c, d) not in cells]
        if missing:
            raise PolicyError(f"missing cells: {missing}")
    return policy


class Policy:
    def __init__(self, data: dict, source: str = "<memory>", require_full_grid: bool = True):
        self.data = validate(data, require_full_grid)
        self.source = source

    @classmethod
    def load(cls, path) -> "Policy":
        p = Path(path)
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise PolicyError(f"cannot read policy {p}: {e}")
        return cls(data, str(p))

    @property
    def b1(self) -> str:
        return self.data["b1"]

    @property
    def solvers_enabled(self) -> bool:
        return bool(self.data.get("solvers_enabled", True))

    def cell(self, category: str, difficulty: str):
        return self.data["cells"].get(cell_key(category, difficulty))

    def models(self) -> set:
        """Every model the policy can call (for pre-flight checks and warm-up)."""
        out = {self.b1, self.data["out_of_scope"]["model"]}
        for c in self.data["cells"].values():
            out |= {c["model"], c.get("escalate_to", self.b1)}
        return out

    def plan(self, category: str, difficulty: str, use_solvers: bool = True) -> Plan:
        """OUT_OF_SCOPE (or an unknown cell) -> straight to the out-of-scope model (B1). Otherwise solver -> cell model -> escalate_to."""
        if category == OOS or category not in CATEGORIES:
            return Plan(OOS, [Step("api", self.data["out_of_scope"]["model"], "oos")], OOS)
        c = self.cell(category, difficulty)
        if c is None:  # no such cell (partial policy): the safe route is B1
            return Plan(cell_key(category, difficulty), [Step("api", self.b1, "primary")], "missing cell -> B1")
        steps = []
        if use_solvers and self.solvers_enabled and category in SOLVER_CATEGORIES:
            steps.append(Step("solver"))
        esc = c.get("escalate_to", self.b1)
        if kind_of(c["model"]) == "local":
            steps.append(Step("local", c["model"], "primary"))
            steps.append(Step("api", esc, "retry"))
        else:
            steps.append(Step("api", c["model"], "primary"))
            if esc != c["model"]:
                steps.append(Step("api", esc, "retry"))
        return Plan(cell_key(category, difficulty), steps, str(c.get("level", "")))


def placeholder_policy(b1: str = "kimi-k3p1-pro", local: str = "gemma3:4b", mid: str = "deepseek-v4p1-flash", api_cells=()) -> dict:
    """A complete, valid policy for tests (never used in production): every cell local except `api_cells` (cell keys -> `mid` model)."""
    cells = {}
    for c in CATEGORIES:
        for d in DIFFICULTIES:
            k = cell_key(c, d)
            m = mid if k in api_cells else local
            cells[k] = {"model": m, "kind": kind_of(m), "escalate_to": b1, "initial_model": m, "reason": "placeholder", "level": "placeholder"}
    return {"b1": b1, "mode": "raw", "cells": cells, "out_of_scope": {"model": b1, "reason": "placeholder"}, "solvers_enabled": True}
