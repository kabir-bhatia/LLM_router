"""Unit tests for baseline / policy / replay logic on synthetic data (no Phase 3 results needed)."""
import numpy as np

from eval.phase4.policy_lib import (apply_guardrail, cascade_option, decide_cell, initial_policy, make_policy, noninferior,
                                     pick_baselines, replay)

CATS = ["math", "factual"]


def synth(n_per_cell=15, acc=None, costs=None, seed=0):
    """models: big (api, accurate, expensive), mid (api), cheap (api, bad), loc (local). acc[model][category] = P(correct)."""
    rng = np.random.default_rng(seed)
    acc = acc or {"big": {"math": 0.97, "factual": 0.97}, "mid": {"math": 0.93, "factual": 0.80},
                  "cheap": {"math": 0.60, "factual": 0.50}, "loc": {"math": 0.95, "factual": 0.40}}
    costs = costs or {"big": 0.010, "mid": 0.002, "cheap": 0.0005, "loc": 0.0}
    kinds = {"big": "api", "mid": "api", "cheap": "api", "loc": "local"}
    tasks, results = [], {}
    for c in CATS:
        for d in ("easy", "hard"):
            for i in range(n_per_cell):
                tid = f"{c}-{d}-{i}"
                tasks.append({"id": tid, "category": c, "difficulty": d, "prompt": f"{c} prompt {i}"})
                shared = rng.random()  # correlated difficulty: models fail on the same hard items
                for m in kinds:
                    results[(m, tid)] = {"passed": bool(shared < acc[m][c]), "cost": costs[m], "latency_ms": 50.0}
    return tasks, results, kinds


def test_noninferior_identical_and_clearly_worse():
    ok, lo, d = noninferior([1] * 30, [1] * 30)
    assert ok and d == 0 and lo == 0
    ok, lo, d = noninferior([1] * 15 + [0] * 15, [1] * 30)
    assert not ok and d == -0.5


def test_noninferior_is_deterministic():
    a = noninferior([1, 0, 1, 1] * 10, [1, 1, 1, 1] * 10)
    b = noninferior([1, 0, 1, 1] * 10, [1, 1, 1, 1] * 10)
    assert a == b


def test_baselines_b1_and_b2():
    tasks, results, kinds = synth(n_per_cell=30)
    out = pick_baselines(tasks, results, kinds)
    assert out["B1"]["model"] == "big"
    # B2 must be non-inferior and the cheapest such; 'cheap' (60% / 50%) cannot be
    assert out["B2"]["model"] in ("mid", "big")
    assert out["B2"]["cost_usd"] <= out["B1"]["cost_usd"]
    assert "cheap" not in (out["B1"]["model"], out["B2"]["model"])


def test_b1_tie_goes_to_cheaper():
    tasks, results, kinds = synth(n_per_cell=15, acc={"big": {"math": 1, "factual": 1}, "mid": {"math": 1, "factual": 1},
                                                      "cheap": {"math": 0.5, "factual": 0.5}, "loc": {"math": 0.5, "factual": 0.5}})
    assert pick_baselines(tasks, results, kinds)["B1"]["model"] == "mid"


def test_policy_routes_local_only_when_it_passes():
    tasks, results, kinds = synth(n_per_cell=15, seed=3)
    pol = make_policy(tasks, results, kinds, "big")
    # local model is as good as B1 on math: should win there (cheapest option); and fail on factual (40%)
    assert pol["cells"]["math|easy"]["model"] in ("loc", "mid")
    assert pol["cells"]["factual|easy"]["model"] != "loc"
    assert pol["cells"]["factual|hard"]["model"] != "cheap"


def test_floor_blocks_even_a_noninferior_option():
    # B1 itself is poor (70%); a candidate equal to B1 is non-inferior but below the 80% floor -> falls through to B1
    tasks = [{"id": f"t{i}", "category": "x", "difficulty": "easy", "prompt": "p"} for i in range(20)]
    results = {}
    for i, t in enumerate(tasks):
        ok = i < 14
        for m in ("b", "c"):
            results[(m, t["id"])] = {"passed": ok, "cost": 1.0 if m == "b" else 0.1, "latency_ms": 1}
    kinds = {"b": "api", "c": "api"}
    dec = decide_cell(tasks, results, kinds, "b", "x", "easy")
    assert dec["model"] == "b" and "no option qualified" in dec["reason"] or "B1" in dec["reason"]


