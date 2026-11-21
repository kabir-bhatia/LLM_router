import pytest

from router.solvers.logic_solver import solve_logic
from router.solvers.math_solver import solve_math
from router.solvers.safe_arith import UnsafeExpression, fmt, safe_eval
from fractions import Fraction


def test_safe_eval_basic():
    assert safe_eval("2 + 3 * 4") == 14
    assert safe_eval("(1 - 20/100) * 50") == 40
    assert safe_eval("1.25 ** 2") == Fraction(25, 16)


@pytest.mark.parametrize("bad", ["__import__('os').system('x')", "open('f')", "a + 1", "2 ** 100", "1 / 0",
                                 "[1][0]", "(lambda: 1)()", "1 if 1 else 2", "'a' * 3"])
def test_safe_eval_rejects(bad):
    with pytest.raises(UnsafeExpression):
        safe_eval(bad)


def test_fmt():
    assert fmt(Fraction(5)) == "5"
    assert fmt(Fraction(5, 2)) == "2.5"
    assert fmt(Fraction(1, 3)) is None


def test_math_sequential():
    r = solve_math("A shop has 200 mugs. It sells 25% on Monday and 10 more on Tuesday. How many mugs are left?")
    assert r.answer == "140"


def test_math_ratio():
    assert solve_math("Split 90 rupees in the ratio 1:2. Report the bigger share.").answer == "60"


def test_math_defers_when_unsure():
    # a number the recipes cannot account for -> defer
    r = solve_math("A tank holds 500 litres and leaks 7 litres per hour for 3 hours. How many litres are left?")
    assert not r.answered or r.answer == "479"  # never a wrong guess; (it may defer)
    assert not solve_math("Why is the sky blue?").answered
    assert not solve_math("Sam has 12 apples and 7 pears. What is the ratio of apples to pears?").answered


def test_math_ambiguous_direction_defers():
    assert not solve_math("A box starts with 100 items. Then 30 items happen. How many are left?").answered


def test_math_purchase_unaccounted_number_defers():
    p = "Ana buys 3 pens at ₹20 each. She uses a coupon worth 5 rupees. She pays with a ₹100 note. How much change comes back?"
    assert not solve_math(p).answered


LOGIC_RACE = ("Three runners - Ann, Bo and Cy - finished a race with no ties.\n\n1. Ann beat Bo.\n2. Cy did not finish first.\n"
              "3. Bo did not finish second.\n\nWho finished first?")


def test_logic_race_unique():
    r = solve_logic(LOGIC_RACE)
    # Ann<Bo, Cy!=1, Bo!=2 -> Ann 1, Cy 2, Bo 3
    assert r.answer == "Ann"


def test_logic_attr_unique():
    p = ("Three friends - Ann, Bo and Cy - each own a different pet: cat, dog, fish. Ann owns the cat. "
         "Bo does not own the dog. Who owns the fish?")
    assert solve_logic(p).answer == "Bo"


def test_logic_not_unique_defers():
    p = "Three runners - Ann, Bo and Cy - finished a race with no ties. Ann beat Bo. Who finished first?"
    r = solve_logic(p)
    assert not r.answered and r.n_solutions == 2


def test_logic_unparsed_sentence_defers():
    p = "Three runners - Ann, Bo and Cy - finished a race with no ties. Ann is faster than Bo. Who finished first?"
    assert not solve_logic(p).answered


def test_logic_non_puzzle_defers():
    assert not solve_logic("Who wrote Hamlet?").answered
