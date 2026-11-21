"""Math task generator (Phase 1, step 3).

Two SEPARATE template sets (D7):
  A = used while building/tuning the Phase 4 solvers (dev only)
  B = never looked at while building solvers; test split draws from B + hand-written items.

Every generated item carries two independent computations:
  primary(params)    - the step-by-step path used to produce the gold answer (Fractions)
  recompute(params)  - a different formulation (closed form with Decimal / brute-force search)
The generator asserts they agree. Rejection sampling keeps every intermediate value integral,
so gold answers are exact.
"""

from __future__ import annotations

import random
from decimal import Decimal as D
from fractions import Fraction as F

NAMES = ["Asha", "Ravi", "Meera", "Karan", "Divya", "Imran", "Sneha", "Vikram", "Tara", "Arjun",
         "Neha", "Rohan", "Pooja", "Farhan", "Leela", "Dev"]
ITEMS = ["notebooks", "pencils", "bottles of juice", "bags of rice", "tickets", "T-shirts",
         "oranges", "chairs", "books", "boxes of chalk"]


def integral(*vals) -> bool:
    return all(F(v).denominator == 1 for v in vals)


def pick(rng, options):
    """options: list of (phrasing, text). Returns (phrasing, text)."""
    return rng.choice(options)


def fmt(n) -> str:
    n = F(n)
    if n.denominator == 1:
        return f"{int(n):,}"
    return f"{float(n):,.2f}"


class Reject(Exception):
    pass


# ------------------------------------------------------------------ SET A
def a_percent_chain(rng, hard):
    n = rng.randrange(200, 2000, 20)
    p1 = rng.choice([10, 15, 20, 25, 30, 40, 50])
    k = rng.randrange(10, 120, 5)
    who = rng.choice(NAMES)
    item = rng.choice(ITEMS)
    if not hard:
        left = F(n) - F(n) * p1 / 100 - k
        if not integral(F(n) * p1 / 100) or left <= 0:
            raise Reject
        rec = D(n) * (1 - D(p1) / 100) - k
        ph, text = pick(rng, [
            ("word_problem", f"A shop has {n} {item}. It sells {p1}% of them on Monday and {k} more on Tuesday. How many {item} are left?"),
            ("casual", f"so {who}'s store started the week with {n} {item}, sold {p1}% on Monday, then another {k} on Tuesday. how many are still on the shelf?"),
            ("imperative", f"Work out how many {item} remain. Starting stock: {n}. Monday sales: {p1}% of the stock. Tuesday sales: {k} units."),
        ])
    else:
        p2 = rng.choice([10, 20, 25, 50])
        k2 = rng.randrange(5, 60, 5)
        a = F(n) * p1 / 100
        r1 = F(n) - a
        b = r1 * p2 / 100
        left = r1 - b - k2
        if not integral(a, b) or left <= 0:
            raise Reject
        rec = D(n) * (1 - D(p1) / 100) * (1 - D(p2) / 100) - k2
        ph, text = pick(rng, [
            ("word_problem", f"A warehouse holds {n} {item}. On day one it ships out {p1}% of them. On day two it ships {p2}% of what remains, and on day three another {k2}. How many {item} are left after day three?"),
            ("embedded", f"Quick one for the inventory report - we opened the quarter with {n} {item}. Week 1 we lost {p1}% of that to sales, week 2 we sold {p2}% of whatever was left, and in week 3 a further {k2} went out. What's the closing stock?"),
            ("formal", f"An initial stock of {n} {item} is depleted in three stages: {p1}% of the initial stock, then {p2}% of the remaining stock, then {k2} units. Determine the final stock."),
        ])
    return dict(prompt=text, answer=left, check=rec, phrasing=ph, family="percent_chain")


