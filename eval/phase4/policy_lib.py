"""Policy and baseline logic (D2, D9, D12), written against plain data structures so it can be unit-tested on synthetic data.

Data model
  tasks   : list of dicts {id, category, difficulty, prompt}            (dev split only)
  results : dict {(model, task_id): {"passed": bool, "cost": float, "latency_ms": float|None}}
  kinds   : dict {model: "local" | "api"}

Rules implemented (D12 replaced the per-cell bootstrap test of D4 after the power analysis)
  Cell rule      per category x difficulty cell (category-level decision when the cell has < MIN_CELL tasks): the cheapest option, in the order
                 local models ($0 marginal, ordered by latency) then API models (ordered by dev cost in the cell), that has at most
                 CELL_EXTRA_MISSES (1) more misses than B1 in the cell AND accuracy >= FLOOR (80%). Plain counts, no resampling.
  Guardrail      replay the whole cascade (solver -> local + validators -> API) on all dev tasks; the router must be at most GUARD_MARGIN
                 (3 points) less accurate than B1 at 95% confidence (one-sided paired bootstrap). If not, hand cells back to the next
                 qualifying option up (ultimately B1), largest accuracy loss first, until it passes. Every step is logged.
  B1 (D2)        most accurate API model on dev (ties -> cheaper).
  B2 (D12)       cheapest single API model that passes the same 240-task test against B1.
"""
from __future__ import annotations

import numpy as np

CELL_EXTRA_MISSES = 1
FLOOR = 0.80
GUARD_MARGIN = 0.03
ALPHA = 0.05          # one-sided 95% confidence
N_BOOT = 10000
MIN_CELL = 10
SEED = 20251120


# ------------------------------------------------------------------ paired bootstrap (used for B2 and the guardrail)
def noninferior(cand, ref, margin: float = GUARD_MARGIN, alpha: float = ALPHA, n_boot: int = N_BOOT, seed: int = SEED):
    """Paired bootstrap non-inferiority: resample tasks with replacement, compute acc(cand) - acc(ref); pass if the alpha-quantile
    (one-sided 95% lower bound) of the difference is >= -margin. Returns (passed, lower_bound, observed_diff)."""
    cand = np.asarray(cand, float)
    ref = np.asarray(ref, float)
    assert cand.shape == ref.shape and cand.ndim == 1 and len(cand) > 0
    n = len(cand)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    d = (cand - ref)[idx].mean(axis=1)
    lower = float(np.quantile(d, alpha))
    return lower >= -margin - 1e-12, lower, float(cand.mean() - ref.mean())


# ------------------------------------------------------------------ helpers
def api_models(kinds):
    return [m for m, k in kinds.items() if k == "api"]


def local_models(kinds):
    return [m for m, k in kinds.items() if k == "local"]


def vec(results, model, task_ids):
    """0/1 correctness vector; a missing or ungraded answer counts as wrong."""
    out = []
    for t in task_ids:
        r = results.get((model, t))
        out.append(1.0 if (r is not None and r["passed"] is True) else 0.0)
    return np.array(out)


def cost_sum(results, model, task_ids):
    return float(sum((results.get((model, t)) or {}).get("cost") or 0.0 for t in task_ids))


def accuracy(results, model, task_ids):
    v = vec(results, model, task_ids)
    return float(v.mean()) if len(v) else float("nan")


# ------------------------------------------------------------------ D2 / D12 baselines
def pick_baselines(tasks, results, kinds, margin=GUARD_MARGIN, n_boot=N_BOOT):
    ids = [t["id"] for t in tasks]
    rows = []
    for m in api_models(kinds):
        rows.append({"model": m, "accuracy": accuracy(results, m, ids), "cost_usd": cost_sum(results, m, ids),
                     "n": int(sum(1 for t in ids if (m, t) in results))})
    # B1: most accurate, ties -> cheaper (exact equality of correct counts)
    rows.sort(key=lambda r: (-round(r["accuracy"] * len(ids)), r["cost_usd"]))
    b1 = rows[0]
    ref = vec(results, b1["model"], ids)
    for r in rows:
        ok, lo, diff = noninferior(vec(results, r["model"], ids), ref, margin, n_boot=n_boot)
        r.update({"noninferior_to_b1": bool(ok), "diff_lower_bound": lo, "diff_observed": diff})
    cands = sorted([r for r in rows if r["noninferior_to_b1"]], key=lambda r: (r["cost_usd"], -r["accuracy"]))
    b2 = cands[0]
    return {"B1": {"model": b1["model"], "accuracy": b1["accuracy"], "cost_usd": b1["cost_usd"],
                   "rule": "most accurate API model on the dev tasks; ties go to the cheaper"},
            "B2": {"model": b2["model"], "accuracy": b2["accuracy"], "cost_usd": b2["cost_usd"],
                   "diff_vs_b1_lower_bound": b2["diff_lower_bound"],
                   "rule": f"D12: cheapest single API model at most {int(round(margin*100))} points worse than B1 at 95% confidence "
                           f"(one-sided paired bootstrap over all {len(ids)} dev tasks)"},
            "n_dev_tasks": len(ids), "table": rows}


