"""D13: LLM-assisted solvers. A small local model TRANSLATES; Python SOLVES and VERIFIES.

  math : the model writes ONE arithmetic expression; the safe AST evaluator computes it.
  logic: the model writes JSON (entities, items, constraints, question); Python brute-forces every assignment and answers only if
         exactly one satisfies all constraints.

Self-gating (anything else -> no answer, the router defers to the next layer):
  math : the reply must contain an expression of plain arithmetic; every numeric literal in it must come from the problem
         (a number in the text, a percentage as p/100, 1 +/- p/100, or the constants 1, 60, 100); every number in the problem must be used;
         the result must be a clean number.
  logic: valid JSON of the known schema; every entity and item must occur in the puzzle text; the number of constraints must equal the number
         of constraint sentences in the puzzle; positions in range; exactly one solution.
The prompts and parsers were developed looking ONLY at dev template-set-A items (D7); sets B / hand are the unseen evaluation.
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from fractions import Fraction
from itertools import permutations

from router.solvers.math_solver import LABEL_RE, NUM_RE, _blank_labels, _n
from router.solvers.safe_arith import UnsafeExpression, fmt, safe_eval

# ------------------------------------------------------------------ prompts (the same text is used by the Kaggle notebook)
MATH_SYSTEM = """You translate a word problem into ONE arithmetic expression. You do not solve it.
Rules:
- Use only numbers that appear in the problem, plus + - * / ( ) and ** for powers.
- Write a percentage as a decimal: 25% is 0.25. "25% off" is (1 - 0.25). "grows 25%" is (1 + 0.25).
- Use every number in the problem exactly as needed. Do not round. Do not write units.
- Reply with exactly one line: EXPR: <expression>

Example 1
Problem: A tank holds 800 litres. 25% leaks out, then 40 litres are added. How many litres are in the tank?
EXPR: 800 * (1 - 0.25) + 40

Example 2
Problem: Split 360 rupees in the ratio 2:7. How much is the smaller share?
EXPR: 360 * 2 / (2 + 7)

Example 3
Problem: Mia buys 3 pens at Rs 12 each and 2 books at Rs 150 each, and pays with a Rs 500 note. How much change?
EXPR: 500 - (3 * 12 + 2 * 150)

Example 4
Problem: A machine makes 90 parts every 15 minutes. How many parts in 3 hours?
EXPR: 90 / 15 * 60 * 3

Example 5
Problem: A town of 5,000 people grows 10% every year. How many people live there after 2 years?
EXPR: 5000 * (1 + 0.1) ** 2"""

LOGIC_SYSTEM = """You translate a logic puzzle into JSON. You do not solve it. Reply with only the JSON object.
Schema:
{"mode": "order" or "match",
 "entities": [the people, exactly as named in the puzzle],
 "items": [the things being matched, exactly as named; only for mode "match"],
 "constraints": [one object per fact, in the order given],
 "question": {...}}
Mode "order": people are ranked 1..N (1 = first). Constraint types:
 {"type":"at","who":X,"pos":k}            X is in position k
 {"type":"not_at","who":X,"pos":k}        X is not in position k
 {"type":"before","who":X,"other":Y}      X is ahead of Y (X beat Y)
 {"type":"between","who":X,"a":Y,"b":Z}   X is somewhere between Y and Z
 {"type":"one_between","a":X,"b":Y}       exactly one person is between X and Y
 {"type":"right_after","who":X,"other":Y} X is immediately after Y
 question: {"type":"who_at","pos":k}
Mode "match": each person has a different item. Constraint types:
 {"type":"has","who":X,"item":i}          X has item i
 {"type":"not_has","who":X,"item":i}      X does not have item i
 {"type":"either","item":i,"a":X,"b":Y}   item i belongs to X or Y
 question: {"type":"who_has","item":i}
Write one constraint per sentence of the puzzle (skip the introduction and the question).