def a_shopping(rng, hard):
    q1 = rng.randrange(2, 9)
    pr1 = rng.randrange(12, 90, 3)
    note = rng.choice([500, 1000, 2000])
    who = rng.choice(NAMES)
    if not hard:
        total = q1 * pr1
        if total >= note:
            raise Reject
        change = F(note - total)
        rec = D(note) - D(q1) * D(pr1)
        ph, text = pick(rng, [
            ("word_problem", f"{who} buys {q1} notebooks at ₹{pr1} each and pays with a ₹{note} note. How much change does {who} get?"),
            ("casual", f"i handed over ₹{note} for {q1} notebooks that cost ₹{pr1} apiece - what should i get back?"),
            ("imperative", f"Calculate the change from a ₹{note} note after buying {q1} items priced at ₹{pr1} each."),
        ])
    else:
        q2 = rng.randrange(2, 7)
        pr2 = rng.randrange(20, 150, 5)
        disc = rng.choice([10, 20, 25])
        sub = F(q1 * pr1 + q2 * pr2)
        paid = sub - sub * disc / 100
        change = F(note) - paid
        if not integral(sub * disc / 100) or change <= 0:
            raise Reject
        rec = D(note) - (D(q1) * D(pr1) + D(q2) * D(pr2)) * (1 - D(disc) / 100)
        ph, text = pick(rng, [
            ("word_problem", f"{who} buys {q1} pens at ₹{pr1} each and {q2} folders at ₹{pr2} each. The whole bill gets a {disc}% discount. {who} pays with a ₹{note} note. How much change comes back?"),
            ("embedded", f"Bill check before I close the till: {q1} pens (₹{pr1} each) and {q2} folders (₹{pr2} each), {disc}% off the total, customer gave ₹{note}. How much change do I owe them?"),
            ("formal", f"A customer purchases {q1} units of item P at ₹{pr1} and {q2} units of item Q at ₹{pr2}. A {disc}% discount applies to the total. If the customer tenders ₹{note}, compute the change returned."),
        ])
    return dict(prompt=text, answer=change, check=rec, phrasing=ph, family="shopping")


def a_ratio_split(rng, hard):
    who = rng.choice(NAMES)
    if not hard:
        a, b = rng.choice([(2, 3), (3, 5), (1, 4), (3, 7), (2, 5)])
        unit = rng.randrange(10, 90, 5)
        total = (a + b) * unit
        share = F(total) * b / (a + b)
        rec = D(unit) * D(b)
        ph, text = pick(rng, [
            ("word_problem", f"₹{total:,} is divided between two friends in the ratio {a}:{b}. How much does the friend with the larger share receive?"),
            ("casual", f"me and my cousin are splitting ₹{total:,} in the ratio {a} to {b} (he gets the bigger part). how much is his share?"),
            ("imperative", f"Split {total:,} rupees in the ratio {a}:{b}. Report the bigger share."),
        ])
    else:
        a, b, c = rng.choice([(2, 3, 5), (1, 2, 4), (3, 4, 5), (2, 5, 7), (1, 3, 6)])
        unit = rng.randrange(6, 60, 2)
        total = (a + b + c) * unit
        share = F(total) * (c - a) / (a + b + c)
        rec = D(unit) * D(c) - D(unit) * D(a)
        ph, text = pick(rng, [
            ("word_problem", f"A prize of ₹{total:,} is shared among three people in the ratio {a}:{b}:{c}. How much more does the person with the largest share get than the person with the smallest?"),
            ("embedded", f"Hi - {who} here. The three of us put money into the stall in the ratio {a}:{b}:{c} and the ₹{total:,} profit has to be split the same way. How much bigger is the top share than the bottom share?"),
            ("formal", f"A sum of ₹{total:,} is apportioned in the ratio {a}:{b}:{c}. Find the difference between the greatest and the least portion."),
        ])
    return dict(prompt=text, answer=share, check=rec, phrasing=ph, family="ratio_split")


def a_growth(rng, hard):
    n0 = rng.randrange(1000, 9000, 100) * 2
    if not hard:
        r = rng.choice([10, 20, 5, 25])
        yrs = 2
        v = F(n0)
        for _ in range(yrs):
            v = v * (100 + r) / 100
        if not integral(v):
            raise Reject
        rec = D(n0) * (1 + D(r) / 100) ** yrs
        ph, text = pick(rng, [
            ("word_problem", f"A town has {n0:,} people and its population grows {r}% every year. How many people live there after {yrs} years?"),
            ("casual", f"our village has {n0:,} residents and it keeps growing by {r}% a year. what will the population be {yrs} years from now?"),
            ("imperative", f"Project the population after {yrs} years. Current: {n0:,}. Annual growth: {r}%, compounded."),
        ])
    else:
        r1, r2, r3 = rng.choice([10, 20, 25]), -rng.choice([10, 20, 50]), rng.choice([10, 20, 5])
        v = F(n0)
        for r in (r1, r2, r3):
            v = v * (100 + r) / 100
        if not integral(v):
            raise Reject
        rec = D(n0) * (1 + D(r1) / 100) * (1 + D(r2) / 100) * (1 + D(r3) / 100)
        ph, text = pick(rng, [
            ("word_problem", f"A company has {n0:,} subscribers. Over three consecutive years its subscriber count changes by +{r1}%, {r2}% and +{r3}% respectively. How many subscribers does it have at the end of year three?"),
            ("embedded", f"For the board deck: we began with {n0:,} subscribers; year 1 grew {r1}%, year 2 shrank {abs(r2)}%, year 3 grew {r3}%. What is the year-3 subscriber count?"),
            ("formal", f"Starting from {n0:,} units, a quantity is changed successively by +{r1}%, {r2}% and +{r3}%. Determine the final quantity."),
        ])
    return dict(prompt=text, answer=v, check=rec, phrasing=ph, family="growth")


