"""Logic puzzle generator (Phase 1, step 3).

Puzzles are permutation puzzles: n people, n distinct values (items or finishing positions).
Clues are drawn from the TRUE clues of a hidden random solution and added until a brute-force
count over all n! permutations says there is exactly one solution; redundant clues are then pruned.

Two separate template sets (D7): set A (solver-dev) and set B (test only) use different themes,
different clue wordings and different question wordings.

Independent verification (`verify_text`): the prompt text is parsed BACK into clues with regexes
derived from the phrase templates, and solved by a different algorithm (backtracking with early
pruning, not full permutation enumeration). It must find exactly one solution and the same answer
as the gold. That checks the English text, not just the internal clue tuples.
"""

from __future__ import annotations

import itertools
import random
import re

ORD = ["first", "second", "third", "fourth", "fifth"]
PEOPLE = ["Ana", "Ben", "Cy", "Dia", "Eli", "Fay", "Gus", "Hana", "Ivan", "Jia", "Kofi", "Lena",
          "Maya", "Noor", "Omar", "Pia", "Raj", "Sara", "Tomas", "Uma"]

# ------------------------------------------------------------------ clue semantics
def holds(clue, a):
    """a[p] = value index (for ordering puzzles the value is the 0-based position)."""
    k = clue[0]
    if k == "is":
        return a[clue[1]] == clue[2]
    if k == "not":
        return a[clue[1]] != clue[2]
    if k == "either":
        return a[clue[1]] == clue[3] or a[clue[2]] == clue[3]
    if k == "before":
        return a[clue[1]] < a[clue[2]]
    if k == "right_after":  # p is directly after q
        return a[clue[1]] == a[clue[2]] + 1
    if k == "gap1":  # exactly one person between p and q
        return abs(a[clue[1]] - a[clue[2]]) == 2
    if k == "between":  # r strictly between p and q
        lo, hi = sorted((a[clue[1]], a[clue[2]]))
        return lo < a[clue[3]] < hi
    if k == "pos":
        return a[clue[1]] == clue[2]
    if k == "notpos":
        return a[clue[1]] != clue[2]
    raise ValueError(k)


def count_solutions(clues, n):
    sols = [a for a in itertools.permutations(range(n)) if all(holds(c, a) for c in clues)]
    return sols


def all_true_clues(a, n, kinds):
    out = []
    P = range(n)
    for p in P:
        for v in range(n):
            if "is" in kinds and a[p] == v:
                out.append(("is", p, v))
            if "not" in kinds and a[p] != v:
                out.append(("not", p, v))
            if "pos" in kinds and a[p] == v:
                out.append(("pos", p, v))
            if "notpos" in kinds and a[p] != v:
                out.append(("notpos", p, v))
    for p, q in itertools.permutations(P, 2):
        if "before" in kinds and a[p] < a[q]:
            out.append(("before", p, q))
        if "right_after" in kinds and a[p] == a[q] + 1:
            out.append(("right_after", p, q))
        if "gap1" in kinds and p < q and abs(a[p] - a[q]) == 2:
            out.append(("gap1", p, q))
        if "either" in kinds and p < q:
            for v in range(n):
                if a[p] == v or a[q] == v:
                    out.append(("either", p, q, v))
    if "between" in kinds:
        for p, q in itertools.combinations(P, 2):
            for r in P:
                if r not in (p, q) and min(a[p], a[q]) < a[r] < max(a[p], a[q]):
                    out.append(("between", p, q, r))
    return out


# ------------------------------------------------------------------ wording
# Each theme: values, intro, per-kind phrase lists, question template ({v} value text, {k} ordinal).
THEMES = {
    "A": {
        "assign": [
            dict(name="pets", values=["cat", "dog", "fish", "rabbit", "parrot"],
                 intro="{n} friends - {names} - each own a different pet: {vals}.",
                 is_=["{p} owns the {v}."], not_=["{p} does not own the {v}.", "{p} is not the owner of the {v}."],
                 either=["The {v} belongs to either {p} or {q}."],
                 ask="Who owns the {v}?"),
            dict(name="drinks", values=["tea", "coffee", "juice", "milk", "lassi"],
                 intro="At a cafe, {nl} people - {names} - each ordered a different drink: {vals}.",
                 is_=["{p} ordered the {v}."], not_=["{p} did not order the {v}."],
                 either=["Either {p} or {q} ordered the {v}."],
                 ask="Who ordered the {v}?"),
        ],
        "order": [
            dict(name="race", intro="{n} runners - {names} - finished a race with no ties.",
                 before=["{p} finished ahead of {q}.", "{p} beat {q}."],
                 right_after=["{p} finished immediately after {q}."],
                 gap1=["Exactly one runner finished between {p} and {q}."],
                 between=["{r} finished somewhere between {p} and {q}."],
                 pos=["{p} finished {k}."], notpos=["{p} did not finish {k}."],
                 ask="Who finished {k}?"),
        ],
    },
    "B": {
        "assign": [
            dict(name="rooms", values=["red", "blue", "green", "yellow", "white"],
                 intro="An office has {nl} staff - {names} - and each sits in a different coloured room ({vals}).",
                 is_=["The {v} room is {p}'s."], not_=["{p} is not in the {v} room.", "The {v} room isn't {p}'s."],
                 either=["The {v} room is occupied by {p} or {q} (not by anyone else)."],
                 ask="Whose is the {v} room?"),
            dict(name="books", values=["novel", "atlas", "diary", "cookbook", "manual"],
                 intro="{names} each picked up a different book from a shelf holding a {vals_or}.",
                 is_=["{p} picked the {v}."], not_=["{p} left the {v} on the shelf.", "{p} did not pick the {v}."],
                 either=["The {v} went to one of {p} and {q}."],
                 ask="Who ended up with the {v}?"),
        ],
        "order": [
            dict(name="queue", intro="{n} people - {names} - stand in a single queue at a ticket counter.",
                 before=["{p} stands somewhere ahead of {q}.", "{q} is behind {p} in the queue."],
                 right_after=["{p} is directly behind {q}.", "{q} is right in front of {p}."],
                 gap1=["{p} and {q} have exactly one person between them."],
                 between=["{r} is in the queue between {p} and {q}."],
                 pos=["{p} is {k} in line."], notpos=["{p} is not {k} in line."],
                 ask="Who is {k} in line?"),
        ],
    },
}

