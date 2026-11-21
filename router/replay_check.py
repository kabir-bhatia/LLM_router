"""Replay-consistency check (Phase 5 step 5): the production Router, fed RECORDED answers, must reproduce eval/phase4/policy_lib.replay().

    python -m router.replay_check [--policy path] [--out eval/results/phase5_replay_check.json]

For every dev task the Router is run with `labels` = the true labels, or the classifiers' predicted labels
(eval/results/phase4/predicted_labels.json), and compared per task with replay() on the same policy: path, correctness, cost, model.

Mismatches are never tolerated, only EXPLAINED and reported separately:
  blank_api_retry   the replay does not model the production rule "blank/failed API reply -> one retry on the next tier"; the recorded
                    first API answer was blank (Phase 3 graded it a miss), so the router retried and the replay did not.
  label_validator   (predicted labels vs the OFFICIAL replay only) replay() validates a recorded answer with the task's TRUE category, the router
                    with the category it predicted. Such a task is routed by the predicted category in both; only the validator differs. The
                    second reference ("replay_predicted_category": same replay with each task's category replaced by the predicted one) must
                    match the router exactly.
  (everything else is a bug and fails the test)
Correctness of a router answer = the Phase 3 graded `passed` of the recorded answer it returned (solver: the cascade oracle's `correct`
and the same answer string).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from eval.phase4.io_phase3 import load_answers, load_results
from eval.phase4.policy_lib import replay
from router.config import RouterConfig
from router.data import ROOT, load_dev
from router.pipeline import Router
from router.policy import Policy
from router.recorded import RecordedClient
from router.validators import validate

P4 = ROOT / "eval" / "results" / "phase4"


def load_inputs(policy_path=None):
    cfg = RouterConfig()
    if policy_path:
        cfg.policy_path = Path(policy_path)
    tasks = load_dev()
    results, kinds, _ = load_results()
    answers = load_answers(models={m for m, k in kinds.items() if k == "local"})
    sol_raw = json.loads((P4 / "solver_cascade_results.json").read_text(encoding="utf-8"))
    solver = {i: r for i, r in sol_raw.items() if r["answered"]}
    predicted = {i: tuple(v) for i, v in json.loads((P4 / "predicted_labels.json").read_text(encoding="utf-8")).items()}
    return cfg, tasks, results, kinds, answers, solver, predicted


def run_check(labels_name="true", policy_path=None, inputs=None, client_hook=None) -> dict:
    cfg, tasks, results, kinds, answers, solver, predicted = inputs or load_inputs(policy_path)
    policy = Policy.load(cfg.policy_path)
    labels = None if labels_name == "true" else predicted
    vfn = lambda cat, prompt, raw: validate(cat, prompt, raw).ok
    sol_ok = {i: bool(r["correct"]) for i, r in solver.items()} if policy.solvers_enabled else None

    # reference: the official Phase 4 replay (true category used for the validators, as policy_lib does)
    ref = replay(tasks, results, kinds, policy.data, vfn, answers, sol_ok, labels)
    # reference 2 (predicted labels only): the same replay with each task's category replaced by the predicted one, so the validators
    # run on the category the router actually used (the router validates by the category it predicted, replay() by the true one)
    ref_pc = None
    if labels is not None:
        pc_tasks = [{**t, "category": labels[t["id"]][0]} for t in tasks]
        ref_pc = replay(pc_tasks, results, kinds, policy.data, vfn, answers, sol_ok, labels)

    client = RecordedClient.from_disk(tasks, answers, kinds)
    if client_hook:
        client_hook(client)   # tests: inject a blank API answer to prove the retry divergence is detected and reported
    router = Router(policy, client, None, cfg)
    rows = []
    for t in tasks:
        res = router.route(t["prompt"], labels=(t["category"], t["difficulty"]) if labels is None else labels[t["id"]])
        if res.layer == "solver":
            path, correct = "solver", bool(solver[t["id"]]["correct"]) if t["id"] in solver and res.answer == f"ANSWER: {solver[t['id']]['answer']}" else False
        elif res.layer == "local":
            path, correct = "local", (results.get((res.model, t["id"])) or {}).get("passed") is True
        elif res.layer == "api":
            path = "escalated" if res.escalated and policy.cell(res.category, res.difficulty) and \
                policy.cell(res.category, res.difficulty)["kind"] == "local" else "api"
            correct = (results.get((res.model, t["id"])) or {}).get("passed") is True
        else:
            path, correct = "error", False
        rows.append({"id": t["id"], "path": path, "correct": correct, "cost": res.cost_usd, "model": res.model, "escalated": res.escalated,
                     "category": res.category, "plan": res.plan, "trace": [(e.get("step"), e.get("model"), e.get("ok")) for e in res.trace]})

    def diff(reference):
        out = []
        for mine, theirs in zip(rows, reference["rows"]):
            assert mine["id"] == theirs["id"]
            why = []
            if mine["path"] != theirs["path"]:
                why.append(f"path {mine['path']} vs {theirs['path']}")
            if mine["correct"] != theirs["correct"]:
                why.append(f"correct {mine['correct']} vs {theirs['correct']}")
            if abs(mine["cost"] - theirs["cost"]) > 1e-12:
                why.append(f"cost {mine['cost']:.7f} vs {theirs['cost']:.7f}")
            if why:
                out.append({"id": mine["id"], "why": why, "router": mine, "replay": theirs})
        return out

    true_cat = {t["id"]: t["category"] for t in tasks}

    def classify(diffs):
        blank, other, label = [], [], []
        for d in diffs:
            first_api = next((e for e in d["router"]["trace"] if e[0] == "api"), None)
            blank_first = False
            if first_api is not None:
                r = client.api_rows.get((first_api[1], d["id"]))
                blank_first = first_api[2] is False and r is not None and not (r.get("raw_text") or "").strip()
            if blank_first and d["router"]["escalated"]:
                blank.append(d)
            elif d["router"]["category"] != true_cat[d["id"]]:
                label.append(d)
            else:
                other.append(d)
        return blank, label, other

    out = {"labels": labels_name, "policy": str(cfg.policy_path), "n": len(rows), "solvers_enabled": policy.solvers_enabled,
           "router": {"accuracy": sum(r["correct"] for r in rows) / len(rows), "cost_usd": sum(r["cost"] for r in rows),
                      "paths": {p: sum(1 for r in rows if r["path"] == p) for p in ("solver", "local", "escalated", "api", "error")}},
           "replay_official": {"accuracy": ref["accuracy"], "cost_usd": ref["cost_usd"], "paths": ref["paths"]}}
    refs = {"replay_official": ref}
    if ref_pc is not None:
        out["replay_predicted_category"] = {"accuracy": ref_pc["accuracy"], "cost_usd": ref_pc["cost_usd"], "paths": ref_pc["paths"]}
        refs["replay_predicted_category"] = ref_pc
    for name, rf in refs.items():
        blank, label, other = classify(diff(rf))
        out[name]["blank_api_retry_tasks"] = blank
        out[name]["label_validator_tasks"] = label
        out[name]["unexplained_mismatches"] = other
    out["rows"] = rows
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default=None)
    ap.add_argument("--out", default=str(ROOT / "eval" / "results" / "phase5_replay_check.json"))
    a = ap.parse_args(argv)
    inputs = load_inputs(a.policy)
    res = {name: run_check(name, inputs=inputs) for name in ("true", "predicted")}
    Path(a.out).write_text(json.dumps({k: {x: y for x, y in v.items() if x != "rows"} for k, v in res.items()}, indent=1, default=str), encoding="utf-8")
    for name, r in res.items():
        print(name, "router acc %.4f cost $%.4f" % (r["router"]["accuracy"], r["router"]["cost_usd"]), r["router"]["paths"])
        for ref in [k for k in r if k.startswith("replay_")]:
            print("  vs", ref, "acc %.4f cost $%.4f" % (r[ref]["accuracy"], r[ref]["cost_usd"]),
                  "| blank-retry tasks:", len(r[ref]["blank_api_retry_tasks"]), "| label-validator:", len(r[ref]["label_validator_tasks"]), "| unexplained:", len(r[ref]["unexplained_mismatches"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