def a_unit_rate(rng, hard):
    if not hard:
        mins = rng.choice([6, 8, 9, 12, 15])
        per = rng.randrange(4, 30)
        made = per * mins
        hours = rng.choice([2, 3, 4])
        total = F(made, mins) * hours * 60
        rec = D(made) / D(mins) * D(hours) * 60
        if not integral(total):
            raise Reject
        ph, text = pick(rng, [
            ("word_problem", f"A machine makes {made} bolts in {mins} minutes. At the same rate, how many bolts does it make in {hours} hours?"),
            ("casual", f"our press stamps out {made} bolts every {mins} min. running it nonstop for {hours} hours, how many bolts is that?"),
            ("imperative", f"Rate: {made} bolts per {mins} minutes. Compute the output over {hours} hours."),
        ])
        ans = total
    else:
        r1 = rng.choice([12, 15, 20, 24, 30])
        r2 = rng.choice([8, 10, 16, 18, 25])
        h1 = rng.choice([2, 3, 4])
        h2 = rng.choice([1, 2, 3])
        if h2 >= h1:
            raise Reject
        ph, text = pick(rng, [
            ("word_problem", f"Machine P makes {r1} parts per hour. Machine Q makes {r2} parts per hour and is switched on only for the last {h2} hours of a {h1}-hour shift, while P runs the whole shift. How many parts do the two machines make in total?"),
            ("embedded", f"Shift summary needed: P ran for the full {h1} hours at {r1} parts/hour; Q joined for just the final {h2} hours at {r2} parts/hour. Total parts from both?"),
            ("formal", f"During a {h1}-hour shift, machine P produces {r1} parts per hour throughout, and machine Q, producing {r2} parts per hour, operates only during the final {h2} hours. Find the combined production."),
        ])
        ans = F(r1 * h1 + r2 * h2)
        rec = D(r1) * D(h1) + D(r2) * D(h2)
    return dict(prompt=text, answer=ans, check=rec, phrasing=ph, family="unit_rate")


# ------------------------------------------------------------------ SET B
def b_markup_discount(rng, hard):
    cost = rng.randrange(200, 1500, 50)
    m = rng.choice([20, 25, 30, 40, 50])
    d = rng.choice([10, 20, 25])
    mark = F(cost) * (100 + m) / 100
    sale = mark * (100 - d) / 100
    if not integral(mark, sale):
        raise Reject
    if not hard:
        ans = mark - cost
        rec = D(cost) * D(m) / 100
        ph, text = pick(rng, [
            ("word_problem", f"A trader buys a lamp for ₹{cost} and marks it up by {m}%. By how many rupees is the marked price above the cost price?"),
            ("casual", f"bought a lamp wholesale at ₹{cost}, tagged it {m}% higher. how many rupees of markup is that?"),
            ("imperative", f"Cost price ₹{cost}, markup {m}%. State the markup amount in rupees."),
        ])
    else:
        ans = sale - cost
        rec = D(cost) * (1 + D(m) / 100) * (1 - D(d) / 100) - D(cost)
        ph, text = pick(rng, [
            ("word_problem", f"A shopkeeper buys a jacket for ₹{cost}, marks it {m}% above cost, then sells it during a sale at {d}% off the marked price. What is the profit (or, if negative, the loss as a negative number) in rupees?"),
            ("embedded", f"Margin check for the month-end sheet: jacket cost ₹{cost}, price tag = cost + {m}%, then we ran a {d}% off sale on the tag price. Net profit per jacket in rupees (negative if loss)?"),
            ("formal", f"An article costing ₹{cost} is listed at a price {m}% above cost and subsequently sold at a {d}% discount on the listed price. Compute the net gain in rupees; give a negative value for a loss."),
        ])
    return dict(prompt=text, answer=ans, check=rec, phrasing=ph, family="markup_discount")


