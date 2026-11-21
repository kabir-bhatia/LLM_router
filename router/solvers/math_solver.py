"""Deterministic word-problem solver for percentage / ratio / purchase / rate problems.

Built by looking ONLY at dev template-set-A math items (D7). Self-gating: every recipe must (1) match its
sentence patterns, (2) account for EVERY number in the prompt, (3) resolve every direction/target word, and
(4) produce a clean number. Anything else returns no answer ("defer"); the solver never guesses.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction

from router.solvers.safe_arith import UnsafeExpression, fmt, safe_eval

NUM = r"\d[\d,]*(?:\.\d+)?"
NUM_RE = re.compile(r"(?<![\w.])(" + NUM + r")")
LABEL_RE = re.compile(r"\b(?:week|year|day|month|quarter)[\s-]+\d+\b", re.I)
CUR = "₹$"


@dataclass
class Result:
    answer: object = None
    recipe: str = ""
    reason: str = ""

    @property
    def answered(self) -> bool:
        return self.answer is not None


def _n(s: str) -> str:
    return s.replace(",", "")


def _blank_labels(text: str) -> str:
    return LABEL_RE.sub(lambda m: " " * len(m.group(0)), text)


def _numbers(text: str) -> list:
    return NUM_RE.findall(_blank_labels(text))


def _sentences(text: str) -> list:
    parts = re.split(r"(?<=[.?!])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _is_question(s: str) -> bool:
    return "?" in s or bool(re.match(r"(?i)(work out|find|calculate|compute|determine|report|what|how)\b", s))


def _defer(reason: str) -> Result:
    return Result(None, "", reason)


# ---------------------------------------------------------------- sequential percent / absolute changes
MINUS = re.compile(r"\b(sold|sell|sells|selling|lost|lose|loses|shrank|shrink|shrinks|dropped|drop|fell|falls|decreas\w*|went out|"
                   r"used|spent|removed|sales|discard\w*)\b", re.I)
PLUS = re.compile(r"\b(grew|grow|grows|growing|gain\w*|increas\w*|rose|rises|added|restock\w*|up by)\b", re.I)
INHERIT = re.compile(r"\b(more|another|further|additional)\b", re.I)
GOOD_Q = re.compile(r"remain|are left|is left|still on|closing|count|live there|does it have|will .* be\b|"
                    r"are there|at the end|left\b", re.I)
BAD_Q = re.compile(r"\b(sold|lost|used|spent|removed|percent|percentage|difference|ratio|change|discount|total sales)\b",
                   re.I)


def _sequential(sents: list) -> Result:
    stmts = [s for s in sents if not _is_question(s)]
    qs = [s for s in sents if _is_question(s)]
    if len(qs) != 1:
        return _defer("seq: need exactly one question")
    q = qs[0]
    if not GOOD_Q.search(q) or BAD_Q.search(q):
        return _defer("seq: question is not a remaining/final-amount question")
    growth_ctx = bool(re.search(r"\b(year|grow|grew|shrank|a year|every year|each year)\b", " ".join(sents), re.I))
    years = None
    my = re.search(r"(?:after\s+(\d+)\s+years?|(\d+)\s+years?\s+(?:from now|later))", q, re.I)
    if my:
        years = int(my.group(1) or my.group(2))
    qnums = _numbers(q)
    if qnums and not (years is not None and len(qnums) == 1):
        return _defer("seq: unexpected number in question")
    clean = _blank_labels(" ".join(stmts))
    toks = list(NUM_RE.finditer(clean))
    if len(toks) < 2 and not (years is not None and len(toks) >= 2):
        return _defer("seq: fewer than 2 numbers")
    start_m = toks[0]
    if clean[start_m.end():].lstrip().startswith("%"):
        return _defer("seq: starts with a percent")
    start = Fraction(_n(start_m.group(1)))
    cur = start
    prev_dir = None
    steps = 0
    last_pct = None
    for i in range(1, len(toks)):
        m = toks[i]
        prev_end = toks[i - 1].end()
        nxt = toks[i + 1].start() if i + 1 < len(toks) else len(clean)
        before = clean[prev_end:m.start()]
        after = clean[m.end():nxt]
        is_pct = after.lstrip().startswith("%")
        val = Fraction(_n(m.group(1)))
        sign_ch = clean[m.start() - 1] if m.start() > 0 else ""
        win_after = re.split(r"[,.;]", after, maxsplit=1)[0]
        ctx = before + " " + win_after
        direction = None
        if sign_ch == "+":
            direction = 1
        elif sign_ch in "-−":
            direction = -1
        else:
            has_m, has_p = bool(MINUS.search(ctx)), bool(PLUS.search(ctx))
            if has_m and has_p:
                return _defer("seq: both directions in one clause")
            if has_m:
                direction = -1
            elif has_p:
                direction = 1
            elif INHERIT.search(ctx) and prev_dir is not None:
                direction = prev_dir
        if direction is None:
            return _defer("seq: direction unresolved")
        prev_dir = direction
        if is_pct:
            of_that = re.search(r"\bof (that|the original|the initial|the total|the starting)\b", win_after, re.I)
            if steps > 0 and of_that:
                return _defer("seq: percent of original after earlier steps (ambiguous base)")
            if steps > 0 and not growth_ctx and not re.search(r"whatever|the rest|remaining|left", win_after, re.I):
                return _defer("seq: later percent with unclear base")
            cur = cur * (1 + direction * val / 100)
            last_pct = direction * val / 100
        else:
            cur = cur + direction * val
            last_pct = None
        steps += 1
    if steps == 0:
        return _defer("seq: no steps")
    if years is not None:
        if last_pct is None or steps != 1:
            return _defer("seq: years multiplier needs exactly one percent step")
        cur = start * (1 + last_pct) ** years
    out = fmt(cur)
    if out is None or cur < 0:
        return _defer("seq: result not a clean non-negative number")
    return Result(out, "sequential")


# ---------------------------------------------------------------- ratio split
def _ratio(text: str) -> Result:
    m = re.search(r"ratio\s+(\d+(?::\d+)+)", text, re.I)
    if m:
        parts = [int(x) for x in m.group(1).split(":")]
    else:
        m = re.search(r"ratio\s+(\d+)\s+to\s+(\d+)", text, re.I)
        if not m:
            return _defer("ratio: no ratio")
        parts = [int(m.group(1)), int(m.group(2))]
    others = _numbers(text[:m.start()] + " " + text[m.end():])
    if len(others) != 1:
        return _defer("ratio: expected exactly one total")
    total = Fraction(_n(others[0]))
    low = text.lower()
    if "how much more" in low and re.search(r"larg|big", low) and re.search(r"smal|least", low):
        expr = f"({total}) * ({max(parts)} - {min(parts)}) / {sum(parts)}"
        kind = "diff"
    else:
        big = bool(re.search(r"\b(bigger|larger|largest|biggest|greater|greatest)\b", low))
        small = bool(re.search(r"\b(smaller|smallest|least)\b", low))
        if big == small:
            return _defer("ratio: target share unclear")
        expr = f"({total}) * {max(parts) if big else min(parts)} / {sum(parts)}"
        kind = "max" if big else "min"
    out = fmt(safe_eval(expr))
    return Result(out, f"ratio-{kind}") if out else _defer("ratio: unclean result")


# ---------------------------------------------------------------- purchase / change
def _purchase(text: str) -> Result:
    if not re.search(r"\b(change|get back|comes back|returned)\b", text, re.I):
        return _defer("purchase: no change question")
    tender = re.search(r"(?:tender(?:s|ed)?|handed over|pays? with an?|paid with an?|gives?|gave)\s+(?:an?\s+)?["
                       + CUR + r"]\s?(" + NUM + ")", text, re.I)
    if not tender:
        return _defer("purchase: no tendered amount")
    items = re.findall(r"(\d+)\s+(?:units? of item \w+|[a-z]+)\s+(?:at|that cost|costing|@)\s+[" + CUR + r"]\s?(" + NUM + ")",
                       text, re.I)
    if not items:
        return _defer("purchase: no items")
    disc = re.search(r"(\d+)\s*%\s*(?:discount|off)|discount of (\d+)\s*%", text, re.I)
    used = [_n(tender.group(1))] + [_n(x) for it in items for x in it]
    pct = None
    if disc:
        pct = disc.group(1) or disc.group(2)
        if not re.search(r"\b(total|whole bill|entire|bill|order|purchase)\b", text, re.I):
            return _defer("purchase: discount scope unclear")
        used.append(pct)
    if sorted(_n(x) for x in _numbers(text)) != sorted(used):
        return _defer("purchase: unaccounted numbers")
    sub = " + ".join(f"{q} * {_n(p)}" for q, p in items)
    if pct:
        expr = f"{_n(tender.group(1))} - ({sub}) * (1 - {pct}/100)"
    else:
        expr = f"{_n(tender.group(1))} - ({sub})"
    v = safe_eval(expr)
    out = fmt(v)
    if out is None or v < 0:
        return _defer("purchase: unclean/negative")
    return Result(out, "purchase")


# ---------------------------------------------------------------- rates
def _rate(text: str) -> Result:
    pairs = re.findall(r"(\d+)\s+hours?\s+at\s+(\d+)\s+[a-z ]*?/\s*hour", text, re.I)
    if pairs:
        if sorted(_numbers(text)) != sorted(x for p in pairs for x in p):
            return _defer("rate: unaccounted numbers")
        if not re.search(r"\btotal\b", text, re.I):
            return _defer("rate: not a total question")
        out = fmt(safe_eval(" + ".join(f"{h} * {r}" for h, r in pairs)))
        return Result(out, "rate-sum") if out else _defer("rate: unclean")
    m = re.search(r"(\d+)\s+[a-z]+\s+every\s+(\d+)\s*min(?:ute)?s?\b.*?\bfor\s+(\d+)\s+hours?", text, re.I | re.S)
    if m:
        if sorted(_numbers(text)) != sorted(m.groups()):
            return _defer("rate: unaccounted numbers")
        if not re.search(r"how many", text, re.I):
            return _defer("rate: question")
        out = fmt(safe_eval(f"{m.group(1)} / {m.group(2)} * 60 * {m.group(3)}"))
        return Result(out, "rate-interval") if out else _defer("rate: unclean")
    return _defer("rate: no pattern")


def solve_math(prompt: str) -> Result:
    text = " ".join(prompt.split())
    sents = _sentences(prompt)
    reasons = []
    for fn, arg in ((_ratio, text), (_purchase, text), (_rate, text), (_sequential, sents)):
        try:
            r = fn(arg)
        except (UnsafeExpression, ZeroDivisionError, ValueError, IndexError):
            continue
        if r.answered:
            return r
        reasons.append(r.reason)
    return _defer("no recipe matched with certainty")