def test_small_cell_falls_back_to_category():
    tasks, results, kinds = synth(n_per_cell=5)
    pol = make_policy(tasks, results, kinds, "big", min_cell=12)
    assert all(v["level"].startswith("category") for v in pol["cells"].values())
    assert pol["cells"]["math|easy"]["model"] == pol["cells"]["math|hard"]["model"]


def test_cascade_replay_escalates_on_validator_failure():
    tasks, results, kinds = synth(n_per_cell=15, seed=1)
    answers = {("loc", t["id"]): ("good" if i % 3 else "") for i, t in enumerate(tasks)}  # every 3rd local answer invalid
    vfn = lambda cat, prompt, raw: bool(raw)
    pol = {"b1": "big", "cells": {f"{c}|{d}": {"model": "loc", "kind": "local", "escalate_to": "big"} for c in CATS for d in ("easy", "hard")},
           "out_of_scope": {"model": "big"}}
    rp = replay(tasks, results, kinds, pol, validate_fn=vfn, answers=answers)
    assert rp["paths"]["escalated"] == sum(1 for i in range(len(tasks)) if i % 3 == 0)
    assert rp["paths"]["local"] + rp["paths"]["escalated"] == len(tasks)
    assert abs(rp["cost_usd"] - 0.010 * rp["paths"]["escalated"]) < 1e-9


def test_replay_solver_first_and_oos():
    tasks, results, kinds = synth(n_per_cell=15)
    pol = {"b1": "big", "cells": {f"{c}|{d}": {"model": "big", "kind": "api", "escalate_to": "big"} for c in CATS for d in ("easy", "hard")},
           "out_of_scope": {"model": "big"}}
    sol = {t["id"]: True for t in tasks if t["category"] == "math"}
    rp = replay(tasks, results, kinds, pol, solver_answers=sol)
    assert rp["paths"]["solver"] == 30 and rp["paths"]["api"] == 30
    labels = {t["id"]: ("out_of_scope", "easy") for t in tasks}
    rp2 = replay(tasks, results, kinds, pol, labels=labels)
    assert rp2["paths"]["api"] == len(tasks)


def test_cascade_option_costs_only_escalations():
    tasks, results, kinds = synth(n_per_cell=15)
    ids = [t["id"] for t in tasks if t["category"] == "math" and t["difficulty"] == "easy"]
    correct, cost = cascade_option(tasks, results, kinds, ids, "loc", "big", lambda c, p, r: False, {})
    assert cost == 0.010 * len(ids)


# ---------------------------------------------------------------- D12
def _mk(cell_specs, n=15):
    """cell_specs: {(cat, diff): {model: n_misses}} -> tasks/results; the first `misses` tasks of each cell are wrong for that model.
    Models: b (api, cost 1.0), c (api, 0.1), l (local)."""
    tasks, results = [], {}
    kinds = {"b": "api", "c": "api", "l": "local"}
    cost = {"b": 1.0, "c": 0.1, "l": 0.0}
    for (cat, d), miss in cell_specs.items():
        for i in range(n):
            tid = f"{cat}-{d}-{i}"
            tasks.append({"id": tid, "category": cat, "difficulty": d, "prompt": "p"})
            for m in kinds:
                results[(m, tid)] = {"passed": i >= miss.get(m, 0), "cost": cost[m], "latency_ms": 10.0}
    return tasks, results, kinds


def test_cell_rule_one_extra_miss_allowed_two_not():
    tasks, results, kinds = _mk({("x", "easy"): {"b": 1, "l": 2}, ("y", "easy"): {"b": 1, "l": 3}})
    assert decide_cell(tasks, results, kinds, "b", "x", "easy")["model"] == "l"      # 2 misses = B1's 1 + 1
    assert decide_cell(tasks, results, kinds, "b", "y", "easy")["model"] != "l"      # 3 misses: two more than B1


