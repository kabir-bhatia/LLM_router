import json

import pytest

from router.solvers.translate import (count_constraint_sentences, parse_logic_translation, parse_math_translation, MATH_SYSTEM,
                                      LOGIC_SYSTEM)

P1 = "A tank holds 800 litres. 25% leaks out, then 40 litres are added. How many litres are in the tank?"


def test_math_good_and_formats():
    assert parse_math_translation("EXPR: 800 * (1 - 0.25) + 40", P1).answer == "640"
    assert parse_math_translation("EXPR: 800 * (1 - 25%) + 40", P1).answer == "640"          # percent literal
    assert parse_math_translation("Sure!\nEXPR: `800 * (1 - 0.25) + 40` = 640", P1).answer == "640"
    assert parse_math_translation("<think>hm</think>EXPR: 800*(1-0.25)+40", P1).answer == "640"


@pytest.mark.parametrize("raw,why", [
    ("EXPR: 800 * 0.75 + 41", "literal"),                 # 41 is not in the problem
    ("EXPR: 800 * (1 - 0.25)", "not used"),                # 40 unused
    ("EXPR: __import__('os').system('x')", "no plain"),
    ("EXPR: 800 / 0 + 40", "rejected"),
    ("I think the answer is 640", "no plain"),
    ("", "no plain"),
])
def test_math_defers(raw, why):
    r = parse_math_translation(raw, P1)
    assert not r.answered and why in r.reason


def test_math_percent_forms_and_constants():
    p = "A town of 5,000 people grows 10% every year. How many people live there after 2 years?"
    assert parse_math_translation("EXPR: 5000 * (1 + 0.1) ** 2", p).answer == "6050"
    assert parse_math_translation("EXPR: 5000 * 1.1 ** 2", p).answer == "6050"
    q = "A machine makes 90 parts every 15 minutes. How many parts in 3 hours?"
    assert parse_math_translation("EXPR: 90 / 15 * 60 * 3", q).answer == "1080"


PUZ = ("Three runners - Ann, Bo and Cy - finished a race with no ties.\n\n1. Ann beat Bo.\n2. Cy did not finish first.\n"
       "3. Bo did not finish second.\n\nWho finished first?")
SPEC = {"mode": "order", "entities": ["Ann", "Bo", "Cy"],
        "constraints": [{"type": "before", "who": "Ann", "other": "Bo"}, {"type": "not_at", "who": "Cy", "pos": 1},
                        {"type": "not_at", "who": "Bo", "pos": 2}], "question": {"type": "who_at", "pos": 1}}


def test_constraint_sentence_count():
    assert count_constraint_sentences(PUZ) == 3
    assert count_constraint_sentences("Three friends - A, B and C - each own a different pet: cat, dog, fish. A owns the cat. The fish belongs to either B or C. Who owns the dog?") == 2


def test_logic_good_and_fenced():
    assert parse_logic_translation(json.dumps(SPEC), PUZ).answer == "Ann"
    assert parse_logic_translation("```json\n" + json.dumps(SPEC) + "\n```", PUZ).answer == "Ann"


def mutate(**kw):
    s = json.loads(json.dumps(SPEC))
    s.update(kw)
    return json.dumps(s)


@pytest.mark.parametrize("raw,why", [
    (mutate(constraints=SPEC["constraints"][:2]), "constraint sentences"),           # a dropped constraint
    (mutate(entities=["Ann", "Bo", "Zed"]), "entity"),                                 # invented entity
    (mutate(question={"type": "who_at", "pos": 9}), "question"),
    ("no json here", "no JSON"),
    (mutate(mode="weird"), "invalid"),
    (mutate(constraints=[{"type": "teleport", "who": "Ann"}] * 3), "unknown constraint"),
    (mutate(constraints=[{"type": "not_at", "who": "Ann", "pos": 7}] * 3), "range"),
])
def test_logic_defers(raw, why):
    r = parse_logic_translation(raw, PUZ)
    assert not r.answered and why in r.reason


def test_logic_not_unique_defers():
    puz = "Three runners - Ann, Bo and Cy - finished a race with no ties. Ann beat Bo. Who finished first?"
    spec = {"mode": "order", "entities": ["Ann", "Bo", "Cy"], "constraints": [{"type": "before", "who": "Ann", "other": "Bo"}],
            "question": {"type": "who_at", "pos": 1}}
    r = parse_logic_translation(json.dumps(spec), puz)
    assert not r.answered and "more than one" in r.reason


def test_match_mode():
    puz = ("Three friends - Ann, Bo and Cy - each own a different pet: cat, dog, fish. Ann owns the cat. "
           "The fish belongs to either Bo or Cy. Cy does not own the fish. Who owns the dog?")
    spec = {"mode": "match", "entities": ["Ann", "Bo", "Cy"], "items": ["cat", "dog", "fish"],
            "constraints": [{"type": "has", "who": "Ann", "item": "cat"}, {"type": "either", "item": "fish", "a": "Bo", "b": "Cy"},
                            {"type": "not_has", "who": "Cy", "item": "fish"}], "question": {"type": "who_has", "item": "dog"}}
    assert parse_logic_translation(json.dumps(spec), puz).answer == "Cy"


def test_prompts_contain_schema():
    assert "EXPR:" in MATH_SYSTEM and "one_between" in LOGIC_SYSTEM


def test_math_free_constants_are_blocked():
    # a stray "+ 1" or "* 100 / 100" must not slip through as an allowed constant
    assert not parse_math_translation("EXPR: 800 * (1 - 0.25) + 40 + 1", P1).answered
    assert not parse_math_translation("EXPR: 800 * 100 * (1 - 0.25) / 100 + 40", P1).answered
    assert not parse_math_translation("EXPR: 800 * 60 * (1 - 0.25) + 40", P1).answered