Example (order)
Puzzle: Three runners - Ann, Bo and Cy - finished a race with no ties. Ann beat Bo. Cy did not finish first. Bo did not finish second. Who finished first?
{"mode":"order","entities":["Ann","Bo","Cy"],"constraints":[{"type":"before","who":"Ann","other":"Bo"},{"type":"not_at","who":"Cy","pos":1},{"type":"not_at","who":"Bo","pos":2}],"question":{"type":"who_at","pos":1}}

Example (match)
Puzzle: Three friends - Ann, Bo and Cy - each own a different pet: cat, dog, fish. Ann owns the cat. The fish belongs to either Bo or Cy. Cy does not own the fish. Who owns the dog?
{"mode":"match","entities":["Ann","Bo","Cy"],"items":["cat","dog","fish"],"constraints":[{"type":"has","who":"Ann","item":"cat"},{"type":"either","item":"fish","a":"Bo","b":"Cy"},{"type":"not_has","who":"Cy","item":"fish"}],"question":{"type":"who_has","item":"dog"}}"""


@dataclass
class TResult:
    answer: object = None
    reason: str = ""
    expr: str = ""

    @property
    def answered(self) -> bool:
        return self.answer is not None


def _defer(reason, expr=""):
    return TResult(None, reason, expr)


# ------------------------------------------------------------------ math
_EXPR_LINE = re.compile(r"EXPR\s*[:=]\s*(.+)", re.I)
_ONLY_ARITH = re.compile(r"^[\d\s.+\-*/()]+$")


def _clean_expr(raw: str):
    """Pull the expression out of the model's reply and normalise typography; None if no plain-arithmetic expression."""
    text = re.sub(r"<think>.*?</think>", "", raw or "", flags=re.S | re.I)
    m = _EXPR_LINE.findall(text)
    cand = m[-1] if m else None
    if cand is None:
        lines = [ln.strip().strip("`") for ln in text.splitlines() if ln.strip()]
        cand = lines[-1] if lines else None
        if cand is None or not re.fullmatch(r"[\d\s.,+\-*/()^%x×÷₹$=]+", cand):
            return None
    cand = cand.replace("`", "").strip()
    cand = cand.split("=")[0] if "=" in cand and re.search(r"=\s*[\d.,]+\s*$", cand) else cand  # drop a trailing "= result"
    cand = cand.replace("×", "*").replace("÷", "/").replace("^", "**").replace("−", "-")
    cand = re.sub(r"[₹$]|Rs\.?", "", cand)
    cand = re.sub(r"(?<=\d),(?=\d{3}\b)", "", cand)                       # thousands separators
    cand = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", cand)               # 25% -> (25/100)
    cand = re.sub(r"(?<=\d)\s*[xX]\s*(?=[\d(])", "*", cand)               # 3 x 4
    cand = cand.strip()
    return cand if cand and _ONLY_ARITH.match(cand) else None


def _literals(expr: str):
    tree = ast.parse(expr, mode="eval")
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            out.append(Fraction(str(n.value)))
    return out


def _value_or_none(node):
    try:
        return safe_eval(ast.unparse(node))
    except (UnsafeExpression, ValueError, SyntaxError, ZeroDivisionError):
        return None