def test_cell_rule_needs_floor_even_with_few_misses():
    tasks, results, kinds = _mk({("x", "easy"): {"b": 4, "l": 5, "c": 5}})   # B1 itself is 11/15 = 73%
    d = decide_cell(tasks, results, kinds, "b", "x", "easy")
    assert d["model"] == "b"


def test_guardrail_hands_back_largest_loss_first_and_logs():
    # eight cells; the local model loses 2 tasks in each of 8 cells (each within the cell rule) -> router is 16/240-ish worse overall
    specs = {(f"c{i}", d): {"b": 0, "l": 1 if i else 1} for i in range(4) for d in ("easy", "hard")}
    specs[("c0", "easy")] = {"b": 0, "l": 1}
    specs[("c1", "hard")] = {"b": 0, "l": 1}
    tasks, results, kinds = _mk(specs)
    # make one cell the biggest loser (still qualifies: l has 1 miss, but replay with validators below adds loss)
    pol = initial_policy(tasks, results, kinds, "b")
    assert all(c["model"] == "l" for c in pol["cells"].values())
    vfn = lambda cat, prompt, raw: True
    pol = apply_guardrail(tasks, results, kinds, pol, validate_fn=vfn, answers={}, margin=0.0001)
    g = pol["guardrail"]
    assert g["steps"][0]["action"] == "initial policy" and not g["steps"][0]["passed"]
    assert g["final"]["passed"]
    assert any(c["model"] != c["initial_model"] for c in pol["cells"].values())
    assert all("HANDED BACK" in c["reason"] for c in pol["cells"].values() if c["model"] != c["initial_model"])
    # every step after the first names a cell and a loss
    assert all("hand back" in s["action"] for s in g["steps"][1:] if "solver" not in s["action"])


def test_guardrail_passes_untouched_when_router_matches_b1():
    tasks, results, kinds = _mk({("x", "easy"): {"b": 0, "l": 0}, ("x", "hard"): {"b": 0, "l": 0}})
    pol = make_policy(tasks, results, kinds, "b")
    assert len(pol["guardrail"]["steps"]) == 1 and pol["guardrail"]["final"]["passed"]
    assert all(c["model"] == "l" for c in pol["cells"].values())


def test_b2_uses_three_point_whole_set_test():
    tasks, results, kinds = _mk({("x", "easy"): {"b": 0, "c": 0}, ("y", "easy"): {"b": 0, "c": 0}}, n=60)
    out = pick_baselines(tasks, results, {"b": "api", "c": "api"})
    assert out["B1"]["model"] == "c"   # tie -> cheaper
    # make c clearly worse than b over 120 tasks
    for i in range(0, 60, 3):
        results[("c", f"x-easy-{i}")]["passed"] = False
    out = pick_baselines(tasks, results, {"b": "api", "c": "api"})
    assert out["B1"]["model"] == "b" and out["B2"]["model"] == "b"


def test_guardrail_uses_predicted_labels_and_hands_back_the_routed_cell():
    # x|easy: local is perfect; x|hard: local misses 6 of 15 so the cell rule keeps B1 there. If the classifier calls every hard task 'easy',
    # those tasks reach the local model: invisible with true labels, caught by the guardrail on predicted labels.
    tasks, results, kinds = _mk({("x", "easy"): {"b": 0, "l": 0}, ("x", "hard"): {"b": 0, "l": 6}})
    labels = {t["id"]: ("x", "easy") for t in tasks}
    true_pol = make_policy(tasks, results, kinds, "b")
    assert true_pol["cells"]["x|hard"]["model"] != "l" and true_pol["cells"]["x|easy"]["model"] == "l"
    assert len(true_pol["guardrail"]["steps"]) == 1 and true_pol["guardrail"]["final"]["passed"]       # true labels: no problem
    pol = make_policy(tasks, results, kinds, "b", labels=labels)
    g = pol["guardrail"]
    assert g["steps"][0]["action"] == "initial policy" and not g["steps"][0]["passed"]
    assert pol["cells"]["x|easy"]["model"] != "l" and "HANDED BACK" in pol["cells"]["x|easy"]["reason"]   # the cell the tasks were routed to
    assert g["final"]["passed"]