# ------------------------------------------------------------------ cell rule
def _cell_ids(tasks, category, difficulty=None):
    return [t["id"] for t in tasks if t["category"] == category and (difficulty is None or t["difficulty"] == difficulty)]


def _order_options(results, kinds, ids):
    """Cheapest first: local models ($0 marginal; ties by mean latency, then by name), then API models by cost on these tasks."""
    def lat(m):
        v = [(results.get((m, t)) or {}).get("latency_ms") for t in ids]
        v = [x for x in v if x is not None]
        return float(np.mean(v)) if v else float("inf")
    loc = sorted(local_models(kinds), key=lambda m: (lat(m), m))
    api = sorted(api_models(kinds), key=lambda m: (cost_sum(results, m, ids), m))
    return loc + api


def option_correct(tasks, results, kinds, ids, model, fallback, mode, validate_fn, answers):
    """Correctness vector of an option over the ids. mode 'raw': the model's own answers; mode 'cascade': for a local model,
    its answer when the validators pass, else the fallback's answer (escalation; B2 by default in the router, D12 update 2026-11-21)."""
    if mode == "cascade" and kinds[model] == "local":
        return cascade_option(tasks, results, kinds, ids, model, fallback, validate_fn, answers)[0]
    return vec(results, model, ids)


def decide_cell(tasks, results, kinds, b1, category, difficulty, mode="raw", validate_fn=None, answers=None,
                extra_misses=CELL_EXTRA_MISSES, floor=FLOOR, fallback=None):
    """D12 cell rule. Returns the chosen route plus the full ladder (options in cost order up to B1) and which of them qualify."""
    ids = _cell_ids(tasks, category, difficulty)
    ref_misses = int(len(ids) - vec(results, b1, ids).sum())
    ladder, log = [], []
    chosen = None
    for m in _order_options(results, kinds, ids):
        if m == b1:
            ladder.append(m)
            break
        c = option_correct(tasks, results, kinds, ids, m, fallback or b1, mode, validate_fn, answers)
        misses = int(len(ids) - c.sum())
        acc = float(c.mean())
        ok = (misses <= ref_misses + extra_misses) and acc >= floor
        log.append({"model": m, "misses": misses, "acc": acc, "qualifies": bool(ok)})
        if ok:
            ladder.append(m)
            if chosen is None:
                chosen = (m, f"accuracy {acc:.0%} ({misses} misses of {len(ids)}) vs B1 {ref_misses} misses; rule: at most {ref_misses + extra_misses} misses and >= {floor:.0%}")
    if not ladder or ladder[-1] != b1:
        ladder.append(b1)
    if chosen is None:
        chosen = (b1, "no cheaper option had <= %d misses and >= %.0f%%; B1" % (ref_misses + extra_misses, floor * 100))
    return {"model": chosen[0], "kind": kinds[chosen[0]], "reason": chosen[1], "n": len(ids), "b1_misses": ref_misses,
            "ladder": ladder, "considered": log}


def cascade_option(tasks, results, kinds, ids, local_model, fallback, validate_fn, answers):
    """Correctness and cost of 'local_model, escalate to fallback when validators fail' over the task ids."""
    by_id = {t["id"]: t for t in tasks}
    correct, cost = [], 0.0
    for t in ids:
        r = results.get((local_model, t))
        accept = r is not None
        if accept and validate_fn is not None:
            raw = (answers or {}).get((local_model, t), "")
            accept = validate_fn(by_id[t]["category"], by_id[t]["prompt"], raw)
        if accept:
            correct.append(1.0 if r["passed"] is True else 0.0)
        else:
            f = results.get((fallback, t))
            correct.append(1.0 if (f is not None and f["passed"] is True) else 0.0)
            cost += (f or {}).get("cost") or 0.0
    return np.array(correct), cost