def _structural_constants_ok(expr: str, probnums, pcts, problem: str):
    """The non-problem constants 1, 60 and 100 are only allowed in their natural roles:
    1 as the left side of (1 +/- percentage); 100 as a divisor when the problem has a percentage; 60 as a minutes<->hours factor
    when the problem mentions both minutes and hours. Returns a reason string or None."""
    tree = ast.parse(expr, mode="eval")
    pct_set = set(pcts)
    parents = {}
    for node in ast.walk(tree):
        for ch in ast.iter_child_nodes(node):
            parents[ch] = node
    probset = set(probnums)
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Constant) and isinstance(n.value, (int, float))):
            continue
        v = Fraction(str(n.value))
        if v in probset or v in pct_set or v in {1 + p for p in pcts} or v in {1 - p for p in pcts}:
            continue
        par = parents.get(n)
        if v == 1:
            ok = (isinstance(par, ast.BinOp) and isinstance(par.op, (ast.Add, ast.Sub)) and par.left is n
                  and _value_or_none(par.right) in pct_set)
            if not ok:
                return "constant 1 outside (1 +/- percentage)"
        elif v == 100:
            if not (pct_set and isinstance(par, ast.BinOp) and isinstance(par.op, ast.Div) and par.right is n):
                return "constant 100 outside a percentage division"
        elif v == 60:
            if not (re.search(r"min", problem, re.I) and re.search(r"hour", problem, re.I)):
                return "constant 60 without minutes and hours in the problem"
        else:
            return f"constant {v} not from the problem"
    return None


