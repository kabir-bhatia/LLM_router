"""Hand-written math and logic items (12 each).

Math: each item has two independently written computations (`via_a`, `via_b`) that must agree
with the stated gold. Logic: each item is a tiny constraint model; brute force over every
assignment must find exactly one solution and it must give the stated answer.
"""

from __future__ import annotations

import itertools
from fractions import Fraction as F
from math import comb, gcd

# ---------------------------------------------------------------- math
# (prompt, gold, via_a, via_b, difficulty, phrasing, note)
HAND_MATH = [
    ("A tank is filled by pipe A alone in 6 hours and by pipe B alone in 3 hours. With both pipes open together, how many minutes does it take to fill the empty tank?",
     120, lambda: 1 / (F(1, 6) + F(1, 3)) * 60, lambda: (6 * 3 / (6 + 3)) * 60, "hard", "word_problem",
     "Combined rate 1/6+1/3 = 1/2 tank per hour, so 2 hours = 120 minutes."),
    ("The price of a bike is raised by 20% and then the new price is cut by 20%. If the bike started at ₹500, what does it cost at the end?",
     480, lambda: F(500) * F(6, 5) * F(4, 5), lambda: 500 - 500 * F(4, 100), "easy", "word_problem",
     "500*1.2 = 600; 600*0.8 = 480 (a +20%/-20% pair nets -4%)."),
    ("hey, a train does the first 120 km at 60 km/h and the next 120 km at 40 km/h. what's its average speed over the whole 240 km?",
     48, lambda: F(240) / (F(120, 60) + F(120, 40)), lambda: 2 * 60 * 40 / (60 + 40), "hard", "casual",
     "Time = 2h + 3h = 5h; 240/5 = 48 km/h (not the simple mean 50)."),
    ("In how many different ways can a committee of 3 people be chosen from a group of 8 people?",
     56, lambda: comb(8, 3), lambda: 8 * 7 * 6 // 6, "easy", "word_problem",
     "C(8,3) = 8*7*6/3! = 56."),
    ("A recipe that serves 4 people uses 300 g of flour. How many grams of flour are needed to serve 10 people with the same recipe?",
     750, lambda: F(300, 4) * 10, lambda: F(300) * F(10, 4), "easy", "word_problem",
     "75 g per person, times 10 = 750 g."),
    ("A town of 8,000 people grows 5% in one year and another 5% the next year. What is its population after the two years?",
     8820, lambda: F(8000) * F(21, 20) * F(21, 20), lambda: 8000 + 400 + 420, "easy", "word_problem",
     "8000 -> 8400 -> 8820."),
    ("The sum of three consecutive even numbers is 78. What is the largest of the three?",
     28, lambda: F(78, 3) + 2, lambda: next(x + 4 for x in range(0, 100, 2) if x + (x + 2) + (x + 4) == 78), "hard", "word_problem",
     "Middle = 78/3 = 26, so the numbers are 24, 26, 28."),
    ("After a 20% discount, a phone costs ₹24,000. What was its price before the discount?",
     30000, lambda: F(24000) / F(4, 5), lambda: next(x for x in range(0, 100000, 1000) if x * 4 // 5 == 24000), "hard", "word_problem",
     "24,000 is 80% of the original, so original = 24,000/0.8 = 30,000."),
    ("Two positive integers have a greatest common divisor of 5 and a least common multiple of 60. One of them is 15. What is the other?",
     20, lambda: F(5 * 60, 15), lambda: next(x for x in range(1, 200) if gcd(x, 15) == 5 and x * 15 // gcd(x, 15) == 60), "hard", "formal",
     "gcd*lcm = product, so other = 5*60/15 = 20; check gcd(20,15)=5, lcm=60."),
    ("You have 30 litres of a 20% acid solution. How many litres of pure acid must be added to make it a 40% solution?",
     10, lambda: F(30 * 40 - 30 * 20, 100 - 40), lambda: next(x for x in range(0, 100) if (6 + x) * 100 == 40 * (30 + x)), "hard", "word_problem",
     "6 L acid now; (6+x)/(30+x) = 0.4 gives x = 10."),
    ("A salary of ₹50,000 is spent as follows: 30% on rent, then 20% of what remains on food. How many rupees are left after rent and food?",
     28000, lambda: F(50000) * F(7, 10) * F(4, 5), lambda: 50000 - 15000 - (50000 - 15000) // 5, "easy", "word_problem",
     "Rent 15,000 leaves 35,000; food 7,000 leaves 28,000."),
    ("A faulty clock gains exactly 3 minutes every hour. It is set to the correct time at 8:00 am. When the true time is 2:00 pm, how many minutes ahead of the true time does the clock show?",
     18, lambda: 3 * (14 - 8), lambda: sum(3 for _ in range(8, 14)), "easy", "word_problem",
     "6 hours elapse, 3 minutes gained per hour = 18 minutes."),
]


def hand_math_items():
    out = []
    for prompt, gold, va, vb, diff, ph, note in HAND_MATH:
        a, b = F(va()), F(vb())
        assert a == b == F(gold), f"hand math mismatch: {prompt[:50]} {a} {b} {gold}"
        out.append(dict(prompt=prompt, gold={"answer": gold, "tolerance": 0}, grader="numeric", category="math",
                        source="hand", difficulty=diff, phrasing=ph, template_set="hand",
                        note=note + " Checked by two independent computations."))
    return out


# ---------------------------------------------------------------- logic
K, N = "knight", "knave"


def _tf(env, who, stmt_true):
    """Knight statements are true, knave statements false."""
    return (env[who] == K) == stmt_true


# (prompt, domains, constraint, ask_var, gold, difficulty, phrasing, note)
HAND_LOGIC = [
    ("On an island, knights always tell the truth and knaves always lie. Amit says: \"Bina is a knave.\" Bina says: \"Amit and I are both knights.\" Is Bina a knight or a knave?",
     {"A": [K, N], "B": [K, N]},
     lambda e: _tf(e, "A", e["B"] == N) and _tf(e, "B", e["A"] == K and e["B"] == K),
     "B", "knave", "easy", "puzzle_story",
     "If Amit were a knave, Bina would be a knight, but then her claim that Amit is a knight would be false: contradiction. So Amit is a knight, Bina a knave."),
    ("On the same island (knights always tell the truth, knaves always lie), three people speak. Dara says: \"Eshan and Farid are the same type.\" Eshan says: \"Dara is a knave.\" Farid says: \"Eshan is a knight.\" Is Farid a knight or a knave?",
     {"D": [K, N], "E": [K, N], "F": [K, N]},
     lambda e: _tf(e, "D", e["E"] == e["F"]) and _tf(e, "E", e["D"] == N) and _tf(e, "F", e["E"] == K),
     "F", None, "hard", "puzzle_story", ""),
    ("Three boxes are labelled \"Apples\", \"Oranges\" and \"Mixed\". Each box really contains one of: only apples, only oranges, or a mix of both, and every label is wrong. You take one fruit out of the box labelled \"Mixed\" and it is an apple. What does the box labelled \"Oranges\" contain? (answer: apples, oranges or mixed)",
     {"A": ["apples", "oranges", "mixed"], "O": ["apples", "oranges", "mixed"], "M": ["apples", "oranges", "mixed"]},
     lambda e: len({e["A"], e["O"], e["M"]}) == 3 and e["A"] != "apples" and e["O"] != "oranges"
     and e["M"] != "mixed" and e["M"] != "oranges",
     "O", "mixed", "easy", "puzzle_story",
     "Mixed-labelled box is wrong so it is pure, and an apple came out, so it is apples; Oranges-labelled box cannot be oranges or apples, so it is mixed."),
    ("Exactly one of three suspects took the cookie. Exactly one of their three statements is true. Xena says: \"Yusuf took it.\" Yusuf says: \"I did not take it.\" Zane says: \"Xena is lying.\" Who took the cookie?",
     {"who": ["Xena", "Yusuf", "Zane"]},
     lambda e: sum([e["who"] == "Yusuf", e["who"] != "Yusuf", not (e["who"] == "Yusuf")]) == 1,
     "who", "Yusuf", "hard", "puzzle_story", ""),
    ("Ria is older than Sam. Sam is older than Tom. Uma is younger than Tom but older than Vik. Of the five, who is the middle one in age (third oldest)?",
     {n: [0, 1, 2, 3, 4] for n in "RSTUV"},
     lambda e: len(set(e.values())) == 5 and e["R"] < e["S"] < e["T"] < e["U"] < e["V"],
     None, "Tom", "easy", "puzzle_ordering", "Chain Ria > Sam > Tom > Uma > Vik; the third is Tom."),
    ("Four talks - Ads, Bots, Cloud and Data - are given one per day from Monday to Thursday. Bots is not on Monday or Thursday. Ads is on an earlier day than Cloud. Data is exactly two days after Ads. Cloud is not on a day adjacent to Bots. Which talk is on Thursday?",
     {t: [0, 1, 2, 3] for t in ("Ads", "Bots", "Cloud", "Data")},
     lambda e: len(set(e.values())) == 4 and e["Bots"] in (1, 2) and e["Ads"] < e["Cloud"]
     and e["Data"] == e["Ads"] + 2 and abs(e["Cloud"] - e["Bots"]) != 1,
     None, None, "hard", "puzzle_scheduling", ""),
    ("Four chairs stand in a row, numbered 1 to 4 from the left. Dev, Eli, Fay and Gia each sit on one. Dev is not on either end chair. Eli sits on the chair immediately to the right of Dev. Fay is on chair 1. Gia does not sit next to Fay. Who is on chair 4?",
     {n: [1, 2, 3, 4] for n in ("Dev", "Eli", "Fay", "Gia")},
     lambda e: len(set(e.values())) == 4 and e["Dev"] in (2, 3) and e["Eli"] == e["Dev"] + 1
     and e["Fay"] == 1 and abs(e["Gia"] - e["Fay"]) != 1,
     None, "Gia", "easy", "puzzle_seating", "Dev=2, Eli=3, Gia=4 is the only seating that keeps Gia away from Fay."),
    ("Five colleagues - Ravi, Sia, Tej, Uday and Vera - live on different floors (1 to 5) of a building. Ravi lives neither on the top floor nor on the ground floor. Sia lives higher than Ravi. Tej lives exactly two floors below Sia. Uday lives on floor 1. Vera lives higher than Sia. Who lives on floor 3?",
     {n: [1, 2, 3, 4, 5] for n in ("Ravi", "Sia", "Tej", "Uday", "Vera")},
     lambda e: len(set(e.values())) == 5 and e["Ravi"] not in (1, 5) and e["Sia"] > e["Ravi"]
     and e["Tej"] == e["Sia"] - 2 and e["Uday"] == 1 and e["Vera"] > e["Sia"],
     None, None, "hard", "puzzle_floors", ""),
    ("Ana, Ben and Cy each chose a different drink: tea, coffee or juice. If Ana chose tea, then Ben chose coffee. Ana did not choose coffee. Ben did not choose juice. Cy did not choose tea. If Ben chose tea, then Cy chose juice. Who chose juice?",
     {"Ana": ["tea", "coffee", "juice"], "Ben": ["tea", "coffee", "juice"], "Cy": ["tea", "coffee", "juice"]},
     lambda e: len(set(e.values())) == 3 and (e["Ana"] != "tea" or e["Ben"] == "coffee")
     and e["Ana"] != "coffee" and e["Ben"] != "juice" and e["Cy"] != "tea"
     and (e["Ben"] != "tea" or e["Cy"] == "juice"),
     None, None, "hard", "puzzle_conditional", ""),
    ("Three neighbours - Hari, Isha and Jay - each keep a different pet (cat, dog or fish) and each drink a different beverage (milk, tea or soda). Hari keeps the cat. The dog owner drinks tea. Isha drinks soda. Jay does not keep the fish. Who keeps the fish and what do they drink? Answer with the person's name only.",
     {"HP": ["cat", "dog", "fish"], "IP": ["cat", "dog", "fish"], "JP": ["cat", "dog", "fish"],
      "HD": ["milk", "tea", "soda"], "ID": ["milk", "tea", "soda"], "JD": ["milk", "tea", "soda"]},
     lambda e: len({e["HP"], e["IP"], e["JP"]}) == 3 and len({e["HD"], e["ID"], e["JD"]}) == 3
     and e["HP"] == "cat" and e["ID"] == "soda" and e["JP"] != "fish"
     and all(e[p + "P"] != "dog" or e[p + "D"] == "tea" for p in "HIJ"),
     None, None, "hard", "puzzle_two_attribute", ""),
    ("A building project has four jobs: Plumbing, Painting, Decorating and Cleaning, done one after another. Plumbing must come before Painting. Painting must come before Decorating. Cleaning is the last job. Which job is second?",
     {t: [1, 2, 3, 4] for t in ("Plumbing", "Painting", "Decorating", "Cleaning")},
     lambda e: len(set(e.values())) == 4 and e["Plumbing"] < e["Painting"] < e["Decorating"] and e["Cleaning"] == 4,
     None, "Painting", "easy", "puzzle_scheduling", "Order is Plumbing, Painting, Decorating, Cleaning."),
    ("Four people queue at a counter: Kia, Lal, Mia and Ned. Lal is not first. Mia is directly behind Kia. Lal and Ned do not stand next to each other. Ned is not last. Who is third in the queue?",
     {n: [1, 2, 3, 4] for n in ("Kia", "Lal", "Mia", "Ned")},
     lambda e: len(set(e.values())) == 4 and e["Lal"] != 1 and e["Mia"] == e["Kia"] + 1
     and abs(e["Lal"] - e["Ned"]) != 1 and e["Ned"] != 4,
     None, None, "hard", "puzzle_ordering", ""),
]

# Ask rules for puzzles whose question is "who is at X" rather than a variable value.
ASK_OVERRIDES = {
    # prompt prefix -> function(env) -> answer string
    "Ria is older": lambda e: next(k for k, v in e.items() if v == 2) and {"R": "Ria", "S": "Sam", "T": "Tom", "U": "Uma", "V": "Vik"}[next(k for k, v in e.items() if v == 2)],
    "Four talks": lambda e: next(k for k, v in e.items() if v == 3),
    "Four chairs": lambda e: next(k for k, v in e.items() if v == 4),
    "Five colleagues": lambda e: next(k for k, v in e.items() if v == 3),
    "Ana, Ben and Cy": lambda e: next(k for k, v in e.items() if v == "juice"),
    "Three neighbours": lambda e: {"H": "Hari", "I": "Isha", "J": "Jay"}[next(k[0] for k, v in e.items() if k.endswith("P") and v == "fish")],
    "A building project": lambda e: next(k for k, v in e.items() if v == 2),
    "Four people queue": lambda e: next(k for k, v in e.items() if v == 3),
}


def solve_hand(entry):
    prompt, doms, cons, ask, gold, diff, ph, note = entry
    names = list(doms)
    sols = []
    for combo in itertools.product(*[doms[n] for n in names]):
        env = dict(zip(names, combo))
        if cons(env):
            sols.append(env)
    return sols


def hand_logic_items():
    out = []
    for entry in HAND_LOGIC:
        prompt, doms, cons, ask, gold, diff, ph, note = entry
        sols = solve_hand(entry)
        assert len(sols) == 1, f"hand logic not unique ({len(sols)}): {prompt[:60]}"
        env = sols[0]
        ov = next((f for k, f in ASK_OVERRIDES.items() if prompt.startswith(k)), None)
        got = ov(env) if ov else env[ask]
        if gold is None:
            gold = got
            note = note or f"Brute force over every assignment finds exactly one consistent solution; the answer is {gold}."
        assert got == gold, f"hand logic gold mismatch {got} vs {gold}: {prompt[:60]}"
        if len(note) < 5:
            note = f"Unique solution by brute force; answer {gold}."
        choices = None
        out.append(dict(prompt=prompt, gold={"answer": gold}, grader="exact", category="logic", source="hand",
                        difficulty=diff, phrasing=ph, template_set="hand",
                        note=note + " (Unique solution confirmed by exhaustive search.)"))
    return out