def initial_policy(tasks, results, kinds, b1, mode="raw", validate_fn=None, answers=None, min_cell=MIN_CELL, fallback=None):
    """B1 is the reference (and the top of every cell's ladder). `fallback` (default B1) is where validator-failed local answers and out-of-scope prompts go."""
    fb = fallback or b1
    cats = sorted({t["category"] for t in tasks})
    policy = {"b1": b1, "fallback": fb, "mode": mode, "cells": {},
              "out_of_scope": {"model": fb, "reason": "D9: no category fits -> straight to the fallback model" + (" (B2)" if fb != b1 else " (B1)")}}
    for c in cats:
        cat_decision = None
        for d in ("easy", "hard"):
            ids = _cell_ids(tasks, c, d)
            if len(ids) >= min_cell:
                dec = decide_cell(tasks, results, kinds, b1, c, d, mode, validate_fn, answers, fallback=fb)
                dec["level"] = "cell"
            else:
                if cat_decision is None:
                    cat_decision = decide_cell(tasks, results, kinds, b1, c, None, mode, validate_fn, answers, fallback=fb)
                dec = dict(cat_decision)
                dec["level"] = "category (cell had %d < %d tasks)" % (len(ids), min_cell)
            dec["escalate_to"] = fb
            dec["initial_model"] = dec["model"]
            policy["cells"][f"{c}|{d}"] = dec
    return policy


# ------------------------------------------------------------------ cascade replay
def replay(tasks, results, kinds, policy, validate_fn=None, answers=None, solver_answers=None, labels=None, hw_rates=None):
    """Replay the real cascade for every dev task. `solver_answers`: {task_id: bool correct} for tasks the solver answered (absent = defers).
    `labels`: optional {task_id: (category, difficulty)} from the classifiers (default: true labels).
    `hw_rates`: optional {model: USD per hour}; every local attempt by such a model adds latency x rate to `hw_cost_usd` (reported separately, cost_usd is unchanged).
    Returns per-task rows and totals (accuracy, cost, escalation counts)."""
    rows = []
    for t in tasks:
        cat, diff = (labels or {}).get(t["id"], (t["category"], t["difficulty"]))
        cell = policy["cells"].get(f"{cat}|{diff}") if cat != "out_of_scope" else None
        route = cell if cell else {"model": policy["out_of_scope"]["model"], "kind": "api", "escalate_to": policy["out_of_scope"]["model"]}
        path, correct, cost, hw = None, False, 0.0, 0.0
        if solver_answers is not None and t["id"] in solver_answers and cat in ("math", "logic"):
            path, correct = "solver", bool(solver_answers[t["id"]])
        elif route["kind"] == "local":
            r = results.get((route["model"], t["id"]))
            if hw_rates and route["model"] in hw_rates:
                hw = ((r or {}).get("latency_ms") or 0.0) / 3.6e6 * hw_rates[route["model"]]
            accept = r is not None
            if accept and validate_fn is not None:
                accept = validate_fn(t["category"], t["prompt"], (answers or {}).get((route["model"], t["id"]), ""))
            if accept:
                path, correct = "local", r["passed"] is True
            else:
                f = results.get((route["escalate_to"], t["id"])) or {}
                path, correct, cost = "escalated", f.get("passed") is True, f.get("cost") or 0.0
        else:
            r = results.get((route["model"], t["id"])) or {}
            path, correct, cost = "api", r.get("passed") is True, r.get("cost") or 0.0
        rows.append({"id": t["id"], "category": t["category"], "difficulty": t["difficulty"], "path": path,
                     "correct": bool(correct), "cost": cost, "hw_cost": hw, "route_model": route["model"],
                     "routed_cell": f"{cat}|{diff}" if cell else None})
    n = len(rows)
    return {"rows": rows, "n": n, "accuracy": sum(r["correct"] for r in rows) / n, "cost_usd": sum(r["cost"] for r in rows),
            "hw_cost_usd": sum(r["hw_cost"] for r in rows),
            "paths": {p: sum(1 for r in rows if r["path"] == p) for p in ("solver", "local", "escalated", "api")}}


def always(tasks, results, model):
    ids = [t["id"] for t in tasks]
    return {"accuracy": accuracy(results, model, ids), "cost_usd": cost_sum(results, model, ids), "n": len(ids)}