def parse_math_translation(raw: str, problem: str) -> TResult:
    expr = _clean_expr(raw)
    if expr is None:
        return _defer("no plain arithmetic expression in the reply")
    try:
        lits = _literals(expr)
        value = safe_eval(expr)
    except (UnsafeExpression, SyntaxError, ZeroDivisionError, ValueError, RecursionError) as e:
        return _defer(f"expression rejected: {type(e).__name__}", expr)
    # literal provenance gate
    probnums = [Fraction(_n(x)) for x in NUM_RE.findall(_blank_labels(problem))]
    pcts = [Fraction(_n(x)) / 100 for x in re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*%", problem)]
    allowed = set(probnums) | set(pcts) | {1 + p for p in pcts} | {1 - p for p in pcts} | {Fraction(1), Fraction(60), Fraction(100)}
    stray = [str(x) for x in lits if x not in allowed]
    if stray:
        return _defer(f"literal(s) not from the problem: {stray[:3]}", expr)
    bad = _structural_constants_ok(expr, probnums, pcts, problem)
    if bad:
        return _defer(f"literal(s) not from the problem: {bad}", expr)
    used = set(lits)
    for x in probnums:
        pct_forms = {x / 100, 1 + x / 100, 1 - x / 100} if x in {p * 100 for p in pcts} else set()
        if x not in used and not (pct_forms & used):
            return _defer(f"problem number {x} not used", expr)
    out = fmt(value)
    if out is None or value < 0:
        return _defer("result is not a clean non-negative number", expr)
    return TResult(out, "", expr)


# ------------------------------------------------------------------ logic
ORDER_TYPES = {"at": ("who", "pos"), "not_at": ("who", "pos"), "before": ("who", "other"), "between": ("who", "a", "b"),
               "one_between": ("a", "b"), "right_after": ("who", "other")}
MATCH_TYPES = {"has": ("who", "item"), "not_has": ("who", "item"), "either": ("item", "a", "b")}


def _extract_json(raw: str):
    text = re.sub(r"<think>.*?</think>", "", raw or "", flags=re.S | re.I)
    for blk in re.findall(r"```(?:json)?\s*(.*?)```", text, re.S | re.I) + [text]:
        blk = blk.strip()
        try:
            return json.loads(blk)
        except ValueError:
            pass
        i, j = blk.find("{"), blk.rfind("}")
        if 0 <= i < j:
            try:
                return json.loads(blk[i:j + 1])
            except ValueError:
                pass
    return None


def count_constraint_sentences(puzzle: str) -> int:
    """Sentences after the introduction (the first sentence) that are not the question."""
    body = re.sub(r"(?:(?<=\s)|^)(?:\d+\.|-)\s+(?=[A-Z])", " ", " ".join(puzzle.strip().split("\n")))
    sents = [s.strip() for s in re.split(r"(?<=[.?])\s+", body) if s.strip()]
    return len([s for s in sents[1:] if not s.endswith("?")])


def _in_text(word: str, text: str) -> bool:
    return bool(re.search(r"(?<![A-Za-z])" + re.escape(str(word)) + r"(?![A-Za-z])", text, re.I))


def solve_logic_spec(spec, puzzle: str) -> TResult:
    if not isinstance(spec, dict):
        return _defer("not a JSON object")
    mode = spec.get("mode")
    ents = spec.get("entities")
    cons = spec.get("constraints")
    q = spec.get("question")
    if mode not in ("order", "match") or not isinstance(ents, list) or not isinstance(cons, list) or not isinstance(q, dict):
        return _defer("missing or invalid fields")
    if not all(isinstance(e, str) for e in ents) or len(set(ents)) != len(ents) or not 2 <= len(ents) <= 6:
        return _defer("bad entity list")
    n = len(ents)
    if not all(_in_text(e, puzzle) for e in ents):
        return _defer("an entity does not occur in the puzzle")
    if mode == "match":
        items = spec.get("items")
        if not isinstance(items, list) or len(items) != n or len(set(map(str, items))) != n or not all(_in_text(i, puzzle) for i in items):
            return _defer("bad item list")
        items = [str(i) for i in items]
        values = items
        schema = MATCH_TYPES
    else:
        values = list(range(1, n + 1))
        schema = ORDER_TYPES
    if not cons:
        return _defer("no constraints")
    if len(cons) != count_constraint_sentences(puzzle):
        return _defer(f"{len(cons)} constraints but {count_constraint_sentences(puzzle)} constraint sentences")
    checks = []
    for c in cons:
        if not isinstance(c, dict) or c.get("type") not in schema:
            return _defer(f"unknown constraint {str(c)[:40]}")
        t = c["type"]
        if any(k not in c for k in schema[t]):
            return _defer(f"constraint {t} missing fields")
        for k in ("who", "other", "a", "b"):
            if k in c and c[k] not in ents:
                return _defer(f"constraint names unknown entity {c[k]!r}")
        if "pos" in c and (not isinstance(c["pos"], int) or isinstance(c["pos"], bool) or not 1 <= c["pos"] <= n):
            return _defer("position out of range")
        if "item" in c and str(c["item"]) not in values:
            return _defer("constraint names unknown item")
        checks.append(c)

    def ok(p, c):
        t = c["type"]
        if t == "at": return p[c["who"]] == c["pos"]
        if t == "not_at": return p[c["who"]] != c["pos"]
        if t == "before": return p[c["who"]] < p[c["other"]]
        if t == "between": return min(p[c["a"]], p[c["b"]]) < p[c["who"]] < max(p[c["a"]], p[c["b"]])
        if t == "one_between": return abs(p[c["a"]] - p[c["b"]]) == 2
        if t == "right_after": return p[c["who"]] == p[c["other"]] + 1
        if t == "has": return p[c["who"]] == str(c["item"])
        if t == "not_has": return p[c["who"]] != str(c["item"])
        if t == "either": return p[c["a"]] == str(c["item"]) or p[c["b"]] == str(c["item"])
        return False

    if mode == "order" and q.get("type") == "who_at" and isinstance(q.get("pos"), int) and 1 <= q["pos"] <= n:
        target = q["pos"]
    elif mode == "match" and q.get("type") == "who_has" and str(q.get("item")) in values:
        target = str(q["item"])
    else:
        return _defer("bad question")
    sols = []
    for perm in permutations(values):
        p = dict(zip(ents, perm))
        if all(ok(p, c) for c in checks):
            sols.append(p)
            if len(sols) > 1:
                return _defer("more than one solution")
    if len(sols) != 1:
        return _defer("no solution")
    who = [e for e, v in sols[0].items() if v == target]
    return TResult(who[0]) if len(who) == 1 else _defer("target ambiguous")


def parse_logic_translation(raw: str, puzzle: str) -> TResult:
    spec = _extract_json(raw)
    if spec is None:
        return _defer("no JSON in the reply")
    return solve_logic_spec(spec, puzzle)