def b_average(rng, hard):
    if not hard:
        k = rng.choice([3, 4, 5])
        target = rng.randrange(60, 90, 2)
        scores = [rng.randrange(40, 100) for _ in range(k)]
        need = target * (k + 1) - sum(scores)
        if not (0 <= need <= 100):
            raise Reject
        # independent: search for the score that makes the mean equal target
        rec = next(x for x in range(0, 101) if D(sum(scores) + x) / (k + 1) == D(target))
        sc = ", ".join(map(str, scores))
        ph, text = pick(rng, [
            ("word_problem", f"A student scored {sc} in her first {k} tests. What must she score in the next test so that her average over all {k + 1} tests is exactly {target}?"),
            ("casual", f"my marks so far: {sc}. what do i need in the next paper for my average across all {k + 1} to be {target} exactly?"),
            ("imperative", f"Given test scores {sc}, find the score on test {k + 1} that makes the mean of all {k + 1} scores equal {target}."),
        ])
        return dict(prompt=text, answer=F(need), check=D(rec), phrasing=ph, family="average")
    n1, n2 = rng.choice([10, 20, 30, 40]), rng.choice([10, 20, 30, 40])
    x1, x2 = rng.randrange(50, 90), rng.randrange(50, 90)
    ans = F(n1 * x1 + n2 * x2, n1 + n2)
    rec = (D(n1) * D(x1) + D(n2) * D(x2)) / D(n1 + n2)
    if not integral(ans):
        raise Reject
    ph, text = pick(rng, [
        ("word_problem", f"Section A has {n1} students with an average mark of {x1}. Section B has {n2} students with an average mark of {x2}. What is the average mark of all {n1 + n2} students together?"),
        ("embedded", f"Writing the school report: {n1} kids in section A averaged {x1}, and the {n2} in section B averaged {x2}. What was the combined average for the two sections?"),
        ("formal", f"Two groups of sizes {n1} and {n2} have mean scores {x1} and {x2} respectively. Calculate the overall mean of the merged group."),
    ])
    return dict(prompt=text, answer=ans, check=rec, phrasing=ph, family="average")


def b_travel(rng, hard):
    v1, v2 = rng.choice([30, 40, 45, 60, 80]), rng.choice([20, 30, 50, 60, 90])
    s1, s2 = rng.randrange(60, 300, 30), rng.randrange(60, 300, 30)
    t = F(s1, v1) + F(s2, v2)
    if not hard:
        if not integral(F(s1, v1)) or not integral(F(s2, v2)):
            raise Reject
        ans = t
        rec = D(s1) / D(v1) + D(s2) / D(v2)
        ph, text = pick(rng, [
            ("word_problem", f"A bus travels {s1} km at {v1} km/h and then another {s2} km at {v2} km/h. How many hours does the whole journey take?"),
            ("casual", f"drove {s1} km doing {v1} km/h, then {s2} km at {v2} km/h. total time on the road in hours?"),
            ("imperative", f"Leg 1: {s1} km at {v1} km/h. Leg 2: {s2} km at {v2} km/h. Find the total travel time in hours."),
        ])
    else:
        ans = F(s1 + s2) / t
        if not integral(ans):
            raise Reject
        rec = (D(s1) + D(s2)) / (D(s1) / D(v1) + D(s2) / D(v2))
        ph, text = pick(rng, [
            ("word_problem", f"A courier covers {s1} km at {v1} km/h and then {s2} km at {v2} km/h. What is the average speed for the whole trip, in km/h?"),
            ("embedded", f"For the logbook: the first stretch was {s1} km at {v1} km/h, the second {s2} km at {v2} km/h. What was the average speed over the full distance, km/h?"),
            ("formal", f"A vehicle traverses {s1} km at a constant {v1} km/h followed by {s2} km at a constant {v2} km/h. Determine the average speed over the entire journey in km/h."),
        ])
    return dict(prompt=text, answer=ans, check=rec, phrasing=ph, family="travel")


