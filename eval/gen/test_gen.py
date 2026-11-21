"""Tests for the generators and the drafted math/logic files."""

import json
from pathlib import Path

from eval.gen import logic_gen
from eval.gen.logic_gen import count_solutions, holds, solve_backtracking

DRAFTS = Path(__file__).resolve().parents[1] / "drafts"


def test_holds_semantics():
    a = (2, 0, 1)  # person0 pos2, person1 pos0, person2 pos1
    assert holds(("before", 1, 0), a)
    assert holds(("right_after", 2, 1), a)
    assert holds(("between", 1, 0, 2), a)
    assert holds(("gap1", 0, 1), a)
    assert not holds(("pos", 0, 0), a)


def test_two_solvers_agree_on_random_clue_sets():
    import random
    rng = random.Random(5)
    for _ in range(30):
        n = 4
        sol = tuple(rng.sample(range(n), n))
        pool = logic_gen.all_true_clues(sol, n, {"not", "either", "before", "right_after", "gap1", "pos"})
        clues = rng.sample(pool, 4)
        assert sorted(count_solutions(clues, n)) == sorted(solve_backtracking(clues, n))


def test_generated_puzzles_roundtrip():
    items = logic_gen.generate("A", [(3, False, False), (5, True, True)], seed=9)
    assert len(items) == 2


def test_drafts_math_logic():
    for name in ("math", "logic"):
        items = json.loads((DRAFTS / f"{name}.json").read_text(encoding="utf-8"))
        assert len(items) == 50
        assert len({i["prompt"] for i in items}) == 50
        sets = {s: sum(1 for i in items if i["template_set"] == s) for s in ("A", "B", "hand")}
        assert sets == {"A": 22, "B": 16, "hand": 12}
        assert 22 <= sum(i["difficulty"] == "easy" for i in items) <= 28


def test_drafts_code_and_ner():
    for name in ("code_debug", "code_gen", "ner"):
        items = json.loads((DRAFTS / f"{name}.json").read_text(encoding="utf-8"))
        assert len(items) == 50 and len({i["prompt"] for i in items}) == 50
        assert sum(i["difficulty"] == "easy" for i in items) == 25