KIND_KEYS = {"is": "is_", "not": "not_", "either": "either", "before": "before", "right_after": "right_after",
             "gap1": "gap1", "between": "between", "pos": "pos", "notpos": "notpos"}


def render_clue(theme, clue, names, values, rng, ordering):
    key = KIND_KEYS[clue[0]]
    tpl = rng.choice(theme[key])
    d = {}
    k = clue[0]
    if k in ("is", "not"):
        d = dict(p=names[clue[1]], v=values[clue[2]])
    elif k == "either":
        d = dict(p=names[clue[1]], q=names[clue[2]], v=values[clue[3]])
    elif k in ("before", "right_after", "gap1"):
        d = dict(p=names[clue[1]], q=names[clue[2]])
    elif k == "between":
        d = dict(p=names[clue[1]], q=names[clue[2]], r=names[clue[3]])
    elif k in ("pos", "notpos"):
        d = dict(p=names[clue[1]], k=ORD[clue[2]])
    return tpl.format(**d)


# ------------------------------------------------------------------ generation
def build_puzzle(rng, set_name, n, hard, ordering):
    themes = THEMES[set_name]["order" if ordering else "assign"]
    theme = rng.choice(themes)
    names = rng.sample(PEOPLE, n)
    values = list(range(n)) if ordering else rng.sample(theme["values"], n)
    sol = list(range(n))
    rng.shuffle(sol)
    sol = tuple(sol)
    if ordering:
        kinds = {"before", "right_after", "gap1", "between", "notpos"} | ({"pos"} if not hard else set())
    else:
        kinds = {"not", "either"} | ({"is"} if not hard else set())
    pool = all_true_clues(sol, n, kinds)
    target_p = rng.randrange(n)  # asked about: who has value/position of target_p
    ask_val = sol[target_p]
    for _ in range(200):
        rng.shuffle(pool)
        chosen = []
        for c in pool:
            # never state the answer directly
            if c[0] in ("is", "pos") and c[1] == target_p:
                continue
            chosen.append(c)
            if len(count_solutions(chosen, n)) == 1:
                break
        else:
            continue
        # prune redundant clues
        for c in list(chosen):
            rest = [x for x in chosen if x is not c]
            if len(count_solutions(rest, n)) == 1:
                chosen = rest
        lo, hi = (3, 5) if not hard else (6, 11)
        if lo <= len(chosen) <= hi:
            break
    else:
        return None
    rng.shuffle(chosen)
    lines = [render_clue(theme, c, names, values, rng, ordering) for c in chosen]
    vals_txt = ", ".join(values) if not ordering else ""
    intro = theme["intro"].format(
        n={3: "Three", 4: "Four", 5: "Five"}[n], nl={3: "three", 4: "four", 5: "five"}[n], names=", ".join(names[:-1]) + " and " + names[-1],
        vals=vals_txt, vals_or=", ".join(values[:-1]) + " or " + values[-1] if not ordering else "")
    if ordering:
        ask = theme["ask"].format(k=ORD[ask_val])
    else:
        ask = theme["ask"].format(v=values[ask_val])
    style = rng.choice(["numbered_list", "bullet_list", "paragraph"])
    if style == "numbered_list":
        body = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(lines))
    elif style == "bullet_list":
        body = "\n".join(f"- {t}" for t in lines)
    else:
        body = " ".join(lines)
    prompt = f"{intro}\n\n{body}\n\n{ask}" if style != "paragraph" else f"{intro} {body}\n\n{ask}"
    return dict(prompt=prompt, answer=names[target_p], names=names, values=values, ordering=ordering,
                theme=theme["name"], clues=chosen, style=style, n=n, set_name=set_name, ask_val=ask_val)


