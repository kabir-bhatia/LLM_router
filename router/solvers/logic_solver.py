"""Deterministic logic-puzzle solver: parse the entities and constraints, brute-force all permutations,
answer only if exactly ONE assignment satisfies every constraint.

Built by looking ONLY at dev template-set-A logic items (D7). Self-gating: every sentence must match a known
constraint grammar in full, the question must match a known form, and the solution must be unique;
otherwise the solver defers (returns no answer).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import permutations

ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6}
ORD_RE = "|".join(ORD)


@dataclass
class LResult:
    answer: object = None
    reason: str = ""
    n_solutions: int = 0

    @property
    def answered(self) -> bool:
        return self.answer is not None


def _defer(reason, n=0):
    return LResult(None, reason, n)


def _split_names(s: str) -> list:
    return [x.strip() for x in re.split(r",|\band\b", s) if x.strip()]


def solve_logic(prompt: str) -> LResult:
    lines = [ln.strip() for ln in prompt.strip().splitlines() if ln.strip()]
    text = " ".join(lines)
    hm = re.search(r"-\s*([A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+)*\s*,?\s*and\s+[A-Z][a-z]+)\s*-", text)
    if not hm:
        return _defer("no entity header")
    names = _split_names(hm.group(1))
    n = len(names)
    if len(set(names)) != n or not 2 <= n <= 6:
        return _defer("bad entity list")
    after_header = text[hm.end():]
    race = bool(re.match(r"\s*finished a race", after_header))
    items = None
    if race:
        mode = "race"
        # the header sentence ends at the first period
    else:
        im = re.search(r"each (?:own a different \w+|ordered a different \w+):\s*([a-z]+(?:\s*,\s*[a-z]+)+)", after_header)
        if not im:
            return _defer("no item list")
        items = [x.strip() for x in im.group(1).split(",")]
        if len(items) != n or len(set(items)) != n:
            return _defer("items/entities count mismatch")
        mode = "attr"
    # constraint sentences: everything after the header sentence (the header has no period before its end)
    first_end = after_header.find(".")
    if first_end < 0:
        return _defer("no sentences")
    body = after_header[first_end + 1:]
    # rebuild sentences from the body text: strip list markers, then split on sentence-ending periods / question marks
    body = re.sub(r"(?:(?<=\s)|^)(?:\d+\.|-)\s+(?=[A-Z])", " ", body)
    sents = [s.strip() for s in re.split(r"(?<=[.?])\s+", body.strip()) if s.strip()]
    N = "(" + "|".join(map(re.escape, names)) + ")"
    I = "(" + "|".join(map(re.escape, items or ["__none__"])) + ")"
    cons = []      # list of callables over assignment dict name -> value (position int or item str)
    question = None
    for s in sents:
        s0 = s.rstrip(".").strip()
        if s0.endswith("?"):
            if question is not None:
                return _defer("two questions")
            question = s0
            continue
        c = None
        if race:
            if (m := re.fullmatch(N + rf" did not finish ({ORD_RE})", s0)):
                a, k = m.group(1), ORD[m.group(2)]
                c = lambda p, a=a, k=k: p[a] != k
            elif (m := re.fullmatch(N + rf" finished ({ORD_RE})", s0)):
                a, k = m.group(1), ORD[m.group(2)]
                c = lambda p, a=a, k=k: p[a] == k
            elif (m := re.fullmatch(N + r" (?:beat|finished ahead of) " + N, s0)):
                a, b = m.groups()
                c = lambda p, a=a, b=b: p[a] < p[b]
            elif (m := re.fullmatch(N + " finished somewhere between " + N + " and " + N, s0)):
                a, b, d = m.groups()
                c = lambda p, a=a, b=b, d=d: min(p[b], p[d]) < p[a] < max(p[b], p[d])
            elif (m := re.fullmatch(r"Exactly one runner finished between " + N + " and " + N, s0)):
                a, b = m.groups()
                c = lambda p, a=a, b=b: abs(p[a] - p[b]) == 2
            elif (m := re.fullmatch(N + " finished immediately after " + N, s0)):
                a, b = m.groups()
                c = lambda p, a=a, b=b: p[a] == p[b] + 1
            elif (m := re.fullmatch(N + " finished immediately before " + N, s0)):
                a, b = m.groups()
                c = lambda p, a=a, b=b: p[a] == p[b] - 1
            elif (m := re.fullmatch(N + " finished (last|first)", s0)):
                a, k = m.group(1), (n if m.group(2) == "last" else 1)
                c = lambda p, a=a, k=k: p[a] == k
        else:
            if (m := re.fullmatch(N + r" (?:is not the owner of|does not own|did not order|does not order) the " + I, s0)):
                a, it = m.groups()
                c = lambda p, a=a, it=it: p[a] != it
            elif (m := re.fullmatch(N + r" (?:owns|ordered) the " + I, s0)):
                a, it = m.groups()
                c = lambda p, a=a, it=it: p[a] == it
            elif (m := re.fullmatch("The " + I + " belongs to either " + N + " or " + N, s0)):
                it, a, b = m.groups()
                c = lambda p, a=a, b=b, it=it: p[a] == it or p[b] == it
            elif (m := re.fullmatch("Either " + N + " or " + N + " ordered the " + I, s0)):
                a, b, it = m.groups()
                c = lambda p, a=a, b=b, it=it: p[a] == it or p[b] == it
        if c is None:
            return _defer(f"unparsed sentence: {s0[:60]}")
        cons.append(c)
    if question is None or not cons:
        return _defer("no question or no constraints")
    # question forms
    if race and (qm := re.fullmatch(rf"Who finished ({ORD_RE}|last|first)\?", question)):
        qk = ORD.get(qm.group(1), n if qm.group(1) == "last" else 1)
        qtype = ("pos", qk)
    elif not race and (qm := re.fullmatch(r"Who (?:owns|ordered) the " + I + r"\?", question)):
        qtype = ("item", qm.group(1))
    else:
        return _defer(f"unparsed question: {question[:60]}")
    values = list(range(1, n + 1)) if race else items
    sols = []
    for perm in permutations(values):
        p = dict(zip(names, perm))
        if all(c(p) for c in cons):
            sols.append(p)
            if len(sols) > 1:
                break
    if len(sols) != 1:
        return _defer("no unique solution", len(sols))
    sol = sols[0]
    target = qtype[1]
    who = [a for a, v in sol.items() if v == target]
    if len(who) != 1:
        return _defer("question target ambiguous")
    return LResult(who[0], "", 1)

