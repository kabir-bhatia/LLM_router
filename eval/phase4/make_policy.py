"""D12/D9: derive the routing policy (cell rule + whole-router guardrail) from the dev benchmark and replay the real cascade on the dev tasks.

Usage: python -m eval.phase4.make_policy [--scores FILE ...] [--out-dir eval/results/phase4]
Writes routing_policy.json (main tier: laptop-class local models + APIs; D12 cell rule on each option's own accuracy), routing_policy_cascade.json (variant judging
local options by their cascade accuracy) and the same two with the GPU-server models added (routing_policy_gpu_server*.json). The guardrail replays on out-of-fold
predicted labels. Also policy_replay.json. policy_report.md is written by eval/phase4/write_policy_report.py.
"""
import argparse
import json

from eval.phase4.io_phase3 import load_answers, load_results
from eval.phase4.policy_lib import always, api_models, make_policy, replay
from router.data import ROOT, load_dev
from router.validators import validate


def solver_correct():
    """{task_id: correct} for tasks the solver path answers. Uses the combined path (pure-Python first, then the chosen D13 translator)
    when eval_translators.py has produced it; otherwise the pure-Python solvers alone."""
    d = ROOT / "eval" / "results" / "phase4"
    comb = d / "solver_cascade_results.json"
    if comb.exists():
        return {i: bool(r["correct"]) for i, r in json.loads(comb.read_text(encoding="utf-8")).items() if r["answered"]}
    rows = json.loads((d / "solver_results.json").read_text(encoding="utf-8"))
    return {r["id"]: bool(r["correct"]) for r in rows if r["answered"]}


GPU_SERVER = ("gemma3:12b", "phi4:14b", "qwen2.5:14b")   # D1/D11: separately reported tier, never an option in the main policy
GPU_RATE = 0.35                                            # USD per hour of a T4 instance (D5)


def predicted_labels(tasks):
    """Out-of-fold classifier guesses {task_id: (category, difficulty)} from eval_difficulty.py (5-fold CV; category from the CV hybrid classifier)."""
    raw = json.loads((ROOT / "eval" / "results" / "phase4" / "predicted_labels.json").read_text(encoding="utf-8"))
    assert set(raw) == {t["id"] for t in tasks}, "predicted_labels.json must cover exactly the 240 dev tasks"
    return {i: tuple(v) for i, v in raw.items()}


def summarise(rp):
    return {k: v for k, v in rp.items() if k != "rows"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", nargs="*", default=None)
    ap.add_argument("--answers", nargs="*", default=None)
    ap.add_argument("--out-dir", default=str(ROOT / "eval" / "results" / "phase4"))
    a = ap.parse_args(argv)
    out = __import__("pathlib").Path(a.out_dir)
    tasks = load_dev()
    results, kinds_all, _ = load_results(a.scores)
    answers = load_answers(a.answers, models={m for m, k in kinds_all.items() if k == "local"})
    base = json.loads((out / "baselines.json").read_text(encoding="utf-8"))
    b1, b2 = base["B1"]["model"], base["B2"]["model"]
    vfn = lambda cat, prompt, raw: validate(cat, prompt, raw).ok
    sol = solver_correct()
    labels = predicted_labels(tasks)
    # main tier: laptop-class local models + APIs. server tier: the same plus the three GPU-server models.
    kinds_main = {m: k for m, k in kinds_all.items() if m not in GPU_SERVER}
    tiers = {"main": (kinds_main, ""), "gpu_server": (kinds_all, "_gpu_server")}
    hw = {m: GPU_RATE for m in GPU_SERVER}
    summary = {"b1": b1, "b2": b2, "always_b1": always(tasks, results, b1), "always_b2": always(tasks, results, b2),
               "labels": "official = out-of-fold predicted labels (guardrail and headline replay); true labels shown for reference",
               "main_options": sorted(kinds_main), "gpu_server_models": list(GPU_SERVER), "variants": {}}
    for tier, (kinds, suffix) in tiers.items():
        for mode, stem in (("raw", "routing_policy"), ("cascade", "routing_policy_cascade")):
            fname = stem.replace("routing_policy", "routing_policy" + suffix) + ".json"
            # cell rule on true labels; guardrail replay on the predicted labels (D12 update, agreed 2026-11-21)
            pol = make_policy(tasks, results, kinds, b1, mode=mode, validate_fn=vfn, answers=answers, solver_answers=sol, labels=labels, fallback=b2)
            pol["tier"] = tier
            pol["escalation_note"] = "escalate_to and out_of_scope = B2 (D12 update 2026-11-21); B1 is the reference and the top of each cell ladder"
            pol["guardrail_labels"] = "out-of-fold predicted (category, difficulty)"
            (out / fname).write_text(json.dumps(pol, indent=1), encoding="utf-8")
            use_sol = sol if pol.get("solvers_enabled", True) else None
            v = {"policy_file": fname, "tier": tier, "rows_predicted": None}
            for lab, lbl in (("predicted", labels), ("true", None)):
                for sname, ss in (("with_solvers", use_sol), ("without_solvers", None)):
                    rp = replay(tasks, results, kinds, pol, validate_fn=vfn, answers=answers, solver_answers=ss, labels=lbl,
                                hw_rates=hw if tier == "gpu_server" else None)
                    v[f"{lab}_{sname}"] = summarise(rp)
                    if lab == "predicted" and sname == "with_solvers":
                        v["rows_predicted"] = rp["rows"]
            summary["variants"][f"{tier}/{mode}"] = v
    (out / "policy_replay.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "variants"}, indent=1))
    for name, v in summary["variants"].items():
        print(name, "predicted:", v["predicted_with_solvers"])
        print("   true:", v["true_with_solvers"])


if __name__ == "__main__":
    main()