# ------------------------------------------------------------------ D12 guardrail
def guardrail_check(tasks, results, kinds, policy, b1, validate_fn=None, answers=None, solver_answers=None,
                    margin=GUARD_MARGIN, n_boot=N_BOOT, labels=None):
    """`labels`: optional {task_id: (category, difficulty)} (the classifiers' out-of-fold predictions); default true labels."""
    rp = replay(tasks, results, kinds, policy, validate_fn, answers, solver_answers, labels)
    ids = [t["id"] for t in tasks]
    router = np.array([1.0 if r["correct"] else 0.0 for r in rp["rows"]])
    ref = vec(results, b1, ids)
    ok, lo, diff = noninferior(router, ref, margin, n_boot=n_boot)
    return {"passed": bool(ok), "lower_bound": lo, "diff_observed": diff, "router_accuracy": float(router.mean()),
            "b1_accuracy": float(ref.mean()), "router_cost_usd": rp["cost_usd"], "replay": rp}


def _next_up(cell):
    """Next qualifying option above the current one on the cell's ladder (ending in B1)."""
    lad = cell["ladder"]
    i = lad.index(cell["model"])
    return lad[min(i + 1, len(lad) - 1)]


def apply_guardrail(tasks, results, kinds, policy, validate_fn=None, answers=None, solver_answers=None,
                    margin=GUARD_MARGIN, n_boot=N_BOOT, labels=None):
    """Hand cells back (largest accuracy loss first) until the whole-router test passes. Mutates and returns the policy;
    policy['guardrail'] holds the full step log."""
    b1 = policy["b1"]
    steps = []
    solver_on = solver_answers
    chk = guardrail_check(tasks, results, kinds, policy, b1, validate_fn, answers, solver_on, margin, n_boot, labels)
    steps.append({"step": 0, "action": "initial policy", "passed": chk["passed"], "lower_bound": chk["lower_bound"],
                  "router_accuracy": chk["router_accuracy"], "b1_accuracy": chk["b1_accuracy"]})
    while not chk["passed"]:
        rows = {r["id"]: r for r in chk["replay"]["rows"]}
        best = None
        for k, cell in policy["cells"].items():
            if cell["model"] == b1:
                continue
            # tasks the router actually sends to this cell (its predicted label when `labels` is given)
            ids = [i for i, r in rows.items() if r["routed_cell"] == k]
            if not ids:
                continue
            loss = int(vec(results, b1, ids).sum() - sum(1 for t in ids if rows[t]["correct"]))
            key = (loss, len(ids), k)
            if best is None or key > best[0]:
                best = (key, k)
        if best is None:
            if solver_on:
                solver_on = None
                chk = guardrail_check(tasks, results, kinds, policy, b1, validate_fn, answers, solver_on, margin, n_boot, labels)
                steps.append({"step": len(steps), "action": "all cells already at B1; solvers switched off", "passed": chk["passed"],
                              "lower_bound": chk["lower_bound"], "router_accuracy": chk["router_accuracy"], "b1_accuracy": chk["b1_accuracy"]})
                policy["solvers_enabled"] = False
                continue
            steps.append({"step": len(steps), "action": "all cells at B1 and still failing (should not happen)", "passed": False})
            break
        (loss, _n, _k), k = best
        cell = policy["cells"][k]
        old, new = cell["model"], _next_up(cell)
        cell["model"], cell["kind"] = new, kinds[new]
        cell["reason"] += f"; HANDED BACK by the guardrail from {old} to {new} (cell loss vs B1: {loss} tasks)"
        chk = guardrail_check(tasks, results, kinds, policy, b1, validate_fn, answers, solver_on, margin, n_boot, labels)
        steps.append({"step": len(steps), "action": f"hand back {k}: {old} -> {new}", "cell_loss_vs_b1": loss, "passed": chk["passed"],
                      "lower_bound": chk["lower_bound"], "router_accuracy": chk["router_accuracy"], "b1_accuracy": chk["b1_accuracy"]})
    policy["guardrail"] = {"margin": margin, "confidence": 0.95, "final": {k: v for k, v in chk.items() if k != "replay"}, "steps": steps}
    policy.setdefault("solvers_enabled", True)
    return policy


def make_policy(tasks, results, kinds, b1, mode="raw", validate_fn=None, answers=None, solver_answers=None, min_cell=MIN_CELL,
                n_boot=N_BOOT, guardrail=True, labels=None, fallback=None):
    pol = initial_policy(tasks, results, kinds, b1, mode, validate_fn, answers, min_cell, fallback)
    if guardrail:
        apply_guardrail(tasks, results, kinds, pol, validate_fn, answers, solver_answers, n_boot=n_boot, labels=labels)
    return pol