def b_savings(rng, hard):
    p = rng.randrange(10, 100, 5) * 100
    r = rng.choice([5, 8, 10, 12, 20])
    if not hard:
        yrs = rng.choice([2, 3, 4, 5])
        ans = F(p) + F(p) * r * yrs / 100
        rec = D(p) * (1 + D(r) * yrs / 100)
        if not integral(ans):
            raise Reject
        ph, text = pick(rng, [
            ("word_problem", f"₹{p:,} is deposited at {r}% simple interest per year. What is the total amount after {yrs} years?"),
            ("casual", f"put ₹{p:,} in a deposit paying {r}% simple interest a year. how much will i have after {yrs} years?"),
            ("imperative", f"Principal ₹{p:,}, simple interest {r}% p.a., time {yrs} years. Give the final amount."),
        ])
    else:
        add = rng.randrange(5, 50, 5) * 100
        v = F(p)
        for _ in range(2):
            v = v * (100 + r) / 100
        v = (v + add) * (100 + r) / 100
        ans = v
        if not integral(ans):
            raise Reject
        g = 1 + D(r) / 100
        rec = (D(p) * g * g + D(add)) * g
        ph, text = pick(rng, [
            ("word_problem", f"₹{p:,} is invested at {r}% compound interest per year. After two years, an extra ₹{add:,} is added, and the whole balance then grows for one more year at the same rate. What is the final balance?"),
            ("embedded", f"Planning my savings: ₹{p:,} sits in an account earning {r}% a year, compounded annually. At the end of year 2 I top it up with ₹{add:,}, and leave everything in for year 3. What's the balance after year 3?"),
            ("formal", f"A principal of ₹{p:,} earns {r}% interest per annum, compounded annually. At the end of the second year a deposit of ₹{add:,} is made. Find the balance at the end of the third year."),
        ])
    return dict(prompt=text, answer=ans, check=rec, phrasing=ph, family="savings")


def b_age_linear(rng, hard):
    if not hard:
        s = rng.randrange(40, 200)
        d = rng.randrange(2, 30)
        if (s + d) % 2:
            raise Reject
        big = F(s + d, 2)
        rec = next(x for x in range(0, 400) if x + (x - d) == s)
        ph, text = pick(rng, [
            ("word_problem", f"The sum of two numbers is {s} and their difference is {d}. What is the larger number?"),
            ("casual", f"two numbers add up to {s} and differ by {d}. which one's the bigger one?"),
            ("imperative", f"Find the larger of two numbers whose sum is {s} and whose difference is {d}."),
        ])
        return dict(prompt=text, answer=big, check=D(rec), phrasing=ph, family="age_linear")
    k = rng.choice([2, 3, 4, 5])
    yrs = rng.randrange(4, 20)
    m = rng.choice([2, 3])
    if m >= k:
        raise Reject
    # father = k*son; in `yrs` years father = m*son  => k*s + yrs = m*(s + yrs)
    num = yrs * (m - 1)
    if num % (k - m):
        raise Reject
    s = F(num, k - m)
    rec = next((x for x in range(1, 150) if k * x + yrs == m * (x + yrs)), None)
    if rec is None or s != rec:
        raise Reject
    who = rng.choice(NAMES)
    ph, text = pick(rng, [
        ("word_problem", f"{who} is {k} times as old as {who}'s daughter. In {yrs} years {who} will be {m} times as old as the daughter will be then. How old is the daughter now?"),
        ("embedded", f"Funny coincidence at the family dinner: {who} is exactly {k} times my age right now, but in {yrs} years {who} will be only {m} times my age. How old am I now?"),
        ("formal", f"A parent's age is {k} times the child's age. After {yrs} years, the parent's age will be {m} times the child's age. Determine the child's present age."),
    ])
    return dict(prompt=text, answer=s, check=D(rec), phrasing=ph, family="age_linear")


SET_A = [a_percent_chain, a_shopping, a_ratio_split, a_growth, a_unit_rate]
SET_B = [b_markup_discount, b_average, b_travel, b_savings, b_age_linear]


def generate(set_name: str, n_easy: int, n_hard: int, seed: int):
    """Return list of item dicts (no ids yet) for template set A or B."""
    rng = random.Random(seed)
    fams = SET_A if set_name == "A" else SET_B
    out, seen = [], set()
    for hard, n in ((False, n_easy), (True, n_hard)):
        k = 0
        guard = 0
        while k < n:
            guard += 1
            assert guard < 20000, "generator stuck"
            fam = fams[(k + (7 if hard else 0)) % len(fams)]
            try:
                it = fam(rng, hard)
            except Reject:
                continue
            ans, chk = F(it["answer"]), F(str(it["check"]))
            assert ans == chk, f"primary/recompute disagree in {fam.__name__}: {ans} vs {chk}\n{it['prompt']}"
            if ans <= 0 and not (fam is b_markup_discount):
                continue
            if it["prompt"] in seen:
                continue
            seen.add(it["prompt"])
            out.append(dict(
                prompt=it["prompt"],
                gold={"answer": int(ans) if ans.denominator == 1 else float(ans),
                      "tolerance": 0 if ans.denominator == 1 else 0.01},
                grader="numeric", category="math",
                source=f"generated:{set_name}:{it['family']}",
                difficulty="hard" if hard else "easy",
                phrasing=it["phrasing"], template_set=set_name,
                note=f"Computed in exact fractions and re-derived by an independent formulation ({it['family']}); both agree on {ans}.",
            ))
            k += 1
    return out