# ------------------------------------------------------------------ independent text verification
def _alt(items):
    return "(?:" + "|".join(re.escape(str(i)) for i in sorted(items, key=len, reverse=True)) + ")"


def parse_clues(prompt, set_name, theme_name, names, values, ordering):
    """Parse the English clue sentences back into clue tuples (independent of the generator's tuples)."""
    themes = THEMES[set_name]["order" if ordering else "assign"]
    theme = next(t for t in themes if t["name"] == theme_name)
    pat = {"p": f"(?P<p>{_alt(names)})", "q": f"(?P<q>{_alt(names)})", "r": f"(?P<r>{_alt(names)})",
           "v": f"(?P<v>{_alt(values if not ordering else [])})" if not ordering else "",
           "k": f"(?P<k>{_alt(ORD)})"}
    body = prompt.split("\n\n")
    text = " ".join(body[1:-1]) if len(body) >= 3 else body[0]
    if len(body) == 2:  # paragraph style: intro and clues share a block
        text = body[0]
    text = re.sub(r"(?m)^(?:\d+\.|-)\s+", "", text)
    sents = re.split(r"(?<=\.)\s+|\n", text.strip())
    found = []
    for s in sents:
        s = s.strip()
        for kind, key in KIND_KEYS.items():
            for tpl in theme.get(key, []):
                rx = re.escape(tpl)
                for ph in ("p", "q", "r", "v", "k"):
                    rx = rx.replace(re.escape("{" + ph + "}"), pat[ph] if ph != "v" or not ordering else "")
                m = re.fullmatch(rx, s)
                if not m:
                    continue
                g = m.groupdict()
                idx = lambda nm: names.index(g[nm])  # noqa: E731
                if kind in ("is", "not"):
                    found.append((kind, idx("p"), list(values).index(g["v"])))
                elif kind == "either":
                    found.append(("either", idx("p"), idx("q"), list(values).index(g["v"])))
                elif kind in ("before", "right_after", "gap1"):
                    found.append((kind, idx("p"), idx("q")))
                elif kind == "between":
                    found.append(("between", idx("p"), idx("q"), idx("r")))
                else:
                    found.append((kind, idx("p"), ORD.index(g["k"])))
                break
            else:
                continue
            break
    return found


def solve_backtracking(clues, n):
    """Count solutions by assigning people one by one and pruning with clues whose people are all placed."""
    def people_of(c):
        if c[0] in ("is", "not", "pos", "notpos"):
            return {c[1]}
        if c[0] == "either":
            return {c[1], c[2]}
        if c[0] == "between":
            return {c[1], c[2], c[3]}
        return {c[1], c[2]}
    deps = [(c, people_of(c)) for c in clues]
    sols = []

    def rec(i, a, used):
        if i == n:
            sols.append(tuple(a))
            return
        for v in range(n):
            if v in used:
                continue
            a.append(v)
            placed = set(range(i + 1))
            ok = True
            for c, ps in deps:
                if i in ps and ps <= placed:
                    full = a + [None] * (n - len(a))
                    if not holds(c, full):
                        ok = False
                        break
            if ok:
                rec(i + 1, a, used | {v})
            a.pop()

    rec(0, [], set())
    return sols


def verify_text(p):
    """Return (ok, message) for a puzzle dict produced by build_puzzle."""
    clues = parse_clues(p["prompt"], p["set_name"], p["theme"], p["names"], p["values"], p["ordering"])
    if len(clues) != len(p["clues"]):
        return False, f"parsed {len(clues)} clues, expected {len(p['clues'])}"
    sols = solve_backtracking(clues, p["n"])
    if len(sols) != 1:
        return False, f"{len(sols)} solutions from parsed text"
    ans = p["names"][[i for i, v in enumerate(sols[0]) if v == p["ask_val"]][0]]
    return (ans == p["answer"]), f"text solution says {ans}, gold {p['answer']}"


def generate(set_name, plan, seed):
    """plan: list of (n, hard, ordering). Returns task dicts without ids."""
    rng = random.Random(seed)
    out, seen = [], set()
    for n, hard, ordering in plan:
        for _ in range(500):
            p = build_puzzle(rng, set_name, n, hard, ordering)
            if p is None or p["prompt"] in seen:
                continue
            ok, msg = verify_text(p)
            assert ok, msg + "\n" + p["prompt"]
            seen.add(p["prompt"])
            break
        else:
            raise RuntimeError("could not build puzzle")
        out.append(dict(
            prompt=p["prompt"], gold={"answer": p["answer"], "choices": p["names"]},
            grader="exact", category="logic",
            source=f"generated:{set_name}:{'order' if ordering else 'assign'}_{p['theme']}",
            difficulty="hard" if hard else "easy",
            phrasing=f"{p['style']}", template_set=set_name,
            note=(f"Exactly one of the {len(list(itertools.permutations(range(n))))} arrangements satisfies all "
                  f"{len(p['clues'])} clues (brute force, re-confirmed by a second solver parsing the text); "
                  f"the answer is {p['answer']}."),
        ))
    return out
